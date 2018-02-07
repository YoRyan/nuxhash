import json
import urllib
import urllib2

TIMEOUT = 20

def api_call(method, params):
    get_data = { 'method': method }
    get_data.update(params)
    request = urllib2.urlopen('https://api.nicehash.com/api?%s' %
                              urllib.urlencode(get_data), timeout=TIMEOUT)
    return json.load(request, 'ascii')

def algorithm_payrates():
    response = api_call('simplemultialgo.info', {})
    algorithms = response['result']['simplemultialgo']
    payrates = dict([(a['name'], float(a['paying'])) for a in algorithms])
    ports = dict([(a['name'], int(a['port'])) for a in algorithms])
    return payrates, ports

def unpaid_balance(address):
    response = api_call('stats.provider', { 'addr': address })
    balances = response['result']['stats']
    return sum([float(b['balance']) for b in balances])

