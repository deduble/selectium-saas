#!/bin/bash
# Windows Port Conflict Fix Script
# Helps resolve common port conflicts on Windows

echo "🪟 Windows Port Conflict Resolver"
echo "=================================="
echo ""

# Get script directory and navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Check what's using the ports
echo "🔍 Checking what's using the ports..."
echo ""

check_port_usage() {
    local port=$1
    local service=$2
    
    echo "Port $port ($service):"
    if command -v netstat >/dev/null 2>&1; then
        netstat -ano | findstr ":$port " 2>/dev/null || echo "  ✅ Port $port is free"
    elif command -v ss >/dev/null 2>&1; then
        ss -tulpn | grep ":$port " 2>/dev/null || echo "  ✅ Port $port is free"
    else
        echo "  ❓ Cannot check port status"
    fi
    echo ""
}

check_port_usage 5432 "PostgreSQL"
check_port_usage 6379 "Redis"

echo "🛠️ Solutions:"
echo ""
echo "Option 1 - Use different ports (Recommended):"
echo "  Edit dev/.env.dev and change:"
echo "    DEV_DB_PORT=5433"
echo "    DEV_REDIS_PORT=6380"
echo ""
echo "Option 2 - Stop Windows services:"
echo "  1. Press Win+R, type 'services.msc'"
echo "  2. Find and stop 'PostgreSQL' service"
echo "  3. Find and stop 'Redis' service"
echo ""
echo "Option 3 - Kill processes (Advanced):"
if command -v taskkill >/dev/null 2>&1; then
    echo "  For PostgreSQL: netstat -ano | findstr :5432"
    echo "  Then: taskkill /PID <PID_FROM_ABOVE>"
    echo "  For Redis: netstat -ano | findstr :6379"
    echo "  Then: taskkill /PID <PID_FROM_ABOVE>"
else
    echo "  Use Task Manager to end PostgreSQL and Redis processes"
fi
echo ""

read -p "Apply Option 1 (change ports)? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f ".env.dev" ]; then
        cp .env.dev .env.dev.backup
        sed -i 's/DEV_DB_PORT=5432/DEV_DB_PORT=5433/' .env.dev
        sed -i 's/DEV_REDIS_PORT=6379/DEV_REDIS_PORT=6380/' .env.dev
        echo "✅ Updated .env.dev to use ports 5433 and 6380"
        echo "📝 Backup saved as .env.dev.backup"
    else
        echo "❌ .env.dev not found. Run dev/setup-dev.sh first."
    fi
fi