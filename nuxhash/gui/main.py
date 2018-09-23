import threading

import wx
from wx.lib.newevent import NewEvent

from nuxhash import settings
from nuxhash.devices.nvidia import enumerate_devices as nvidia_devices
from nuxhash.gui.mining import MiningScreen
from nuxhash.gui.settings import SettingsScreen
from nuxhash.nicehash import unpaid_balance, simplemultialgo_info


PADDING_PX = 10
BALANCE_UPDATE_MIN = 5

NewBalanceEvent, EVT_BALANCE = NewEvent()


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

        self.Bind(EVT_BALANCE, self.OnNewBalance)
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda event: self._update_balance(), self._timer)
        self._timer.Start(milliseconds=BALANCE_UPDATE_MIN*60*1e3)

        self._probe_devices()
        self._load_persist()

    def read_settings(self, new_settings):
        self._settings = new_settings
        for s in [self._settings_screen,
                  self._mining_screen]:
            s.read_settings(new_settings)
        self._update_balance()

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

    def _update_balance(self):
        thread = GetBalanceThread(self, self._settings['nicehash']['wallet'])
        thread.start()

    def OnNewBalance(self, event):
        self._mining_screen.set_balance(event.balance)


class GetBalanceThread(threading.Thread):

    def __init__(self, window, address):
        threading.Thread.__init__(self)
        self._window = window
        self._address = address

    def run(self):
        balance = unpaid_balance(self._address)
        wx.PostEvent(self._window, NewBalanceEvent(balance=balance))


def main():
    app = wx.App(False)
    frame = MainWindow(None, title='nuxhash')
    frame.Show()
    app.MainLoop()

