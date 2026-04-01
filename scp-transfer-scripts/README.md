# SCP Transfer Scripts

Scripts and documentation for transferring files to/from network lab infrastructure using SCP/SFTP.

## Overview

This collection includes scripts and commands for file transfers in the Morgan Stanley SDA Phase 2 lab environment.

## Infrastructure

### SFTP Servers

| Server | IP Address | Credentials | Root Directory | Notes |
|--------|------------|-------------|----------------|-------|
| Windows SFTP #1 | 172.31.2.137 | sdaadmin / CXlabs.123 | / | Primary SFTP server |
| Windows SFTP #2 | 172.31.2.138<br>172.31.0.67 | admin / CXlabs.123 | C:\SFTP_Root\ | SolarWinds SFTP Server |
| Mac HTTP | 172.31.0.22:8080 | N/A | / | HTTP server for quick transfers |

## Scripts Included

1. **scp-upload-to-windows.sh** - Upload files from Mac to Windows SFTP servers
2. **scp-download-from-windows.sh** - Download files from Windows SFTP servers
3. **device-scp-pull.sh** - Commands for network devices to pull files via SCP
4. **windows-firewall-setup.ps1** - PowerShell script to configure Windows firewall for SFTP
5. **batch-file-transfer.sh** - Transfer multiple files in batch

## Quick Start

### Upload File to Windows Server

```bash
./scp-upload-to-windows.sh /path/to/file.bin 172.31.2.138
```

### Download File from Windows Server

```bash
./scp-download-from-windows.sh 172.31.2.138 /remote/path/file.bin /local/destination/
```

### Network Device Pull from SFTP Server

```bash
# On IOS-XE device
copy scp://admin@172.31.2.138/file.bin bootflash: vrf Mgmt-vrf
```

## Prerequisites

### Mac/Linux

- `sshpass` installed: `brew install sshpass`
- SSH client installed (usually pre-installed)

### Windows Server

- OpenSSH Server or SolarWinds SFTP Server installed
- Firewall rule allowing port 22 (TCP)
- User account configured with read/write permissions

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

## Documentation

- [Windows Firewall Configuration](windows-firewall-setup.md)
- [SolarWinds SFTP Server Setup](solarwinds-sftp-setup.md)
- [Network Device SCP Commands](device-scp-commands.md)

## Date Created

April 1, 2026

## Author

MS SDA Phase 2 Lab - Wade Benbark
