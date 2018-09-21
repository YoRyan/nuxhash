import logging
from collections import defaultdict

from nuxhash.switching.switcher import ProfitSwitcher

class NaiveSwitcher(ProfitSwitcher):
    def __init__(self, settings, **kwargs):
        super(NaiveSwitcher, self).__init__(settings, **kwargs)
        # dict of device -> algorithm
        self.last_decision = defaultdict(lambda: None)

    def decide(self, mbtc_per_day_per_device, timestamp):
        decision = {}
        for device, revenues in mbtc_per_day_per_device.items():
            switch_algo, switch_revenue = max(revenues.items(), key=lambda p: p[1])
            stay_algo = self.last_decision[device]

            if stay_algo is None:
                logging.info('Assigning %s to %s (%.3f mBTC/day)' %
                             (device, switch_algo.name, switch_revenue))
                decision[device] = switch_algo
            elif switch_algo != stay_algo:
                stay_revenue = revenues[stay_algo]
                min_factor = 1.0 + self.settings['switching']['threshold']

                if stay_revenue != 0.0 and switch_revenue/stay_revenue >= min_factor:
                    logging.info('Switching %s from %s to %s (%.3f -> %.3f mBTC/day)' %
                                 (device, stay_algo.name, switch_algo.name,
                                  stay_revenue, switch_revenue))
                    decision[device] = switch_algo
                else:
                    decision[device] = stay_algo
            else:
                decision[device] = stay_algo
        self.last_decision = decision
        return decision

