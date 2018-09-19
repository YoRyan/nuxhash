class ProfitSwitcher(object):
    def __init__(self, settings):
        # current state of settings
        self.settings = settings

    def reset(self):
        """(Re)initialize the profit-switching logic if necessary."""
        pass

    def input_revenues(self, mbtc_per_day_per_device, timestamp):
        """Read dict of device -> algorithm -> revenue and effective timestamp."""
        pass

    def assign_algorithms(self):
        """Return dict of device -> algorithm."""
        pass

