---
title: Driver Setup
author_profile: true
layout: single
---

![Akbar](/pages/images/akbar.png)

# Intro

The page documents the process of installing the Nvudua driver.

# Check that the GPU Hardware is Detected

```sh
# lspci | grep -i nvidia
02:00.0 VGA compatible controller: NVIDIA Corporation GM204GL [Quadro M4000] (rev a1)
```

# Ensure Non-Free Software Repos and Contrib Repos are Enabled

```sh
root@wintermute:/opt/prod/xmrig # cat /etc/apt/sources.list
deb http://deb.debian.org/debian/ trixie main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian/ trixie main contrib non-free non-free-firmware

deb http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
deb-src http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware

deb http://deb.debian.org/debian/ trixie-updates main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian/ trixie-updates main contrib non-free non-free-firmware
```

# Install Build Tools

To bu8ild the Nvidia kernel version...

```sh
apt install build-essential linux-headers-amd64 cmake libssl-dev python3.13-venv git-lfs python3-dev
```

# Install NVidia Driver

```sh
apt update
apt install nvidia-driver
```

You will likely have to reboot because of a kernel module conflict.

# Install the CUDA Toolkit

```sh
apt install nvidia-cuda-dev nvidia-cuda-toolkit
```

# Confirm Driver 

```sh
# nvidia-smi 
Sat Aug 29 15:53:59 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 550.163.01             Driver Version: 550.163.01     CUDA Version: 12.4     |
|-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  Quadro M4000                   Off |   00000000:02:00.0 Off |                  N/A |
| 62%   49C    P0             38W /  120W |       0MiB /   8192MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
                                                                                         
+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI        PID   Type   Process name                              GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+
```

# Confirm Toolkit

```sh
# nvcc --version
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2024 NVIDIA Corporation
Built on Thu_Mar_28_02:18:24_PDT_2024
Cuda compilation tools, release 12.4, V12.4.131
Build cuda_12.4.r12.4/compiler.34097967_0
```

# Download QWen

```sh
git clone https://github.com/ggml-org/llama.cpp
```

# Build QWen

```sh
cd llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON
cmake --build build --config Release -j 10
```
