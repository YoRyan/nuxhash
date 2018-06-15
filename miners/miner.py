import logging
from functools import wraps

class MinerException(Exception):
    pass

class MinerStartFailed(MinerException):
    def __init__(self, failure):
        self.failure = failure

class MinerNotRunning(MinerException):
    def __init__(self, failure):
        self.failure = failure

class MinerNotResponding(MinerException):
    def __init__(self, failure):
        self.failure = failure

class Miner(object):
    def __init__(self, settings, stratums):
        # list of runnable algorithms supplied by this miner
        self.algorithms = []
        # current state of settings
        self.settings = settings
        # dict of algorithm name -> nicehash stratum uri
        self.stratums = stratums
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
    def __init__(self, parent, name, algorithms):
        self.parent = parent
        # human-readable name for the benchmark records
        self.name = name
        # list of algorithms run (for multialgorithms; same order as reported
        # speeds)
        self.algorithms = algorithms

    def __repr__(self):
        return "<algorithm:%s %s>" % (self.name, self.algorithms)

    def set_devices(self, devices):
        """Run this algorithm on the set of devices."""
        pass

    def current_speeds(self):
        pass

    def restart_miner_if_needed(self):
        if not self.parent.is_running():
            self.parent.reload()

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
        line = process.stdout.readline().rstrip()
        if line != '':
            logging.debug(line + '\033[0m') # reset terminal colors

