![logo](https://raw.githubusercontent.com/YoRyan/nuxhash/master/nuxhash/gui/icons/nuxhash_128x128.png)

nuxhash is a [NiceHash](https://nicehash.com) cryptocurrency mining client for
Linux. nuxhash consists of a headless daemon and an optional wxPython-based GUI.
It is currently in beta.

![GUI screenshot](https://raw.githubusercontent.com/wiki/YoRyan/nuxhash/gui_alpha.png)

## Features

- Miner downloader
- Profit-switching
- Nvidia graphics cards
- NiceHash's proprietary [excavator](https://github.com/nicehash/excavator) miner
- Command-line and (optional) GUI interfaces

## Quick Start

Install the following dependencies (this list is for Ubuntu 18.04 LTS):

* Python 3.6
* Nvidia's proprietary graphics driver for Linux, version 387.xx or later
* curl (to download excavator)
* ocl-icd-libopencl1 [(to run CUDA apps)](https://askubuntu.com/questions/1032430/opencl-with-nvidia-390-on-ubunut-18-04)

Optionally, install this to enable the GUI interface:

* python3-wxgtk4.0

Then, install nuxhash.

```
sudo apt install python3-pip
sudo pip3 install git+https://github.com/YoRyan/nuxhash
```

To start the daemon, run `nuxhashd`. To start the graphical interface, run `nuxhash-gui`.

## Roadmap

- [x] Daemon with basic mining logic
- [x] Automatic miner downloads and integrity checking
- [X] Finish wx-based GUI
- [ ] Implement other miners
- [ ] Support AMD devices

I have no plans to implement direct overclocking or fan control.
