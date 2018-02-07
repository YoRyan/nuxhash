import sys
sys.path.append('..')

import miners, settings
from pprint import pprint
from time import sleep

devices = miners.devices.enumerate_nvidia_devices()

exc = miners.Excavator(settings.DEFAULT_SETTINGS, devices)
exc.load()

ns = [a for a in exc.algorithms[devices[0]] if a.algorithms == ['neoscrypt']][0]
ns.run(['neoscrypt.usa.nicehash.com:3341'], '32RPicPbRK18S2fzY4cEwNUy17iygJyPjF.test')
sleep(10)
ns.stop()

eq = [a for a in exc.algorithms[devices[0]] if a.algorithms == ['equihash']][0]
print 'equihash benchmark = ',
print eq.benchmark(['equihash.usa.nicehash.com:3357'], '32RPicPbRK18S2fzY4cEwNUy17iygJyPjF.test', 60)

dp = [a for a in exc.algorithms[devices[0]] if a.algorithms == ['daggerhashimoto', 'pascal']][0]
print 'daggerhash-pascal benchmark = ',
print dp.benchmark(['daggerhashimoto.usa.nicehash.com:3353', 'pascal.usa.nicehash.com:3358'], '32RPicPbRK18S2fzY4cEwNUy17iygJyPjF.test', 60)

exc.unload()

