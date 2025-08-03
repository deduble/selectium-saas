#!/bin/bash
# Start API with hot reloading and comprehensive error handling

set -e

echo "🐍 Starting Selextract API with hot reloading..."

# Get script directory to work from any location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Navigate to project root
cd "$PROJECT_ROOT"

# Load environment variables from both root .env and root .env.dev
if [ -f ".env" ]; then
    echo "📄 Loading root environment variables..."
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi

if [ -f ".env.dev" ]; then
    echo "📄 Loading development environment variables from root .env.dev..."
    export $(grep -v '^#' .env.dev | grep -v '^$' | xargs)
else
    echo "❌ .env.dev not found. Run ./dev/setup-dev.sh first."
    exit 1
fi

# Check for port conflicts before starting infrastructure
echo "🔌 Checking for port conflicts..."
check_port_conflict() {
    local port=$1
    local service=$2
    
    if netstat -an 2>/dev/null | grep -q ":$port.*LISTENING" || \
       ss -ln 2>/dev/null | grep -q ":$port " || \
       lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port $port is already in use (needed for $service)"
        return 1
    fi
    return 0
}

conflicts=0
if ! check_port_conflict "${DEV_DB_PORT:-5432}" "PostgreSQL"; then
    conflicts=$((conflicts + 1))
fi

if ! check_port_conflict "${DEV_REDIS_PORT:-6379}" "Redis"; then
    conflicts=$((conflicts + 1))
fi

if [ $conflicts -gt 0 ]; then
    echo ""
    echo "🚨 Port conflicts detected! Here's how to fix:"
    echo ""
    echo "Option 1 - Stop conflicting services:"
    echo "  Windows: Stop PostgreSQL and Redis services in Services.msc"
    echo "  Linux/Mac: sudo systemctl stop postgresql redis"
    echo ""
    echo "Option 2 - Use different ports (update .env.dev):"
    echo "  DEV_DB_PORT=5433"
    echo "  DEV_REDIS_PORT=6380"
    echo ""
    echo "Option 3 - Kill processes using ports:"
    if command -v lsof >/dev/null 2>&1; then
        echo "  lsof -ti:${DEV_DB_PORT:-5432} | xargs kill -9"
        echo "  lsof -ti:${DEV_REDIS_PORT:-6379} | xargs kill -9"
    else
        echo "  netstat -ano | findstr :${DEV_DB_PORT:-5432} (then taskkill /PID <PID>)"
        echo "  netstat -ano | findstr :${DEV_REDIS_PORT:-6379} (then taskkill /PID <PID>)"
    fi
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if infrastructure is running
if ! docker compose -f dev/docker-compose.dev.yml ps | grep -q "Up"; then
    echo "🐳 Infrastructure not running. Starting..."
    if ! docker compose -f dev/docker-compose.dev.yml up -d; then
        echo "❌ Failed to start infrastructure. Check port conflicts above."
        exit 1
    fi
    echo "⏳ Waiting for infrastructure to be ready..."
    sleep 10
fi

# Navigate to API directory
cd api

# Verify virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup-dev.sh first."
    exit 1
fi

# Activate virtual environment (Windows-compatible)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ -f "venv/Scripts/activate" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Development environment variables already loaded above

# Expert Recommendation: Validate database connection before starting
echo "🔍 Validating database connection..."

# Use appropriate Python command (should use venv's python after activation)
python_cmd="python"
if ! command -v python &> /dev/null && command -v python3 &> /dev/null; then
    python_cmd="python3"
fi

$python_cmd -c "
from database import engine
from sqlalchemy import text
try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

# Start API server with hot reloading
echo "🔥 Starting FastAPI with hot reload on port $DEV_API_PORT..."
echo "📖 API Documentation: http://localhost:$DEV_API_PORT/docs"
echo "🛑 Press Ctrl+C to stop"
echo ""

uvicorn main:app \
    --reload \
    --host 0.0.0.0 \
    --port $DEV_API_PORT \
    --log-level debug \
    --access-log