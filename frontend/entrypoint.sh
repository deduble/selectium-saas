#!/bin/sh
set -e

# Ensure we're in the right directory
cd /app

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting Frontend entrypoint script..."

# Ensure .next directory exists with proper structure
log "Ensuring .next directory structure..."
mkdir -p /app/.next/cache
mkdir -p /app/.next/server
mkdir -p /app/.next/static

# Generate BUILD_ID if missing
if [ ! -f /app/.next/BUILD_ID ]; then
    log "BUILD_ID file missing, generating..."
    # Generate a timestamp-based BUILD_ID similar to Next.js
    date +%s%3N > /app/.next/BUILD_ID
    log "Generated BUILD_ID: $(cat /app/.next/BUILD_ID)"
else
    log "BUILD_ID file exists: $(cat /app/.next/BUILD_ID)"
fi

# Ensure proper ownership (if running as root, change ownership)
if [ "$(id -u)" = "0" ]; then
    log "Running as root, setting ownership to selextract:selextract"
    chown -R selextract:selextract /app/.next
    # Switch to selextract user
    exec su-exec selextract "$0" "$@"
fi

# Verify critical files exist
log "Verifying critical Next.js files..."
if [ ! -f /app/server.js ]; then
    log "ERROR: server.js not found!"
    exit 1
fi

if [ ! -f /app/.next/BUILD_ID ]; then
    log "ERROR: BUILD_ID still missing after generation!"
    exit 1
fi

# List .next directory contents for debugging
log "Contents of .next directory:"
ls -la /app/.next/ || true

log "Starting Next.js server..."
# Start the Next.js application
exec node server.js