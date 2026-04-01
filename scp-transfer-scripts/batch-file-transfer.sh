#!/bin/bash
#
# batch-file-transfer.sh
# Transfer multiple files in batch to Windows SFTP server
#
# Usage: ./batch-file-transfer.sh <file_list.txt> <server_ip> [username] [password]
#
# file_list.txt format (one file path per line):
#   /path/to/file1.bin
#   /path/to/file2.exe
#   /path/to/file3.tar.gz
#
# Example:
#   ./batch-file-transfer.sh files.txt 172.31.2.138
#

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_success() { echo -e "${BLUE}[SUCCESS]${NC} $1"; }

# Check arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <file_list.txt> <server_ip> [username] [password]"
    echo ""
    echo "file_list.txt format (one file path per line):"
    echo "  /path/to/file1.bin"
    echo "  /path/to/file2.exe"
    echo ""
    echo "Example:"
    echo "  $0 files.txt 172.31.2.138"
    exit 1
fi

FILE_LIST="$1"
SERVER_IP="$2"
USERNAME="${3:-admin}"
PASSWORD="${4:-CXlabs.123}"

# Validate file list exists
if [ ! -f "$FILE_LIST" ]; then
    print_error "File list not found: $FILE_LIST"
    exit 1
fi

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
print_success "Server is accessible"

# Count total files
TOTAL_FILES=$(wc -l < "$FILE_LIST" | tr -d ' ')
print_info "Found $TOTAL_FILES files to transfer"
echo ""

# Initialize counters
SUCCESS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# Create log file
LOG_FILE="batch-transfer-$(date +%Y%m%d-%H%M%S).log"
echo "Batch Transfer Log - $(date)" > "$LOG_FILE"
echo "Server: $USERNAME@$SERVER_IP" >> "$LOG_FILE"
echo "Files: $TOTAL_FILES" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"

# Process each file
CURRENT=0
while IFS= read -r FILE_PATH; do
    CURRENT=$((CURRENT + 1))

    # Skip empty lines and comments
    if [ -z "$FILE_PATH" ] || [[ "$FILE_PATH" == \#* ]]; then
        continue
    fi

    FILE_NAME=$(basename "$FILE_PATH")
    FILE_SIZE=""

    echo -e "${BLUE}[$CURRENT/$TOTAL_FILES]${NC} Processing: $FILE_NAME"

    # Check if file exists
    if [ ! -f "$FILE_PATH" ]; then
        print_warn "File not found, skipping: $FILE_PATH"
        echo "SKIP: $FILE_PATH (not found)" >> "$LOG_FILE"
        SKIP_COUNT=$((SKIP_COUNT + 1))
        continue
    fi

    # Get file size
    FILE_SIZE=$(ls -lh "$FILE_PATH" | awk '{print $5}')
    echo "  Size: $FILE_SIZE"

    # Transfer file
    echo "  Transferring..."
    if sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no "$FILE_PATH" "$USERNAME@$SERVER_IP:/" >> "$LOG_FILE" 2>&1; then
        print_success "  Transfer complete"
        echo "SUCCESS: $FILE_PATH ($FILE_SIZE)" >> "$LOG_FILE"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        print_error "  Transfer failed"
        echo "FAIL: $FILE_PATH ($FILE_SIZE)" >> "$LOG_FILE"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    echo ""
done < "$FILE_LIST"

# Print summary
echo "========================================="
echo "         Transfer Summary"
echo "========================================="
echo -e "${GREEN}Successful:${NC} $SUCCESS_COUNT"
echo -e "${RED}Failed:${NC}     $FAIL_COUNT"
echo -e "${YELLOW}Skipped:${NC}    $SKIP_COUNT"
echo -e "${BLUE}Total:${NC}      $TOTAL_FILES"
echo "========================================="
echo ""
echo "Log file: $LOG_FILE"

# Add summary to log
echo "---" >> "$LOG_FILE"
echo "Summary:" >> "$LOG_FILE"
echo "  Successful: $SUCCESS_COUNT" >> "$LOG_FILE"
echo "  Failed: $FAIL_COUNT" >> "$LOG_FILE"
echo "  Skipped: $SKIP_COUNT" >> "$LOG_FILE"
echo "  Total: $TOTAL_FILES" >> "$LOG_FILE"
echo "Completed: $(date)" >> "$LOG_FILE"

# Exit with appropriate code
if [ $FAIL_COUNT -gt 0 ]; then
    exit 1
else
    exit 0
fi
