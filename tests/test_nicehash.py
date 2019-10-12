from unittest import main, TestCase

import nuxhash.nicehash as nh
from nuxhash.settings import DEFAULT_SETTINGS


class TestNHApi(TestCase):

    def test_get_request(self):
        response = nh.send(nh.api2_get('exchangeRate', 'list'))
        self.assertIn('list', response)

        exchange = response['list'][0]
        self.assertIn('exchangeRate', exchange)
        self.assertIn('toCurrency', exchange)
        self.assertIn('fromCurrency', exchange)


class TestNHMultialgo(TestCase):

    def setUp(self):
        self.settings = DEFAULT_SETTINGS
        self.settings['nicehash']['region'] = 'eu'

    def test_payrate(self):
        mbtc_per_hash = nh.simplemultialgo_info(self.settings)
        self.assertGreater(mbtc_per_hash['cryptonight'], 0.0)

    def test_stratum(self):
        stratums = nh.stratums(self.settings)
        self.assertIn('cryptonight.eu.nicehash.com', stratums['cryptonight'])

if __name__ == '__main__':
    main()

