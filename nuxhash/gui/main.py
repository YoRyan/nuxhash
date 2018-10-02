import logging
import sched
import socket
import threading
import time
from copy import deepcopy
from datetime import datetime
from ssl import SSLError
from urllib.error import URLError

import wx
from wx.lib.newevent import NewEvent

from nuxhash import nicehash, settings
from nuxhash.devices.nvidia import enumerate_devices as nvidia_devices
from nuxhash.gui import mining
from nuxhash.gui.benchmarks import BenchmarksScreen
from nuxhash.gui.settings import SettingsScreen, EVT_NEW_SETTINGS
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
        self._devices = self._probe_devices()
        notebook = wx.Notebook(self)

        self._mining_screen = mining.MiningScreen(notebook, window=self)
        notebook.AddPage(self._mining_screen, text='Mining')

        self._benchmarks_screen = BenchmarksScreen(notebook, devices=self._devices)
        notebook.AddPage(self._benchmarks_screen, text='Benchmarks')

        self._settings_screen = SettingsScreen(notebook)
        notebook.AddPage(self._settings_screen, text='Settings')

        self.Bind(EVT_BALANCE, self.OnNewBalance)
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda event: self._update_balance(), self._timer)
        self._timer.Start(milliseconds=BALANCE_UPDATE_MIN*60*1e3)

        self._mining_thread = None
        self.Bind(EVT_MINING_STATUS, self.OnMiningStatus)
        self.Bind(EVT_NEW_SETTINGS, self.OnSettingsUpdate)
        self.Bind(mining.EVT_START_MINING, self.OnStartMining)
        self.Bind(mining.EVT_STOP_MINING, self.OnStopMining)

        self.settings = settings.load_settings(CONFIG_DIR)
        self.benchmarks = settings.load_benchmarks(CONFIG_DIR, self._devices)

    @property
    def benchmarks(self):
        return self._benchmarks
    @benchmarks.setter
    def benchmarks(self, value):
        self._benchmarks = value
        for screen in [self._benchmarks_screen]:
            screen.benchmarks = value
        settings.save_benchmarks(CONFIG_DIR, self._benchmarks)

    @property
    def settings(self):
        return self._settings
    @settings.setter
    def settings(self, value):
        self._settings = value
        for screen in [self._mining_screen,
                       self._benchmarks_screen,
                       self._settings_screen]:
            screen.settings = value
        self._update_balance()
        settings.save_settings(CONFIG_DIR, self._settings)

    def _probe_devices(self):
        return nvidia_devices()

    def _update_balance(self):
        address = self._settings['nicehash']['wallet']
        thread = threading.Thread(target=post_balance, args=(address, self))
        thread.start()

    def OnNewBalance(self, event):
        wx.PostEvent(self._mining_screen, event)

    def OnMiningStatus(self, event):
        wx.PostEvent(self._mining_screen, event)

    def OnStartMining(self, event):
        if not self._mining_thread:
            self._mining_thread = MiningThread(
                devices=self._devices,
                window=self,
                settings=deepcopy(self._settings),
                benchmarks=deepcopy(self._benchmarks))
            self._mining_thread.start()

    def OnStopMining(self, event):
        if self._mining_thread:
            self._mining_thread.stop()
            self._mining_thread.join()
            self._mining_thread = None

    def OnSettingsUpdate(self, event):
        self.settings = event.settings


def post_balance(address, target):
    balance = nicehash.unpaid_balance(address)
    wx.PostEvent(target, NewBalanceEvent(balance=balance))


class MiningThread(threading.Thread):

    PROFIT_PRIORITY = 1
    STATUS_PRIORITY = 2
    STOP_PRIORITY = 0

    def __init__(self, devices=[], window=None,
                 settings=settings.DEFAULT_SETTINGS,
                 benchmarks=settings.EMPTY_BENCHMARKS):
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

