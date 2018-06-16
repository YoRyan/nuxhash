#!/usr/bin/env python2

import benchmarks
import devices.nvidia
import download.downloads
import miners.excavator
import nicehash
import settings
import utils

from collections import defaultdict
from pathlib2 import Path
from ssl import SSLError
from threading import Event
from time import sleep
from urllib2 import HTTPError, URLError
import argparse
import logging
import os
import readline
import signal
import socket
import sys

DEFAULT_CONFIGDIR = os.path.expanduser('~/.config/nuxhash')
SETTINGS_FILENAME = 'settings.conf'
BENCHMARKS_FILENAME = 'benchmarks.json'

BENCHMARK_SECS = 90

def main():
    # parse commmand-line arguments
    argp = argparse.ArgumentParser(description='Sell GPU hash power on the NiceHash market.')
    argp_benchmark = argp.add_mutually_exclusive_group()
    argp_benchmark.add_argument('--benchmark-all', action='store_true',
                                help='benchmark all algorithms on all devices')
    argp_benchmark.add_argument('--benchmark-missing', action='store_true',
                                help='benchmark algorithm-device combinations not measured')
    argp.add_argument('--list-devices', action='store_true',
                      help='list all devices')
    argp.add_argument('-v', '--verbose', action='store_true',
                      help='print more information to the console log')
    argp.add_argument('--show-mining', action='store_true',
                      help='print output from mining processes, implies --verbose')
    argp.add_argument('-c', '--configdir', nargs=1, default=[DEFAULT_CONFIGDIR],
                      help='directory for configuration and benchmark files (default: ~/.config/nuxhash/)')
    args = argp.parse_args()
    config_dir = Path(args.configdir[0])

    # initiate logging
    if args.benchmark_all:
        log_level = logging.ERROR
    elif args.show_mining:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARN
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=log_level)

    # probe graphics cards
    nvidia_devices = devices.nvidia.enumerate_devices()
    all_devices = nvidia_devices

    # load from config directory
    nx_settings, nx_benchmarks = load_persistent_data(config_dir, all_devices)

    # if no wallet configured, do initial setup prompts
    if nx_settings['nicehash']['wallet'] == '':
        wallet, workername, region = initial_setup()
        nx_settings['nicehash']['wallet'] = wallet
        nx_settings['nicehash']['workername'] = workername
        nx_settings['nicehash']['region'] = region

    # download and initialize miners
    downloadables = download.downloads.make_miners(config_dir)
    for d in downloadables:
        if not d.verify():
            logging.info('Downloading %s' % d.name)
            d.download()
    nx_miners = [miners.excavator.Excavator(config_dir, nx_settings)]

    if args.benchmark_all:
        nx_benchmarks = run_missing_benchmarks(nx_miners, nx_settings, all_devices,
                                               defaultdict(lambda: {}))
    elif args.benchmark_missing:
        nx_benchmarks = run_missing_benchmarks(nx_miners, nx_settings, all_devices,
                                               nx_benchmarks)
    elif args.list_devices:
        list_devices(all_devices)
    else:
        do_mining(nx_miners, nx_settings, nx_benchmarks, all_devices)

    # save to config directory
    save_persistent_data(config_dir, nx_settings, nx_benchmarks)

def load_persistent_data(config_dir, nx_devices):
    try:
        settings_fd = open(str(config_dir/SETTINGS_FILENAME), 'r')
    except IOError as err:
        if err.errno != 2: # file not found
            raise
        nx_settings = settings.DEFAULT_SETTINGS
    else:
        nx_settings = settings.read_from_file(settings_fd)
        settings_fd.close()

    nx_benchmarks = {d: {} for d in nx_devices}
    try:
        benchmarks_fd = open(str(config_dir/BENCHMARKS_FILENAME), 'r')
    except IOError as err:
        if err.errno != 2:
            raise
    else:
        saved_benchmarks = benchmarks.read_from_file(benchmarks_fd, nx_devices)
        for d in saved_benchmarks:
            nx_benchmarks[d].update(saved_benchmarks[d])
        benchmarks_fd.close()

    return nx_settings, nx_benchmarks

def save_persistent_data(config_dir, nx_settings, nx_benchmarks):
    try:
        os.makedirs(str(config_dir))
    except OSError:
        if not os.path.isdir(str(config_dir)):
            raise

    with open(str(config_dir/SETTINGS_FILENAME), 'w') as settings_fd:
        settings.write_to_file(settings_fd, nx_settings)

    with open(str(config_dir/BENCHMARKS_FILENAME), 'w') as benchmarks_fd:
        benchmarks.write_to_file(benchmarks_fd, nx_benchmarks)

def initial_setup():
    print 'nuxhashd initial setup'

    wallet = raw_input('Wallet address: ')
    workername = raw_input('Worker name: ')
    region = raw_input('Region (eu/usa/hk/jp/in/br): ')

    print

    return wallet, workername, region

def run_missing_benchmarks(miners, settings, devices, old_benchmarks):
    stratums = nicehash.simplemultialgo_info(settings)[1]

    algorithms = sum([miner.algorithms for miner in miners], [])
    algorithm = lambda name: next((a for a in algorithms if a.name == name), None)
    for miner in miners:
        miner.stratums = stratums
        miner.load()

    done = sum([[(device, algorithm(algorithm_name)) for algorithm_name in benchmarks.keys()]
                for device, benchmarks in old_benchmarks.iteritems()], [])
    all_targets = sum([[(device, algorithm) for algorithm in algorithms]
                       for device in devices], [])
    benchmarks = run_benchmarks(set(all_targets) - set(done))

    for miner in miners:
        miner.unload()

    for d in benchmarks:
        old_benchmarks[d].update(benchmarks[d])
    return old_benchmarks

def run_benchmarks(targets):
    if len(targets) == 0:
        print 'Nothing to benchmark.'
        return []

    benchmarks = defaultdict(lambda: {})
    last_device = None
    for device, algorithm in sorted(targets, key=lambda t: str(t[0])):
        if device != last_device:
            if isinstance(device, devices.nvidia.NvidiaDevice):
                print '\nCUDA device %s: %s (%s)' % (device.cuda_index, device.name, device.uuid)
            last_device = device
        try:
            benchmarks[device][algorithm.name] = run_benchmark(device, algorithm)
        except KeyboardInterrupt:
            print 'Benchmarking aborted (completed benchmarks saved).'
            break
    return benchmarks

def run_benchmark(device, algorithm):
    status_dot = [-1]
    def report_speeds(sample, secs_remaining):
        status_dot[0] = (status_dot[0] + 1) % 3
        status_line = ''.join(['.' if i == status_dot[0] else ' ' for i in range(3)])
        if secs_remaining < 0:
            print ('  %s %s %s (warming up, %s)\r' %
                   (algorithm.name, status_line, utils.format_speeds(sample),
                    utils.format_time(-secs_remaining))),
        else:
            print ('  %s %s %s (sampling, %s)  \r' %
                   (algorithm.name, status_line, utils.format_speeds(sample),
                    utils.format_time(secs_remaining))),
        sys.stdout.flush()
    speeds = utils.run_benchmark(algorithm, device,
                                 algorithm.warmup_secs, BENCHMARK_SECS,
                                 sample_callback=report_speeds)
    print '  %s: %s                      ' % (algorithm.name,
                                              utils.format_speeds(speeds))
    return speeds

def list_devices(nx_devices):
    for d in sorted(nx_devices, key=str):
        if isinstance(d, devices.nvidia.NvidiaDevice):
            print 'CUDA device %s: %s (%s)' % (d.cuda_index, d.name, d.uuid)

def do_mining(nx_miners, nx_settings, nx_benchmarks, nx_devices):
    # get algorithm -> port information for stratum URLs
    logging.info('Querying NiceHash for miner connection information...')
    mbtc_per_hash = stratums = None
    while mbtc_per_hash is None:
        try:
            mbtc_per_hash, stratums = nicehash.simplemultialgo_info(nx_settings)
        except (HTTPError, URLError, socket.error, socket.timeout):
            pass

    # initialize miners
    for miner in nx_miners:
        miner.stratums = stratums
    algorithms = sum([miner.algorithms for miner in nx_miners], [])

    # quit signal
    quit = Event()
    signal.signal(signal.SIGINT, lambda signum, frame: quit.set())

    current_algorithm = {d: None for d in nx_devices}
    while not quit.is_set():
        # calculate most profitable algorithm for each device
        for device in nx_devices:
            def mbtc_per_day(algorithm):
                device_benchmarks = nx_benchmarks[device]
                if algorithm.name in device_benchmarks:
                    mbtc_per_day_multi = [device_benchmarks[algorithm.name][i]*
                                          mbtc_per_hash[algorithm.algorithms[i]]*(24*60*60)
                                          for i in range(len(algorithm.algorithms))]
                    return sum(mbtc_per_day_multi)
                else:
                    return 0

            current = current_algorithm[device]
            maximum = max(algorithms, key=lambda a: mbtc_per_day(a))

            if current is None:
                logging.info('Assigning %s to %s (%.3f mBTC/day)' %
                             (device, maximum.name, mbtc_per_day(maximum)))
                current_algorithm[device] = maximum
            elif current != maximum:
                current_revenue = mbtc_per_day(current)
                maximum_revenue = mbtc_per_day(maximum)
                min_factor = 1.0 + nx_settings['switching']['threshold']

                if current_revenue != 0 and maximum_revenue/current_revenue >= min_factor:
                    logging.info('Switching %s from %s to %s (%.3f -> %.3f mBTC/day)' %
                                 (device, current.name, maximum.name,
                                  current_revenue, maximum_revenue))
                    current_algorithm[device] = maximum

        # attach devices to respective algorithms atomically
        for algorithm in algorithms:
            my_devices = [d for d, a in current_algorithm.items() if a == algorithm]
            algorithm.set_devices(my_devices)

        # wait for specified interval
        quit.wait(nx_settings['switching']['interval'])

        # probe miner status
        for algorithm in current_algorithm.values():
            algorithm.restart_miner_if_needed()

        # query nicehash profitability data again
        try:
            mbtc_per_hash = nicehash.simplemultialgo_info(nx_settings)[0]
        except URLError as err:
            logging.warning('Failed to retrieve NiceHash profitability stats: %s' %
                            err.reason)
        except HTTPError as err:
            logging.warning('Failed to retrieve NiceHash profitability stats: %s %s' %
                            (err.code, err.reason))
        except (socket.timeout, SSLError):
            logging.warning('Failed to retrieve NiceHash profitability stats: timed out')
        except (ValueError, KeyError):
            logging.warning('Failed to retrieve NiceHash profitability stats: bad response')

    logging.info('Cleaning up')
    for miner in nx_miners:
        miner.unload()

if __name__ == '__main__':
    main()

