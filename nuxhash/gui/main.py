import logging

import wx
from wx.lib.newevent import NewCommandEvent, NewEvent

from nuxhash import settings
from nuxhash.devices.nvidia import enumerate_devices as nvidia_devices
from nuxhash.gui.benchmarks import BenchmarksScreen
from nuxhash.gui.mining import MiningScreen
from nuxhash.gui.settings import SettingsScreen


PADDING_PX = 10
CONFIG_DIR = settings.DEFAULT_CONFIGDIR

StartMiningEvent, EVT_START_MINING = NewCommandEvent()
StopMiningEvent, EVT_STOP_MINING = NewCommandEvent()
StartBenchmarkingEvent, EVT_START_BENCHMARKS = NewCommandEvent()
StopBenchmarkingEvent, EVT_STOP_BENCHMARKS = NewCommandEvent()

NewBenchmarksEvent, EVT_BENCHMARKS = NewEvent()
NewSettingsEvent, EVT_SETTINGS = NewEvent()


class MainWindow(wx.Frame):

    def __init__(self, parent, *args, **kwargs):
        wx.Frame.__init__(self, parent, *args, **kwargs)
        self.SetSizeHints(minW=500, minH=500)
        self._Devices = self._ProbeDevices()
        self._Settings = settings.load_settings(CONFIG_DIR)
        self._Benchmarks = settings.load_benchmarks(CONFIG_DIR, self._Devices)
        self.Bind(EVT_START_MINING, self.OnStartMining)
        self.Bind(EVT_STOP_MINING, self.OnStopMining)
        self.Bind(EVT_START_BENCHMARKS, self.OnStartBenchmarking)
        self.Bind(EVT_STOP_BENCHMARKS, self.OnStopBenchmarking)

        # Create notebook and its pages.
        notebook = wx.Notebook(self)

        self._MiningScreen = MiningScreen(
            notebook, devices=self._Devices, frame=self)
        notebook.AddPage(self._MiningScreen, text='Mining')

        self._BenchmarksScreen = BenchmarksScreen(
            notebook, devices=self._Devices, frame=self)
        notebook.AddPage(self._BenchmarksScreen, text='Benchmarks')

        self._SettingsScreen = SettingsScreen(notebook, frame=self)
        notebook.AddPage(self._SettingsScreen, text='Settings')

        self._Screens = [self._MiningScreen,
                         self._BenchmarksScreen,
                         self._SettingsScreen]

    def OnStartMining(self, event):
        wx.PostEvent(self._BenchmarksScreen, event)

    def OnStopMining(self, event):
        wx.PostEvent(self._BenchmarksScreen, event)

    def OnStartBenchmarking(self, event):
        wx.PostEvent(self._MiningScreen, event)

    def OnStopBenchmarking(self, event):
        wx.PostEvent(self._MiningScreen, event)

    @property
    def Benchmarks(self):
        return self._Benchmarks
    @Benchmarks.setter
    def Benchmarks(self, value):
        self._Benchmarks = value
        logging.info('Saving user benchmarks.')
        settings.save_benchmarks(CONFIG_DIR, self._Benchmarks)
        for screen in self._Screens:
            wx.PostEvent(screen, NewBenchmarksEvent())

    @property
    def Settings(self):
        return self._Settings
    @Settings.setter
    def Settings(self, value):
        self._Settings = value
        logging.info('Saving user settings.')
        settings.save_settings(CONFIG_DIR, self._Settings)
        for screen in self._Screens:
            wx.PostEvent(screen, NewSettingsEvent())

    def _ProbeDevices(self):
        return nvidia_devices()


def main():
    app = wx.App(False)
    frame = MainWindow(None, title='nuxhash')
    frame.Show()
    app.MainLoop()

