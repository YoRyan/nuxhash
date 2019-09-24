![logo](https://raw.githubusercontent.com/YoRyan/nuxhash/master/nuxhash/gui/icons/nuxhash_128x128.png)

nuxhash is a [NiceHash](https://nicehash.com) cryptocurrency mining client for
Linux. nuxhash consists of a headless daemon and an optional wxPython-based GUI.
It is currently in beta.

Donations: bc1q2ne5zqa6k5egd82p4rv0rn44tpc35gv3afu52n

## Features

- Miner downloader
- Profit-switching
- Nvidia graphics cards
- NiceHash's proprietary [excavator](https://github.com/nicehash/excavator) miner
- Command-line and (optional) GUI interfaces

![GUI screenshot](https://raw.githubusercontent.com/wiki/YoRyan/nuxhash/gui_alpha.png)

```
nuxhashd initial setup
Wallet address: 3DJBpNcgP3Pihw45p9544PK6TbbYeMcnk7
Worker name: nuxhash
Region (eu/usa/hk/jp/in/br): usa

  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   617    0   617    0     0   1402      0 --:--:-- --:--:-- --:--:--  1402
100 5618k  100 5618k    0     0  1283k      0  0:00:04  0:00:04 --:--:-- 1554k

CUDA device: GeForce GTX 1060 6GB (GPU-452679f3-ba2b-2cfe-4aff-5a50c4a32efb)
  excavator_equihash  .  287.41  H/s (warming up, 23 s)
```

## Dependencies

* Python 3.6 or later
* Nvidia's proprietary graphics driver for Linux, version 387.xx or later
* curl

Optionally, for the GUI interface:

* wxPython 4 for Python 3

## Quick Start

Install the following dependencies (this list is for Ubuntu 18.04 LTS):

* python3
* python3-pip
* curl
* ocl-icd-libopencl1 [(to run CUDA apps)](https://askubuntu.com/questions/1032430/opencl-with-nvidia-390-on-ubunut-18-04)

Optionally, install this package to enable the GUI interface:

* python3-wxgtk4.0

Then, install nuxhash.

```
$ sudo pip3 install git+https://github.com/YoRyan/nuxhash
```

To start the daemon, run `nuxhashd`. To start the graphical interface, run `nuxhash-gui`.

### Donation Fee

nuxhash will donate 0.5% of its mining time to me. If you don't like this, you
may opt out by setting the flag in the configuration file (located by default at
`~/.config/nuxhash/settings.conf`). Currently, there are no penalties if you do
so, but please consider sending me a one-time donation.

## Roadmap

- [x] Daemon with basic mining logic
- [x] Automatic miner downloads and integrity checking
- [X] Finish wx-based GUI
- [ ] Implement other miners
- [ ] Support AMD devices

I have no plans to implement direct overclocking or fan control.
