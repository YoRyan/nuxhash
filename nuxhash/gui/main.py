import wx

from nuxhash import settings
from nuxhash.devices.nvidia import enumerate_devices as nvidia_devices
from nuxhash.gui.mining import MiningScreen
from nuxhash.gui.settings import SettingsScreen


PADDING_PX = 10


class MainWindow(wx.Frame):

    def __init__(self, parent, *args, **kwargs):
        wx.Frame.__init__(self, parent, *args, **kwargs)
        self.SetSizeHints(minW=500, minH=500)
        self._devices = []
        self._settings = None
        self._benchmarks = None
        notebook = wx.Notebook(self)

        self._mining_screen = MiningScreen(notebook)
        notebook.AddPage(self._mining_screen, text='Mining')

        def settings_callback(new_settings):
            self.read_settings(new_settings)
            self._save_persist()
        self._settings_screen = SettingsScreen(notebook,
                                               commit_callback=settings_callback)
        notebook.AddPage(self._settings_screen, text='Settings')

        self._probe_devices()
        self._load_persist()

    def read_settings(self, new_settings):
        self._settings = new_settings
        for s in [self._settings_screen,
                  self._mining_screen]:
            s.read_settings(new_settings)

    def _probe_devices(self):
        self._devices = nvidia_devices()

    def _load_persist(self):
        nx_settings, nx_benchmarks = settings.load_persistent_data(
            settings.DEFAULT_CONFIGDIR,
            self._devices
            )
        self.read_settings(nx_settings)
        self._benchmarks = nx_benchmarks

    def _save_persist(self):
        settings.save_persistent_data(settings.DEFAULT_CONFIGDIR,
                                      self._settings, self._benchmarks)


def main():
    app = wx.App(False)
    frame = MainWindow(None, title='nuxhash')
    frame.Show()
    app.MainLoop()

