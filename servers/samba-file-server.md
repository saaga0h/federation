# Samba File Server Installation Guide

## Overview

This document provides step-by-step instructions for installing and configuring a Samba File Server that authenticates against Samba Active Directory. The file server serves ZFS datasets via SMB shares with AD user authentication.

**Environment Details:**
- **Platform**: Proxmox VE with LXC container
- **Priviledged**: Yes
- **Container ID**: 624
- **Operating System**: Debian 12 (bookworm) standard template
- **Network**: Secure VLAN (192.168.20.0/24)
- **Hostname**: samba.home.federation.fi
- **IP Address**: 192.168.20.10 (static)
- **AD Domain**: HOME.FEDERATION.FI (192.168.1.8)
- **Container Type**: Privileged (required for proper file permissions)

---

## Prerequisites

### Active Directory Requirements
- **Samba AD Server**: Running and accessible at 192.168.1.8
- **Domain**: HOME.FEDERATION.FI configured and functional
- **Cross-VLAN connectivity**: Secure VLAN can reach Management VLAN AD services

### ZFS Dataset Structure
The following ZFS datasets will be mounted via bind mounts:
- `/rust/home` → `/home` (User home directories)
- `/rust/media/movies` → `/media/movies` (Movie collection)
- `/rust/media/tv-shows` → `/media/tv-shows` (TV shows)
- `/rust/media/music` → `/media/music` (Music collection)

### Required Firewall Rules
From Secure VLAN (192.168.20.0/24) to Management VLAN (192.168.1.0/24):
- Port 53 (DNS)
- Port 88 (Kerberos)
- Port 389 (LDAP)
- Port 636 (LDAPS)
- Port 445 (SMB for sysvol access)
- Port 464 (Kerberos password changes)

---

## Phase 1: LXC Container Setup

### Container Specifications
- **Template**: Debian 12 standard
- **Container Type**: Privileged (required for file permissions)
- **Memory**: 2GB RAM
- **Storage**: 16GB (minimum)  
- **Network**: Secure VLAN with static IP
- **ZFS Bind Mounts**: Multiple datasets for file sharing

### Create Container with Bind Mounts
```bash
# On Proxmox host - Create container
pct create 101 /var/lib/vz/template/cache/debian-12-standard_12.2-1_amd64.tar.zst \
  --hostname samba \
  --memory 2048 \
  --rootfs local-lvm:16 \
  --net0 name=eth0,bridge=vmbr2,ip=192.168.20.10/24,gw=192.168.20.1,tag=20 \
  --privileged 1 \
  --start 0

# Add ZFS dataset bind mounts
pct set 101 -mp0 /rust/home,mp=/home
pct set 101 -mp1 /rust/media/movies,mp=/media/movies  
pct set 101 -mp2 /rust/media/tv-shows,mp=/media/tv-shows
pct set 101 -mp3 /rust/media/music,mp=/media/music

# Start container
pct start 101
```

### Initial Container Configuration
```bash
# Enter container
pct enter 101

# Update system
apt update && apt upgrade -y

# Set static hostname
hostnamectl set-hostname samba.home.federation.fi
echo "127.0.0.1 samba.home.federation.fi samba" >> /etc/hosts

# Configure DNS to use AD server first
cat > /etc/resolv.conf << EOF
nameserver 192.168.1.8
nameserver 8.8.8.8
search home.federation.fi
domain home.federation.fi
EOF
```

### Test Network and Mounts
```bash
# Test internet connectivity
ping -c 3 google.com

# Test AD server connectivity
ping -c 3 192.168.1.8
nslookup HOME.FEDERATION.FI 192.168.1.8

# Verify ZFS mounts are available
df -h | grep /media
ls -la /home
ls -la /media/movies
ls -la /media/tv-shows
ls -la /media/music

# Verify hostname
hostname -f
# Expected: samba.home.federation.fi
```

---

## Phase 2: Install Samba File Server Packages

### Install Required Packages
```bash
# Install Samba file server and AD integration packages
apt install samba winbind libnss-winbind libpam-winbind krb5-user smbclient -y
```

**Note**: During krb5-user installation, you may be prompted for realm. You can skip as we'll configure manually.

### Test Package Installation
```bash
# Verify Samba version
samba --version
# Expected: Version 4.17.12-Debian

# Check winbind availability
winbindd --version
# Should show winbind version

# Test smbclient
smbclient --version
# Should show smbclient version
```

---

## Phase 3: Configure Kerberos Authentication

### Create Kerberos Configuration
```bash
# Create /etc/krb5.conf for AD authentication
cat > /etc/krb5.conf << EOF
[libdefaults]
    default_realm = HOME.FEDERATION.FI
    dns_lookup_realm = false
    dns_lookup_kdc = true

[realms]
    HOME.FEDERATION.FI = {
        kdc = 192.168.1.8
        admin_server = 192.168.1.8
        default_domain = home.federation.fi
    }

[domain_realm]
    .home.federation.fi = HOME.FEDERATION.FI
    home.federation.fi = HOME.FEDERATION.FI
EOF
```

### Test Kerberos Connectivity
```bash
# Test Kerberos authentication to AD
kinit administrator@HOME.FEDERATION.FI
# Enter AD administrator password

# Verify ticket was obtained
klist
# Should show valid ticket for administrator@HOME.FEDERATION.FI

# Test DNS SRV record resolution
dig -t SRV _kerberos._tcp.HOME.FEDERATION.FI @192.168.1.8
dig -t SRV _ldap._tcp.HOME.FEDERATION.FI @192.168.1.8
# Both should return valid SRV records
```

---

## Phase 4: Configure Samba as Domain Member

### Create Samba Configuration
```bash
# Remove default smb.conf
rm -f /etc/samba/smb.conf

# Create new smb.conf for domain member
cat > /etc/samba/smb.conf << 'EOF'
[global]
    workgroup = FEDERATION
    realm = HOME.FEDERATION.FI
    security = ads
    netbios name = SAMBA
    password server = 192.168.1.8
    
    # Winbind configuration
    winbind use default domain = yes
    winbind offline logon = false
    winbind enum users = yes
    winbind enum groups = yes
    winbind refresh tickets = yes
    
    # ID mapping for AD users
    idmap config * : backend = tdb
    idmap config * : range = 10000-19999
    idmap config FEDERATION : backend = rid
    idmap config FEDERATION : range = 100000-999999
    
    # User template settings
    template homedir = /home/%U
    template shell = /bin/bash
    
    # SMB protocol optimizations
    min protocol = SMB2
    max protocol = SMB3
    
    # Performance settings
    socket options = TCP_NODELAY IPTOS_LOWDELAY SO_RCVBUF=131072 SO_SNDBUF=131072
    use sendfile = yes
    
    # Disable unused services
    disable spoolss = yes
    load printers = no
    printing = bsd
    printcap name = /dev/null

# User home directories
[homes]
    comment = User Home Directories
    browseable = no
    read only = no
    create mask = 0700
    directory mask = 0700
    valid users = %S
    path = /home/%U

# Media shares - read-only for users, write access for admins
[movies]
    comment = Movie Collection
    path = /media/movies
    browseable = yes
    read only = yes
    valid users = @"Media Users", @"Media Admins"
    write list = @"Media Admins"
    admin users = @"Media Admins"
    create mask = 0664
    directory mask = 0775
    force group = "Media Admins"

[tv-shows]
    comment = TV Shows  
    path = /media/tv-shows
    browseable = yes
    read only = yes
    valid users = @"Media Users", @"Media Admins"
    write list = @"Media Admins"
    admin users = @"Media Admins"
    create mask = 0664
    directory mask = 0775
    force group = "Media Admins"

[music]
    comment = Music Collection
    path = /media/music
    browseable = yes
    read only = yes
    valid users = @"Media Users", @"Media Admins"
    write list = @"Media Admins"
    admin users = @"Media Admins"
    create mask = 0664
    directory mask = 0775
    force group = "Media Admins"
EOF
```

### Test Samba Configuration
```bash
# Test configuration syntax
testparm
# Should show no errors and display the configuration

# Check specific sections
testparm -s --section-name=global
testparm -s --section-name=homes
```

---

## Phase 5: Configure NSS and Join Domain

### Configure Name Service Switch
```bash
# Backup original nsswitch.conf
cp /etc/nsswitch.conf /etc/nsswitch.conf.backup

# Configure NSS to use winbind for user/group resolution
sed -i 's/^passwd:.*/passwd:         files winbind/' /etc/nsswitch.conf
sed -i 's/^group:.*/group:          files winbind/' /etc/nsswitch.conf
sed -i 's/^shadow:.*/shadow:         files winbind/' /etc/nsswitch.conf
```

### Join Domain
```bash
# Join the domain using administrator credentials
net ads join -U administrator -W FEDERATION

# Expected output: 
# "Joined 'SAMBA' to dns domain 'home.federation.fi'"
```

### Start Winbind Service
```bash
# Enable and start winbind
systemctl enable winbind
systemctl start winbind
systemctl status winbind
# Should show "active (running)"

# Start SMB services
systemctl enable smbd
systemctl start smbd
systemctl status smbd
# Should show "active (running)"
```

### Test Domain Integration
```bash
# Test domain join status
net ads testjoin
# Should return "Join is OK"

# Test domain user enumeration
wbinfo -u
# Should list AD users: administrator, keycloak-svc, testuser, etc.

# Test domain group enumeration  
wbinfo -g
# Should list AD groups

# Test user resolution
getent passwd administrator
id administrator
# Should show AD user with UID/GID mapping

# Test group resolution
getent group "domain users"
# Should show AD group with members
```

---

## Phase 6: Fix File Permissions

### Identify Permission Mismatches
```bash
# Check existing file ownership in home directories
ls -ln /home/
# Note numeric UID/GID of existing files

# Check AD user mapping
id existinguser
# Compare UID/GID with filesystem ownership
```

### Fix Home Directory Permissions
```bash
# For each existing user with mismatched permissions
# Replace 'username' with actual usernames
for username in user1 user2 user3; do
    if [ -d "/home/$username" ] && id "$username" &>/dev/null; then
        echo "Fixing ownership for $username"
        chown -R "$username:domain users" "/home/$username"
        chmod 755 "/home/$username"
        find "/home/$username" -type d -exec chmod 755 {} \;
        find "/home/$username" -type f -exec chmod 644 {} \;
    fi
done
```

### Fix Media Directory Permissions
```bash
# Set proper ownership for media directories
chown -R root:"Media Admins" /media/movies /media/tv-shows /media/music
chmod -R 775 /media/movies /media/tv-shows /media/music

# Verify permissions
ls -ld /media/movies /media/tv-shows /media/music
```

### Test File Access
```bash
# Test local SMB access
smbclient -L localhost -U administrator
# Should show all shares: homes, movies, tv-shows, music

# Test specific share access
smbclient //localhost/movies -U administrator
# Should connect and allow 'ls' command

# Test user home directory access
smbclient //localhost/administrator -U administrator
# Should connect to administrator's home directory
```

---

## Phase 7: Create Missing Home Directories

### Auto-create Home Directories
```bash
# Install PAM module for automatic home directory creation
apt install libpam-mkhomedir

# Or create homes manually for existing AD users
samba-tool user list | while read user; do
    if [ ! -d "/home/$user" ]; then
        echo "Creating home directory for $user"
        mkdir -p "/home/$user"
        chown "$user:domain users" "/home/$user"
        chmod 700 "/home/$user"
    fi
done
```

### Test Home Directory Creation
```bash
# Test with administrator user
ls -la /home/administrator/
# Should exist with proper ownership

# Test SMB access to home directory
smbclient //localhost/administrator -U administrator -c 'ls'
# Should show home directory contents
```

---

## Phase 8: Configure Advanced Features

### Optional: macOS Compatibility (VFS Fruit)
```bash
# Install additional VFS modules
apt install samba-vfs-modules

# Add to global section in smb.conf (optional)
cat >> /etc/samba/smb.conf << 'EOF'

# macOS compatibility (uncomment if needed)
# fruit:metadata = stream
# fruit:model = MacSamba  
# fruit:veto_appledouble = no
# fruit:posix_rename = yes
# fruit:zero_file_id = yes
EOF
```

### Configure Share-Specific VFS (if needed)
```bash
# Add VFS modules to specific shares (uncomment in smb.conf if needed)
# For each media share, you can add:
# vfs objects = fruit streams_xattr
# fruit:resource = file
# fruit:metadata = stream
```

---

## Phase 9: Test SMB File Server

### Local Testing
```bash
# Test share listing
smbclient -L localhost -U administrator
# Expected shares: homes, movies, tv-shows, music, IPC$

# Test each share individually
smbclient //localhost/movies -U administrator -c 'ls; quit'
smbclient //localhost/tv-shows -U administrator -c 'ls; quit'  
smbclient //localhost/music -U administrator -c 'ls; quit'
smbclient //localhost/administrator -U administrator -c 'ls; quit'

# Test write access (for Media Admins)
smbclient //localhost/movies -U administrator -c 'mkdir test; rmdir test; quit'
# Should succeed if administrator is in Media Admins group
```

### Test Different User Access Levels
```bash
# Test as regular user (read-only access)
smbclient //localhost/movies -U testuser -c 'ls; quit'
# Should work (read access)

smbclient //localhost/movies -U testuser -c 'mkdir test; quit'
# Should fail (no write access for regular users)

# Verify user can access their home directory
smbclient //localhost/testuser -U testuser -c 'ls; quit'
# Should show testuser's home directory
```

### Network Testing from Client
```bash
# From a client machine on Secure VLAN (192.168.20.0/24)
ping 192.168.20.10

# Test SMB connectivity
smbclient -L 192.168.20.10 -U administrator

# Test specific share access from client
smbclient //192.168.20.10/movies -U administrator

# From macOS (in Finder):
# smb://192.168.20.10 or smb://samba.home.federation.fi

# From Windows:
# \\192.168.20.10 or \\samba.home.federation.fi
```

---

## Final Configuration Files

### /etc/samba/smb.conf (Complete Configuration)
```ini
[global]
    workgroup = FEDERATION
    realm = HOME.FEDERATION.FI
    security = ads
    netbios name = SAMBA
    password server = 192.168.1.8
    
    # Winbind configuration
    winbind use default domain = yes
    winbind offline logon = false
    winbind enum users = yes
    winbind enum groups = yes
    winbind refresh tickets = yes
    
    # ID mapping for AD users
    idmap config * : backend = tdb
    idmap config * : range = 10000-19999
    idmap config FEDERATION : backend = rid
    idmap config FEDERATION : range = 100000-999999
    
    # User template settings
    template homedir = /home/%U
    template shell = /bin/bash
    
    # SMB protocol optimizations
    min protocol = SMB2
    max protocol = SMB3
    
    # Performance settings
    socket options = TCP_NODELAY IPTOS_LOWDELAY SO_RCVBUF=131072 SO_SNDBUF=131072
    use sendfile = yes
    
    # Disable unused services
    disable spoolss = yes
    load printers = no
    printing = bsd
    printcap name = /dev/null

[homes]
    comment = User Home Directories
    browseable = no
    read only = no
    create mask = 0700
    directory mask = 0700
    valid users = %S
    path = /home/%U

[movies]
    comment = Movie Collection
    path = /media/movies
    browseable = yes
    read only = yes
    valid users = @"Media Users", @"Media Admins"
    write list = @"Media Admins"
    admin users = @"Media Admins"
    create mask = 0664
    directory mask = 0775
    force group = "Media Admins"

[tv-shows]
    comment = TV Shows  
    path = /media/tv-shows
    browseable = yes
    read only = yes
    valid users = @"Media Users", @"Media Admins"
    write list = @"Media Admins"
    admin users = @"Media Admins"
    create mask = 0664
    directory mask = 0775
    force group = "Media Admins"

[music]
    comment = Music Collection
    path = /media/music
    browseable = yes
    read only = yes
    valid users = @"Media Users", @"Media Admins"
    write list = @"Media Admins"
    admin users = @"Media Admins"
    create mask = 0664
    directory mask = 0775
    force group = "Media Admins"
```

### /etc/krb5.conf (Kerberos Configuration)
```ini
[libdefaults]
    default_realm = HOME.FEDERATION.FI
    dns_lookup_realm = false
    dns_lookup_kdc = true

[realms]
    HOME.FEDERATION.FI = {
        kdc = 192.168.1.8
        admin_server = 192.168.1.8
        default_domain = home.federation.fi
    }

[domain_realm]
    .home.federation.fi = HOME.FEDERATION.FI
    home.federation.fi = HOME.FEDERATION.FI
```

### /etc/resolv.conf (DNS Configuration)
```
nameserver 192.168.1.8
nameserver 8.8.8.8
search home.federation.fi
domain home.federation.fi
```

### /etc/nsswitch.conf (Relevant Lines)
```
passwd:         files winbind
group:          files winbind
shadow:         files winbind
```

---

## Troubleshooting

### Common Issues and Solutions

**1. Domain Join Fails**
```bash
# Check AD server connectivity
ping 192.168.1.8
telnet 192.168.1.8 389

# Test Kerberos authentication
kinit administrator@HOME.FEDERATION.FI

# Check DNS resolution
nslookup HOME.FEDERATION.FI 192.168.1.8

# Try joining with explicit server specification
net ads join -U administrator -S 192.168.1.8
```

**2. Winbind Not Resolving Users**
```bash
# Check winbind status
systemctl status winbind
journalctl -u winbind

# Test domain communication
wbinfo --domain-info FEDERATION
wbinfo -t

# Restart winbind service
systemctl restart winbind

# Clear winbind cache
net cache flush
```

**3. File Permission Issues**
```bash
# Check file ownership
ls -ln /home/username/
id username

# Fix ownership recursively
chown -R username:"domain users" /home/username/

# Check SMB access
smbclient //localhost/username -U username
```

**4. SMB Shares Not Accessible**
```bash
# Test configuration
testparm

# Check SMB service status
systemctl status smbd

# Test local access first
smbclient -L localhost -U administrator

# Check file permissions on share directories
ls -ld /media/movies
```

**5. Cross-VLAN Connectivity Issues**
```bash
# Test network connectivity
ping 192.168.1.8

# Test specific ports
telnet 192.168.1.8 389  # LDAP
telnet 192.168.1.8 88   # Kerberos
telnet 192.168.1.8 445  # SMB

# Check firewall rules on both VLANs
```

---

## Backup and Maintenance

### Backup Configuration
```bash
# Backup Samba configuration
tar -czf /backup/samba-fileserver-config-$(date +%Y%m%d).tar.gz \
  /etc/samba/ \
  /etc/krb5.conf \
  /etc/nsswitch.conf \
  /etc/resolv.conf

# Document mount points
pct config 101 > /backup/lxc-config-$(date +%Y%m%d).txt
```

### Regular Maintenance
```bash
# Check domain membership
net ads testjoin

# Monitor service status
systemctl status winbind smbd

# Check disk usage on mounted datasets
df -h | grep /media

# Monitor SMB connections
smbstatus

# Check winbind cache
wbinfo -u | wc -l
wbinfo -g | wc -l
```

### Performance Monitoring
```bash
# Monitor SMB activity
tail -f /var/log/samba/log.smbd

# Check system resources
htop
iostat 1 3

# Monitor network activity
iftop -i eth0
```

---

## Validation Checklist

- [ ] LXC container created with privileged mode and correct network
- [ ] ZFS datasets mounted via bind mounts at correct paths
- [ ] Network connectivity to AD server working
- [ ] Kerberos authentication to AD successful
- [ ] Domain join completed successfully
- [ ] Winbind resolving AD users and groups
- [ ] NSS integration working (`getent passwd administrator`)
- [ ] SMB services running and listening
- [ ] All shares accessible locally via smbclient
- [ ] File permissions fixed for existing data
- [ ] Home directories created for AD users
- [ ] Cross-VLAN client access working
- [ ] Different user access levels working correctly
- [ ] Performance acceptable for file operations

---

## Client Connection Examples

### Windows Client
```
# Map network drive
\\samba.home.federation.fi\movies
\\192.168.20.10\movies

# Access user home
\\samba.home.federation.fi\username
```

### macOS Client
```bash
# Connect to server in Finder
smb://samba.home.federation.fi
smb://192.168.20.10

# Command line mount
mount -t smbfs //administrator@192.168.20.10/movies /mnt/movies
```

### Linux Client
```bash
# Install SMB client
apt install cifs-utils

# Mount share
mount -t cifs //192.168.20.10/movies /mnt/movies -o username=administrator,domain=FEDERATION

# Or use smbclient
smbclient //192.168.20.10/movies -U administrator
```

---

## Next Steps

1. **Test client access** - Verify Windows/macOS/Linux clients can connect
2. **Performance tuning** - Optimize for your specific workload
3. **Additional shares** - Create department or project-specific shares
4. **Backup strategy** - Configure regular backups of file server configuration
5. **Monitoring** - Set up monitoring for service health and performance
6. **Documentation** - Document share purposes and access controls for users

---

## Support Information

**File Server Details:**
- Hostname: samba.home.federation.fi (192.168.20.10)
- Domain: FEDERATION (HOME.FEDERATION.FI)
- AD Server: 192.168.1.8
- Network: Secure VLAN (192.168.20.0/24)

**Key Services:**
- SMB/CIFS: Port 445
- Winbind: AD user/group resolution
- Mount Points: ZFS datasets via bind mounts

**Troubleshooting Commands:**
- Service status: `systemctl status smbd winbind`
- Domain status: `net ads testjoin`
- User resolution: `wbinfo -u` and `getent passwd`
- Share testing: `smbclient -L localhost -U administrator`
- Configuration test: `testparm`

This completes the Samba File Server installation and configuration documentation.