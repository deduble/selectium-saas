#!/bin/bash

# Selextract Cloud Backup Script
# This script creates comprehensive backups of the entire system

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_BASE_DIR="${BACKUP_DIR:-/opt/backups}"
LOG_FILE="/var/log/backup.log"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
REMOTE_BACKUP_ENABLED="${REMOTE_BACKUP_ENABLED:-false}"

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
        error "This script must be run as root for complete system backup"
    fi
}

# Load environment variables
load_environment() {
    if [[ -f "$PROJECT_DIR/.env.prod" ]]; then
        set -a
        source "$PROJECT_DIR/.env.prod"
        set +a
        info "Environment variables loaded"
    else
        warning "Production environment file not found, using defaults"
    fi
}

# Create backup directory structure
setup_backup_directory() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="$BACKUP_BASE_DIR/$timestamp"
    
    mkdir -p "$BACKUP_DIR"/{database,application,system,logs}
    
    info "Backup directory created: $BACKUP_DIR"
    echo "$BACKUP_DIR" > /tmp/current_backup_path
}

# Backup PostgreSQL database
backup_database() {
    info "Backing up PostgreSQL database..."
    
    local db_backup_file="$BACKUP_DIR/database/selextract_$(date +%Y%m%d_%H%M%S).sql"
    
    # Check if database container is running
    if ! docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" ps | grep -q postgres.*Up; then
        warning "PostgreSQL container is not running, skipping database backup"
        return 0
    fi
    
    # Create database backup using pg_dump
    if docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T postgres \
        pg_dump -U postgres -d selextract --verbose --clean --no-owner --no-privileges \
        > "$db_backup_file"; then
        
        # Compress the backup
        gzip "$db_backup_file"
        
        # Create schema-only backup for faster recovery testing
        docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T postgres \
            pg_dump -U postgres -d selextract --schema-only \
            > "$BACKUP_DIR/database/schema_only.sql"
        gzip "$BACKUP_DIR/database/schema_only.sql"
        
        # Create globals backup (users, roles, etc.)
        docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T postgres \
            pg_dumpall --globals-only --clean \
            > "$BACKUP_DIR/database/globals.sql"
        gzip "$BACKUP_DIR/database/globals.sql"
        
        success "Database backup completed: ${db_backup_file}.gz"
    else
        error "Database backup failed"
    fi
}

# Backup Redis data
backup_redis() {
    info "Backing up Redis data..."
    
    if ! docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" ps | grep -q redis.*Up; then
        warning "Redis container is not running, skipping Redis backup"
        return 0
    fi
    
    # Create Redis backup using BGSAVE
    docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T redis \
        redis-cli BGSAVE
    
    # Wait for backup to complete
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        local last_save=$(docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T redis \
            redis-cli LASTSAVE)
        
        sleep 1
        
        local current_save=$(docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T redis \
            redis-cli LASTSAVE)
        
        if [[ "$current_save" != "$last_save" ]]; then
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            warning "Redis backup may not have completed properly"
        fi
        
        ((attempt++))
    done
    
    # Copy Redis dump file
    docker cp "$(docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" ps -q redis):/data/dump.rdb" \
        "$BACKUP_DIR/database/redis_dump.rdb"
    
    success "Redis backup completed"
}

# Backup application files and configuration
backup_application() {
    info "Backing up application files and configuration..."
    
    # Backup environment configuration
    if [[ -f "$PROJECT_DIR/.env.prod" ]]; then
        cp "$PROJECT_DIR/.env.prod" "$BACKUP_DIR/application/"
        success "Environment configuration backed up"
    fi
    
    # Backup Docker Compose configurations
    cp "$PROJECT_DIR/docker-compose.prod.yml" "$BACKUP_DIR/application/"
    if [[ -f "$PROJECT_DIR/docker-compose.yml" ]]; then
        cp "$PROJECT_DIR/docker-compose.yml" "$BACKUP_DIR/application/"
    fi
    
    # Backup Nginx configuration
    if [[ -d "$PROJECT_DIR/nginx" ]]; then
        cp -r "$PROJECT_DIR/nginx" "$BACKUP_DIR/application/"
        success "Nginx configuration backed up"
    fi
    
    # Backup monitoring configuration
    if [[ -d "$PROJECT_DIR/monitoring" ]]; then
        cp -r "$PROJECT_DIR/monitoring" "$BACKUP_DIR/application/"
        success "Monitoring configuration backed up"
    fi
    
    # Backup scripts
    if [[ -d "$PROJECT_DIR/scripts" ]]; then
        cp -r "$PROJECT_DIR/scripts" "$BACKUP_DIR/application/"
        success "Scripts backed up"
    fi
    
    # Backup results directory
    if [[ -d "/opt/selextract/results" ]]; then
        info "Backing up results directory..."
        tar -czf "$BACKUP_DIR/application/results.tar.gz" -C "/opt/selextract" results/
        success "Results directory backed up"
    fi
    
    # Backup SSL certificates
    if [[ -d "/etc/nginx/ssl" ]]; then
        cp -r "/etc/nginx/ssl" "$BACKUP_DIR/application/"
        success "SSL certificates backed up"
    fi
}

# Backup system configuration
backup_system() {
    info "Backing up system configuration..."
    
    local system_files=(
        "/etc/nginx/nginx.conf"
        "/etc/nginx/sites-available"
        "/etc/nginx/sites-enabled"
        "/etc/crontab"
        "/etc/logrotate.d/selextract"
        "/etc/fail2ban/jail.local"
        "/etc/ssh/sshd_config"
        "/etc/ufw"
        "/etc/systemd/system/ssl-renewal.service"
        "/etc/systemd/system/ssl-renewal.timer"
    )
    
    for file in "${system_files[@]}"; do
        if [[ -e "$file" ]]; then
            local dirname=$(dirname "$file")
            mkdir -p "$BACKUP_DIR/system$dirname"
            cp -r "$file" "$BACKUP_DIR/system$file"
        fi
    done
    
    # Backup system package list
    if command -v dpkg &>/dev/null; then
        dpkg --get-selections > "$BACKUP_DIR/system/packages_dpkg.txt"
    fi
    
    if command -v rpm &>/dev/null; then
        rpm -qa > "$BACKUP_DIR/system/packages_rpm.txt"
    fi
    
    # Backup crontab
    crontab -l > "$BACKUP_DIR/system/crontab.txt" 2>/dev/null || echo "No crontab found"
    
    success "System configuration backed up"
}

# Backup logs
backup_logs() {
    info "Backing up application logs..."
    
    local log_dirs=(
        "/var/log/selextract"
        "/var/log/nginx"
        "/opt/selextract/logs"
    )
    
    for log_dir in "${log_dirs[@]}"; do
        if [[ -d "$log_dir" ]]; then
            local basename=$(basename "$log_dir")
            tar -czf "$BACKUP_DIR/logs/${basename}_logs.tar.gz" -C "$(dirname "$log_dir")" "$basename/"
            info "Backed up logs from $log_dir"
        fi
    done
    
    # Backup recent system logs
    journalctl --since="7 days ago" --output=export > "$BACKUP_DIR/logs/journal_7days.export" || \
        warning "Could not backup journal logs"
    
    success "Logs backup completed"
}

# Create backup manifest
create_backup_manifest() {
    info "Creating backup manifest..."
    
    local manifest_file="$BACKUP_DIR/MANIFEST.txt"
    
    cat > "$manifest_file" << EOF
Selextract Cloud Backup Manifest
================================
Backup Date: $(date)
Backup Directory: $BACKUP_DIR
Server Hostname: $(hostname)
Server IP: $(hostname -I | awk '{print $1}')
Backup Script Version: 1.0

Contents:
- database/: PostgreSQL and Redis data backups
- application/: Application configuration and data
- system/: System configuration files
- logs/: Application and system logs

Files in backup:
EOF
    
    # List all files in backup with sizes
    find "$BACKUP_DIR" -type f -exec ls -lh {} \; | \
        awk '{print $9 " (" $5 ")"}' | \
        sort >> "$manifest_file"
    
    # Calculate total backup size
    local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    echo "" >> "$manifest_file"
    echo "Total Backup Size: $total_size" >> "$manifest_file"
    
    success "Backup manifest created"
}

# Verify backup integrity
verify_backup() {
    info "Verifying backup integrity..."
    
    local errors=0
    
    # Check if critical files exist
    local critical_files=(
        "$BACKUP_DIR/database"
        "$BACKUP_DIR/application/.env.prod"
        "$BACKUP_DIR/application/docker-compose.prod.yml"
        "$BACKUP_DIR/MANIFEST.txt"
    )
    
    for file in "${critical_files[@]}"; do
        if [[ ! -e "$file" ]]; then
            error "Critical backup file missing: $file"
            ((errors++))
        fi
    done
    
    # Test database backup if it exists
    if [[ -f "$BACKUP_DIR/database/selextract_"*".sql.gz" ]]; then
        if gunzip -t "$BACKUP_DIR/database/selextract_"*".sql.gz"; then
            info "Database backup file integrity verified"
        else
            error "Database backup file is corrupted"
            ((errors++))
        fi
    fi
    
    if [[ $errors -eq 0 ]]; then
        success "Backup integrity verification passed"
        return 0
    else
        error "Backup integrity verification failed with $errors errors"
        return 1
    fi
}

# Upload backup to remote storage
upload_to_remote() {
    if [[ "$REMOTE_BACKUP_ENABLED" != "true" ]]; then
        info "Remote backup is disabled, skipping upload"
        return 0
    fi
    
    info "Uploading backup to remote storage..."
    
    # Create compressed archive for upload
    local archive_name="selextract_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    local archive_path="/tmp/$archive_name"
    
    tar -czf "$archive_path" -C "$BACKUP_BASE_DIR" "$(basename "$BACKUP_DIR")"
    
    # Upload using configured method
    if [[ -n "${AWS_S3_BUCKET:-}" ]]; then
        # AWS S3 upload
        if command -v aws &>/dev/null; then
            aws s3 cp "$archive_path" "s3://$AWS_S3_BUCKET/backups/$archive_name"
            success "Backup uploaded to AWS S3"
        else
            warning "AWS CLI not found, skipping S3 upload"
        fi
    elif [[ -n "${BACKBLAZE_BUCKET:-}" ]]; then
        # Backblaze B2 upload
        if command -v b2 &>/dev/null; then
            b2 upload-file "$BACKBLAZE_BUCKET" "$archive_path" "backups/$archive_name"
            success "Backup uploaded to Backblaze B2"
        else
            warning "Backblaze B2 CLI not found, skipping upload"
        fi
    elif [[ -n "${RSYNC_DESTINATION:-}" ]]; then
        # Rsync upload
        rsync -avz --progress "$archive_path" "$RSYNC_DESTINATION/"
        success "Backup uploaded via rsync"
    else
        info "No remote backup destination configured"
    fi
    
    # Clean up local archive
    rm -f "$archive_path"
}

# Clean up old backups
cleanup_old_backups() {
    info "Cleaning up backups older than $RETENTION_DAYS days..."
    
    if [[ -d "$BACKUP_BASE_DIR" ]]; then
        # Find and remove old backup directories
        find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "20*" -mtime +$RETENTION_DAYS -exec rm -rf {} \;
        
        # Count remaining backups
        local backup_count=$(find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "20*" | wc -l)
        info "Cleanup completed. $backup_count backups remaining"
    fi
}

# Send backup notification
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
            --data "{\"text\":\"$emoji Selextract Backup $status: $message\"}" \
            "$SLACK_WEBHOOK_URL" &>/dev/null || true
    fi
    
    # Send email if configured
    if command -v mail &>/dev/null && [[ -n "${ADMIN_EMAIL:-}" ]]; then
        echo "Backup $status: $message" | \
            mail -s "Selextract Backup $status" "$ADMIN_EMAIL" || true
    fi
}

# Main backup function
main() {
    local start_time=$(date +%s)
    
    info "Starting Selextract Cloud backup..."
    send_notification "STARTED" "Backup process initiated"
    
    # Trap to handle failures
    trap 'send_notification "FAILED" "Backup process failed. Check logs at $LOG_FILE"' ERR
    
    check_root
    load_environment
    setup_backup_directory
    backup_database
    backup_redis
    backup_application
    backup_system
    backup_logs
    create_backup_manifest
    
    if verify_backup; then
        upload_to_remote
        cleanup_old_backups
        
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local backup_size=$(du -sh "$BACKUP_DIR" | cut -f1)
        
        success "Backup completed successfully in ${duration}s"
        success "Backup location: $BACKUP_DIR"
        success "Backup size: $backup_size"
        
        send_notification "SUCCESS" "Backup completed in ${duration}s, size: $backup_size"
    else
        error "Backup verification failed"
    fi
}

# Handle command line arguments
case "${1:-}" in
    --database-only)
        info "Creating database-only backup..."
        check_root
        load_environment
        setup_backup_directory
        backup_database
        backup_redis
        create_backup_manifest
        verify_backup
        ;;
    --no-remote)
        REMOTE_BACKUP_ENABLED="false"
        main
        ;;
    --verify)
        if [[ -n "${2:-}" ]]; then
            BACKUP_DIR="$2"
            verify_backup
        else
            error "Please specify backup directory to verify"
        fi
        ;;
    --help)
        echo "Usage: $0 [--database-only|--no-remote|--verify backup_dir|--help]"
        echo ""
        echo "Options:"
        echo "  --database-only   Create backup of database only"
        echo "  --no-remote      Skip remote backup upload"
        echo "  --verify dir     Verify integrity of specified backup"
        echo "  --help           Show this help message"
        ;;
    *)
        main
        ;;
esac