import threading

import wx
import wx.dataview
from wx.lib.newevent import NewEvent
from wx.lib.scrolledpanel import ScrolledPanel

from nuxhash import utils
from nuxhash.devices.nvidia import NvidiaDevice
from nuxhash.gui import main
from nuxhash.miners import all_miners
from nuxhash.nicehash import simplemultialgo_info
from nuxhash.settings import DEFAULT_SETTINGS


BENCHMARK_SECS = 60

StatusEvent, EVT_STATUS = NewEvent()
SetEvent, EVT_SET_VALUE = NewEvent()
DoneEvent, EVT_COMPLETE = NewEvent()


class BenchmarksScreen(wx.Panel):

    def __init__(self, parent, *args, devices=[], frame=None, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self._devices = devices
        self._frame = frame
        # dict of (device, algorithm) -> Item
        self._items = {}
        self._thread = None
        self.Bind(main.EVT_SETTINGS, self.OnNewSettings)
        self.Bind(main.EVT_BENCHMARKS, self.OnNewBenchmarks)
        self.Bind(EVT_STATUS, self.OnBenchmarkStatus)
        self.Bind(EVT_SET_VALUE, self.OnBenchmarkSet)
        self.Bind(EVT_COMPLETE, self.OnBenchmarksComplete)
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
        self._select_todo = wx.Button(self, label='Unmeasured')
        self.Bind(wx.EVT_BUTTON, self.OnSelectUnmeasured, self._select_todo)
        bottom_sizer.Add(self._select_todo)

        bottom_sizer.AddSpacer(main.PADDING_PX)

        self._select_none = wx.Button(self, label='None')
        self.Bind(wx.EVT_BUTTON, self.OnSelectNone, self._select_none)
        bottom_sizer.Add(self._select_none)

        bottom_sizer.AddStretchSpacer()

        bottom_sizer.AddSpacer(main.PADDING_PX)
        self._benchmark = wx.Button(self, label='Benchmark')
        self.Bind(wx.EVT_BUTTON, self.OnBenchmark, self._benchmark)
        bottom_sizer.Add(self._benchmark)

        self._repopulate()

    def OnNewSettings(self, event):
        pass

    def OnNewBenchmarks(self, event):
        pass

    def _repopulate(self):
        self._miners = [miner(main.CONFIG_DIR, self._frame.settings)
                        for miner in all_miners]
        all_algorithms = sum([miner.algorithms for miner in self._miners], [])
        self._items = {}
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
                item = Item(pane, algorithm)
                sizer.Add(item.checkbox)
                sizer.Add(item.label)
                sizer.Add(item.speeds)
                self._items[(device, algorithm)] = item

                benchmarks = self._frame.benchmarks[device]
                if algorithm.name in benchmarks:
                    item.speeds.set_values(benchmarks[algorithm.name])
        self.Layout()

    def OnSelectUnmeasured(self, event):
        self._set_selection(
            [(device, algorithm) for (device, algorithm) in self._items.keys()
             if algorithm.name not in self._frame.benchmarks[device]])

    def OnSelectNone(self, event):
        self._set_selection([])

    def OnBenchmark(self, event):
        if not self._thread:
            self._select_todo.Disable()
            self._select_none.Disable()
            for item in self._items.values():
                item.checkbox.Disable()
            self._benchmark.SetLabel('Cancel')

            selection = self._get_selection()
            self._thread = BenchmarkThread(
                selection, window=self,
                settings=self._frame.settings, miners=self._miners)
            self._thread.start()
        else:
            self._thread.stop()
            self._thread.join()

    def OnBenchmarkStatus(self, event):
        item = self._items[event.target]
        if event.warmup:
            item.speeds.set_warmup(event.time)
        else:
            item.speeds.set_benchmark(event.speeds, event.time)

    def OnBenchmarkSet(self, event):
        device, algorithm = event.target
        self._frame.benchmarks[device][algorithm.name] = event.speeds
        # We still need to activate the setter.
        self._frame.benchmarks = self._frame.benchmarks

        item = self._items[event.target]
        item.speeds.set_values(event.speeds)

    def OnBenchmarksComplete(self, event):
        self._thread.join()
        self._thread = None

        self._select_todo.Enable()
        self._select_none.Enable()
        for (device, algorithm), item in self._items.items():
            item.checkbox.Enable()
            # Reset speed controls in case benchmarking was aborted.
            benchmarks = self._frame.benchmarks[device]
            if algorithm.name in benchmarks:
                item.speeds.set_values(benchmarks[algorithm.name])
            else:
                item.speeds.set_values([0.0]*len(algorithm.algorithms))
        self._benchmark.SetLabel('Benchmark')

    def _set_selection(self, selection):
        for (device, algorithm) in self._items.keys():
            item = self._items[(device, algorithm)]
            if (device, algorithm) in selection:
                item.select()
            else:
                item.deselect()

    def _get_selection(self):
        return [(device, algorithm) for ((device, algorithm), item)
                in self._items.items() if item.is_selected()]

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
        payrates, stratums = simplemultialgo_info(self._settings)
        for miner in self._miners:
            miner.stratums = stratums
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

            wx.PostEvent(self._window, SetEvent(target=target, speeds=speeds))

        for miner in self._miners:
            miner.unload()

        wx.PostEvent(self._window, DoneEvent())

    def stop(self):
        self._abort.set()


class Item(object):

    def __init__(self, parent, algorithm):
        self.checkbox = wx.CheckBox(parent)
        self.label = wx.StaticText(parent, label=algorithm.name)
        self.speeds = SpeedCtrl(parent)
        self.speeds.set_values([0.0]*len(algorithm.algorithms))

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
        self._status_pos = 0

    def set_values(self, values):
        self.Enable()
        if all(speed == 0.0 for speed in values):
            s = '--'
        else:
            s = '; '.join(utils.format_speed(speed).strip() for speed in values)
        self.SetValue(s)

    def set_warmup(self, remaining):
        self.Disable()
        self.SetValue('warming up (%d)%s' % (remaining, self._status_dot()))

    def set_benchmark(self, values, remaining):
        self.Disable()
        s = '; '.join(utils.format_speed(speed).strip() for speed in values)
        self.SetValue('%s (%d)%s' % (s, remaining, self._status_dot()))

    def _status_dot(self):
        s = ''.join('.' if i == self._status_pos else ' ' for i in range(3))
        self._status_pos = (self._status_pos + 1) % 3
        return s

