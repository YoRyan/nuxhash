import socket
from contextlib import contextmanager
from threading import Event
from time import sleep


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


def format_balance(v, unit):
    """Turn a Bitcoin balance into a string with requested unit."""
    if unit == 'BTC':
        return '%.8f BTC' % v
    elif unit == 'mBTC':
        return '%.5f mBTC' % (v*1e3)


def run_benchmark(
        algorithm, device, warmup_duration, sample_duration,
        sample_callback=lambda sample, secs_remaining: None, abort_signal=Event()):
    """Run algorithm on device for duration seconds and report the average speed.

    Keyword arguments:
    sample_callback -- called whenever a sample is taken;
                       secs_remaining < 0 indicates warmup period
    abort_signal -- signal to abort the benchmarking early;
                    will return average of already taken samples
    """
    SAMPLE_INTERVAL = 1
    BLANK = [0.0]*len(algorithm.algorithms)
    assert algorithm.accepts(device)

    @contextmanager
    def acquire(algorithm):
        algorithm.benchmarking = True
        algorithm.set_devices([device])
        yield algorithm
        algorithm.set_devices([])
        algorithm.benchmarking = False
    with acquire(algorithm) as running_algo:
        # Run warmup period.
        i = 0
        while i < warmup_duration//SAMPLE_INTERVAL and not abort_signal.is_set():
            if not running_algo.parent.is_running():
                return BLANK
            sample = running_algo.current_speeds()
            sample_callback(sample, i*SAMPLE_INTERVAL - warmup_duration)
            abort_signal.wait(SAMPLE_INTERVAL)
            i += 1

        # Perform actual sampling.
        samples = []
        i = 0
        while i < sample_duration//SAMPLE_INTERVAL and not abort_signal.is_set():
            if not running_algo.parent.is_running():
                return BLANK
            sample = running_algo.current_speeds()
            samples.append(sample)
            sample_callback(sample, sample_duration - i*SAMPLE_INTERVAL)
            abort_signal.wait(SAMPLE_INTERVAL)
            i += 1

    # Return average of all samples.
    def sum_list_elements(lists):
        sums = lists[0]
        for l in lists[1:]:
            for i, e in enumerate(l):
                sums[i] += e
        return sums
    return (list(map(lambda total: total/len(samples), sum_list_elements(samples)))
            if len(samples) > 0 else BLANK)

def get_port():
    with socket.socket() as s:
        s.bind(('', 0))
        # This is a race condition, but probably a minor one.
        return s.getsockname()[1]

