# Samba Active Directory Installation Guide

## Overview

This document provides step-by-step instructions for installing and configuring Samba Active Directory Domain Controller on Proxmox LXC container.

**Environment Details:**
- **Platform**: Proxmox VE with LXC container
- **Priviledged**: Yes
- **Container ID**: 628
- **Operating System**: Debian 12 (bookworm) standard template
- **Network**: Management VLAN1 (192.168.1.0/24)
- **Domain**: HOME.FEDERATION.FI
- **NetBIOS Domain**: FEDERATION
- **Hostname**: ad.home.federation.fi
- **IP Address**: 192.168.1.8 (static)

---

## Prerequisites

### Network Architecture
- **Management VLAN**: Core infrastructure services (DNS, AD, Proxmox)
- **Secure VLAN**: User systems and file servers
- **Services VLAN**: Web services and applications
- **Cross-VLAN firewall rules**: Allow authentication traffic from other VLANs to Management VLAN

### Required Firewall Rules
From Secure/Services VLANs to Management VLAN (AD server):
- Port 53 (DNS)
- Port 88 (Kerberos)
- Port 389 (LDAP)
- Port 636 (LDAPS)
- Port 445 (SMB)
- Port 464 (Kerberos password changes)

---

## Phase 1: LXC Container Setup

### Container Specifications
- **Template**: Debian 12 standard
- **Container Type**: Privileged
- **Memory**: 4GB RAM
- **Storage**: 32GB (minimum)
- **Network**: Management VLAN with static IP
- **Features**: Nesting disabled, Keyctl disabled

### Create Container
```bash
# On Proxmox host
pct create 100 /var/lib/vz/template/cache/debian-12-standard_12.2-1_amd64.tar.zst \
  --hostname ad \
  --memory 4096 \
  --rootfs local-lvm:32 \
  --net0 name=eth0,bridge=vmbr1,ip=192.168.1.8/24,gw=192.168.1.1,tag=10 \
  --privileged 1 \
  --start 1
```

### Initial Container Configuration
```bash
# Enter container
pct enter 100

# Update system
apt update && apt upgrade -y

# Set static hostname
hostnamectl set-hostname ad.home.federation.fi
echo "127.0.0.1 ad.home.federation.fi ad" >> /etc/hosts

# Configure DNS resolution
cat > /etc/resolv.conf << EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
search home.federation.fi
domain home.federation.fi
EOF
```

### Test Network Connectivity
```bash
# Test internet connectivity
ping -c 3 google.com

# Test DNS resolution
nslookup google.com

# Verify hostname
hostname -f
# Expected: ad.home.federation.fi
```

---

## Phase 2: Install Samba AD Packages

### Install Required Packages
```bash
# Install Samba AD and dependencies
apt install samba samba-ad-dc winbind libnss-winbind krb5-user smbclient ldb-tools python3-pycryptodome chrony -y
```

**Note**: During installation, you'll be prompted for Kerberos realm configuration. You can skip this as we'll configure it manually later.

### Disable Conflicting Services
```bash
# Disable standard Samba services (we'll use samba-ad-dc)
systemctl disable samba smbd nmbd winbind
systemctl mask samba smbd nmbd winbind
```

### Test Package Installation
```bash
# Verify Samba version
samba --version
# Expected: Version 4.17.12-Debian

# Check if samba-tool is available
samba-tool --help
# Should show samba-tool command options
```

---

## Phase 3: Configure Kerberos

### Create Kerberos Configuration
```bash
# Create /etc/krb5.conf
cat > /etc/krb5.conf << EOF
[libdefaults]
    default_realm = HOME.FEDERATION.FI
    dns_lookup_realm = false
    dns_lookup_kdc = true

[realms]
    HOME.FEDERATION.FI = {
        kdc = localhost
        admin_server = localhost
        default_domain = home.federation.fi
    }

[domain_realm]
    .home.federation.fi = HOME.FEDERATION.FI
    home.federation.fi = HOME.FEDERATION.FI
EOF
```

### Remove Existing Samba Configuration
```bash
# Remove default smb.conf (will be recreated during provisioning)
rm -f /etc/samba/smb.conf
```

---

## Phase 4: Provision Samba AD Domain

### Domain Provisioning
```bash
# Provision the domain
samba-tool domain provision \
  --realm=HOME.FEDERATION.FI \
  --domain=FEDERATION \
  --server-role=dc \
  --dns-backend=SAMBA_INTERNAL \
  --adminpass=YourStrongAdminPassword

# Example output should show:
# - Domain provisioned successfully
# - Administrator password set
# - DNS domain configured
```

### Copy Kerberos Configuration
```bash
# Copy Samba-generated Kerberos config to system location
cp /var/lib/samba/private/krb5.conf /etc/krb5.conf
```

### Test Domain Provisioning
```bash
# Check if domain was created
ls -la /var/lib/samba/private/
# Should see sam.ldb, secrets.ldb, and other database files

# Test Samba configuration
testparm
# Should show valid configuration without errors
```

---

## Phase 5: Configure and Start Services

### Enable Samba AD Service
```bash
# Enable and start samba-ad-dc
systemctl unmask samba-ad-dc
systemctl enable samba-ad-dc
systemctl start samba-ad-dc
```

### Configure Time Synchronization
```bash
# Configure chrony for AD time synchronization
echo "ntpsigndsocket /var/lib/samba/ntp_signd/" >> /etc/chrony/chrony.conf

# Set proper permissions
chown root:_chrony /var/lib/samba/ntp_signd/
chmod 750 /var/lib/samba/ntp_signd/

# Restart chrony
systemctl restart chrony
```

### Test Service Status
```bash
# Check samba-ad-dc status
systemctl status samba-ad-dc
# Should show "active (running)"

# Check if services are listening on correct ports
netstat -tlnp | grep :53    # DNS
netstat -tlnp | grep :88    # Kerberos
netstat -tlnp | grep :389   # LDAP
netstat -tlnp | grep :445   # SMB

# Check for any startup errors
journalctl -u samba-ad-dc --no-pager
```

---

## Phase 6: Test Authentication and DNS

### Test Kerberos Authentication
```bash
# Get Kerberos ticket for administrator
kinit administrator
# Enter the password you set during provisioning

# List active tickets
klist
# Should show valid ticket for administrator@HOME.FEDERATION.FI

# Test DNS SRV records
dig -t SRV _ldap._tcp.HOME.FEDERATION.FI @localhost
dig -t SRV _kerberos._tcp.HOME.FEDERATION.FI @localhost
# Both should return valid SRV records pointing to ad.home.federation.fi
```

### Test SMB Functionality
```bash
# Test SMB shares
smbclient -L localhost -U administrator
# Should show sysvol and netlogon shares

# Test basic domain functionality
smbclient //localhost/netlogon -U administrator -c 'ls'
# Should list netlogon share contents
```

### Test DNS Resolution
```bash
# Test domain resolution
nslookup HOME.FEDERATION.FI localhost
nslookup ad.home.federation.fi localhost

# Test reverse DNS (if configured)
nslookup 192.168.1.8 localhost
```

---

## Phase 7: Create Initial Users and Groups

### Create Test Users
```bash
# Create a test user
samba-tool user create testuser \
  --given-name="Test" \
  --surname="User" \
  --mail-address="testuser@home.federation.fi"

# Create service account for Keycloak
samba-tool user create keycloak-svc \
  --given-name="Keycloak" \
  --surname="Service" \
  --description="Keycloak LDAP Service Account"

# Set service account password to not expire
samba-tool user setexpiry keycloak-svc --noexpiry
```

### Create Groups
```bash
# Create media management groups
samba-tool group add "Media Admins" --description="Can manage media files"
samba-tool group add "Media Users" --description="Can view media files"

# Add users to groups
samba-tool group addmembers "Media Admins" administrator
samba-tool group addmembers "Media Users" testuser
samba-tool group addmembers "Users" keycloak-svc
```

### Test User Management
```bash
# List all users
samba-tool user list

# List all groups
samba-tool group list

# Show user details
samba-tool user show testuser

# Test group membership
samba-tool group listmembers "Media Admins"
```

---

## Phase 8: Configure DNS Resolution

### Update System DNS
```bash
# Update /etc/resolv.conf to use local AD for DNS
cat > /etc/resolv.conf << EOF
nameserver 127.0.0.1
nameserver 8.8.8.8
search home.federation.fi
domain home.federation.fi
EOF
```

### Test DNS Configuration
```bash
# Test internal DNS resolution
nslookup ad.home.federation.fi
# Should resolve to 192.168.1.8

# Test external DNS resolution
nslookup google.com
# Should resolve to external IP

# Test SRV record resolution
dig -t SRV _ldap._tcp.home.federation.fi
# Should return SRV record for ad.home.federation.fi
```

---

## Phase 9: Verify Cross-VLAN Connectivity

### Test from Other VLANs
```bash
# From Secure VLAN (192.168.20.0/24), test AD connectivity
ping 192.168.1.8
nslookup HOME.FEDERATION.FI 192.168.1.8
telnet 192.168.1.8 389  # LDAP
telnet 192.168.1.8 88   # Kerberos

# Test Kerberos authentication from remote VLAN
kinit administrator@HOME.FEDERATION.FI
```

---

## Final Configuration Files

### /etc/samba/smb.conf (Generated by Provisioning)
```ini
# Global parameters
[global]
    dns forwarder = 8.8.8.8
    netbios name = AD
    realm = HOME.FEDERATION.FI
    server role = active directory domain controller
    workgroup = FEDERATION
    idmap_ldb:use rfc2307 = yes

[sysvol]
    path = /var/lib/samba/sysvol
    read only = No

[netlogon]
    path = /var/lib/samba/sysvol/home.federation.fi/scripts
    read only = No
```

### /etc/krb5.conf (Final Configuration)
```ini
[libdefaults]
    default_realm = HOME.FEDERATION.FI
    dns_lookup_realm = false
    dns_lookup_kdc = true

[realms]
    HOME.FEDERATION.FI = {
        kdc = localhost
        admin_server = localhost
        default_domain = home.federation.fi
    }

[domain_realm]
    .home.federation.fi = HOME.FEDERATION.FI
    home.federation.fi = HOME.FEDERATION.FI
```

---

## Troubleshooting

### Common Issues and Solutions

**1. DNS Errors During Startup**
```bash
# Check logs for DNS update errors
journalctl -u samba-ad-dc | grep -i dns

# These are usually harmless if basic functionality works
# Test with: smbclient -L localhost -U administrator
```

**2. Kerberos Authentication Fails**
```bash
# Check time synchronization (critical for Kerberos)
date
timedatectl status

# Verify krb5.conf configuration
kinit administrator
# If fails, check /etc/krb5.conf syntax
```

**3. Service Won't Start**
```bash
# Check service status and logs
systemctl status samba-ad-dc
journalctl -u samba-ad-dc --no-pager

# Common issue: incorrect permissions on database files
chown -R root:root /var/lib/samba/private/
```

**4. Cross-VLAN Connectivity Issues**
```bash
# Test network connectivity
ping 192.168.1.8

# Test specific ports
telnet 192.168.1.8 389
telnet 192.168.1.8 88

# Check firewall rules on both sides
```

---

## Backup and Maintenance

### Backup Domain
```bash
# Create offline backup
samba-tool domain backup offline --targetdir=/backup/samba-ad/$(date +%Y%m%d)

# Backup configuration files
tar -czf /backup/samba-config-$(date +%Y%m%d).tar.gz \
  /etc/samba/ \
  /etc/krb5.conf \
  /etc/resolv.conf
```

### Regular Maintenance
```bash
# Check domain health
samba-tool domain level show
samba-tool user list | wc -l

# Update DNS forwarders if needed
samba-tool dns serverinfo localhost

# Monitor logs for issues
journalctl -u samba-ad-dc --since "24 hours ago" | grep -i error
```

---

## Validation Checklist

- [ ] LXC container created with correct specifications
- [ ] Network connectivity working (internet and cross-VLAN)
- [ ] Samba AD packages installed successfully
- [ ] Domain provisioned without errors
- [ ] Kerberos authentication working (`kinit administrator`)
- [ ] DNS SRV records resolving correctly
- [ ] SMB shares accessible (`smbclient -L localhost`)
- [ ] Services listening on correct ports (53, 88, 389, 445)
- [ ] Time synchronization configured
- [ ] Test users and groups created
- [ ] Cross-VLAN connectivity verified
- [ ] Backup strategy implemented

---

## Next Steps

1. **Configure SMB File Server** - Join domain member server for file sharing
2. **Set up Keycloak** - Configure LDAP federation for SSO
3. **Join client systems** - Windows/Linux domain join procedures
4. **Implement backup strategy** - Regular domain and configuration backups
5. **Monitor and maintain** - Regular health checks and updates

---

## Support Information

**Domain Details:**
- Domain: HOME.FEDERATION.FI
- NetBIOS: FEDERATION
- DC: ad.home.federation.fi (192.168.1.8)
- Administrator: administrator@HOME.FEDERATION.FI

**Key Commands:**
- Domain management: `samba-tool domain`
- User management: `samba-tool user`
- Group management: `samba-tool group`
- DNS management: `samba-tool dns`
- Configuration test: `testparm`
- Service logs: `journalctl -u samba-ad-dc`

This completes the Samba Active Directory installation and configuration for your environment.