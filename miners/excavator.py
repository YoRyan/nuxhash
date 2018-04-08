import miner

import json
import os
import socket
import subprocess
import threading
from time import sleep

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
    'nist5',
    'cryptonightV7'
    ]

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

    def __init__(self, executable, port, region, auth):
        self.executable = executable
        self.address = ('127.0.0.1', port)
        self.region = region
        self.auth = auth
        # dict of algorithm name -> ESAlgorithm
        self.running_algorithms = dict([(algorithm, ESAlgorithm(self, algorithm))
                                        for algorithm in ALGORITHMS])
        # dict of (algorithm name, device id) -> excavator worker id
        self.running_workers = {}

    def start(self):
        """Launches excavator."""
        self.process = subprocess.Popen([self.executable,
                                         '-i', self.address[0],
                                         '-p', str(self.address[1])],
                                        stdin=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        stdout=subprocess.PIPE,
                                        preexec_fn=os.setpgrp) # don't forward signals
        # send stdout to logger
        log_thread = threading.Thread(target=miner.log_output, args=(self.process,))
        log_thread.start()

        while not self._test_connection():
            if self.process.poll() is None:
                sleep(1)
            else:
                raise miner.MinerStartFailed

        # connect to NiceHash
        self.send_command('subscribe', ['nhmp.%s.nicehash.com:3200' % self.region,
                                        self.auth])

    def stop(self):
        """Stops excavator."""
        # stop all running workers
        for (algorithm, device) in self.running_workers.keys():
            self.stop_work(algorithm, device)

        # disconnect from NiceHash
        self.send_command('unsubscribe', [])

        # send the quit command, but don't read a response
        s = socket.create_connection(self.address, self.TIMEOUT)
        s.sendall(json.dumps({ 'id': 1, 'method': 'quit', 'params': [] }) + '\n')

        # wait for the process to exit
        self.process.wait()
        self.stdout = None

    def send_command(self, method, params):
        """Sends a command to excavator, returns the JSON-encoded response.

        method -- name of the command to execute
        params -- list of arguments for the command
        """

        # send newline-terminated command
        command = {
            'id': 1,
            'method': method,
            'params': [str(param) for param in params]
            }
        s = socket.create_connection(self.address, self.TIMEOUT)
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

        # read response
        response_data = json.loads(response)
        if response_data['error'] is None:
            return response_data
        else:
            raise ExcavatorAPIError(response_data)

    def _test_connection(self):
        try:
            self.send_command('info', [])
        except (socket.error, socket.timeout):
            return False
        else:
            return True

    def start_work(self, algorithm, device):
        """Start running algorithm on device."""
        # create associated algorithm(s)
        for multialgorithm in algorithm.split('_'):
            self.running_algorithms[multialgorithm].grab()

        # create worker
        response = self.send_command('worker.add', [algorithm, str(device.index)])
        self.running_workers[(algorithm, device)] = response['worker_id']

    def stop_work(self, algorithm, device):
        """Stop running algorithm on device."""
        # destroy worker
        worker_id = self.running_workers[(algorithm, device)]
        self.send_command('worker.free', [str(worker_id)])
        self.running_workers.pop((algorithm, device))

        # destroy associated algorithm(s) if no longer used
        for multialgorithm in algorithm.split('_'):
            self.running_algorithms[multialgorithm].release()

    def device_speeds(self, device):
        """Report the speeds of all algorithms running on device."""
        response = self.send_command('worker.list', [])

        data = [worker for worker in response['workers']
                if worker['device_id'] == device.index][0]
        return dict([(algorithm['name'], algorithm['speed'])
                     for algorithm in data['algorithms']])

class ESResource(object):
    def __init__(self):
        self.hodlers = 0

    def grab(self):
        if self.hodlers <= 0:
            self._create()
        self.hodlers += 1

    def release(self):
        self.hodlers -= 1
        if self.hodlers <= 0:
            self.hodlers = 0
            self._destroy()

    def _create(self):
        pass

    def _destroy(self):
        pass

class ESAlgorithm(ESResource):
    def __init__(self, server, algorithm):
        super(ESAlgorithm, self).__init__()
        self.server = server
        self.params = algorithm.split('_')

    def _create(self):
        self.server.send_command('algorithm.add', self.params)

    def _destroy(self):
        self.server.send_command('algorithm.remove', self.params)

class ExcavatorAlgorithm(miner.Algorithm):
    def __init__(self, parent, algorithm):
        algorithms = [a.lower() for a in algorithm.split('_')]
        super(ExcavatorAlgorithm, self).__init__(parent,
                                                 name='excavator_%s' % algorithm,
                                                 algorithms=algorithms)
        self.devices = set()

    def set_devices(self, devices):
        old = self.devices
        new = set(devices)
        if old != new:
            for device in old - new:
                self._detach_device(device)
            for device in new - old:
                self._attach_device(device)
            self.devices = new

    def _attach_device(self, device):
        try:
            self.parent.server.start_work('_'.join(self.algorithms), device)
        except (socket.error, socket.timeout):
            raise miner.MinerNotRunning('could not connect to excavator')
        else:
            self.devices.add(device)

    def _detach_device(self, device):
        try:
            self.parent.server.stop_work('_'.join(self.algorithms), device)
        except (socket.error, socket.timeout):
            raise miner.MinerNotRunning('could not connect to excavator')
        else:
            self.devices.remove(device)

    def current_speeds(self):
        try:
            stats = [self.parent.server.device_speeds(device)
                     for device in self.devices]
        except (socket.error, socket.timeout):
            raise miner.MinerNotRunning('could not connect to excavator')
        else:
            total_speed = lambda algorithm: sum([dd[algorithm] for dd in stats])
            return [total_speed(algorithm) for algorithm in self.algorithms]

class Excavator(miner.Miner):
    def __init__(self, settings, stratums):
        super(Excavator, self).__init__(settings, stratums)

        self.server = None
        for algorithm in ALGORITHMS:
            runnable = ExcavatorAlgorithm(self, algorithm)
            self.algorithms.append(runnable)

    def load(self):
        auth = '%s.%s:x' % (self.settings['nicehash']['wallet'],
                            self.settings['nicehash']['workername'])
        self.server = ExcavatorServer(self.settings['excavator']['path'],
                                      self.settings['excavator']['port'],
                                      self.settings['nicehash']['region'],
                                      auth)
        self.server.start()

    def unload(self):
        self.server.stop()
        self.server = None

