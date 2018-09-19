import ConfigParser
import json
import os
from pathlib2 import Path
from collections import defaultdict

DEFAULT_CONFIGDIR = Path(os.path.expanduser('~/.config/nuxhash'))
SETTINGS_FILENAME = 'settings.conf'
BENCHMARKS_FILENAME = 'benchmarks.json'

DEFAULT_SETTINGS = {
    'nicehash': {
        'wallet': '',
        'workername': 'nuxhash',
        'region': 'usa',
        },
    'excavator': {
        'enabled': True,
        'port': 3456
        },
    'switching': {
        'interval': 60,
        'threshold': 0.1
        },
    'gui': {
        'units': 'mBTC'
        }
    }

def read_settings_from_file(fd):
    settings = {}
    parser = ConfigParser.SafeConfigParser()
    parser.readfp(fd)

    def get_option(parser_method, section, option):
        try:
            return parser_method(section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return DEFAULT_SETTINGS[section][option]

    nicehash = {}
    nicehash['wallet'] = get_option(parser.get, 'nicehash', 'wallet')
    nicehash['workername'] = get_option(parser.get, 'nicehash', 'workername')
    nicehash['region'] = get_option(parser.get, 'nicehash', 'region')
    settings['nicehash'] = nicehash

    excavator = {}
    excavator['enabled'] = get_option(parser.getboolean, 'excavator', 'enabled')
    excavator['port'] = get_option(parser.getint, 'excavator', 'port')
    settings['excavator'] = excavator

    switching = {}
    switching['interval'] = get_option(parser.getint, 'switching', 'interval')
    switching['threshold'] = get_option(parser.getfloat, 'switching', 'threshold')
    settings['switching'] = switching

    gui = {}
    gui['units'] = get_option(parser.get, 'gui', 'units')
    settings['gui'] = gui

    return settings

def write_settings_to_file(fd, settings):
    parser = ConfigParser.SafeConfigParser()

    for section in settings:
        parser.add_section(section)
        for option in settings[section]:
            value = settings[section][option]
            parser.set(section, option, str(value))

    parser.write(fd)

def read_benchmarks_from_file(fd, devices):
    benchmarks = defaultdict(lambda: {})
    js = json.load(fd, 'ascii')

    for js_device in js:
        device = next((d for d in devices if str(d) == js_device), None)
        if device is not None:
            # read speeds
            js_speeds = js[js_device]
            for algorithm in js_speeds:
                if isinstance(js_speeds[algorithm], list):
                    benchmarks[device][algorithm] = js_speeds[algorithm]
                else:
                    benchmarks[device][algorithm] = [js_speeds[algorithm]]

    return benchmarks

def write_benchmarks_to_file(fd, benchmarks):
    to_file = {}

    for device in benchmarks:
        to_file[str(device)] = {}
        speeds = benchmarks[device]
        for algorithm in speeds:
            if len(speeds[algorithm]) == 1:
                to_file[str(device)][algorithm] = speeds[algorithm][0]
            else:
                to_file[str(device)][algorithm] = speeds[algorithm]

    json.dump(to_file, fd, indent=4)

def load_persistent_data(config_dir, devices):
    try:
        with open(str(config_dir/SETTINGS_FILENAME), 'r') as settings_fd:
            settings = read_settings_from_file(settings_fd)
    except IOError as err:
        if err.errno != os.errno.ENOENT:
            raise
        settings = DEFAULT_SETTINGS

    benchmarks = defaultdict(lambda: {})
    try:
        with open(str(config_dir/BENCHMARKS_FILENAME), 'r') as benchmarks_fd:
            benchmarks = read_benchmarks_from_file(benchmarks_fd, devices)
    except IOError as err:
        if err.errno != os.errno.ENOENT:
            raise

    return settings, benchmarks

def save_persistent_data(config_dir, settings, benchmarks):
    try:
        os.makedirs(str(config_dir))
    except OSError:
        if not os.path.isdir(str(config_dir)):
            raise

    with open(str(config_dir/SETTINGS_FILENAME), 'w') as settings_fd:
        write_settings_to_file(settings_fd, settings)

    with open(str(config_dir/BENCHMARKS_FILENAME), 'w') as benchmarks_fd:
        write_benchmarks_to_file(benchmarks_fd, benchmarks)

