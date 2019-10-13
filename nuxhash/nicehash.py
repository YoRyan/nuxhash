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

def unpaid_balance(nx_settings, address):
    return None

