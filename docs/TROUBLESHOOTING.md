# Selextract Cloud Troubleshooting Guide

This guide provides solutions to common issues encountered during deployment and operation of Selextract Cloud.

## Table of Contents

- [Deployment Issues](#deployment-issues)
- [Service Issues](#service-issues)
- [Database Issues](#database-issues)
- [Worker and Task Issues](#worker-and-task-issues)
- [SSL and Certificate Issues](#ssl-and-certificate-issues)
- [Performance Issues](#performance-issues)
- [Authentication Issues](#authentication-issues)
- [Monitoring and Logging Issues](#monitoring-and-logging-issues)
- [Network and Connectivity Issues](#network-and-connectivity-issues)
- [Storage and Backup Issues](#storage-and-backup-issues)

---

## Local Development Setup Issues (FIXED) 🚀

### Missing Environment Variables (RESOLVED)

**Problem:** Environment variable warnings during startup:
```
WARNING: "DATABASE_URL" variable is not set. Defaulting to a blank string.
WARNING: "REDIS_URL" variable is not set. Defaulting to a blank string.
WARNING: "NEXT_PUBLIC_API_URL" variable is not set. Defaulting to a blank string.
```

**✅ Solution Applied:** The `.env` file now includes all required environment variables:

```bash
DATABASE_URL=postgresql://selextract:supersecretpassword@postgres:5432/selextract
REDIS_URL=redis://:supersecretpassword@redis:6379/0
NEXT_PUBLIC_API_URL=http://localhost:8000
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

**If you still see these warnings:**

1. **Verify `.env` file exists:**
   ```bash
   ls -la .env
   ```

2. **Re-copy from example:**
   ```bash
   cp .env.example .env
   ```

3. **Check required variables:**
   ```bash
   grep -E "(DATABASE_URL|REDIS_URL|NEXT_PUBLIC_API_URL)" .env
   ```

### Database Initialization Issues (RESOLVED)

**Problem:** Alembic configuration errors:
```
FAILED: No config file 'alembic.ini' found, or file has no '[alembic]' section
```

**✅ Solution Applied:**
- Created API container entrypoint script for proper initialization
- Database setup now happens automatically via FastAPI lifespan manager
- No manual database setup required

**Verification Commands:**
```bash
# Check API health (should work without manual DB setup)
curl http://localhost:8000/health

# Check container status (all should be healthy)
docker-compose ps

# Verify environment variables loaded (no warnings)
docker-compose up -d
```

**Expected Success Indicators:**
- ✅ No environment variable warnings on startup
- ✅ API responds with health status: `{"status":"healthy"}` or `{"status":"degraded"}`
- ✅ Frontend responds: `{"status":"ok"}`
- ✅ All containers show "healthy" status

---

## Deployment Issues

### Issue: Docker Compose Services Fail to Start

**Symptoms:**
- Services exit with code 1 or 125
- "Port already in use" errors
- Container restart loops

**Diagnosis:**
```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# View service logs
docker-compose -f docker-compose.prod.yml logs service_name

# Check port usage
netstat -tulpn | grep :80
netstat -tulpn | grep :443
```

**Solutions:**

1. **Port conflicts:**
```bash
# Stop conflicting services
sudo systemctl stop apache2 nginx
sudo pkill -f nginx

# Or change ports in docker-compose.prod.yml
# nginx:
#   ports:
#     - "8080:80"
#     - "8443:443"
```

2. **Permission issues:**
```bash
# Fix permissions
sudo chown -R deploy:deploy /opt/selextract-cloud
sudo chmod -R 755 /opt/selextract-cloud
chmod 600 .env.prod
```

3. **Resource limits:**
```bash
# Check available resources
free -h
df -h

# Reduce service replicas if needed
docker-compose -f docker-compose.prod.yml up -d --scale worker=1
```

### Issue: Environment Variables Not Loading

**Symptoms:**
- "Missing required environment variable" errors
- Services using default values
- Authentication failures

**Diagnosis:**
```bash
# Check environment file
cat .env.prod
env | grep SELEXTRACT

# Verify Docker can read environment
docker-compose -f docker-compose.prod.yml config
```

**Solutions:**

1. **File permissions:**
```bash
chmod 600 .env.prod
chown deploy:deploy .env.prod
```

2. **Variable format:**
```bash
# Ensure no spaces around = signs
# Wrong: VARIABLE = value
# Correct: VARIABLE=value

# Quote complex values
JWT_SECRET_KEY="abc123!@#def456"
```

3. **Reload configuration:**
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Issue: SSL Certificate Setup Fails

**Symptoms:**
- Certbot errors
- "Challenge failed" messages
- Certificate not found errors

**Diagnosis:**
```bash
# Test DNS resolution
nslookup api.selextract.com
nslookup app.selextract.com

# Check port accessibility
curl -I http://api.selextract.com
telnet api.selextract.com 80
```

**Solutions:**

1. **DNS propagation:**
```bash
# Wait for DNS propagation (up to 48 hours)
# Use online DNS checker tools

# Temporary hosts file entry for testing
echo "YOUR_SERVER_IP api.selextract.com" >> /etc/hosts
```

2. **Firewall issues:**
```bash
# Ensure ports are open
ufw allow 80
ufw allow 443
ufw reload

# Check iptables rules
iptables -L
```

3. **Manual certificate generation:**
```bash
# Stop nginx temporarily
docker-compose -f docker-compose.prod.yml stop nginx

# Get certificate with standalone mode
certbot certonly --standalone -d api.selextract.com -d app.selextract.com

# Restart nginx
docker-compose -f docker-compose.prod.yml start nginx
```

---

## Service Issues

### Issue: API Service Returns 502 Bad Gateway

**Symptoms:**
- Nginx shows 502 errors
- API service not responding
- Upstream connection refused

**Diagnosis:**
```bash
# Check API service status
docker-compose -f docker-compose.prod.yml logs api

# Test internal connectivity
docker-compose -f docker-compose.prod.yml exec nginx curl http://api:8000/health

# Check service health
curl -H "Host: api.selextract.com" http://localhost/health
```

**Solutions:**

1. **API service crashed:**
```bash
# Restart API service
docker-compose -f docker-compose.prod.yml restart api

# Check for Python errors in logs
docker-compose -f docker-compose.prod.yml logs api | grep -i error
```

2. **Database connection issues:**
```bash
# Test database connectivity
docker-compose -f docker-compose.prod.yml exec api python -c "
import os
import psycopg2
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
print('Database connected successfully')
"
```

3. **Resource exhaustion:**
```bash
# Check memory usage
docker stats --no-stream
free -h

# Scale down if needed
docker-compose -f docker-compose.prod.yml up -d --scale worker=1
```

### Issue: Worker Tasks Not Processing

**Symptoms:**
- Tasks stuck in PENDING state
- Queue depth increasing
- No task execution logs

**Diagnosis:**
```bash
# Check worker status
docker-compose -f docker-compose.prod.yml logs worker

# Check queue status
docker-compose -f docker-compose.prod.yml exec redis redis-cli LLEN celery

# Monitor worker activity
docker-compose -f docker-compose.prod.yml exec worker celery -A worker.celery_config inspect active
```

**Solutions:**

1. **Worker not connected:**
```bash
# Restart worker
docker-compose -f docker-compose.prod.yml restart worker

# Check Celery broker connectivity
docker-compose -f docker-compose.prod.yml exec worker python -c "
from celery import Celery
app = Celery('worker', broker='redis://redis:6379/0')
print('Broker connected:', app.control.ping())
"
```

2. **Memory/resource issues:**
```bash
# Check worker memory usage
docker stats selectium-saas_worker_1

# Reduce worker concurrency
# In worker/celery_config.py:
# worker_concurrency = 2  # Reduce from 4
```

3. **Proxy connectivity issues:**
```bash
# Test proxy connectivity
docker-compose -f docker-compose.prod.yml exec worker python -c "
from worker.proxies import ProxyManager
pm = ProxyManager()
print('Proxy test:', pm.test_proxy())
"
```

### Issue: Frontend Not Loading

**Symptoms:**
- Blank page or loading errors
- JavaScript errors in browser
- 404 for static assets

**Diagnosis:**
```bash
# Check frontend service
docker-compose -f docker-compose.prod.yml logs frontend

# Test frontend access
curl -H "Host: app.selextract.com" http://localhost/

# Check build output
docker-compose -f docker-compose.prod.yml exec frontend ls -la /app/.next
```

**Solutions:**

1. **Build issues:**
```bash
# Rebuild frontend
docker-compose -f docker-compose.prod.yml build --no-cache frontend
docker-compose -f docker-compose.prod.yml up -d frontend
```

2. **Environment configuration:**
```bash
# Check Next.js environment variables
docker-compose -f docker-compose.prod.yml exec frontend env | grep NEXT

# Verify API connectivity from frontend
docker-compose -f docker-compose.prod.yml exec frontend curl http://api:8000/health
```

3. **Static file serving:**
```bash
# Check nginx configuration
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
docker-compose -f docker-compose.prod.yml restart nginx
```

---

## Database Issues

### Issue: Database Connection Refused

**Symptoms:**
- "Connection refused" errors
- "Could not connect to server" messages
- API service failing to start

**Diagnosis:**
```bash
# Check PostgreSQL status
docker-compose -f docker-compose.prod.yml logs postgres

# Test database connectivity
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U postgres

# Check port binding
docker-compose -f docker-compose.prod.yml ps postgres
```

**Solutions:**

1. **Service not running:**
```bash
# Start PostgreSQL
docker-compose -f docker-compose.prod.yml up -d postgres

# Check logs for startup errors
docker-compose -f docker-compose.prod.yml logs postgres | tail -50
```

2. **Connection string issues:**
```bash
# Verify DATABASE_URL format
echo $DATABASE_URL
# Should be: postgresql://user:password@host:port/database

# Test connection manually
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "SELECT 1;"
```

3. **Resource constraints:**
```bash
# Check disk space for database
df -h
docker-compose -f docker-compose.prod.yml exec postgres df -h /var/lib/postgresql/data

# Check memory usage
free -h
```

### Issue: Database Migration Failures

**Symptoms:**
- Alembic migration errors
- Schema version mismatches
- "Table already exists" errors

**Diagnosis:**
```bash
# Check migration status
docker-compose -f docker-compose.prod.yml exec api alembic current
docker-compose -f docker-compose.prod.yml exec api alembic history --verbose

# Check database schema
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "\dt"
```

**Solutions:**

1. **Reset migrations:**
```bash
# Backup database first
./scripts/backup.sh

# Reset migrations
docker-compose -f docker-compose.prod.yml exec api alembic stamp head
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

2. **Manual schema fixes:**
```bash
# Connect to database
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract

# Check and fix schema manually
\d+ table_name
DROP TABLE IF EXISTS problematic_table;
```

### Issue: Database Performance Problems

**Symptoms:**
- Slow query response times
- High CPU usage on database
- Connection pool exhaustion

**Diagnosis:**
```bash
# Check active connections
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "
SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';
"

# Check slow queries
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
"

# Check database size
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "
SELECT pg_size_pretty(pg_database_size('selextract'));
"
```

**Solutions:**

1. **Optimize queries:**
```bash
# Analyze slow queries
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "
EXPLAIN ANALYZE SELECT * FROM tasks WHERE created_at > NOW() - INTERVAL '1 day';
"

# Add indexes
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "
CREATE INDEX CONCURRENTLY idx_tasks_created_at ON tasks(created_at);
"
```

2. **Tune PostgreSQL:**
```bash
# Update PostgreSQL configuration
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -c "
ALTER SYSTEM SET shared_buffers = '1GB';
ALTER SYSTEM SET effective_cache_size = '3GB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
SELECT pg_reload_conf();
"
```

3. **Database maintenance:**
```bash
# Run vacuum and analyze
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "
VACUUM ANALYZE;
"

# Check and fix bloat
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "
REINDEX DATABASE selextract;
"
```

---

## Worker and Task Issues

### Issue: Worker Containers Continuously Restarting ✅ RESOLVED

**Symptoms:**
- Worker containers in restart loops
- "supervisord.pid does not exist" errors
- "No module named 'task_schemas'" import errors
- Celery autodiscovery failures

**Root Causes Identified:**
1. Missing `/app/tmp` directory in worker containers
2. Incorrect relative imports in task modules
3. Celery autodiscovery configuration pointing to wrong module paths
4. Missing environment variable configuration

**✅ Complete Solution Implemented:**

```bash
# 1. Fixed Dockerfile to create required directories
# In worker/Dockerfile - added:
RUN mkdir -p /app/tmp /app/logs /app/results

# 2. Fixed import statements in worker/tasks.py
# Changed: from .task_schemas import TaskConfig
# To: from task_schemas import TaskConfig

# 3. Fixed Celery autodiscovery in worker/main.py
# Changed: app.autodiscover_tasks(['worker.tasks'])
# To: app.autodiscover_tasks(['tasks'])

# 4. Ensured proper environment variables in docker-compose.yml
```

**Verification Commands:**
```bash
# Check worker stability (should show RUNNING for 10+ minutes)
docker-compose ps worker

# Verify successful startup logs
docker-compose logs worker | grep -E "(RUNNING|Database is ready|Redis is ready)"

# Confirm task discovery
docker-compose exec worker celery -A main inspect registered
```

**Expected Success Indicators:**
- ✅ `celery-worker entered RUNNING state`
- ✅ `celery-beat entered RUNNING state`
- ✅ `Database is ready!`
- ✅ `Redis is ready!`
- ✅ No restart loops for 10+ minutes

### Issue: Tasks Failing with Timeout Errors

**Symptoms:**
- Tasks marked as FAILED
- "SoftTimeLimitExceeded" errors
- Browser automation timeouts

**Diagnosis:**
```bash
# Check task logs
docker-compose -f docker-compose.prod.yml logs worker | grep -i timeout

# Check task configuration
docker-compose -f docker-compose.prod.yml exec api python -c "
from api.models import Task
task = Task.query.filter_by(status='FAILED').first()
print(task.error_details if task else 'No failed tasks')
"

# Monitor task execution time
docker-compose -f docker-compose.prod.yml exec worker celery -A main inspect stats
```

**Solutions:**

1. **Increase task timeouts:**
```python
# In worker/tasks.py
@app.task(bind=True, time_limit=600, soft_time_limit=300)  # Increase from default
def scrape_task(self, task_id):
    # Task implementation
```

2. **Optimize scraping logic:**
```python
# In worker/tasks.py
# Reduce page load timeout
page.set_default_timeout(30000)  # 30 seconds instead of 60

# Use faster selectors
await page.wait_for_selector("h1", timeout=10000)  # Wait less time
```

3. **Resource allocation:**
```bash
# Increase worker memory limits
# In docker-compose.prod.yml:
# worker:
#   deploy:
#     resources:
#       limits:
#         memory: '4G'  # Increase from 2G
```

### Issue: Proxy Connection Failures

**Symptoms:**
- "Proxy connection refused" errors
- High proxy error rates
- Tasks failing with network errors

**Diagnosis:**
```bash
# Test proxy connectivity
docker-compose -f docker-compose.prod.yml exec worker python -c "
from worker.proxies import ProxyManager
pm = ProxyManager()
proxies = pm.get_working_proxies()
print(f'Working proxies: {len(proxies)}')
"

# Check proxy API response
curl -H "Authorization: Token YOUR_WEBSHARE_API_KEY" https://proxy.webshare.io/api/v2/proxy/list/
```

**Solutions:**

1. **Refresh proxy list:**
```bash
# Clear proxy cache
docker-compose -f docker-compose.prod.yml exec redis redis-cli DEL proxy:working_proxies

# Restart worker to refresh proxies
docker-compose -f docker-compose.prod.yml restart worker
```

2. **Update proxy configuration:**
```bash
# Check Webshare.io API key
docker-compose -f docker-compose.prod.yml exec worker python -c "
import os
print('API Key set:', bool(os.getenv('WEBSHARE_API_KEY')))
"

# Test without proxies temporarily
# In worker/tasks.py, comment out proxy usage for testing
```

3. **Implement fallback strategy:**
```python
# In worker/proxies.py
def get_proxy_with_fallback(self):
    """Get proxy with fallback to direct connection"""
    try:
        return self.get_random_proxy()
    except Exception:
        return None  # Use direct connection
```

### Issue: Browser Automation Failures

**Symptoms:**
- Playwright/Chrome crashes
- "Browser disconnected" errors
- Memory exhaustion in workers

**Diagnosis:**
```bash
# Check browser processes
docker-compose -f docker-compose.prod.yml exec worker ps aux | grep chrome

# Check memory usage
docker stats selectium-saas_worker_1

# Test browser launch
docker-compose -f docker-compose.prod.yml exec worker python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    print('Browser launched successfully')
    browser.close()
"
```

**Solutions:**

1. **Browser resource limits:**
```python
# In worker/tasks.py
browser = playwright.chromium.launch(
    headless=True,
    args=[
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-extensions',
        '--disable-gpu',
        '--memory-pressure-off',
        '--max_old_space_size=2048'
    ]
)
```

2. **Memory management:**
```bash
# Increase shared memory
# In docker-compose.prod.yml:
# worker:
#   shm_size: '2gb'
```

3. **Browser cleanup:**
```python
# Ensure proper cleanup in worker/tasks.py
try:
    # Browser automation code
    pass
finally:
    if 'context' in locals():
        context.close()
    if 'browser' in locals():
        browser.close()
```

---

## SSL and Certificate Issues

### Issue: Certificate Expired or Invalid

**Symptoms:**
- Browser SSL warnings
- "Certificate has expired" errors
- API calls failing with SSL errors

**Diagnosis:**
```bash
# Check certificate validity
openssl x509 -in /etc/letsencrypt/live/api.selextract.com/fullchain.pem -text -noout | grep -A 2 "Validity"

# Test SSL connection
openssl s_client -connect api.selextract.com:443 -servername api.selextract.com

# Check certificate auto-renewal
systemctl status certbot.timer
```

**Solutions:**

1. **Manual renewal:**
```bash
# Stop nginx
docker-compose -f docker-compose.prod.yml stop nginx

# Renew certificates
certbot renew --standalone

# Restart nginx
docker-compose -f docker-compose.prod.yml start nginx
```

2. **Fix auto-renewal:**
```bash
# Check cron jobs
crontab -l

# Add renewal cron if missing
echo "0 3 * * * certbot renew --quiet --deploy-hook 'docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml restart nginx'" | crontab -
```

3. **Certificate chain issues:**
```bash
# Verify full certificate chain
curl -I https://api.selextract.com

# Update nginx SSL configuration
# In nginx/sites-available/selextract.conf:
# ssl_certificate /etc/letsencrypt/live/api.selextract.com/fullchain.pem;
# ssl_certificate_key /etc/letsencrypt/live/api.selextract.com/privkey.pem;
```

### Issue: Mixed Content Warnings

**Symptoms:**
- Browser console errors about mixed content
- Some resources not loading over HTTPS
- Insecure connection warnings

**Solutions:**

1. **Force HTTPS redirects:**
```nginx
# In nginx/sites-available/selextract.conf
server {
    listen 80;
    server_name api.selextract.com app.selextract.com;
    return 301 https://$server_name$request_uri;
}
```

2. **Update frontend configuration:**
```javascript
// In frontend/next.config.js
module.exports = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains'
          }
        ]
      }
    ]
  }
}
```

---

## Performance Issues

### Issue: High Response Times

**Symptoms:**
- API responses > 2 seconds
- Frontend loading slowly
- Timeout errors

**Diagnosis:**
```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s https://api.selextract.com/health

# Monitor API performance
docker-compose -f docker-compose.prod.yml logs api | grep -E "(ERROR|WARN|took)"

# Check resource usage
htop
iotop
```

**Solutions:**

1. **Scale workers:**
```bash
# Increase worker count
docker-compose -f docker-compose.prod.yml up -d --scale worker=4

# Monitor improvement
watch "docker stats --no-stream"
```

2. **Database optimization:**
```bash
# Check slow queries
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 5;
"

# Add missing indexes
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "
CREATE INDEX CONCURRENTLY idx_tasks_user_id ON tasks(user_id);
CREATE INDEX CONCURRENTLY idx_tasks_status ON tasks(status);
"
```

3. **Caching optimization:**
```bash
# Check Redis performance
docker-compose -f docker-compose.prod.yml exec redis redis-cli info stats

# Increase Redis memory if needed
# In docker-compose.prod.yml:
# redis:
#   command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
```

### Issue: High Memory Usage

**Symptoms:**
- OOM (Out of Memory) kills
- Slow performance
- System becoming unresponsive

**Diagnosis:**
```bash
# Check memory usage by service
docker stats --no-stream
free -h

# Check for memory leaks
docker-compose -f docker-compose.prod.yml logs worker | grep -i "memory"

# Monitor memory over time
watch "free -h && echo '---' && docker stats --no-stream"
```

**Solutions:**

1. **Reduce service memory:**
```yaml
# In docker-compose.prod.yml
worker:
  deploy:
    resources:
      limits:
        memory: '2G'  # Reduce if too high
  environment:
    - CELERY_WORKER_CONCURRENCY=2  # Reduce concurrent tasks
```

2. **Browser memory optimization:**
```python
# In worker/tasks.py
browser = playwright.chromium.launch(
    args=['--memory-pressure-off', '--disable-dev-shm-usage']
)
```

3. **Add swap space:**
```bash
# Create swap file
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

## Authentication Issues

### Issue: Google OAuth Not Working

**Symptoms:**
- "Invalid client" errors
- OAuth redirects failing
- Users can't log in

**Diagnosis:**
```bash
# Check OAuth configuration
docker-compose -f docker-compose.prod.yml exec api python -c "
import os
print('Google Client ID:', os.getenv('GOOGLE_CLIENT_ID')[:10] + '...')
print('Google Secret set:', bool(os.getenv('GOOGLE_CLIENT_SECRET')))
"

# Check redirect URLs in Google Console
# Should match: https://app.selextract.com/auth/success
```

**Solutions:**

1. **Update OAuth settings:**
```bash
# In Google Cloud Console:
# 1. Go to APIs & Services > Credentials
# 2. Edit OAuth 2.0 Client
# 3. Add authorized redirect URIs:
#    - https://app.selextract.com/auth/success
#    - http://localhost:3000/auth/success (for development)

# Update environment variables
# GOOGLE_CLIENT_ID=your-actual-client-id
# GOOGLE_CLIENT_SECRET=your-actual-secret
```

2. **Check domain verification:**
```bash
# Verify domain ownership in Google Search Console
# Add domain: selextract.com
# Verify via DNS TXT record or HTML file
```

3. **Session configuration:**
```bash
# Ensure session secret is set
docker-compose -f docker-compose.prod.yml exec frontend env | grep NEXTAUTH_SECRET

# Generate new secret if missing
openssl rand -base64 32
```

### Issue: JWT Token Errors

**Symptoms:**
- "Invalid token" errors
- Frequent re-authentication required
- API authentication failures

**Diagnosis:**
```bash
# Check JWT configuration
docker-compose -f docker-compose.prod.yml exec api python -c "
import os
print('JWT Secret set:', bool(os.getenv('JWT_SECRET_KEY')))
print('JWT Algorithm:', os.getenv('JWT_ALGORITHM', 'HS256'))
"

# Test token generation
curl -X POST https://api.selextract.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'
```

**Solutions:**

1. **Regenerate JWT secret:**
```bash
# Generate new secret
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Update in .env.prod
JWT_SECRET_KEY=new_generated_secret

# Restart services
docker-compose -f docker-compose.prod.yml restart api frontend
```

2. **Token expiration settings:**
```python
# In api/auth.py
# Adjust token expiration time
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours instead of default
```

---

## Monitoring and Logging Issues

### Issue: Grafana Not Accessible

**Symptoms:**
- Grafana login page not loading
- "Connection refused" errors
- Monitoring dashboards unavailable

**Diagnosis:**
```bash
# Check Grafana service
docker-compose -f monitoring/docker-compose.monitoring.yml logs grafana

# Test access
curl -I http://localhost:3000
curl -I https://monitoring.selextract.com/grafana/
```

**Solutions:**

1. **Service restart:**
```bash
# Restart monitoring stack
cd monitoring
docker-compose -f docker-compose.monitoring.yml restart grafana

# Check service status
docker-compose -f docker-compose.monitoring.yml ps
```

2. **Configuration issues:**
```bash
# Check Grafana configuration
docker-compose -f monitoring/docker-compose.monitoring.yml exec grafana cat /etc/grafana/grafana.ini | grep -A 5 "\[server\]"

# Reset admin password
docker-compose -f monitoring/docker-compose.monitoring.yml exec grafana grafana-cli admin reset-admin-password newpassword
```

### Issue: Prometheus Not Collecting Metrics

**Symptoms:**
- Empty dashboards
- "No data" in Grafana
- Metrics endpoints not responding

**Diagnosis:**
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Test metrics endpoints
curl http://api:8000/metrics
curl http://localhost:8080/metrics  # Node exporter
```

**Solutions:**

1. **Update Prometheus configuration:**
```yaml
# In monitoring/prometheus.yml
# Ensure all targets are correctly configured
- job_name: 'selextract-api'
  static_configs:
    - targets: ['api:8000']
```

2. **Restart monitoring:**
```bash
cd monitoring
docker-compose -f docker-compose.monitoring.yml down
docker-compose -f docker-compose.monitoring.yml up -d
```

### Issue: Logs Not Appearing

**Symptoms:**
- Missing application logs
- Log rotation not working
- Disk space issues from logs

**Diagnosis:**
```bash
# Check log files
find /var/log -name "*selextract*" -type f -exec ls -lh {} \;

# Check Docker logs
docker-compose -f docker-compose.prod.yml logs --since 1h

# Check disk usage
df -h /var/log
```

**Solutions:**

1. **Fix log rotation:**
```bash
# Create logrotate configuration
cat > /etc/logrotate.d/selextract << 'EOF'
/var/log/selextract/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 deploy deploy
    postrotate
        docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml restart api worker frontend
    endscript
}
EOF

# Test logrotate
logrotate -d /etc/logrotate.d/selextract
```

2. **Clean up old logs:**
```bash
# Remove old logs
find /var/log -name "*.log" -mtime +30 -delete
journalctl --vacuum-time=30d

# Limit Docker log sizes
# In docker-compose.prod.yml:
# logging:
#   driver: "json-file"
#   options:
#     max-size: "10m"
#     max-file: "3"
```

---

## Network and Connectivity Issues

### Issue: External API Calls Failing

**Symptoms:**
- Webshare.io API timeouts
- Lemon Squeezy webhook failures
- External service connection errors

**Diagnosis:**
```bash
# Test external connectivity
docker-compose -f docker-compose.prod.yml exec api curl -I https://proxy.webshare.io
docker-compose -f docker-compose.prod.yml exec api curl -I https://api.lemonsqueezy.com

# Check DNS resolution
docker-compose -f docker-compose.prod.yml exec api nslookup proxy.webshare.io
```

**Solutions:**

1. **Firewall configuration:**
```bash
# Allow outbound HTTPS
ufw allow out 443
ufw allow out 80

# Check iptables for blocking rules
iptables -L OUTPUT
```

2. **DNS issues:**
```bash
# Update DNS servers
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf

# Restart Docker to pick up DNS changes
systemctl restart docker
```

3. **Proxy server blocking:**
```bash
# If behind corporate firewall, configure proxy
# In docker-compose.prod.yml:
# environment:
#   - HTTP_PROXY=http://proxy.company.com:8080
#   - HTTPS_PROXY=http://proxy.company.com:8080
```

### Issue: Internal Service Communication Failing

**Symptoms:**
- Services can't reach each other
- Database connection refused
- Redis connection errors

**Diagnosis:**
```bash
# Check Docker networks
docker network ls
docker network inspect selextract-cloud_default

# Test internal connectivity
docker-compose -f docker-compose.prod.yml exec api ping postgres
docker-compose -f docker-compose.prod.yml exec worker ping redis
```

**Solutions:**

1. **Recreate Docker network:**
```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Remove network
docker network rm selextract-cloud_default

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

2. **Service discovery issues:**
```bash
# Check service names in Docker Compose
docker-compose -f docker-compose.prod.yml config | grep -A 5 services:

# Update connection strings to use service names
# DATABASE_URL=postgresql://postgres:password@postgres:5432/selextract
# REDIS_URL=redis://:password@redis:6379/0
```

---

## Storage and Backup Issues

### Issue: Backup Script Failing

**Symptoms:**
- Backup files not created
- Permission denied errors
- Incomplete backups

**Diagnosis:**
```bash
# Test backup script
./scripts/backup.sh --dry-run

# Check backup directory permissions
ls -la /opt/backups/
df -h /opt/backups/

# Check script logs
journalctl -u backup.service
```

**Solutions:**

1. **Fix permissions:**
```bash
# Create backup directory
mkdir -p /opt/backups
chown deploy:deploy /opt/backups
chmod 755 /opt/backups

# Fix script permissions
chmod +x scripts/backup.sh
```

2. **Disk space issues:**
```bash
# Check available space
df -h

# Clean old backups
find /opt/backups -name "*.tar.gz" -mtime +7 -delete

# Compress existing backups
gzip /opt/backups/*.sql
```

3. **Database dump issues:**
```bash
# Test database dump manually
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres selextract > /tmp/test_dump.sql

# Check for errors
echo $?  # Should be 0 for success
```

### Issue: Restore Process Failing

**Symptoms:**
- Database restore errors
- Data corruption after restore
- Service startup failures after restore

**Diagnosis:**
```bash
# Check backup integrity
./scripts/restore.sh --verify /opt/backups/latest_backup

# Test restore in staging
./scripts/restore.sh --test /opt/backups/backup_file.tar.gz
```

**Solutions:**

1. **Backup validation:**
```bash
# Verify backup before restore
tar -tzf /opt/backups/backup_file.tar.gz | head -10

# Check SQL dump syntax
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres --set ON_ERROR_STOP=on -f /tmp/backup.sql
```

2. **Safe restore procedure:**
```bash
# Create current backup before restore
./scripts/backup.sh --prefix "before_restore"

# Stop services during restore
docker-compose -f docker-compose.prod.yml down

# Perform restore
./scripts/restore.sh /opt/backups/backup_file.tar.gz

# Verify restore
./scripts/health-check.sh
```

---

## Emergency Procedures

### Complete System Recovery

If the system is completely unresponsive:

```bash
# 1. Stop all services
docker-compose -f docker-compose.prod.yml down
docker system prune -f

# 2. Check system resources
free -h
df -h
top

# 3. Restart Docker daemon
systemctl restart docker

# 4. Start essential services only
docker-compose -f docker-compose.prod.yml up -d postgres redis

# 5. Verify database
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# 6. Start remaining services
docker-compose -f docker-compose.prod.yml up -d

# 7. Verify health
./scripts/health-check.sh
```

### Rollback Deployment

If a deployment breaks the system:

```bash
# 1. Stop current deployment
docker-compose -f docker-compose.prod.yml down

# 2. Restore from backup
./scripts/restore.sh /opt/backups/$(ls -t /opt/backups/ | head -1)

# 3. Checkout previous code version
git log --oneline -10
git checkout PREVIOUS_COMMIT_HASH

# 4. Deploy previous version
./scripts/deploy.sh

# 5. Verify rollback
./scripts/health-check.sh
```

### Contact Support

If you cannot resolve the issue:

1. **Gather diagnostic information:**
```bash
# Create support bundle
tar -czf selextract-support-$(date +%Y%m%d).tar.gz \
  /opt/selextract-cloud/docker-compose.prod.yml \
  /opt/selextract-cloud/.env.prod \
  /var/log/selextract/ \
  <(docker-compose -f docker-compose.prod.yml logs --since 24h) \
  <(docker stats --no-stream) \
  <(free -h) \
  <(df -h)
```

2. **Include this information:**
   - Error messages and logs
   - Steps to reproduce the issue
   - System specifications
   - Recent changes made
   - Output of diagnostic commands

3. **Create an issue** with the support bundle and detailed description.

Remember to remove sensitive information (passwords, API keys) from logs before sharing.