import json
import logging
from urllib.parse import urlencode
from urllib.request import urlopen


TIMEOUT = 20


class NicehashException(Exception):
    """An exceptional reponse returned by the NiceHash service."""
    pass


class APIError(NicehashException):

    def __init__(self, result):
        self.result = result

    def __str__(self):
        return 'NH: %s' % self.result['error']


class BadResponse(NicehashException):

    def __str__(self):
        return 'Bad JSON response'


def api_call(method, params):
    get_data = { 'method': method }
    get_data.update(params)
    with urlopen('https://api.nicehash.com/api?%s'
                 % urlencode(get_data), timeout=TIMEOUT) as request:
        try:
            result = json.load(request)['result']
        except (ValueError, KeyError):
            raise BadResponse
        else:
            if 'error' in result:
                raise APIError(result)
            else:
                return result


def unpaid_balance(address):
    result = api_call('stats.provider', { 'addr': address })
    balances = result['stats']
    return sum([float(b['balance']) for b in balances])


def simplemultialgo_info(nx_settings):
    response = api_call('simplemultialgo.info', [])
    algorithms_info = response['simplemultialgo']
    mbtc_per_hash = {algorithm['name']: (float(algorithm['paying'])
                                         *1e-9) # GH -> H/s/day
                     for algorithm in algorithms_info}
    stratums = {algorithm['name']: '%s.%s.nicehash.com:%d'
                % (algorithm['name'],
                   nx_settings['nicehash']['region'],
                   algorithm['port'])
                for algorithm in algorithms_info}
    return mbtc_per_hash, stratums

