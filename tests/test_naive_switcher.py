from pathlib import Path
from unittest import main, TestCase

import nuxhash.settings
import tests
from nuxhash.miners.excavator import Excavator
from nuxhash.switching.naive import NaiveSwitcher


class TestNaiveSwitcher(TestCase):

    def setUp(self):
        settings = nuxhash.settings.DEFAULT_SETTINGS
        settings['switching']['threshold'] = 0.5

        self.devices = tests.get_test_devices()
        self.benchmarks = tests.get_test_benchmarks()
        self.miner = Excavator(Path('/'))
        self.equihash = next(a for a in self.miner.algorithms
                             if a.algorithms == ['equihash'])
        self.neoscrypt = next(a for a in self.miner.algorithms
                              if a.algorithms == ['neoscrypt'])

        self.switcher = NaiveSwitcher(settings)
        self.switcher.reset()

    def test_most_profitable(self):
        device = self.devices[0]

        equihash_revenue = 4.0*self.benchmarks[device]['excavator_equihash'][0]
        neoscrypt_revenue = 2.0*self.benchmarks[device]['excavator_neoscrypt'][0]
        revenues = { device: { self.equihash: equihash_revenue,
                               self.neoscrypt: neoscrypt_revenue } }
        decision = self.switcher.decide(revenues, None)

        self.assertEqual(decision[device], self.neoscrypt)

    def test_below_threshold(self):
        device = self.devices[0]

        self.switcher.decide({ device: { self.equihash: 2.0,
                                         self.neoscrypt: 1.0 } }, None)
        decision = self.switcher.decide({ device: { self.equihash: 2.0,
                                                    self.neoscrypt: 2.5 } }, None)

        self.assertEqual(decision[device], self.equihash)

    def test_above_threshold(self):
        device = self.devices[0]

        self.switcher.decide({ device: { self.equihash: 2.0,
                                         self.neoscrypt: 1.0 } }, None)
        decision = self.switcher.decide({ device: { self.equihash: 2.0,
                                                    self.neoscrypt: 3.5 } }, None)

        self.assertEqual(decision[device], self.neoscrypt)


if __name__ == '__main__':
    main()

