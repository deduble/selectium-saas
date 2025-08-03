#!/bin/bash
# Stop development environment

echo "🛑 Stopping Selextract Cloud development environment..."

# Stop infrastructure containers
docker compose -f docker-compose.dev.yml down

echo "✅ Development environment stopped"
echo "💡 API and Frontend processes may still be running - stop them manually if needed"