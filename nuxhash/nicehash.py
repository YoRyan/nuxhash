import json
from urllib.parse import urlencode
from urllib.request import urlopen


TIMEOUT = 20


class NicehashAPIError(Exception):
    """Exception returned by the NiceHash service."""
    def __init__(self, response):
        self.response = response
        self.error = response['error']


def api_call(method, params):
    get_data = { 'method': method }
    get_data.update(params)
    request = urlopen('https://api.nicehash.com/api?%s' %
                      urlencode(get_data), timeout=TIMEOUT)
    response = json.load(request)
    result = response['result']
    if 'error' in result:
        raise NicehashAPIError(result)
    else:
        return response


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

