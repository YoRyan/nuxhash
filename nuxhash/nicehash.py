import json
import logging

from requests import Request, Session


API2_ENDPOINT = 'https://api2.nicehash.com/main/api/v2/'
TIMEOUT = 20


class NicehashException(Exception):
    """An exceptional reponse returned by the NiceHash service."""
    pass


class APIError(NicehashException):

    def __init__(self, result):
        self.result = result

    def __str__(self):
        return f"NH: {self.result['error']}"


class BadResponse(NicehashException):

    def __str__(self):
        return 'Bad JSON response'


def get_request(*path, **params):
    return Request('GET', f"{API2_ENDPOINT}{'/'.join(path)}",
                   params=params).prepare()


def post_request(body, *path, **params):
    return Request('POST', f"{API2_ENDPOINT}{'/'.join(path)}",
                   data=body, params=params).prepare()


def api2_send(prepped_request):
    with Session() as session:
        response = session.send(prepped_request, timeout=TIMEOUT)
        try:
            json_response = response.json()
        except (ValueError, KeyError):
            raise BadResponse
        else:
            if 'error' in json_response:
                raise APIError(json_response)
            else:
                return json_response


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

