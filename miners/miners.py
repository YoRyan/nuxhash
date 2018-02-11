from time import sleep
import logging

BENCHMARK_WARMUP = 240
BENCHMARK_SAMPLE_INTERVAL = 1

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
    def __init__(self, miner, name, algorithms):
        self.miner = miner
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

def run_benchmark(algorithm, device, duration,
                  sample_callback=lambda sample, secs_remaining: None):
    """Run algorithm on device for duration seconds and report the average speed.

    Keyword arguments:
    sample_callback -- called whenever a sample is taken;
                       (secs_remaining == -1) => still warming up
    """
    algorithm.attach_device(device)
    # warmup period
    for i in range(BENCHMARK_WARMUP/BENCHMARK_SAMPLE_INTERVAL):
        sample = algorithm.current_speeds()
        sample_callback(sample, -1)
        sleep(BENCHMARK_SAMPLE_INTERVAL)
    # actual sampling
    samples = []
    for i in range(duration/BENCHMARK_SAMPLE_INTERVAL):
        sample = algorithm.current_speeds()
        samples.append(sample)
        sample_callback(sample, duration - i*BENCHMARK_SAMPLE_INTERVAL)
        sleep(BENCHMARK_SAMPLE_INTERVAL)
    algorithm.detach_device(device)

    # return average of all samples
    def sum_list_elements(lists):
        sums = lists[0]
        for l in lists[1:]:
            for i, e in enumerate(l):
                sums[i] += e
        return sums
    return map(lambda total: total/len(samples), sum_list_elements(samples))

def log_output(process):
    while process.poll() is None:
        line = process.stdout.readline().strip()
        if line != '':
            logging.debug(line + '\033[0m') # reset terminal colors

