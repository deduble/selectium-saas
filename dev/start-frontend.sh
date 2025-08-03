#!/bin/bash
# Start Frontend with hot reloading and environment validation

set -e

echo "⚛️ Starting Selextract Frontend with hot reloading..."

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
fi

# Navigate to frontend directory
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "❌ Node modules not found. Run ./dev/setup-dev.sh first."
    exit 1
fi

# Expert Recommendation: Validate API connectivity
echo "🔍 Validating API connection..."
if curl -s -f "http://localhost:$DEV_API_PORT/health" > /dev/null; then
    echo "✅ API connection successful"
else
    echo "⚠️  API not responding. Make sure API is running on port $DEV_API_PORT"
    echo "💡 Start API first: ./start-api.sh"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start frontend development server
echo "🔥 Starting Next.js development server on port $DEV_FRONTEND_PORT..."
echo "🌐 Frontend: http://localhost:$DEV_FRONTEND_PORT"
echo "🛑 Press Ctrl+C to stop"
echo ""

npm run dev -- --port $DEV_FRONTEND_PORT