class FakeDevice(object):
    def __init__(self, pci_bus, uuid, name):
        self.pci_bus = pci_bus
        self.uuid = uuid
        self.name = name
    def __eq__(self, other):
        return self.uuid == other.uuid
    def __ne__(self, other):
        return self.uuid != other.uuid
    def __str__(self):
        return 'test_%s' % self.uuid
    def __repr__(self):
        return '<test device %s: %s>' % (self.uuid, self.name)
    def __hash__(self):
        return hash(self.uuid)

def get_test_devices():
    return [FakeDevice(1, 'GPU-aabbccdd00', 'Novideo GrillForce RTX 9080'),
            FakeDevice(2, 'GPU-aabbccdd01', 'Ayyti Rayydeon RX 420'),
            FakeDevice(3, 'GPU-aabbccdd02', 'Intlel Grafix')]

def get_test_benchmarks():
    devices = get_test_devices()
    return { devices[0]: { 'excavator_equihash': [300],
                           'excavator_daggerhashimoto_pascal': [25, 400],
                           'excavator_neoscrypt': [750] },
             devices[1]: { 'excavator_equihash': [200],
                           'excavator_daggerhashimoto_pascal': [15, 200],
                           'excavator_neoscrypt': [500] },
             devices[2]: { 'excavator_equihash': [400],
                           'excavator_daggerhashimoto_pascal': [30, 500],
                           'excavator_neoscrypt': [950] } }

