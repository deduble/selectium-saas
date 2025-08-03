#!/bin/bash
# One-command quick start for development

set -e

echo "🚀 Selextract Cloud - Quick Development Start"
echo "============================================="

# Get script directory and navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Check if setup has been run
if [ ! -f ".env.dev" ] || [ ! -d "api/venv" ] || [ ! -d "frontend/node_modules" ]; then
    echo "🔧 First-time setup required. Running setup..."
    ./dev/setup-dev.sh
fi

# Start infrastructure
echo "🐳 Starting infrastructure containers..."
docker compose -f dev/docker-compose.dev.yml up -d

# Wait for infrastructure
echo "⏳ Waiting for infrastructure to be ready..."
sleep 5

# Check if infrastructure is healthy
if ! docker compose -f dev/docker-compose.dev.yml ps | grep -q "healthy"; then
    echo "⚠️  Infrastructure may still be starting. Check status with: docker compose -f dev/docker-compose.dev.yml ps"
fi

echo ""
echo "✅ Quick start complete!"
echo ""
echo "🚀 Next: Start your development services:"
echo ""
echo "Option 1 - Separate Terminals (Recommended):"
echo "  Terminal 1: cd dev && ./start-api.sh"
echo "  Terminal 2: cd dev && ./start-frontend.sh"
echo ""
echo "Option 2 - VS Code Tasks:"
echo "  Ctrl+Shift+P → 'Tasks: Run Task' → Select task"
echo ""
echo "Option 3 - VS Code Debug (F5):"
echo "  F5 → Select 'Debug Full Stack'"
echo ""
echo "🌐 Development URLs:"
echo "  • Frontend: http://localhost:3000"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • API Health: http://localhost:8000/health"
echo ""
echo "📖 See docs/DEVELOPMENT_GUIDE.md for detailed information"