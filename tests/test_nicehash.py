from unittest import main, TestCase

from nuxhash.daemon import DONATE_ADDRESS
from nuxhash.settings import DEFAULT_SETTINGS
from nuxhash.nicehash import get_request, post_request, api2_send


class TestNHApi(TestCase):

    def test_get_request(self):
        response = api2_send(get_request('exchangeRate', 'list'))
        self.assertIn('list', response)

        exchange = response['list'][0]
        self.assertIn('exchangeRate', exchange)
        self.assertIn('toCurrency', exchange)
        self.assertIn('fromCurrency', exchange)


class TestNHBalance(TestCase):

    def test_balance(self):
        balance = nicehash.unpaid_balance(DONATE_ADDRESS)
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
        self.assertGreater(self.payrates['cryptonight'], 0.0)

    def test_stratum(self):
        self.assertEqual(self.stratums['cryptonight'],
                         'cryptonight.eu.nicehash.com:3355')

if __name__ == '__main__':
    main()

