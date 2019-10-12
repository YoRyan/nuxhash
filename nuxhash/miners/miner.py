import logging
from functools import wraps


SHORT_WARMUP_SECS = 30
LONG_WARMUP_SECS = 300


class MinerException(Exception):
    pass


class MinerStartFailed(MinerException):
    pass


class MinerNotRunning(MinerException):
    pass


class MinerNotResponding(MinerException):
    pass


class Miner(object):

    def __init__(self, config_dir):
        # list of runnable algorithms supplied by this miner
        self.algorithms = []
        # configuration directory, for accessing downloaded miners
        self.config_dir = config_dir
        # current state of settings
        self._settings = None
        # dict of algorithm name -> nicehash stratum uri
        self._stratums = {}

    def load(self):
        """Initialize the mining program if necessary (e.g. start a server)."""
        pass

    def unload(self):
        """Clean up after load()."""
        pass

    def is_running(self):
        """Probe if the miner is operational."""
        pass

    @property
    def settings(self):
        return self._settings
    @settings.setter
    def settings(self, v):
        """Change settings during runtime."""
        self._settings = v

    @property
    def stratums(self):
        return self._stratums
    @stratums.setter
    def stratums(self, v):
        """Change pools during runtime."""
        self._stratums = v


class Algorithm(object):

    def __init__(self, parent, name, algorithms, warmup_secs=SHORT_WARMUP_SECS):
        self.parent = parent
        # human-readable name for the benchmark records
        self.name = name
        # list of algorithms run (for multialgorithms; same order as reported
        # speeds)
        self.algorithms = algorithms
        # warmup time for benchmarking purposes (either short or long)
        self.warmup_secs = warmup_secs
        # benchmarking mode
        self._benchmarking = False

    def __repr__(self):
        return f'<algorithm:{self.name} {self.algorithms}>'

    def accepts(self, device):
        """Check if this algorithm will run on this device."""
        return False

    def set_devices(self, devices):
        """Run this algorithm on the set of devices."""
        pass

    @property
    def benchmarking(self):
        return self._benchmarking
    @benchmarking.setter
    def benchmarking(self, v):
        self._benchmarking = v

    def current_speeds(self):
        pass


# Helper decorator for Algorithm methods.
def needs_miner_running(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.parent.is_running():
            self.parent.load()
        return method(self, *args, **kwargs)
    return wrapper


def log_output(process):
    while process.poll() is None:
        line = process.stdout.readline().decode('utf-8').rstrip()
        if line != '':
            # Reset terminal colors.
            logging.debug(line + '\033[0m')
    process.stdout.close()

