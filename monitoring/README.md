# Selextract Cloud Monitoring Stack

Complete production-ready monitoring, metrics, and alerting system for Selextract Cloud using Prometheus, Grafana, and Alertmanager.

## 🏗️ Architecture Overview

The monitoring stack consists of:

- **Prometheus**: Metrics collection and time-series database
- **Grafana**: Data visualization and dashboarding  
- **Alertmanager**: Alert routing and notification management
- **Node Exporter**: System-level metrics (CPU, memory, disk, network)
- **PostgreSQL Exporter**: Database performance metrics
- **Redis Exporter**: Cache performance metrics  
- **Nginx Exporter**: Web server metrics
- **Celery Exporter**: Task queue metrics
- **Custom API Metrics**: Application-specific business metrics

## 📊 Metrics Collected

### System Metrics
- CPU usage and load averages
- Memory utilization
- Disk space and I/O performance
- Network traffic and errors
- File system usage and inodes

### Application Metrics
- HTTP request rates, latency, and error rates
- API endpoint performance
- Database connection pools and query performance
- Redis cache hit ratios and memory usage
- Celery task queue lengths and worker status

### Business Metrics
- User registrations and activity
- Compute unit consumption
- Task creation and completion rates
- Proxy usage and failure rates
- Security events (failed logins, rate limits)

## 🚀 Quick Start

### 1. Environment Setup

Copy and configure environment variables:

```bash
cp .env.example .env
# Edit .env with your specific values
```

Required environment variables:
```bash
# Monitoring
GRAFANA_ADMIN_PASSWORD=supersecretpassword
ADMIN_EMAIL=admin@selextract.com
SMTP_PASSWORD=your_smtp_password
ALERTMANAGER_WEBHOOK_PASSWORD=supersecretwebhookpassword

# Optional: Slack integration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

### 2. Deploy Monitoring Stack

```bash
# Start the complete monitoring stack
cd monitoring
docker-compose -f docker-compose.monitoring.yml up -d

# Verify all services are running
docker-compose -f docker-compose.monitoring.yml ps
```

### 3. Access Services

- **Grafana**: http://localhost:3000 (admin/password from env)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **API Metrics**: http://localhost:8000/metrics

## 📈 Dashboards

### Selextract Overview Dashboard

The main dashboard provides:

- **System Health**: CPU, memory, disk usage
- **Application Performance**: API response times, error rates
- **Task Management**: Queue lengths, worker status, task completion rates
- **Business Metrics**: User activity, compute unit consumption
- **Infrastructure**: Database and Redis performance

Access: Grafana → Dashboards → Selextract Cloud Overview

### Key Visualizations

1. **CPU Usage**: Real-time CPU utilization across all cores
2. **Memory Usage**: RAM consumption with thresholds
3. **API Response Time**: 50th and 95th percentile latencies
4. **API Error Rate**: HTTP 4xx/5xx error percentages
5. **Celery Queue Length**: Pending tasks in queue
6. **Active Workers**: Number of healthy Celery workers
7. **Database Connections**: PostgreSQL connection pool usage
8. **Redis Memory**: Cache memory utilization
9. **User Registrations**: New user signup rates
10. **Compute Unit Consumption**: Business metric tracking
11. **Security Events**: Failed login attempts and rate limits
12. **Proxy Performance**: Success/failure rates

## 🚨 Alerting

### Alert Categories

**Critical Alerts** (Immediate action required):
- Service downtime (API, database, Redis)
- High error rates (>5%)
- Resource exhaustion (>90% memory/disk)

**Warning Alerts** (Investigation needed):
- High resource usage (>80%)
- Elevated error rates (>1%)
- Task queue backlog
- Slow query performance

**Info Alerts** (Informational):
- Low compute units remaining
- Business threshold breaches

### Alert Routing

Alerts are routed based on severity:

- **Critical**: Email + Slack + Webhook (5min repeat)
- **Warning**: Email + Webhook (30min repeat)  
- **Info**: Webhook only (12hr repeat)

### Notification Channels

1. **Email**: Configured via SMTP for admin notifications
2. **Slack**: Optional integration for team alerts
3. **Webhook**: API integration for custom handling

## 🔧 Configuration

### Prometheus Configuration

Located at [`prometheus.yml`](./prometheus.yml):

- **Scrape Interval**: 15 seconds default
- **Evaluation Interval**: 15 seconds for alerts
- **Retention**: 30 days of metrics data
- **Targets**: All application and infrastructure components

### Alert Rules

Defined in [`alert_rules.yml`](./alert_rules.yml):

- System resource thresholds
- Application performance SLAs
- Business logic alerts
- Security event detection

### Grafana Provisioning

Automatic setup via:
- Data sources: [`grafana/datasources/prometheus.yml`](./grafana/datasources/prometheus.yml)
- Dashboards: [`grafana/dashboards/`](./grafana/dashboards/)

## 📱 Dashboard Panels

### System Overview Row
- CPU Usage (timeseries)
- Memory Usage (timeseries)
- Disk Usage (gauge)
- Network Traffic (timeseries)

### Application Performance Row  
- API Response Time (timeseries)
- API Error Rate (timeseries)
- Request Volume (stat)
- Active Connections (gauge)

### Task Management Row
- Celery Queue Length (gauge)
- Active Workers (gauge)
- Task Completion Rate (stat)
- Task Duration (histogram)

### Business Metrics Row
- User Registrations (timeseries)
- Compute Unit Usage (timeseries)
- Revenue Metrics (stat)
- Active Users (gauge)

### Infrastructure Row
- Database Connections (gauge)
- Redis Memory Usage (gauge)
- Proxy Success Rate (timeseries)
- Security Events (timeseries)

## 🔍 Troubleshooting

### Common Issues

**Prometheus not scraping metrics:**
```bash
# Check target health
curl http://localhost:9090/api/v1/targets

# Verify service endpoints
curl http://api:8000/metrics
curl http://node-exporter:9100/metrics
```

**Grafana dashboard not loading:**
```bash
# Check data source connectivity
docker-compose -f docker-compose.monitoring.yml logs grafana

# Verify Prometheus data source
curl http://localhost:3000/api/datasources
```

**Alerts not firing:**
```bash
# Check alert rules evaluation
curl http://localhost:9090/api/v1/rules

# Check alertmanager configuration  
curl http://localhost:9093/api/v1/status
```

**Missing metrics:**
```bash
# Check exporter logs
docker-compose -f docker-compose.monitoring.yml logs postgres-exporter
docker-compose -f docker-compose.monitoring.yml logs redis-exporter

# Verify metric endpoints
curl http://postgres-exporter:9187/metrics
curl http://redis-exporter:9121/metrics
```

### Log Analysis

View service logs:
```bash
# All monitoring services
docker-compose -f docker-compose.monitoring.yml logs

# Specific service
docker-compose -f docker-compose.monitoring.yml logs prometheus
docker-compose -f docker-compose.monitoring.yml logs grafana
docker-compose -f docker-compose.monitoring.yml logs alertmanager
```

## 🧪 Testing Alerts

Test alert conditions:

```bash
# Trigger high CPU alert (run in container)
stress --cpu 4 --timeout 300s

# Trigger memory alert
stress --vm 1 --vm-bytes 2G --timeout 300s

# Trigger API error alert
# Generate 500 errors to /test-endpoint

# Test database alert
# Create high connection load
```

## 📊 Metrics Reference

### HTTP Metrics
- `http_requests_total{method, endpoint, status_code}`
- `http_request_duration_seconds{method, endpoint}`
- `http_request_size_bytes{method, endpoint}`
- `http_response_size_bytes{method, endpoint}`

### Business Metrics
- `selextract_user_registrations_total`
- `selextract_compute_units_consumed_total{user_id, task_type}`
- `selextract_tasks_created_total{task_type, user_id}`
- `selextract_tasks_completed_total{task_type, status}`

### Task Queue Metrics
- `celery_queue_length{queue}`
- `celery_workers_active`
- `celery_task_runtime_seconds{task_name}`
- `celery_task_failed_total{task_name, error_type}`

### Security Metrics
- `selextract_failed_login_attempts_total{ip_address}`
- `selextract_rate_limit_violations_total{endpoint, ip_address}`

## 🔒 Security

### Access Control
- Grafana admin credentials in environment variables
- Alertmanager webhook authentication
- Prometheus metric endpoint protection

### Network Security
- Internal Docker network isolation
- Minimal exposed ports
- TLS encryption for external connections

## 🔄 Maintenance

### Regular Tasks

**Daily:**
- Monitor alert notifications
- Check service health
- Review performance trends

**Weekly:**
- Analyze capacity trends
- Update alert thresholds
- Review dashboard usage

**Monthly:**
- Clean up old data
- Update monitoring components
- Capacity planning review

### Backup

Critical configurations to backup:
- `prometheus.yml` - Prometheus configuration
- `alert_rules.yml` - Alert definitions  
- `alertmanager.yml` - Alert routing
- `grafana/dashboards/` - Dashboard definitions
- Environment variables

### Updates

Update monitoring stack:
```bash
# Pull latest images
docker-compose -f docker-compose.monitoring.yml pull

# Restart with new images
docker-compose -f docker-compose.monitoring.yml up -d
```

## 🎯 Performance Tuning

### Prometheus Optimization
- Adjust scrape intervals based on needs
- Configure retention policies
- Enable query optimizations
- Use recording rules for complex queries

### Grafana Optimization  
- Cache dashboard queries
- Optimize panel refresh rates
- Use template variables efficiently
- Configure data source query timeouts

### Resource Limits
All services have defined resource limits in docker-compose:
- Prometheus: 2GB RAM, 1 CPU
- Grafana: 1GB RAM, 0.5 CPU
- Alertmanager: 256MB RAM, 0.2 CPU
- Exporters: 128MB RAM, 0.1 CPU each

## 📞 Support

For monitoring-related issues:

1. Check service logs and health endpoints
2. Verify network connectivity between services  
3. Validate configuration syntax
4. Review resource usage and limits
5. Consult troubleshooting section above

The monitoring stack is designed for production reliability with comprehensive observability into the Selextract Cloud platform.