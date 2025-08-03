#!/bin/bash

# Selextract Cloud Maintenance Script
# Performs routine maintenance tasks including cleanup, optimization, and health checks

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/maintenance.log"
DRY_RUN="${DRY_RUN:-false}"
MAINTENANCE_TYPE="${1:-all}"

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
check_permissions() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root for complete maintenance operations"
        exit 1
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
        warning "Production environment file not found"
    fi
}

# Pre-maintenance health check
pre_maintenance_check() {
    info "Running pre-maintenance health check..."
    
    cd "$PROJECT_DIR"
    
    # Check if services are running
    if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        error "No services are running. Maintenance requires running services."
        exit 1
    fi
    
    # Check system resources
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $disk_usage -ge 95 ]]; then
        error "Disk usage is critical (${disk_usage}%). Aborting maintenance."
        exit 1
    fi
    
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [[ $memory_usage -ge 95 ]]; then
        warning "Memory usage is high (${memory_usage}%). Maintenance may impact performance."
    fi
    
    success "Pre-maintenance check completed"
}

# Clean up Docker resources
cleanup_docker() {
    info "Cleaning up Docker resources..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] Would clean up Docker resources"
        return 0
    fi
    
    # Remove unused images (keep last 7 days)
    local removed_images=$(docker image prune -af --filter "until=168h" 2>&1 | grep "Total reclaimed space" || echo "0B")
    info "Removed unused images: $removed_images"
    
    # Remove unused containers
    local removed_containers=$(docker container prune -f 2>&1 | grep "Total reclaimed space" || echo "0B")
    info "Removed unused containers: $removed_containers"
    
    # Remove unused networks
    docker network prune -f >/dev/null 2>&1 || warning "Could not prune networks"
    
    # Remove unused volumes (be careful - only remove truly unused volumes)
    local unused_volumes=$(docker volume ls -qf dangling=true)
    if [[ -n "$unused_volumes" ]]; then
        echo "$unused_volumes" | xargs docker volume rm 2>/dev/null || warning "Could not remove some volumes"
        info "Removed unused volumes"
    fi
    
    success "Docker cleanup completed"
}

# Clean up log files
cleanup_logs() {
    info "Cleaning up log files..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] Would clean up old log files"
        return 0
    fi
    
    # Clean up application logs older than 30 days
    if [[ -d "/var/log/selextract" ]]; then
        find /var/log/selextract -name "*.log" -mtime +30 -delete 2>/dev/null || warning "Could not clean some application logs"
        info "Cleaned up old application logs"
    fi
    
    # Clean up old nginx logs
    find /var/log/nginx -name "*.log.*" -mtime +14 -delete 2>/dev/null || warning "Could not clean some nginx logs"
    
    # Clean up old backup logs
    find /var/log -name "*backup*.log" -mtime +30 -delete 2>/dev/null || warning "Could not clean some backup logs"
    
    # Rotate current logs if they're too large
    local large_logs=$(find /var/log -name "*.log" -size +100M 2>/dev/null)
    for log_file in $large_logs; do
        if [[ -f "$log_file" ]]; then
            mv "$log_file" "${log_file}.$(date +%Y%m%d)"
            touch "$log_file"
            info "Rotated large log file: $log_file"
        fi
    done
    
    # Clean up systemd journal
    journalctl --vacuum-time=30d >/dev/null 2>&1 || warning "Could not clean systemd journal"
    journalctl --vacuum-size=500M >/dev/null 2>&1 || warning "Could not limit systemd journal size"
    
    success "Log cleanup completed"
}

# Clean up backup files
cleanup_backups() {
    info "Cleaning up old backup files..."
    
    local backup_retention_days="${BACKUP_RETENTION_DAYS:-30}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        local old_backups=$(find /opt/backups -type d -name "20*" -mtime +$backup_retention_days 2>/dev/null | wc -l)
        info "[DRY RUN] Would remove $old_backups old backup directories"
        return 0
    fi
    
    # Remove backups older than retention period
    local removed_count=0
    while IFS= read -r -d '' backup_dir; do
        rm -rf "$backup_dir"
        ((removed_count++))
    done < <(find /opt/backups -type d -name "20*" -mtime +$backup_retention_days -print0 2>/dev/null)
    
    if [[ $removed_count -gt 0 ]]; then
        info "Removed $removed_count old backup directories"
    else
        info "No old backups to remove"
    fi
    
    # Clean up partial or failed backups
    find /opt/backups -type d -name "20*" -empty -delete 2>/dev/null || true
    
    success "Backup cleanup completed"
}

# Clean up application data
cleanup_application_data() {
    info "Cleaning up application data..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] Would clean up old application data"
        return 0
    fi
    
    # Clean up old task results (older than 90 days)
    if [[ -d "/opt/selextract/results" ]]; then
        find /opt/selextract/results -type f -mtime +90 -delete 2>/dev/null || warning "Could not clean some result files"
        info "Cleaned up old task results"
    fi
    
    # Clean up temporary files
    find /tmp -name "selextract-*" -mtime +1 -delete 2>/dev/null || warning "Could not clean some temp files"
    
    # Clean up old screenshots or downloads if they exist
    if [[ -d "/opt/selextract/downloads" ]]; then
        find /opt/selextract/downloads -type f -mtime +7 -delete 2>/dev/null || warning "Could not clean download files"
    fi
    
    success "Application data cleanup completed"
}

# Optimize database
optimize_database() {
    info "Optimizing database..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] Would optimize database"
        return 0
    fi
    
    cd "$PROJECT_DIR"
    
    # Check if database is accessible
    if ! docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
        warning "Database is not accessible, skipping optimization"
        return 0
    fi
    
    # Run VACUUM ANALYZE
    if docker-compose -f docker-compose.prod.yml exec -T postgres \
        psql -U postgres -d selextract -c "VACUUM ANALYZE;" >/dev/null 2>&1; then
        info "Database vacuum completed"
    else
        warning "Database vacuum failed"
    fi
    
    # Update table statistics
    if docker-compose -f docker-compose.prod.yml exec -T postgres \
        psql -U postgres -d selextract -c "ANALYZE;" >/dev/null 2>&1; then
        info "Database statistics updated"
    else
        warning "Database statistics update failed"
    fi
    
    # Reindex if needed (only for small databases to avoid long locks)
    local db_size=$(docker-compose -f docker-compose.prod.yml exec -T postgres \
        psql -U postgres -d selextract -t -c "SELECT pg_size_pretty(pg_database_size('selextract'));" 2>/dev/null | xargs || echo "unknown")
    
    info "Database size: $db_size"
    
    # Only reindex if database is smaller than 1GB to avoid long locks
    local size_bytes=$(docker-compose -f docker-compose.prod.yml exec -T postgres \
        psql -U postgres -d selextract -t -c "SELECT pg_database_size('selextract');" 2>/dev/null | xargs || echo "0")
    
    if [[ "$size_bytes" -lt 1073741824 ]]; then  # 1GB in bytes
        if docker-compose -f docker-compose.prod.yml exec -T postgres \
            psql -U postgres -d selextract -c "REINDEX DATABASE selextract;" >/dev/null 2>&1; then
            info "Database reindex completed"
        else
            warning "Database reindex failed"
        fi
    else
        info "Database too large for automatic reindex, skipping"
    fi
    
    success "Database optimization completed"
}

# Optimize Redis
optimize_redis() {
    info "Optimizing Redis..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] Would optimize Redis"
        return 0
    fi
    
    cd "$PROJECT_DIR"
    
    # Check if Redis is accessible
    if ! docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping >/dev/null 2>&1; then
        warning "Redis is not accessible, skipping optimization"
        return 0
    fi
    
    # Get Redis info
    local redis_memory=$(docker-compose -f docker-compose.prod.yml exec -T redis \
        redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r' || echo "unknown")
    info "Redis memory usage: $redis_memory"
    
    # Save current state
    docker-compose -f docker-compose.prod.yml exec -T redis redis-cli BGSAVE >/dev/null 2>&1 || \
        warning "Could not trigger Redis background save"
    
    # Clean up expired keys
    docker-compose -f docker-compose.prod.yml exec -T redis redis-cli --scan --pattern "*" | \
        head -1000 | xargs docker-compose -f docker-compose.prod.yml exec -T redis redis-cli TTL >/dev/null 2>&1 || true
    
    success "Redis optimization completed"
}

# Check and repair file permissions
fix_permissions() {
    info "Checking and fixing file permissions..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] Would fix file permissions"
        return 0
    fi
    
    # Fix application directory permissions
    if [[ -d "/opt/selextract" ]]; then
        chown -R deploy:deploy /opt/selextract 2>/dev/null || warning "Could not fix /opt/selextract ownership"
        chmod -R 755 /opt/selextract 2>/dev/null || warning "Could not fix /opt/selextract permissions"
    fi
    
    # Fix backup directory permissions
    if [[ -d "/opt/backups" ]]; then
        chown -R deploy:deploy /opt/backups 2>/dev/null || warning "Could not fix /opt/backups ownership"
        chmod -R 755 /opt/backups 2>/dev/null || warning "Could not fix /opt/backups permissions"
    fi
    
    # Fix log directory permissions
    if [[ -d "/var/log/selextract" ]]; then
        chown -R deploy:deploy /var/log/selextract 2>/dev/null || warning "Could not fix log directory ownership"
        chmod -R 644 /var/log/selextract 2>/dev/null || warning "Could not fix log directory permissions"
    fi
    
    # Ensure script permissions
    chmod +x "$PROJECT_DIR/scripts"/*.sh 2>/dev/null || warning "Could not fix script permissions"
    
    success "Permission fixes completed"
}

# Update system packages
update_system_packages() {
    info "Updating system packages..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] Would update system packages"
        return 0
    fi
    
    # Update package lists
    apt update >/dev/null 2>&1 || warning "Could not update package lists"
    
    # Upgrade security packages only
    DEBIAN_FRONTEND=noninteractive apt-get -y upgrade \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        $(apt list --upgradable 2>/dev/null | grep -i security | cut -d/ -f1) \
        >/dev/null 2>&1 || warning "Could not upgrade security packages"
    
    # Clean up package cache
    apt autoremove -y >/dev/null 2>&1 || warning "Could not remove unnecessary packages"
    apt autoclean >/dev/null 2>&1 || warning "Could not clean package cache"
    
    success "System packages updated"
}

# Generate maintenance report
generate_report() {
    info "Generating maintenance report..."
    
    local report_file="/var/log/maintenance-report-$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$report_file" << EOF
Selextract Cloud Maintenance Report
==================================
Date: $(date)
Maintenance Type: $MAINTENANCE_TYPE
Dry Run: $DRY_RUN

System Status:
- CPU Load: $(uptime | awk -F'load average:' '{print $2}' | xargs)
- Memory Usage: $(free -h | awk 'NR==2{printf "%.1f%%", $3*100/$2}')
- Disk Usage: $(df -h / | awk 'NR==2{print $5}')

Service Status:
$(cd "$PROJECT_DIR" && docker-compose -f docker-compose.prod.yml ps)

Docker Resources:
- Images: $(docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | wc -l) total
- Containers: $(docker ps -a | wc -l) total ($(docker ps | wc -l) running)
- Volumes: $(docker volume ls | wc -l) total

Database Status:
EOF

    # Add database info if accessible
    cd "$PROJECT_DIR"
    if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
        echo "- Database Size: $(docker-compose -f docker-compose.prod.yml exec -T postgres \
            psql -U postgres -d selextract -t -c "SELECT pg_size_pretty(pg_database_size('selextract'));" 2>/dev/null | xargs)" >> "$report_file"
        echo "- Active Connections: $(docker-compose -f docker-compose.prod.yml exec -T postgres \
            psql -U postgres -d selextract -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null | xargs)" >> "$report_file"
    else
        echo "- Database: Not accessible" >> "$report_file"
    fi
    
    # Add Redis info if accessible
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping >/dev/null 2>&1; then
        echo "- Redis Memory: $(docker-compose -f docker-compose.prod.yml exec -T redis \
            redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r')" >> "$report_file"
    else
        echo "- Redis: Not accessible" >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF

Recent Logs (last 10 error entries):
$(journalctl --since="24 hours ago" --priority=err --no-pager -n 10 2>/dev/null || echo "No recent errors")

Maintenance Completed: $(date)
EOF
    
    success "Maintenance report generated: $report_file"
}

# Send maintenance notification
send_notification() {
    local status="$1"
    local summary="$2"
    
    # Send to Slack if webhook is configured
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local emoji="🔧"
        if [[ "$status" == "COMPLETED" ]]; then
            emoji="✅"
        elif [[ "$status" == "FAILED" ]]; then
            emoji="❌"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$emoji Selextract Maintenance $status: $summary\"}" \
            "$SLACK_WEBHOOK_URL" &>/dev/null || true
    fi
    
    # Send email if configured
    if command -v mail &>/dev/null && [[ -n "${ADMIN_EMAIL:-}" ]]; then
        echo "Maintenance $status: $summary" | \
            mail -s "Selextract Maintenance $status" "$ADMIN_EMAIL" || true
    fi
}

# Main maintenance function
main() {
    local start_time=$(date +%s)
    
    info "Starting Selextract Cloud maintenance (type: $MAINTENANCE_TYPE)..."
    if [[ "$DRY_RUN" == "true" ]]; then
        warning "Running in DRY RUN mode - no changes will be made"
    fi
    
    send_notification "STARTED" "Maintenance process initiated (type: $MAINTENANCE_TYPE)"
    
    # Trap to handle failures
    trap 'send_notification "FAILED" "Maintenance process failed. Check logs at $LOG_FILE"' ERR
    
    check_permissions
    load_environment
    pre_maintenance_check
    
    case "$MAINTENANCE_TYPE" in
        "all"|"full")
            cleanup_docker
            cleanup_logs
            cleanup_backups
            cleanup_application_data
            optimize_database
            optimize_redis
            fix_permissions
            update_system_packages
            ;;
        "cleanup")
            cleanup_docker
            cleanup_logs
            cleanup_backups
            cleanup_application_data
            ;;
        "optimize")
            optimize_database
            optimize_redis
            ;;
        "docker")
            cleanup_docker
            ;;
        "logs")
            cleanup_logs
            ;;
        "database")
            optimize_database
            ;;
        "security")
            update_system_packages
            fix_permissions
            ;;
        *)
            error "Unknown maintenance type: $MAINTENANCE_TYPE"
            echo "Valid types: all, cleanup, optimize, docker, logs, database, security"
            exit 1
            ;;
    esac
    
    generate_report
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    success "Maintenance completed successfully in ${duration}s"
    send_notification "COMPLETED" "Maintenance completed in ${duration}s"
}

# Handle command line arguments
case "${1:-all}" in
    --help)
        echo "Usage: $0 [all|cleanup|optimize|docker|logs|database|security] [--dry-run]"
        echo ""
        echo "Maintenance types:"
        echo "  all       - Complete maintenance (default)"
        echo "  cleanup   - Clean up old files and Docker resources"
        echo "  optimize  - Optimize database and Redis"
        echo "  docker    - Clean up Docker resources only"
        echo "  logs      - Clean up log files only"
        echo "  database  - Optimize database only"
        echo "  security  - Update packages and fix permissions"
        echo ""
        echo "Options:"
        echo "  --dry-run - Show what would be done without making changes"
        ;;
    --dry-run)
        DRY_RUN="true"
        main "all"
        ;;
    *)
        if [[ "${2:-}" == "--dry-run" ]]; then
            DRY_RUN="true"
        fi
        main "$1"
        ;;
esac