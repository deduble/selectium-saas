# Selextract Cloud Maintenance Guide

This guide outlines regular maintenance procedures to ensure optimal performance, security, and reliability of your Selextract Cloud deployment.

## Table of Contents

- [Maintenance Schedule Overview](#maintenance-schedule-overview)
- [Daily Maintenance Tasks](#daily-maintenance-tasks)
- [Weekly Maintenance Tasks](#weekly-maintenance-tasks)
- [Monthly Maintenance Tasks](#monthly-maintenance-tasks)
- [Quarterly Maintenance Tasks](#quarterly-maintenance-tasks)
- [Emergency Maintenance](#emergency-maintenance)
- [Automated Maintenance Scripts](#automated-maintenance-scripts)
- [Maintenance Checklists](#maintenance-checklists)
- [Performance Optimization](#performance-optimization)
- [Capacity Planning](#capacity-planning)

---

## Maintenance Schedule Overview

| Frequency | Duration | Window | Critical Tasks |
|-----------|----------|---------|----------------|
| **Daily** | 15-30 min | Any time | Health checks, log review, backup verification |
| **Weekly** | 1-2 hours | Off-peak | Security updates, performance review, certificate check |
| **Monthly** | 2-4 hours | Planned downtime | Database maintenance, system updates, capacity review |
| **Quarterly** | 4-8 hours | Planned downtime | Major updates, disaster recovery test, security audit |

---

## Daily Maintenance Tasks

### System Health Verification (5 minutes)

```bash
#!/bin/bash
# Daily health check routine

echo "=== Daily Health Check $(date) ==="

# 1. Basic service status
echo "Checking service status..."
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml ps

# 2. Quick health endpoint test
echo "Testing health endpoints..."
curl -sf https://api.selextract.com/health || echo "⚠️ API health check failed"
curl -sf https://app.selextract.com/api/health || echo "⚠️ Frontend health check failed"

# 3. Database connectivity
echo "Testing database connectivity..."
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres pg_isready -U postgres

# 4. Redis connectivity
echo "Testing Redis connectivity..."
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T redis redis-cli ping

# 5. Worker status
echo "Checking worker status..."
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T worker celery -A worker.celery_config inspect ping

# 6. SSL certificate validity (remaining days)
echo "Checking SSL certificate validity..."
echo | openssl s_client -connect api.selextract.com:443 -servername api.selextract.com 2>/dev/null | \
  openssl x509 -noout -dates | grep notAfter | cut -d= -f2

echo "Health check completed at $(date)"
```

### Log Review (10 minutes)

```bash
#!/bin/bash
# Daily log review

echo "=== Daily Log Review $(date) ==="

LOG_DIR="/var/log/selextract"
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

# 1. Check for critical errors
echo "Checking for critical errors..."
find $LOG_DIR -name "*.log" -mtime -1 -exec grep -l "CRITICAL\|FATAL" {} \; | while read file; do
    echo "Critical errors in $file:"
    grep "CRITICAL\|FATAL" "$file"
done

# 2. Check for authentication failures
echo "Checking for authentication failures..."
grep -h "authentication failed\|invalid token\|unauthorized" $LOG_DIR/*.log | wc -l

# 3. Check for task failures
echo "Checking task failure rate..."
TOTAL_TASKS=$(docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -t -c "SELECT COUNT(*) FROM tasks WHERE created_at >= CURRENT_DATE;")
FAILED_TASKS=$(docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -t -c "SELECT COUNT(*) FROM tasks WHERE status = 'FAILED' AND created_at >= CURRENT_DATE;")
echo "Task failure rate: $FAILED_TASKS/$TOTAL_TASKS"

# 4. Check disk space
echo "Checking disk space..."
df -h | grep -E "(^/dev|Use%)"

# 5. Check memory usage
echo "Checking memory usage..."
free -h

echo "Log review completed at $(date)"
```

### Backup Verification (5 minutes)

```bash
#!/bin/bash
# Verify last night's backup

echo "=== Backup Verification $(date) ==="

BACKUP_DIR="/opt/backups"
LATEST_BACKUP=$(ls -t $BACKUP_DIR/*.tar.gz | head -1)

if [[ -n "$LATEST_BACKUP" ]]; then
    echo "Latest backup: $LATEST_BACKUP"
    echo "Backup size: $(du -h "$LATEST_BACKUP" | cut -f1)"
    echo "Backup age: $(stat -c %y "$LATEST_BACKUP")"
    
    # Quick integrity check
    if tar -tzf "$LATEST_BACKUP" >/dev/null 2>&1; then
        echo "✓ Backup integrity check passed"
    else
        echo "⚠️ Backup integrity check failed"
    fi
else
    echo "⚠️ No recent backup found"
fi

echo "Backup verification completed at $(date)"
```

### Daily Monitoring Dashboard Review (10 minutes)

Access Grafana dashboard and review:

1. **System Overview Dashboard:**
   - CPU usage trends
   - Memory utilization
   - Disk I/O patterns
   - Network traffic

2. **Application Metrics:**
   - API response times
   - Task completion rates
   - Error rates
   - Active user sessions

3. **Infrastructure Health:**
   - Database performance
   - Redis hit rates
   - Worker queue depths
   - Proxy success rates

**Alert Thresholds to Monitor:**
- CPU usage > 80% for 15+ minutes
- Memory usage > 90%
- Disk usage > 85%
- API response time > 2 seconds
- Task failure rate > 5%

---

## Weekly Maintenance Tasks

### Security Updates (30 minutes)

```bash
#!/bin/bash
# Weekly security updates

echo "=== Weekly Security Updates $(date) ==="

# 1. Update package lists
apt update

# 2. Check for security updates
echo "Available security updates:"
apt list --upgradable | grep -i security

# 3. Apply security updates (automatic)
unattended-upgrade -d

# 4. Check for Docker updates
echo "Current Docker version:"
docker --version
echo "Latest Docker version available:"
curl -s https://api.github.com/repos/docker/docker-ce/releases/latest | grep -o '"tag_name": "[^"]*' | cut -d'"' -f4

# 5. Update Docker Compose if needed
CURRENT_COMPOSE=$(docker-compose --version | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+')
LATEST_COMPOSE=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -o '"tag_name": "[^"]*' | cut -d'"' -f4 | sed 's/v//')

if [[ "$CURRENT_COMPOSE" != "$LATEST_COMPOSE" ]]; then
    echo "Docker Compose update available: $CURRENT_COMPOSE -> $LATEST_COMPOSE"
fi

# 6. Check fail2ban status
systemctl status fail2ban
fail2ban-client status

echo "Security updates completed at $(date)"
```

### Performance Review (45 minutes)

```bash
#!/bin/bash
# Weekly performance analysis

echo "=== Weekly Performance Review $(date) ==="

# 1. Database performance analysis
echo "Database performance metrics:"
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -c "
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
"

# 2. Check database size growth
echo "Database size trends:"
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# 3. Redis performance metrics
echo "Redis performance:"
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T redis redis-cli info stats | grep -E "(hits|misses|evicted_keys)"

# 4. Task processing statistics
echo "Task processing stats (last 7 days):"
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -c "
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_tasks,
    COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed,
    COUNT(*) FILTER (WHERE status = 'FAILED') as failed,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_duration_seconds
FROM tasks 
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date;
"

# 5. Worker efficiency analysis
echo "Worker performance:"
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T worker celery -A worker.celery_config inspect stats | grep -E "(pool|rusage)"

echo "Performance review completed at $(date)"
```

### SSL Certificate Management (15 minutes)

```bash
#!/bin/bash
# Weekly SSL certificate check

echo "=== SSL Certificate Management $(date) ==="

# 1. Check certificate expiration
for domain in api.selextract.com app.selextract.com monitoring.selextract.com; do
    echo "Checking $domain:"
    echo | openssl s_client -connect $domain:443 -servername $domain 2>/dev/null | \
    openssl x509 -noout -dates -subject
    echo
done

# 2. Test certificate auto-renewal
echo "Testing certificate auto-renewal:"
certbot renew --dry-run

# 3. Check auto-renewal timer
echo "Auto-renewal timer status:"
systemctl status certbot.timer

# 4. Verify certificate chain
echo "Verifying certificate chain:"
curl -I https://api.selextract.com 2>&1 | grep -i "SSL\|TLS"

echo "SSL certificate management completed at $(date)"
```

### Log Rotation and Cleanup (20 minutes)

```bash
#!/bin/bash
# Weekly log management

echo "=== Log Management $(date) ==="

# 1. Check log file sizes
echo "Current log sizes:"
find /var/log -name "*.log" -type f -exec du -h {} \; | sort -hr | head -20

# 2. Force log rotation for large files
echo "Rotating large log files:"
logrotate -f /etc/logrotate.d/selextract

# 3. Clean old Docker logs
echo "Cleaning old Docker logs:"
docker system prune -f --filter "until=168h"  # 7 days

# 4. Clean application logs older than 30 days
echo "Cleaning old application logs:"
find /var/log/selextract -name "*.log" -mtime +30 -delete

# 5. Clean journal logs
echo "Cleaning systemd journal:"
journalctl --vacuum-time=30d

# 6. Check remaining disk space
echo "Remaining disk space:"
df -h /var/log /opt

echo "Log management completed at $(date)"
```

---

## Monthly Maintenance Tasks

### Database Maintenance (60 minutes)

```bash
#!/bin/bash
# Monthly database maintenance

echo "=== Monthly Database Maintenance $(date) ==="

# 1. Full database backup before maintenance
echo "Creating maintenance backup..."
/opt/selextract-cloud/scripts/backup.sh --prefix "monthly_maintenance"

# 2. Database statistics update
echo "Updating database statistics..."
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -c "ANALYZE;"

# 3. Vacuum database
echo "Running database vacuum..."
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -c "VACUUM VERBOSE;"

# 4. Reindex database
echo "Reindexing database..."
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -c "REINDEX DATABASE selextract;"

# 5. Check for database bloat
echo "Checking for table bloat:"
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# 6. Update table statistics
echo "Updating PostgreSQL configuration if needed..."
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -c "
SELECT name, setting, unit FROM pg_settings WHERE name IN (
    'shared_buffers',
    'effective_cache_size',
    'maintenance_work_mem',
    'checkpoint_completion_target',
    'wal_buffers',
    'default_statistics_target'
);
"

echo "Database maintenance completed at $(date)"
```

### System Updates and Patching (90 minutes)

```bash
#!/bin/bash
# Monthly system updates

echo "=== Monthly System Updates $(date) ==="

# 1. Create full system backup
echo "Creating pre-update backup..."
/opt/selextract-cloud/scripts/backup.sh --prefix "pre_system_update"

# 2. Update all packages
echo "Updating system packages..."
apt update && apt upgrade -y

# 3. Clean package cache
echo "Cleaning package cache..."
apt autoremove -y
apt autoclean

# 4. Update Docker and Docker Compose
echo "Checking Docker updates..."
# Note: Manual verification recommended for Docker updates

# 5. Update application dependencies
echo "Updating application dependencies..."
cd /opt/selextract-cloud

# Update Python dependencies
docker-compose -f docker-compose.prod.yml build --no-cache api worker

# Update Node.js dependencies
docker-compose -f docker-compose.prod.yml build --no-cache frontend

# 6. Restart services with updated components
echo "Restarting services..."
docker-compose -f docker-compose.prod.yml restart

# 7. Verify system after updates
echo "Verifying system health..."
sleep 30
/opt/selextract-cloud/scripts/health-check.sh

echo "System updates completed at $(date)"
```

### Capacity Planning Review (45 minutes)

```bash
#!/bin/bash
# Monthly capacity analysis

echo "=== Monthly Capacity Planning $(date) ==="

# 1. Storage growth analysis
echo "Storage usage trends:"
du -sh /opt/selextract-cloud /opt/backups /var/log/selextract
df -h

# 2. Database growth analysis
echo "Database growth analysis:"
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -c "
SELECT 
    DATE_TRUNC('month', created_at) as month,
    COUNT(*) as new_tasks,
    pg_size_pretty(SUM(LENGTH(config::text) + LENGTH(COALESCE(result, '')::text))) as data_size
FROM tasks 
WHERE created_at >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month;
"

# 3. User growth analysis
echo "User growth analysis:"
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -c "
SELECT 
    DATE_TRUNC('month', created_at) as month,
    COUNT(*) as new_users
FROM users 
WHERE created_at >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month;
"

# 4. Resource utilization patterns
echo "Resource utilization summary:"
# Requires monitoring data - implement based on your Prometheus/Grafana setup

# 5. Generate capacity recommendations
echo "Capacity recommendations:"
CURRENT_TASKS_PER_DAY=$(docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -t -c "SELECT COUNT(*) FROM tasks WHERE created_at >= CURRENT_DATE - INTERVAL '30 days';")
PROJECTED_GROWTH_RATE=1.2  # 20% monthly growth

echo "Current tasks per month: $CURRENT_TASKS_PER_DAY"
echo "Projected growth rate: 20% monthly"
echo "Recommended actions based on current usage..."

echo "Capacity planning completed at $(date)"
```

### Security Audit (60 minutes)

```bash
#!/bin/bash
# Monthly security audit

echo "=== Monthly Security Audit $(date) ==="

# 1. Check for security vulnerabilities
echo "Scanning for security vulnerabilities..."
apt list --upgradable | grep -i security

# 2. Review authentication logs
echo "Reviewing authentication attempts:"
grep -h "authentication" /var/log/selextract/*.log | tail -20

# 3. Check fail2ban status
echo "Fail2ban statistics:"
fail2ban-client status
for jail in $(fail2ban-client status | grep "Jail list" | cut -d: -f2 | tr ',' '\n' | tr -d ' '); do
    echo "Jail: $jail"
    fail2ban-client status $jail
done

# 4. SSL/TLS configuration check
echo "SSL/TLS configuration review:"
for domain in api.selextract.com app.selextract.com; do
    echo "Testing $domain:"
    echo | openssl s_client -connect $domain:443 -servername $domain 2>/dev/null | \
    openssl x509 -noout -text | grep -A 5 "Signature Algorithm"
done

# 5. Check file permissions
echo "Checking critical file permissions:"
ls -la /opt/selextract-cloud/.env.prod*
ls -la /etc/letsencrypt/live/*/
ls -la /opt/backups/

# 6. Review Docker security
echo "Docker security review:"
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml config | grep -E "(privileged|cap_add|security_opt)"

# 7. Network security check
echo "Network security check:"
netstat -tlnp | grep -E ":(80|443|22|5432|6379|3000|9090)"

echo "Security audit completed at $(date)"
```

---

## Quarterly Maintenance Tasks

### Disaster Recovery Test (4 hours)

```bash
#!/bin/bash
# Quarterly disaster recovery test

echo "=== Quarterly Disaster Recovery Test $(date) ==="

# 1. Create test backup
echo "Creating test backup..."
/opt/selextract-cloud/scripts/backup.sh --prefix "dr_test"

# 2. Document current state
echo "Documenting current system state..."
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml ps > /tmp/dr_test_initial_state.txt
docker stats --no-stream >> /tmp/dr_test_initial_state.txt

# 3. Simulate failure and recovery
echo "Simulating system failure..."
# Note: Perform in maintenance window
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml down

# 4. Test restore procedure
echo "Testing restore procedure..."
LATEST_BACKUP=$(ls -t /opt/backups/dr_test_*.tar.gz | head -1)
/opt/selextract-cloud/scripts/restore.sh "$LATEST_BACKUP"

# 5. Verify recovery
echo "Verifying system recovery..."
sleep 60
/opt/selextract-cloud/scripts/health-check.sh

# 6. Document recovery time
echo "Recovery completed at $(date)"
echo "DR test results: Success/Failure and recovery time should be documented"

echo "Disaster recovery test completed at $(date)"
```

### Performance Optimization Review (3 hours)

```bash
#!/bin/bash
# Quarterly performance optimization

echo "=== Quarterly Performance Optimization $(date) ==="

# 1. Comprehensive performance analysis
echo "Running performance benchmarks..."
/opt/selextract-cloud/scripts/performance/benchmark.sh

# 2. Database performance tuning
echo "Analyzing database performance..."
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -c "
SELECT query, calls, total_time, mean_time, rows, 100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 20;
"

# 3. Index optimization
echo "Checking index usage..."
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -c "
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY n_distinct DESC;
"

# 4. Resource utilization analysis
echo "Analyzing resource utilization patterns..."
# This should integrate with your monitoring system

# 5. Optimization recommendations
echo "Generating optimization recommendations..."
# Based on analysis results

echo "Performance optimization review completed at $(date)"
```

---

## Automated Maintenance Scripts

### Setup Cron Jobs

Add these to the system crontab (`crontab -e`):

```bash
# Daily maintenance at 2 AM
0 2 * * * /opt/selextract-cloud/scripts/backup.sh >/dev/null 2>&1
30 2 * * * /opt/selextract-cloud/maintenance/daily-health-check.sh

# Weekly maintenance on Sunday at 3 AM
0 3 * * 0 /opt/selextract-cloud/maintenance/weekly-maintenance.sh

# Monthly maintenance on first Sunday at 4 AM
0 4 1 * * /opt/selextract-cloud/maintenance/monthly-maintenance.sh

# Certificate renewal check daily
0 5 * * * certbot renew --quiet --deploy-hook 'docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml restart nginx'
```

### Maintenance Script Template

```bash
#!/bin/bash
# maintenance-template.sh - Template for maintenance scripts

set -euo pipefail

# Configuration
SCRIPT_NAME="$(basename "$0")"
LOG_FILE="/var/log/selextract/maintenance-${SCRIPT_NAME%.sh}-$(date +%Y%m%d).log"
LOCK_FILE="/tmp/${SCRIPT_NAME%.sh}.lock"
EMAIL_ALERT="admin@selextract.com"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    mail -s "Maintenance Error: $SCRIPT_NAME" "$EMAIL_ALERT" < "$LOG_FILE"
    exit 1
}

# Lock mechanism
exec 200>"$LOCK_FILE"
flock -n 200 || error_exit "Script already running"

# Cleanup on exit
cleanup() {
    rm -f "$LOCK_FILE"
    log "Maintenance script completed"
}
trap cleanup EXIT

# Main maintenance logic
main() {
    log "Starting maintenance: $SCRIPT_NAME"
    
    # Your maintenance tasks here
    
    log "Maintenance completed successfully"
}

# Execute main function
main "$@"
```

---

## Maintenance Checklists

### Pre-Maintenance Checklist

- [ ] Announce maintenance window to users
- [ ] Create full system backup
- [ ] Verify backup integrity
- [ ] Check system resource availability
- [ ] Ensure maintenance scripts are tested
- [ ] Prepare rollback procedures
- [ ] Notify monitoring systems (if applicable)

### During Maintenance Checklist

- [ ] Follow maintenance scripts step by step
- [ ] Monitor system resources continuously
- [ ] Document any issues encountered
- [ ] Take screenshots of important metrics
- [ ] Verify each step before proceeding
- [ ] Keep stakeholders informed of progress

### Post-Maintenance Checklist

- [ ] Run comprehensive health checks
- [ ] Verify all services are running
- [ ] Test critical user workflows
- [ ] Check monitoring dashboards
- [ ] Review maintenance logs
- [ ] Update documentation if needed
- [ ] Notify users of completed maintenance
- [ ] Schedule next maintenance activities

---

## Performance Optimization

### Database Performance Tuning

```sql
-- Monthly database optimization queries

-- 1. Identify slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
WHERE mean_time > 1000  -- queries taking more than 1 second
ORDER BY mean_time DESC
LIMIT 10;

-- 2. Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan < 100  -- potentially unused indexes
ORDER BY idx_scan;

-- 3. Check table sizes and bloat
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
       pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Redis Performance Optimization

```bash
# Redis optimization checks
docker-compose -f docker-compose.prod.yml exec redis redis-cli info memory
docker-compose -f docker-compose.prod.yml exec redis redis-cli info stats
docker-compose -f docker-compose.prod.yml exec redis redis-cli config get maxmemory*
```

### Application Performance Monitoring

```python
# Performance monitoring script for API
import requests
import time
import json

def monitor_api_performance():
    """Monitor API response times and log performance metrics."""
    endpoints = [
        '/health',
        '/api/v1/tasks',
        '/api/v1/users/me'
    ]
    
    results = {}
    
    for endpoint in endpoints:
        start_time = time.time()
        try:
            response = requests.get(f"https://api.selextract.com{endpoint}")
            response_time = time.time() - start_time
            results[endpoint] = {
                'status_code': response.status_code,
                'response_time': response_time,
                'success': response.status_code == 200
            }
        except Exception as e:
            results[endpoint] = {
                'error': str(e),
                'response_time': time.time() - start_time,
                'success': False
            }
    
    return results
```

---

## Capacity Planning

### Monthly Capacity Assessment

```bash
#!/bin/bash
# Monthly capacity assessment script

echo "=== Capacity Assessment $(date) ==="

# 1. Current resource utilization
echo "Current CPU utilization:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1

echo "Current memory utilization:"
free | grep Mem | awk '{printf "%.2f%%\n", $3/$2 * 100.0}'

echo "Current disk utilization:"
df -h / | awk 'NR==2{printf "%s\n", $5}'

# 2. Database growth
echo "Database size growth:"
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -c "
SELECT pg_size_pretty(pg_database_size('selextract'));
"

# 3. Task volume trends
echo "Task volume trends (last 30 days):"
docker-compose -f /opt/selextract-cloud/docker-compose.prod.yml exec -T postgres psql -U postgres -d selextract -c "
SELECT DATE(created_at) as date, COUNT(*) as tasks
FROM tasks 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC
LIMIT 7;
"

# 4. Generate scaling recommendations
CURRENT_CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 | cut -d'.' -f1)
if [ "$CURRENT_CPU" -gt 80 ]; then
    echo "⚠️ Recommendation: Consider CPU scaling"
fi

CURRENT_MEM=$(free | grep Mem | awk '{printf "%.0f\n", $3/$2 * 100.0}')
if [ "$CURRENT_MEM" -gt 85 ]; then
    echo "⚠️ Recommendation: Consider memory scaling"
fi

echo "Capacity assessment completed at $(date)"
```

### Scaling Decision Matrix

| Metric | Current | Warning | Critical | Action Required |
|--------|---------|---------|----------|-----------------|
| CPU Usage | <70% | 70-85% | >85% | Scale up/out |
| Memory Usage | <80% | 80-90% | >90% | Add memory/scale out |
| Disk Usage | <75% | 75-85% | >85% | Add storage/cleanup |
| Queue Depth | <50 | 50-100 | >100 | Add workers |
| Response Time | <1s | 1-2s | >2s | Optimize/scale |
| Error Rate | <1% | 1-5% | >5% | Investigate/fix |

---

This maintenance guide provides a comprehensive framework for keeping your Selextract Cloud deployment running optimally. Adapt the schedules and procedures based on your specific usage patterns and requirements.

**Remember:**
- Always backup before maintenance
- Test procedures in staging first
- Monitor system health during and after maintenance
- Document any issues and resolutions
- Keep maintenance logs for audit and improvement purposes