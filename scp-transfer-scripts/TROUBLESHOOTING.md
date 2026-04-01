# SCP Transfer Troubleshooting Guide

Common issues and solutions for SCP/SFTP file transfers.

## Table of Contents
1. [Connection Issues](#connection-issues)
2. [Authentication Issues](#authentication-issues)
3. [Port/Firewall Issues](#portfirewall-issues)
4. [Permission Issues](#permission-issues)
5. [Performance Issues](#performance-issues)

---

## Connection Issues

### Issue: "Connection timed out"

**Symptoms:**
```
ssh: connect to host 172.31.2.138 port 22: Operation timed out
scp: Connection closed
```

**Causes:**
- Server is not reachable
- Firewall blocking port 22
- SFTP service not running

**Solutions:**

1. **Test basic connectivity:**
```bash
ping 172.31.2.138
```

2. **Check if port 22 is accessible:**
```bash
nc -zv 172.31.2.138 22
```

3. **Check routing (on network devices):**
```bash
show ip route vrf Mgmt-vrf 172.31.2.138
```

4. **Verify firewall rules on Windows:**
```powershell
Get-NetFirewallPortFilter | Where-Object {$_.LocalPort -eq 22} | Get-NetFirewallRule
```

---

### Issue: "Connection refused"

**Symptoms:**
```
ssh: connect to host 172.31.2.138 port 22: Connection refused
```

**Causes:**
- SFTP/SSH service is not running
- Service is listening on different port
- Service is bound to specific IP that doesn't match target

**Solutions:**

1. **Check if service is running (Windows):**
```powershell
Get-Service | Where-Object {$_.DisplayName -like "*SFTP*" -or $_.DisplayName -like "*SSH*"}
```

2. **Check listening ports:**
```powershell
netstat -an | findstr :22
```

3. **Start the service:**
```powershell
Start-Service "SolarWinds SFTP Server"
# OR
Start-Service sshd
```

---

## Authentication Issues

### Issue: "Permission denied"

**Symptoms:**
```
Permission denied, please try again.
Permission denied (publickey,password).
```

**Causes:**
- Incorrect username or password
- User not configured in SFTP server
- User permissions not set

**Solutions:**

1. **Verify credentials:**
   - 172.31.2.138: admin / CXlabs.123
   - 172.31.2.137: sdaadmin / CXlabs.123

2. **Test SSH login first:**
```bash
ssh admin@172.31.2.138
```

3. **Check user configuration (SolarWinds):**
   - Open SolarWinds SFTP Settings
   - Click "Users" tab
   - Verify user exists and is enabled
   - Check password is correct

4. **Configure new user (SolarWinds):**
   - Users tab → Click "Add"
   - Username: admin
   - Password: CXlabs.123
   - Home Directory: C:\SFTP_Root
   - Permissions: Read, Write
   - Enable account: ✓

---

### Issue: "Host key verification failed"

**Symptoms:**
```
Host key verification failed.
```

**Solutions:**

1. **Use StrictHostKeyChecking=no (for lab/testing):**
```bash
scp -o StrictHostKeyChecking=no file.bin admin@172.31.2.138:/
```

2. **Remove old host key:**
```bash
ssh-keygen -R 172.31.2.138
```

---

## Port/Firewall Issues

### Issue: Port 22 not accessible from remote

**Check from Mac/Linux:**
```bash
nc -zv 172.31.2.138 22
```

**Check from Windows (PowerShell):**
```powershell
Test-NetConnection -ComputerName 172.31.2.138 -Port 22
```

**Solutions:**

1. **Create firewall rule (Windows):**
```powershell
New-NetFirewallRule -DisplayName "SolarWinds SFTP Server Port 22" -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow -Profile Any
```

2. **Check firewall rule exists:**
```powershell
Get-NetFirewallRule -DisplayName "SolarWinds SFTP Server Port 22"
```

3. **Verify rule is enabled:**
```powershell
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*SFTP*"} | Select-Object DisplayName, Enabled, Direction, Action
```

---

### Issue: Port 22 listening but not accessible

**Causes:**
- Service bound to specific IP (not all interfaces)
- Firewall rule has wrong scope

**Solutions:**

1. **Check IP binding (Windows):**
```powershell
Get-NetTCPConnection -LocalPort 22 | Select-Object LocalAddress, State
```

Should show `0.0.0.0:22` (all interfaces) not just `127.0.0.1:22` (localhost only)

2. **Configure SolarWinds to bind all IPs:**
   - Open SolarWinds SFTP Settings
   - TCP/IP Settings tab
   - Select "Bind to all local IP addresses"
   - Click OK and restart service

---

## Permission Issues

### Issue: "Permission denied" after successful login

**Symptoms:**
- Can connect via SSH/SCP
- Transfer starts but fails with permission error
- Files not appearing in expected location

**Solutions:**

1. **Check user has write permissions:**
   - SolarWinds: Users tab → Edit user → Check "Write" permission

2. **Verify directory permissions (Windows):**
```powershell
# Check SFTP root directory
Get-Acl C:\SFTP_Root | Format-List

# Grant permissions
$acl = Get-Acl C:\SFTP_Root
$permission = "BUILTIN\Users","FullControl","ContainerInherit,ObjectInherit","None","Allow"
$accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule $permission
$acl.SetAccessRule($accessRule)
Set-Acl C:\SFTP_Root $acl
```

3. **Check disk space:**
```powershell
Get-PSDrive C | Select-Object Used,Free
```

---

## Performance Issues

### Issue: Slow transfer speeds

**Solutions:**

1. **Check network latency:**
```bash
ping -c 10 172.31.2.138
```

2. **Use compression:**
```bash
scp -C file.bin admin@172.31.2.138:/
```

3. **Increase buffer size:**
```bash
scp -o "Ciphers=aes128-gcm@openssh.com" file.bin admin@172.31.2.138:/
```

4. **Check server load (Windows):**
```powershell
Get-Counter '\Processor(_Total)\% Processor Time'
Get-Counter '\Network Interface(*)\Bytes Total/sec'
```

---

### Issue: Transfer hangs or freezes

**Causes:**
- Network interruption
- Timeout too short
- Server overloaded

**Solutions:**

1. **Increase timeout:**
```bash
scp -o ConnectTimeout=60 -o ServerAliveInterval=15 file.bin admin@172.31.2.138:/
```

2. **Check for network issues:**
```bash
mtr 172.31.2.138  # On Mac: brew install mtr
```

3. **Monitor server resources:**
```powershell
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10
```

---

## Diagnostic Commands

### Mac/Linux

```bash
# Check connectivity
ping 172.31.2.138
nc -zv 172.31.2.138 22

# Test SSH
ssh admin@172.31.2.138

# Verbose SCP (debug)
scp -v file.bin admin@172.31.2.138:/

# Check sshpass installation
which sshpass
brew list sshpass
```

### Windows Server

```powershell
# Check service status
Get-Service | Where-Object {$_.DisplayName -like "*SFTP*"}

# Check listening ports
netstat -an | findstr :22
Get-NetTCPConnection -LocalPort 22

# Check firewall rules
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*SFTP*"}

# Test local connectivity
Test-NetConnection -ComputerName localhost -Port 22

# Check network adapters
Get-NetAdapter | Select-Object Name, Status, LinkSpeed
Get-NetIPAddress | Where-Object {$_.IPAddress -like "172.31.*"}
```

### IOS-XE Device

```bash
# Check connectivity
ping vrf Mgmt-vrf 172.31.2.138

# Check routing
show ip route vrf Mgmt-vrf 172.31.2.138

# Test SSH
test ssh vrf Mgmt-vrf 172.31.2.138

# Check bootflash space
show bootflash: | include free
dir bootflash:

# Verify SCP server enabled
show running-config | include scp
```

---

## Quick Reference: Working Configuration

### Successful SCP Transfer Checklist

- [ ] Server is reachable (ping succeeds)
- [ ] Port 22 is accessible (nc -zv succeeds)
- [ ] Firewall rule allows port 22 inbound
- [ ] SFTP service is running
- [ ] User is configured with correct credentials
- [ ] User has read/write permissions
- [ ] Destination directory exists and is writable
- [ ] Sufficient disk space available

### Known Working Servers

| Server | IP | User | Password | Root Dir | Status |
|--------|-----|------|----------|----------|--------|
| Windows #1 | 172.31.2.137 | sdaadmin | CXlabs.123 | / | ✓ Working |
| Windows #2 | 172.31.2.138 | admin | CXlabs.123 | C:\SFTP_Root\ | ✓ Working |
| Windows #2 (alt) | 172.31.0.67 | admin | CXlabs.123 | C:\SFTP_Root\ | ✓ Working |

---

## Getting Help

If issues persist:

1. **Collect diagnostics:**
   - Run all diagnostic commands above
   - Check server logs (Windows Event Viewer or SolarWinds logs)
   - Capture network traffic (Wireshark/tcpdump)

2. **Check service logs:**
   - Windows: Event Viewer → Windows Logs → Application
   - SolarWinds: Check SFTP server logs in installation directory

3. **Verify from both ends:**
   - Test from client → server
   - Test from server → localhost
   - Test between different client/server pairs

---

## Date Created
April 1, 2026
