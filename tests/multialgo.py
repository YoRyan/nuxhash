import sys
sys.path.append('..')

import nicehash, settings
from pprint import pprint

paying, stratums = nicehash.simplemultialgo_info(settings.DEFAULT_SETTINGS)

print 'mBTC per hash:'
pprint(paying)

print
print 'connection info:'
pprint(stratums)

