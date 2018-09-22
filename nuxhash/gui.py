import wx
from copy import deepcopy
from functools import wraps

from nuxhash import settings
from nuxhash.devices.nvidia import enumerate_devices as nvidia_devices


FIELD_BORDER = 10
REGIONS = ['eu', 'usa', 'jp', 'hk']
UNITS = ['BTC', 'mBTC']


class MainWindow(wx.Frame):

    def __init__(self, parent, *args, **kwargs):
        wx.Frame.__init__(self, parent, *args, **kwargs)
        self.SetSizeHints(minW=500, minH=500)
        self.devices = []
        self.settings = None
        self.benchmarks = None
        notebook = wx.Notebook(self)

        def settings_callback(new_settings):
            self.settings = new_settings
            self.save_persistent_data()
        self.settings_screen = SettingsScreen(notebook, commit_callback=settings_callback)
        notebook.AddPage(self.settings_screen, text='Settings')

        self.probe_devices()
        self.load_persistent_data()

    def probe_devices(self):
        self.devices = nvidia_devices()

    def load_persistent_data(self):
        nx_settings, nx_benchmarks = settings.load_persistent_data(
            settings.DEFAULT_CONFIGDIR,
            self.devices
            )
        self.settings = nx_settings
        self.benchmarks = nx_benchmarks
        self.settings_screen.read_settings(nx_settings)

    def save_persistent_data(self):
        settings.save_persistent_data(settings.DEFAULT_CONFIGDIR,
                                      self.settings, self.benchmarks)


class SettingsScreen(wx.Panel):

    def __init__(self, parent, commit_callback=lambda settings: None,
                 *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.settings = self.new_settings = None
        self.commit_callback = commit_callback

        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(sizer)
        sizer_flags = wx.SizerFlags().Border(wx.ALL, FIELD_BORDER)
        form_sizer_flags = (wx.SizerFlags().Center()
                                           .Left())

        # Add basic setting controls.
        basic_form = wx.Window(self)
        sizer.Add(basic_form, sizer_flags)
        basic_sizer = wx.FlexGridSizer(3, 2, FIELD_BORDER, FIELD_BORDER)
        basic_sizer.AddGrowableCol(1)
        basic_form.SetSizer(basic_sizer)

        basic_sizer.Add(wx.StaticText(basic_form, label='Wallet address'),
                        form_sizer_flags)
        self.wallet = wx.TextCtrl(basic_form, size=(300, -1))
        self.Bind(wx.EVT_TEXT, self.OnWalletChange, self.wallet)
        basic_sizer.Add(self.wallet, form_sizer_flags)

        basic_sizer.Add(wx.StaticText(basic_form, label='Worker name'),
                        form_sizer_flags)
        self.worker = wx.TextCtrl(basic_form, size=(150, -1))
        self.Bind(wx.EVT_TEXT, self.OnWorkerChange, self.worker)
        basic_sizer.Add(self.worker, form_sizer_flags)

        basic_sizer.Add(wx.StaticText(basic_form, label='Region'),
                        form_sizer_flags)
        self.region = ChoiceByValue(
            basic_form,
            choices=REGIONS,
            fallback_choice=settings.DEFAULT_SETTINGS['nicehash']['region']
            )
        self.Bind(wx.EVT_CHOICE, self.OnRegionChange, self.region)
        basic_sizer.Add(self.region, form_sizer_flags)

        # Add divider.
        sizer.Add(wx.StaticLine(self), wx.SizerFlags().Expand())

        # Add advanced setting controls.
        advanced_form = wx.Window(self)
        sizer.Add(advanced_form, sizer_flags)
        advanced_sizer = wx.FlexGridSizer(3, 2, FIELD_BORDER, FIELD_BORDER)
        advanced_sizer.AddGrowableCol(1)
        advanced_form.SetSizer(advanced_sizer)

        advanced_sizer.Add(
            wx.StaticText(advanced_form, label='Update interval (secs)'),
            form_sizer_flags
            )
        self.interval = wx.SpinCtrl(advanced_form, size=(125, -1),
                                    min=10, max=300, initial=60)
        self.Bind(wx.EVT_SPINCTRL, self.OnIntervalChange, self.interval)
        advanced_sizer.Add(self.interval, form_sizer_flags)

        advanced_sizer.Add(
            wx.StaticText(advanced_form, label='Profitability switch threshold (%)'),
            form_sizer_flags
            )
        self.threshold = wx.SpinCtrl(advanced_form, size=(125, -1),
                                     min=1, max=50, initial=10)
        self.Bind(wx.EVT_SPINCTRL, self.OnThresholdChange, self.threshold)
        advanced_sizer.Add(self.threshold, form_sizer_flags)

        advanced_sizer.Add(
            wx.StaticText(advanced_form, label='Display units'),
            form_sizer_flags
            )
        self.units = ChoiceByValue(
            advanced_form,
            choices=UNITS,
            fallback_choice=settings.DEFAULT_SETTINGS['gui']['units']
            )
        self.Bind(wx.EVT_CHOICE, self.OnUnitsChange, self.units)
        advanced_sizer.Add(self.units, form_sizer_flags)

        # Add spacer.
        sizer.AddStretchSpacer()

        # Add revert/save controls.
        save_form = wx.Window(self)
        sizer.Add(save_form, sizer_flags.Right())
        save_sizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        save_form.SetSizer(save_sizer)

        self.revert = wx.Button(save_form, label='Revert')
        self.Bind(wx.EVT_BUTTON, self.OnRevert, self.revert)
        save_sizer.Add(self.revert)

        save_sizer.AddSpacer(FIELD_BORDER)

        self.save = wx.Button(save_form, label='Save')
        self.Bind(wx.EVT_BUTTON, self.OnSave, self.save)
        save_sizer.Add(self.save)

    def change_event(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            self.revert.Enable()
            self.save.Enable()
            method(self, *args, **kwargs)
        return wrapper

    @change_event
    def OnWalletChange(self, event):
        self.new_settings['nicehash']['wallet'] = event.GetString()

    @change_event
    def OnWorkerChange(self, event):
        self.new_settings['nicehash']['workername'] = event.GetString()

    @change_event
    def OnRegionChange(self, event):
        self.new_settings['nicehash']['region'] = REGIONS[event.GetSelection()]

    @change_event
    def OnIntervalChange(self, event):
        self.new_settings['switching']['interval'] = event.GetPosition()

    @change_event
    def OnThresholdChange(self, event):
        self.new_settings['switching']['threshold'] = event.GetPosition()/100.0

    @change_event
    def OnUnitsChange(self, event):
        self.new_settings['gui']['units'] = UNITS[event.GetSelection()]

    def OnRevert(self, event):
        self.read_settings(self.settings)

    def OnSave(self, event):
        self.settings = deepcopy(self.new_settings)
        self.revert.Disable()
        self.save.Disable()
        self.commit_callback(self.new_settings)

    def read_settings(self, nx_settings):
        self.settings = nx_settings
        self.new_settings = deepcopy(nx_settings)
        self.revert.Disable()
        self.save.Disable()
        self.wallet.ChangeValue(nx_settings['nicehash']['wallet'])
        self.worker.ChangeValue(nx_settings['nicehash']['workername'])
        self.region.SetValue(nx_settings['nicehash']['region'])
        self.interval.SetValue(nx_settings['switching']['interval'])
        self.threshold.SetValue(nx_settings['switching']['threshold']*100)
        self.units.SetValue(nx_settings['gui']['units'])


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


def main():
    app = wx.App(False)
    frame = MainWindow(None, title='nuxhash')
    frame.Show()
    app.MainLoop()

