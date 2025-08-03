#!/bin/bash

# Selextract Cloud API Entrypoint Script
# Initializes the API environment and database

set -e

echo "=== Selextract Cloud API Starting ==="

# Create required directories
mkdir -p /app/logs /app/uploads /app/data
chown selextract:selextract /app/logs /app/uploads /app/data 2>/dev/null || true

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

# Initialize database (tables will be created by FastAPI lifespan)
echo "Database initialization will be handled by FastAPI lifespan manager"

# Verify API dependencies
echo "Verifying API configuration..."
python3 -c "
try:
    from database import db_config
    from models import Base
    from auth import get_google_auth_url
    print('API configuration verified successfully')
except Exception as e:
    print(f'API configuration error: {e}')
    exit(1)
"

echo "Starting FastAPI application..."
exec "$@"