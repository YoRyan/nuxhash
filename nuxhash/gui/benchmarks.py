import wx
import wx.dataview

from nuxhash import utils
from nuxhash.devices.nvidia import NvidiaDevice
from nuxhash.gui import main
from nuxhash.miners import all_miners
from nuxhash.settings import DEFAULT_SETTINGS


class BenchmarksScreen(wx.Panel):

    def __init__(self, parent, *args, devices=[], **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(sizer)

        self._dataview = wx.dataview.DataViewCtrl(self)
        self._dataview.AppendTextColumn('Algorithm', 0, width=300)
        self._dataview.AppendTextColumn('Speed', 1, width=wx.COL_WIDTH_AUTOSIZE)
        self._datamodel = BenchmarksTreeModel(devices=devices)
        self._dataview.AssociateModel(self._datamodel)
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
        return self._datamodel.benchmarks
    @benchmarks.setter
    def benchmarks(self, value):
        self._datamodel.benchmarks = value

    @property
    def settings(self):
        return self._datamodel.settings
    @settings.setter
    def settings(self, value):
        self._datamodel.settings = value


class BenchmarksTreeModel(wx.dataview.PyDataViewModel):

    def __init__(self, *args, devices=[], **kwargs):
        wx.dataview.PyDataViewModel.__init__(self, *args, **kwargs)
        #self.UseWeakRefs(True)
        self._devices = devices
        self._benchmarks = {device: {} for device in self._devices}
        self._settings = DEFAULT_SETTINGS
        miners = [miner(main.CONFIG_DIR, self._settings) for miner in all_miners]
        self._algorithms = sum([miner.algorithms for miner in miners], [])

    @property
    def benchmarks(self):
        return self._benchmarks
    @benchmarks.setter
    def benchmarks(self, value):
        self._benchmarks = value
        #self.Cleared()

    @property
    def settings(self):
        return self._settings
    @settings.setter
    def settings(self, value):
        self._settings = value
        miners = [miner(main.CONFIG_DIR, self._settings) for miner in all_miners]
        self._algorithms = sum([miner.algorithms for miner in miners], [])
        #self.Cleared()

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

