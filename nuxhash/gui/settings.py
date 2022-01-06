from copy import deepcopy
from functools import wraps

import wx
from pubsub import pub
from wx.lib.agw.hyperlink import HyperLinkCtrl

from nuxhash import settings
from nuxhash.bitcoin import check_bc
from nuxhash.gui import main
from nuxhash.settings import DEFAULT_SETTINGS


REGIONS = ['eu', 'usa', 'jp', 'hk']
UNITS = ['BTC', 'mBTC']
INVALID_COLOR = 'PINK'


class SettingsScreen(wx.Panel):

    def __init__(self, parent, *args, frame=None, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self._Settings = None
        pub.subscribe(self._OnSettings, 'data.settings')

        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(sizer)

        def add_divider(sizer):
            sizer.Add(wx.StaticLine(self), wx.SizerFlags().Expand())

        def add_valign(sizer, window, sizerflags=wx.SizerFlags()):
            sizer.Add(window, sizerflags.Align(wx.ALIGN_CENTER_VERTICAL))

        def two_col_sizer(rows):
            sizer = wx.FlexGridSizer(rows, 2, main.PADDING_PX, main.PADDING_PX)
            sizer.AddGrowableCol(1)
            return sizer

        # Add basic setting controls.
        basicForm = wx.Window(self)
        sizer.Add(basicForm, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
                                            .Expand())
        basicSizer = two_col_sizer(3)
        basicForm.SetSizer(basicSizer)

        add_valign(basicSizer, wx.StaticText(basicForm, label='Wallet address'))
        self._Wallet = AddressCtrl(basicForm, size=(-1, -1))
        self.Bind(wx.EVT_TEXT, self.OnControlChange, self._Wallet)
        add_valign(basicSizer, self._Wallet, wx.SizerFlags().Expand())

        add_valign(basicSizer, wx.StaticText(basicForm, label='Worker name'))
        self._Worker = wx.TextCtrl(basicForm, size=(200, -1))
        self.Bind(wx.EVT_TEXT, self.OnControlChange, self._Worker)
        add_valign(basicSizer, self._Worker)

        add_valign(basicSizer, wx.StaticText(basicForm, label='Region'))
        self._Region = ChoiceByValue(
                basicForm, choices=REGIONS,
                fallbackChoice=settings.DEFAULT_SETTINGS['nicehash']['region'])
        self.Bind(wx.EVT_CHOICE, self.OnControlChange, self._Region)
        add_valign(basicSizer, self._Region)

        # Add API key controls.
        apiCollapsible = wx.CollapsiblePane(
                self, label='API Keys', style=wx.CP_NO_TLW_RESIZE)
        self.Bind(
                wx.EVT_COLLAPSIBLEPANE_CHANGED, self.OnPaneChange, apiCollapsible)
        sizer.Add(apiCollapsible, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
                                                 .Expand())
        apiPane = apiCollapsible.GetPane()
        apiPaneSizer = wx.BoxSizer(orient=wx.VERTICAL)
        apiPane.SetSizer(apiPaneSizer)
        apiForm = wx.Window(apiPane)
        apiPaneSizer.Add(apiForm, wx.SizerFlags().Expand())
        apiFormSizer = two_col_sizer(3)
        apiForm.SetSizer(apiFormSizer)

        add_valign(apiFormSizer, wx.StaticText(apiForm, label='Organization ID'))
        self._Organization = wx.TextCtrl(apiForm, size=(-1, -1))
        self.Bind(wx.EVT_TEXT, self.OnControlChange, self._Organization)
        add_valign(apiFormSizer, self._Organization, wx.SizerFlags().Expand())

        add_valign(apiFormSizer, wx.StaticText(apiForm, label='API Key Code'))
        self._ApiKey = wx.TextCtrl(
                apiForm, size=(-1, -1), style=wx.TE_PASSWORD)
        self.Bind(wx.EVT_TEXT, self.OnControlChange, self._ApiKey)
        add_valign(apiFormSizer, self._ApiKey, wx.SizerFlags().Expand())

        add_valign(apiFormSizer,
                   wx.StaticText(apiForm, label='API Secret Key Code'))
        self._ApiSecret = wx.TextCtrl(
                apiForm, size=(-1, -1), style=wx.TE_PASSWORD)
        self.Bind(wx.EVT_TEXT, self.OnControlChange, self._ApiSecret)
        add_valign(apiFormSizer, self._ApiSecret, wx.SizerFlags().Expand())

        apiPaneSizer.AddSpacer(main.PADDING_PX)

        apiLink = HyperLinkCtrl(
                apiPane, label='(Get keys here)',
                URL='https://www.nicehash.com/my/settings/keys')
        apiPaneSizer.Add(apiLink, wx.SizerFlags().Expand())

        add_divider(sizer)

        # Add advanced setting controls.
        advancedForm = wx.Window(self)
        sizer.Add(advancedForm, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
                                               .Expand())
        advancedSizer = two_col_sizer(3)
        advancedForm.SetSizer(advancedSizer)

        add_valign(advancedSizer,
                   wx.StaticText(advancedForm, label='Update interval (secs)'))
        self._Interval = wx.SpinCtrl(advancedForm, size=(125, -1),
                                     min=10, max=300, initial=60)
        self.Bind(wx.EVT_SPINCTRL, self.OnControlChange, self._Interval)
        add_valign(advancedSizer, self._Interval)

        add_valign(advancedSizer,
                   wx.StaticText(advancedForm,
                                 label='Profitability switch threshold (%)'))
        self._Threshold = wx.SpinCtrl(advancedForm, size=(125, -1),
                                      min=1, max=50, initial=10)
        self.Bind(wx.EVT_SPINCTRL, self.OnControlChange, self._Threshold)
        add_valign(advancedSizer, self._Threshold)

        add_valign(advancedSizer,
                   wx.StaticText(advancedForm, label='Display units'))
        self._Units = ChoiceByValue(
                advancedForm, choices=UNITS,
                fallbackChoice=settings.DEFAULT_SETTINGS['gui']['units'])
        self.Bind(wx.EVT_CHOICE, self.OnControlChange, self._Units)
        add_valign(advancedSizer, self._Units)

        sizer.AddStretchSpacer()

        # Add revert/save controls.
        saveForm = wx.Window(self)
        sizer.Add(saveForm, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
                                           .Right())
        saveSizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        saveForm.SetSizer(saveSizer)

        self._Revert = wx.Button(saveForm, id=wx.ID_REVERT_TO_SAVED)
        self.Bind(wx.EVT_BUTTON, self.OnRevert, self._Revert)
        saveSizer.Add(self._Revert)

        saveSizer.AddSpacer(main.PADDING_PX)

        self._Save = wx.Button(saveForm, id=wx.ID_APPLY)
        self.Bind(wx.EVT_BUTTON, self.OnSave, self._Save)
        saveSizer.Add(self._Save)

    def _OnSettings(self, settings):
        if settings != self._Settings:
            self._Settings = settings
            self._Reset()

    def OnControlChange(self, event):
        self._Revert.Enable()
        self._Save.Enable()

    def OnPaneChange(self, event):
        self.Layout()

    def OnRevert(self, event):
        self._Reset()

    def OnSave(self, event):
        new_settings = deepcopy(self._Settings)
        new_settings['nicehash']['wallet'] = self._Wallet.GetValue()
        new_settings['nicehash']['workername'] = self._Worker.GetValue()
        new_settings['nicehash']['region'] = REGIONS[self._Region.GetSelection()]
        new_settings['nicehash']['api_organization'] = \
                self._Organization.GetValue()
        new_settings['nicehash']['api_key'] = self._ApiKey.GetValue()
        new_settings['nicehash']['api_secret'] = self._ApiSecret.GetValue()
        new_settings['switching']['interval'] = self._Interval.GetValue()
        new_settings['switching']['threshold'] = self._Threshold.GetValue()/100.0
        new_settings['gui']['units'] = UNITS[self._Units.GetSelection()]
        pub.sendMessage('data.settings', settings=new_settings)

        self._Revert.Disable()
        self._Save.Disable()

    def _Reset(self):
        self._Wallet.SetValue(self._Settings['nicehash']['wallet'])
        self._Worker.SetValue(self._Settings['nicehash']['workername'])
        self._Region.SetValue(self._Settings['nicehash']['region'])
        self._Organization.SetValue(self._Settings['nicehash']['api_organization'])
        self._ApiKey.SetValue(self._Settings['nicehash']['api_key'])
        self._ApiSecret.SetValue(self._Settings['nicehash']['api_secret'])
        self._Interval.SetValue(self._Settings['switching']['interval'])
        self._Threshold.SetValue(self._Settings['switching']['threshold']*100)
        self._Units.SetValue(self._Settings['gui']['units'])
        self._Revert.Disable()
        self._Save.Disable()


class ChoiceByValue(wx.Choice):

    def __init__(self, *args, choices=[], fallbackChoice='', **kwargs):
        wx.Choice.__init__(self, *args, choices=choices, **kwargs)
        self._Choices = choices
        self._Fallback = fallbackChoice

    def SetValue(self, value):
        if value in self._Choices:
            wx.Choice.SetSelection(self, self._Choices.index(value))
        else:
            wx.Choice.SetSelection(self, self._Choices.index(self._Fallback))


class AddressCtrl(wx.TextCtrl):

    def __init__(self, parent, *args, **kwargs):
        wx.StaticText.__init__(self, parent, *args, **kwargs)
        self.Bind(wx.EVT_TEXT, self._OnSetValue)

    def _OnSetValue(self, event):
        if not check_bc(self.GetValue()):
            self.SetBackgroundColour(INVALID_COLOR)
        else:
            self.SetBackgroundColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
        event.Skip()

