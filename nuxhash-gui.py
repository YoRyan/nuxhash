#!/usr/bin/env python2

import devices.nvidia
import settings

import wx
from copy import deepcopy
from functools import wraps

FIELD_BORDER = 10
REGIONS = ['eu', 'usa', 'jp', 'hk']
UNITS = ['BTC', 'mBTC']

class MainWindow(wx.Frame):
    def __init__(self, parent, *args, **kwargs):
        wx.Frame.__init__(self, parent, *args, **kwargs)

        self.devices = []
        self.settings = None
        self.benchmarks = None

        notebook = wx.Notebook(self)

        def settings_callback(new_settings):
            self.settings = new_settings
            self.save_persistent_data()
        self.settings_screen = SettingsScreen(notebook, commit_callback=settings_callback)
        notebook.AddPage(self.settings_screen, text='Settings')

        self.SetSizeHints(minW=500, minH=500)

        self.probe_devices()
        self.load_persistent_data()

    def probe_devices(self):
        nvidia_devices = devices.nvidia.enumerate_devices()
        self.devices = nvidia_devices

    def load_persistent_data(self):
        nx_settings, nx_benchmarks = settings.load_persistent_data(settings.DEFAULT_CONFIGDIR,
                                                                   self.devices)

        self.settings = nx_settings
        self.benchmarks = nx_benchmarks

        self.settings_screen.read_settings(nx_settings)

    def save_persistent_data(self):
        settings.save_persistent_data(settings.DEFAULT_CONFIGDIR,
                                      self.settings, self.benchmarks)

class SettingsScreen(wx.Panel):
    def __init__(self, parent, commit_callback=lambda settings: None, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.settings = self.new_settings = None
        self.commit_callback = commit_callback

        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        sizer_flags = wx.SizerFlags().Border(wx.ALL, FIELD_BORDER)

        # basic settings
        self.create_basic_form()
        sizer.AddF(self.basic_form, sizer_flags)

        # divider
        sizer.AddF(wx.StaticLine(self), wx.SizerFlags().Expand())

        # advanced settings
        self.create_advanced_form()
        sizer.AddF(self.advanced_form, sizer_flags)

        # spacer
        sizer.AddStretchSpacer()

        # io controls
        self.create_io_controls()
        sizer.AddF(self.io_controls, sizer_flags.Right())

        self.SetSizer(sizer)

    def create_basic_form(self):
        wrapper = wx.Window(self)
        self.basic_form = wrapper

        sizer = wx.FlexGridSizer(3, 2, FIELD_BORDER, FIELD_BORDER)
        sizer.AddGrowableCol(1)
        wrapper.SetSizer(sizer)
        sizer_flags = (wx.SizerFlags().Center()
                                      .Left())

        # wallet address
        sizer.AddF(wx.StaticText(wrapper, label='Wallet address'), sizer_flags)
        self.wallet = wx.TextCtrl(wrapper, size=(300, -1))
        sizer.AddF(self.wallet, sizer_flags)
        self.Bind(wx.EVT_TEXT, self.OnWalletChange, self.wallet)

        # worker name
        sizer.AddF(wx.StaticText(wrapper, label='Worker name'), sizer_flags)
        self.worker = wx.TextCtrl(wrapper, size=(150, -1))
        sizer.AddF(self.worker, sizer_flags)
        self.Bind(wx.EVT_TEXT, self.OnWorkerChange, self.worker)

        # nicehash region
        sizer.AddF(wx.StaticText(wrapper, label='Region'), sizer_flags)
        self.region = wx.Choice(wrapper, choices=REGIONS)
        sizer.AddF(self.region, sizer_flags)
        self.Bind(wx.EVT_CHOICE, self.OnRegionChange, self.region)

    def create_advanced_form(self):
        wrapper = wx.Window(self)
        self.advanced_form = wrapper

        sizer = wx.FlexGridSizer(3, 2, FIELD_BORDER, FIELD_BORDER)
        sizer.AddGrowableCol(1)
        wrapper.SetSizer(sizer)
        sizer_flags = (wx.SizerFlags().Center()
                                      .Left())

        # switch interval
        sizer.AddF(wx.StaticText(wrapper, label='Update interval (secs)'), sizer_flags)
        self.interval = wx.SpinCtrl(wrapper, size=(125, -1),
                                    min=10, max=300, initial=60)
        sizer.AddF(self.interval, sizer_flags)
        self.Bind(wx.EVT_SPINCTRL, self.OnIntervalChange, self.interval)

        # switch threshold
        sizer.AddF(wx.StaticText(wrapper, label='Profitability switch threshold (%)'),
                   sizer_flags)
        self.threshold = wx.SpinCtrl(wrapper, size=(125, -1),
                                     min=1, max=50, initial=10)
        sizer.AddF(self.threshold, sizer_flags)
        self.Bind(wx.EVT_SPINCTRL, self.OnThresholdChange, self.threshold)

        # units
        sizer.AddF(wx.StaticText(wrapper, label='Display units'), sizer_flags)
        self.units = wx.Choice(wrapper, choices=UNITS)
        sizer.AddF(self.units, sizer_flags)
        self.Bind(wx.EVT_CHOICE, self.OnUnitsChange, self.units)

    def create_io_controls(self):
        self.io_controls = wx.Window(self)

        sizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        self.io_controls.SetSizer(sizer)

        # revert button
        self.revert = wx.Button(self.io_controls, label='Revert')
        sizer.Add(self.revert)
        self.Bind(wx.EVT_BUTTON, self.OnRevert, self.revert)

        # spacer
        sizer.AddSpacer(FIELD_BORDER)

        # save button
        self.save = wx.Button(self.io_controls, label='Save')
        sizer.Add(self.save)
        self.Bind(wx.EVT_BUTTON, self.OnSave, self.save)

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

        wallet = nx_settings['nicehash']['wallet']
        self.wallet.ChangeValue(wallet)

        worker = nx_settings['nicehash']['workername']
        self.worker.ChangeValue(worker)

        region = nx_settings['nicehash']['region']
        default_region = settings.DEFAULT_SETTINGS['nicehash']['region']
        set_choice(self.region, REGIONS, region, fallback=default_region)

        interval = nx_settings['switching']['interval']
        self.interval.SetValue(interval)

        threshold = nx_settings['switching']['threshold']
        self.threshold.SetValue(threshold*100)

        units = nx_settings['gui']['units']
        default_units = settings.DEFAULT_SETTINGS['gui']['units']
        set_choice(self.units, UNITS, units, fallback=default_units)

def set_choice(wx_choice, options, value, fallback=None):
    if value in options:
        wx_choice.SetSelection(options.index(value))
    elif fallback is not None:
        wx_choice.SetSelection(options.index(fallback))
    else:
        wx_choice.SetSelection(0)

if __name__ == '__main__':
    app = wx.App(False)
    frame = MainWindow(None, title='nuxhash')
    frame.Show()
    app.MainLoop()

