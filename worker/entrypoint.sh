#!/bin/bash

# Selextract Cloud Worker Entrypoint Script
# Initializes the worker environment and starts supervisord

set -e

echo "=== Selextract Cloud Worker Starting ==="

# Create required directories
mkdir -p /app/logs /app/tmp /app/results
chown selextract:selextract /app/logs /app/tmp /app/results

# Wait for database to be ready
echo "Waiting for database to be ready..."
until python3 -c "
import os
import psycopg2
try:
    database_url = os.getenv('DATABASE_URL')
    print(f'Connecting to: {database_url}')
    conn = psycopg2.connect(database_url)
    conn.close()
    print('Database is ready!')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" 2>/dev/null; do
    echo "Database not ready, waiting 5 seconds..."
    sleep 5
done

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
until python3 -c "
import os
import redis
try:
    r = redis.from_url(os.getenv('REDIS_URL'))
    r.ping()
    print('Redis is ready!')
except:
    exit(1)
" 2>/dev/null; do
    echo "Redis not ready, waiting 5 seconds..."
    sleep 5
done

# Skip database migrations for now - will be handled by API service
echo "Skipping database migrations (handled by API service)..."
# cd /app
# python3 -m alembic upgrade head

# Verify worker files are accessible
echo "Verifying worker configuration..."
python3 -c "
try:
    from celery_config import celery_app
    from task_schemas import validate_task_config
    from proxies import get_proxy_manager
    print('Worker configuration verified successfully')
except Exception as e:
    print(f'Worker configuration error: {e}')
    exit(1)
"

echo "Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf