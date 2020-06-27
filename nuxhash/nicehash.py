from nuxhash.nhrest.python import nicehash as nh


HOST = 'https://api2.nicehash.com'


def simplemultialgo_info(nx_settings):
    api = nh.public_api(HOST)
    response = api.get_multialgo_info()
    pay_factor = 1e-9 # GH -> H/s/day
    return {algorithm['algorithm'].lower(): float(algorithm['paying'])*pay_factor
            for algorithm in response['miningAlgorithms']}

def stratums(nx_settings):
    api = nh.public_api(HOST)
    response = api.get_algorithms()
    ports = {algorithm['algorithm'].lower(): algorithm['port']
             for algorithm in response['miningAlgorithms']}
    region = nx_settings['nicehash']['region']
    return {algorithm: f'{algorithm}.{region}.nicehash.com:{port}'
            for algorithm, port in ports.items()}

def get_balances(nx_settings):
    address = nx_settings['nicehash']['wallet']

    response = nh.public_api(HOST).request(
            'GET', f'/main/api/v2/mining/external/{address}/rigs2/', '', None)
    unpaid = response.get('unpaidAmount', None)
    if response.get('externalAddress', True):
        wallet = response.get('externalBalance', None)
    else:
        try:
            response = nh.private_api(HOST,
                                      nx_settings['nicehash']['api_organization'],
                                      nx_settings['nicehash']['api_key'],
                                      nx_settings['nicehash']['api_secret']) \
                    .get_accounts_for_currency('BTC')
        except:
            wallet = None
        else:
            wallet = response.get('balance', None)

    def float_if_valid(v): return None if v is None else float(v)
    return float_if_valid(wallet), float_if_valid(unpaid)

