# Docker Container Naming Migration Guide

This guide helps you migrate from inconsistent container naming to the standardized "selectium-saas" project naming scheme.

## Overview of Changes

We've standardized all Docker container naming to use consistent "selectium-saas" project prefixes by:

1. **Added COMPOSE_PROJECT_NAME** to all environment files (`.env`, `.env.example`, `.env.prod`)
2. **Removed hardcoded container names** from all Docker Compose files
3. **Updated monitoring configurations** to use standardized container references
4. **Standardized network naming** across all compose files

## Expected Container Names After Migration

With `COMPOSE_PROJECT_NAME=selectium-saas`, your containers will be named:

### Development Environment (`docker-compose.yml`)
- `selectium-saas_postgres_1`
- `selectium-saas_redis_1`
- `selectium-saas_api_1`
- `selectium-saas_worker_1` (scaled: `selectium-saas_worker_2`, `selectium-saas_worker_3`, etc.)
- `selectium-saas_frontend_1`
- `selectium-saas_nginx_1`

### Production Environment (`docker-compose.prod.yml`)
- `selectium-saas_postgres_1`
- `selectium-saas_redis_1`
- `selectium-saas_api_1`
- `selectium-saas_worker_1` (scaled: `selectium-saas_worker_2`, `selectium-saas_worker_3`, etc.)
- `selectium-saas_frontend_1`
- `selectium-saas_nginx_1`
- `selectium-saas_prometheus_1`
- `selectium-saas_grafana_1`
- `selectium-saas_alertmanager_1`
- `selectium-saas_postgres-exporter_1`
- `selectium-saas_redis-exporter_1`

### Monitoring Stack (`monitoring/docker-compose.monitoring.yml`)
- `selectium-saas_prometheus_1`
- `selectium-saas_grafana_1`
- `selectium-saas_alertmanager_1`
- `selectium-saas_node-exporter_1`
- `selectium-saas_postgres-exporter_1`
- `selectium-saas_redis-exporter_1`
- `selectium-saas_nginx-exporter_1`
- `selectium-saas_celery-exporter_1`

## Migration Steps

### Step 1: Backup Current Environment

**⚠️ CRITICAL:** Always backup before making changes!

```bash
# Create full backup
./scripts/backup.sh

# Document current container state
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" > pre-migration-containers.txt

# Backup current environment files
cp .env .env.backup
cp .env.prod .env.prod.backup
```

### Step 2: Update Environment Files

The COMPOSE_PROJECT_NAME has already been added to your environment files. Verify it's present:

```bash
# Check development environment
grep "COMPOSE_PROJECT_NAME" .env
# Should output: COMPOSE_PROJECT_NAME=selectium-saas

# Check production environment
grep "COMPOSE_PROJECT_NAME" .env.prod
# Should output: COMPOSE_PROJECT_NAME=selectium-saas
```

### Step 3: Migration for Development Environment

```bash
# Stop current services
docker-compose down

# Pull any updated images
docker-compose pull

# Remove old containers with inconsistent names (if any exist)
docker rm -f selextract_postgres selextract_redis selextract_api selextract_frontend selextract_nginx 2>/dev/null || true

# Start with new naming
docker-compose up -d

# Verify new container names
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
```

### Step 4: Migration for Production Environment

**⚠️ Schedule during maintenance window - this will cause downtime!**

```bash
# Enable maintenance mode (if configured)
# Update MAINTENANCE_MODE=true in .env.prod

# Stop current production services
docker-compose -f docker-compose.prod.yml down

# Remove old containers with inconsistent names
docker rm -f selextract-postgres selextract-redis selextract-api selextract-frontend selextract-nginx \
              selextract-prometheus selextract-grafana selextract-alertmanager \
              selextract-postgres-exporter selextract-redis-exporter 2>/dev/null || true

# Start with new naming
docker-compose -f docker-compose.prod.yml up -d

# Verify health after migration
./scripts/health-check.sh

# Disable maintenance mode
# Update MAINTENANCE_MODE=false in .env.prod
```

### Step 5: Migration for Monitoring Stack

```bash
# Navigate to monitoring directory
cd monitoring

# Stop monitoring services
docker-compose -f docker-compose.monitoring.yml down

# Remove old containers
docker rm -f selextract-prometheus selextract-grafana selextract-alertmanager \
              selextract-node-exporter selextract-postgres-exporter \
              selextract-redis-exporter selextract-nginx-exporter \
              selextract-celery-exporter 2>/dev/null || true

# Start with new naming
docker-compose -f docker-compose.monitoring.yml up -d

# Return to project root
cd ..
```

## Verification Commands

### Verify Container Names

```bash
# Check all containers have "selectium-saas" prefix
docker ps --format "table {{.Names}}\t{{.Image}}" | grep selectium-saas

# Verify no old containers remain
docker ps -a | grep -E "(selextract_|selextract-)" | grep -v selectium-saas
# This should return no results
```

### Verify Service Connectivity

```bash
# Test database connectivity
docker exec selectium-saas_postgres_1 pg_isready -U postgres

# Test Redis connectivity
docker exec selectium-saas_redis_1 redis-cli ping

# Test API health
curl -f http://localhost:8000/health

# Test worker status
docker exec selectium-saas_worker_1 celery -A main inspect ping
```

### Verify Networks

```bash
# Check network names are consistent
docker network ls | grep selectium-saas

# Verify services can communicate
docker exec selectium-saas_api_1 ping selectium-saas_postgres_1
docker exec selectium-saas_worker_1 ping selectium-saas_redis_1
```

## Troubleshooting

### Issue: Services Can't Connect After Migration

**Symptoms:**
- Database connection refused
- Redis connection errors
- API health checks failing

**Solution:**
```bash
# Recreate networks
docker-compose down
docker network prune -f
docker-compose up -d

# Check network connectivity
docker network inspect selectium-saas_selextract_internal
```

### Issue: Monitoring Can't Connect to Main Services

**Symptoms:**
- Prometheus targets showing as down
- Grafana showing no data
- Exporters failing to connect

**Solution:**
```bash
# Update external network references
cd monitoring
docker-compose -f docker-compose.monitoring.yml down
docker network ls | grep selectium-saas  # Note the correct network name
docker-compose -f docker-compose.monitoring.yml up -d
```

### Issue: Old Containers Still Running

**Symptoms:**
- Mixed container naming
- Port conflicts
- Duplicate services

**Solution:**
```bash
# Stop all containers
docker stop $(docker ps -q)

# Remove containers with old naming
docker rm $(docker ps -a -q --filter "name=selextract_" --filter "name=selextract-")

# Remove old networks
docker network rm selextract-network 2>/dev/null || true
docker network rm selextract_default 2>/dev/null || true

# Start fresh
docker-compose -f docker-compose.prod.yml up -d
```

## Rollback Procedure

If migration fails and you need to rollback:

```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down
cd monitoring && docker-compose -f docker-compose.monitoring.yml down && cd ..

# Restore environment files
cp .env.backup .env
cp .env.prod.backup .env.prod

# Restore from backup
./scripts/restore.sh /path/to/backup/file

# Start services with old configuration
docker-compose -f docker-compose.prod.yml up -d
```

## Post-Migration Validation Checklist

- [ ] All containers use "selectium-saas" prefix
- [ ] No containers with old naming remain
- [ ] All services pass health checks
- [ ] Database connectivity working
- [ ] Redis connectivity working
- [ ] API responding correctly
- [ ] Workers processing tasks
- [ ] Frontend accessible
- [ ] Monitoring stack operational
- [ ] Prometheus collecting metrics
- [ ] Grafana dashboards showing data
- [ ] Alerts configured correctly

## Network Changes Summary

### Before Migration
- `selextract-network` (in production)
- `selextract_internal` (in development)
- `selextract_public` (in development)
- Mixed external network references in monitoring

### After Migration
- `selectium-saas_selextract_internal` (standardized across all environments)
- `selectium-saas_selextract_public` (development only)
- Consistent external network references: `selectium-saas_selextract_internal`

## Important Notes

1. **Container Names:** Docker Compose automatically appends `_1`, `_2`, etc. to service names
2. **Service Discovery:** Internal service communication uses service names (e.g., `postgres`, `redis`), not container names
3. **Scaling:** When scaling services, containers will be named `selectium-saas_worker_1`, `selectium-saas_worker_2`, etc.
4. **Monitoring:** External monitoring references now use the standardized container names
5. **Backups:** Ensure your backup scripts account for the new container names

## Scripts That May Need Updates

Some custom scripts may reference container names directly. Update these patterns:

### Old Patterns to Replace
```bash
# Old patterns
docker exec selextract_postgres ...
docker exec selextract-postgres ...
docker logs selextract_worker ...
```

### New Patterns to Use
```bash
# New patterns (use service names with docker-compose)
docker-compose exec postgres ...
docker-compose exec worker ...
docker-compose logs worker

# Or use the full container names
docker exec selectium-saas_postgres_1 ...
docker exec selectium-saas_worker_1 ...
```

## Support

If you encounter issues during migration:

1. **Check logs:** `docker-compose logs <service_name>`
2. **Verify networks:** `docker network ls`
3. **Check connectivity:** Use ping tests between containers
4. **Review configuration:** Ensure COMPOSE_PROJECT_NAME is set correctly
5. **Restore from backup:** If necessary, follow the rollback procedure

For additional support, refer to:
- [`docs/TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
- [`docs/OPERATIONS_RUNBOOK.md`](OPERATIONS_RUNBOOK.md)
- [`docs/QUICK_START.md`](QUICK_START.md)