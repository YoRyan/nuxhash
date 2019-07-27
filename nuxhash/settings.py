import configparser
import errno
import json
import os
from collections import defaultdict
from pathlib import Path


DEFAULT_CONFIGDIR = Path(os.path.expanduser('~/.config/nuxhash'))
SETTINGS_FILENAME = 'settings.conf'
BENCHMARKS_FILENAME = 'benchmarks.json'
DEFAULT_SETTINGS = {
    'nicehash': {
        'wallet': '',
        'workername': 'nuxhash',
        'region': 'usa',
        },
    'switching': {
        'interval': 60,
        'threshold': 0.1
        },
    'gui': {
        'units': 'mBTC'
        },
    'donate': {
        'optout': False
        },
    'excavator_miner': {
        'listen': '',
        'args': ''
        }
    }
EMPTY_BENCHMARKS = defaultdict(lambda: {})


def read_settings_from_file(fd):
    parser = configparser.ConfigParser()
    parser.read_file(fd)
    def get_option(parser_method, section, option):
        try:
            return parser_method(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return DEFAULT_SETTINGS[section][option]
    return {
        'nicehash': {
            'wallet': get_option(parser.get, 'nicehash', 'wallet'),
            'workername': get_option(parser.get, 'nicehash', 'workername'),
            'region': get_option(parser.get, 'nicehash', 'region')
            },
        'switching': {
            'interval': get_option(parser.getint, 'switching', 'interval'),
            'threshold': get_option(parser.getfloat, 'switching', 'threshold')
            },
        'gui': {
            'units': get_option(parser.get, 'gui', 'units')
            },
        'donate': {
            'optout': get_option(parser.getboolean, 'donate', 'optout')
            },
        'excavator_miner': {
            'listen': get_option(parser.get, 'excavator_miner', 'listen'),
            'args': get_option(parser.get, 'excavator_miner', 'args')
            }
        }


def write_settings_to_file(fd, settings):
    parser = configparser.ConfigParser()
    for section in settings:
        parser.add_section(section)
        for option in settings[section]:
            value = settings[section][option]
            parser.set(section, option, str(value))
    parser.write(fd)


def read_benchmarks_from_file(fd, devices):
    benchmarks = defaultdict(lambda: {})
    js = json.load(fd)
    for js_device in js:
        device = next((device for device in devices
                       if str(device) == js_device), None)
        if device is None:
            continue
        js_speeds = js[js_device]
        for algorithm_name in js_speeds:
            if isinstance(js_speeds[algorithm_name], list):
                benchmarks[device][algorithm_name] = js_speeds[algorithm_name]
            else:
                benchmarks[device][algorithm_name] = [js_speeds[algorithm_name]]
    return benchmarks


def write_benchmarks_to_file(fd, benchmarks):
    to_file = {}
    for device in benchmarks:
        to_file[str(device)] = {}
        speeds = benchmarks[device]
        for algorithm_name in speeds:
            if len(speeds[algorithm_name]) == 1:
                to_file[str(device)][algorithm_name] = speeds[algorithm_name][0]
            else:
                to_file[str(device)][algorithm_name] = speeds[algorithm_name]
    json.dump(to_file, fd, indent=4)


def load_settings(config_dir):
    try:
        with open(config_dir/SETTINGS_FILENAME, 'r') as settings_fd:
            settings = read_settings_from_file(settings_fd)
    except IOError as err:
        if err.errno != errno.ENOENT:
            raise
        return DEFAULT_SETTINGS
    else:
        return settings


def load_benchmarks(config_dir, devices):
    try:
        with open(config_dir/BENCHMARKS_FILENAME, 'r') as benchmarks_fd:
            benchmarks = read_benchmarks_from_file(benchmarks_fd, devices)
    except IOError as err:
        if err.errno != errno.ENOENT:
            raise
        return EMPTY_BENCHMARKS
    else:
        return benchmarks


def save_settings(config_dir, settings):
    _mkdir(config_dir)
    with open(config_dir/SETTINGS_FILENAME, 'w') as settings_fd:
        write_settings_to_file(settings_fd, settings)


def save_benchmarks(config_dir, benchmarks):
    _mkdir(config_dir)
    with open(config_dir/BENCHMARKS_FILENAME, 'w') as benchmarks_fd:
        write_benchmarks_to_file(benchmarks_fd, benchmarks)


def _mkdir(d):
    try:
        os.makedirs(d)
    except OSError:
        if not os.path.isdir(d):
            raise

