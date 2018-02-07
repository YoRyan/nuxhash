from time import sleep

BENCHMARK_WARMUP = 60
BENCHMARK_SAMPLE_INTERVAL = 5

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
    def __init__(self, name, algorithms):
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

def run_benchmark(algorithm, device, duration):
    """Run algorithm on device for duration seconds and report the average speed."""
    samples = []
    algorithm.attach_device(device)
    sleep(BENCHMARK_WARMUP)
    for i in range(duration/BENCHMARK_SAMPLE_INTERVAL):
        samples.append(algorithm.current_speeds())
        sleep(BENCHMARK_SAMPLE_INTERVAL)
    algorithm.detach_device(device)

    def sum_list_elements(lists):
        head_list = lists[0]
        if len(lists) == 1:
            return head_list
        else:
            return [head_list[i] + sum_list_elements(lists[1:])[i] for
                    i in range(len(head_list))]
    return map(lambda total: total/len(samples), sum_list_elements(samples))

