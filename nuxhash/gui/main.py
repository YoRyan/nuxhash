import logging
import sched
import socket
import threading
import time
from copy import deepcopy
from collections import defaultdict
from datetime import datetime
from ssl import SSLError
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
MINING_UPDATE_SECS = 5
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
            self._mining_thread.stop()
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

    PROFIT_PRIORITY = 1
    STATUS_PRIORITY = 2
    STOP_PRIORITY = 0

    def __init__(self, window, settings, benchmarks, devices):
        threading.Thread.__init__(self)
        self._window = window
        self._settings = settings
        self._benchmarks = benchmarks
        self._devices = devices
        self._stop_signal = threading.Event()
        self._scheduler = sched.scheduler(
            time.time, lambda t: self._stop_signal.wait(t))

    def run(self):
        # Initialize miners.
        stratums = None
        while stratums is None:
            try:
                payrates, stratums = nicehash.simplemultialgo_info(
                    self._settings)
            except (socket.error, socket.timeout, SSLError, URLError):
                time.sleep(5)
        self._miners = [Excavator(CONFIG_DIR, self._settings)]
        for miner in self._miners:
            miner.stratums = stratums
        self._algorithms = sum([miner.algorithms for miner in self._miners], [])

        # Initialize profit-switching.
        self._profit_switch = NaiveSwitcher(self._settings)
        self._profit_switch.reset()

        self._scheduler.enter(0, MiningThread.PROFIT_PRIORITY, self._switch_algos)
        self._scheduler.enter(0, MiningThread.STATUS_PRIORITY, self._read_status)
        self._scheduler.run()

    def stop(self):
        self._scheduler.enter(0, MiningThread.STOP_PRIORITY, self._stop_mining)
        self._stop_signal.set()

    def _switch_algos(self):
        # Get profitability information from NiceHash.
        try:
            payrates, stratums = nicehash.simplemultialgo_info(
                self._settings)
        except (socket.error, socket.timeout, SSLError, URLError) as err:
            logging.warning('NiceHash stats: %s' % err)
        except nicehash.BadResponseError:
            logging.warning('NiceHash stats: Bad response')
        else:
            download_time = datetime.now()
            self._current_payrates = payrates

        # Calculate BTC/day rates.
        def revenue(device, algorithm):
            benchmarks = self._benchmarks[device]
            if algorithm.name in benchmarks:
                return sum([payrates[algorithm.algorithms[i]]
                            *benchmarks[algorithm.name][i]
                            for i in range(len(algorithm.algorithms))])
            else:
                return 0.0
        revenues = {device: {algorithm: revenue(device, algorithm)
                             for algorithm in self._algorithms}
                    for device in self._devices}

        # Get device -> algorithm assignments from profit switcher.
        assigned_algorithm = self._profit_switch.decide(revenues, download_time)
        self._assignments = assigned_algorithm
        for this_algorithm in self._algorithms:
            this_devices = [device for device, algorithm
                            in assigned_algorithm.items()
                            if algorithm == this_algorithm]
            this_algorithm.set_devices(this_devices)

        self._scheduler.enter(self._settings['switching']['interval'],
                              MiningThread.PROFIT_PRIORITY, self._switch_algos)

    def _read_status(self):
        running_algorithms = self._assignments.values()
        # Check miner status.
        for algorithm in running_algorithms:
            if not algorithm.parent.is_running():
                logging.error('Detected %s crash, restarting miner'
                              % algorithm.name)
                algorithm.parent.reload()
        speeds = {algorithm: algorithm.current_speeds()
                  for algorithm in running_algorithms}
        revenue = {algorithm: sum([self._current_payrates[multialgorithm]
                                   *speeds[algorithm][i]
                                   for i, multialgorithm
                                   in enumerate(algorithm.algorithms)])
                    for algorithm in running_algorithms}
        devices = {algorithm: [device for device, this_algorithm
                               in self._assignments.items()
                               if this_algorithm == algorithm]
                   for algorithm in running_algorithms}
        wx.PostEvent(self._window,
                     MiningStatusEvent(speeds=speeds, revenue=revenue,
                                       devices=devices))
        self._scheduler.enter(MINING_UPDATE_SECS, MiningThread.STATUS_PRIORITY,
                              self._read_status)

    def _stop_mining(self):
        logging.info('Stopping mining')
        for algorithm in self._algorithms:
            algorithm.set_devices([])
        for miner in self._miners:
            miner.unload()
        # Empty the scheduler.
        for job in self._scheduler.queue:
            self._scheduler.cancel(job)


def main():
    app = wx.App(False)
    frame = MainWindow(None, title='nuxhash')
    frame.Show()
    app.MainLoop()

