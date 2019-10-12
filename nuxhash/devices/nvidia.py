import subprocess
import xml.etree.ElementTree as ET

class NvidiaDevice(object):
    def __init__(self, pci_bus, uuid, name):
        self.pci_bus = pci_bus
        self.uuid = uuid
        self.name = name
    def __eq__(self, other):
        if isinstance(other, NvidiaDevice):
            return self.uuid == other.uuid
        else:
            return False
    def __ne__(self, other):
        return not self == other
    def __str__(self):
        return f'nvidia_{self.uuid}'
    def __repr__(self):
        return f'<nvidia device {self.uuid}: {self.name}>'
    def __hash__(self):
        return hash(self.uuid)

def enumerate_devices():
    devices = []
    try:
        raw = subprocess.check_output(['nvidia-smi', '--query', '--xml-format'])
        xml = ET.fromstring(raw)
    except OSError as err:
        if err.errno != 2: # file not found
            raise
    else:
        for gpu in xml.findall('gpu'):
            pci_bus = int(gpu.find('pci').find('pci_bus').text, 16)
            uuid = gpu.find('uuid').text
            name = gpu.find('product_name').text
            devices.append(NvidiaDevice(pci_bus, uuid, name))
    return devices

