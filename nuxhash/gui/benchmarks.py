import wx
import wx.dataview
import wx.lib.scrolledpanel

from nuxhash import utils
from nuxhash.devices.nvidia import NvidiaDevice
from nuxhash.gui import main
from nuxhash.miners import all_miners
from nuxhash.settings import DEFAULT_SETTINGS, EMPTY_BENCHMARKS


class BenchmarksScreen(wx.Panel):

    def __init__(self, parent, *args, devices=[], **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self._devices = devices
        self._settings = DEFAULT_SETTINGS
        self._benchmarks = EMPTY_BENCHMARKS
        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(sizer)

        # Create inner scrolled area.
        inner_window = wx.lib.scrolledpanel.ScrolledPanel(self)
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
        clear = wx.Button(self, id=wx.ID_CLEAR)
        bottom_sizer.Add(clear)
        bottom_sizer.AddStretchSpacer()
        select_todo = wx.Button(self, label='Select Unmeasured')
        bottom_sizer.Add(select_todo)
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
                sizer.Add(wx.CheckBox(pane))
                sizer.Add(wx.StaticText(pane, label=algorithm.name))
                speeds = self._benchmarks[device][algorithm.name]
                sizer.Add(wx.StaticText(
                    pane, label=utils.format_speeds(speeds).strip()))

    def OnPaneChanged(self, event):
        self.Layout()

