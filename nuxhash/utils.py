from time import sleep

from nuxhash.miners.miner import MinerNotRunning

def format_speed(s):
    """Turn a high hashes/second value into a human-readable string."""
    if s >= 1e18:
        return '%6.2f EH/s' % (s/1e18)
    elif s >= 1e15:
        return '%6.2f PH/s' % (s/1e15)
    elif s >= 1e12:
        return '%6.2f TH/s' % (s/1e12)
    elif s >= 1e9:
        return '%6.2f GH/s' % (s/1e9)
    elif s >= 1e6:
        return '%6.2f MH/s' % (s/1e6)
    elif s >= 1e3:
        return '%6.2f kH/s' % (s/1e3)
    else:
        return '%6.2f  H/s' % s

def format_speeds(speeds):
    """Turn a list of hashes/second values into a human-readable string."""
    return ', '.join([format_speed(s) for s in speeds])

def format_time(seconds):
    """Turn a high seconds value into a human-readable string."""
    m = seconds // 60
    s = seconds % 60
    if m == 1 and s == 0:
        return '60 s'
    elif m == 0:
        return '%2d s' % s
    else:
        return '%1d:%02d' % (m, s)

def run_benchmark(algorithm, device, warmup_duration, sample_duration,
                  sample_callback=lambda sample, secs_remaining: None):
    """Run algorithm on device for duration seconds and report the average speed.

    Keyword arguments:
    sample_callback -- called whenever a sample is taken;
                       secs_remaining < 0 indicates warmup period
    """
    SAMPLE_INTERVAL = 1

    algorithm.benchmark_devices([device])
    # warmup period
    for i in range(warmup_duration//SAMPLE_INTERVAL):
        if not algorithm.parent.is_running():
            raise MinerNotRunning
        sample = algorithm.current_speeds()
        sample_callback(sample, i*SAMPLE_INTERVAL - warmup_duration)
        sleep(SAMPLE_INTERVAL)
    # actual sampling
    samples = []
    for i in range(sample_duration//SAMPLE_INTERVAL):
        if not algorithm.parent.is_running():
            raise MinerNotRunning
        sample = algorithm.current_speeds()
        samples.append(sample)
        sample_callback(sample, sample_duration - i*SAMPLE_INTERVAL)
        sleep(SAMPLE_INTERVAL)
    algorithm.benchmark_devices([])

    # return average of all samples
    def sum_list_elements(lists):
        sums = lists[0]
        for l in lists[1:]:
            for i, e in enumerate(l):
                sums[i] += e
        return sums
    return map(lambda total: total/len(samples), sum_list_elements(samples))

