#!/bin/bash
#
# scp-download-from-windows.sh
# Download files from Windows SFTP server to Mac/Linux
#
# Usage: ./scp-download-from-windows.sh <server_ip> <remote_file> <local_destination> [username] [password]
#
# Examples:
#   ./scp-download-from-windows.sh 172.31.2.138 /file.bin ~/Downloads/
#   ./scp-download-from-windows.sh 172.31.2.137 /ios_images/cat9k.bin /tmp/ sdaadmin CXlabs.123
#

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check arguments
if [ $# -lt 3 ]; then
    echo "Usage: $0 <server_ip> <remote_file> <local_destination> [username] [password]"
    echo ""
    echo "Examples:"
    echo "  $0 172.31.2.138 /file.bin ~/Downloads/"
    echo "  $0 172.31.2.137 /ios_images/cat9k.bin /tmp/ sdaadmin CXlabs.123"
    exit 1
fi

SERVER_IP="$1"
REMOTE_FILE="$2"
LOCAL_DEST="$3"
USERNAME="${4:-admin}"
PASSWORD="${5:-CXlabs.123}"

# Create local destination if it doesn't exist
mkdir -p "$LOCAL_DEST"

print_info "Server: $USERNAME@$SERVER_IP"
print_info "Remote file: $REMOTE_FILE"
print_info "Local destination: $LOCAL_DEST"

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    print_error "sshpass is not installed"
    echo "Install with: brew install sshpass"
    exit 1
fi

# Test connectivity
print_info "Testing connectivity to $SERVER_IP..."
if ! nc -z -w 5 "$SERVER_IP" 22 > /dev/null 2>&1; then
    print_error "Port 22 is not accessible on $SERVER_IP"
    exit 1
fi

# Perform SCP transfer
print_info "Starting SCP download..."
if sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no "$USERNAME@$SERVER_IP:$REMOTE_FILE" "$LOCAL_DEST"; then
    print_info "Download completed successfully!"
    echo ""
    FILE_NAME=$(basename "$REMOTE_FILE")
    echo "File location: $LOCAL_DEST$FILE_NAME"
    ls -lh "$LOCAL_DEST$FILE_NAME"
else
    print_error "Download failed!"
    exit 1
fi
