#!/usr/bin/env python2

from benchmarks import *
from settings import *
import miners
import nicehash

from time import sleep
import argparse
import os

DEFAULT_CONFIGDIR = os.path.expanduser('~/.config/nuxhash')
SETTINGS_FILENAME = 'settings.conf'
BENCHMARKS_FILENAME = 'benchmarks.json'

BENCHMARK_SECS = 30

def main():
    # parse commmand-line arguments
    argp = argparse.ArgumentParser(description='Sell GPU hash power on the NiceHash market.')
    argp.add_argument('-c', '--configdir', nargs=1, default=[DEFAULT_CONFIGDIR],
                      help='directory for configuration and benchmark files')
    argp.add_argument('--benchmark-all', action='store_true',
                      help='benchmark all algorithms on all devices')
    argp.add_argument('--list-devices', action='store_true',
                      help='list all devices')
    args = argp.parse_args()
    config_dir = args.configdir[0]

    # probe graphics cards
    devices = miners.enumerate_devices()

    # load from config directory
    settings, benchmarks = load_persistent_data(config_dir, devices)

    if args.benchmark_all:
        benchmarks = run_all_benchmarks(settings, devices)
    elif args.list_devices:
        list_devices(devices)
    else:
        do_mining(settings, benchmarks, devices)

    # save to config directory
    save_persistent_data(config_dir, settings, benchmarks)

def load_persistent_data(config_dir, devices):
    try:
        settings_fd = open('%s/%s' % (config_dir, SETTINGS_FILENAME), 'r')
    except IOError as err:
        if err.errno != 2: # file not found
            raise
        settings = DEFAULT_SETTINGS
    else:
        settings = read_settings_from_file(settings_fd)

    try:
        benchmarks_fd = open('%s/%s' % (config_dir, BENCHMARKS_FILENAME), 'r')
    except IOError as err:
        if err.errno != 2:
            raise
        benchmarks = dict([(d, {}) for d in devices])
    else:
        benchmarks = read_benchmarks_from_file(benchmarks_fd, devices)

    return settings, benchmarks

def save_persistent_data(config_dir, settings, benchmarks):
    try:
        os.makedirs(config_dir)
    except OSError:
        if not os.path.isdir(config_dir):
            raise

    write_settings_to_file(open('%s/%s' % (config_dir, SETTINGS_FILENAME), 'w'),
                           settings)
    write_benchmarks_to_file(open('%s/%s' % (config_dir, BENCHMARKS_FILENAME), 'w'),
                             benchmarks)

def run_all_benchmarks(settings, devices):
    print 'Contacting NiceHash ...'
    stratums = nicehash.simplemultialgo_info(settings)[1]
    print

    excavator = miners.Excavator(settings, stratums)
    excavator.load()
    algorithms = excavator.algorithms

    benchmarks = {}

    for d in sorted(devices, key=str):
        benchmarks[d] = {}

        if d.driver == 'nvidia':
            print 'CUDA device %d: %s' % (d.index, d.name)

        for a in algorithms:
            print '  %s ... ' % a.name,
            speeds = miners.run_benchmark(a, d, BENCHMARK_SECS)
            print format_speeds(speeds)
            benchmarks[d][a.name] = speeds
            break

    excavator.unload()

    return benchmarks

def format_speeds(speeds):
    def format_speed(x):
        if x >= 1e18:
            return '%.2f EH/s' % (x/1e18)
        elif x >= 1e15:
            return '%.2f PH/s' % (x/1e15)
        elif x >= 1e12:
            return '%.2f TH/s' % (x/1e12)
        elif x >= 1e9:
            return '%.2f GH/s' % (x/1e9)
        elif x >= 1e6:
            return '%.2f MH/s' % (x/1e6)
        elif x >= 1e3:
            return '%.2f kH/s' % (x/1e3)
        else:
            return '%.2f H/s' % x

    return ', '.join([format_speed(s) for s in speeds])

def list_devices(devices):
    for d in sorted(devices, key=str):
        if d.driver == 'nvidia':
            print 'CUDA device %d: %s' % (d.index, d.name)

def do_mining(settings, benchmarks, devices):
    print 'Contacting NiceHash ...'
    mbtc_per_hash, stratums = nicehash.simplemultialgo_info(settings)

    def mbtc_per_day(algorithm, device):
        device_benchmarks = benchmarks[device]
        if algorithm.name in device_benchmarks:
            mbtc_per_day_multi = [device_benchmarks[algorithm.name][i]*
                                  mbtc_per_hash[algorithm.algorithms[i]]
                                  for i in range(len(algorithm.algorithms))]
            return sum(mbtc_per_day_multi)
        else:
            return 0

    excavator = miners.Excavator(settings, stratums)
    excavator.load()
    algorithms = excavator.algorithms

    current_algorithm = dict([(d, None) for d in devices])
    while True:
        for device in devices:
            current = current_algorithm[device]
            maximum = max(algorithms, key=lambda a: mbtc_per_day(a, device))

            if current is not None and current != maximum:
                current_revenue = mbtc_per_day(current)
                maximum_revenue = mbtc_per_day(maximum)
                min_factor = 1.0 + settings['switching']['threshold']

                if current_revenue != 0 and maximum_revenue/current_revenue >= min_factor:
                    current.detach_device(device)
                    maximum.attach_device(device)
                    current_algorithm[device] = maximum
            else:
                maximum.attach_device(device)
                current_algorithm[device] = maximum
        # wait, then query nicehash profitability data again
        sleep(settings['switching']['interval'])
        mbtc_per_hash = nicehash.simplemultialgo_info(settings)[0]

if __name__ == '__main__':
    main()

