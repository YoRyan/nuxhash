import miner

import json
import socket
import subprocess
import threading
from time import sleep

class ExcavatorError(Exception):
    pass

class ExcavatorAPIError(ExcavatorError):
    """Exception returned by excavator."""
    def __init__(self, response):
        self.response = response
        self.error = response['error']

class ExcavatorServer(object):
    BUFFER_SIZE = 1024
    TIMEOUT = 10

    def __init__(self, executable, port, stratums, auth):
        self.executable = executable
        self.address = ('127.0.0.1', port)
        self.stratums = stratums
        self.auth = auth
        # dict of algorithm name -> (excavator algorithm id, [attached devices])
        self.running_algorithms = {}
        # dict of device id -> excavator worker id
        # TODO allow multiple simultaneous algorithms per device
        self.running_workers = {}

    def start(self):
        """Launches excavator."""
        self.process = subprocess.Popen([self.executable,
                                         '-i', self.address[0],
                                         '-p', str(self.address[1])],
                                        stdin=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        stdout=subprocess.PIPE)
        # send stdout to logger
        log_thread = threading.Thread(target=miner.log_output, args=(self.process,))
        log_thread.start()

        while not self.test_connection():
            if self.process.poll() is None:
                sleep(1)
            else:
                raise miner.MinerStartFailed

    def stop(self):
        """Stops excavator."""
        self.running_workers = {}
        try:
            self.send_command('quit', [])
        except socket.error as err:
            if err.errno != 104: # expected error: connection reset by peer
                raise
        else:
            self.process.wait()
            self.stdout = None

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

    def dispatch_device(self, algorithm, device):
        """Start running algorithm on device."""
        if algorithm not in self.running_algorithms:
            add_params = [algorithm] + sum([[self.stratums[ma], self.auth]
                                            for ma in algorithm.split('_')], [])

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
        """Stop running the active algorithm on device."""
        algorithm = [a for a in self.running_algorithms.keys()
                     if device in self.running_algorithms[a][1]][0]
        self.running_algorithms[algorithm][1].remove(device)
        worker_id = self.running_workers[device]
        self.running_workers.pop(device)

        self.send_command('worker.free', [str(worker_id)])

        if len(self.running_algorithms[algorithm][1]) == 0: # no more devices
            algorithm_id = self.running_algorithms[algorithm][0]
            self.running_algorithms.pop(algorithm)

            self.send_command('algorithm.remove', [str(algorithm_id)])

    def device_speeds(self, device):
        """Get current speeds for device that is running a single algorithm."""
        algorithm = [a for a in self.running_algorithms.keys()
                     if device in self.running_algorithms[a][1]][0]

        response = self.send_command('algorithm.list', [])

        algorithm_data = [ad for ad in response['algorithms']
                          if ad['name'] == algorithm][0]
        worker_id = self.running_workers[device]
        worker_data = [wd for wd in algorithm_data['workers']
                       if wd['worker_id'] == worker_id][0]
        return worker_data['speed']

    def algorithm_speeds(self, algorithm):
        """Get sum of speeds for all devices running algorithm."""
        response = self.send_command('algorithm.list', [])

        algorithm_data = [ad for ad in response['algorithms']
                          if ad['name'] == algorithm][0]
        worker_speeds = [wd['speed'] for wd in algorithm_data['workers']]
        return [sum([ws[0] for ws in worker_speeds]),
                sum([ws[1] for ws in worker_speeds])]

class ExcavatorAlgorithm(miner.Algorithm):
    def __init__(self, parent, algorithm):
        super(ExcavatorAlgorithm, self).__init__(parent,
                                                 name='excavator_%s' % algorithm,
                                                 algorithms=algorithm.split('_'))
        pass

    def attach_device(self, device):
        try:
            self.parent.server.dispatch_device('_'.join(self.algorithms), device)
        except (socket.error, socket.timeout):
            raise miner.MinerNotRunning('could not connect to excavator')

    def detach_device(self, device):
        try:
            self.parent.server.free_device(device)
        except (socket.error, socket.timeout):
            raise miner.MinerNotRunning('could not connect to excavator')

    def current_speeds(self):
        try:
            speeds = self.parent.server.algorithm_speeds('_'.join(self.algorithms))
        except (socket.error, socket.timeout):
            raise miner.MinerNotRunning('could not connect to excavator')
        else:
            if len(self.algorithms) == 2:
                return speeds
            else:
                return speeds[:1]

class Excavator(miner.Miner):
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

    def __init__(self, settings, stratums):
        super(Excavator, self).__init__(settings, stratums)

        self.server = None
        for algorithm in self.ALGORITHMS:
            runnable = ExcavatorAlgorithm(self, algorithm)
            self.algorithms.append(runnable)

    def load(self):
        auth = '%s.%s:x' % (self.settings['nicehash']['wallet'],
                            self.settings['nicehash']['workername'])
        self.server = ExcavatorServer(self.settings['excavator']['path'],
                                      self.settings['excavator']['port'],
                                      self.stratums,
                                      auth)
        self.server.start()

    def unload(self):
        self.server.stop()
        self.server = None

