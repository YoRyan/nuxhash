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
    def __init__(self, config_dir, settings):
        # list of runnable algorithms supplied by this miner
        self.algorithms = []
        # configuration directory, for accessing downloaded miners
        self.config_dir = config_dir
        # current state of settings
        self.settings = settings
        # dict of algorithm name -> nicehash stratum uri; set later
        self.stratums = {}
    def load(self):
        """Initialize the mining program if necessary (e.g. start a server)."""
        pass
    def unload(self):
        """Clean up after load()."""
        pass
    def reload(self):
        """Restart the miner in the event of an unusual condition (crash)."""
        pass
    def is_running(self):
        """Probe if the miner is operational."""
        pass

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
        self.benchmarking = False

    def __repr__(self):
        return "<algorithm:%s %s>" % (self.name, self.algorithms)

    def set_devices(self, devices):
        """Run this algorithm on the set of devices."""
        pass

    def set_benchmarking(self, v):
        """Engage/disengage benchmarking mode."""
        self.benchmarking = v

    def current_speeds(self):
        pass

# helper decorator for Algorithm methods
def needs_miner_running(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.parent.is_running():
            self.parent.reload()
        return method(self, *args, **kwargs)
    return wrapper

def log_output(process):
    while process.poll() is None:
        line = str(process.stdout.readline()).rstrip()
        if line != '':
            logging.debug(line + '\033[0m') # reset terminal colors
    process.stdout.close()

