import ConfigParser

DEFAULT_SETTINGS = {
    'nicehash': {
        'wallet': '',
        'workername': 'nuxhash',
        'region': 'usa'
        },
    'excavator': {
        'enabled': True,
        'path': '/opt/excavator/bin/excavator',
        'port': 3456
        },
    'switching': {
        'interval': 60,
        'threshold': 0.1
        }
    }

def read_from_file(fd):
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
    excavator['path'] = get_option(parser.get, 'excavator', 'path')
    excavator['port'] = get_option(parser.getint, 'excavator', 'port')
    settings['excavator'] = excavator

    switching = {}
    switching['interval'] = get_option(parser.getint, 'switching', 'interval')
    switching['threshold'] = get_option(parser.getfloat, 'switching', 'threshold')
    settings['switching'] = switching

    return settings

def write_to_file(fd, settings):
    parser = ConfigParser.SafeConfigParser()

    for section in settings:
        parser.add_section(section)
        for option in settings[section]:
            value = settings[section][option]
            parser.set(section, option, str(value))

    parser.write(fd)

