import re
import threading

import wx
import wx.dataview
from wx.lib.newevent import NewCommandEvent, NewEvent
from wx.lib.scrolledpanel import ScrolledPanel

from nuxhash import utils
from nuxhash.devices.nvidia import NvidiaDevice
from nuxhash.gui import main
from nuxhash.miners import all_miners
from nuxhash.settings import DEFAULT_SETTINGS


BENCHMARK_SECS = 60

StatusEvent, EVT_STATUS = NewEvent()
SetEvent, EVT_SET_VALUE = NewCommandEvent()
DeleteEvent, EVT_CLEAR_VALUE = NewCommandEvent()
DoneEvent, EVT_COMPLETE = NewEvent()
InputSpeedsEvent, EVT_SPEEDS = NewCommandEvent()


class BenchmarksScreen(wx.Panel):

    def __init__(self, parent, *args, devices=[], frame=None, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self._Devices = devices
        self._Frame = frame
        # dict of (device, algorithm) -> Item
        self._Items = {}
        self._Thread = None

        self.Bind(main.EVT_SETTINGS, self.OnNewSettings)
        self.Bind(main.EVT_BENCHMARKS, self.OnNewBenchmarks)
        self.Bind(main.EVT_START_MINING, self.OnStartMining)
        self.Bind(main.EVT_STOP_MINING, self.OnStopMining)

        self.Bind(EVT_STATUS, self.OnBenchmarkStatus)
        self.Bind(EVT_SET_VALUE, self.OnBenchmarkSet)
        self.Bind(EVT_CLEAR_VALUE, self.OnBenchmarkDelete)
        self.Bind(EVT_COMPLETE, self.OnBenchmarksComplete)
        self.Bind(EVT_SPEEDS, self.OnInputSpeeds)

        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(sizer)

        # Create inner scrolled area.
        innerWindow = ScrolledPanel(self)
        innerWindow.SetupScrolling()
        sizer.Add(innerWindow, wx.SizerFlags().Border(wx.LEFT|wx.RIGHT|wx.TOP,
                                                      main.PADDING_PX)
                                              .Proportion(1.0)
                                              .Expand())
        innerSizer = wx.BoxSizer(orient=wx.VERTICAL)
        innerWindow.SetSizer(innerSizer)

        # Populate it with a collapsible panel for each device.
        self._DevicePanes = {}
        for device in self._Devices:
            deviceCp = wx.CollapsiblePane(
                innerWindow, label=('%s\n%s' % (device.name, device.uuid)))
            self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.OnPaneChanged,
                      deviceCp)
            innerSizer.Add(deviceCp, wx.SizerFlags().Expand())
            self._DevicePanes[device] = deviceCp.GetPane()

        bottomSizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        sizer.Add(bottomSizer, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
                                              .Expand())

        # Create bottom controls.
        self._SelectTodo = wx.Button(self, label='Unmeasured')
        self.Bind(wx.EVT_BUTTON, self.OnSelectUnmeasured, self._SelectTodo)
        bottomSizer.Add(self._SelectTodo)

        bottomSizer.AddSpacer(main.PADDING_PX)

        self._SelectNone = wx.Button(self, label='None')
        self.Bind(wx.EVT_BUTTON, self.OnSelectNone, self._SelectNone)
        bottomSizer.Add(self._SelectNone)

        bottomSizer.AddStretchSpacer()

        self._Benchmark = wx.Button(self, label='Benchmark')
        self.Bind(wx.EVT_BUTTON, self.OnBenchmark, self._Benchmark)
        bottomSizer.Add(self._Benchmark)

        self._Repopulate()

    def OnNewSettings(self, event):
        pass

    def OnNewBenchmarks(self, event):
        pass

    def OnStartMining(self, event):
        self._Benchmark.Disable()

    def OnStopMining(self, event):
        self._Benchmark.Enable()

    def _Repopulate(self):
        self._Miners = [miner(main.CONFIG_DIR, self._Frame.Settings)
                        for miner in all_miners]
        allAlgorithms = sum([miner.algorithms for miner in self._Miners], [])
        self._Items = {}
        for device in self._Devices:
            pane = self._DevicePanes[device]
            oldSizer = pane.GetSizer()
            if oldSizer:
                oldSizer.Clear(True)

            algorithms = [algorithm for algorithm in allAlgorithms
                          if algorithm.accepts(device)]
            sizer = wx.FlexGridSizer(len(algorithms), 4, wx.Size(0, 0))
            pane.SetSizer(sizer, deleteOld=True)
            sizer.AddGrowableCol(3)
            for algorithm in algorithms:
                item = Item(pane, algorithm)
                sizer.Add(item.checkbox)
                sizer.Add(item.label, wx.SizerFlags().Expand())
                sizer.AddSpacer(main.PADDING_PX)
                sizer.Add(item.speeds, wx.SizerFlags().Expand())
                self._Items[(device, algorithm)] = item
                self._ResetSpeedCtrl(device, algorithm)
        self.Layout()

    def OnSelectUnmeasured(self, event):
        self._Selection = (
            [(device, algorithm) for (device, algorithm) in self._Items.keys()
             if algorithm.name not in self._Frame.Benchmarks[device]])

    def OnSelectNone(self, event):
        self._Selection = []

    def OnBenchmark(self, event):
        selection = self._Selection
        if not self._Thread and len(selection) > 0:
            self._SelectTodo.Disable()
            self._SelectNone.Disable()
            for item in self._Items.values():
                item.checkbox.Disable()
            self._Benchmark.SetLabel('Cancel')

            wx.PostEvent(self._Frame, main.StartBenchmarkingEvent(id=wx.ID_ANY))

            self._Thread = BenchmarkThread(
                selection, window=self,
                settings=self._Frame.Settings, miners=self._Miners)
            self._Thread.start()
        elif self._Thread:
            self._Thread.stop()
            self._Thread.join()

    def OnBenchmarkStatus(self, event):
        item = self._Items[event.target]
        if event.warmup:
            item.speeds.SetWarmup(event.time)
        else:
            item.speeds.SetBenchmark(event.speeds, event.time)

    def OnBenchmarkSet(self, event):
        device, algorithm = event.target
        self._Frame.Benchmarks[device][algorithm.name] = event.speeds
        # Still need to activate the setter.
        self._Frame.Benchmarks = self._Frame.Benchmarks
        self._ResetSpeedCtrl(device, algorithm)

    def OnBenchmarkDelete(self, event):
        device, algorithm = event.target
        benchmarks = self._Frame.Benchmarks[device]
        if algorithm.name in benchmarks:
            del benchmarks[algorithm.name]
        # Still need to activate the setter.
        self._Frame.Benchmarks = self._Frame.Benchmarks
        self._ResetSpeedCtrl(device, algorithm)

    def OnBenchmarksComplete(self, event):
        self._Thread.join()
        self._Thread = None

        wx.PostEvent(self._Frame, main.StopBenchmarkingEvent(id=wx.ID_ANY))

        self._SelectTodo.Enable()
        self._SelectNone.Enable()
        for (device, algorithm), item in self._Items.items():
            item.checkbox.Enable()
            # Reset speed controls in case benchmarking was aborted.
            self._ResetSpeedCtrl(device, algorithm)
        self._Benchmark.SetLabel('Benchmark')

    def OnInputSpeeds(self, event):
        source = event.GetEventObject()
        target = next((device, algorithm) for ((device, algorithm), item)
                      in self._Items.items() if item.speeds == source)
        device, algorithm = target
        nSpeeds = len(event.speeds)
        nNeeded = len(algorithm.algorithms)
        if nSpeeds >= nNeeded:
            speeds = event.speeds[:nNeeded]
            wx.PostEvent(
                self, SetEvent(target=target, speeds=speeds, id=wx.ID_ANY))
        elif nSpeeds == 0:
            wx.PostEvent(
                self, DeleteEvent(target=target, id=wx.ID_ANY))
        else:
            self._ResetSpeedCtrl(device, algorithm)

    def _ResetSpeedCtrl(self, device, algorithm):
        benchmarks = self._Frame.Benchmarks[device]
        item = self._Items[(device, algorithm)]
        if algorithm.name in benchmarks:
            item.speeds.SetValues(benchmarks[algorithm.name])
        else:
            item.speeds.SetValues([0.0]*len(algorithm.algorithms))

    @property
    def _Selection(self):
        return [(device, algorithm) for ((device, algorithm), item)
                in self._Items.items() if item.is_selected()]
    @_Selection.setter
    def _Selection(self, selection):
        for (device, algorithm) in self._Items.keys():
            item = self._Items[(device, algorithm)]
            if (device, algorithm) in selection:
                item.select()
            else:
                item.deselect()

    def OnPaneChanged(self, event):
        self.Layout()


class BenchmarkThread(threading.Thread):

    def __init__(self, targets, window=None, settings=DEFAULT_SETTINGS, miners=[]):
        threading.Thread.__init__(self)
        self._targets = targets
        self._window = window
        self._settings = settings
        self._miners = miners
        self._abort = threading.Event()

    def run(self):
        for miner in self._miners:
            miner.load()

        for target in self._targets:
            def report(sample, secs_remaining):
                wx.PostEvent(self._window,
                             StatusEvent(target=target, speeds=sample,
                                         time=abs(secs_remaining),
                                         warmup=(secs_remaining < 0)))
            device, algorithm = target
            speeds = utils.run_benchmark(
                algorithm, device, algorithm.warmup_secs, BENCHMARK_SECS,
                sample_callback=report, abort_signal=self._abort)
            if self._abort.is_set():
                break

            wx.PostEvent(
                self._window, SetEvent(target=target, speeds=speeds, id=wx.ID_ANY))

        for miner in self._miners:
            miner.unload()

        wx.PostEvent(self._window, DoneEvent())

    def stop(self):
        self._abort.set()


class Item(object):

    def __init__(self, parent, algorithm):
        self.checkbox = wx.CheckBox(parent)
        self.label = wx.StaticText(parent, label=algorithm.name)
        self.label.Bind(wx.EVT_LEFT_UP, self._onclick)
        self.speeds = SpeedCtrl(parent)

    def _onclick(self, event):
        self.checkbox.SetValue(not self.checkbox.GetValue())

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
                               size=(-1, 20), **kwargs)
        self._StatusPos = 0
        self.Bind(wx.EVT_KILL_FOCUS, self._OnUnfocus)

    def SetValues(self, values):
        self.Enable()
        if all(speed == 0.0 for speed in values):
            s = '--'
        else:
            s = '; '.join(utils.format_speed(speed).strip() for speed in values)
        self.ChangeValue(s)

    def SetWarmup(self, remaining):
        self.Disable()
        self.ChangeValue('warming up (%d)%s' % (remaining, self._StatusDot()))

    def SetBenchmark(self, values, remaining):
        self.Disable()
        s = '; '.join(utils.format_speed(speed).strip() for speed in values)
        self.ChangeValue('%s (%d)%s' % (s, remaining, self._StatusDot()))

    def _StatusDot(self):
        s = ''.join('.' if i == self._StatusPos else ' ' for i in range(3))
        self._StatusPos = (self._StatusPos + 1) % 3
        return s

    def _OnUnfocus(self, event):
        speeds = []
        speedsRe = r' *[;,]? *(\d+\.?\d*) *([EePpTtGgMmkK](?:H|H/s)?|(?:H|H/s))'
        for match in re.finditer(speedsRe, self.GetValue()):
            factor = {
                'E': 1e18,
                'P': 1e15,
                'T': 1e12,
                'G': 1e9,
                'M': 1e6,
                'K': 1e3,
                'H': 1
                }
            value = float(match[1])
            unit = match[2][0].upper()
            speeds.append(value*factor[unit])

        event = InputSpeedsEvent(speeds=speeds, id=wx.ID_ANY)
        event.SetEventObject(self)
        wx.PostEvent(self, event)

