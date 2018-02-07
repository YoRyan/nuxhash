from time import sleep

class Miner(object):
    def __init__(self, settings, devices):
        # list of runnable algorithms supplied by this miner indexed by device
        self.algorithms = {}
        for device in devices:
            self.algorithms[device] = []
    def load(self):
        """Initialize the mining program if necessary (e.g. start a server)."""
        pass
    def unload(self):
        """Clean up after load()."""
        pass

class Algorithm(object):
    BENCHMARK_WARMUP = 60
    BENCHMARK_SAMPLE_INTERVAL = 5

    def __init__(self, name, algorithms, device):
        # human-readable name for the benchmark records
        self.name = name
        # list of algorithms run (for multialgorithms; same order as reported speeds)
        self.algorithms = algorithms
        # reference to device
        self.device = device

    def __repr__(self):
        return "<algorithm:%s %s device:%s>" % (self.name, self.algorithms, self.device)

    def run(self, stratums, auth):
        """Run this algorithm."""
        pass

    def stop(self):
        """Stop running this algorithm."""
        pass

    def benchmark(self, stratums, auth, duration):
        """Run this algorithm for duration seconds and report the average speed."""
        samples = []
        self.run(stratums, auth)
        sleep(self.BENCHMARK_WARMUP)
        for i in range(duration/self.BENCHMARK_SAMPLE_INTERVAL):
            samples.append(self.current_speeds())
            sleep(self.BENCHMARK_SAMPLE_INTERVAL)
        self.stop()

        def sum_list_elements(lists):
            head_list = lists[0]
            if len(lists) == 1:
                return head_list
            else:
                return [head_list[i] + sum_list_elements(lists[1:])[i] for
                        i in range(len(head_list))]
        return map(lambda total: total/len(samples), sum_list_elements(samples))

    def current_speeds(self):
        pass

