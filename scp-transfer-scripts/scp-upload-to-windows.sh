#!/bin/bash
#
# scp-upload-to-windows.sh
# Upload files from Mac/Linux to Windows SFTP server
#
# Usage: ./scp-upload-to-windows.sh <local_file> <server_ip> [username] [password]
#
# Examples:
#   ./scp-upload-to-windows.sh /Users/wbenbark/Downloads/file.bin 172.31.2.138
#   ./scp-upload-to-windows.sh /path/to/file.bin 172.31.2.137 sdaadmin CXlabs.123
#

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <local_file> <server_ip> [username] [password]"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/file.bin 172.31.2.138"
    echo "  $0 /path/to/file.bin 172.31.2.137 sdaadmin CXlabs.123"
    exit 1
fi

LOCAL_FILE="$1"
SERVER_IP="$2"
USERNAME="${3:-admin}"
PASSWORD="${4:-CXlabs.123}"

# Validate local file exists
if [ ! -f "$LOCAL_FILE" ]; then
    print_error "File not found: $LOCAL_FILE"
    exit 1
fi

# Get file size
FILE_SIZE=$(ls -lh "$LOCAL_FILE" | awk '{print $5}')
FILE_NAME=$(basename "$LOCAL_FILE")

print_info "File: $FILE_NAME"
print_info "Size: $FILE_SIZE"
print_info "Destination: $USERNAME@$SERVER_IP"

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    print_error "sshpass is not installed"
    echo "Install with: brew install sshpass"
    exit 1
fi

# Test connectivity
print_info "Testing connectivity to $SERVER_IP..."
if ! ping -c 2 -W 2 "$SERVER_IP" > /dev/null 2>&1; then
    print_warn "Server $SERVER_IP is not responding to ping"
fi

# Test SSH port
print_info "Checking SSH port 22..."
if ! nc -z -w 5 "$SERVER_IP" 22 > /dev/null 2>&1; then
    print_error "Port 22 is not accessible on $SERVER_IP"
    echo "Check firewall rules or ensure SFTP service is running"
    exit 1
fi

print_info "Port 22 is accessible"

# Perform SCP transfer
print_info "Starting SCP transfer..."
if sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no "$LOCAL_FILE" "$USERNAME@$SERVER_IP:/"; then
    print_info "Transfer completed successfully!"
    echo ""
    echo "File location on server:"
    if [ "$SERVER_IP" == "172.31.2.138" ] || [ "$SERVER_IP" == "172.31.0.67" ]; then
        echo "  C:\\SFTP_Root\\$FILE_NAME"
    else
        echo "  /$FILE_NAME"
    fi
else
    print_error "Transfer failed!"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Verify credentials: $USERNAME / $PASSWORD"
    echo "  2. Check SFTP service is running on server"
    echo "  3. Verify user has write permissions"
    exit 1
fi
