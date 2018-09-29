from copy import deepcopy
from functools import wraps

import wx

from nuxhash import settings
from nuxhash.gui import main


REGIONS = ['eu', 'usa', 'jp', 'hk']
UNITS = ['BTC', 'mBTC']


class SettingsScreen(wx.Panel):

    def __init__(self, parent, commit_callback=lambda settings: None,
                 *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self._settings = self.new_settings = None
        self._commit_callback = commit_callback

        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(sizer)

        # Add basic setting controls.
        basic_form = wx.Window(self)
        sizer.Add(basic_form, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
                                             .Expand())
        basic_sizer = wx.FlexGridSizer(3, 2, main.PADDING_PX, main.PADDING_PX)
        basic_sizer.AddGrowableCol(1)
        basic_form.SetSizer(basic_sizer)

        basic_sizer.Add(wx.StaticText(basic_form, label='Wallet address'),
                        wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL))
        self._wallet = wx.TextCtrl(basic_form, size=(-1, -1))
        self.Bind(wx.EVT_TEXT, self.OnWalletChange, self._wallet)
        basic_sizer.Add(self._wallet,
                        wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL).Expand())

        basic_sizer.Add(wx.StaticText(basic_form, label='Worker name'),
                        wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL))
        self._worker = wx.TextCtrl(basic_form, size=(200, -1))
        self.Bind(wx.EVT_TEXT, self.OnWorkerChange, self._worker)
        basic_sizer.Add(self._worker,
                        wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL))

        basic_sizer.Add(wx.StaticText(basic_form, label='Region'),
                        wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL))
        self._region = ChoiceByValue(
            basic_form, choices=REGIONS,
            fallback_choice=settings.DEFAULT_SETTINGS['nicehash']['region'])
        self.Bind(wx.EVT_CHOICE, self.OnRegionChange, self._region)
        basic_sizer.Add(self._region, wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL))

        # Add divider.
        sizer.Add(wx.StaticLine(self), wx.SizerFlags().Expand())

        # Add advanced setting controls.
        advanced_form = wx.Window(self)
        sizer.Add(advanced_form, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
                                                .Expand())
        advanced_sizer = wx.FlexGridSizer(3, 2, main.PADDING_PX, main.PADDING_PX)
        advanced_sizer.AddGrowableCol(1)
        advanced_form.SetSizer(advanced_sizer)

        advanced_sizer.Add(
            wx.StaticText(advanced_form, label='Update interval (secs)'),
            wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL))
        self._interval = wx.SpinCtrl(advanced_form, size=(125, -1),
                                     min=10, max=300, initial=60)
        self.Bind(wx.EVT_SPINCTRL, self.OnIntervalChange, self._interval)
        advanced_sizer.Add(self._interval,
                           wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL))

        advanced_sizer.Add(
            wx.StaticText(advanced_form, label='Profitability switch threshold (%)'),
            wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL))
        self._threshold = wx.SpinCtrl(advanced_form, size=(125, -1),
                                      min=1, max=50, initial=10)
        self.Bind(wx.EVT_SPINCTRL, self.OnThresholdChange, self._threshold)
        advanced_sizer.Add(self._threshold,
                           wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL))

        advanced_sizer.Add(
            wx.StaticText(advanced_form, label='Display units'),
            wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL))
        self._units = ChoiceByValue(
            advanced_form, choices=UNITS,
            fallback_choice=settings.DEFAULT_SETTINGS['gui']['units'])
        self.Bind(wx.EVT_CHOICE, self.OnUnitsChange, self._units)
        advanced_sizer.Add(self._units,
                           wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL))

        # Add spacer.
        sizer.AddStretchSpacer()

        # Add revert/save controls.
        save_form = wx.Window(self)
        sizer.Add(save_form, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
                                            .Right())
        save_sizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        save_form.SetSizer(save_sizer)

        self._revert = wx.Button(save_form, id=wx.ID_REVERT_TO_SAVED)
        self.Bind(wx.EVT_BUTTON, self.OnRevert, self._revert)
        save_sizer.Add(self._revert)

        save_sizer.AddSpacer(main.PADDING_PX)

        self._save = wx.Button(save_form, id=wx.ID_APPLY)
        self.Bind(wx.EVT_BUTTON, self.OnSave, self._save)
        save_sizer.Add(self._save)

    def change_event(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            self._revert.Enable()
            self._save.Enable()
            method(self, *args, **kwargs)
        return wrapper

    @change_event
    def OnWalletChange(self, event):
        self._new_settings['nicehash']['wallet'] = event.GetString()

    @change_event
    def OnWorkerChange(self, event):
        self._new_settings['nicehash']['workername'] = event.GetString()

    @change_event
    def OnRegionChange(self, event):
        self._new_settings['nicehash']['region'] = REGIONS[event.GetSelection()]

    @change_event
    def OnIntervalChange(self, event):
        self._new_settings['switching']['interval'] = event.GetPosition()

    @change_event
    def OnThresholdChange(self, event):
        self._new_settings['switching']['threshold'] = event.GetPosition()/100.0

    @change_event
    def OnUnitsChange(self, event):
        self._new_settings['gui']['units'] = UNITS[event.GetSelection()]

    def OnRevert(self, event):
        self.read_settings(self._settings)

    def OnSave(self, event):
        self._settings = deepcopy(self._new_settings)
        self._revert.Disable()
        self._save.Disable()
        self._commit_callback(self._new_settings)

    def read_settings(self, nx_settings):
        self._settings = nx_settings
        self._new_settings = deepcopy(nx_settings)
        self._revert.Disable()
        self._save.Disable()
        self._wallet.ChangeValue(nx_settings['nicehash']['wallet'])
        self._worker.ChangeValue(nx_settings['nicehash']['workername'])
        self._region.SetValue(nx_settings['nicehash']['region'])
        self._interval.SetValue(nx_settings['switching']['interval'])
        self._threshold.SetValue(nx_settings['switching']['threshold']*100)
        self._units.SetValue(nx_settings['gui']['units'])


class ChoiceByValue(wx.Choice):

    def __init__(self, *args, choices=[], fallback_choice='', **kwargs):
        wx.Choice.__init__(self, *args, choices=choices, **kwargs)
        self._choices = choices
        self._fallback = fallback_choice

    def SetValue(self, value):
        if value in self._choices:
            wx.Choice.SetSelection(self, self._choices.index(value))
        else:
            wx.Choice.SetSelection(self, self._choices.index(self._fallback))

