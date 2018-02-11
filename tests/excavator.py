import sys
sys.path.append('..')

import miners.devices
import miners.excavator
import miners.miner
import settings
import utils

import logging
from pprint import pprint
from time import sleep

logging.basicConfig(format='%(message)s', level=logging.DEBUG)

devices = miners.devices.enumerate_nvidia_devices()

stratums = {
    'neoscrypt': 'neoscrypt.usa.nicehash.com:3341',
    'equihash': 'equihash.usa.nicehash.com:3357',
    'daggerhashimoto': 'daggerhashimoto.usa.nicehash.com:3353',
    'pascal': 'pascal.usa.nicehash.com:3358'
    }

my_settings = settings.DEFAULT_SETTINGS
my_settings['nicehash']['wallet'] = '1BQSMa5mfDNzut5PN9xgtJe3wqaqGEEerD'

exc = miners.excavator.Excavator(my_settings, stratums)
exc.load()

ns = [a for a in exc.algorithms if a.algorithms == ['neoscrypt']][0]
ns.attach_device(devices[0])
sleep(10)
ns.detach_device(devices[0])

eq = [a for a in exc.algorithms if a.algorithms == ['equihash']][0]
logging.info('equihash benchmark = ' + str(utils.run_benchmark(eq, devices[0], 30, 60)))

dp = [a for a in exc.algorithms if a.algorithms == ['daggerhashimoto', 'pascal']][0]
logging.info('daggerhash-pascal benchmark = ' + str(utils.run_benchmark(dp, devices[0], 30, 60)))

exc.unload()

