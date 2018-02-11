import re
import subprocess

class Device(object):
    def __init__(self, driver, index, name):
        self.driver = driver
        self.index = index
        self.name = name
    def __str__(self):
        return '%s_%d' % (self.driver, self.index)
    def __repr__(self):
        return '<%s device #%d: %s>' % (self.driver, self.index, self.name)
    def __hash__(self):
        return hash(self.driver) + hash(self.name) + self.index

def enumerate_devices():
    return enumerate_nvidia_devices()

def enumerate_nvidia_devices():
    devices = []
    try:
        smi = subprocess.check_output(['nvidia-smi', '--list-gpus'])
    except OSError as err:
        if err.errno != 2: # file not found
            raise
    else:
        for line in smi.splitlines():
            result = re.match(r'GPU (\d+): ([\w ]+) \(', line)
            devices.append(Device('nvidia', int(result.group(1)), result.group(2)))
    return devices

