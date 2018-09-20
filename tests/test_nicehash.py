from nuxhash.settings import DEFAULT_SETTINGS
import nuxhash.nicehash

from unittest import main, TestCase

class TestNHApi(TestCase):
    def runTest(self):
        response = nuxhash.nicehash.api_call('unknown', {})
        self.assertEqual(response, { 'result': { 'error': 'Unknown method.' } })

class TestNHBalance(TestCase):
    def runTest(self):
        balance = nuxhash.nicehash.unpaid_balance('3Qe7nT9hBSVoXr8rM2TG6pq82AmLVKHy23')
        self.assertGreaterEqual(balance, 0.0)

class TestNHMultialgo(TestCase):
    def setUp(self):
        settings = DEFAULT_SETTINGS
        settings['nicehash']['region'] = 'eu'
        self.payrates, self.stratums = nuxhash.nicehash.simplemultialgo_info(settings)
    def test_payrate(self):
        self.assertGreaterEqual(self.payrates['cryptonight'], 0.0)
    def test_stratum(self):
        self.assertEqual(self.stratums['cryptonight'], 'cryptonight.eu.nicehash.com:3355')

if __name__ == '__main__':
    main()

