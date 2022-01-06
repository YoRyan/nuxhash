import logging
import os
import signal
import sys
import threading
from pathlib import Path
from subprocess import Popen

import wx
from pubsub import pub
from wx.lib.newevent import NewCommandEvent

import nuxhash.settings
from nuxhash.devices.nvidia import enumerate_devices as nvidia_devices
from nuxhash.download.downloads import make_miners
from nuxhash.gui.about import AboutScreen
from nuxhash.gui.benchmarks import BenchmarksScreen
from nuxhash.gui.mining import MiningScreen
from nuxhash.gui.settings import SettingsScreen


PADDING_PX = 10
CONFIG_DIR = nuxhash.settings.DEFAULT_CONFIGDIR
ICON_PATH = Path(os.path.dirname(__file__))/'icons'/'nuxhash.svg'

PubSubSendEvent, EVT_PUBSUB = NewCommandEvent()


class MainWindow(wx.Frame):

    def __init__(self, parent, *args, **kwargs):
        wx.Frame.__init__(self, parent, *args, **kwargs)
        self.SetIcon(wx.Icon(wx.IconLocation(str(ICON_PATH))))
        self.SetSizeHints(minW=500, minH=500)
        self._Devices = self._ProbeDevices()
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(EVT_PUBSUB, self.OnPubSend)

        # Create notebook and its pages.
        notebook = wx.Notebook(self)
        notebook.AddPage(
                MiningScreen(notebook, devices=self._Devices),
                text='Mining')
        notebook.AddPage(
                BenchmarksScreen(notebook, devices=self._Devices),
                text='Benchmarks')
        notebook.AddPage(
                SettingsScreen(notebook),
                text='Settings')
        notebook.AddPage(
                AboutScreen(notebook),
                text='About')

        # Check miner downloads.
        pub.subscribe(self._OnDownloadProgress, 'download.progress')
        self._DlThread = self._DlProgress = None
        self._DownloadMiners()

        # Read user data.
        pub.subscribe(self._OnSettings, 'data.settings')
        pub.subscribe(self._OnBenchmarks, 'data.benchmarks')

        loaded_settings = nuxhash.settings.load_settings(CONFIG_DIR)
        if loaded_settings == nuxhash.settings.DEFAULT_SETTINGS:
            self._FirstRun()
        pub.sendMessage('data.settings', settings=loaded_settings)

        benchmarks = nuxhash.settings.load_benchmarks(CONFIG_DIR, self._Devices)
        pub.sendMessage('data.benchmarks', benchmarks=benchmarks)

    def _DownloadMiners(self):
        to_download = [item for item in make_miners(CONFIG_DIR)
                       if not item.verify()]
        if len(to_download) > 0:
            self._DlThread = DownloadThread(self, to_download)
            self._DlThread.start()
            self._DlProgress = wx.ProgressDialog('nuxhash', '', parent=self)
            self._DlProgress.ShowModal()
            self._DlProgress.Destroy()

    def _FirstRun(self):
        dialog = wx.MessageDialog(
                self,
                'Welcome to nuxhash!\n\nSet your NiceHash wallet address and run '
                'some benchmarks, and then you can start mining.',
                style=wx.OK)
        dialog.ShowModal()

    def _OnDownloadProgress(self, progress, message):
        if self._DlThread:
            if progress > 0.99: # Avoid precision errors.
                self._DlProgress.Update(100.0)
                self._DlThread.join()
                self._DlThread = None
            else:
                self._DlProgress.Update(progress*100, newmsg=message)

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


class DownloadThread(threading.Thread):

    def __init__(self, frame, downloads, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self._frame = frame
        self._downloads = downloads

    def run(self):
        n_downloads = len(self._downloads)
        for i, item in enumerate(self._downloads):
            sendMessage(
                    self._frame, 'download.progress',
                    progress=i/n_downloads, message=f'Downloading {item.name}')
            item.download()
            sendMessage(
                    self._frame, 'download.progress',
                    progress=(i+1)/n_downloads, message='')


def sendMessage(window, topic, **data):
    """Like pub.sendMessage(), except safely callable by other threads."""
    wx.PostEvent(window, PubSubSendEvent(topic=topic, data=data, id=wx.ID_ANY))


def main():
    sys.excepthook = excepthook

    app = wx.App(False)
    frame = MainWindow(None, title='nuxhash')
    frame.Show()
    app.MainLoop()

def excepthook(type, value, traceback):
    sys.__excepthook__(type, value, traceback)
    # Restart the app and kill all miners.
    Popen(sys.argv, preexec_fn=os.setpgrp)
    os.killpg(os.getpgid(0), signal.SIGKILL) # (This also kills us.)

