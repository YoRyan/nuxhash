import logging
import sched
import socket
import threading
import time
from copy import deepcopy
from datetime import datetime
from random import random

import wx
import wx.dataview
from wx.lib.pubsub import pub

from nuxhash import nicehash, utils
from nuxhash.bitcoin import check_bc
from nuxhash.daemon import DONATE_ADDRESS
from nuxhash.devices.nvidia import NvidiaDevice
from nuxhash.gui import main
from nuxhash.miners import all_miners
from nuxhash.nicehash import get_balances
from nuxhash.settings import DEFAULT_SETTINGS, EMPTY_BENCHMARKS
from nuxhash.switching.naive import NaiveSwitcher


MINING_UPDATE_SECS = 5
BALANCE_UPDATE_MIN = 5
NVIDIA_COLOR = (66, 244, 69)
DONATE_PROB = 0.005


class MiningScreen(wx.Panel):

    def __init__(self, parent, *args, devices=[], **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self._Thread = None
        self._Benchmarking = False
        self._Devices = devices
        self._Settings = self._Benchmarks = None

        pub.subscribe(self._OnSettings, 'data.settings')
        pub.subscribe(self._OnBenchmarks, 'data.benchmarks')

        pub.subscribe(self._OnStartBenchmarking, 'benchmarking.start')
        pub.subscribe(self._OnStopBenchmarking, 'benchmarking.stop')

        pub.subscribe(self._OnClose, 'app.close')

        pub.subscribe(self._OnNewBalances, 'nicehash.balances')
        pub.subscribe(self._OnMiningStatus, 'mining.status')

        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(sizer)

        # Update balance periodically.
        self._Timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._OnBalanceTimer, self._Timer)
        self._Timer.Start(milliseconds=BALANCE_UPDATE_MIN*60*1e3)

        # Add mining panel.
        self._Panel = MiningPanel(self, style=wx.dataview.DV_HORIZ_RULES)
        sizer.Add(self._Panel, wx.SizerFlags().Border(wx.LEFT|wx.RIGHT|wx.TOP,
                                                      main.PADDING_PX)
                                              .Proportion(1.0)
                                              .Expand())

        bottomSizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        sizer.Add(bottomSizer, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
                                              .Expand())

        # Add balance displays.
        balances = wx.FlexGridSizer(2, 2, main.PADDING_PX)
        balances.AddGrowableCol(1)
        bottomSizer.Add(balances, wx.SizerFlags().Proportion(1.0).Expand())

        balances.Add(wx.StaticText(self, label='Daily revenue'))
        self._Revenue = wx.StaticText(
            self, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
        self._Revenue.SetFont(self.GetFont().Bold())
        balances.Add(self._Revenue, wx.SizerFlags().Expand())

        balances.Add(wx.StaticText(self, label='Balance (unpaid)'))
        self._Balances = wx.StaticText(
            self, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
        self._Balances.SetFont(self.GetFont().Bold())
        balances.Add(self._Balances, wx.SizerFlags().Expand())

        bottomSizer.AddSpacer(main.PADDING_PX)

        # Add start/stop button.
        self._StartStop = wx.Button(self, label='Start Mining')
        bottomSizer.Add(self._StartStop, wx.SizerFlags().Expand()
                                                        .Center())
        self.Bind(wx.EVT_BUTTON, self.OnStartStop, self._StartStop)

    def _OnSettings(self, settings):
        if settings != self._Settings:
            self._Settings = settings
            self._UpdateBalances()
            self._UpdateMining()

    def _OnBenchmarks(self, benchmarks):
        if benchmarks != self._Benchmarks:
            self._Benchmarks = benchmarks
            self._UpdateMining()

    def _OnStartBenchmarking(self):
        self._Benchmarking = True
        self._UpdateMining()

    def _OnStopBenchmarking(self):
        self._Benchmarking = False
        self._UpdateMining()

    def _UpdateMining(self):
        if (self._Benchmarks is not None
            and not self._Benchmarking
            and check_bc(self._Settings['nicehash']['wallet'])
            and any(self._Benchmarks[device] != {} for device in self._Devices)):
            if self._Thread:
                # TODO: Update mining thread more gracefully?
                self._StopMining()
                self._StartMining()
            self._StartStop.Enable()
        else:
            if self._Thread:
                self._StopMining()
            self._StartStop.Disable()

    def _OnClose(self):
        if self._Thread:
            self._Thread.stop()

    def _OnBalanceTimer(self, event):
        self._UpdateBalances()

    def _UpdateBalances(self):
        address = self._Settings['nicehash']['wallet']
        if check_bc(address):
            def do_requests(address, target):
                wallet, unpaid = get_balances(self._Settings)
                main.sendMessage(target, 'nicehash.balances',
                                 wallet=wallet, unpaid=unpaid)
            thread = threading.Thread(target=do_requests, args=(address, self))
            thread.start()
        else:
            pub.sendMessage('nicehash.balances', wallet=None, unpaid=None)

    def OnStartStop(self, event):
        if not self._Thread:
            self._StartMining()
        else:
            self._StopMining()

    def _StartMining(self):
        pub.sendMessage('mining.start')
        self._StartStop.SetLabel('Stop Mining')
        self._Thread = MiningThread(
                devices=self._Devices, window=self,
                settings=deepcopy(self._Settings),
                benchmarks=deepcopy(self._Benchmarks))
        self._Thread.start()

    def _StopMining(self):
        pub.sendMessage('mining.stop')
        self._Revenue.SetLabel('')
        self._StartStop.SetLabel('Start Mining')
        self._Thread.stop()
        self._Thread = None

    def _OnNewBalances(self, wallet, unpaid):
        if unpaid is not None:
            unit = self._Settings['gui']['units']
            unpaid_str = utils.format_balance(unpaid, unit)
            if wallet is not None:
                wallet_str = utils.format_balance(wallet, unit)
                label = f'{wallet_str} ({unpaid_str})'
            else:
                label = f'api keys required ({unpaid_str})'
        else:
            label = ''
        self._Balances.SetLabel(label)

    def _OnMiningStatus(self, speeds, revenue, devices):
        totalRevenue = sum(revenue.values())
        unit = self._Settings['gui']['units']
        self._Revenue.SetLabel(utils.format_balance(totalRevenue, unit))


class MiningPanel(wx.dataview.DataViewListCtrl):

    def __init__(self, parent, *args, **kwargs):
        wx.dataview.DataViewListCtrl.__init__(self, parent, *args, **kwargs)
        self._Settings = None
        self.Disable()
        self.AppendTextColumn('Algorithm', width=wx.COL_WIDTH_AUTOSIZE)
        self.AppendColumn(
                wx.dataview.DataViewColumn('Devices', DeviceListRenderer(),
                                           1, align=wx.ALIGN_LEFT,
                                           width=wx.COL_WIDTH_AUTOSIZE),
                'string')
        self.AppendTextColumn('Speed', width=wx.COL_WIDTH_AUTOSIZE)
        self.AppendTextColumn('Revenue')

        pub.subscribe(self._OnSettings, 'data.settings')
        pub.subscribe(self._OnStartMining, 'mining.start')
        pub.subscribe(self._OnStopMining, 'mining.stop')
        pub.subscribe(self._OnMiningStatus, 'mining.status')

    def _OnSettings(self, settings):
        if settings != self._Settings:
            self._Settings = settings

    def _OnStartMining(self):
        self.Enable()

    def _OnStopMining(self):
        self.Disable()
        self.DeleteAllItems()

    def _OnMiningStatus(self, speeds, revenue, devices):
        self.DeleteAllItems()
        algorithms = list(speeds.keys())
        algorithms.sort(key=lambda algorithm: algorithm.name)
        for algorithm in algorithms:
            algo_sublist = ', '.join(algorithm.algorithms)
            algo = f'{algorithm.name}\n({algo_sublist})'
            devicesStr = ','.join([DeviceListRenderer._DeviceToString(device)
                                   for device in devices[algorithm]])
            speed = ',\n'.join([utils.format_speed(speed)
                                for speed in speeds[algorithm]])
            pay = utils.format_balance(
                revenue[algorithm], self._Settings['gui']['units'])
            self.AppendItem([algo, devicesStr, speed, pay])


class DeviceListRenderer(wx.dataview.DataViewCustomRenderer):

    CORNER_RADIUS = 5

    def __init__(self, *args, **kwargs):
        wx.dataview.DataViewCustomRenderer.__init__(self, *args, **kwargs)
        self._Devices = []
        self._ColorDb = wx.ColourDatabase()

    def SetValue(self, value):
        vendors = { 'N': 'nvidia' }
        self._Devices = [{ 'name': s[2:], 'vendor': vendors[s[0]] }
                         for s in value.split(',')]
        return True

    def GetValue(self):
        tags = { 'nvidia': 'N' }
        return ','.join([f"{tags[device['vendor']]}:{device['name']}"
                         for device in self._Devices])

    def GetSize(self):
        boxes = [self.GetTextExtent(device['name']) for device in self._Devices]
        RADIUS = DeviceListRenderer.CORNER_RADIUS
        return wx.Size(max(box.GetWidth() for box in boxes) + RADIUS*2,
                       (sum(box.GetHeight() for box in boxes)
                        + RADIUS*2*len(boxes) + RADIUS*(len(boxes) - 1)))

    def Render(self, cell, dc, state):
        position = cell.GetPosition()
        for device in self._Devices:
            box = self.GetTextExtent(device['name'])
            RADIUS = DeviceListRenderer.CORNER_RADIUS

            if device['vendor'] == 'nvidia':
                color = self._ColorDb.Find('LIME GREEN')
            else:
                color = self._ColorDb.Find('LIGHT GREY')
            dc.SetBrush(wx.Brush(color))
            dc.SetPen(wx.TRANSPARENT_PEN)
            shadeRect = wx.Rect(
                    position,
                    wx.Size(box.GetWidth() + RADIUS*2, box.GetHeight() + RADIUS*2))
            dc.DrawRoundedRectangle(shadeRect, RADIUS)

            textRect = wx.Rect(
                    wx.Point(position.x + RADIUS, position.y + RADIUS), box)
            self.RenderText(device['name'], 0, textRect, dc, state)

            position = wx.Point(
                    position.x, (position.y + box.GetHeight() + RADIUS*2 + RADIUS))
        return True

    def _DeviceToString(device):
        if isinstance(device, NvidiaDevice):
            name = device.name
            name = name.replace('GeForce', '')
            name = name.replace('GTX', '')
            name = name.replace('RTX', '')
            name = name.strip()
            return f'N:{name}'
        else:
            raise Exception('bad device instance')


class MiningThread(threading.Thread):

    PROFIT_PRIORITY = 1
    STATUS_PRIORITY = 2
    STOP_PRIORITY = 0

    def __init__(self, devices=[], window=None,
                 settings=DEFAULT_SETTINGS, benchmarks=EMPTY_BENCHMARKS):
        threading.Thread.__init__(self)
        self._window = window
        self._settings = settings
        self._benchmarks = benchmarks
        self._devices = devices
        self._payrates = (None, None)
        self._stop_signal = threading.Event()
        self._scheduler = sched.scheduler(
            time.time, lambda t: self._stop_signal.wait(t))

    def run(self):
        # Initialize miners.
        stratums = None
        while stratums is None:
            try:
                payrates = nicehash.simplemultialgo_info(self._settings)
                stratums = nicehash.stratums(self._settings)
            except Exception as err:
                logging.warning(f'NiceHash stats: {err}, retrying in 5 seconds')
                time.sleep(5)
            else:
                self._payrates = payrates
        self._miners = [miner(main.CONFIG_DIR) for miner in all_miners]
        for miner in self._miners:
            miner.settings = self._settings
            miner.stratums = stratums
        self._algorithms = sum([miner.algorithms for miner in self._miners], [])

        # Initialize profit-switching.
        self._profit_switch = NaiveSwitcher(self._settings)
        self._profit_switch.reset()

        self._scheduler.enter(0, MiningThread.PROFIT_PRIORITY, self._switch_algos)
        self._scheduler.enter(0, MiningThread.STATUS_PRIORITY, self._read_status)
        self._scheduler.run()

    def stop(self):
        self._scheduler.enter(0, MiningThread.STOP_PRIORITY, self._stop_mining)
        self._stop_signal.set()
        self.join()

    def _switch_algos(self):
        # Get profitability information from NiceHash.
        try:
            ret_payrates = nicehash.simplemultialgo_info(self._settings)
        except Exception as err:
            logging.warning(f'NiceHash stats: {err}')
        else:
            self._payrates = (ret_payrates, datetime.now())

        interval = self._settings['switching']['interval']
        payrates, payrates_time = self._payrates

        # Calculate BTC/day rates.
        def revenue(device, algorithm):
            benchmarks = self._benchmarks[device]
            if algorithm.name in benchmarks:
                return sum([payrates[sub_algo]*benchmarks[algorithm.name][i]
                            if sub_algo in payrates else 0.0
                            for i, sub_algo in enumerate(algorithm.algorithms)])
            else:
                return 0.0
        revenues = {device: {algorithm: revenue(device, algorithm)
                             for algorithm in self._algorithms}
                    for device in self._devices}

        # Get device -> algorithm assignments from profit switcher.
        assigned_algorithm = self._profit_switch.decide(revenues, payrates_time)
        self._assignments = assigned_algorithm
        for this_algorithm in self._algorithms:
            this_devices = [device for device, algorithm
                            in assigned_algorithm.items()
                            if algorithm == this_algorithm]
            this_algorithm.set_devices(this_devices)

        # Donation time.
        if not self._settings['donate']['optout'] and random() < DONATE_PROB:
            logging.warning('This interval will be donation time.')
            donate_settings = deepcopy(self._settings)
            donate_settings['nicehash']['wallet'] = DONATE_ADDRESS
            donate_settings['nicehash']['workername'] = 'nuxhash'
            for miner in self._miners:
                miner.settings = donate_settings
            self._scheduler.enter(interval, MiningThread.PROFIT_PRIORITY,
                                  self._reset_miners)

        self._scheduler.enter(interval, MiningThread.PROFIT_PRIORITY,
                              self._switch_algos)

    def _reset_miners(self):
        for miner in self._miners:
            miner.settings = self._settings

    def _read_status(self):
        payrates, payrates_time = self._payrates
        running_algorithms = self._assignments.values()
        speeds = {algorithm: algorithm.current_speeds()
                  for algorithm in running_algorithms}
        revenue = {algorithm: sum([payrates[sub_algo]*speeds[algorithm][i]
                                  for i, sub_algo
                                  in enumerate(algorithm.algorithms)])
                   for algorithm in running_algorithms}
        devices = {algorithm: [device for device, this_algorithm
                               in self._assignments.items()
                               if this_algorithm == algorithm]
                   for algorithm in running_algorithms}
        main.sendMessage(self._window, 'mining.status',
                         speeds=speeds, revenue=revenue, devices=devices)
        self._scheduler.enter(MINING_UPDATE_SECS, MiningThread.STATUS_PRIORITY,
                              self._read_status)

    def _stop_mining(self):
        logging.info('Stopping mining')
        for algorithm in self._algorithms:
            algorithm.set_devices([])
        for miner in self._miners:
            miner.unload()
        # Empty the scheduler.
        for job in self._scheduler.queue:
            self._scheduler.cancel(job)

