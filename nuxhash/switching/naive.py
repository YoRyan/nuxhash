import logging
from collections import defaultdict

from nuxhash.switching.switcher import ProfitSwitcher


class NaiveSwitcher(ProfitSwitcher):

    def __init__(self, settings, **kwargs):
        super(NaiveSwitcher, self).__init__(settings, **kwargs)
        # dict of device -> algorithm
        self.last_decision = defaultdict(lambda: None)

    def decide(self, btc_per_day_per_device, timestamp):
        decision = {}
        for device, revenues in btc_per_day_per_device.items():
            switch_algo, switch_revenue = max(revenues.items(), key=lambda p: p[1])
            stay_algo = self.last_decision[device]

            if stay_algo is None:
                logging.info(f'Assigning {device} to {switch_algo.name} '
                             + f'({round(switch_revenue, ndigits=3)} mBTC/day)')
                decision[device] = switch_algo
            elif switch_algo != stay_algo:
                stay_revenue = revenues[stay_algo]
                min_factor = 1.0 + self.settings['switching']['threshold']

                if stay_revenue != 0.0 and switch_revenue/stay_revenue >= min_factor:
                    logging.info(f'Switching {device} from {stay_algo.name} '
                                 + f'to {switch_algo.name} ({stay_revenue:.3f} '
                                 + f'-> {switch_revenue:.3f} mBTC/day)')
                    decision[device] = switch_algo
                else:
                    decision[device] = stay_algo
            else:
                decision[device] = stay_algo
        self.last_decision = decision
        return decision

