# Immixh installation guide

## Overview


**Environment Details:**
- **Platform**: Proxmox VE with LXC container
- **Priviledged**: Yes
- **Container ID**: 623
- **Installation**: [Proxmox Helper Script](https://community-scripts.github.io/ProxmoxVE/scripts?id=immich)

## Config

**fstab**

```conf
# UNCONFIGURED FSTAB FOR BASE SYSTEM
sn-nfs.home.federation.fi:/rust/media/photos          /media/photos   nfs     ro,defaults,users  0       0
```