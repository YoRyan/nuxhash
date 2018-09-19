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
    #'cryptonight',
    'keccak',
    'neoscrypt',
    #'nist5',
    'cryptonightV7',
    'lyra2z'
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
        self.process = None
        # dict of algorithm name -> ESAlgorithm
        self.running_algorithms = {algorithm: ESAlgorithm(self, algorithm)
                                   for algorithm in ALGORITHMS}
        # dict of PCI bus id -> device id
        self.device_map = {}
        # dict of (algorithm name, Device instance) -> excavator worker id
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

        # read device topology
        self._read_devices()

    def restart(self):
        # kill old process (if any)
        if self.process is not None:
            try:
                self.process.terminate()
            except OSError, e:
                if e.errno != os.errno.ESRCH:
                    raise
            self.process.wait()

        # reset internal data structures
        old_workers = self.running_workers
        self.running_workers = {}
        self.running_algorithms = {algorithm: ESAlgorithm(self, algorithm)
                                   for algorithm in ALGORITHMS}

        # start excavator again
        self.start()

        # add back previous workers
        for key, worker_id in old_workers.iteritems():
            algorithm, device = key
            self.start_work(algorithm, device)

    def stop(self):
        """Stops excavator."""
        if self.process is None or self.process.poll() is not None:
            return

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
        except (socket.error, socket.timeout, ValueError):
            return False
        else:
            return True

    def _read_devices(self):
        response = self.send_command('device.list', [])
        bus_to_idx = {device_data['details']['bus_id']: device_data['device_id']
                      for device_data in response['devices']}
        self.device_map = bus_to_idx

    def start_work(self, algorithm, device):
        """Start running algorithm on device."""
        # create associated algorithm(s)
        for multialgorithm in algorithm.split('_'):
            self.running_algorithms[multialgorithm].grab()

        # create worker
        device_id = self.device_map[device.pci_bus]
        response = self.send_command('worker.add', [algorithm, device_id])
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

        # NOTE: assumes 1:1 mapping of workers to devices
        device_id = self.device_map[device.pci_bus]
        data = next(worker for worker in response['workers']
                    if worker['device_id'] == device_id)
        return {algorithm['name']: algorithm['speed']
                for algorithm in data['algorithms']}

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
    def __init__(self, parent, excavator_algorithm, **kwargs):
        algorithms = excavator_algorithm.lower().split('_')
        super(ExcavatorAlgorithm, self).__init__(parent,
                                                 name='excavator_%s' % excavator_algorithm,
                                                 algorithms=algorithms,
                                                 **kwargs)
        self.excavator_algorithm = excavator_algorithm
        self.devices = set()

    @miner.needs_miner_running
    def set_devices(self, devices):
        old = self.devices
        new = set(devices)
        if old != new:
            for device in old - new:
                self._detach_device(device)
            for device in new - old:
                self._attach_device(device)

    def _attach_device(self, device):
        try:
            self.parent.server.start_work(self.excavator_algorithm, device)
        except (socket.error, socket.timeout):
            raise miner.MinerNotRunning('could not connect to excavator')
        else:
            self.devices.add(device)

    def _detach_device(self, device):
        try:
            self.parent.server.stop_work(self.excavator_algorithm, device)
        except (socket.error, socket.timeout):
            raise miner.MinerNotRunning('could not connect to excavator')
        else:
            self.devices.remove(device)

    @miner.needs_miner_running
    def current_speeds(self):
        try:
            workers = [self.parent.server.device_speeds(device)
                       for device in self.devices]
        except (socket.error, socket.timeout):
            raise miner.MinerNotRunning('could not connect to excavator')
        else:
            total_speed = lambda algorithm: sum([w[algorithm] for w in workers
                                                 if algorithm in w])
            return [total_speed(algorithm)
                    for algorithm in self.excavator_algorithm.split('_')]

class Excavator(miner.Miner):
    def __init__(self, config_dir, settings):
        super(Excavator, self).__init__(config_dir, settings)

        self.server = None
        for algorithm in ALGORITHMS:
            if 'daggerhashimoto' in algorithm:
                warmup_secs = miner.LONG_WARMUP_SECS
            else:
                warmup_secs = miner.SHORT_WARMUP_SECS
            runnable = ExcavatorAlgorithm(self, algorithm, warmup_secs=warmup_secs)
            self.algorithms.append(runnable)

        auth = '%s.%s:x' % (self.settings['nicehash']['wallet'],
                            self.settings['nicehash']['workername'])
        executable = str(config_dir/'excavator'/'excavator')
        self.server = ExcavatorServer(executable,
                                      self.settings['excavator']['port'],
                                      self.settings['nicehash']['region'],
                                      auth)

    def load(self):
        self.server.start()

    def unload(self):
        self.server.stop()
        self.server = None

    def reload(self):
        self.server.restart()

    def is_running(self):
        if self.server.process is not None and self.server.process.poll() is None:
            return self.server._test_connection()
        else:
            return False

