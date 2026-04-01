#
# windows-firewall-setup.ps1
# Configure Windows Firewall to allow SFTP/SCP connections on port 22
#
# Usage: Run as Administrator in PowerShell
#   .\windows-firewall-setup.ps1
#
# Date: April 1, 2026
#

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== Windows Firewall Setup for SFTP/SCP ===" -ForegroundColor Cyan
Write-Host ""

# Check if firewall rule already exists
$existingRule = Get-NetFirewallRule -DisplayName "SolarWinds SFTP Server Port 22" -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "[INFO] Firewall rule already exists" -ForegroundColor Yellow
    $existingRule | Select-Object DisplayName, Enabled, Direction, Action, Profile | Format-Table

    $response = Read-Host "Do you want to recreate the rule? (y/n)"
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "[INFO] Removing existing rule..." -ForegroundColor Yellow
        Remove-NetFirewallRule -DisplayName "SolarWinds SFTP Server Port 22"
    } else {
        Write-Host "[INFO] Keeping existing rule. Exiting." -ForegroundColor Green
        exit 0
    }
}

# Create new firewall rule
Write-Host "[INFO] Creating new firewall rule for port 22..." -ForegroundColor Green

try {
    New-NetFirewallRule `
        -DisplayName "SolarWinds SFTP Server Port 22" `
        -Description "Allow inbound SFTP/SCP connections on port 22 for SolarWinds SFTP Server" `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort 22 `
        -Action Allow `
        -Profile Any `
        -Enabled True

    Write-Host "[SUCCESS] Firewall rule created successfully!" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to create firewall rule: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Verify the rule
Write-Host "[INFO] Verifying firewall rule..." -ForegroundColor Cyan
$newRule = Get-NetFirewallRule -DisplayName "SolarWinds SFTP Server Port 22"
$newRule | Select-Object DisplayName, Enabled, Direction, Action, Profile | Format-Table

Write-Host ""

# Check if port 22 is listening
Write-Host "[INFO] Checking if port 22 is listening..." -ForegroundColor Cyan
$listening = Get-NetTCPConnection -LocalPort 22 -State Listen -ErrorAction SilentlyContinue

if ($listening) {
    Write-Host "[SUCCESS] Port 22 is listening" -ForegroundColor Green
    $listening | Select-Object LocalAddress, LocalPort, State, OwningProcess | Format-Table

    # Get process name
    $processId = $listening[0].OwningProcess
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "[INFO] Service: $($process.ProcessName)" -ForegroundColor Cyan
    }
} else {
    Write-Host "[WARNING] Port 22 is NOT listening" -ForegroundColor Yellow
    Write-Host "[INFO] Make sure SFTP/SSH service is running" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To start OpenSSH Server:" -ForegroundColor Cyan
    Write-Host "  Start-Service sshd" -ForegroundColor White
    Write-Host ""
    Write-Host "To start SolarWinds SFTP Server:" -ForegroundColor Cyan
    Write-Host "  Start-Service 'SolarWinds SFTP Server'" -ForegroundColor White
}

Write-Host ""

# Test local connectivity
Write-Host "[INFO] Testing local connectivity to port 22..." -ForegroundColor Cyan
$testResult = Test-NetConnection -ComputerName localhost -Port 22 -InformationLevel Quiet

if ($testResult) {
    Write-Host "[SUCCESS] Port 22 is accessible locally" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Port 22 is NOT accessible locally" -ForegroundColor Yellow
    Write-Host "[INFO] Service may not be running or is not configured properly" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Firewall Setup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Ensure SFTP service is running (OpenSSH or SolarWinds)" -ForegroundColor White
Write-Host "2. Configure SFTP users with appropriate permissions" -ForegroundColor White
Write-Host "3. Test connectivity from remote machine:" -ForegroundColor White
Write-Host "   ssh username@<server-ip>" -ForegroundColor Gray
Write-Host "4. Test SCP transfer:" -ForegroundColor White
Write-Host "   scp test.txt username@<server-ip>:/" -ForegroundColor Gray
Write-Host ""
