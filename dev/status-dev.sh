#!/bin/bash
# Check development environment status

echo "🔍 Selextract Cloud - Development Status"
echo "========================================"

# Get script directory and navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Load environment variables from root
if [ -f ".env.dev" ]; then
    source .env.dev
else
    echo "❌ .env.dev not found"
    exit 1
fi

echo ""
echo "📋 Environment Configuration:"
echo "  Database Port: $DEV_DB_PORT"
echo "  Redis Port: $DEV_REDIS_PORT"  
echo "  API Port: $DEV_API_PORT"
echo "  Frontend Port: $DEV_FRONTEND_PORT"

echo ""
echo "🐳 Infrastructure Status:"
if docker compose -f docker-compose.dev.yml ps &>/dev/null; then
    docker compose -f docker-compose.dev.yml ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
else
    echo "  ❌ Infrastructure not running"
fi

echo ""
echo "🔌 Port Status:"
ports=("$DEV_DB_PORT" "$DEV_REDIS_PORT" "$DEV_API_PORT" "$DEV_FRONTEND_PORT")
services=("PostgreSQL" "Redis" "API" "Frontend")

for i in "${!ports[@]}"; do
    port="${ports[$i]}"
    service="${services[$i]}"
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "  ✅ Port $port ($service) - In use"
    else
        echo "  ⭕ Port $port ($service) - Available"
    fi
done

echo ""
echo "🐍 API Environment:"
if [ -d "../api/venv" ]; then
    echo "  ✅ Virtual environment exists"
    if [ -f "../api/venv/bin/python" ]; then
        python_version=$(../api/venv/bin/python --version 2>&1)
        echo "  📦 Python: $python_version"
    fi
else
    echo "  ❌ Virtual environment not found"
fi

echo ""
echo "⚛️ Frontend Environment:"
if [ -d "../frontend/node_modules" ]; then
    echo "  ✅ Node modules installed"
    if command -v node &> /dev/null; then
        node_version=$(node --version)
        echo "  📦 Node.js: $node_version"
    fi
else
    echo "  ❌ Node modules not found"
fi

echo ""
echo "🌐 Service Health Checks:"

# Check API health
if curl -s -f "http://localhost:$DEV_API_PORT/health" > /dev/null 2>&1; then
    echo "  ✅ API responding at http://localhost:$DEV_API_PORT"
else
    echo "  ❌ API not responding at http://localhost:$DEV_API_PORT"
fi

# Check Frontend health  
if curl -s -f "http://localhost:$DEV_FRONTEND_PORT/api/health" > /dev/null 2>&1; then
    echo "  ✅ Frontend responding at http://localhost:$DEV_FRONTEND_PORT"
else
    echo "  ❌ Frontend not responding at http://localhost:$DEV_FRONTEND_PORT"
fi

echo ""
echo "🛠️  Quick Actions:"
echo "  Setup: ./setup-dev.sh"
echo "  Start API: ./start-api.sh"
echo "  Start Frontend: ./start-frontend.sh"
echo "  Stop All: ./stop-dev.sh"
echo "  Database: ../scripts/dev/db-migrate.sh status"