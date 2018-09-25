from collections import defaultdict

import wx

from nuxhash import utils
from nuxhash.devices.nvidia import NvidiaDevice
from nuxhash.gui import main
from nuxhash.miners.excavator import Excavator


class MiningScreen(wx.Panel):

    def __init__(self, parent, *args, devices=[], window=None, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self._devices = devices
        self._window = window
        self._settings = None
        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(sizer)

        # Add mining panel.
        self._mining = MiningPanel(self)
        sizer.Add(self._mining, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
                                               .Proportion(1.0)
                                               .Expand())

        bottom_sizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        sizer.Add(bottom_sizer, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
                                               .Expand())

        # Add balance displays.
        balances = wx.FlexGridSizer(2, 2, main.PADDING_PX)
        balances.AddGrowableCol(1)
        bottom_sizer.Add(balances, wx.SizerFlags().Proportion(1.0).Expand())

        balances.Add(wx.StaticText(self, label='Daily revenue'))
        self._revenue = wx.StaticText(self,
                                      style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
        self._revenue.SetFont(self.GetFont().Bold())
        balances.Add(self._revenue, wx.SizerFlags().Expand())

        balances.Add(wx.StaticText(self, label='Address balance'))
        self._balance = wx.StaticText(self,
                                      style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
        self._balance.SetFont(self.GetFont().Bold())
        balances.Add(self._balance, wx.SizerFlags().Expand())

        bottom_sizer.AddSpacer(main.PADDING_PX)

        # Add start/stop button.
        self._startstop = wx.Button(self, label='Start Mining')
        bottom_sizer.Add(self._startstop, wx.SizerFlags().Expand()
                                                         .Center())
        self.Bind(wx.EVT_BUTTON, self.OnStartStop, self._startstop)

    def read_settings(self, new_settings):
        self._settings = new_settings
        self._mining.read_settings(new_settings)

    def start_mining(self):
        self._startstop.SetLabel('Stop Mining')

    def stop_mining(self):
        self._startstop.SetLabel('Start Mining')

    def set_revenue(self, v):
        unit = self._settings['gui']['units']
        self._revenue.SetLabel(utils.format_balance(v, unit))

    def set_balance(self, v):
        unit = self._settings['gui']['units']
        self._balance.SetLabel(utils.format_balance(v, unit))

    def set_mining(self, event):
        daily_revenue = sum([event.mbtc_per_day_per_hash[device][algorithm]
                             for device, algorithm in event.assignments.items()])
        self.set_revenue(daily_revenue)

    def OnStartStop(self, event):
        self._window.toggle_mining()


class MiningPanel(wx.ScrolledCanvas):

    def __init__(self, parent, *args, **kwargs):
        wx.ScrolledCanvas.__init__(self, parent, *args, **kwargs)
        self._sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(self._sizer)

        legend_row = wx.BoxSizer(orient=wx.HORIZONTAL)
        self._sizer.Add(legend_row, wx.SizerFlags().Expand())
        legend_row.Add(wx.StaticText(self, label='Algorithm'),
                       wx.SizerFlags().Proportion(2.0))
        legend_row.Add(wx.StaticText(self, label='Speed'),
                       wx.SizerFlags().Proportion(1.0))
        legend_row.Add(wx.StaticText(self, label='Revenue'),
                       wx.SizerFlags().Proportion(1.0))

        self._algorithms = wx.BoxSizer(orient=wx.VERTICAL)
        self._sizer.Add(self._algorithms, wx.SizerFlags().Expand())

    def read_settings(self, new_settings):
        self._settings = new_settings

    def display_status(self, algorithms,
                       speeds=defaultdict(lambda: [0.0]),
                       revenue=defaultdict(lambda: 0.0),
                       devices=defaultdict(lambda: [])):
        self._algorithms.DeleteWindows()
        for algorithm in sort(algorithms, key=lambda a: a.name):
            data_row = wx.BoxSizer(orient=wx.HORIZONTAL)
            self._algorithms.Add(data_row, wx.SizerFlags().Expand())
            data_row.Add(
                wx.StaticText(
                    self,
                    label='%s (%s)' % (self.name, ', '.join(self.algorithms))),
                wx.SizerFlags().Proportion(2.0))
            data_row.Add(
                wx.StaticText(self, label=utils.format_speeds(speeds[algorithm])),
                wx.SizerFlags().Proportion(1.0))
            data_row.Add(
                wx.StaticText(
                    self,
                    label=utils.format_balance(revenues[algorithm],
                                               self._settings['gui']['units'])),
                wx.SizerFlags().Proportion(1.0))

            devices_row = wx.BoxSizer(orient=wx.VERTICAL)
            self._algorithms.Add(devices_row, wx.SizerFlags.Expand())
            for device in devices[algorithms]:
                text = wx.StaticText(self, label=device.name)
                if isinstance(device, NvidiaDevice):
                    text.SetBackgroundColor((66, 244, 69))
                devices_row.Add(
                    text, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX))

