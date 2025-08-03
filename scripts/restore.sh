#!/bin/bash

# Selextract Cloud Restore Script
# This script handles disaster recovery from backups

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/restore.log"
BACKUP_BASE_DIR="${BACKUP_DIR:-/opt/backups}"

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

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root for complete system restore"
    fi
}

# List available backups
list_backups() {
    info "Available backups in $BACKUP_BASE_DIR:"
    
    if [[ ! -d "$BACKUP_BASE_DIR" ]]; then
        error "Backup directory not found: $BACKUP_BASE_DIR"
    fi
    
    local backup_dirs=($(find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "20*" | sort -r))
    
    if [[ ${#backup_dirs[@]} -eq 0 ]]; then
        error "No backups found in $BACKUP_BASE_DIR"
    fi
    
    for i in "${!backup_dirs[@]}"; do
        local backup_dir="${backup_dirs[$i]}"
        local backup_name=$(basename "$backup_dir")
        local backup_size=$(du -sh "$backup_dir" 2>/dev/null | cut -f1 || echo "Unknown")
        local backup_date=$(date -d "${backup_name//_/ }" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "Unknown")
        
        echo "  [$((i+1))] $backup_name ($backup_size) - $backup_date"
    done
    
    echo
}

# Select backup interactively
select_backup() {
    list_backups
    
    local backup_dirs=($(find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "20*" | sort -r))
    
    echo -n "Select backup to restore [1-${#backup_dirs[@]}]: "
    read -r selection
    
    if [[ ! "$selection" =~ ^[0-9]+$ ]] || [[ $selection -lt 1 ]] || [[ $selection -gt ${#backup_dirs[@]} ]]; then
        error "Invalid selection"
    fi
    
    RESTORE_BACKUP_DIR="${backup_dirs[$((selection-1))]}"
    info "Selected backup: $(basename "$RESTORE_BACKUP_DIR")"
}

# Verify backup integrity before restore
verify_backup_integrity() {
    local backup_dir="$1"
    
    info "Verifying backup integrity..."
    
    # Check if backup directory exists
    if [[ ! -d "$backup_dir" ]]; then
        error "Backup directory not found: $backup_dir"
    fi
    
    # Check for manifest
    if [[ ! -f "$backup_dir/MANIFEST.txt" ]]; then
        error "Backup manifest not found. This may not be a valid backup."
    fi
    
    # Check critical components
    local critical_components=(
        "database"
        "application"
        "application/.env.prod"
        "application/docker-compose.prod.yml"
    )
    
    for component in "${critical_components[@]}"; do
        if [[ ! -e "$backup_dir/$component" ]]; then
            error "Critical backup component missing: $component"
        fi
    done
    
    # Test database backup integrity
    if [[ -f "$backup_dir/database/selextract_"*".sql.gz" ]]; then
        if ! gunzip -t "$backup_dir/database/selextract_"*".sql.gz"; then
            error "Database backup file is corrupted"
        fi
    fi
    
    success "Backup integrity verification passed"
}

# Stop all services
stop_services() {
    info "Stopping all Selextract services..."
    
    cd "$PROJECT_DIR"
    
    # Stop services gracefully
    if [[ -f "docker-compose.prod.yml" ]]; then
        docker-compose -f docker-compose.prod.yml down --timeout 30 || warning "Some services may not have stopped gracefully"
    fi
    
    # Stop any remaining containers
    local remaining_containers=$(docker ps -q --filter "name=selextract")
    if [[ -n "$remaining_containers" ]]; then
        docker stop $remaining_containers || warning "Could not stop all containers"
    fi
    
    success "Services stopped"
}

# Restore application configuration
restore_application_config() {
    local backup_dir="$1"
    
    info "Restoring application configuration..."
    
    # Backup current configuration if it exists
    if [[ -f "$PROJECT_DIR/.env.prod" ]]; then
        cp "$PROJECT_DIR/.env.prod" "$PROJECT_DIR/.env.prod.backup.$(date +%s)"
        info "Current configuration backed up"
    fi
    
    # Restore environment configuration
    if [[ -f "$backup_dir/application/.env.prod" ]]; then
        cp "$backup_dir/application/.env.prod" "$PROJECT_DIR/"
        success "Environment configuration restored"
    fi
    
    # Restore Docker Compose configuration
    if [[ -f "$backup_dir/application/docker-compose.prod.yml" ]]; then
        cp "$backup_dir/application/docker-compose.prod.yml" "$PROJECT_DIR/"
        success "Docker Compose configuration restored"
    fi
    
    # Restore Nginx configuration
    if [[ -d "$backup_dir/application/nginx" ]]; then
        cp -r "$backup_dir/application/nginx"/* "$PROJECT_DIR/nginx/"
        success "Nginx configuration restored"
    fi
    
    # Restore monitoring configuration
    if [[ -d "$backup_dir/application/monitoring" ]]; then
        cp -r "$backup_dir/application/monitoring"/* "$PROJECT_DIR/monitoring/"
        success "Monitoring configuration restored"
    fi
    
    # Restore scripts
    if [[ -d "$backup_dir/application/scripts" ]]; then
        cp -r "$backup_dir/application/scripts"/* "$PROJECT_DIR/scripts/"
        chmod +x "$PROJECT_DIR/scripts"/*.sh
        success "Scripts restored"
    fi
    
    # Restore SSL certificates
    if [[ -d "$backup_dir/application/ssl" ]]; then
        mkdir -p "/etc/nginx/ssl"
        cp -r "$backup_dir/application/ssl"/* "/etc/nginx/ssl/"
        success "SSL certificates restored"
    fi
}

# Restore system configuration
restore_system_config() {
    local backup_dir="$1"
    
    info "Restoring system configuration..."
    
    if [[ ! -d "$backup_dir/system" ]]; then
        warning "No system configuration found in backup, skipping"
        return 0
    fi
    
    # Restore system files with caution
    local system_files=(
        "/etc/nginx/nginx.conf"
        "/etc/nginx/sites-available"
        "/etc/nginx/sites-enabled"
        "/etc/logrotate.d/selextract"
        "/etc/fail2ban/jail.local"
        "/etc/systemd/system/ssl-renewal.service"
        "/etc/systemd/system/ssl-renewal.timer"
    )
    
    for file in "${system_files[@]}"; do
        local backup_file="$backup_dir/system$file"
        if [[ -e "$backup_file" ]]; then
            # Backup current file if it exists
            if [[ -e "$file" ]]; then
                cp "$file" "$file.backup.$(date +%s)"
            fi
            
            # Restore from backup
            cp -r "$backup_file" "$file"
            info "Restored: $file"
        fi
    done
    
    # Reload systemd if service files were restored
    if [[ -f "$backup_dir/system/etc/systemd/system/ssl-renewal.service" ]]; then
        systemctl daemon-reload
        info "Systemd configuration reloaded"
    fi
    
    success "System configuration restored"
}

# Start infrastructure services
start_infrastructure() {
    info "Starting infrastructure services..."
    
    cd "$PROJECT_DIR"
    
    # Load environment variables
    if [[ -f ".env.prod" ]]; then
        set -a
        source ".env.prod"
        set +a
    fi
    
    # Start database first
    docker-compose -f docker-compose.prod.yml up -d postgres
    
    # Wait for database to be ready
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
        sleep 5
        ((attempt++))
    done
    
    # Start Redis
    docker-compose -f docker-compose.prod.yml up -d redis
    
    # Wait for Redis to be ready
    attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping | grep -q PONG; then
            success "Redis is ready"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            error "Redis failed to start within expected time"
        fi
        
        info "Waiting for Redis... (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    success "Infrastructure services started"
}

# Restore database
restore_database() {
    local backup_dir="$1"
    
    info "Restoring database..."
    
    # Find database backup file
    local db_backup_file=$(find "$backup_dir/database" -name "selextract_*.sql.gz" | head -1)
    
    if [[ -z "$db_backup_file" ]]; then
        error "Database backup file not found"
    fi
    
    # Drop and recreate database
    info "Recreating database..."
    docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T postgres \
        psql -U postgres -c "DROP DATABASE IF EXISTS selextract;"
    
    docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T postgres \
        psql -U postgres -c "CREATE DATABASE selextract;"
    
    # Restore globals if available
    if [[ -f "$backup_dir/database/globals.sql.gz" ]]; then
        info "Restoring database globals..."
        gunzip -c "$backup_dir/database/globals.sql.gz" | \
            docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T postgres \
            psql -U postgres
    fi
    
    # Restore main database
    info "Restoring main database..."
    gunzip -c "$db_backup_file" | \
        docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T postgres \
        psql -U postgres -d selextract
    
    success "Database restored successfully"
}

# Restore Redis data
restore_redis() {
    local backup_dir="$1"
    
    if [[ ! -f "$backup_dir/database/redis_dump.rdb" ]]; then
        warning "Redis backup not found, skipping Redis restore"
        return 0
    fi
    
    info "Restoring Redis data..."
    
    # Stop Redis temporarily
    docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" stop redis
    
    # Copy Redis dump file
    docker cp "$backup_dir/database/redis_dump.rdb" \
        "$(docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" ps -q redis):/data/dump.rdb"
    
    # Start Redis
    docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" start redis
    
    # Wait for Redis to load data
    sleep 5
    
    success "Redis data restored"
}

# Restore application data
restore_application_data() {
    local backup_dir="$1"
    
    info "Restoring application data..."
    
    # Restore results directory
    if [[ -f "$backup_dir/application/results.tar.gz" ]]; then
        info "Restoring results directory..."
        mkdir -p "/opt/selextract"
        tar -xzf "$backup_dir/application/results.tar.gz" -C "/opt/selextract/"
        chown -R 1000:1000 "/opt/selextract/results" || warning "Could not set ownership for results directory"
        success "Results directory restored"
    fi
}

# Start all services
start_all_services() {
    info "Starting all services..."
    
    cd "$PROJECT_DIR"
    
    # Start remaining services
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for API to be ready
    local max_attempts=30
    local attempt=1
    
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
    
    success "All services started successfully"
}

# Verify restore
verify_restore() {
    info "Verifying restore..."
    
    local services=(
        "postgres"
        "redis"
        "api"
        "frontend"
        "nginx"
    )
    
    local failed_services=()
    
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
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "$endpoint" &>/dev/null; then
            info "✓ $endpoint is responding"
        else
            warning "✗ $endpoint is not responding"
        fi
    done
    
    if [[ ${#failed_services[@]} -eq 0 ]]; then
        success "Restore verification passed"
        return 0
    else
        error "Restore verification failed. Failed services: ${failed_services[*]}"
        return 1
    fi
}

# Send restore notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Send to Slack if webhook is configured
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local emoji="✅"
        if [[ "$status" == "FAILED" ]]; then
            emoji="❌"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$emoji Selextract Restore $status: $message\"}" \
            "$SLACK_WEBHOOK_URL" &>/dev/null || true
    fi
    
    # Send email if configured
    if command -v mail &>/dev/null && [[ -n "${ADMIN_EMAIL:-}" ]]; then
        echo "Restore $status: $message" | \
            mail -s "Selextract Restore $status" "$ADMIN_EMAIL" || true
    fi
}

# Main restore function
main() {
    local backup_dir="${1:-}"
    local start_time=$(date +%s)
    
    info "Starting Selextract Cloud restore process..."
    send_notification "STARTED" "Restore process initiated"
    
    # Trap to handle failures
    trap 'send_notification "FAILED" "Restore process failed. Check logs at $LOG_FILE"' ERR
    
    check_root
    
    # Select backup if not provided
    if [[ -z "$backup_dir" ]]; then
        select_backup
        backup_dir="$RESTORE_BACKUP_DIR"
    elif [[ ! -d "$backup_dir" ]]; then
        error "Backup directory not found: $backup_dir"
    fi
    
    # Verify backup before proceeding
    verify_backup_integrity "$backup_dir"
    
    # Confirm restore operation
    warning "This will restore the system from backup: $(basename "$backup_dir")"
    warning "Current data and configuration will be replaced!"
    read -p "Are you sure you want to proceed? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "Restore cancelled by user"
        exit 0
    fi
    
    stop_services
    restore_application_config "$backup_dir"
    restore_system_config "$backup_dir"
    start_infrastructure
    restore_database "$backup_dir"
    restore_redis "$backup_dir"
    restore_application_data "$backup_dir"
    start_all_services
    
    if verify_restore; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        success "Restore completed successfully in ${duration}s"
        send_notification "SUCCESS" "Restore completed in ${duration}s from backup $(basename "$backup_dir")"
        
        info "Post-restore checklist:"
        info "1. Verify all application functionality"
        info "2. Check SSL certificates validity"
        info "3. Test user authentication"
        info "4. Verify monitoring systems"
        info "5. Check log files for any errors"
    else
        error "Restore verification failed"
    fi
}

# Handle command line arguments
case "${1:-}" in
    --list)
        list_backups
        ;;
    --verify)
        if [[ -n "${2:-}" ]]; then
            verify_backup_integrity "$2"
        else
            error "Please specify backup directory to verify"
        fi
        ;;
    --help)
        echo "Usage: $0 [backup_directory|--list|--verify backup_dir|--help]"
        echo ""
        echo "Options:"
        echo "  backup_directory  Restore from specified backup directory"
        echo "  --list           List available backups"
        echo "  --verify dir     Verify backup integrity without restoring"
        echo "  --help           Show this help message"
        echo ""
        echo "If no backup directory is specified, you will be prompted to select one."
        ;;
    *)
        main "$1"
        ;;
esac