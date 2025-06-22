# Ollama installation guide

## Overview

Install instruction for Ollama, working gpu drivers on host required.

**Environment details:**
- **Platform**: Proxmox VE with LXC container
- **Priviledged**: No
- **Container ID**: 620
- **Operating System**: Debian 12 (bookworm) standard template
- **Network**: Services VLAN60 (192.168.60.0/24)
- **Hostname**: ollama.home.federation.fi
- **IP Address**: 192.168.60.80 (static)
- **VLAN ID**: 60
- **DNS server**: 192.168.60.1
- **DNS domain**: home.federation.fi
- **Memory**: 8GB
- **Disk**: 32GB
- **Cores**: 4

## LXC configuration

```bash
ls -al /dev/nvidia*
```

It will output something similar to this for a single GPU (nvidia0) and the universal groups for nvidiactl, nvidia-uvm, nvidia-uvm-tools, nvidia-cap1 and nvidia-cap2. Note the 195, 509 and 234 listed here. Those id’s WILL be different for you and we will note what those are and use them in the next step.

```bash
crw-rw-rw- 1 root root 195,   0 Jun 15 21:21 /dev/nvidia0
crw-rw-rw- 1 root root 195, 255 Jun 15 21:21 /dev/nvidiactl
crw-rw-rw- 1 root root 195, 254 Jun 15 21:21 /dev/nvidia-modeset
crw-rw-rw- 1 root root 511,   0 Jun 15 22:08 /dev/nvidia-uvm
crw-rw-rw- 1 root root 511,   1 Jun 15 22:08 /dev/nvidia-uvm-tools

/dev/nvidia-caps:
total 0
drwxr-xr-x  2 root root     80 Jun 15 22:08 .
drwxr-xr-x 21 root root   7440 Jun 21 21:03 ..
cr--------  1 root root 237, 1 Jun 15 22:08 nvidia-cap1
cr--r--r--  1 root root 237, 2 Jun 15 22:08 nvidia-cap2
```

**Edit container configuration**

```conf
arch: amd64
cores: 4
features: nesting=1
hostname: ollama
memory: 8192
nameserver: 192.168.60.1
net0: name=eth0,bridge=vmbr1,firewall=1,gw=192.168.60.1,hwaddr=BC:24:11:2C:20:EE,ip=192.168.60.80/24,tag=60,type=veth
ostype: debian
rootfs: apps:620/vm-620-disk-0.raw,size=32G
searchdomain: home.federation.fi
swap: 0
unprivileged: 1
lxc.cgroup2.devices.allow: c 195:* rwm
lxc.cgroup2.devices.allow: c 237:* rwm
lxc.cgroup2.devices.allow: c 511:* rwm
lxc.mount.entry: /dev/nvidia0 dev/nvidia0 none bind,optional,create=file
lxc.mount.entry: /dev/nvidiactl dev/nvidiactl none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-modeset dev/nvidia-modeset none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-uvm dev/nvidia-uvm none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-uvm-tools dev/nvidia-uvm-tools none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-caps/nvidia-cap1 dev/nvidia-caps/nvidia-cap1 none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-caps/nvidia-cap2 dev/nvidia-caps/nvidia-cap2 none bind,optional,create=file
```

## Install

**Download (latest) drivers**

Use same driver version which is installed on host system.

```bash
wget https://us.download.nvidia.com/XFree86/Linux-x86_64/535.247.01/NVIDIA-Linux-x86_64-535.247.01.run
```

**Install drivers**

```bash
chmod +x NVIDIA-Linux-x86_64-535.247.01.run

./NVIDIA-Linux-x86_64-535.247.01.run --no-kernel-modules
```

**Install toolkit**

```bash
apt update

apt install gpg curl

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt update

apt install nvidia-container-toolkit
```

**Test drivers**

```
nvidia-smi
```

**Install Ollama**

```bash
curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o ollama-linux-amd64.tgz

tar -C /usr -xzf ollama-linux-amd64.tgz
```

**Systemctl**

```bash
systemctl enable ollama

systemctl start ollama

systemctl status ollama
```

**Nvtop**

```bash
apt install nvtop
```
