# ZFS Command Line Cheat Sheet

## Pool Management

### Create Pools
```bash
# Create simple pool
zpool create mypool /dev/sda

# Create mirror pool
zpool create mypool mirror /dev/sda /dev/sdb

# Create RAIDZ pool (RAID5-like)
zpool create mypool raidz /dev/sda /dev/sdb /dev/sdc

# Create RAIDZ2 pool (RAID6-like)
zpool create mypool raidz2 /dev/sda /dev/sdb /dev/sdc /dev/sdd
```

### Pool Information & Status
```bash
# List all pools
zpool list

# Show detailed pool status
zpool status

# Show pool history
zpool history

# Show pool I/O statistics
zpool iostat

# Show pool configuration
zpool get all mypool
```

### Pool Maintenance
```bash
# Scrub pool (check for errors)
zpool scrub mypool

# Stop scrub
zpool scrub -s mypool

# Export pool (unmount)
zpool export mypool

# Import pool
zpool import mypool

# Import pool with different name
zpool import mypool newname

# Clear pool errors
zpool clear mypool
```

## Dataset Management

### Create Datasets
```bash
# Create filesystem dataset
zfs create mypool/dataset

# Create dataset with mountpoint
zfs create -o mountpoint=/mnt/data mypool/data

# Create volume (block device)
zfs create -V 10G mypool/volume
```

### List & Information
```bash
# List all datasets
zfs list

# List with specific properties
zfs list -o name,used,avail,mountpoint

# Show dataset properties
zfs get all mypool/dataset

# Show specific property
zfs get compression mypool/dataset
```

### Mount & Unmount
```bash
# Mount dataset
zfs mount mypool/dataset

# Unmount dataset
zfs umount mypool/dataset

# Mount all datasets
zfs mount -a
```

### Destroy Datasets
```bash
# Destroy dataset
zfs destroy mypool/dataset

# Destroy dataset and all children
zfs destroy -r mypool/parent

# Force destroy (unmount first)
zfs destroy -f mypool/dataset
```

## Snapshots

### Create Snapshots
```bash
# Create snapshot
zfs snapshot mypool/dataset@snapshot1

# Create recursive snapshot
zfs snapshot -r mypool/parent@snapshot1

# Create snapshot with current timestamp
zfs snapshot mypool/dataset@$(date +%Y%m%d-%H%M%S)
```

### List & Manage Snapshots
```bash
# List snapshots
zfs list -t snapshot

# List snapshots for specific dataset
zfs list -t snapshot -d 1 mypool/dataset

# Destroy snapshot
zfs destroy mypool/dataset@snapshot1

# Destroy range of snapshots
zfs destroy mypool/dataset@snap1%snap5
```

### Rollback & Clone
```bash
# Rollback to snapshot
zfs rollback mypool/dataset@snapshot1

# Clone snapshot to new dataset
zfs clone mypool/dataset@snapshot1 mypool/newdataset

# Promote clone (make it independent)
zfs promote mypool/newdataset
```

## Send & Receive (Backup/Replication)

### Basic Send/Receive
```bash
# Send snapshot to file
zfs send mypool/dataset@snapshot1 > backup.zfs

# Receive from file
zfs receive mypool/restored < backup.zfs

# Send over network
zfs send mypool/dataset@snapshot1 | ssh user@host zfs receive backuppool/dataset

# Incremental send
zfs send -i mypool/dataset@snap1 mypool/dataset@snap2 | ssh user@host zfs receive backuppool/dataset
```

### Advanced Send Options
```bash
# Send with progress
zfs send mypool/dataset@snapshot1 | pv | zfs receive mypool/backup

# Send recursively
zfs send -R mypool/parent@snapshot1 | zfs receive backuppool/parent

# Resume interrupted receive
zfs receive -s mypool/dataset
```

## Properties & Settings

### Common Properties
```bash
# Set compression
zfs set compression=lz4 mypool/dataset

# Set record size
zfs set recordsize=1M mypool/dataset

# Set quota
zfs set quota=100G mypool/dataset

# Set reservation
zfs set reservation=50G mypool/dataset

# Enable deduplication
zfs set dedup=on mypool/dataset

# Set copies (redundancy)
zfs set copies=2 mypool/dataset
```

### Mountpoint & Access
```bash
# Set mountpoint
zfs set mountpoint=/custom/path mypool/dataset

# Disable automount
zfs set canmount=off mypool/dataset

# Set read-only
zfs set readonly=on mypool/dataset
```

## NFS Sharing (sharenfs)

### Basic NFS Sharing
```bash
# Enable NFS sharing (default options)
zfs set sharenfs=on mypool/dataset

# Share with specific options
zfs set sharenfs="rw,no_root_squash" mypool/dataset

# Share with access restrictions
zfs set sharenfs="rw@192.168.1.0/24,ro@10.0.0.0/8" mypool/dataset

# Complex NFS options
zfs set sharenfs="rw=@192.168.1.0/24,root=server1.domain.com,sync" mypool/dataset
```

### NFS Management
```bash
# Check current NFS shares
zfs get sharenfs mypool/dataset

# Show all shared datasets
zfs get -s local sharenfs

# Disable NFS sharing
zfs set sharenfs=off mypool/dataset

# Show system NFS exports (verify)
showmount -e localhost
cat /etc/exports
```

### Common NFS Options
```bash
# Read-write access
zfs set sharenfs="rw" mypool/dataset

# Read-only access
zfs set sharenfs="ro" mypool/dataset

# No root squashing (root access)
zfs set sharenfs="rw,no_root_squash" mypool/dataset

# Async writes (faster but less safe)
zfs set sharenfs="rw,async" mypool/dataset

# Sync writes (safer but slower)
zfs set sharenfs="rw,sync" mypool/dataset

# Specific host access
zfs set sharenfs="rw=client1.domain.com:client2.domain.com" mypool/dataset

# Network-based access
zfs set sharenfs="rw=@192.168.1.0/24" mypool/dataset
```

## SMB/CIFS Sharing

### Basic SMB Sharing
```bash
# Enable SMB sharing
zfs set sharesmb=on mypool/dataset

# Set SMB share name
zfs set sharesmb=name=myshare mypool/dataset

# Disable SMB sharing
zfs set sharesmb=off mypool/dataset

# Check SMB shares
zfs get sharesmb
```

## Useful Monitoring Commands

### System Information
```bash
# Show ARC statistics
cat /proc/spl/kstat/zfs/arcstats

# Show pool capacity and health
zpool list -H -o name,size,alloc,free,cap,health

# Monitor pool I/O in real-time
zpool iostat -v 2

# Show dataset space usage
zfs list -o space

# Check for pool errors
zpool status | grep -E "(DEGRADED|FAULTED|OFFLINE|errors:)"
```

### Performance Tuning
```bash
# Set ARC max size (in bytes)
echo 8589934592 > /sys/module/zfs/parameters/zfs_arc_max

# Set recordsize for databases
zfs set recordsize=8K mypool/database

# Set recordsize for large files
zfs set recordsize=1M mypool/media

# Enable sync writes optimization
zfs set sync=always mypool/database
```

## Quick Reference Examples

### Complete Dataset Setup with NFS
```bash
# Create pool
zpool create datapool /dev/sdb

# Create dataset
zfs create datapool/share

# Set properties
zfs set compression=lz4 datapool/share
zfs set sharenfs="rw@192.168.1.0/24,no_root_squash" datapool/share

# Create snapshot
zfs snapshot datapool/share@initial

# Verify NFS export
showmount -e localhost
```

### Backup Workflow
```bash
# Create initial backup
zfs snapshot source/data@backup-$(date +%Y%m%d)
zfs send source/data@backup-$(date +%Y%m%d) | zfs receive backup/data

# Incremental backup (next day)
zfs snapshot source/data@backup-$(date +%Y%m%d)
zfs send -i source/data@backup-$(date -d yesterday +%Y%m%d) source/data@backup-$(date +%Y%m%d) | zfs receive backup/data
```

## Important Notes

- Always export pools properly before system shutdown
- Regular scrubs help maintain data integrity
- Snapshots are instant and space-efficient
- Test restore procedures regularly
- Monitor pool health with `zpool status`
- Use compression for most workloads (lz4 is fast)
- Set appropriate recordsize based on workload
- NFS shares are automatically managed by ZFS
- Consider using `sync=always` for critical data