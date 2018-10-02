import argparse
import logging
import os
import readline
import sched
import signal
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from ssl import SSLError
from threading import Event
from urllib.error import URLError

from nuxhash import nicehash, settings, utils
from nuxhash.devices.nvidia import enumerate_devices as nvidia_devices
from nuxhash.devices.nvidia import NvidiaDevice
from nuxhash.download.downloads import make_miners
from nuxhash.miners.excavator import Excavator
from nuxhash.miners.miner import MinerNotRunning
from nuxhash.switching.naive import NaiveSwitcher


BENCHMARK_SECS = 60


def main():
    argp = argparse.ArgumentParser(
        description='Sell GPU hash power on the NiceHash market.')
    argp_benchmark = argp.add_mutually_exclusive_group()
    argp_benchmark.add_argument(
        '--benchmark-all', action='store_true',
        help='benchmark all algorithms on all devices')
    argp_benchmark.add_argument(
        '--benchmark-missing', action='store_true',
        help='benchmark algorithm-device combinations not measured')
    argp.add_argument('--list-devices', action='store_true',
                      help='list all devices')
    argp.add_argument('-v', '--verbose', action='store_true',
                      help='print more information to the console log')
    argp.add_argument('--show-mining', action='store_true',
                      help='print output from mining processes, implies --verbose')
    argp.add_argument(
        '-c', '--configdir', nargs=1, default=[settings.DEFAULT_CONFIGDIR],
        help=('directory for configuration and benchmark files'
              + ' (default: ~/.config/nuxhash/)'))
    args = argp.parse_args()
    config_dir = Path(args.configdir[0])

    if args.show_mining:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARN
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=log_level)

    all_devices = nvidia_devices()
    nx_settings = settings.load_settings(config_dir)
    nx_benchmarks = settings.load_benchmarks(config_dir, all_devices)

    # If no wallet configured, do initial setup prompts.
    if nx_settings['nicehash']['wallet'] == '':
        wallet, workername, region = initial_setup()
        nx_settings['nicehash']['wallet'] = wallet
        nx_settings['nicehash']['workername'] = workername
        nx_settings['nicehash']['region'] = region

    # Download and initialize miners.
    downloadables = make_miners(config_dir)
    for d in downloadables:
        if not d.verify():
            logging.info('Downloading %s' % d.name)
            d.download()
    nx_miners = [Excavator(config_dir, nx_settings)]

    # Select code path(s), benchmarks and/or mining.
    if args.benchmark_all:
        nx_benchmarks = run_missing_benchmarks(
            nx_miners, nx_settings, all_devices, settinsg.EMPTY_BENCHMARKS)
    elif args.benchmark_missing:
        nx_benchmarks = run_missing_benchmarks(
            nx_miners, nx_settings, all_devices, nx_benchmarks)
    elif args.list_devices:
        list_devices(all_devices)
    else:
        nx_benchmarks = run_missing_benchmarks(
            nx_miners, nx_settings, all_devices, nx_benchmarks)
        session = MiningSession(nx_miners, nx_settings, nx_benchmarks, all_devices)
        session.run()

    settings.save_settings(config_dir, nx_settings)
    settings.save_benchmarks(config_dir, nx_benchmarks)


def initial_setup():
    print('nuxhashd initial setup')
    wallet = input('Wallet address: ')
    workername = input('Worker name: ')
    region = input('Region (eu/usa/hk/jp/in/br): ')
    print()
    return wallet, workername, region


def run_missing_benchmarks(miners, settings, devices, old_benchmarks):
    mbtc_per_hash, stratums = nicehash.simplemultialgo_info(settings)

    algorithms = sum([miner.algorithms for miner in miners], [])
    def algorithm(name): return next((algorithm for algorithm in algorithms
                                      if algorithm.name == name), None)

    # Temporarily suppress logging.
    logger = logging.getLogger()
    log_level = logger.getEffectiveLevel()
    logger.setLevel(logging.ERROR)
    for miner in miners:
        miner.stratums = stratums
        miner.load()

    done = sum([[(device, algorithm(algorithm_name))
                 for algorithm_name in benchmarks.keys()]
                for device, benchmarks in old_benchmarks.items()], [])
    all_targets = sum([[(device, algorithm) for algorithm in algorithms]
                       for device in devices], [])
    benchmarks = run_benchmarks(set(all_targets) - set(done))

    for miner in miners:
        miner.unload()
    logger.setLevel(log_level)

    for d in benchmarks:
        old_benchmarks[d].update(benchmarks[d])
    return old_benchmarks


def run_benchmarks(targets):
    if len(targets) == 0:
        return []

    benchmarks = settings.EMPTY_BENCHMARKS
    last_device = None
    for device, algorithm in sorted(targets, key=lambda t: str(t[0])):
        if device != last_device:
            if isinstance(device, NvidiaDevice):
                print('\nCUDA device: %s (%s)' % (device.name, device.uuid))
            last_device = device
        try:
            benchmarks[device][algorithm.name] = run_benchmark(device, algorithm)
        except MinerNotRunning:
            print('  %s: failed to complete benchmark     ' % algorithm.name)
            benchmarks[device][algorithm.name] = [0.0]*len(algorithm.algorithms)
        except KeyboardInterrupt:
            print('Benchmarking aborted (completed benchmarks saved).')
            break
    return benchmarks


def run_benchmark(device, algorithm):
    status_dot = [-1]
    def report_speeds(sample, secs_remaining):
        status_dot[0] = (status_dot[0] + 1) % 3
        status_line = ''.join(['.' if i == status_dot[0] else ' '
                               for i in range(3)])
        if secs_remaining < 0:
            print('  %s %s %s (warming up, %s)\r'
                  % (algorithm.name, status_line, utils.format_speeds(sample),
                     utils.format_time(-secs_remaining)), end='')
        else:
            print('  %s %s %s (sampling, %s)  \r'
                  % (algorithm.name, status_line, utils.format_speeds(sample),
                     utils.format_time(secs_remaining)), end='')
        sys.stdout.flush()
    speeds = utils.run_benchmark(algorithm, device,
                                 algorithm.warmup_secs, BENCHMARK_SECS,
                                 sample_callback=report_speeds)
    print('  %s: %s                      ' % (algorithm.name,
                                              utils.format_speeds(speeds)))
    return speeds


def list_devices(nx_devices):
    for d in sorted(nx_devices, key=str):
        if isinstance(d, NvidiaDevice):
            print('CUDA device: %s (%s)' % (d.name, d.uuid))


class MiningSession(object):

    PROFIT_PRIORITY = 1
    WATCH_PRIORITY = 2
    STOP_PRIORITY = 0
    WATCH_INTERVAL = 15

    def __init__(self, miners, settings, benchmarks, devices):
        self._miners = miners
        self._settings = settings
        self._benchmarks = benchmarks
        self._devices = devices
        self._last_payrates = (None, None)
        self._quit_signal = Event()
        self._scheduler = sched.scheduler(
                time.time, lambda t: self._quit_signal.wait(t))
        self._algorithms = []
        self._profit_switch = None

    def run(self):
        # Initialize miners.
        logging.info('Querying NiceHash for miner connection information...')
        payrates = stratums = None
        while payrates is None:
            try:
                payrates, stratums = nicehash.simplemultialgo_info(self._settings)
            except (socket.error, socket.timeout, SSLError, URLError):
                time.sleep(5)
            else:
                self._last_payrates = (payrates, datetime.now())
        for miner in self._miners:
            miner.stratums = stratums
        self._algorithms = sum([miner.algorithms for miner in self._miners], [])

        # Initialize profit-switching.
        self._profit_switch = NaiveSwitcher(self._settings)
        self._profit_switch.reset()

        # Attach the SIGINT signal for quitting.
        signal.signal(signal.SIGINT, lambda signum, frame: self.stop())

        self._scheduler.enter(0, MiningSession.PROFIT_PRIORITY, self._switch_algos)
        self._scheduler.enter(0, MiningSession.WATCH_PRIORITY, self._watch_algos)
        self._scheduler.run()

    def stop(self):
        self._scheduler.enter(0, MiningSession.STOP_PRIORITY, self._stop_mining)
        self._quit_signal.set()

    def _switch_algos(self):
        # Get profitability information from NiceHash.
        try:
            payrates, stratums = nicehash.simplemultialgo_info(self._settings)
        except (socket.error, socket.timeout, SSLError, URLError) as err:
            logging.warning('NiceHash stats: %s' % err)
        except nicehash.BadResponseError:
            logging.warning('NiceHash stats: Bad response')
        else:
            download_time = datetime.now()
            self._last_payrates = (payrates, download_time)

        # Calculate BTC/day rates.
        def revenue(device, algorithm):
            benchmarks = self._benchmarks[device]
            if algorithm.name in benchmarks:
                return sum([payrates[algorithm.algorithms[i]]
                            *benchmarks[algorithm.name][i]
                            for i in range(len(algorithm.algorithms))])
            else:
                return 0.0
        revenues = {device: {algorithm: revenue(device, algorithm)
                             for algorithm in self._algorithms}
                    for device in self._devices}

        # Get device -> algorithm assignments from profit switcher.
        self._assignments = self._profit_switch.decide(revenues, download_time)
        for this_algorithm in self._algorithms:
            this_devices = [device for device, algorithm
                            in self._assignments.items()
                            if algorithm == this_algorithm]
            this_algorithm.set_devices(this_devices)

        self._scheduler.enter(self._settings['switching']['interval'],
                              MiningSession.PROFIT_PRIORITY, self._switch_algos)

    def _watch_algos(self):
        running_algorithms = self._assignments.values()
        for algorithm in running_algorithms:
            if not algorithm.parent.is_running():
                logging.error('Detected %s crash, restarting miner'
                              % algorithm.name)
                algorithm.parent.reload()
        self._scheduler.enter(MiningSession.WATCH_INTERVAL,
                              MiningSession.WATCH_PRIORITY, self._watch_algos)

    def _stop_mining(self):
        logging.info('Cleaning up')
        for algorithm in self._algorithms:
            algorithm.set_devices([])
        for miner in self._miners:
            miner.unload()
        # Empty the scheduler.
        for job in self._scheduler.queue:
            self._scheduler.cancel(job)

