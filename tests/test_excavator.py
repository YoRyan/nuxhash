import unittest
from subprocess import call
from time import sleep

import nuxhash.settings
from nuxhash.daemon import DONATE_ADDRESS
from nuxhash.devices.nvidia import enumerate_devices as nvidia_devices
from nuxhash.download.downloads import make_miners
from nuxhash.miners.excavator import Excavator
from tests import get_test_devices


devices = nvidia_devices()


@unittest.skipIf(len(devices) == 0, 'requires an nvidia graphics card')
class TestExcavator(unittest.TestCase):

    def setUp(self):
        self.configdir = nuxhash.settings.DEFAULT_CONFIGDIR
        self.device = devices[0]

        self.settings = nuxhash.settings.DEFAULT_SETTINGS
        self.settings['nicehash']['wallet'] = DONATE_ADDRESS

        self.alt_settings = nuxhash.settings.DEFAULT_SETTINGS
        self.alt_settings['nicehash']['wallet'] = '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'
        self.alt_settings['nicehash']['workername'] = 'nuxhashtest'

        self.excavator = Excavator(self.configdir)
        self.excavator.settings = self.settings
        self.equihash = next(a for a in self.excavator.algorithms
                             if a.algorithms == ['equihash'])
        self.neoscrypt = next(a for a in self.excavator.algorithms
                              if a.algorithms == ['neoscrypt'])

        make_miners(self.configdir)
        self.excavator.load()

    def tearDown(self):
        self.excavator.unload()

    def _get_workers(self):
        response = self.excavator.server.send_command('worker.list', [])
        def algorithms(worker): return [a['name'] for a in worker['algorithms']]
        return [{ 'device_uuid': w['device_uuid'],
                  'algorithms': algorithms(w) } for w in response['workers']]

    def _get_algorithms(self):
        response = self.excavator.server.send_command('algorithm.list', [])
        return [a['name'] for a in response['algorithms']]

    def test_add_worker(self):
        self.equihash.set_devices([self.device])
        self.assertEqual(self._get_workers(), [{ 'device_uuid': self.device.uuid,
                                                 'algorithms': ['equihash'] }])

    def test_add_algorithm(self):
        self.equihash.set_devices([self.device])
        self.assertEqual(self._get_algorithms(), ['equihash'])

    def test_remove_worker(self):
        self.equihash.set_devices([self.device])
        sleep(1)
        self.equihash.set_devices([])
        self.assertEqual(self._get_workers(), [])

    def test_remove_algorithm(self):
        self.equihash.set_devices([self.device])
        sleep(1)
        self.equihash.set_devices([])
        self.assertEqual(self._get_algorithms(), [])

    def test_report_speed(self):
        self.equihash.set_devices([self.device])
        self.assertEqual(len(self.equihash.current_speeds()), 1)

    def test_switch_worker(self):
        self.equihash.set_devices([self.device])
        sleep(1)
        self.equihash.set_devices([])
        self.neoscrypt.set_devices([self.device])
        self.assertEqual(self._get_workers(), [{ 'device_uuid': self.device.uuid,
                                                 'algorithms': ['neoscrypt'] }])

    def test_switch_algorithm(self):
        self.equihash.set_devices([self.device])
        sleep(1)
        self.equihash.set_devices([])
        self.neoscrypt.set_devices([self.device])
        self.assertEqual(self._get_algorithms(), ['neoscrypt'])

    def test_simultaneous_worker(self):
        self.equihash.set_devices([self.device])
        sleep(1)
        self.neoscrypt.set_devices([self.device])
        sleep(1)
        self.equihash.set_devices([])
        self.assertEqual(self._get_workers(), [{ 'device_uuid': self.device.uuid,
                                                 'algorithms': ['neoscrypt'] }])

    def test_simultaneous_algorithm(self):
        self.equihash.set_devices([self.device])
        sleep(1)
        self.neoscrypt.set_devices([self.device])
        sleep(1)
        self.equihash.set_devices([])
        self.assertEqual(self._get_algorithms(), ['neoscrypt'])

    def test_set_twice(self):
        self.equihash.set_devices([self.device])
        sleep(1)
        self.equihash.set_devices([self.device])
        self.assertEqual(self._get_algorithms(), ['equihash'])

    def test_benchmark_mode(self):
        self.equihash.set_devices([self.device])
        sleep(1)
        self.equihash.benchmarking = True
        self.assertEqual(self._get_workers(), [{ 'device_uuid': self.device.uuid,
                                                 'algorithms': ['equihash'] }])

    def test_benchmark_stop(self):
        self.equihash.benchmarking = True
        self.equihash.set_devices([self.device])
        sleep(1)
        self.equihash.set_devices([])
        self.assertEqual(self._get_workers(), [])

    def test_bad_device(self):
        device = get_test_devices()[0]
        self.assertFalse(self.equihash.accepts(device))

    def test_set_bad_device(self):
        devices = get_test_devices()
        self.assertRaises(AssertionError,
                          lambda: self.equihash.set_devices(devices))

    def test_settings_switch(self):
        self.equihash.set_devices([self.device])
        sleep(1)
        self.excavator.settings = self.alt_settings
        self.assertEqual(self._get_workers(), [{ 'device_uuid': self.device.uuid,
                                                 'algorithms': ['equihash'] }])

    def test_settings_switch_algorithm(self):
        self.equihash.set_devices([self.device])
        sleep(1)
        self.excavator.settings = self.alt_settings
        self.assertEqual(self._get_algorithms(), ['equihash'])

    def test_settings_switch_back(self):
        self.equihash.set_devices([self.device])
        sleep(1)
        status = (self._get_workers(), self._get_algorithms())
        self.excavator.settings = self.alt_settings
        sleep(1)
        self.excavator.settings = self.settings
        sleep(1)
        self.assertEqual(status, (self._get_workers(), self._get_algorithms()))

    def test_restart_after_crash(self):
        self.equihash.set_devices([self.device])
        status = (self._get_workers(), self._get_algorithms())
        sleep(1)
        call(['killall', 'excavator'])
        sleep(1)
        self.equihash.current_speeds()
        self.assertEqual(status, (self._get_workers(), self._get_algorithms()))


if __name__ == '__main__':
    unittest.main()

