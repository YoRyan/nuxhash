from collections import defaultdict

import wx
import wx.dataview

from nuxhash import utils
from nuxhash.devices.nvidia import NvidiaDevice
from nuxhash.gui import main
from nuxhash.miners.excavator import Excavator


NVIDIA_COLOR = (66, 244, 69)


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
        sizer.Add(self._mining, wx.SizerFlags().Border(wx.LEFT|wx.RIGHT|wx.TOP,
                                                       main.PADDING_PX)
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
        total_revenue = sum(event.revenue.values())
        self.set_revenue(total_revenue)
        self._mining.display_status(speeds=event.speeds, revenue=event.revenue,
                                    devices=event.devices)

    def OnStartStop(self, event):
        self._window.toggle_mining()


class MiningPanel(wx.ScrolledCanvas):

    def __init__(self, parent, *args, **kwargs):
        wx.ScrolledCanvas.__init__(self, parent, *args, **kwargs)
        self._sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(self._sizer)

        self._algorithms = wx.dataview.DataViewListCtrl(self)
        self._algorithms.AppendTextColumn('Algorithm')
        self._algorithms.AppendColumn(
            wx.dataview.DataViewColumn('Devices', DeviceListRenderer(),
                                       1, align=wx.ALIGN_LEFT),
            'string')
        self._algorithms.AppendTextColumn('Speed')
        self._algorithms.AppendTextColumn('Revenue')
        self._sizer.Add(self._algorithms, wx.SizerFlags().Proportion(1.0)
                                                         .Expand())

    def read_settings(self, new_settings):
        self._settings = new_settings

    def display_status(self,
                       speeds=defaultdict(lambda: [0.0]),
                       revenue=defaultdict(lambda: 0.0),
                       devices=defaultdict(lambda: [])):
        self._algorithms.DeleteAllItems()
        algorithms = list(speeds.keys())
        algorithms.sort(key=lambda algorithm: algorithm.name)
        for algorithm in algorithms:
            algo = '%s (%s)' % (algorithm.name, ', '.join(algorithm.algorithms))
            devices = ','.join([DeviceListRenderer.device_to_string(device)
                                for device in devices[algorithm]])
            speed = utils.format_speeds(speeds[algorithm])
            revenue = utils.format_balance(revenue[algorithm],
                                           self._settings['gui']['units'])
            self._algorithms.AppendItem([algo, devices, speed, revenue])


class DeviceListRenderer(wx.dataview.DataViewCustomRenderer):

    def __init__(self, *args, **kwargs):
        wx.dataview.DataViewCustomRenderer.__init__(self, *args, **kwargs)
        self.value = None

    def SetValue(self, value):
        self.value = value
        return True

    def GetValue(self):
        return self.value

    def GetSize(self):
        text = self.value.replace(',', '\n')
        return self.GetTextExtent(text)

    def Render(self, cell, dc, state):
        text = self.value.replace(',', '\n')
        self.RenderText(text, 0, cell, dc, state)
        return True

    def device_to_string(device):
        if isinstance(device, NvidiaDevice):
            name = device.name
            name = name.replace('GeForce', '')
            name = name.replace('GTX', '')
            name = name.strip()
            return 'NV:%s' % name
        else:
            raise Exception('bad device instance')

