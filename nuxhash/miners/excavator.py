import json
import os
import socket
import subprocess
import threading
from time import sleep

from nuxhash.miners import miner


ALGORITHMS = [
    'equihash',
    'pascal',
    'decred',
    #'sia',
    #'lbry',
    'blake2s',
    'daggerhashimoto',
    'lyra2rev2',
    'daggerhashimoto_decred',
    #'daggerhashimoto_sia',
    'daggerhashimoto_pascal',
    #'cryptonight',
    'keccak',
    'neoscrypt',
    #'nist5',
    'cryptonightV7',
    'lyra2z',
    'x16r'
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
        self.process.stdin.close()
        # Send stdout to logger.
        log_thread = threading.Thread(target=miner.log_output, args=(self.process,))
        log_thread.start()

        while not self._test_connection():
            if self.process.poll() is None:
                sleep(1)
            else:
                raise miner.MinerStartFailed

        # Connect to NiceHash.
        self.send_command('subscribe',
                          ['nhmp.%s.nicehash.com:3200' % self.region, self.auth])

        # Read excavator's device topology.
        self._read_devices()

        # Add back previously running workers.
        for key, worker_id in self.running_workers.items():
            algorithm, device = key
            self.start_work(algorithm, device)

    def restart(self):
        """Restarts excavator."""
        self.stop()
        self.start()

    def stop(self):
        """Stops excavator."""
        if self.process is None or self.process.poll() is not None:
            return

        # Disconnect from NiceHash.
        self.send_command('unsubscribe', [])

        # Send the quit command, but don't read a response.
        js_data = json.dumps({ 'id': 1, 'method': 'quit', 'params': [] }) + '\n'
        with socket.create_connection(self.address, self.TIMEOUT) as s:
            s.sendall(js_data.encode('ascii'))

        # Wait for the process to exit.
        self.process.wait()
        self.stdout = None

    def send_command(self, method, params):
        """Sends a command to excavator, returns the JSON-encoded response.

        method -- name of the command to execute
        params -- list of arguments for the command
        """
        # Send newline-terminated command.
        command = {
            'id': 1,
            'method': method,
            'params': [str(param) for param in params]
            }
        js_data = json.dumps(command).replace('\n', '\\n') + '\n'
        response = ''
        with socket.create_connection(self.address, self.TIMEOUT) as s:
            s.sendall(js_data.encode('ascii'))
            while True:
                chunk = s.recv(self.BUFFER_SIZE).decode()
                # Excavator responses are newline-terminated too.
                if '\n' in chunk:
                    response += chunk[:chunk.index('\n')]
                    break
                else:
                    response += chunk
        # Read the response.
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

    def start_work(self, algorithm, device, benchmarking=False):
        """Start running algorithm on device."""
        # Create associated algorithm(s).
        for multialgorithm in algorithm.split('_'):
            algorithm_instance = self.running_algorithms[multialgorithm]
            algorithm_instance.set_benchmarking(benchmarking)
            algorithm_instance.grab()

        # Create worker.
        device_id = self.device_map[device.pci_bus]
        response = self.send_command('worker.add', [algorithm, device_id])
        self.running_workers[(algorithm, device)] = response['worker_id']

    def stop_work(self, algorithm, device):
        """Stop running algorithm on device."""
        # Destroy worker.
        worker_id = self.running_workers[(algorithm, device)]
        self.send_command('worker.free', [str(worker_id)])
        self.running_workers.pop((algorithm, device))

        # Destroy associated algorithm(s) if no longer used.
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
        self._server = server
        self._algorithm = algorithm
        self._benchmark = False

    def set_benchmarking(self, v):
        self._benchmark = v

    def _create(self):
        if self._benchmark:
            self._server.send_command('algorithm.add',
                                      [self._algorithm, 'benchmark'])
        else:
            self._server.send_command('algorithm.add', [self._algorithm])

    def _destroy(self):
        self._server.send_command('algorithm.remove', [self._algorithm])


class ExcavatorAlgorithm(miner.Algorithm):

    def __init__(self, parent, excavator_algorithm, **kwargs):
        algorithms = excavator_algorithm.lower().split('_')
        miner.Algorithm.__init__(
            self, parent, name='excavator_%s' % excavator_algorithm,
            algorithms=algorithms, **kwargs)
        self._excavator_algorithm = excavator_algorithm
        self._devices = []

    @miner.needs_miner_running
    def set_devices(self, devices):
        self._transition(set(self._devices), set(devices),
                         detach=self._stop_work,
                         attach=self._start_work)
        self._devices = devices

    def set_benchmarking(self, v):
        self.benchmarking = v
        devices = self._devices
        if len(devices) > 0:
            # NOTE: May break on dual mining algos, but satisfactory for now.
            self.set_devices([])
            self.set_devices(devices)

    def _transition(self, old, new,
                    detach=lambda x: None, attach=lambda x: None):
        if old != new:
            for x in old - new:
                detach(x)
            for x in new - old:
                attach(x)

    def _start_work(self, device):
        try:
            self.parent.server.start_work(self._excavator_algorithm, device,
                                          benchmarking=self.benchmarking)
        except (socket.error, socket.timeout):
            raise miner.MinerNotRunning('could not connect to excavator')

    def _stop_work(self, device):
        try:
            self.parent.server.stop_work(self._excavator_algorithm, device)
        except (socket.error, socket.timeout):
            raise miner.MinerNotRunning('could not connect to excavator')

    @miner.needs_miner_running
    def current_speeds(self):
        try:
            workers = [self.parent.server.device_speeds(device)
                       for device in self._devices]
        except (socket.error, socket.timeout):
            raise miner.MinerNotRunning('could not connect to excavator')
        else:
            def total_speed(algorithm):
                return sum([worker[algorithm] for worker in workers
                            if algorithm in worker])
            return [total_speed(algorithm)
                    for algorithm in self._excavator_algorithm.split('_')]


class Excavator(miner.Miner):

    def __init__(self, config_dir, settings):
        miner.Miner.__init__(self, config_dir, settings)
        for algorithm in ALGORITHMS:
            runnable = ExcavatorAlgorithm(self, algorithm,
                                          warmup_secs=miner.SHORT_WARMUP_SECS)
            self.algorithms.append(runnable)
        executable = config_dir/'excavator'/'excavator'
        auth = '%s.%s:x' % (self.settings['nicehash']['wallet'],
                            self.settings['nicehash']['workername'])
        self.server = ExcavatorServer(executable,
                                      self.settings['excavator']['port'],
                                      self.settings['nicehash']['region'],
                                      auth)

    def load(self):
        self.server.start()

    def unload(self):
        self.server.stop()

    def reload(self):
        self.server.restart()

    def is_running(self):
        if (self.server.process is not None
            and self.server.process.poll() is None):
            return self.server._test_connection()
        else:
            return False

