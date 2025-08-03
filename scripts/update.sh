#!/bin/bash

# Selextract Cloud Zero-Downtime Update Script
# This script handles application updates with minimal service interruption

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/update.log"
BACKUP_DIR="/opt/backups"
UPDATE_STRATEGY="${UPDATE_STRATEGY:-rolling}"

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

# Check prerequisites
check_prerequisites() {
    info "Checking update prerequisites..."
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
    fi
    
    # Check if services are running
    cd "$PROJECT_DIR"
    if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        error "No services are currently running. Use deploy.sh for initial deployment."
    fi
    
    # Check if git repository is clean (if using git)
    if [[ -d "$PROJECT_DIR/.git" ]]; then
        if ! git diff-index --quiet HEAD --; then
            warning "Git repository has uncommitted changes"
            read -p "Do you want to continue anyway? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                error "Update cancelled due to uncommitted changes"
            fi
        fi
    fi
    
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

# Create pre-update backup
create_backup() {
    info "Creating pre-update backup..."
    
    # Use the backup script to create a backup
    if [[ -x "$SCRIPT_DIR/backup.sh" ]]; then
        "$SCRIPT_DIR/backup.sh" --no-remote
        BACKUP_PATH=$(cat /tmp/current_backup_path 2>/dev/null || echo "")
        if [[ -n "$BACKUP_PATH" ]]; then
            echo "$BACKUP_PATH" > /tmp/pre_update_backup_path
            success "Pre-update backup created: $BACKUP_PATH"
        else
            error "Failed to create pre-update backup"
        fi
    else
        warning "Backup script not found, skipping pre-update backup"
    fi
}

# Pull latest code (if using git)
pull_latest_code() {
    info "Pulling latest application code..."
    
    if [[ -d "$PROJECT_DIR/.git" ]]; then
        cd "$PROJECT_DIR"
        
        # Fetch latest changes
        git fetch origin
        
        # Check if there are updates
        local current_commit=$(git rev-parse HEAD)
        local latest_commit=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master)
        
        if [[ "$current_commit" == "$latest_commit" ]]; then
            info "No code updates available"
            return 0
        fi
        
        info "Updating from $current_commit to $latest_commit"
        
        # Pull latest changes
        git pull origin main 2>/dev/null || git pull origin master
        
        success "Latest code pulled successfully"
    else
        info "Not a git repository, skipping code update"
    fi
}

# Build updated images
build_images() {
    info "Building updated Docker images..."
    
    cd "$PROJECT_DIR"
    
    # Build images with no cache to ensure latest updates
    docker-compose -f docker-compose.prod.yml build --no-cache --pull
    
    success "Images built successfully"
}

# Update database schema (migrations)
run_migrations() {
    info "Running database migrations..."
    
    cd "$PROJECT_DIR"
    
    # Run migrations using the API container
    if docker-compose -f docker-compose.prod.yml exec -T api python -c "
import asyncio
from api.database import engine, Base
from sqlalchemy import text

async def run_migrations():
    async with engine.begin() as conn:
        # Check if database is accessible
        result = await conn.execute(text('SELECT 1'))
        print('Database connection successful')
        
        # Create/update tables
        await conn.run_sync(Base.metadata.create_all)
        print('Database migrations completed successfully')

asyncio.run(run_migrations())
"; then
        success "Database migrations completed"
    else
        error "Database migrations failed"
    fi
}

# Rolling update strategy
rolling_update() {
    info "Performing rolling update..."
    
    cd "$PROJECT_DIR"
    
    # Update services one by one to maintain availability
    local services=("worker" "api" "frontend")
    
    for service in "${services[@]}"; do
        info "Updating $service..."
        
        # Scale up new instances
        local current_replicas=$(docker-compose -f docker-compose.prod.yml ps -q $service | wc -l)
        local new_replicas=$((current_replicas + 1))
        
        # Start new instance
        docker-compose -f docker-compose.prod.yml up -d --scale $service=$new_replicas $service
        
        # Wait for new instance to be healthy
        local max_attempts=30
        local attempt=1
        local new_container=""
        
        while [[ $attempt -le $max_attempts ]]; do
            # Get the newest container
            new_container=$(docker-compose -f docker-compose.prod.yml ps -q $service | head -1)
            
            if [[ -n "$new_container" ]] && docker inspect "$new_container" | grep -q '"Status": "running"'; then
                # Additional health check for API
                if [[ "$service" == "api" ]]; then
                    if curl -f http://localhost:8000/health &>/dev/null; then
                        break
                    fi
                else
                    break
                fi
            fi
            
            if [[ $attempt -eq $max_attempts ]]; then
                error "New $service instance failed to start properly"
            fi
            
            info "Waiting for new $service instance... (attempt $attempt/$max_attempts)"
            sleep 10
            ((attempt++))
        done
        
        # Remove old instances
        local old_containers=($(docker-compose -f docker-compose.prod.yml ps -q $service | tail -n +2))
        for container in "${old_containers[@]}"; do
            if [[ -n "$container" ]]; then
                docker stop "$container" || warning "Could not stop container $container"
                docker rm "$container" || warning "Could not remove container $container"
            fi
        done
        
        success "$service updated successfully"
    done
}

# Blue-green update strategy
blue_green_update() {
    info "Performing blue-green update..."
    
    cd "$PROJECT_DIR"
    
    # This is a simplified blue-green implementation
    # In a full implementation, you'd need separate environments
    
    # For now, we'll use the rolling update approach
    # as true blue-green requires more infrastructure
    warning "Blue-green update not fully implemented, falling back to rolling update"
    rolling_update
}

# Update monitoring and reverse proxy last
update_infrastructure() {
    info "Updating infrastructure services..."
    
    cd "$PROJECT_DIR"
    
    # Update nginx configuration if changed
    docker-compose -f docker-compose.prod.yml up -d nginx
    
    # Test nginx configuration
    if ! docker-compose -f docker-compose.prod.yml exec -T nginx nginx -t; then
        error "Nginx configuration test failed"
    fi
    
    # Reload nginx to pick up any configuration changes
    docker-compose -f docker-compose.prod.yml exec -T nginx nginx -s reload || \
        warning "Could not reload nginx configuration"
    
    # Update monitoring services
    docker-compose -f docker-compose.prod.yml up -d prometheus grafana alertmanager
    
    success "Infrastructure services updated"
}

# Verify update success
verify_update() {
    info "Verifying update..."
    
    local services=(
        "postgres"
        "redis"
        "api"
        "worker"
        "frontend"
        "nginx"
        "prometheus"
        "grafana"
    )
    
    local failed_services=()
    
    # Check service status
    for service in "${services[@]}"; do
        if docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" ps | grep -q "$service.*Up"; then
            info "✓ $service is running"
        else
            warning "✗ $service is not running properly"
            failed_services+=("$service")
        fi
    done
    
    # Test HTTP endpoints
    local endpoints=(
        "http://localhost/health"
        "http://localhost:8000/health"
        "http://localhost:3000"
        "http://localhost:9090/-/healthy"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "$endpoint" &>/dev/null; then
            info "✓ $endpoint is responding"
        else
            warning "✗ $endpoint is not responding"
        fi
    done
    
    # Check if any workers are processing tasks
    local worker_count=$(docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" ps -q worker | wc -l)
    if [[ $worker_count -gt 0 ]]; then
        info "✓ $worker_count worker(s) are running"
    else
        warning "✗ No workers are running"
    fi
    
    if [[ ${#failed_services[@]} -eq 0 ]]; then
        success "Update verification passed"
        return 0
    else
        error "Update verification failed. Failed services: ${failed_services[*]}"
        return 1
    fi
}

# Cleanup old images and containers
cleanup() {
    info "Cleaning up old Docker resources..."
    
    # Remove old images (keep one previous version)
    docker image prune -f --filter "until=168h" # 7 days
    
    # Remove stopped containers
    docker container prune -f
    
    # Remove unused networks
    docker network prune -f
    
    success "Cleanup completed"
}

# Rollback function
rollback() {
    warning "Rolling back to previous version..."
    
    local backup_path=""
    if [[ -f "/tmp/pre_update_backup_path" ]]; then
        backup_path=$(cat /tmp/pre_update_backup_path)
    fi
    
    if [[ -n "$backup_path" ]] && [[ -d "$backup_path" ]]; then
        info "Using backup: $backup_path"
        if [[ -x "$SCRIPT_DIR/restore.sh" ]]; then
            "$SCRIPT_DIR/restore.sh" "$backup_path"
            success "Rollback completed"
        else
            error "Restore script not found, manual rollback required"
        fi
    else
        error "No backup available for rollback, manual intervention required"
    fi
}

# Send update notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Send to Slack if webhook is configured
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local emoji="🔄"
        if [[ "$status" == "SUCCESS" ]]; then
            emoji="✅"
        elif [[ "$status" == "FAILED" ]]; then
            emoji="❌"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$emoji Selextract Update $status: $message\"}" \
            "$SLACK_WEBHOOK_URL" &>/dev/null || true
    fi
    
    # Send email if configured
    if command -v mail &>/dev/null && [[ -n "${ADMIN_EMAIL:-}" ]]; then
        echo "Update $status: $message" | \
            mail -s "Selextract Update $status" "$ADMIN_EMAIL" || true
    fi
}

# Check for maintenance mode
enable_maintenance_mode() {
    info "Enabling maintenance mode..."
    
    # Create a simple maintenance page
    cat > /tmp/maintenance.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Selextract - Under Maintenance</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        .container { max-width: 600px; margin: 0 auto; }
        h1 { color: #333; }
        p { color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 Maintenance in Progress</h1>
        <p>Selextract is currently being updated to serve you better.</p>
        <p>We'll be back shortly. Thank you for your patience!</p>
        <p><small>If you need immediate assistance, please contact support.</small></p>
    </div>
</body>
</html>
EOF
    
    # You could serve this through nginx during updates
    info "Maintenance mode enabled"
}

disable_maintenance_mode() {
    info "Disabling maintenance mode..."
    rm -f /tmp/maintenance.html
    info "Maintenance mode disabled"
}

# Main update function
main() {
    local start_time=$(date +%s)
    
    info "Starting Selextract Cloud update process..."
    send_notification "STARTED" "Update process initiated"
    
    # Trap to handle failures
    trap 'send_notification "FAILED" "Update failed. Check logs at $LOG_FILE"; rollback' ERR
    
    check_prerequisites
    load_environment
    create_backup
    pull_latest_code
    build_images
    run_migrations
    
    # Choose update strategy
    case "$UPDATE_STRATEGY" in
        "rolling")
            rolling_update
            ;;
        "blue-green")
            blue_green_update
            ;;
        *)
            warning "Unknown update strategy: $UPDATE_STRATEGY, using rolling update"
            rolling_update
            ;;
    esac
    
    update_infrastructure
    
    if verify_update; then
        cleanup
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        success "Update completed successfully in ${duration}s"
        send_notification "SUCCESS" "Update completed in ${duration}s"
        
        # Clean up backup reference
        rm -f /tmp/pre_update_backup_path
    else
        error "Update verification failed"
    fi
}

# Handle command line arguments
case "${1:-}" in
    --strategy)
        UPDATE_STRATEGY="${2:-rolling}"
        main
        ;;
    --rollback)
        rollback
        ;;
    --verify)
        verify_update
        ;;
    --help)
        echo "Usage: $0 [--strategy rolling|blue-green|--rollback|--verify|--help]"
        echo ""
        echo "Options:"
        echo "  --strategy type  Specify update strategy (rolling or blue-green)"
        echo "  --rollback      Rollback to previous version"
        echo "  --verify        Verify current deployment status"
        echo "  --help          Show this help message"
        echo ""
        echo "Environment variables:"
        echo "  UPDATE_STRATEGY    Default update strategy (default: rolling)"
        ;;
    *)
        main
        ;;
esac