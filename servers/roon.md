# Roon Installation Guide

## Overview


**Environment Details:**
- **Platform**: Proxmox VE with LXC container
- **Priviledged**: Yes
- **Container ID**: 602
- **Operating System**: Debian 12 (bookworm) standard template
- **vmbr0**:
  - **Network**: Services VLAN30 (192.168.30.0/24)
  - **Hostname**: roon.home.federation.fi
  - **IP address**: 192.168.30.10 (static)
  - **VLAN ID**: 30
  - **DNS server**: 192.168.30.1
  - **DNS domain**: home.federation.fi
- **vmbr2**:
  - **Hostname**: sn-roon.home.federation.fi
  - **IP address**: 192.168.200.100 (static)

- **Memory**: 4GB
- **Disk**: 32GB
- **Cores**: max 4

## Config

**fstab**

```conf
# UNCONFIGURED FSTAB FOR BASE SYSTEM
192.168.200.5:/rust/media/music          /media/music   nfs     ro,defaults,users  0       0
```