import wx
import wx.dataview

from nuxhash import utils
from nuxhash.devices.nvidia import NvidiaDevice
from nuxhash.gui import main
from nuxhash.miners import all_miners


class BenchmarksScreen(wx.Panel):

    def __init__(self, parent, *args, devices=[], **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self._devices = devices
        self._benchmarks = self._settings = self._datamodel = None
        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(sizer)

        self._dataview = wx.dataview.DataViewCtrl(self)
        self._dataview.AppendTextColumn('Algorithm', 0, width=300)
        self._dataview.AppendTextColumn('Speed', 1, width=wx.COL_WIDTH_AUTOSIZE)
        sizer.Add(self._dataview, wx.SizerFlags().Border(wx.LEFT|wx.RIGHT|wx.TOP,
                                                         main.PADDING_PX)
                                                 .Proportion(1.0)
                                                 .Expand())

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
        self._reload_model()

    @property
    def settings(self):
        return self._settings
    @settings.setter
    def settings(self, value):
        self._settings = value
        self._reload_model()

    def _reload_model(self):
        # We cannot simply call PyDataViewModel.Cleared() because that method
        # (contrary to documentation) does not reload data on Linux, see
        # https://github.com/wxWidgets/Phoenix/issues/824
        if self._datamodel:
            self._dataview.UnselectAll()
            del self._datamodel

        self._datamodel = BenchmarksTreeModel(devices=self._devices,
                                              benchmarks=self._benchmarks,
                                              settings=self._settings)
        self._dataview.AssociateModel(self._datamodel)
        self._datamodel.DecRef()


class BenchmarksTreeModel(wx.dataview.PyDataViewModel):

    def __init__(self, *args, devices=[], benchmarks=None,
                 settings=None, **kwargs):
        wx.dataview.PyDataViewModel.__init__(self, *args, **kwargs)
        self._devices = devices
        self._benchmarks = benchmarks
        self._settings = settings
        miners = [miner(main.CONFIG_DIR, self._settings) for miner in all_miners]
        self._algorithms = sum([miner.algorithms for miner in miners], [])

    def IsContainer(self, item):
        if not item:
            return True
        else:
            node = self.ItemToObject(item)
            return isinstance(node, DeviceNode)

    def GetParent(self, item):
        if not item:
            return wx.dataview.NullDataViewItem
        else:
            node = self.ItemToObject(item)
            if isinstance(node, DeviceNode):
                return wx.dataview.NullDataViewItem
            elif isinstance(node, AlgorithmNode):
                return self.ObjectToItem(node.device)

    def GetChildren(self, item, children):
        if not item:
            for device in self._devices:
                device_node = self._to_device_node(device)
                algorithms = [algorithm for algorithm in self._algorithms
                              if algorithm.accepts(device)]
                device_node.algorithms = [AlgorithmNode(algorithm.name, device_node)
                                          for algorithm in algorithms]
                children.append(self.ObjectToItem(device_node))
            return len(self._devices)
        else:
            node = self.ItemToObject(item)
            if isinstance(node, DeviceNode):
                for algorithm_node in node.algorithms:
                    children.append(self.ObjectToItem(algorithm_node))
                return len(node.algorithms)
            else:
                return 0

    def GetColumnCount(self):
        return 2

    def GetColumnType(self, col):
        types = [
            'string',
            'string'
            ]
        return types[col]

    def GetValue(self, item, col):
        node = self.ItemToObject(item)
        if isinstance(node, DeviceNode):
            device = self._to_device(node)
            data = [
                '%s\n%s' % (device.name, device.uuid),
                ''
                ]
            return data[col]
        elif isinstance(node, AlgorithmNode):
            device = self._to_device(node.device)
            benchmarks = self._benchmarks[device]
            algorithm = next(algorithm for algorithm in self._algorithms
                             if algorithm.name == node.name)
            data = [
                algorithm.name,
                utils.format_speeds(benchmarks[algorithm.name]).strip()
                ]
            return data[col]
        else:
            raise RuntimeError('unknown node type')

    def _to_device(self, device_node):
        if device_node.vendor == 'nvidia':
            return next(device for device in self._devices
                        if (isinstance(device, NvidiaDevice)
                            and device.uuid == device_node.uuid))
        else:
            raise RuntimeError('non-Nvidia not implemented')

    def _to_device_node(self, device):
        if isinstance(device, NvidiaDevice):
            return DeviceNode(device.uuid, 'nvidia')
        else:
            raise RuntimeError('non-Nvidia not implemented')


class DeviceNode(object):

    def __init__(self, uuid, vendor):
        self.uuid = uuid
        self.vendor = vendor
        self.algorithms = []


class AlgorithmNode(object):

    def __init__(self, name, device):
        self.name = name
        self.device = device

