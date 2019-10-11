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


def api2_get(*path, **params):
    return Request('GET', f"{API2_ENDPOINT}{'/'.join(path)}",
                   params=params).prepare()


def api2_post(body, *path, **params):
    return Request('POST', f"{API2_ENDPOINT}{'/'.join(path)}",
                   data=body, params=params).prepare()


def send(prepped_request):
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
    response = send(api2_get('public', 'simplemultialgo', 'info'))
    pay_factor = 1e-9 # GH -> H/s/day
    return {algorithm['algorithm'].lower(): float(algorithm['paying'])*pay_factor
            for algorithm in response['miningAlgorithms']}

def stratums(nx_settings):
    response = send(api2_get('mining', 'algorithms'))
    ports = {algorithm['algorithm'].lower(): algorithm['port']
             for algorithm in response['miningAlgorithms']}
    region = nx_settings['nicehash']['region']
    return {algorithm: f'{algorithm}.{region}.nicehash.com:{port}'
            for algorithm, port in ports.items()}

