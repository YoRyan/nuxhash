import argparse
import logging
import os
import readline
import sched
import signal
import socket
import sys
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from random import random
from threading import Event

from nuxhash import nicehash, settings, utils
from nuxhash.bitcoin import check_bc
from nuxhash.devices.nvidia import enumerate_devices as nvidia_devices
from nuxhash.devices.nvidia import NvidiaDevice
from nuxhash.download.downloads import make_miners
from nuxhash.miners import all_miners
from nuxhash.miners.miner import MinerNotRunning
from nuxhash.switching.naive import NaiveSwitcher
from nuxhash.version import __version__


BENCHMARK_SECS = 60
DONATE_PROB = 0.005
DONATE_ADDRESS = '3DJBpNcgP3Pihw45p9544PK6TbbYeMcnk7'


def main():
    sys.excepthook = excepthook

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
    argp.add_argument('--version', action='store_true',
                      help='show nuxhash version')
    args = argp.parse_args()
    config_dir = Path(args.configdir[0])

    if args.version:
        print(f'nuxhash daemon {__version__}')
        return

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
            logging.info(f'Downloading {d.name}')
            d.download()
    nx_miners = [miner(config_dir) for miner in all_miners]
    for miner in nx_miners:
        miner.settings = nx_settings

    # Select code path(s), benchmarks and/or mining.
    if args.benchmark_all:
        nx_benchmarks = run_missing_benchmarks(
            nx_miners, nx_settings, all_devices, settings.EMPTY_BENCHMARKS)
    elif args.benchmark_missing:
        nx_benchmarks = run_missing_benchmarks(
            nx_miners, nx_settings, all_devices, nx_benchmarks)
    elif args.list_devices:
        list_devices(all_devices)
    else:
        nx_benchmarks = run_missing_benchmarks(
            nx_miners, nx_settings, all_devices, nx_benchmarks)
        session = MiningSession(nx_miners, nx_settings, nx_benchmarks, all_devices)
        # Attach the SIGINT signal for quitting.
        # NOTE: If running in a shell, Ctrl-C will get sent to our subprocesses too,
        #       because we are the foreground process group. Miners will get killed
        #       before we have a chance to properly shut them down.
        signal.signal(signal.SIGINT, lambda signum, frame: session.stop())
        session.run()

    settings.save_settings(config_dir, nx_settings)
    settings.save_benchmarks(config_dir, nx_benchmarks)

    terminate()


def excepthook(type, value, traceback):
    sys.__excepthook__(type, value, traceback)
    logging.critical('Crash! Killing all miners.')
    os.killpg(os.getpgid(0), signal.SIGKILL) # (This also kills us.)


def terminate():
    os.killpg(os.getpgid(0), signal.SIGTERM)


def initial_setup():
    print('nuxhashd initial setup')

    wallet = ''
    while not check_bc(wallet):
        wallet = input('Wallet address: ')

    workername = input('Worker name: ')
    if workername == '':
        workername = 'nuxhash'

    region = ''
    while region not in ['eu', 'usa', 'hk', 'jp', 'in', 'br']:
        region = input('Region (eu/usa/hk/jp/in/br): ')

    print()
    return wallet, workername, region


def run_missing_benchmarks(miners, settings, devices, old_benchmarks):
    # Temporarily suppress logging.
    logger = logging.getLogger()
    log_level = logger.getEffectiveLevel()
    logger.setLevel(logging.ERROR)

    for miner in miners:
        miner.load()

    algorithms = sum([miner.algorithms for miner in miners], [])
    done = sum([[(device, next((algorithm for algorithm in algorithms
                                if algorithm.name == algorithm_name), None))
                 for algorithm_name in benchmarks.keys()]
                for device, benchmarks in old_benchmarks.items()], [])
    all_targets = sum([[(device, algorithm) for algorithm in algorithms
                        if algorithm.accepts(device)]
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
                print(f'\nCUDA device: {device.name} ({device.uuid})')
            last_device = device
        try:
            benchmarks[device][algorithm.name] = run_benchmark(device, algorithm)
        except MinerNotRunning:
            print(f'  {algorithm.name}: failed to complete benchmark     ')
            benchmarks[device][algorithm.name] = [0.0]*len(algorithm.algorithms)
        except KeyboardInterrupt:
            print('Benchmarking aborted (completed benchmarks saved).')
            for algorithm in set(algorithm for device, algorithm in targets):
                algorithm.set_devices([])
            break
    return benchmarks


def run_benchmark(device, algorithm):
    status_dot = [-1]
    def report_speeds(sample, secs_remaining):
        status_dot[0] = (status_dot[0] + 1) % 3
        status_line = ''.join(['.' if i == status_dot[0] else ' '
                               for i in range(3)])
        speeds = utils.format_speeds(sample)
        time = utils.format_time(abs(secs_remaining))
        if secs_remaining < 0:
            print(f'  {algorithm.name} {status_line} {speeds} (warming up, {time})'
                  + '\r', end='')
        else:
            print(f'  {algorithm.name} {status_line} {speeds} (sampling, {time}) '
                  + '\r', end='')
        sys.stdout.flush()

    speeds = utils.run_benchmark(
        algorithm, device, algorithm.warmup_secs, BENCHMARK_SECS,
        sample_callback=report_speeds)

    print(f'  {algorithm.name}: {utils.format_speeds(speeds)}' + ' '*22)
    return speeds


def list_devices(nx_devices):
    for d in sorted(nx_devices, key=str):
        if isinstance(d, NvidiaDevice):
            print(f'CUDA device: {d.name} ({d.uuid})')


class MiningSession(object):

    PROFIT_PRIORITY = 1
    STOP_PRIORITY = 0

    def __init__(self, miners, settings, benchmarks, devices):
        self._miners = miners
        self._settings = settings
        self._benchmarks = benchmarks
        self._devices = devices
        self._payrates = (None, None)
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
                payrates = nicehash.simplemultialgo_info(self._settings)
                stratums = nicehash.stratums(self._settings)
            except Exception as err:
                logging.warning(f'NiceHash stats: {err}, retrying in 5 seconds')
                time.sleep(5)
            else:
                self._payrates = (payrates, datetime.now())
        for miner in self._miners:
            miner.stratums = stratums
            miner.load()
        self._algorithms = sum([miner.algorithms for miner in self._miners], [])

        # Initialize profit-switching.
        self._profit_switch = NaiveSwitcher(self._settings)
        self._profit_switch.reset()

        self._scheduler.enter(0, MiningSession.PROFIT_PRIORITY, self._switch_algos)
        self._scheduler.run()

    def stop(self):
        self._scheduler.enter(0, MiningSession.STOP_PRIORITY, self._stop_mining)
        self._quit_signal.set()

    def _switch_algos(self):
        # Get profitability information from NiceHash.
        try:
            ret_payrates = nicehash.simplemultialgo_info(self._settings)
        except Exception as err:
            logging.warning(f'NiceHash stats: {err}')
        else:
            self._payrates = (ret_payrates, datetime.now())

        interval = self._settings['switching']['interval']
        payrates, payrates_time = self._payrates

        # Calculate BTC/day rates.
        def revenue(device, algorithm):
            benchmarks = self._benchmarks[device]
            if algorithm.name in benchmarks:
                return sum([payrates[sub_algo]*benchmarks[algorithm.name][i]
                            if sub_algo in payrates else 0.0
                            for i, sub_algo in enumerate(algorithm.algorithms)])
            else:
                return 0.0
        revenues = {device: {algorithm: revenue(device, algorithm)
                             for algorithm in self._algorithms}
                    for device in self._devices}

        # Get device -> algorithm assignments from profit switcher.
        self._assignments = self._profit_switch.decide(revenues, payrates_time)
        for this_algorithm in self._algorithms:
            this_devices = [device for device, algorithm
                            in self._assignments.items()
                            if algorithm == this_algorithm]
            this_algorithm.set_devices(this_devices)

        # Donation time.
        if not self._settings['donate']['optout'] and random() < DONATE_PROB:
            logging.warning('This interval will be donation time.')
            donate_settings = deepcopy(self._settings)
            donate_settings['nicehash']['wallet'] = DONATE_ADDRESS
            donate_settings['nicehash']['workername'] = 'nuxhash'
            for miner in self._miners:
                miner.settings = donate_settings
            self._scheduler.enter(interval, MiningSession.PROFIT_PRIORITY,
                                  self._reset_miners)

        self._scheduler.enter(interval, MiningSession.PROFIT_PRIORITY,
                              self._switch_algos)

    def _reset_miners(self):
        for miner in self._miners:
            miner.settings = self._settings

    def _stop_mining(self):
        logging.info('Quit signal received, terminating miners')
        # Empty the scheduler.
        for job in self._scheduler.queue:
            self._scheduler.cancel(job)

