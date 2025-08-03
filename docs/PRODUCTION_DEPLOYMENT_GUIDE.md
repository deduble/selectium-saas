# Selextract Cloud Production Deployment Guide

This comprehensive guide will walk you through deploying Selextract Cloud to a production server from scratch. Follow these steps carefully to ensure a secure, reliable, and scalable deployment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [Initial Configuration](#initial-configuration)
4. [Security Hardening](#security-hardening)
5. [SSL Certificate Setup](#ssl-certificate-setup)
6. [Application Deployment](#application-deployment)
7. [Monitoring Setup](#monitoring-setup)
8. [Testing and Verification](#testing-and-verification)
9. [Post-Deployment Tasks](#post-deployment-tasks)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

### Hardware Requirements

**Minimum Production Server Specifications:**
- **CPU:** 8 cores (16 cores recommended)
- **RAM:** 32GB (64GB recommended)
- **Storage:** 500GB SSD (1TB recommended)
- **Network:** 1Gbps connection
- **OS:** Ubuntu 20.04 LTS or Ubuntu 22.04 LTS

**Recommended Production Server (Hetzner EX44):**
- **CPU:** AMD Ryzen 7 3700X (8 cores, 16 threads)
- **RAM:** 64GB DDR4
- **Storage:** 2 × 512GB NVMe SSD
- **Network:** 1Gbps unmetered
- **Monthly Cost:** ~€59

### Domain and DNS Setup

Before starting, ensure you have:
- [ ] Domain name registered (e.g., `selextract.com`)
- [ ] DNS configured with A records pointing to your server:
  - `app.selextract.com` → Server IP
  - `api.selextract.com` → Server IP
  - `monitoring.selextract.com` → Server IP
- [ ] TTL set to 300 seconds (5 minutes) for faster propagation

### External Services

Set up these external services before deployment:
- [ ] **Google OAuth:** Create OAuth 2.0 credentials
- [ ] **Lemon Squeezy:** Set up billing products and webhooks
- [ ] **Webshare.io:** Purchase proxy plan and get API key
- [ ] **Email Service:** SMTP credentials for alerts (Gmail, SendGrid, etc.)
- [ ] **Backup Storage:** S3, Backblaze B2, or similar (optional)

## Server Setup

### 1. Initial Server Access

```bash
# Connect to your server
ssh root@YOUR_SERVER_IP

# Update system packages
apt update && apt upgrade -y

# Set timezone
timedatectl set-timezone UTC

# Set hostname
hostnamectl set-hostname selextract-prod
```

### 2. Create Deployment User

```bash
# Create deployment user
adduser deploy
usermod -aG sudo deploy

# Configure SSH key access for deploy user
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Test access with new user
su - deploy
```

### 3. Install Docker and Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add deploy user to docker group
sudo usermod -aG docker deploy

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### 4. Clone Application Repository

```bash
# Clone the repository
cd /opt
sudo git clone https://github.com/your-username/selextract-cloud.git
sudo chown -R deploy:deploy selextract-cloud
cd selextract-cloud

# Or if deploying from local development
# Upload your project files to /opt/selextract-cloud
```

## Initial Configuration

### 1. Configure Environment Variables

```bash
# Copy production environment template
cp .env.prod .env.prod.local

# Edit production configuration
nano .env.prod.local
```

**Critical values to update in `.env.prod.local`:**

```bash
# Database passwords (generate strong 32+ character passwords)
POSTGRES_PASSWORD=your_super_secure_postgres_password_here
REDIS_PASSWORD=your_super_secure_redis_password_here

# JWT and session secrets (generate 64+ character random strings)
JWT_SECRET_KEY=your_jwt_secret_key_64_chars_minimum
NEXTAUTH_SECRET=your_nextauth_secret_64_chars_minimum

# OAuth credentials
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret

# External API keys
WEBSHARE_API_KEY=your-webshare-api-key
LEMON_SQUEEZY_API_KEY=your-lemon-squeezy-api-key
LEMON_SQUEEZY_STORE_ID=your-store-id
LEMON_SQUEEZY_WEBHOOK_SECRET=your-webhook-secret

# Product variant IDs
LEMON_SQUEEZY_STARTER_VARIANT_ID=actual-starter-variant-id
LEMON_SQUEEZY_PROFESSIONAL_VARIANT_ID=actual-professional-variant-id
LEMON_SQUEEZY_ENTERPRISE_VARIANT_ID=actual-enterprise-variant-id

# Admin credentials
GRAFANA_ADMIN_PASSWORD=your_secure_grafana_password
ADMIN_EMAIL=admin@selextract.com

# SMTP settings for alerts
SMTP_HOST=smtp.gmail.com
SMTP_USER=alerts@selextract.com
SMTP_PASSWORD=your-smtp-password

# Slack webhook (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

**Security note:** Ensure file permissions are secure:
```bash
chmod 600 .env.prod.local
```

### 2. Generate Strong Passwords

Use these commands to generate secure passwords:

```bash
# Generate 32-character password
openssl rand -base64 32

# Generate 64-character secret
openssl rand -base64 64

# Generate UUID for session secrets
uuidgen
```

### 3. Create Required Directories

```bash
# Create application directories
sudo mkdir -p /opt/selextract/{logs,results,ssl}
sudo mkdir -p /opt/backups
sudo mkdir -p /var/log/selextract

# Set proper ownership
sudo chown -R deploy:deploy /opt/selextract
sudo chown -R deploy:deploy /opt/backups
sudo chown -R deploy:deploy /var/log/selextract
```

## Security Hardening

Run the comprehensive security hardening script:

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run security hardening (as root)
sudo ./scripts/security-hardening.sh
```

This script will:
- Configure UFW firewall
- Harden SSH configuration
- Install and configure fail2ban
- Set up automatic security updates
- Configure system limits and kernel parameters
- Install monitoring tools
- Set up intrusion detection

**Important:** Test SSH access after running this script to ensure you can still connect.

## SSL Certificate Setup

### 1. Setup SSL Certificates

```bash
# Run SSL setup script (as root)
sudo ./scripts/setup-ssl.sh
```

The script will:
- Install certbot for Let's Encrypt
- Generate temporary self-signed certificates
- Configure Nginx for SSL
- Set up automatic certificate renewal

### 2. Obtain Let's Encrypt Certificates

After DNS propagation (wait 5-10 minutes), obtain real certificates:

```bash
# Get real Let's Encrypt certificates
sudo ./scripts/setup-ssl.sh --letsencrypt
```

### 3. Enable Nginx Sites

```bash
# Create symbolic link to enable site
sudo ln -sf /opt/selextract-cloud/nginx/sites-available/selextract.conf /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## Application Deployment

### 1. Initial Deployment

```bash
# Navigate to project directory
cd /opt/selextract-cloud

# Use production environment file
cp .env.prod.local .env.prod

# Run initial deployment
./scripts/deploy.sh
```

The deployment script will:
- Validate prerequisites
- Create pre-deployment backup
- Build Docker images
- Start services in correct order
- Run database migrations
- Verify deployment success

### 2. Monitor Deployment Progress

```bash
# Watch container status
watch docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.yml logs -f worker
docker-compose -f docker-compose.prod.yml logs -f frontend
```

### 3. Verify Services

```bash
# Run health check
./scripts/health-check.sh

# Test API endpoint
curl -f http://localhost:8000/health

# Test frontend
curl -f http://localhost:3000

# Test external access (replace with your domain)
curl -f https://api.selextract.com/health
curl -f https://app.selextract.com
```

## Monitoring Setup

### 1. Access Monitoring Interfaces

After successful deployment, access these URLs:

- **Grafana:** `https://monitoring.selextract.com/grafana/`
- **Prometheus:** `https://monitoring.selextract.com/prometheus/`
- **Alertmanager:** `https://monitoring.selextract.com/alertmanager/`

### 2. Configure Grafana

1. Login with credentials from `.env.prod`
2. Import pre-configured dashboards
3. Configure notification channels (Slack, Email)
4. Set up alerting rules

### 3. Configure Alertmanager

Edit `monitoring/alertmanager.yml` to configure notifications:

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@selextract.com'
  smtp_auth_username: 'alerts@selextract.com'
  smtp_auth_password: 'your-smtp-password'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  email_configs:
  - to: 'admin@selextract.com'
    subject: 'Selextract Alert: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
```

## Testing and Verification

### 1. Comprehensive Health Check

```bash
# Run full health check
./scripts/health-check.sh

# Check specific components
./scripts/health-check.sh --critical-only
```

### 2. Test User Registration and Login

1. Navigate to `https://app.selextract.com`
2. Click "Sign in with Google"
3. Complete OAuth flow
4. Verify user dashboard loads

### 3. Test API Functionality

```bash
# Test that API is accessible for OAuth callback
curl https://api.selextract.com/health

# Test health endpoint
curl https://api.selextract.com/health
```

### 4. Test Worker Functionality

Create a test task through the web interface or API to verify:
- Task creation and queuing
- Worker processing
- Result storage and retrieval
- Proxy functionality

### 5. Test Backup and Restore

```bash
# Create test backup
./scripts/backup.sh --database-only

# List available backups
./scripts/restore.sh --list

# Test backup integrity
./scripts/backup.sh --verify /opt/backups/latest_backup_directory
```

## Post-Deployment Tasks

### 1. Configure Automated Backups

```bash
# Add daily backup to crontab
sudo crontab -e

# Add this line for daily backups at 2 AM
0 2 * * * /opt/selextract-cloud/scripts/backup.sh >/dev/null 2>&1
```

### 2. Configure Health Check Monitoring

```bash
# Add health check to crontab (every 5 minutes)
*/5 * * * * /opt/selextract-cloud/scripts/health-check.sh --silent
```

### 3. Set Up Log Rotation

```bash
# Configure log rotation
sudo cp monitoring/logrotate.d/selextract /etc/logrotate.d/
sudo logrotate -d /etc/logrotate.d/selextract
```

### 4. Configure Monitoring Alerts

1. Set up PagerDuty or similar for critical alerts
2. Configure Slack notifications for warnings
3. Set up uptime monitoring (UptimeRobot, Pingdom)

### 5. Performance Optimization

```bash
# Optimize PostgreSQL settings
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d selextract -c "
    ALTER SYSTEM SET shared_buffers = '8GB';
    ALTER SYSTEM SET effective_cache_size = '24GB';
    ALTER SYSTEM SET maintenance_work_mem = '2GB';
    SELECT pg_reload_conf();
  "

# Optimize Redis settings
docker-compose -f docker-compose.prod.yml exec redis \
  redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

## Troubleshooting

### Common Issues

#### 1. SSL Certificate Issues

```bash
# Check certificate status
./scripts/setup-ssl.sh --verify

# Renew certificates manually
sudo certbot renew --dry-run
sudo certbot renew
```

#### 2. Container Not Starting

```bash
# Check container logs
docker-compose -f docker-compose.prod.yml logs <service_name>

# Check resource usage
docker stats

# Restart specific service
docker-compose -f docker-compose.prod.yml restart <service_name>
```

#### 3. Database Connection Issues

```bash
# Check PostgreSQL status
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U postgres

# Check database logs
docker-compose -f docker-compose.prod.yml logs postgres

# Reset database connection pool
docker-compose -f docker-compose.prod.yml restart api
```

#### 4. High Resource Usage

```bash
# Check system resources
htop
df -h
free -h

# Check Docker resource usage
docker system df
docker stats

# Clean up unused resources
docker system prune -f
```

#### 5. Worker Not Processing Tasks

```bash
# Check worker logs
docker-compose -f docker-compose.prod.yml logs worker

# Check Redis connection
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# Check Celery status
docker-compose -f docker-compose.prod.yml exec worker celery -A main inspect active
```

### Emergency Procedures

#### 1. Rollback Deployment

```bash
# Rollback to previous version
./scripts/deploy.sh --rollback

# Or restore from backup
./scripts/restore.sh
```

#### 2. Scale Workers During High Load

```bash
# Scale up workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=8

# Scale down workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=2
```

#### 3. Emergency Maintenance Mode

```bash
# Enable maintenance mode
echo "MAINTENANCE_MODE=true" >> .env.prod
docker-compose -f docker-compose.prod.yml restart nginx

# Disable maintenance mode
sed -i '/MAINTENANCE_MODE=true/d' .env.prod
docker-compose -f docker-compose.prod.yml restart nginx
```

### Getting Help

If you encounter issues not covered in this guide:

1. Check the application logs in `/var/log/selextract/`
2. Run the health check script for detailed diagnostics
3. Review monitoring dashboards for system metrics
4. Consult the project's issue tracker on GitHub
5. Contact the development team via the configured support channels

## Security Checklist

Before going live, ensure:

- [ ] All default passwords changed
- [ ] SSL certificates properly configured
- [ ] Firewall rules configured and tested
- [ ] fail2ban running and configured
- [ ] SSH key-based authentication only
- [ ] Regular backups scheduled and tested
- [ ] Monitoring alerts configured
- [ ] Security updates automated
- [ ] Log monitoring configured
- [ ] Intrusion detection active

## Performance Monitoring

Monitor these key metrics:

- **System:** CPU, Memory, Disk I/O, Network
- **Application:** Response times, Error rates, Task throughput
- **Database:** Connection pool, Query performance, Lock contention
- **Workers:** Queue depth, Processing times, Error rates
- **External Services:** Proxy health, API rate limits

## Maintenance Schedule

Establish regular maintenance:

- **Daily:** Automated backups, Health checks
- **Weekly:** Security updates, Log review
- **Monthly:** Performance review, Capacity planning
- **Quarterly:** Security audit, Disaster recovery test

## Future Scaling Path

As your Selextract Cloud deployment grows, you'll need to scale beyond the single-server architecture. This section outlines the planned scaling path and implementation strategies.

### Scaling Overview

The scaling path follows a deliberate progression:

1. **Phase 1:** Database Decoupling (Current → Multi-service)
2. **Phase 2:** Dedicated Worker Nodes (Compute Scaling)
3. **Phase 3:** Load Balancer Implementation (High Availability)
4. **Phase 4:** Shared Storage Adoption (Data Scaling)

### Phase 1: Database Decoupling

**When to Scale:** CPU > 80% consistently, or database connections > 80% of pool

**Implementation:**

```bash
# 1. Provision dedicated database server
# Recommended specs: 16+ cores, 64GB+ RAM, NVMe SSD

# 2. Update environment configuration
# In .env.prod, change:
DATABASE_URL=postgresql://postgres:password@db-server.internal:5432/selextract
REDIS_URL=redis://:password@redis-server.internal:6379/0

# 3. Migrate data
./scripts/backup.sh --database-only
scp /opt/backups/latest_backup.tar.gz db-server:/tmp/
ssh db-server "cd /tmp && tar -xzf latest_backup.tar.gz"
ssh db-server "psql -U postgres < /tmp/backup/database/selextract_*.sql"

# 4. Update Docker Compose (remove database services)
# Create docker-compose.external-db.yml without postgres/redis services

# 5. Deploy with external database
docker-compose -f docker-compose.external-db.yml up -d
```

**Expected Improvements:**
- 50-70% reduction in main server resource usage
- Better database performance isolation
- Easier database maintenance and optimization

### Phase 2: Dedicated Worker Nodes

**When to Scale:** Task queue depth > 100 consistently, or need for specialized workers

**Implementation:**

```bash
# 1. Provision worker servers
# Recommended specs per worker: 8+ cores, 32GB+ RAM

# 2. Create worker-only Docker Compose configuration
# docker-compose.worker.yml:
version: '3.8'
services:
  worker:
    build: ./worker
    environment:
      - CELERY_BROKER_URL=redis://:password@redis-server.internal:6379/0
      - DATABASE_URL=postgresql://postgres:password@db-server.internal:5432/selextract
    deploy:
      replicas: 4
      resources:
        limits:
          cpus: '2'
          memory: '8G'

# 3. Deploy workers on each node
for worker_node in worker-01 worker-02 worker-03; do
  scp -r . $worker_node:/opt/selextract-worker/
  ssh $worker_node "cd /opt/selextract-worker && docker-compose -f docker-compose.worker.yml up -d"
done

# 4. Update main server (remove worker service)
docker-compose -f docker-compose.api-only.yml up -d

# 5. Configure worker monitoring
# Add worker nodes to Prometheus configuration
```

**Worker Node Setup Script:**

```bash
#!/bin/bash
# setup-worker-node.sh

WORKER_NODE="$1"
if [[ -z "$WORKER_NODE" ]]; then
    echo "Usage: $0 <worker-node-hostname>"
    exit 1
fi

# Copy application code
rsync -av --exclude='.git' --exclude='node_modules' . "$WORKER_NODE:/opt/selextract-worker/"

# Setup worker environment
ssh "$WORKER_NODE" << 'EOF'
    cd /opt/selextract-worker
    
    # Install Docker if not present
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
    fi
    
    # Create worker-specific environment
    cp .env.prod .env.worker
    
    # Start worker services
    docker-compose -f docker-compose.worker.yml up -d
    
    # Verify worker is running
    docker-compose -f docker-compose.worker.yml logs worker
EOF

echo "Worker node $WORKER_NODE setup complete"
```

**Expected Improvements:**
- Linear scaling of task processing capacity
- Isolation of compute-intensive operations
- Better fault tolerance (worker failures don't affect API)

### Phase 3: Load Balancer Implementation

**When to Scale:** API response time > 2s, or need for high availability

**Implementation:**

```bash
# 1. Provision load balancer server
# Recommended: HAProxy or Nginx with 4+ cores, 16GB+ RAM

# 2. Configure HAProxy for high availability
# /etc/haproxy/haproxy.cfg:
global
    daemon
    maxconn 4096

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend selextract_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/selextract.pem
    redirect scheme https if !{ ssl_fc }
    default_backend selextract_api_servers

backend selextract_api_servers
    balance roundrobin
    option httpchk GET /health
    server api-01 api-server-01.internal:8000 check
    server api-02 api-server-02.internal:8000 check
    server api-03 api-server-03.internal:8000 check

# 3. Provision multiple API servers
for api_node in api-01 api-02; do
    # Clone main server setup
    rsync -av --exclude='worker' . $api_node:/opt/selextract-api/
    ssh $api_node "cd /opt/selextract-api && docker-compose -f docker-compose.api-only.yml up -d"
done

# 4. Update DNS to point to load balancer
# A records should point to load balancer IP
```

**Load Balancer Health Monitoring:**

```bash
#!/bin/bash
# lb-health-check.sh

BACKEND_SERVERS=("api-01.internal:8000" "api-02.internal:8000" "api-03.internal:8000")

for server in "${BACKEND_SERVERS[@]}"; do
    if curl -f -s --max-time 5 "http://$server/health" > /dev/null; then
        echo "✓ $server is healthy"
    else
        echo "✗ $server is unhealthy"
        # Alert administrators
        curl -X POST "$SLACK_WEBHOOK_URL" -d "{\"text\":\"⚠️ API server $server is unhealthy\"}"
    fi
done
```

**Expected Improvements:**
- Zero-downtime deployments
- Automatic failover between API servers
- Better handling of traffic spikes
- Geographic distribution capability

### Phase 4: Shared Storage Adoption

**When to Scale:** Storage > 80% full, or need for distributed file access

**Implementation with MinIO:**

```bash
# 1. Provision MinIO cluster (minimum 4 nodes)
# Recommended: 4 nodes, 8+ cores each, 32GB+ RAM, 1TB+ NVMe each

# 2. Setup MinIO cluster
for minio_node in minio-01 minio-02 minio-03 minio-04; do
    ssh $minio_node << 'EOF'
        # Install MinIO
        wget https://dl.min.io/server/minio/release/linux-amd64/minio
        chmod +x minio
        sudo mv minio /usr/local/bin/
        
        # Create MinIO user
        sudo useradd -r minio-user -s /sbin/nologin
        
        # Create data directories
        sudo mkdir -p /mnt/data{1,2,3,4}
        sudo chown minio-user:minio-user /mnt/data*
        
        # Create systemd service
        sudo tee /etc/systemd/system/minio.service << 'SERVICE'
[Unit]
Description=MinIO
Documentation=https://docs.min.io
Wants=network-online.target
After=network-online.target
AssertFileIsExecutable=/usr/local/bin/minio

[Service]
WorkingDirectory=/usr/local/

User=minio-user
Group=minio-user

EnvironmentFile=/etc/default/minio
ExecStartPre=/bin/bash -c "if [ -z \"${MINIO_VOLUMES}\" ]; then echo \"Variable MINIO_VOLUMES not set in /etc/default/minio\"; exit 1; fi"
ExecStart=/usr/local/bin/minio server $MINIO_OPTS $MINIO_VOLUMES

Restart=always
LimitNOFILE=65536
TasksMax=infinity
TimeoutStopSec=infinity
SendSIGKILL=no

[Install]
WantedBy=multi-user.target
SERVICE
        
        # Configure MinIO environment
        sudo tee /etc/default/minio << 'CONFIG'
MINIO_ROOT_USER=selextract_admin
MINIO_ROOT_PASSWORD=your_super_secure_minio_password_here
MINIO_VOLUMES="http://minio-0{1...4}.internal/mnt/data{1...4}"
MINIO_OPTS="--console-address :9001"
CONFIG
        
        # Start MinIO
        sudo systemctl enable minio
        sudo systemctl start minio
EOF
done

# 3. Configure MinIO buckets
mc alias set selextract-minio http://minio-01.internal:9000 selextract_admin your_password
mc mb selextract-minio/task-results
mc mb selextract-minio/backups
mc mb selextract-minio/logs

# 4. Update application configuration
# In .env.prod:
STORAGE_BACKEND=minio
MINIO_ENDPOINT=http://minio-lb.internal:9000
MINIO_ACCESS_KEY=selextract_app
MINIO_SECRET_KEY=app_secret_key
MINIO_BUCKET_RESULTS=task-results
MINIO_BUCKET_BACKUPS=backups
```

**Application Integration:**

```python
# worker/storage.py
import boto3
from botocore.client import Config

class MinIOStorage:
    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url=os.getenv('MINIO_ENDPOINT'),
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY'),
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        self.bucket = os.getenv('MINIO_BUCKET_RESULTS')
    
    def upload_results(self, task_id, file_path):
        """Upload task results to MinIO."""
        key = f"tasks/{task_id}/results.json"
        self.client.upload_file(file_path, self.bucket, key)
        return f"s3://{self.bucket}/{key}"
    
    def download_results(self, task_id, local_path):
        """Download task results from MinIO."""
        key = f"tasks/{task_id}/results.json"
        self.client.download_file(self.bucket, key, local_path)
```

**Expected Improvements:**
- Unlimited storage scalability
- Better data durability and availability
- Simplified backup management
- CDN integration capabilities

### Scaling Metrics and Monitoring

**Key Performance Indicators:**

```yaml
# scaling-alerts.yml
groups:
  - name: scaling_alerts
    rules:
      # Database Scaling Triggers
      - alert: DatabaseCPUHigh
        expr: postgres_cpu_usage_percent > 80
        for: 15m
        annotations:
          summary: "Consider database decoupling"
      
      # Worker Scaling Triggers
      - alert: TaskQueueDepthHigh
        expr: celery_queue_length > 100
        for: 10m
        annotations:
          summary: "Consider adding worker nodes"
      
      # API Scaling Triggers
      - alert: APIResponseTimeHigh
        expr: api_response_time_95th > 2
        for: 5m
        annotations:
          summary: "Consider load balancer implementation"
      
      # Storage Scaling Triggers
      - alert: StorageUsageHigh
        expr: disk_usage_percent > 80
        for: 5m
        annotations:
          summary: "Consider shared storage adoption"
```

### Capacity Planning Guidelines

**Traffic Growth Projections:**

| Phase | Users | Tasks/Day | Storage | Servers Required |
|-------|-------|-----------|---------|------------------|
| Current | 1-100 | <1,000 | <100GB | 1 (all-in-one) |
| Phase 1 | 100-500 | 1,000-5,000 | 100GB-500GB | 3 (api, db, redis) |
| Phase 2 | 500-2,000 | 5,000-20,000 | 500GB-2TB | 6+ (api, db, redis, 3x workers) |
| Phase 3 | 2,000-10,000 | 20,000-100,000 | 2TB-10TB | 10+ (lb, 3x api, db, redis, 4x workers) |
| Phase 4 | 10,000+ | 100,000+ | 10TB+ | 15+ (+ MinIO cluster) |

**Resource Planning Calculator:**

```bash
#!/bin/bash
# capacity-calculator.sh

DAILY_TASKS="$1"
AVG_TASK_DURATION_MINUTES="$2"
PEAK_CONCURRENCY_FACTOR="$3"  # e.g., 3.0 for 3x average during peak hours

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <daily_tasks> <avg_duration_minutes> <peak_factor>"
    echo "Example: $0 10000 5 3.0"
    exit 1
fi

# Calculate required workers
TASKS_PER_MINUTE=$((DAILY_TASKS / (24 * 60)))
PEAK_TASKS_PER_MINUTE=$(echo "$TASKS_PER_MINUTE * $PEAK_CONCURRENCY_FACTOR" | bc)
CONCURRENT_TASKS=$(echo "$PEAK_TASKS_PER_MINUTE * $AVG_TASK_DURATION_MINUTES" | bc)
RECOMMENDED_WORKERS=$(echo "($CONCURRENT_TASKS / 4) + 1" | bc)  # 4 tasks per worker + buffer

echo "=== Capacity Planning Results ==="
echo "Daily Tasks: $DAILY_TASKS"
echo "Peak Tasks per Minute: $PEAK_TASKS_PER_MINUTE"
echo "Concurrent Tasks (Peak): $CONCURRENT_TASKS"
echo "Recommended Workers: $RECOMMENDED_WORKERS"
echo "Recommended Worker Nodes: $(echo "($RECOMMENDED_WORKERS / 4) + 1" | bc)"

# Database recommendations
DB_CONNECTIONS=$((RECOMMENDED_WORKERS * 5))  # 5 connections per worker
echo "Recommended DB Connection Pool: $DB_CONNECTIONS"

# Storage recommendations
DAILY_STORAGE_GB=$(echo "$DAILY_TASKS * 0.1" | bc)  # 100KB per task average
MONTHLY_STORAGE_GB=$(echo "$DAILY_STORAGE_GB * 30" | bc)
echo "Estimated Monthly Storage Growth: ${MONTHLY_STORAGE_GB}GB"
```

### Migration Scripts

**Phase 1 Migration (Database Decoupling):**

```bash
#!/bin/bash
# migrate-to-phase1.sh

set -euo pipefail

EXTERNAL_DB_HOST="$1"
EXTERNAL_REDIS_HOST="$2"

echo "Starting Phase 1 migration: Database decoupling"

# 1. Create backup
./scripts/backup.sh --database-only

# 2. Setup external databases
echo "Setting up external PostgreSQL..."
ssh "$EXTERNAL_DB_HOST" << 'EOF'
    # Install PostgreSQL
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
    
    # Configure PostgreSQL
    sudo -u postgres psql -c "CREATE DATABASE selextract;"
    sudo -u postgres psql -c "CREATE USER selextract WITH PASSWORD 'your_secure_password';"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE selextract TO selextract;"
    
    # Configure for external connections
    echo "host all all 0.0.0.0/0 md5" | sudo tee -a /etc/postgresql/*/main/pg_hba.conf
    echo "listen_addresses = '*'" | sudo tee -a /etc/postgresql/*/main/postgresql.conf
    sudo systemctl restart postgresql
EOF

echo "Setting up external Redis..."
ssh "$EXTERNAL_REDIS_HOST" << 'EOF'
    # Install Redis
    sudo apt update
    sudo apt install -y redis-server
    
    # Configure Redis for external access
    sudo sed -i 's/bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf
    echo "requirepass your_secure_redis_password" | sudo tee -a /etc/redis/redis.conf
    sudo systemctl restart redis
EOF

# 3. Migrate data
echo "Migrating database..."
LATEST_BACKUP=$(ls -t /opt/backups/ | head -1)
gunzip -c "/opt/backups/$LATEST_BACKUP/database/selextract_*.sql.gz" | \
    PGPASSWORD=your_secure_password psql -h "$EXTERNAL_DB_HOST" -U selextract -d selextract

# 4. Update configuration
echo "Updating application configuration..."
cp .env.prod .env.prod.backup
sed -i "s|DATABASE_URL=.*|DATABASE_URL=postgresql://selextract:your_secure_password@${EXTERNAL_DB_HOST}:5432/selextract|" .env.prod
sed -i "s|REDIS_URL=.*|REDIS_URL=redis://:your_secure_redis_password@${EXTERNAL_REDIS_HOST}:6379/0|" .env.prod

# 5. Update Docker Compose
cp docker-compose.prod.yml docker-compose.phase1.yml
# Remove postgres and redis services from docker-compose.phase1.yml

# 6. Deploy with external services
echo "Deploying with external databases..."
docker-compose -f docker-compose.phase1.yml up -d

# 7. Verify migration
echo "Verifying migration..."
./scripts/health-check.sh

echo "Phase 1 migration completed successfully!"
echo "Remember to:"
echo "1. Monitor database performance on external server"
echo "2. Setup backup procedures for external databases"
echo "3. Configure monitoring for new infrastructure"
```

### Scaling Checklist

Before scaling to each phase, ensure:

#### Phase 1 Preparation:
- [ ] Database backup procedures tested and verified
- [ ] External database server provisioned and secured
- [ ] Network connectivity between servers configured
- [ ] Database migration scripts tested in staging
- [ ] Monitoring configured for external database
- [ ] Rollback procedure documented and tested

#### Phase 2 Preparation:
- [ ] Worker nodes provisioned with appropriate specs
- [ ] Container orchestration strategy defined
- [ ] Worker deployment scripts tested
- [ ] Queue monitoring and scaling policies configured
- [ ] Worker failure handling procedures documented
- [ ] Performance benchmarks established

#### Phase 3 Preparation:
- [ ] Load balancer configured and tested
- [ ] SSL certificate management automated
- [ ] Health check endpoints implemented
- [ ] Session storage strategy for load balancing
- [ ] Deployment strategy for zero-downtime updates
- [ ] Disaster recovery procedures updated

#### Phase 4 Preparation:
- [ ] MinIO cluster properly configured and secured
- [ ] Data migration strategy from local storage
- [ ] Application code updated for object storage
- [ ] Backup procedures adapted for distributed storage
- [ ] CDN integration planned (if needed)
- [ ] Storage monitoring and alerting configured

---

Congratulations! You have successfully deployed Selextract Cloud to production. This comprehensive guide provides both immediate deployment instructions and a clear path for future scaling as your needs grow. Remember to monitor the system closely during the first few days and be prepared to scale resources based on actual usage patterns following the outlined phases.