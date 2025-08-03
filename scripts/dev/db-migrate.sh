#!/bin/bash
# Database migration utility for development

set -e

cd "$(dirname "$0")/../../api"

# Ensure API environment is activated
if [ ! -d "venv" ]; then
    echo "❌ API environment not set up. Run dev/setup-dev.sh first"
    exit 1
fi

source venv/bin/activate
export $(grep -v '^#' ../dev/.env.dev | xargs)

case "${1:-}" in
    "upgrade")
        echo "⬆️ Running database migrations..."
        alembic upgrade head
        echo "✅ Migrations completed"
        ;;
    "downgrade")
        echo "⬇️ Rolling back database migration..."
        alembic downgrade -1
        echo "✅ Rollback completed"
        ;;
    "reset")
        echo "🗑️ Resetting database..."
        read -p "This will destroy all data. Continue? (y/N): " confirm
        if [[ $confirm == [yY] ]]; then
            alembic downgrade base
            alembic upgrade head
            echo "✅ Database reset completed"
        fi
        ;;
    "status")
        echo "📊 Database migration status:"
        alembic current
        ;;
    *)
        echo "📋 Database Migration Utility"
        echo "Usage: $0 {upgrade|downgrade|reset|status}"
        echo ""
        echo "Commands:"
        echo "  upgrade   - Apply pending migrations"
        echo "  downgrade - Rollback last migration"
        echo "  reset     - Reset database (destructive)"
        echo "  status    - Show current migration status"
        ;;
esac