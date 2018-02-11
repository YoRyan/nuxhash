import logging

class MinerException(Exception):
    pass

class MinerStartFailed(MinerException):
    def __init__(self, failure):
        self.failure = failure

class MinerNotRunning(MinerException):
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

    def attach_device(self, device):
        """Run this algorithm on device."""
        pass

    def detach_device(self, device):
        """Stop running this algorithm on device."""
        pass

    def current_speeds(self):
        pass

def log_output(process):
    while process.poll() is None:
        line = process.stdout.readline().rstrip()
        if line != '':
            logging.debug(line + '\033[0m') # reset terminal colors

