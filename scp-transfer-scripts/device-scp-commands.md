# Network Device SCP Commands

Commands for transferring files to/from network devices using SCP.

## IOS-XE Devices (Catalyst 9000 Series)

### Pull File from SFTP Server to Device

**Basic syntax:**
```
copy scp://username@server-ip/path/to/file bootflash: vrf Mgmt-vrf
```

**Examples:**

```bash
# Pull SMU patch from Windows SFTP server
copy scp://admin@172.31.2.138/cat9k_iosxe.17.15.04.CSCwr84543.SPA.smu.bin bootflash: vrf Mgmt-vrf

# Pull IOS-XE image
copy scp://sdaadmin@172.31.2.137/ios_images/cat9k_iosxe.17.15.04.SPA.bin bootflash: vrf Mgmt-vrf

# Pull from Catalyst Center
copy scp://maglev@172.31.2.244/data/tmp/smu_files/patch.bin bootflash: vrf Mgmt-vrf
```

**Interactive prompts:**
1. Destination filename: Press **Enter** to accept default
2. Password: Enter the server password

---

### Push File from Device to SFTP Server

**Basic syntax:**
```
copy bootflash:filename scp://username@server-ip/ vrf Mgmt-vrf
```

**Examples:**

```bash
# Push running config to server
copy running-config bootflash:running-config-backup.txt
copy bootflash:running-config-backup.txt scp://admin@172.31.2.138/ vrf Mgmt-vrf

# Push tech-support output
show tech-support | redirect bootflash:tech-support-output.txt
copy bootflash:tech-support-output.txt scp://admin@172.31.2.138/ vrf Mgmt-vrf

# Push packet capture
monitor capture CAP export bootflash:capture.pcap
copy bootflash:capture.pcap scp://admin@172.31.2.138/ vrf Mgmt-vrf
```

---

## Pre-Transfer Checks

### 1. Verify Connectivity to Server

```bash
ping vrf Mgmt-vrf 172.31.2.138
```

### 2. Check Available Bootflash Space

```bash
show bootflash: | include bytes
dir bootflash: | include free
```

### 3. Test SSH Connectivity

```bash
test ssh vrf Mgmt-vrf 172.31.2.138
```

### 4. Enable SCP Server (if copying TO device)

```bash
configure terminal
ip scp server enable
end
```

---

## Post-Transfer Verification

### 1. Verify File Exists

```bash
dir bootflash: | include <filename>
```

### 2. Check File Size

```bash
dir bootflash:<filename>
```

### 3. Calculate MD5 Checksum

```bash
verify /md5 bootflash:<filename>
```

### 4. Show File Information

```bash
show file information bootflash:<filename>
```

---

## Troubleshooting

### Connection Timeout

**Issue:** SCP transfer times out

**Solutions:**
```bash
# Check VRF routing
show ip route vrf Mgmt-vrf <server-ip>

# Verify management interface
show ip interface GigabitEthernet0/0

# Test reachability
ping vrf Mgmt-vrf <server-ip>
```

---

### Authentication Failed

**Issue:** "Permission denied" error

**Solutions:**
1. Verify credentials are correct
2. Check if user exists on SFTP server
3. Verify user has appropriate permissions
4. Try connecting via SSH first to validate credentials

```bash
# Test SSH login
ssh username@server-ip
```

---

### Insufficient Space

**Issue:** Not enough space on bootflash

**Solutions:**
```bash
# Delete old files
delete bootflash:*.old

# Delete specific files
delete /force bootflash:old_file.bin

# Squeeze to reclaim space
squeeze bootflash:
```

---

## Common File Paths

### IOS-XE Device Storage
- `bootflash:/` - Main flash storage (primary)
- `flash:/` - Alias for bootflash
- `nvram:/` - NVRAM storage (startup-config)
- `usbflash0:/` - USB storage (if present)

### Windows SFTP Server Paths
- **172.31.2.138**: Files land in `C:\SFTP_Root\`
- **172.31.2.137**: Files land in root `/`

### Catalyst Center Paths
- `/data/tmp/` - Temporary storage
- `/data/swim/images/` - SWIM imported images
- `/data/backup/` - Config backups
- `/software/downloads/` - Downloaded files

---

## Device Information

### Lab Device Credentials
- **IOS-XE (Catalyst 9K)**: admin1 / CXlabs.123
- **NX-OS (Nexus 9K)**: admin / CXlabs.123
- **Special TACACS devices**: dnac_admin_tacacs / CXlabs.123

### Management VRF
All devices use **Mgmt-vrf** for management traffic including SCP transfers.

---

## Examples by Use Case

### 1. SMU Installation

```bash
# Pull SMU from server
copy scp://admin@172.31.2.138/cat9k_iosxe.17.15.04.CSCwr84543.SPA.smu.bin bootflash: vrf Mgmt-vrf

# Verify checksum
verify /md5 bootflash:cat9k_iosxe.17.15.04.CSCwr84543.SPA.smu.bin

# Install SMU
install add file bootflash:cat9k_iosxe.17.15.04.CSCwr84543.SPA.smu.bin activate commit
```

### 2. Configuration Backup

```bash
# Backup to server
copy running-config bootflash:backup-$(date +%Y%m%d).txt
copy bootflash:backup-$(date +%Y%m%d).txt scp://admin@172.31.2.138/ vrf Mgmt-vrf
```

### 3. Packet Capture Collection

```bash
# Export capture
monitor capture CAP export bootflash:capture-$(date +%Y%m%d-%H%M).pcap

# Transfer to server for analysis
copy bootflash:capture-$(date +%Y%m%d-%H%M).pcap scp://admin@172.31.2.138/ vrf Mgmt-vrf
```

---

## Date Created
April 1, 2026
