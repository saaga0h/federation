# Proxmox

## Network

**Briges**
  - **vmbr0**:
    - CIDR: 192.168.1.20/24
    - Gateway: 192.168.1.1
    - VLAN: trunk
  - **vmbr1**:
    - CIDR: none
    - VLAN: trunk
  - **vmbr2**:
    - CIDR: 192.168.200.5/24
    - VLAN: none
    - Not connected, used internally as storage network
    
## Telegraf

**Requirements**

- Workign InfluxDB instance
- zfs bucket
- api token for write access to zfs bucket

**Telegraf configuration**

Add/replace following lines on `/etc/telegraf/telegraf.conf` to setup a connection to InfluxDB and statics collection for ZFS

```conf
[agent]
  interval = "10s"
  round_interval = true
  metric_batch_size = 1000
  metric_buffer_limit = 10000
  collection_jitter = "0s"
  flush_interval = "10s"
  flush_jitter = "0s"
  precision = ""
  hostname = "vox"
  omit_hostname = false

# Configuration for sending metrics to InfluxDB
[[outputs.influxdb_v2]]
  urls = ["http://influxdb.home.federation.fi:8086"]
  token = "<token>"
  organization = "Federation"
  bucket = "zfs"

#  Read metrics from zpool_influxdb
[[inputs.exec]]
  commands = ["/usr/bin/zpool_influxdb"]
  timeout = "5s"
  data_format = "influx"
```

## Smart notitfications

Configure Smart tools to send notifications to federation@home.federation.fi, which handled by Ntfy. Add following configuration to `/etc/smartd.conf`

```conf
DEVICESCAN -H -f -u -p -l error -l selftest -n standby,24,q \
-I 194 \
-I 190 \
-W 5,55,60 \
-i 9 \
-R 5! \
-C 197 \
-U 198 \
-o on -S on -s (S/../../../02|L/../01/./04) \
-m federation@home.federation.fi \
-M daily \
-M exec /usr/share/smartmontools/smartd-runner
```

Set relayhost to point where Ntfy server is running in `/etc/postfix/main.cf`

```conf
# See /usr/share/postfix/main.cf.dist for a commented, more complete version

myhostname=vox.home.federation.fi

smtpd_banner = $myhostname ESMTP $mail_name (Debian/GNU)
biff = no

# appending .domain is the MUA's job.
append_dot_mydomain = no

# Uncomment the next line to generate "delayed mail" warnings
#delay_warning_time = 4h

alias_maps = hash:/etc/aliases
alias_database = hash:/etc/aliases
mydestination = $myhostname, localhost.$mydomain, localhost
relayhost = ntfy.home.federation.fi:587
mynetworks = 127.0.0.0/8
inet_interfaces = loopback-only
recipient_delimiter = +

compatibility_level = 2
```

## GPU drivers

## API tokens and user accounts

**Service accounts**
- **checkmk**: checkmk@pve
- **pulse**: pulse@pve
- **terraform**: terraform@pam
- **zbbix**: zbbix@pve