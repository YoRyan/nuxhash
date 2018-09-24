import logging
import socket
import threading
from copy import deepcopy
from collections import defaultdict
from datetime import datetime
from ssl import SSLError
from time import sleep
from urllib.error import URLError

import wx
from wx.lib.newevent import NewEvent

from nuxhash import nicehash, settings
from nuxhash.devices.nvidia import enumerate_devices as nvidia_devices
from nuxhash.gui.mining import MiningScreen
from nuxhash.gui.settings import SettingsScreen
from nuxhash.miners.excavator import Excavator
from nuxhash.switching.naive import NaiveSwitcher


PADDING_PX = 10
BALANCE_UPDATE_MIN = 5
CONFIG_DIR = settings.DEFAULT_CONFIGDIR

NewBalanceEvent, EVT_BALANCE = NewEvent()
MiningStatusEvent, EVT_MINING_STATUS = NewEvent()


class MainWindow(wx.Frame):

    def __init__(self, parent, *args, **kwargs):
        wx.Frame.__init__(self, parent, *args, **kwargs)
        self.SetSizeHints(minW=500, minH=500)
        self._devices = []
        self._settings = None
        self._benchmarks = None
        notebook = wx.Notebook(self)

        self._mining_screen = MiningScreen(notebook,
                                           devices=self._devices,
                                           window=self)
        notebook.AddPage(self._mining_screen, text='Mining')

        def settings_callback(new_settings):
            self.read_settings(new_settings)
            self._save_persist()
        self._settings_screen = SettingsScreen(notebook,
                                               commit_callback=settings_callback)
        notebook.AddPage(self._settings_screen, text='Settings')

        self.Bind(EVT_BALANCE, self.OnNewBalance)
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda event: self._update_balance(), self._timer)
        self._timer.Start(milliseconds=BALANCE_UPDATE_MIN*60*1e3)

        self._mining = False
        self._mining_thread = None
        self.Bind(EVT_MINING_STATUS, self.OnMiningStatus)

        self._devices = nvidia_devices()

        self._load_persist()

    def read_settings(self, new_settings):
        self._settings = new_settings
        for s in [self._settings_screen,
                  self._mining_screen]:
            s.read_settings(new_settings)
        self._update_balance()

    def _load_persist(self):
        nx_settings, nx_benchmarks = settings.load_persistent_data(
            CONFIG_DIR, self._devices)
        self.read_settings(nx_settings)
        self._benchmarks = nx_benchmarks

    def _save_persist(self):
        settings.save_persistent_data(CONFIG_DIR,
                                      self._settings, self._benchmarks)

    def _update_balance(self):
        address = self._settings['nicehash']['wallet']
        thread = threading.Thread(target=post_balance, args=(address, self))
        thread.start()

    def start_mining(self):
        if not self._mining:
            self._mining_thread = MiningThread(self,
                                               deepcopy(self._settings),
                                               deepcopy(self._benchmarks),
                                               self._devices)
            self._mining_thread.start()
            self._mining_screen.start_mining()
            self._mining = True

    def stop_mining(self):
        if self._mining:
            self._mining_thread.stop_signal.set()
            self._mining_thread.join()
            self._mining_screen.stop_mining()
            self._mining = False

    def toggle_mining(self):
        if self._mining:
            self.stop_mining()
        else:
            self.start_mining()

    def OnNewBalance(self, event):
        self._mining_screen.set_balance(event.balance)

    def OnMiningStatus(self, event):
        self._mining_screen.set_mining(event)


def post_balance(address, target):
    balance = nicehash.unpaid_balance(address)
    wx.PostEvent(target, NewBalanceEvent(balance=balance))


class MiningThread(threading.Thread):

    def __init__(self, window, settings, benchmarks, devices):
        threading.Thread.__init__(self)
        self._window = window
        self._settings = settings
        self._benchmarks = benchmarks
        self._devices = devices
        self.stop_signal = threading.Event()

    def run(self):
        # Initialize miners.
        mbtc_per_hash = stratums = download_time = None
        while mbtc_per_hash is None:
            try:
                mbtc_per_hash, stratums = nicehash.simplemultialgo_info(
                    self._settings)
            except (socket.error, socket.timeout, SSLError, URLError):
                sleep(5)
            else:
                download_time = datetime.now()
        miners = [Excavator(CONFIG_DIR, self._settings)]
        for miner in miners:
            miner.stratums = stratums
        algorithms = sum([miner.algorithms for miner in miners], [])

        # Initialize profit-switching.
        profit_switch = NaiveSwitcher(self._settings)
        profit_switch.reset()

        assigned_algorithm = {device: None for device in self._devices}
        revenues = {device: defaultdict(lambda: 0.0) for device in self._devices}
        while not self.stop_signal.is_set():
            # Calculate BTC/day rates.
            def revenue(device, algorithm):
                benchmarks = self._benchmarks[device]
                if algorithm.name in benchmarks:
                    return sum([mbtc_per_hash[algorithm.algorithms[i]]
                                *benchmarks[algorithm.name][i]
                                for i in range(len(algorithm.algorithms))])
                else:
                    return 0.0
            revenues = {device: {algorithm: revenue(device, algorithm)
                                 for algorithm in algorithms}
                        for device in self._devices}

            # Get device -> algorithm assignments from profit switcher.
            assigned_algorithm = profit_switch.decide(revenues, download_time)
            wx.PostEvent(self._window,
                         MiningStatusEvent(mbtc_per_day_per_hash=revenues,
                                           assignments=assigned_algorithm))
            for this_algorithm in algorithms:
                this_devices = [device for device, algorithm
                                in assigned_algorithm.items()
                                if algorithm == this_algorithm]
                this_algorithm.set_devices(this_devices)

            self.stop_signal.wait(self._settings['switching']['interval'])

            for algorithm in assigned_algorithm.values():
                if not algorithm.parent.is_running():
                    logging.error('Detected %s crash, restarting miner'
                                  % algorithm.name)
                    algorithm.parent.reload()

            try:
                mbtc_per_hash, stratums = nicehash.simplemultialgo_info(
                    self._settings)
            except (socket.error, socket.timeout, SSLError, URLError) as err:
                logging.warning('NiceHash stats: %s' % err)
            except nicehash.BadResponseError:
                logging.warning('NiceHash stats: Bad response')
            else:
                download_time = datetime.now()

        logging.info('Stopping mining')
        for miner in miners:
            miner.unload()


def main():
    app = wx.App(False)
    frame = MainWindow(None, title='nuxhash')
    frame.Show()
    app.MainLoop()

