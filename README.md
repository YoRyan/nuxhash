nuxhash is a [NiceHash](https://nicehash.com) cryptocurrency mining client for
Linux. Like NiceHash's official Windows software, it uses NiceHash's proprietary
[excavator](https://github.com/nicehash/excavator) program to perform hashes of
the most profitable algorithm(s) for each card.

At the moment, nuxhash is super-early alpha software, but it's already usable
for headless mining on Nvidia cards. A GUI version is in progress.

![GUI screenshot](https://raw.githubusercontent.com/wiki/YoRyan/nuxhash/gui_alpha.png)

## Roadmap

- [x] Daemon with basic mining logic
- [x] Automatic miner downloads and integrity checking
- [ ] Finish wx-based GUI
- [ ] Implement other miners
- [ ] Support AMD devices
- [ ] Add 0.5% donation fee (opt-out)

I have no plans to implement direct overclocking or fan control.

## Quick Start (daemon)

External dependencies, Ubuntu 18.04 LTS:

* Python 3.6
* Nvidia's proprietary graphics driver for Linux, version 387.xx or later
* curl (to download excavator)
* ocl-icd-libopencl1 [(to run CUDA apps)](https://askubuntu.com/questions/1032430/opencl-with-nvidia-390-on-ubunut-18-04)

Install Python package.

```
python3 setup.py install
```

Perform initial setup, run benchmarks (approx. 5 minutes/algorithm/card).

```
$ nuxhashd --benchmark-all
nuxhashd initial setup
Wallet address: 3Qe7nT9hBSVoXr8rM2TG6pq82AmLVKHy23
Worker name: nuxhashdev
Region (eu/usa/hk/jp/in/br): usa

Querying NiceHash for miner connection information...

CUDA device 0: GeForce GTX 1060 6GB
  excavator_equihash: 318.95  H/s
  excavator_pascal: 749.24 MH/s
  excavator_decred:   1.92 GH/s
  excavator_sia:   1.19 GH/s
  excavator_lbry: 199.19 MH/s
  excavator_blake2s:   2.79 GH/s
  excavator_daggerhashimoto:  20.41 MH/s
  excavator_lyra2rev2:  28.60 MH/s
  excavator_daggerhashimoto_decred:  19.83 MH/s, 713.77 MH/s
  excavator_daggerhashimoto_sia:  20.62 MH/s, 263.89 MH/s
  excavator_daggerhashimoto_pascal:   8.79 MH/s, 492.29 MH/s
  excavator_cryptonight: 422.90  H/s
  excavator_keccak: 568.92 MH/s
  excavator_neoscrypt: 798.90 kH/s
  excavator_nist5:  33.38 MH/s
```

Go mining. Remove `--show-mining` for silent operation.

```
$ nuxhashd --show-mining
2018-02-11 15:52:23,339 INFO: Querying NiceHash for miner connection information...
2018-02-11 15:52:23,646 DEBUG: =========================== www.nicehash.com =========================
2018-02-11 15:52:23,646 DEBUG:            Excavator v1.4.3a_nvidia GPU Miner for NiceHash.
2018-02-11 15:52:23,646 DEBUG:            Copyright (C) 2018 NiceHash. All rights reserved.
2018-02-11 15:52:23,646 DEBUG:                               Developed by
2018-02-11 15:52:23,646 DEBUG:          djeZo, dropky, voidstar, and agiz
2018-02-11 15:52:23,646 DEBUG:                    with help and contributions from
2018-02-11 15:52:23,646 DEBUG:            zawawa, pallas, Vorksholk, bitbandi, ocminer, and Genoil.
2018-02-11 15:52:23,646 DEBUG: =========================== www.nicehash.com =========================
2018-02-11 15:52:23,646 DEBUG: Build time: 2018-02-02 11:22:18+01:00
2018-02-11 15:52:23,646 DEBUG: Build number: 900883172
2018-02-11 15:52:23,646 DEBUG: [15:52:23][0x00007f822ae21b80][info] Log started
2018-02-11 15:52:23,658 DEBUG: [15:52:23][0x00007f822ae21b80][info] core | Found CUDA device: GeForce GTX 1060 6GB
2018-02-11 15:52:23,751 DEBUG: [15:52:23][0x00007f822ae21b80][info] api | Listening on 127.0.0.1:3456
2018-02-11 15:52:23,751 DEBUG: [15:52:23][0x00007f822ae21b80][info] core | Initialized!
2018-02-11 15:52:24,640 INFO: Assigning nvidia_0 to excavator_neoscrypt (0.173 mBTC/day)
2018-02-11 15:52:24,644 DEBUG: [15:52:24][0x00007f8225d55700][info] net | Connecting to 169.62.79.78:3341 (neoscrypt.usa.nicehash.com)
2018-02-11 15:52:24,694 DEBUG: [15:52:24][0x00007f8226556700][info] net | Connected!
2018-02-11 15:52:24,779 DEBUG: [15:52:24][0x00007f82091e5700][info] wrkr0-0 | Algorithm: CUDA-neoscrypt parameters: B=440
2018-02-11 15:52:24,798 DEBUG: [15:52:24][0x00007f8225d55700][info] net | Authorized as 3Qe7nT9hBSVoXr8rM2TG6pq82AmLVKHy23.ATXcavator
2018-02-11 15:52:24,829 DEBUG: [15:52:24][0x00007f8225d55700][info] algo-neoscrypt | New job_0 '00000017bf8b2202', diff=0.0625
2018-02-11 15:52:36,192 DEBUG: [15:52:36][0x00007f8226556700][info] algo-neoscrypt | New job_0 '00000017bf8ba41c', diff=0.0625
2018-02-11 15:52:52,931 DEBUG: [15:52:52][0x00007f8225d55700][info] algo-neoscrypt | New job_0 '00000017bf8c1e17', diff=0.0625
2018-02-11 15:53:07,428 DEBUG: [15:53:07][0x00007f8225d55700][info] algo-neoscrypt | New job_0 '00000017bf8c743b', diff=0.0625
2018-02-11 15:53:37,398 DEBUG: [15:53:37][0x00007f8226556700][info] algo-neoscrypt | New job_0 '00000017bf8d2256', diff=0.0625
2018-02-11 15:53:54,492 DEBUG: [15:53:54][0x00007f8225d55700][info] algo-neoscrypt | New job_0 '00000017bf8d7aa2', diff=0.0625
2018-02-11 15:53:57,493 DEBUG: [15:53:57][0x00007f8226556700][info] algo-neoscrypt | New job_0 '00000017bf8dc39e', diff=0.0625
2018-02-11 15:54:11,509 DEBUG: [15:54:11][0x00007f8225d55700][info] algo-neoscrypt | New job_0 '00000017bf8e1917', diff=0.0625
2018-02-11 15:54:27,527 DEBUG: [15:54:27][0x00007f8226556700][info] algo-neoscrypt | New job_0 '00000017bf8e5396', diff=0.0625
2018-02-11 15:55:04,577 DEBUG: [15:55:04][0x00007f8225d55700][info] algo-neoscrypt | New job_0 '00000017bf8edd67', diff=0.0625
2018-02-11 15:55:10,592 DEBUG: [15:55:10][0x00007f8226556700][info] algo-neoscrypt | New job_0 '00000017bf8f2565', diff=0.0625
2018-02-11 15:55:17,594 DEBUG: [15:55:17][0x00007f8225d55700][info] algo-neoscrypt | New job_0 '00000017bf8f5e66', diff=0.0625
2018-02-11 15:55:17,838 DEBUG: [15:55:17][0x00007f8225d55700][info] algo-neoscrypt | New job_0 '00000017bf8f69da', diff=0.0625
2018-02-11 15:56:06,527 DEBUG: [15:56:06][0x00007f8225d55700][info] algo-neoscrypt | New job_0 '00000017bf8ff67f', diff=0.03125
2018-02-11 15:57:09,724 DEBUG: [15:57:09][0x00007f8226556700][info] algo-neoscrypt | New job_0 '00000017bf90d2b5', diff=0.03125
2018-02-11 15:57:33,820 DEBUG: [15:57:33][0x00007f8225d55700][info] net | Share #10 accepted
```

## Quick Start (graphical) (coming soon)

External dependencies, Ubuntu 18.04 LTS:

* python3-wxgtk4.0

Install Python package.

```
python3 setup.py install
```

Try it out.

```
nuxhash-gui
```
