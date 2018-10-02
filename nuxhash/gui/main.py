import wx

from nuxhash import settings
from nuxhash.devices.nvidia import enumerate_devices as nvidia_devices
from nuxhash.gui.benchmarks import BenchmarksScreen
from nuxhash.gui.mining import MiningScreen
from nuxhash.gui.settings import SettingsScreen, EVT_NEW_SETTINGS


PADDING_PX = 10
CONFIG_DIR = settings.DEFAULT_CONFIGDIR


class MainWindow(wx.Frame):

    def __init__(self, parent, *args, **kwargs):
        wx.Frame.__init__(self, parent, *args, **kwargs)
        self.SetSizeHints(minW=500, minH=500)
        self._devices = self._probe_devices()

        notebook = wx.Notebook(self)

        self._mining_screen = MiningScreen(notebook, devices=self._devices)
        notebook.AddPage(self._mining_screen, text='Mining')

        self._benchmarks_screen = BenchmarksScreen(notebook, devices=self._devices)
        notebook.AddPage(self._benchmarks_screen, text='Benchmarks')

        self._settings_screen = SettingsScreen(notebook)
        notebook.AddPage(self._settings_screen, text='Settings')

        self.Bind(EVT_NEW_SETTINGS, self.OnSettingsUpdate)

        self.settings = settings.load_settings(CONFIG_DIR)
        self.benchmarks = settings.load_benchmarks(CONFIG_DIR, self._devices)

    @property
    def benchmarks(self):
        return self._benchmarks
    @benchmarks.setter
    def benchmarks(self, value):
        self._benchmarks = value
        for screen in [self._mining_screen,
                       self._benchmarks_screen]:
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
        settings.save_settings(CONFIG_DIR, self._settings)

    def _probe_devices(self):
        return nvidia_devices()

    def OnSettingsUpdate(self, event):
        self.settings = event.settings


def main():
    app = wx.App(False)
    frame = MainWindow(None, title='nuxhash')
    frame.Show()
    app.MainLoop()

