#!/bin/bash

# Selextract Cloud Production Deployment Script
# This script handles complete production deployment with zero-downtime updates

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/deployment.log"
BACKUP_DIR="/opt/backups"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    log "ERROR: $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
    log "WARNING: $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    log "INFO: $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    log "SUCCESS: $1"
}

# Check if running as correct user
check_user() {
    if [[ "$(whoami)" != "$DEPLOY_USER" ]] && [[ $EUID -ne 0 ]]; then
        error "This script should be run as user '$DEPLOY_USER' or root"
    fi
}

# Check prerequisites
check_prerequisites() {
    info "Checking deployment prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not available"
    fi
    
    # Check if required files exist
    local required_files=(
        "$PROJECT_DIR/docker-compose.prod.yml"
        "$PROJECT_DIR/.env.prod"
        "$PROJECT_DIR/nginx/nginx.conf"
        "$PROJECT_DIR/nginx/sites-available/selextract.conf"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            error "Required file not found: $file"
        fi
    done
    
    success "Prerequisites check passed"
}

# Load environment variables
load_environment() {
    info "Loading environment configuration..."
    
    if [[ -f "$PROJECT_DIR/.env.prod" ]]; then
        set -a
        source "$PROJECT_DIR/.env.prod"
        set +a
        success "Environment variables loaded"
    else
        error "Production environment file not found: $PROJECT_DIR/.env.prod"
    fi
}

# Create necessary directories
setup_directories() {
    info "Setting up deployment directories..."
    
    local directories=(
        "$BACKUP_DIR"
        "/var/log/selextract"
        "/opt/selextract/results"
        "/opt/selextract/logs"
        "/opt/selextract/ssl"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            info "Created directory: $dir"
        fi
    done
    
    # Set proper permissions
    chown -R "$DEPLOY_USER:$DEPLOY_USER" /opt/selextract || warning "Could not set ownership for /opt/selextract"
    chmod -R 755 /opt/selextract || warning "Could not set permissions for /opt/selextract"
    
    success "Directories setup completed"
}

# Backup current deployment
backup_current_deployment() {
    info "Creating backup of current deployment..."
    
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/deployment_$backup_timestamp"
    
    mkdir -p "$backup_path"
    
    # Backup database if containers are running
    if docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" ps | grep -q postgres; then
        info "Backing up PostgreSQL database..."
        docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T postgres \
            pg_dump -U postgres -d selextract | gzip > "$backup_path/database.sql.gz"
        success "Database backup created"
    fi
    
    # Backup current configuration
    if [[ -f "$PROJECT_DIR/.env.prod" ]]; then
        cp "$PROJECT_DIR/.env.prod" "$backup_path/"
    fi
    
    # Backup results directory if it exists
    if [[ -d "/opt/selextract/results" ]]; then
        tar -czf "$backup_path/results.tar.gz" -C "/opt/selextract" results/
        info "Results directory backed up"
    fi
    
    # Store backup path for potential rollback
    echo "$backup_path" > /tmp/last_backup_path
    
    success "Backup created at: $backup_path"
}

# Pull latest images
pull_images() {
    info "Pulling latest Docker images..."
    
    cd "$PROJECT_DIR"
    
    # Build custom images
    docker-compose -f docker-compose.prod.yml build --no-cache --pull
    
    # Pull external images
    docker-compose -f docker-compose.prod.yml pull
    
    success "Images updated successfully"
}

# Deploy with zero-downtime strategy
deploy_services() {
    info "Starting zero-downtime deployment..."
    
    cd "$PROJECT_DIR"
    
    # Start infrastructure services first (database, redis, monitoring)
    info "Starting infrastructure services..."
    docker-compose -f docker-compose.prod.yml up -d postgres redis prometheus grafana alertmanager
    
    # Wait for database to be ready
    info "Waiting for database to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U postgres; then
            success "Database is ready"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            error "Database failed to start within expected time"
        fi
        
        info "Waiting for database... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    # Start application services
    info "Starting application services..."
    docker-compose -f docker-compose.prod.yml up -d api worker
    
    # Wait for API to be ready
    info "Waiting for API to be ready..."
    attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f http://localhost:8000/health &>/dev/null; then
            success "API is ready"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            error "API failed to start within expected time"
        fi
        
        info "Waiting for API... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    # Start frontend
    info "Starting frontend..."
    docker-compose -f docker-compose.prod.yml up -d frontend
    
    # Finally start nginx
    info "Starting nginx reverse proxy..."
    docker-compose -f docker-compose.prod.yml up -d nginx
    
    success "All services deployed successfully"
}

# Run database migrations
run_migrations() {
    info "Running database migrations..."
    
    cd "$PROJECT_DIR"
    
    # Run migrations inside the API container
    if docker-compose -f docker-compose.prod.yml exec -T api python -c "
import asyncio
from api.database import engine, Base
from sqlalchemy import text

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print('Database tables created/updated successfully')

asyncio.run(create_tables())
"; then
        success "Database migrations completed"
    else
        warning "Database migrations may have failed, check logs"
    fi
}

# Verify deployment
verify_deployment() {
    info "Verifying deployment..."
    
    local services=(
        "postgres:5432"
        "redis:6379" 
        "api:8000"
        "frontend:3000"
        "nginx:80"
        "nginx:443"
        "prometheus:9090"
        "grafana:3000"
    )
    
    local failed_services=()
    
    for service in "${services[@]}"; do
        local service_name="${service%:*}"
        local port="${service#*:}"
        
        if docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" ps | grep -q "$service_name.*Up"; then
            info "✓ $service_name is running"
        else
            warning "✗ $service_name is not running properly"
            failed_services+=("$service_name")
        fi
    done
    
    # Test HTTP endpoints
    local endpoints=(
        "http://localhost/health"
        "http://localhost:8000/health"
        "http://localhost:3000"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "$endpoint" &>/dev/null; then
            info "✓ $endpoint is responding"
        else
            warning "✗ $endpoint is not responding"
        fi
    done
    
    if [[ ${#failed_services[@]} -eq 0 ]]; then
        success "Deployment verification passed"
        return 0
    else
        error "Deployment verification failed. Failed services: ${failed_services[*]}"
        return 1
    fi
}

# Setup monitoring and logging
setup_monitoring() {
    info "Setting up monitoring and logging..."
    
    cd "$PROJECT_DIR"
    
    # Ensure monitoring services are running
    docker-compose -f docker-compose.prod.yml up -d prometheus grafana alertmanager
    
    # Setup log directories
    mkdir -p /var/log/selextract/{api,worker,frontend,nginx}
    chown -R "$DEPLOY_USER:$DEPLOY_USER" /var/log/selextract
    
    success "Monitoring and logging setup completed"
}

# Cleanup old images and containers
cleanup() {
    info "Cleaning up old Docker resources..."
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused containers
    docker container prune -f
    
    # Remove unused networks
    docker network prune -f
    
    # Remove unused volumes (be careful with this)
    # docker volume prune -f
    
    success "Cleanup completed"
}

# Rollback function
rollback() {
    local backup_path="${1:-}"
    
    if [[ -z "$backup_path" ]] && [[ -f "/tmp/last_backup_path" ]]; then
        backup_path=$(cat /tmp/last_backup_path)
    fi
    
    if [[ -z "$backup_path" ]] || [[ ! -d "$backup_path" ]]; then
        error "No valid backup path provided for rollback"
    fi
    
    warning "Starting rollback to backup: $backup_path"
    
    cd "$PROJECT_DIR"
    
    # Stop current services
    docker-compose -f docker-compose.prod.yml down
    
    # Restore configuration
    if [[ -f "$backup_path/.env.prod" ]]; then
        cp "$backup_path/.env.prod" "$PROJECT_DIR/"
    fi
    
    # Restore database
    if [[ -f "$backup_path/database.sql.gz" ]]; then
        info "Restoring database..."
        docker-compose -f docker-compose.prod.yml up -d postgres
        sleep 10
        gunzip -c "$backup_path/database.sql.gz" | \
            docker-compose -f docker-compose.prod.yml exec -T postgres \
            psql -U postgres -d selextract
    fi
    
    # Restart services
    deploy_services
    
    success "Rollback completed"
}

# Send deployment notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Send to Slack if webhook is configured
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚀 Selextract Deployment $status: $message\"}" \
            "$SLACK_WEBHOOK_URL" &>/dev/null || true
    fi
    
    # Send email if configured
    if command -v mail &>/dev/null && [[ -n "${ADMIN_EMAIL:-}" ]]; then
        echo "Deployment $status: $message" | \
            mail -s "Selextract Deployment $status" "$ADMIN_EMAIL" || true
    fi
}

# Main deployment function
main() {
    local start_time=$(date +%s)
    
    info "Starting Selextract Cloud production deployment..."
    send_notification "STARTED" "Production deployment initiated"
    
    # Trap to handle failures
    trap 'error "Deployment failed. Check logs at $LOG_FILE"' ERR
    
    check_user
    check_prerequisites
    load_environment
    setup_directories
    backup_current_deployment
    pull_images
    deploy_services
    run_migrations
    setup_monitoring
    
    if verify_deployment; then
        cleanup
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        success "Deployment completed successfully in ${duration}s"
        send_notification "SUCCESS" "Deployment completed in ${duration}s"
    else
        error "Deployment verification failed"
    fi
}

# Handle command line arguments
case "${1:-}" in
    --rollback)
        rollback "${2:-}"
        ;;
    --verify)
        verify_deployment
        ;;
    --backup)
        backup_current_deployment
        ;;
    --help)
        echo "Usage: $0 [--rollback [backup_path]|--verify|--backup|--help]"
        echo ""
        echo "Options:"
        echo "  --rollback [path]  Rollback to previous deployment or specified backup"
        echo "  --verify          Verify current deployment status"
        echo "  --backup          Create backup of current deployment"
        echo "  --help            Show this help message"
        ;;
    *)
        main
        ;;
esac