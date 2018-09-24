class ProfitSwitcher(object):

    def __init__(self, settings):
        # current state of settings
        self.settings = settings

    def reset(self):
        """(Re)initialize the profit-switching logic if necessary."""
        pass

    def decide(self, mbtc_per_day_per_device, timestamp):
        """Read dict of device -> algorithm -> revenue and effective timestamp.

        Return dict of device -> algorithm."""
        pass

