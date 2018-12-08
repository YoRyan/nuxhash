from unittest import main, TestCase

from nuxhash.settings import DEFAULT_SETTINGS
from nuxhash import nicehash


class TestNHApi(TestCase):

    def runTest(self):
        self.assertRaises(nicehash.APIError,
                          lambda: nicehash.api_call('unknown', {}))


class TestNHBalance(TestCase):

    def test_balance(self):
        balance = nicehash.unpaid_balance('3Qe7nT9hBSVoXr8rM2TG6pq82AmLVKHy23')
        self.assertGreaterEqual(balance, 0.0)

    def test_bad_address(self):
        self.assertRaises(nicehash.APIError,
                          lambda: nicehash.unpaid_balance('x'))


class TestNHMultialgo(TestCase):

    def setUp(self):
        settings = DEFAULT_SETTINGS
        settings['nicehash']['region'] = 'eu'
        self.payrates, self.stratums = nicehash.simplemultialgo_info(settings)

    def test_payrate(self):
        self.assertGreaterEqual(self.payrates['cryptonight'], 0.0)

    def test_stratum(self):
        self.assertEqual(self.stratums['cryptonight'],
                         'cryptonight.eu.nicehash.com:3355')

if __name__ == '__main__':
    main()

