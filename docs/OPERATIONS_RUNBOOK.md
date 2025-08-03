# Selextract Cloud Operations Runbook

This document provides standard operating procedures for managing Selextract Cloud in production. It covers common operational tasks, troubleshooting procedures, and emergency response protocols.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Weekly Operations](#weekly-operations)
3. [Monthly Operations](#monthly-operations)
4. [Emergency Procedures](#emergency-procedures)
5. [Monitoring and Alerting](#monitoring-and-alerting)
6. [Performance Optimization](#performance-optimization)
7. [Scaling Procedures](#scaling-procedures)
8. [Troubleshooting Guide](#troubleshooting-guide)

## Daily Operations

### Morning Health Check (9:00 AM UTC)

```bash
# Run comprehensive health check
cd /opt/selextract-cloud
./scripts/health-check.sh

# Check overnight alerts
curl -s "http://localhost:9090/api/v1/alerts" | jq '.data[] | select(.state=="firing")'

# Review system metrics
./scripts/system-status.sh

# Check backup status
ls -la /opt/backups/ | tail -5
```

### Service Status Verification

```bash
# Check all service containers
docker-compose -f docker-compose.prod.yml ps

# Verify external connectivity
curl -f https://api.selextract.com/health
curl -f https://app.selextract.com
curl -f https://monitoring.selextract.com/grafana/api/health

# Check worker processing (✅ FULLY OPERATIONAL)
docker-compose -f docker-compose.prod.yml exec worker celery -A main inspect active

# Verify worker system health (NEW - CRITICAL CHECK)
docker-compose -f docker-compose.prod.yml logs worker | grep -E "(RUNNING|Database is ready|Redis is ready|supervisord started)"

# Confirm task discovery is working
docker-compose -f docker-compose.prod.yml exec worker celery -A main inspect registered | grep -c "execute_scraping_task"
```

**✅ Worker System Success Indicators:**
- `celery-worker entered RUNNING state, process has stayed up for > than 0 seconds`
- `celery-beat entered RUNNING state, process has stayed up for > than 0 seconds`
- `Database is ready!`
- `Redis is ready!`
- `supervisord started with pid 1`
- No container restarts in the last 10+ minutes

### Log Review

```bash
# Check for errors in application logs (last 24 hours)
find /var/log/selextract -name "*.log" -mtime -1 -exec grep -l "ERROR\|CRITICAL" {} \;

# Review nginx error logs
tail -50 /var/log/nginx/error.log

# Check systemd journal for system errors
journalctl --since="24 hours ago" --priority=err --no-pager

# NEW: Check worker stability (no restart loops)
docker-compose -f docker-compose.prod.yml ps worker | grep -v "Restarting"
```

### Performance Metrics Review

Daily metrics to monitor in Grafana:
- **System Load:** Should be < 80% of available cores
- **Memory Usage:** Should be < 85% of total RAM
- **Disk Usage:** Should be < 80% of total space
- **API Response Time:** 95th percentile < 2 seconds
- **Task Success Rate:** Should be > 95%
- **Database Connections:** Should be < 80% of max pool

## Weekly Operations

### Security Updates (Every Monday)

```bash
# Update system packages
sudo apt update && sudo apt list --upgradable

# Apply security updates
sudo unattended-upgrade -d

# Review fail2ban logs
sudo fail2ban-client status
sudo journalctl -u fail2ban --since="7 days ago" | grep "Ban\|Unban"

# Check SSL certificate expiry
./scripts/setup-ssl.sh --verify

# Review user access logs
sudo last | head -20
```

### Performance Review

```bash
# Generate weekly performance report
./scripts/performance-report.sh --week

# Review slow database queries
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d selextract -c "
    SELECT query, mean_time, calls 
    FROM pg_stat_statements 
    ORDER BY mean_time DESC 
    LIMIT 10;"

# Check worker efficiency
docker-compose -f docker-compose.prod.yml exec worker celery -A main inspect stats
```

### Backup Verification

```bash
# List recent backups
./scripts/backup.sh --list

# Test backup integrity
LATEST_BACKUP=$(ls -t /opt/backups/ | head -1)
./scripts/backup.sh --verify "/opt/backups/$LATEST_BACKUP"

# Verify remote backup upload (if configured)
# Check your cloud storage provider
```

### Capacity Planning

```bash
# Check disk usage trends
df -h /
du -sh /opt/selextract/results/* | sort -h | tail -10

# Review memory usage patterns
free -h
docker stats --no-stream

# Analyze task processing trends
# Review Grafana dashboards for task volume and processing times
```

## Monthly Operations

### Full System Maintenance

```bash
# Schedule maintenance window
# Update MAINTENANCE_MODE=true in .env.prod if needed

# Full system backup
./scripts/backup.sh

# Update Docker images
docker-compose -f docker-compose.prod.yml pull
./scripts/update.sh

# Database maintenance
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d selextract -c "VACUUM ANALYZE;"

# Clean up old Docker images
docker image prune -f --filter "until=720h" # 30 days

# Clean up old logs
find /var/log -name "*.log" -mtime +30 -delete
journalctl --vacuum-time=30d
```

## Backup and Restore Procedures

### Automated Backup System

The backup system creates comprehensive backups including database, configuration, and application data.

#### Backup Components

```bash
# Database backup (PostgreSQL dump)
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U postgres selextract > backup_$(date +%Y%m%d_%H%M%S).sql

# Configuration backup
tar -czf config_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  .env.prod \
  docker-compose.prod.yml \
  nginx/ \
  monitoring/

# Application state backup
tar -czf app_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  /var/log/selextract/ \
  /opt/selextract/results/ \
  /etc/letsencrypt/
```

#### Backup Schedule and Retention

```bash
# Daily backups (automated via cron)
0 2 * * * /opt/selextract-cloud/scripts/backup.sh >/dev/null 2>&1

# Backup retention policy
# Daily: Keep for 7 days
# Weekly: Keep for 4 weeks
# Monthly: Keep for 12 months

# Clean old backups automatically
find /opt/backups -name "daily_*" -mtime +7 -delete
find /opt/backups -name "weekly_*" -mtime +28 -delete
find /opt/backups -name "monthly_*" -mtime +365 -delete
```

#### Backup Verification

```bash
# Test backup integrity
./scripts/backup.sh --verify /opt/backups/latest_backup.tar.gz

# Verify database backup
gunzip -c /opt/backups/latest_backup.tar.gz | \
  docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U postgres -d test_restore --dry-run

# Check backup size and content
tar -tvf /opt/backups/latest_backup.tar.gz | head -20
du -h /opt/backups/latest_backup.tar.gz
```

### Critical Restore Procedures

#### Full System Restore

**⚠️ CRITICAL: Only perform during scheduled maintenance window**

```bash
# 1. Stop all services
docker-compose -f docker-compose.prod.yml down
systemctl stop nginx

# 2. Backup current state (if possible)
mv /opt/selextract-cloud /opt/selextract-cloud.backup.$(date +%Y%m%d_%H%M%S)

# 3. Extract backup archive
cd /opt
tar -xzf /opt/backups/restore_backup.tar.gz

# 4. Restore database
docker-compose -f docker-compose.prod.yml up -d postgres
sleep 30  # Wait for postgres to start

# Drop and recreate database
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -c "
DROP DATABASE IF EXISTS selextract;
CREATE DATABASE selextract;
"

# Restore database from backup
gunzip -c backup/database/selextract_*.sql.gz | \
  docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U postgres -d selextract

# 5. Restore configuration files
cp backup/config/.env.prod .env.prod
cp backup/config/docker-compose.prod.yml docker-compose.prod.yml
cp -r backup/config/nginx/ nginx/
cp -r backup/config/monitoring/ monitoring/

# 6. Restore SSL certificates
sudo cp -r backup/ssl/letsencrypt/ /etc/letsencrypt/

# 7. Restore application data
sudo cp -r backup/logs/ /var/log/selextract/
cp -r backup/results/ /opt/selextract/results/

# 8. Restart all services
docker-compose -f docker-compose.prod.yml up -d
systemctl start nginx

# 9. Verify restore
./scripts/health-check.sh
./scripts/validate-deployment.sh

# 10. Test critical functionality
curl -f https://api.selextract.com/health
curl -f https://app.selextract.com/
```

#### Database-Only Restore

```bash
# For database corruption or data loss scenarios

# 1. Create backup of current database (if possible)
docker-compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U postgres selextract > emergency_backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Stop API and worker services (keep database running)
docker-compose -f docker-compose.prod.yml stop api worker frontend

# 3. Restore from backup
BACKUP_FILE="/opt/backups/database_backup.sql"
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U postgres -d selextract < "$BACKUP_FILE"

# 4. Verify data integrity
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U postgres -d selextract -c "
    SELECT COUNT(*) FROM users;
    SELECT COUNT(*) FROM tasks;
    SELECT COUNT(*) FROM billing;
  "

# 5. Restart services
docker-compose -f docker-compose.prod.yml start api worker frontend

# 6. Test database connectivity
./scripts/health-check.sh --database-only
```

#### Configuration-Only Restore

```bash
# For configuration errors or corruption

# 1. Stop services
docker-compose -f docker-compose.prod.yml down

# 2. Backup current configuration
mkdir -p /tmp/config_backup_$(date +%Y%m%d_%H%M%S)
cp .env.prod /tmp/config_backup_*/
cp docker-compose.prod.yml /tmp/config_backup_*/
cp -r nginx/ /tmp/config_backup_*/

# 3. Restore configuration from backup
tar -xzf /opt/backups/config_backup.tar.gz
cp backup/config/.env.prod .env.prod
cp backup/config/docker-compose.prod.yml docker-compose.prod.yml
cp -r backup/config/nginx/ nginx/

# 4. Validate configuration
docker-compose -f docker-compose.prod.yml config
nginx -t -c nginx/nginx.conf

# 5. Restart services
docker-compose -f docker-compose.prod.yml up -d

# 6. Verify functionality
./scripts/health-check.sh
```

### Disaster Recovery Testing

#### Monthly DR Test Procedure

```bash
# 1. Schedule maintenance window (off-peak hours)
# 2. Create current backup
./scripts/backup.sh --prefix "dr_test"

# 3. Document current system state
./scripts/system-status.sh > /tmp/dr_test_initial_state.txt
docker-compose -f docker-compose.prod.yml ps >> /tmp/dr_test_initial_state.txt

# 4. Simulate disaster (controlled environment)
docker-compose -f docker-compose.prod.yml down
mv /opt/selextract-cloud /opt/selextract-cloud.dr_test_backup

# 5. Perform full restore
BACKUP_FILE="/opt/backups/dr_test_*.tar.gz"
cd /opt
tar -xzf "$BACKUP_FILE"
cd selextract-cloud

# 6. Time the recovery process
START_TIME=$(date +%s)
./scripts/restore.sh --full
END_TIME=$(date +%s)
RECOVERY_TIME=$((END_TIME - START_TIME))

# 7. Verify complete recovery
./scripts/health-check.sh --comprehensive
./scripts/validate-deployment.sh

# 8. Document results
echo "DR Test Results:" > /tmp/dr_test_results.txt
echo "Recovery Time: ${RECOVERY_TIME} seconds" >> /tmp/dr_test_results.txt
echo "Recovery Success: $(./scripts/health-check.sh && echo 'YES' || echo 'NO')" >> /tmp/dr_test_results.txt

# 9. Restore original system
rm -rf /opt/selextract-cloud
mv /opt/selextract-cloud.dr_test_backup /opt/selextract-cloud
cd /opt/selextract-cloud
docker-compose -f docker-compose.prod.yml up -d
```

### Security Audit

```bash
# Run security audit
./scripts/security-hardening.sh --audit

# Review access logs
sudo grep "Failed password" /var/log/auth.log | tail -20

# Check for unauthorized users
awk -F: '$3 >= 1000 && $7 != "/usr/sbin/nologin" {print}' /etc/passwd

# Verify firewall rules
sudo ufw status numbered

# Check for suspicious network connections
sudo netstat -tuln | grep LISTEN
```

### Performance Optimization

```bash
# Optimize database
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d selextract -c "
    REINDEX DATABASE selextract;
    ANALYZE;
  "

# Clear Redis cache if needed
docker-compose -f docker-compose.prod.yml exec redis redis-cli FLUSHDB

# Review and adjust worker scaling
# Based on task queue depth and processing times
```

## Emergency Procedures

### High Load Emergency

**Symptoms:** High CPU, memory, or response times

```bash
# Immediate assessment
./scripts/health-check.sh --critical-only
top
docker stats

# Scale workers if needed
docker-compose -f docker-compose.prod.yml up -d --scale worker=8

# Enable rate limiting
# Update nginx configuration if not already enabled

# Monitor improvement
watch -n 5 "docker stats --no-stream"
```

### Database Emergency

**Symptoms:** Database connection errors, slow queries

```bash
# Check database status
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U postgres

# Check connections
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d selextract -c "
    SELECT count(*) as active_connections, state 
    FROM pg_stat_activity 
    GROUP BY state;"

# Kill long-running queries if needed
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d selextract -c "
    SELECT pg_terminate_backend(pid) 
    FROM pg_stat_activity 
    WHERE state = 'active' 
    AND now() - query_start > interval '10 minutes';"

# Restart database if necessary (last resort)
docker-compose -f docker-compose.prod.yml restart postgres
```

### Storage Emergency

**Symptoms:** Disk space > 90% full

```bash
# Immediate space check
df -h

# Clean up old backups
find /opt/backups -type d -mtime +7 -exec rm -rf {} \;

# Clean up old results
find /opt/selextract/results -type f -mtime +30 -delete

# Clean up Docker resources
docker system prune -af --volumes

# Clean up logs
journalctl --vacuum-size=100M
find /var/log -name "*.log" -mtime +7 -delete
```

### Complete Service Outage

**Symptoms:** All services down

```bash
# Check Docker daemon
sudo systemctl status docker

# Check system resources
free -h
df -h
top

# Restart Docker if needed
sudo systemctl restart docker

# Restart all services
cd /opt/selextract-cloud
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# Monitor restart
watch "docker-compose -f docker-compose.prod.yml ps"

# If restart fails, consider rollback
./scripts/deploy.sh --rollback
```

### Security Breach Response

**Symptoms:** Suspicious activity, unauthorized access

```bash
# Immediate containment
# 1. Change all passwords
# 2. Review recent user activities
# 3. Check for unauthorized changes

# Review access logs
sudo grep "Accepted" /var/log/auth.log | tail -50
sudo grep "Failed" /var/log/auth.log | tail -50

# Check active sessions
who
w

# Review recent commands
history | tail -50

# Check for new users or changes
sudo grep "useradd\|usermod\|passwd" /var/log/auth.log

# If compromised, consider:
# 1. Isolate server (firewall rules)
# 2. Create forensic backup
# 3. Restore from clean backup
# 4. Harden security further
```

## Monitoring and Alerting

### Monitoring Infrastructure Setup

#### Prometheus Configuration

```yaml
# monitoring/prometheus.yml - Complete configuration
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'selextract-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics
    scrape_interval: 10s

  - job_name: 'selextract-frontend'
    static_configs:
      - targets: ['frontend:3000']
    metrics_path: /api/metrics

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx-exporter:9113']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'worker'
    static_configs:
      - targets: ['worker:8001']
    metrics_path: /metrics
```

#### Alert Rules Configuration

```yaml
# monitoring/alert_rules.yml - Complete alert definitions
groups:
  - name: selextract_critical
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.instance }} is down"
          description: "{{ $labels.job }} service has been down for more than 1 minute"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for 5+ minutes"

      - alert: DatabaseConnectionsHigh
        expr: postgresql_connections_active / postgresql_connections_max > 0.9
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database connections near limit"
          description: "PostgreSQL connections at {{ $value | humanizePercentage }} of maximum"

      - alert: DiskSpaceHigh
        expr: (node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes > 0.9
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Disk space critically low"
          description: "Disk usage is {{ $value | humanizePercentage }} on {{ $labels.mountpoint }}"

      - alert: MemoryUsageHigh
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.95
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Memory usage critically high"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      - alert: SSLCertificateExpiring
        expr: ssl_certificate_expiry_seconds < 7 * 24 * 3600
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "SSL certificate expiring soon"
          description: "SSL certificate expires in {{ $value | humanizeDuration }}"

  - name: selextract_warning
    rules:
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 3
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High API response time"
          description: "95th percentile response time is {{ $value }}s"

      - alert: WorkerQueueHigh
        expr: celery_queue_length > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Worker queue depth high"
          description: "Task queue has {{ $value }} pending tasks"

      - alert: TaskFailureRateHigh
        expr: rate(tasks_total{status="failed"}[15m]) / rate(tasks_total[15m]) > 0.1
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High task failure rate"
          description: "Task failure rate is {{ $value | humanizePercentage }}"

      - alert: ResourceUsageHigh
        expr: rate(cpu_usage_total[5m]) > 0.8 or (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.8
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High resource usage"
          description: "CPU or memory usage above 80% for 15+ minutes"

      - alert: BackupFailed
        expr: backup_success == 0
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Backup process failed"
          description: "Daily backup has not completed successfully"
```

#### Grafana Dashboard Setup

```bash
# Setup Grafana dashboards
cd monitoring

# Install essential dashboards
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @grafana/dashboards/selextract-overview.json

# Configure data sources
curl -X POST http://admin:admin@localhost:3000/api/datasources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Prometheus",
    "type": "prometheus",
    "url": "http://prometheus:9090",
    "access": "proxy",
    "isDefault": true
  }'

# Setup alerting channels
curl -X POST http://admin:admin@localhost:3000/api/alert-notifications \
  -H "Content-Type: application/json" \
  -d '{
    "name": "email-alerts",
    "type": "email",
    "settings": {
      "addresses": "admin@selextract.com;ops@selextract.com"
    }
  }'
```

### Critical Alerts (Immediate Response Required)

#### Service Down Alert
**Trigger:** Any core service (API, Database, Redis) not responding for 1+ minutes
**Response Time:** Immediate (< 5 minutes)

**Response Procedure:**
```bash
# 1. Verify alert accuracy
./scripts/health-check.sh --service-specific

# 2. Check service logs
docker-compose -f docker-compose.prod.yml logs [service_name] --tail=50

# 3. Attempt service restart
docker-compose -f docker-compose.prod.yml restart [service_name]

# 4. If restart fails, check resources
docker stats --no-stream
free -h
df -h

# 5. Escalate if service doesn't recover in 5 minutes
```

#### High Error Rate Alert
**Trigger:** API error rate > 5% for 5+ minutes
**Response Time:** Immediate (< 5 minutes)

**Response Procedure:**
```bash
# 1. Check error distribution
curl -s http://localhost:9090/api/v1/query?query='rate(http_requests_total{status=~"5.."}[5m]) by (endpoint)'

# 2. Review API logs for error patterns
docker-compose -f docker-compose.prod.yml logs api | grep -E "(ERROR|5[0-9][0-9])" | tail -20

# 3. Check database connectivity
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# 4. Monitor error recovery
watch "curl -s http://localhost:9090/api/v1/query?query='rate(http_requests_total{status=~\"5..\"}[1m])'"
```

#### Database Connections High Alert
**Trigger:** > 90% of max database connections used
**Response Time:** Immediate (< 5 minutes)

**Response Procedure:**
```bash
# 1. Check current connections
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "
  SELECT count(*) as active_connections, state
  FROM pg_stat_activity
  WHERE state IS NOT NULL
  GROUP BY state;
"

# 2. Identify long-running queries
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "
  SELECT pid, now() - query_start AS duration, query
  FROM pg_stat_activity
  WHERE state = 'active'
  AND query_start < now() - interval '5 minutes'
  ORDER BY duration DESC;
"

# 3. Kill problematic queries if necessary
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE state = 'active'
  AND query_start < now() - interval '10 minutes';
"

# 4. Scale API containers if needed
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

### Warning Alerts (Response Within 1 Hour)

#### High Response Time Alert
**Trigger:** API 95th percentile > 3 seconds for 10+ minutes
**Response Time:** Within 1 hour

**Response Procedure:**
```bash
# 1. Analyze slow endpoints
curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) by (endpoint)'

# 2. Check system resources
./scripts/system-status.sh

# 3. Review database performance
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d selextract -c "
  SELECT query, calls, total_time, mean_time
  FROM pg_stat_statements
  WHERE mean_time > 1000
  ORDER BY mean_time DESC
  LIMIT 10;
"

# 4. Consider horizontal scaling
docker-compose -f docker-compose.prod.yml up -d --scale api=4 --scale worker=6
```

### Detailed Alert Response Matrix

| Alert | Severity | Response Time | Escalation | Auto-remediation |
|-------|----------|---------------|------------|------------------|
| Service Down | Critical | < 5 min | L2 after 15 min | Service restart |
| High Error Rate | Critical | < 5 min | L2 after 10 min | None |
| DB Connections High | Critical | < 5 min | L2 after 15 min | Kill long queries |
| Disk Space Critical | Critical | < 10 min | L2 immediately | Log cleanup |
| Memory Critical | Critical | < 5 min | L2 after 10 min | Container restart |
| SSL Expiring | Critical | < 4 hours | L2 after 24 hours | Auto-renewal |
| High Response Time | Warning | < 1 hour | L2 after 4 hours | Scale containers |
| Queue Depth High | Warning | < 1 hour | L2 after 2 hours | Scale workers |
| Task Failure Rate | Warning | < 1 hour | L2 after 2 hours | Worker restart |
| Resource Usage High | Warning | < 1 hour | L2 after 4 hours | Resource optimization |
| Backup Failed | Warning | < 2 hours | L2 after 8 hours | Retry backup |

### Key Metrics to Monitor

#### System Health Metrics

```bash
# CPU utilization (should be < 80% average)
rate(cpu_usage_total[5m])

# Memory usage (should be < 85% of total)
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes

# Disk usage (should be < 80% of capacity)
(node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes

# Network I/O (monitor for anomalies)
rate(node_network_receive_bytes_total[5m])
rate(node_network_transmit_bytes_total[5m])

# Load average (should be < number of CPU cores)
node_load1
```

#### Application Performance Metrics

```bash
# API request rate
rate(http_requests_total[5m])

# API response time percentiles
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# Error rate by endpoint
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Task processing metrics
rate(tasks_total[5m])
celery_queue_length
rate(tasks_total{status="completed"}[5m]) / rate(tasks_total[5m])

# Database performance
postgresql_connections_active
rate(postgresql_queries_total[5m])
postgresql_slow_queries_total
```

#### Business Intelligence Metrics

```bash
# User activity
active_users_total
rate(user_registrations_total[24h])
rate(user_logins_total[1h])

# Task execution metrics
tasks_by_type_total
avg_task_duration_seconds
compute_units_consumed_total

# Billing metrics
revenue_total
active_subscriptions_total
churn_rate
```

### Monitoring Dashboard Guide

#### Main Overview Dashboard

Access: `https://monitoring.selextract.com/grafana/d/overview`

**Key Panels to Monitor:**
1. **System Health Summary** - Overall system status indicator
2. **Service Uptime** - Current status of all services
3. **API Performance** - Request rates, response times, error rates
4. **Resource Utilization** - CPU, memory, disk usage trends
5. **Task Processing** - Queue depth, completion rates, processing times
6. **Database Performance** - Connection count, query performance, locks
7. **Error Tracking** - Error rates by service and endpoint
8. **User Activity** - Active sessions, new registrations, feature usage

#### Daily Review Checklist

**Morning Review (9:00 AM UTC):**
- [ ] Check overnight alerts in Grafana
- [ ] Review error rate trends from last 24 hours
- [ ] Verify backup completion status
- [ ] Check resource utilization patterns
- [ ] Review task processing statistics
- [ ] Confirm SSL certificate status

**Evening Review (6:00 PM UTC):**
- [ ] Check peak hour performance metrics
- [ ] Review any alerts triggered during business hours
- [ ] Verify scaling decisions were effective
- [ ] Check user activity and engagement metrics
- [ ] Plan any needed maintenance for off-peak hours

### Alert Fatigue Prevention

#### Alert Tuning Guidelines

```bash
# Reduce false positives by adjusting thresholds
# Example: Adjust memory alert to account for normal variation
alert: MemoryUsageHigh
expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.90  # Increased from 0.85
for: 10m  # Increased from 5m

# Group related alerts to avoid spam
# Example: Group all database alerts with same labels
alert: DatabaseIssues
expr: postgresql_up == 0 OR postgresql_connections_active / postgresql_connections_max > 0.9
```

#### Alert Escalation Matrix

```yaml
# Level 1: Automated response (0-15 minutes)
- Auto-restart failed services
- Scale resources based on load
- Clear temporary files on disk space alerts
- Rotate logs if disk space critical

# Level 2: On-call engineer (15-60 minutes)
- Manual investigation required
- Complex troubleshooting needed
- Multiple system components affected
- Business impact assessment needed

# Level 3: Senior engineer (1-4 hours)
- Architecture-level decisions required
- Vendor escalation needed
- Major incident coordination
- Post-incident review planning

# Level 4: Emergency escalation (immediate)
- Complete system outage
- Security breach detected
- Data loss suspected
- Legal/compliance issues
```

## Performance Optimization

### Database Optimization

```bash
# Analyze query performance
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d selextract -c "
    SELECT query, calls, total_time, mean_time, rows
    FROM pg_stat_statements 
    ORDER BY mean_time DESC 
    LIMIT 20;"

# Check index usage
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d selextract -c "
    SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
    FROM pg_stat_user_indexes 
    ORDER BY idx_tup_read DESC;"

# Optimize PostgreSQL settings for your workload
# Edit postgresql.conf through Docker environment variables
```

### Worker Optimization

```bash
# Monitor worker performance
docker-compose -f docker-compose.prod.yml exec worker celery -A main inspect stats

# Check queue depth
docker-compose -f docker-compose.prod.yml exec worker celery -A main inspect reserved

# Adjust concurrency based on load
docker-compose -f docker-compose.prod.yml up -d --scale worker=N
```

### Caching Optimization

```bash
# Monitor Redis performance
docker-compose -f docker-compose.prod.yml exec redis redis-cli info memory
docker-compose -f docker-compose.prod.yml exec redis redis-cli info stats

# Analyze cache hit rates
docker-compose -f docker-compose.prod.yml exec redis redis-cli info stats | grep hits
```

## Scaling Procedures

### Horizontal Scaling (More Workers)

```bash
# Scale up workers during high load
docker-compose -f docker-compose.prod.yml up -d --scale worker=8

# Scale down workers during low load
docker-compose -f docker-compose.prod.yml up -d --scale worker=2

# Monitor scaling effectiveness
watch "docker-compose -f docker-compose.prod.yml exec worker celery -A main inspect active"
```

### Vertical Scaling (More Resources)

When you need to upgrade server resources:

1. **Plan Maintenance Window:** Schedule during low-traffic period
2. **Create Full Backup:** `./scripts/backup.sh`
3. **Document Current State:** Note all configurations and customizations
4. **Resize Server:** Through hosting provider control panel
5. **Verify Resource Changes:** Check `free -h`, `nproc`, `df -h`
6. **Update Resource Limits:** Modify `docker-compose.prod.yml` if needed
7. **Restart Services:** `docker-compose -f docker-compose.prod.yml restart`
8. **Verify Performance:** Monitor metrics for improvement

### Database Scaling

For database performance issues:

```bash
# Increase connection pool size
# Edit DATABASE_URL and restart API containers

# Optimize PostgreSQL memory settings
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -c "
    ALTER SYSTEM SET shared_buffers = '25% of RAM';
    ALTER SYSTEM SET effective_cache_size = '75% of RAM';
    SELECT pg_reload_conf();"

# Consider read replicas for future scaling
# This would require architecture changes
```

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: API Returning 500 Errors

**Diagnosis:**
```bash
docker-compose -f docker-compose.prod.yml logs api | tail -50
```

**Common Causes:**
- Database connection issues
- Missing environment variables
- Memory exhaustion
- Unhandled exceptions

**Solutions:**
1. Check database connectivity
2. Verify environment configuration
3. Restart API service
4. Scale up resources if needed

#### Issue: Workers Not Processing Tasks ✅ RESOLVED

**Diagnosis:**
```bash
docker-compose -f docker-compose.prod.yml logs worker
docker-compose -f docker-compose.prod.yml exec redis redis-cli llen celery
docker-compose -f docker-compose.prod.yml ps worker  # Check for restart loops
```

**Common Causes:**
- Redis connection issues
- Worker container crashed (✅ FIXED)
- Task serialization problems
- Memory issues
- **Missing `/app/tmp` directory** (✅ FIXED)
- **Incorrect module imports** (✅ FIXED)
- **Celery autodiscovery misconfiguration** (✅ FIXED)

**✅ Root Cause Resolution Applied:**
1. **Fixed Dockerfile** - Added required directories:
   ```dockerfile
   RUN mkdir -p /app/tmp /app/logs /app/results
   ```

2. **Fixed Import Statements** - Corrected relative imports in `worker/tasks.py`:
   ```python
   # Changed from: from .task_schemas import TaskConfig
   # To: from task_schemas import TaskConfig
   ```

3. **Fixed Celery Autodiscovery** - Updated `worker/main.py`:
   ```python
   # Changed from: app.autodiscover_tasks(['worker.tasks'])
   # To: app.autodiscover_tasks(['tasks'])
   ```

**Solutions:**
1. Restart Redis service
2. Restart worker services
3. Clear stuck tasks from queue
4. Check worker resource usage
5. **NEW: Verify no restart loops** - `docker-compose ps worker` should show stable containers
6. **NEW: Verify supervisord status** - Look for "supervisord started with pid 1" in logs

#### Issue: High Database Load

**Diagnosis:**
```bash
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d selextract -c "
    SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
    FROM pg_stat_activity 
    WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';"
```

**Solutions:**
1. Kill long-running queries
2. Add database indexes
3. Optimize query patterns
4. Increase database resources

#### Issue: SSL Certificate Problems

**Diagnosis:**
```bash
./scripts/setup-ssl.sh --verify
openssl x509 -in /etc/nginx/ssl/selextract.com/fullchain.pem -text -noout
```

**Solutions:**
1. Renew certificates: `./scripts/setup-ssl.sh --renew`
2. Check DNS configuration
3. Verify nginx configuration
4. Restart nginx service

### Emergency Contacts

**Primary On-Call:** [Your contact information]
**Secondary On-Call:** [Backup contact]
**Hosting Provider Support:** [Provider support details]
**Domain Registrar Support:** [Registrar support details]

### Escalation Procedures

1. **Level 1 (0-30 minutes):** Follow standard procedures in this runbook
2. **Level 2 (30-60 minutes):** Escalate to secondary on-call
3. **Level 3 (60+ minutes):** Contact external support (hosting, vendors)
4. **Level 4 (Critical):** Consider emergency rollback or failover

---

Remember to keep this runbook updated as procedures change and new issues are discovered. Document any new solutions in the appropriate sections for future reference.