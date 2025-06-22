# Samba AD Cheat Sheet

## User Management

### Create Users
```bash
# Basic user
samba-tool user create username

# User with details
samba-tool user create username --given-name="First" --surname="Last" --mail-address="user@domain.com"

# User with non-expiring password
samba-tool user create username --password="password" --must-change-at-next-login
samba-tool user setexpiry username --noexpiry
```

### Manage Users
```bash
# List all users
samba-tool user list

# Show user details
samba-tool user show username

# Set password
samba-tool user setpassword username --newpassword="newpassword"

# Set password to not expire
samba-tool user setexpiry username --noexpiry

# Enable/disable user
samba-tool user enable username
samba-tool user disable username

# Delete user
samba-tool user delete username

# Edit user (opens editor)
samba-tool user edit username
```

### Reset User Password
```bash
# Interactive password change
samba-tool user setpassword username

# Set specific password
samba-tool user setpassword username --newpassword="password123"

# Force password change at next login
samba-tool user setpassword username --must-change-at-next-login
```

## Group Management

### Create Groups
```bash
# Create group
samba-tool group add "Group Name" --description="Group description"

# Example groups
samba-tool group add "IT Admins" --description="IT administrators"
samba-tool group add "Media Admins" --description="Can manage media files"
```

### Manage Groups
```bash
# List all groups
samba-tool group list

# Show group details
samba-tool group show "Group Name"

# Add members to group
samba-tool group addmembers "Group Name" username1,username2,username3

# Remove members from group
samba-tool group removemembers "Group Name" username1,username2

# List group members
samba-tool group listmembers "Group Name"

# Delete group
samba-tool group delete "Group Name"
```

## DNS Management

### DNS Records
```bash
# List DNS zones
samba-tool dns zonelist localhost

# List records in zone
samba-tool dns query localhost domain.com @ ALL

# Add A record
samba-tool dns add localhost domain.com hostname A 192.168.1.100 -U administrator

# Add CNAME record
samba-tool dns add localhost domain.com alias CNAME hostname.domain.com -U administrator

# Delete record
samba-tool dns delete localhost domain.com hostname A 192.168.1.100 -U administrator

# Show specific record
samba-tool dns query localhost domain.com hostname A
```

### DNS Troubleshooting
```bash
# Test SRV records
dig -t SRV _ldap._tcp.domain.com @localhost
dig -t SRV _kerberos._tcp.domain.com @localhost

# Test DNS resolution
nslookup hostname.domain.com localhost
```

## Domain Information

### Domain Status
```bash
# Check domain level
samba-tool domain level show

# Show domain info
samba-tool domain info localhost

# Check replication (multi-DC)
samba-tool drs showrepl

# Test domain join
net ads testjoin
```

### Domain Backup/Restore
```bash
# Backup domain
samba-tool domain backup offline --targetdir=/backup/path

# Backup with specific backend
samba-tool domain backup online --server=DC_NAME --targetdir=/backup/path -U administrator
```

## Computer/Machine Management

### Join Domain
```bash
# Join domain (from member server)
net ads join -U administrator

# Join with specific workgroup
net ads join -U administrator -W WORKGROUP

# Leave domain
net ads leave -U administrator
```

### Computer Accounts
```bash
# List computer accounts
samba-tool computer list

# Create computer account
samba-tool computer create computername

# Delete computer account
samba-tool computer delete computername

# Show computer details
samba-tool computer show computername
```

## Kerberos & Authentication

### Kerberos Testing
```bash
# Get ticket
kinit administrator@DOMAIN.COM

# List tickets
klist

# Destroy tickets
kdestroy

# Test service tickets
kinit -S cifs/servername.domain.com administrator@DOMAIN.COM
```

### Authentication Troubleshooting
```bash
# Test LDAP authentication
ldapsearch -H ldap://localhost -D "administrator@DOMAIN.COM" -W -b "DC=domain,DC=com" "(objectClass=user)"

# Check winbind (on member servers)
wbinfo -u  # List users
wbinfo -g  # List groups
wbinfo -t  # Test trust
```

## Service Management

### Samba Services
```bash
# Start/stop/restart Samba AD
systemctl start samba-ad-dc
systemctl stop samba-ad-dc
systemctl restart samba-ad-dc
systemctl status samba-ad-dc

# Check service status
systemctl is-active samba-ad-dc
systemctl is-enabled samba-ad-dc

# View logs
journalctl -u samba-ad-dc -f
journalctl -u samba-ad-dc --since "1 hour ago"
```

### Configuration Testing
```bash
# Test smb.conf syntax
testparm

# Test specific section
testparm -s --section-name=global

# Show effective configuration
testparm -v
```

## Useful LDAP Queries

### Direct LDAP Access
```bash
# List all users with attributes
ldapsearch -H ldap://localhost -D "administrator@DOMAIN.COM" -W -b "CN=Users,DC=domain,DC=com" "(objectClass=user)" cn mail memberOf

# List all groups
ldapsearch -H ldap://localhost -D "administrator@DOMAIN.COM" -W -b "CN=Users,DC=domain,DC=com" "(objectClass=group)" cn member

# Find user by email
ldapsearch -H ldap://localhost -D "administrator@DOMAIN.COM" -W -b "DC=domain,DC=com" "(mail=user@domain.com)"
```

## Network Troubleshooting

### Port Testing
```bash
# Check if services are listening
netstat -tlnp | grep :389   # LDAP
netstat -tlnp | grep :636   # LDAPS
netstat -tlnp | grep :88    # Kerberos
netstat -tlnp | grep :53    # DNS
netstat -tlnp | grep :445   # SMB

# Test connectivity from remote host
telnet dc.domain.com 389
telnet dc.domain.com 88
```

### Time Synchronization
```bash
# Check time (critical for Kerberos)
date
timedatectl status

# Check NTP sync
chrony sources -v
systemctl status chrony
```

## Quick Diagnostics

### Health Checks
```bash
# One-liner health check
echo "=== Domain Status ===" && samba-tool domain level show && \
echo "=== Users ===" && samba-tool user list | wc -l && \
echo "=== Groups ===" && samba-tool group list | wc -l && \
echo "=== DNS ===" && dig -t SRV _ldap._tcp.$(hostname -d) @localhost +short
```

### Common File Locations
```bash
# Configuration files
/etc/samba/smb.conf          # Main Samba config
/etc/krb5.conf               # Kerberos config
/var/lib/samba/private/      # Samba database files
/var/log/samba/              # Samba logs

# Important directories
/var/lib/samba/sysvol/       # SYSVOL share
/var/lib/samba/private/      # Private DB files
```

## Examples for Your Domain

### Your Domain: HOME.FEDERATION.FI
```bash
# Create user for your domain
samba-tool user create john --given-name="John" --surname="Doe" --mail-address="john@home.federation.fi"

# Test your domain DNS
dig -t SRV _ldap._tcp.HOME.FEDERATION.FI @localhost

# Add user to your media group
samba-tool group addmembers "Media Admins" john

# Check your domain replication
samba-tool drs showrepl
```

## Tips

- Always use `-U administrator` for commands requiring authentication
- Use `--help` with any samba-tool command for detailed options
- Test configuration changes with `testparm` before restarting services
- Check logs with `journalctl -u samba-ad-dc` when troubleshooting
- Keep regular backups with `samba-tool domain backup`