# Emby Installation Guide

## Overview


**Environment Details:**
- **Platform**: Proxmox VE with LXC container
- **Container ID**: 603
- **Priviledged**: Yes
- **Installation**: [Proxmox Helper Script](https://community-scripts.github.io/ProxmoxVE/scripts?id=emby)


## Config

**fstab**

```conf
# UNCONFIGURED FSTAB FOR BASE SYSTEM
192.168.200.5:/rust/media/movies          /media/movies   nfs     defaults,users  0       0
192.168.200.5:/rust/media/tv-shows        /media/tv-shows nfs     defaults,users  0       0
```