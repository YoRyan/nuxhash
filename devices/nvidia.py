import subprocess
import xml.etree.ElementTree as ET

class NvidiaDevice(object):
    def __init__(self, cuda_index, uuid, name):
        self.cuda_index = cuda_index
        self.uuid = uuid
        self.name = name
    def __str__(self):
        return 'nvidia_%s' % (self.uuid)
    def __repr__(self):
        return '<nvidia device %s: %s>' % (self.uuid, self.name)
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
            cuda_index = int(gpu.find('minor_number').text)
            uuid = gpu.find('uuid').text
            name = gpu.find('product_name').text
            devices.append(NvidiaDevice(cuda_index, uuid, name))
    return devices

