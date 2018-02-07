import json
import socket
import subprocess
from miners import Algorithm, Miner
from time import sleep

class ExcavatorError(Exception):
    pass

class ExcavatorAPIError(ExcavatorError):
    """Exception returned by excavator."""
    def __init__(self, response):
        self.response = response
        self.error = response['error']

class ExcavatorServer:
    BUFFER_SIZE = 1024
    TIMEOUT = 10

    def __init__(self, executable, port):
        self.executable = executable
        self.address = ('127.0.0.1', port)
        # dict of algorithm name -> (excavator algorithm id, [attached devices])
        self.running_algorithms = {}
        # dict of device id -> excavator worker id
        self.running_workers = {}

    def start(self):
        """Launches excavator."""
        self.process = subprocess.Popen([self.executable,
                                         '-i', self.address[0],
                                         '-p', str(self.address[1])])
        while not self.test_connection():
            sleep(1)

    def stop(self):
        """Stops excavator."""
        active_devices = list(self.running_workers.keys())
        for device in active_devices:
            self.free_device(device)
        self.process.terminate()
        self.process.wait()

    def send_command(self, method, params):
        """Sends a command to excavator, returns the JSON-encoded response.

        method -- name of the command to execute
        params -- list of arguments for the command
        """

        command = {
            'id': 1,
            'method': method,
            'params': params
            }
        s = socket.create_connection(self.address, self.TIMEOUT)
        # send newline-terminated command
        s.sendall((json.dumps(command).replace('\n', '\\n') + '\n').encode())
        response = ''
        while True:
            chunk = s.recv(self.BUFFER_SIZE).decode()
            # excavator responses are newline-terminated too
            if '\n' in chunk:
                response += chunk[:chunk.index('\n')]
                break
            else:
                response += chunk
        s.close()

        response_data = json.loads(response)
        if response_data['error'] is None:
            return response_data
        else:
            raise ExcavatorAPIError(response_data)

    def test_connection(self):
        try:
            self.send_command('info', [])
        except (socket.error, socket.timeout):
            return False
        else:
            return True

    def dispatch_device(self, algorithm, stratums, auth, device):
        if algorithm not in self.running_algorithms:
            add_params = [algorithm] + sum([[stratums[i], auth] for i, ma in
                                            enumerate(algorithm.split('_'))], [])

            response = self.send_command('algorithm.add', add_params)
            algorithm_id = response['algorithm_id']
            self.running_algorithms[algorithm] = (algorithm_id, [device])
        else:
            algorithm_id = self.running_algorithms[algorithm][0]
            self.running_algorithms[algorithm][1].append(device)

        response = self.send_command('worker.add', [str(algorithm_id),
                                                    str(device.index)])
        self.running_workers[device] = response['worker_id']

    def free_device(self, device):
        algorithm = [a for a in self.running_algorithms.keys() if
                     device in self.running_algorithms[a][1]][0]
        self.running_algorithms[algorithm][1].remove(device)
        worker_id = self.running_workers[device]
        self.running_workers.pop(device)

        self.send_command('worker.free', [str(worker_id)])

        if len(self.running_algorithms[algorithm][1]) == 0: # no more devices
            algorithm_id = self.running_algorithms[algorithm][0]
            self.running_algorithms.pop(algorithm)

            self.send_command('algorithm.remove', [str(algorithm_id)])

    def device_speeds(self, device):
        algorithm = [a for a in self.running_algorithms.keys() if
                     device in self.running_algorithms[a][1]][0]

        response = self.send_command('algorithm.list', [])

        algorithm_data = [ad for ad in response['algorithms'] if
                          ad['name'] == algorithm][0]
        worker_id = self.running_workers[device]
        worker_data = [wd for wd in algorithm_data['workers'] if
                       wd['worker_id'] == worker_id][0]
        return worker_data['speed']

class ExcavatorAlgorithm(Algorithm):
    def __init__(self, algorithm, excavator, device):
        super(ExcavatorAlgorithm, self).__init__('excavator_%s' % algorithm,
                                                 algorithm.split('_'), device)

        self.excavator = excavator

    def run(self, stratums, auth):
        self.excavator.server.dispatch_device('_'.join(self.algorithms),
                                              stratums, auth, self.device)

    def stop(self):
        self.excavator.server.free_device(self.device)

    def current_speeds(self):
        speeds = self.excavator.server.device_speeds(self.device)
        if len(self.algorithms) == 2:
            return speeds
        else:
            return speeds[:1]

class Excavator(Miner):
    ALGORITHMS = [
        'equihash',
        'pascal',
        'decred',
        'sia',
        'lbry',
        'blake2s',
        'daggerhashimoto',
        'lyra2rev2',
        'daggerhashimoto_decred',
        'daggerhashimoto_sia',
        'daggerhashimoto_pascal',
        'cryptonight',
        'keccak',
        'neoscrypt',
        'nist5'
        ]

    def __init__(self, settings, devices):
        super(Excavator, self).__init__(settings, devices)

        self.settings = settings
        self.server = None
        for device in devices:
            for algorithm in self.ALGORITHMS:
                runnable = ExcavatorAlgorithm(algorithm, self, device)
                self.algorithms[device].append(runnable)

    def load(self):
        self.server = ExcavatorServer(self.settings['excavator']['path'],
                                      self.settings['excavator']['port'])
        self.server.start()

    def unload(self):
        self.server.stop()
        self.server = None

