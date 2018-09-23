import wx

from nuxhash import utils
from nuxhash.gui import main
from nuxhash.nicehash import unpaid_balance, simplemultialgo_info


class MiningScreen(wx.Panel):

    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self._settings = None
        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        sizer_flags = wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
        self.SetSizer(sizer)

        sizer.AddStretchSpacer()

        # Add balance displays.
        balances = wx.FlexGridSizer(2, 2, main.PADDING_PX, main.PADDING_PX)
        balances.AddGrowableCol(1)
        sizer.Add(balances, sizer_flags.Expand())

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

    def read_settings(self, new_settings):
        self._settings = new_settings
        # TODO
        self.set_balance(unpaid_balance(self._settings['nicehash']['wallet']))

    def set_revenue(self, v):
        unit = self._settings['gui']['units']
        self._revenue.SetLabel(utils.format_balance(v, unit))

    def set_balance(self, v):
        unit = self._settings['gui']['units']
        self._balance.SetLabel(utils.format_balance(v, unit))

