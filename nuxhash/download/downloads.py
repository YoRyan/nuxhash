import os
import subprocess
from pathlib2 import Path
from shutil import rmtree

downloads_path = Path(os.path.dirname(__file__))/'downloadables'

class Downloadable(object):
    def __init__(self, config_dir, dir_name, script_name, name):
        self.dir = config_dir/dir_name
        self.script = downloads_path/script_name
        self.name = name
    def run_script(self, *args):
        return subprocess.call([str(self.script)] + list(args), cwd=str(self.dir))
    def verify(self):
        if self.dir.is_dir():
            return self.run_script('verify') == 0
        else:
            return False
    def download(self):
        if not self.dir.is_dir():
            os.makedirs(str(self.dir))
        for child in self.dir.iterdir():
            if child.is_dir():
                rmtree(str(child))
            else:
                os.remove(str(child))
        self.run_script('download')

def make_miners(config_dir):
    return [Downloadable(config_dir, 'excavator', 'excavator.sh', 'NiceHash excavator')]

