import wx
import wx.dataview
from wx.lib.newevent import NewCommandEvent
from wx.lib.scrolledpanel import ScrolledPanel

from nuxhash import utils
from nuxhash.devices.nvidia import NvidiaDevice
from nuxhash.gui import main
from nuxhash.miners import all_miners
from nuxhash.settings import DEFAULT_SETTINGS, EMPTY_BENCHMARKS


BenchmarksUpdateEvent, EVT_NEW_BENCHMARKS = NewCommandEvent()


class BenchmarksScreen(wx.Panel):

    def __init__(self, parent, *args, devices=[], **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self._devices = devices
        self._settings = DEFAULT_SETTINGS
        self._benchmarks = EMPTY_BENCHMARKS
        # dict of (device, algorithm) -> Runnable
        self._runnables = {}
        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(sizer)

        # Create inner scrolled area.
        inner_window = ScrolledPanel(self)
        inner_window.SetupScrolling()
        sizer.Add(inner_window, wx.SizerFlags().Border(wx.LEFT|wx.RIGHT|wx.TOP,
                                                       main.PADDING_PX)
                                               .Proportion(1.0)
                                               .Expand())
        inner_sizer = wx.BoxSizer(orient=wx.VERTICAL)
        inner_window.SetSizer(inner_sizer)

        # Populate it with a collapsible panel for each device.
        self._device_pane = {}
        for device in self._devices:
            device_cp = wx.CollapsiblePane(
                inner_window, label=('%s\n%s' % (device.name, device.uuid)))
            self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.OnPaneChanged,
                      device_cp)
            inner_sizer.Add(device_cp, wx.SizerFlags().Expand())
            self._device_pane[device] = device_cp.GetPane()

        bottom_sizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        sizer.Add(bottom_sizer, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
                                               .Expand())

        # Create bottom controls.
        select_todo = wx.Button(self, label='Unmeasured')
        self.Bind(wx.EVT_BUTTON, self.OnSelectUnmeasured, select_todo)
        bottom_sizer.Add(select_todo)

        bottom_sizer.AddSpacer(main.PADDING_PX)

        select_none = wx.Button(self, label='None')
        self.Bind(wx.EVT_BUTTON, self.OnSelectNone, select_none)
        bottom_sizer.Add(select_none)

        bottom_sizer.AddStretchSpacer()

        bottom_sizer.AddSpacer(main.PADDING_PX)
        benchmark = wx.Button(self, label='Benchmark')
        bottom_sizer.Add(benchmark)

    @property
    def benchmarks(self):
        return self._benchmarks
    @benchmarks.setter
    def benchmarks(self, value):
        self._benchmarks = value
        self._repopulate()

    @property
    def settings(self):
        return self._settings
    @settings.setter
    def settings(self, value):
        self._settings = value
        self._repopulate()

    def _repopulate(self):
        miners = [miner(main.CONFIG_DIR, self._settings) for miner in all_miners]
        all_algorithms = sum([miner.algorithms for miner in miners], [])
        self._runnables = {}
        for device in self._devices:
            pane = self._device_pane[device]
            old_sizer = pane.GetSizer()
            if old_sizer:
                old_sizer.Clear(True)

            algorithms = [algorithm for algorithm in all_algorithms
                          if algorithm.accepts(device)]
            sizer = wx.FlexGridSizer(len(algorithms), 3, wx.Size(0, 0))
            pane.SetSizer(sizer, deleteOld=True)
            sizer.AddGrowableCol(1)
            for algorithm in algorithms:
                runnable = Runnable(pane, algorithm)
                sizer.Add(runnable.checkbox)
                sizer.Add(runnable.label)
                sizer.Add(runnable.speeds)
                self._runnables[(device, algorithm)] = runnable

                benchmarks = self._benchmarks[device]
                if algorithm.name in benchmarks:
                    runnable.set_speeds(benchmarks[algorithm.name])
        self.Layout()


    def OnSelectUnmeasured(self, event):
        self._set_selection(
            [(device, algorithm) for (device, algorithm) in self._runnables.keys()
             if algorithm.name not in self._benchmarks[device]])

    def OnSelectNone(self, event):
        self._set_selection([])

    def _set_selection(self, selection):
        for (device, algorithm) in self._runnables.keys():
            runnable = self._runnables[(device, algorithm)]
            if (device, algorithm) in selection:
                runnable.select()
            else:
                runnable.deselect()

    def _get_selection(self):
        return [(device, algorithm) for ((device, algorithm), runnable)
                in self._runnables.items() if runnable.is_selected()]

    def OnPaneChanged(self, event):
        self.Layout()


class Runnable(object):

    def __init__(self, parent, algorithm):
        self.checkbox = wx.CheckBox(parent)
        self.label = wx.StaticText(parent, label=algorithm.name)
        self.speeds = SpeedCtrl(parent)
        self.set_speeds([0.0]*len(algorithm.algorithms))

    def set_speeds(self, values):
        self.speeds.set_speeds(values)

    def is_selected(self):
        return self.checkbox.GetValue()

    def select(self):
        self.checkbox.SetValue(True)

    def deselect(self):
        self.checkbox.SetValue(False)


class SpeedCtrl(wx.TextCtrl):

    def __init__(self, parent, *args, **kwargs):
        wx.StaticText.__init__(self, parent, *args,
                               style=wx.BORDER_NONE|wx.TE_CENTRE,
                               size=(150, 20), **kwargs)

    def set_speeds(self, values):
        if all(speed == 0.0 for speed in values):
            s = '--'
        else:
            s = '; '.join(utils.format_speed(speed).strip() for speed in values)
        self.SetValue(s)

