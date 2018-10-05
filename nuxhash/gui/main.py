import logging

import wx
from wx.lib.pubsub import pub
from wx.lib.newevent import NewCommandEvent

import nuxhash.settings
from nuxhash.devices.nvidia import enumerate_devices as nvidia_devices
from nuxhash.gui.benchmarks import BenchmarksScreen
from nuxhash.gui.mining import MiningScreen
from nuxhash.gui.settings import SettingsScreen


PADDING_PX = 10
CONFIG_DIR = nuxhash.settings.DEFAULT_CONFIGDIR

PubSubSendEvent, EVT_PUBSUB = NewCommandEvent()


class MainWindow(wx.Frame):

    def __init__(self, parent, *args, **kwargs):
        wx.Frame.__init__(self, parent, *args, **kwargs)
        self.SetSizeHints(minW=500, minH=500)
        self._Devices = self._ProbeDevices()
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(EVT_PUBSUB, self.OnPubSend)

        # Create notebook and its pages.
        notebook = wx.Notebook(self)

        self._MiningScreen = MiningScreen(
            notebook, devices=self._Devices)
        notebook.AddPage(self._MiningScreen, text='Mining')

        self._BenchmarksScreen = BenchmarksScreen(
            notebook, devices=self._Devices)
        notebook.AddPage(self._BenchmarksScreen, text='Benchmarks')

        self._SettingsScreen = SettingsScreen(notebook)
        notebook.AddPage(self._SettingsScreen, text='Settings')

        # Read user data.
        pub.sendMessage(
            'data.settings', settings=nuxhash.settings.load_settings(CONFIG_DIR))
        pub.sendMessage(
            'data.benchmarks',
            benchmarks=nuxhash.settings.load_benchmarks(CONFIG_DIR, self._Devices))
        pub.subscribe(self._OnSettings, 'data.settings')
        pub.subscribe(self._OnBenchmarks, 'data.benchmarks')

    def OnClose(self, event):
        logging.info('Closing up!')
        pub.sendMessage('app.close')
        event.Skip()

    def OnPubSend(self, event):
        pub.sendMessage(event.topic, **event.data)

    def _OnSettings(self, settings):
        logging.info('Saving user settings.')
        nuxhash.settings.save_settings(CONFIG_DIR, settings)

    def _OnBenchmarks(self, benchmarks):
        logging.info('Saving user benchmarks.')
        nuxhash.settings.save_benchmarks(CONFIG_DIR, benchmarks)

    def _ProbeDevices(self):
        return nvidia_devices()


def sendMessage(window, topic, **data):
    """Like pub.sendMessage(), except safely callable by other threads."""
    wx.PostEvent(window, PubSubSendEvent(topic=topic, data=data, id=wx.ID_ANY))


def main():
    app = wx.App(False)
    frame = MainWindow(None, title='nuxhash')
    frame.Show()
    app.MainLoop()

