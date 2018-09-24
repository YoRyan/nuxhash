import os
import subprocess
from pathlib import Path
from shutil import rmtree


DOWNLOADS_PATH = Path(os.path.dirname(__file__))/'downloadables'


class Downloadable(object):

    def __init__(self, config_dir, dir_name, script_name, name):
        self.dir = config_dir/dir_name
        self.script = DOWNLOADS_PATH/script_name
        self.name = name

    def run_script(self, *args):
        return subprocess.call([self.script] + list(args), cwd=self.dir)

    def verify(self):
        if self.dir.is_dir():
            return self.run_script('verify') == 0
        else:
            return False

    def download(self):
        if not self.dir.is_dir():
            os.makedirs(self.dir)
        for child in self.dir.iterdir():
            if child.is_dir():
                rmtree(child)
            else:
                os.remove(child)
        self.run_script('download')


def make_miners(config_dir):
    return [
        Downloadable(config_dir, 'excavator', 'excavator.sh', 'NiceHash excavator')
        ]

