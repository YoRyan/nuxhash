import wx

from nuxhash import utils
from nuxhash.gui import main
from nuxhash.miners.excavator import Excavator


class MiningScreen(wx.Panel):

    def __init__(self, parent, *args, devices=[], window=None, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self._devices = devices
        self._window = window
        self._settings = None
        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        sizer_flags = wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
        self.SetSizer(sizer)

        sizer.AddStretchSpacer()

        bottom_sizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        sizer.Add(bottom_sizer, sizer_flags.Expand())

        # Add balance displays.
        balances = wx.FlexGridSizer(2, 2, main.PADDING_PX)
        balances.AddGrowableCol(1)
        bottom_sizer.Add(balances, wx.SizerFlags(proportion=1.0).Expand())

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

