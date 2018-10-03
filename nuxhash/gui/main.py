import logging

import wx
from wx.lib.newevent import NewEvent

from nuxhash import settings
from nuxhash.devices.nvidia import enumerate_devices as nvidia_devices
from nuxhash.gui.benchmarks import BenchmarksScreen
from nuxhash.gui.mining import MiningScreen
from nuxhash.gui.settings import SettingsScreen


PADDING_PX = 10
CONFIG_DIR = settings.DEFAULT_CONFIGDIR

NewBenchmarksEvent, EVT_BENCHMARKS = NewEvent()
NewSettingsEvent, EVT_SETTINGS = NewEvent()


class MainWindow(wx.Frame):

    def __init__(self, parent, *args, **kwargs):
        wx.Frame.__init__(self, parent, *args, **kwargs)
        self.SetSizeHints(minW=500, minH=500)
        self._devices = self._probe_devices()
        self._settings = settings.load_settings(CONFIG_DIR)
        self._benchmarks = settings.load_benchmarks(CONFIG_DIR, self._devices)

        # Create notebook and its pages.
        notebook = wx.Notebook(self)

        self._mining_screen = MiningScreen(
            notebook, devices=self._devices, frame=self)
        notebook.AddPage(self._mining_screen, text='Mining')

        self._benchmarks_screen = BenchmarksScreen(
            notebook, devices=self._devices, frame=self)
        notebook.AddPage(self._benchmarks_screen, text='Benchmarks')

        self._settings_screen = SettingsScreen(notebook, frame=self)
        notebook.AddPage(self._settings_screen, text='Settings')

        self._screens = [self._mining_screen,
                         self._benchmarks_screen,
                         self._settings_screen]

    @property
    def benchmarks(self):
        return self._benchmarks
    @benchmarks.setter
    def benchmarks(self, value):
        self._benchmarks = value
        logging.info('Saving user benchmarks.')
        settings.save_benchmarks(CONFIG_DIR, self._benchmarks)
        for screen in self._screens:
            wx.PostEvent(screen, NewBenchmarksEvent())

    @property
    def settings(self):
        return self._settings
    @settings.setter
    def settings(self, value):
        self._settings = value
        logging.info('Saving user settings.')
        settings.save_settings(CONFIG_DIR, self._settings)
        for screen in self._screens:
            wx.PostEvent(screen, NewSettingsEvent())

    def _probe_devices(self):
        return nvidia_devices()


def main():
    app = wx.App(False)
    frame = MainWindow(None, title='nuxhash')
    frame.Show()
    app.MainLoop()

