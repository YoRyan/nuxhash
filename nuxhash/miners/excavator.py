import json
import os
import socket
import subprocess
import threading

from nuxhash.devices.nvidia import NvidiaDevice
from nuxhash.miners import miner
from nuxhash.utils import get_port


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
    'cryptonightV8',
    'lyra2z',
    'x16r'
    ]
NHMP_PORT = 3200


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

    def __init__(self, executable):
        self._executable = executable
        self.__subscription = self._process = None
        self._randport = get_port()
        self.__address = ('127.0.0.1', self._randport)
        self._extra_args = []
        # dict of algorithm name -> ESAlgorithm
        self._running_algorithms = {algorithm: ESAlgorithm(self, algorithm)
                                    for algorithm in ALGORITHMS}
        # dict of PCI bus id -> device id
        self._device_map = {}
        # dict of (algorithm name, Device instance) -> excavator worker id
        self._running_workers = {}

    @property
    def settings(self):
        return None
    @settings.setter
    def settings(self, v):
        self._subscription = (v['nicehash']['region'],
                              v['nicehash']['wallet'],
                              v['nicehash']['workername'])
        if v['excavator_miner']['listen'] == '':
            self._address = ('127.0.0.1', self._randport)
        else:
            ip, port = v['excavator_miner']['listen'].split(':')
            self._address = (ip, port)
        self._extra_args = v['excavator_miner']['args'].split()

    @property
    def _subscription(self):
        return self.__subscription
    @_subscription.setter
    def _subscription(self, v):
        if v != self.__address:
            self.__subscription = v
            if self.is_running():
                # As of API 0.1.8, this changes strata but leaves all workers running.
                self.send_command('unsubscribe', [])
                self._subscribe()

    @property
    def _address(self):
        return self.__address
    @_address.setter
    def _address(self, v):
        if v != self.__address:
            if self.is_running():
                self.stop()
                self.__address = v
                self.start()
            else:
                self.__address = v

    def start(self):
        """Launches excavator."""

        # Start process.
        ip, port = self._address
        self._process = subprocess.Popen(
            [self._executable, '-i', ip, '-p', str(port)] + self._extra_args,
            stdin=subprocess.DEVNULL, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

        # Send stdout to logger.
        log_thread = threading.Thread(
            target=miner.log_output, args=(self._process,))
        log_thread.start()

        # Wait for startup.
        while not self._test_connection():
            if self._process.poll() is not None:
                raise miner.MinerStartFailed

        self._read_devices()
        self._subscribe()

        # Add back previously running workers.
        self._running_algorithms = {algorithm: ESAlgorithm(self, algorithm)
                                    for algorithm in ALGORITHMS}
        for key, worker_id in self._running_workers.items():
            algorithm, device = key
            self.start_work(algorithm, device)

    def _subscribe(self):
        region, wallet, worker = self._subscription
        self.send_command('subscribe', [f'nhmp.{region}.nicehash.com:{NHMP_PORT}',
                                        f'{wallet}.{worker}:x'])

    def stop(self):
        """Stops excavator."""
        self.send_command('unsubscribe', [])
        self.send_command_only('quit', [])

        self._process.wait()

    def is_running(self):
        return self._process is not None and self._process.poll() is None

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
        with socket.create_connection(self._address, self.TIMEOUT) as s:
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

    def send_command_only(self, method, params):
        """Sends a command to excavator without reading the response.

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
        with socket.create_connection(self._address, self.TIMEOUT) as s:
            s.sendall(js_data.encode('ascii'))

    def _test_connection(self):
        try:
            self.send_command_only('info', [])
        except (socket.error, socket.timeout, ValueError):
            return False
        else:
            return True

    def _read_devices(self):
        response = self.send_command('device.list', [])
        bus_to_idx = {device_data['details']['bus_id']: device_data['device_id']
                      for device_data in response['devices']}
        self._device_map = bus_to_idx

    def start_work(self, algorithm, device, benchmarking=False):
        """Start running algorithm on device."""
        # Create associated algorithm(s).
        for multialgorithm in algorithm.split('_'):
            algorithm_instance = self._running_algorithms[multialgorithm]
            algorithm_instance.set_benchmarking(benchmarking)
            algorithm_instance.grab()

        # Create worker.
        device_id = self._device_map[device.pci_bus]
        if benchmarking:
            response = self.send_command(
                    'worker.add', [f'benchmark-{algorithm}', device_id])
        else:
            response = self.send_command('worker.add', [algorithm, device_id])
        self._running_workers[(algorithm, device)] = response['worker_id']

    def stop_work(self, algorithm, device):
        """Stop running algorithm on device."""
        # Destroy worker.
        worker_id = self._running_workers[(algorithm, device)]
        self.send_command('worker.free', [str(worker_id)])
        self._running_workers.pop((algorithm, device))

        # Destroy associated algorithm(s) if no longer used.
        for multialgorithm in algorithm.split('_'):
            self._running_algorithms[multialgorithm].release()

    def device_speeds(self, device):
        """Report the speeds of all algorithms running on device."""
        response = self.send_command('worker.list', [])
        # NOTE: assumes 1:1 mapping of workers to devices
        device_id = self._device_map[device.pci_bus]
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
            self._server.send_command(
                    'algorithm.add', [f'benchmark-{self._algorithm}'])
        else:
            self._server.send_command('algorithm.add', [self._algorithm])

    def _destroy(self):
        if self._benchmark:
            self._server.send_command(
                    'algorithm.remove', [f'benchmark-{self._algorithm}'])
        else:
            self._server.send_command('algorithm.remove', [self._algorithm])


class ExcavatorAlgorithm(miner.Algorithm):

    def __init__(self, parent, excavator_algorithm, **kwargs):
        algorithms = excavator_algorithm.lower().split('_')
        miner.Algorithm.__init__(
            self, parent, name=f'excavator_{excavator_algorithm}',
            algorithms=algorithms, **kwargs)
        self._excavator_algorithm = excavator_algorithm
        self._devices = []

    def accepts(self, device):
        # TODO: Proper support table instead of blindly accepting team green.
        return isinstance(device, NvidiaDevice)

    @miner.needs_miner_running
    def set_devices(self, devices):
        assert all(self.accepts(device) for device in devices)
        self._transition(set(self._devices), set(devices),
                         detach=self._stop_work,
                         attach=self._start_work)
        self._devices = devices

    @miner.Algorithm.benchmarking.setter
    def benchmarking(self, v):
        self._benchmarking = v
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

    def __init__(self, config_dir):
        miner.Miner.__init__(self, config_dir)
        for algorithm in ALGORITHMS:
            runnable = ExcavatorAlgorithm(self, algorithm,
                                          warmup_secs=miner.SHORT_WARMUP_SECS)
            self.algorithms.append(runnable)
        self.server = ExcavatorServer(config_dir/'excavator'/'excavator')

    def load(self):
        self.server.start()

    def unload(self):
        self.server.stop()

    def is_running(self):
        return self.server.is_running()

    @miner.Miner.settings.setter
    def settings(self, v):
        miner.Miner.settings.setter(v)
        self.server.settings = v

