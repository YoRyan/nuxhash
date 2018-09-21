import json
from urllib.parse import urlencode
from urllib.request import urlopen

TIMEOUT = 20

def api_call(method, params):
    get_data = { 'method': method }
    get_data.update(params)

    request = urlopen('https://api.nicehash.com/api?%s' %
                      urlencode(get_data), timeout=TIMEOUT)
    return json.load(request)

def unpaid_balance(address):
    response = api_call('stats.provider', { 'addr': address })
    balances = response['result']['stats']
    return sum([float(b['balance']) for b in balances])

def simplemultialgo_info(nx_settings):
    response = api_call('simplemultialgo.info', [])

    algorithms_info = response['result']['simplemultialgo']
    mbtc_per_hash = {a['name']: float(a['paying'])*1e-11 for a in algorithms_info}
    stratums = {a['name']: '%s.%s.nicehash.com:%d' % (a['name'],
                                                      nx_settings['nicehash']['region'],
                                                      a['port'])
                for a in algorithms_info}

    return mbtc_per_hash, stratums

