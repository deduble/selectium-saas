#!/bin/bash

# Selextract Cloud Health Check Script
# This script performs comprehensive health checks on all system components

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/health-check.log"
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-30}"
CRITICAL_THRESHOLD="${CRITICAL_THRESHOLD:-90}"
WARNING_THRESHOLD="${WARNING_THRESHOLD:-80}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Status tracking
OVERALL_STATUS="HEALTHY"
FAILED_CHECKS=()
WARNING_CHECKS=()
CRITICAL_CHECKS=()

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    log "ERROR: $1"
    OVERALL_STATUS="CRITICAL"
    FAILED_CHECKS+=("$1")
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
    log "WARNING: $1"
    if [[ "$OVERALL_STATUS" == "HEALTHY" ]]; then
        OVERALL_STATUS="WARNING"
    fi
    WARNING_CHECKS+=("$1")
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    log "INFO: $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    log "SUCCESS: $1"
}

critical() {
    echo -e "${RED}[CRITICAL]${NC} $1" >&2
    log "CRITICAL: $1"
    OVERALL_STATUS="CRITICAL"
    CRITICAL_CHECKS+=("$1")
}

# Load environment variables
load_environment() {
    if [[ -f "$PROJECT_DIR/.env.prod" ]]; then
        set -a
        source "$PROJECT_DIR/.env.prod"
        set +a
    else
        warning "Production environment file not found"
    fi
}

# Check Docker daemon
check_docker() {
    info "Checking Docker daemon..."
    
    if ! command -v docker &> /dev/null; then
        critical "Docker is not installed"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        critical "Docker daemon is not running"
        return 1
    fi
    
    # Check Docker version
    local docker_version=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")
    info "Docker version: $docker_version"
    
    success "Docker daemon is healthy"
    return 0
}

# Check container status
check_containers() {
    info "Checking container status..."
    
    cd "$PROJECT_DIR"
    
    local required_services=(
        "postgres"
        "redis"
        "api"
        "worker"
        "frontend"
        "nginx"
        "prometheus"
        "grafana"
    )
    
    local container_issues=0
    
    for service in "${required_services[@]}"; do
        local status=$(docker-compose -f docker-compose.prod.yml ps -q $service | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null || echo "not_found")
        
        case "$status" in
            "running")
                success "✓ $service container is running"
                ;;
            "exited"|"dead")
                error "✗ $service container has stopped"
                ((container_issues++))
                ;;
            "restarting")
                warning "⚠ $service container is restarting"
                ((container_issues++))
                ;;
            "not_found")
                error "✗ $service container not found"
                ((container_issues++))
                ;;
            *)
                warning "? $service container status unknown: $status"
                ((container_issues++))
                ;;
        esac
    done
    
    if [[ $container_issues -eq 0 ]]; then
        success "All containers are healthy"
        return 0
    else
        error "$container_issues container issues detected"
        return 1
    fi
}

# Check service health endpoints
check_service_endpoints() {
    info "Checking service health endpoints..."
    
    local endpoints=(
        "http://localhost:8000/health:API"
        "http://localhost:3000:Frontend"
        "http://localhost:9090/-/healthy:Prometheus"
        "http://localhost:3001/api/health:Grafana"
    )
    
    local endpoint_issues=0
    
    for endpoint_info in "${endpoints[@]}"; do
        local endpoint="${endpoint_info%:*}"
        local service="${endpoint_info#*:}"
        
        if curl -f -s --max-time "$HEALTH_CHECK_TIMEOUT" "$endpoint" > /dev/null 2>&1; then
            success "✓ $service endpoint is responding"
        else
            error "✗ $service endpoint is not responding: $endpoint"
            ((endpoint_issues++))
        fi
    done
    
    if [[ $endpoint_issues -eq 0 ]]; then
        success "All service endpoints are healthy"
        return 0
    else
        error "$endpoint_issues endpoint issues detected"
        return 1
    fi
}

# Check database connectivity
check_database() {
    info "Checking database connectivity..."
    
    cd "$PROJECT_DIR"
    
    # Check PostgreSQL
    if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        success "✓ PostgreSQL is accepting connections"
        
        # Check database size and connections
        local db_size=$(docker-compose -f docker-compose.prod.yml exec -T postgres \
            psql -U postgres -d selextract -t -c "SELECT pg_size_pretty(pg_database_size('selextract'));" 2>/dev/null | xargs || echo "unknown")
        local active_connections=$(docker-compose -f docker-compose.prod.yml exec -T postgres \
            psql -U postgres -d selextract -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null | xargs || echo "unknown")
        
        info "Database size: $db_size"
        info "Active connections: $active_connections"
        
        # Check for long-running queries
        local long_queries=$(docker-compose -f docker-compose.prod.yml exec -T postgres \
            psql -U postgres -d selextract -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '5 minutes';" 2>/dev/null | xargs || echo "0")
        
        if [[ "$long_queries" -gt 0 ]]; then
            warning "$long_queries long-running database queries detected"
        fi
    else
        error "PostgreSQL is not accepting connections"
        return 1
    fi
    
    # Check Redis
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
        success "✓ Redis is responding"
        
        # Check Redis memory usage
        local redis_memory=$(docker-compose -f docker-compose.prod.yml exec -T redis \
            redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r' || echo "unknown")
        info "Redis memory usage: $redis_memory"
        
        # Check Redis connected clients
        local redis_clients=$(docker-compose -f docker-compose.prod.yml exec -T redis \
            redis-cli info clients 2>/dev/null | grep connected_clients | cut -d: -f2 | tr -d '\r' || echo "unknown")
        info "Redis connected clients: $redis_clients"
    else
        error "Redis is not responding"
        return 1
    fi
    
    return 0
}

# Check system resources
check_system_resources() {
    info "Checking system resources..."
    
    # Check disk usage
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $disk_usage -ge $CRITICAL_THRESHOLD ]]; then
        critical "Disk usage is critical: ${disk_usage}%"
    elif [[ $disk_usage -ge $WARNING_THRESHOLD ]]; then
        warning "Disk usage is high: ${disk_usage}%"
    else
        success "✓ Disk usage is normal: ${disk_usage}%"
    fi
    
    # Check memory usage
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [[ $memory_usage -ge $CRITICAL_THRESHOLD ]]; then
        critical "Memory usage is critical: ${memory_usage}%"
    elif [[ $memory_usage -ge $WARNING_THRESHOLD ]]; then
        warning "Memory usage is high: ${memory_usage}%"
    else
        success "✓ Memory usage is normal: ${memory_usage}%"
    fi
    
    # Check CPU load
    local cpu_load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_cores=$(nproc)
    local cpu_load_percent=$(echo "$cpu_load $cpu_cores" | awk '{printf "%.0f", ($1/$2)*100}')
    
    if [[ $cpu_load_percent -ge $CRITICAL_THRESHOLD ]]; then
        critical "CPU load is critical: ${cpu_load_percent}% (${cpu_load} on ${cpu_cores} cores)"
    elif [[ $cpu_load_percent -ge $WARNING_THRESHOLD ]]; then
        warning "CPU load is high: ${cpu_load_percent}% (${cpu_load} on ${cpu_cores} cores)"
    else
        success "✓ CPU load is normal: ${cpu_load_percent}% (${cpu_load} on ${cpu_cores} cores)"
    fi
    
    # Check inodes
    local inode_usage=$(df -i / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $inode_usage -ge $CRITICAL_THRESHOLD ]]; then
        critical "Inode usage is critical: ${inode_usage}%"
    elif [[ $inode_usage -ge $WARNING_THRESHOLD ]]; then
        warning "Inode usage is high: ${inode_usage}%"
    else
        success "✓ Inode usage is normal: ${inode_usage}%"
    fi
}

# Check SSL certificates
check_ssl_certificates() {
    info "Checking SSL certificates..."
    
    local cert_file="/etc/nginx/ssl/selextract.com/fullchain.pem"
    
    if [[ ! -f "$cert_file" ]]; then
        error "SSL certificate file not found: $cert_file"
        return 1
    fi
    
    # Check certificate validity
    local expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate 2>/dev/null | cut -d= -f2)
    local expiry_timestamp=$(date -d "$expiry_date" +%s 2>/dev/null || echo "0")
    local current_timestamp=$(date +%s)
    local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
    
    if [[ $days_until_expiry -le 7 ]]; then
        critical "SSL certificate expires in $days_until_expiry days"
    elif [[ $days_until_expiry -le 30 ]]; then
        warning "SSL certificate expires in $days_until_expiry days"
    else
        success "✓ SSL certificate is valid (expires in $days_until_expiry days)"
    fi
    
    # Check certificate chain
    if openssl verify -CAfile "$cert_file" "$cert_file" > /dev/null 2>&1; then
        success "✓ SSL certificate chain is valid"
    else
        warning "SSL certificate chain validation failed"
    fi
}

# Check backup status
check_backup_status() {
    info "Checking backup status..."
    
    local backup_dir="/opt/backups"
    
    if [[ ! -d "$backup_dir" ]]; then
        error "Backup directory not found: $backup_dir"
        return 1
    fi
    
    # Find most recent backup
    local latest_backup=$(find "$backup_dir" -maxdepth 1 -type d -name "20*" | sort | tail -1)
    
    if [[ -z "$latest_backup" ]]; then
        error "No backups found in $backup_dir"
        return 1
    fi
    
    local backup_age=$(( ($(date +%s) - $(stat -c %Y "$latest_backup")) / 86400 ))
    
    if [[ $backup_age -gt 7 ]]; then
        critical "Latest backup is $backup_age days old"
    elif [[ $backup_age -gt 3 ]]; then
        warning "Latest backup is $backup_age days old"
    else
        success "✓ Latest backup is $backup_age days old"
    fi
    
    # Check backup integrity
    if [[ -f "$latest_backup/MANIFEST.txt" ]]; then
        success "✓ Backup manifest found"
    else
        warning "Backup manifest missing from latest backup"
    fi
}

# Check log files for errors
check_logs() {
    info "Checking application logs for errors..."
    
    local log_dirs=(
        "/var/log/selextract"
        "/opt/selextract/logs"
        "/var/log/nginx"
    )
    
    local error_count=0
    
    for log_dir in "${log_dirs[@]}"; do
        if [[ -d "$log_dir" ]]; then
            # Check for recent errors (last 24 hours)
            local recent_errors=$(find "$log_dir" -name "*.log" -mtime -1 -exec grep -l -i "error\|critical\|fatal" {} \; 2>/dev/null | wc -l)
            
            if [[ $recent_errors -gt 0 ]]; then
                warning "$recent_errors log files with recent errors found in $log_dir"
                ((error_count++))
            fi
        fi
    done
    
    # Check systemd journal for recent errors
    if command -v journalctl &>/dev/null; then
        local journal_errors=$(journalctl --since="24 hours ago" --priority=err --no-pager --quiet | wc -l)
        if [[ $journal_errors -gt 10 ]]; then
            warning "$journal_errors error entries in systemd journal (last 24h)"
            ((error_count++))
        fi
    fi
    
    if [[ $error_count -eq 0 ]]; then
        success "✓ No significant errors found in logs"
    fi
}

# Check monitoring systems
check_monitoring() {
    info "Checking monitoring systems..."
    
    cd "$PROJECT_DIR"
    
    # Check Prometheus targets
    if curl -s "http://localhost:9090/api/v1/targets" | grep -q '"health":"up"'; then
        success "✓ Prometheus targets are healthy"
    else
        warning "Some Prometheus targets may be down"
    fi
    
    # Check Grafana
    if curl -f -s "http://localhost:3001/api/health" > /dev/null 2>&1; then
        success "✓ Grafana is responding"
    else
        warning "Grafana health check failed"
    fi
    
    # Check if alerts are firing
    local firing_alerts=$(curl -s "http://localhost:9090/api/v1/alerts" 2>/dev/null | grep -o '"state":"firing"' | wc -l || echo "0")
    if [[ $firing_alerts -gt 0 ]]; then
        warning "$firing_alerts alerts are currently firing"
    else
        success "✓ No alerts are currently firing"
    fi
}

# Check network connectivity
check_network() {
    info "Checking network connectivity..."
    
    # Check external connectivity
    if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
        success "✓ External network connectivity is working"
    else
        error "External network connectivity failed"
    fi
    
    # Check DNS resolution
    if nslookup google.com > /dev/null 2>&1; then
        success "✓ DNS resolution is working"
    else
        error "DNS resolution failed"
    fi
    
    # Check if required ports are listening
    local required_ports=(80 443 5432 6379 8000 3000 9090 3001)
    local port_issues=0
    
    for port in "${required_ports[@]}"; do
        if ss -tlnp | grep -q ":$port "; then
            success "✓ Port $port is listening"
        else
            error "Port $port is not listening"
            ((port_issues++))
        fi
    done
    
    return $port_issues
}

# Check security status
check_security() {
    info "Checking security status..."
    
    # Check if fail2ban is running
    if systemctl is-active --quiet fail2ban 2>/dev/null; then
        success "✓ Fail2ban is running"
        
        # Check for recent bans
        local recent_bans=$(fail2ban-client status 2>/dev/null | grep -o "Currently banned:[[:space:]]*[0-9]*" | awk '{print $3}' || echo "0")
        if [[ $recent_bans -gt 0 ]]; then
            info "$recent_bans IPs are currently banned by fail2ban"
        fi
    else
        warning "Fail2ban is not running"
    fi
    
    # Check UFW status
    if command -v ufw &>/dev/null; then
        if ufw status | grep -q "Status: active"; then
            success "✓ UFW firewall is active"
        else
            warning "UFW firewall is not active"
        fi
    fi
    
    # Check for unusual login attempts
    local failed_logins=$(journalctl --since="24 hours ago" | grep "Failed password" | wc -l 2>/dev/null || echo "0")
    if [[ $failed_logins -gt 50 ]]; then
        warning "$failed_logins failed login attempts in the last 24 hours"
    fi
}

# Generate health report
generate_report() {
    echo
    echo "=================================="
    echo "Selextract Cloud Health Report"
    echo "=================================="
    echo "Timestamp: $(date)"
    echo "Overall Status: $OVERALL_STATUS"
    echo "=================================="
    
    if [[ ${#CRITICAL_CHECKS[@]} -gt 0 ]]; then
        echo
        echo "CRITICAL ISSUES:"
        for issue in "${CRITICAL_CHECKS[@]}"; do
            echo "  ❌ $issue"
        done
    fi
    
    if [[ ${#FAILED_CHECKS[@]} -gt 0 ]]; then
        echo
        echo "FAILED CHECKS:"
        for check in "${FAILED_CHECKS[@]}"; do
            echo "  ❌ $check"
        done
    fi
    
    if [[ ${#WARNING_CHECKS[@]} -gt 0 ]]; then
        echo
        echo "WARNINGS:"
        for warning in "${WARNING_CHECKS[@]}"; do
            echo "  ⚠️  $warning"
        done
    fi
    
    echo
    echo "Health check completed at $(date)"
    echo "=================================="
}

# Send health notification
send_notification() {
    local status="$1"
    local summary="$2"
    
    # Only send notifications for critical issues or if explicitly requested
    if [[ "$status" == "CRITICAL" ]] || [[ "${FORCE_NOTIFICATION:-false}" == "true" ]]; then
        # Send to Slack if webhook is configured
        if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
            local emoji="❌"
            if [[ "$status" == "HEALTHY" ]]; then
                emoji="✅"
            elif [[ "$status" == "WARNING" ]]; then
                emoji="⚠️"
            fi
            
            curl -X POST -H 'Content-type: application/json' \
                --data "{\"text\":\"$emoji Selextract Health Check $status: $summary\"}" \
                "$SLACK_WEBHOOK_URL" &>/dev/null || true
        fi
        
        # Send email if configured
        if command -v mail &>/dev/null && [[ -n "${ADMIN_EMAIL:-}" ]]; then
            echo "Health Check $status: $summary" | \
                mail -s "Selextract Health Alert - $status" "$ADMIN_EMAIL" || true
        fi
    fi
}

# Main health check function
main() {
    info "Starting Selextract Cloud health check..."
    
    load_environment
    
    # Run all health checks
    check_docker || true
    check_containers || true
    check_service_endpoints || true
    check_database || true
    check_system_resources || true
    check_ssl_certificates || true
    check_backup_status || true
    check_logs || true
    check_monitoring || true
    check_network || true
    check_security || true
    
    # Generate and display report
    generate_report
    
    # Send notifications if needed
    local summary="Overall status: $OVERALL_STATUS"
    if [[ ${#CRITICAL_CHECKS[@]} -gt 0 ]]; then
        summary="$summary, ${#CRITICAL_CHECKS[@]} critical issues"
    fi
    if [[ ${#WARNING_CHECKS[@]} -gt 0 ]]; then
        summary="$summary, ${#WARNING_CHECKS[@]} warnings"
    fi
    
    send_notification "$OVERALL_STATUS" "$summary"
    
    # Exit with appropriate code
    case "$OVERALL_STATUS" in
        "HEALTHY")
            exit 0
            ;;
        "WARNING")
            exit 1
            ;;
        "CRITICAL")
            exit 2
            ;;
        *)
            exit 3
            ;;
    esac
}

# Handle command line arguments
case "${1:-}" in
    --silent)
        exec > /dev/null 2>&1
        main
        ;;
    --notify)
        FORCE_NOTIFICATION="true"
        main
        ;;
    --critical-only)
        # Only run critical checks
        info "Running critical health checks only..."
        load_environment
        check_docker || true
        check_containers || true
        check_service_endpoints || true
        check_database || true
        generate_report
        ;;
    --help)
        echo "Usage: $0 [--silent|--notify|--critical-only|--help]"
        echo ""
        echo "Options:"
        echo "  --silent        Run health check silently (no output)"
        echo "  --notify        Force send notifications regardless of status"
        echo "  --critical-only Run only critical health checks"
        echo "  --help          Show this help message"
        echo ""
        echo "Exit codes:"
        echo "  0 - Healthy"
        echo "  1 - Warning"
        echo "  2 - Critical"
        echo "  3 - Unknown"
        ;;
    *)
        main
        ;;
esac