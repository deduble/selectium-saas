#!/bin/bash

# Selextract Cloud System Status Script
# Provides comprehensive system status overview for operations

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_FORMAT="${OUTPUT_FORMAT:-console}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Display functions
print_header() {
    if [[ "$OUTPUT_FORMAT" == "console" ]]; then
        echo -e "${CYAN}================================${NC}"
        echo -e "${CYAN}$1${NC}"
        echo -e "${CYAN}================================${NC}"
    else
        echo "=== $1 ==="
    fi
}

print_section() {
    if [[ "$OUTPUT_FORMAT" == "console" ]]; then
        echo -e "\n${BLUE}$1${NC}"
        echo -e "${BLUE}$(printf '%*s' ${#1} '' | tr ' ' '-')${NC}"
    else
        echo ""
        echo "-- $1 --"
    fi
}

print_status() {
    local status="$1"
    local message="$2"
    
    if [[ "$OUTPUT_FORMAT" == "console" ]]; then
        case "$status" in
            "OK"|"HEALTHY")
                echo -e "  ${GREEN}✓${NC} $message"
                ;;
            "WARNING")
                echo -e "  ${YELLOW}⚠${NC} $message"
                ;;
            "ERROR"|"CRITICAL")
                echo -e "  ${RED}✗${NC} $message"
                ;;
            *)
                echo -e "  ${BLUE}•${NC} $message"
                ;;
        esac
    else
        echo "  [$status] $message"
    fi
}

# Load environment variables
load_environment() {
    if [[ -f "$PROJECT_DIR/.env.prod" ]]; then
        set -a
        source "$PROJECT_DIR/.env.prod"
        set +a
    fi
}

# System information
show_system_info() {
    print_section "System Information"
    
    print_status "INFO" "Hostname: $(hostname)"
    print_status "INFO" "Uptime: $(uptime -p)"
    print_status "INFO" "Load Average: $(uptime | awk -F'load average:' '{print $2}' | xargs)"
    print_status "INFO" "Kernel: $(uname -r)"
    print_status "INFO" "OS: $(lsb_release -d | cut -f2 2>/dev/null || echo "Unknown")"
    print_status "INFO" "Architecture: $(uname -m)"
    
    # CPU information
    local cpu_cores=$(nproc)
    local cpu_model=$(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs 2>/dev/null || echo "Unknown")
    print_status "INFO" "CPU: $cpu_model ($cpu_cores cores)"
    
    # Memory information
    local total_mem=$(free -h | awk 'NR==2{print $2}')
    local used_mem=$(free -h | awk 'NR==2{print $3}')
    local mem_percent=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
    print_status "INFO" "Memory: $used_mem / $total_mem (${mem_percent}%)"
}

# Resource usage
show_resource_usage() {
    print_section "Resource Usage"
    
    # CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        print_status "WARNING" "CPU Usage: ${cpu_usage}% (High)"
    elif (( $(echo "$cpu_usage > 95" | bc -l) )); then
        print_status "CRITICAL" "CPU Usage: ${cpu_usage}% (Critical)"
    else
        print_status "OK" "CPU Usage: ${cpu_usage}%"
    fi
    
    # Memory usage
    local mem_percent=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
    if (( $(echo "$mem_percent > 85" | bc -l) )); then
        print_status "WARNING" "Memory Usage: ${mem_percent}% (High)"
    elif (( $(echo "$mem_percent > 95" | bc -l) )); then
        print_status "CRITICAL" "Memory Usage: ${mem_percent}% (Critical)"
    else
        print_status "OK" "Memory Usage: ${mem_percent}%"
    fi
    
    # Swap usage
    local swap_percent=$(free | awk 'NR==3{if($2>0) printf "%.1f", $3*100/$2; else print "0"}')
    if [[ "$swap_percent" != "0" ]] && (( $(echo "$swap_percent > 50" | bc -l) )); then
        print_status "WARNING" "Swap Usage: ${swap_percent}%"
    else
        print_status "OK" "Swap Usage: ${swap_percent}%"
    fi
    
    # Disk usage
    while IFS= read -r line; do
        local filesystem=$(echo "$line" | awk '{print $1}')
        local usage=$(echo "$line" | awk '{print $5}' | sed 's/%//')
        local mount=$(echo "$line" | awk '{print $6}')
        
        if [[ $usage -gt 90 ]]; then
            print_status "CRITICAL" "Disk $mount: ${usage}% (Critical)"
        elif [[ $usage -gt 80 ]]; then
            print_status "WARNING" "Disk $mount: ${usage}% (High)"
        else
            print_status "OK" "Disk $mount: ${usage}%"
        fi
    done < <(df -h | grep -vE '^Filesystem|tmpfs|cdrom|udev')
    
    # Inode usage
    local inode_usage=$(df -i / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $inode_usage -gt 90 ]]; then
        print_status "CRITICAL" "Inode Usage: ${inode_usage}% (Critical)"
    elif [[ $inode_usage -gt 80 ]]; then
        print_status "WARNING" "Inode Usage: ${inode_usage}% (High)"
    else
        print_status "OK" "Inode Usage: ${inode_usage}%"
    fi
}

# Docker status
show_docker_status() {
    print_section "Docker Status"
    
    if ! command -v docker &> /dev/null; then
        print_status "ERROR" "Docker not installed"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        print_status "ERROR" "Docker daemon not running"
        return 1
    fi
    
    print_status "OK" "Docker daemon running"
    
    # Docker version
    local docker_version=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "Unknown")
    print_status "INFO" "Docker version: $docker_version"
    
    # Docker resources
    local total_containers=$(docker ps -a | wc -l)
    local running_containers=$(docker ps | wc -l)
    print_status "INFO" "Containers: $running_containers running / $((total_containers-1)) total"
    
    local total_images=$(docker images | wc -l)
    print_status "INFO" "Images: $((total_images-1)) total"
    
    local total_volumes=$(docker volume ls | wc -l)
    print_status "INFO" "Volumes: $((total_volumes-1)) total"
    
    # Docker storage
    local docker_storage=$(docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}" 2>/dev/null || echo "Unable to get storage info")
    if [[ "$docker_storage" != "Unable to get storage info" ]]; then
        print_status "INFO" "Docker storage usage:"
        echo "$docker_storage" | tail -n +2 | while read line; do
            print_status "INFO" "  $line"
        done
    fi
}

# Service status
show_service_status() {
    print_section "Application Services"
    
    cd "$PROJECT_DIR"
    
    if [[ ! -f "docker-compose.prod.yml" ]]; then
        print_status "ERROR" "docker-compose.prod.yml not found"
        return 1
    fi
    
    local services=("postgres" "redis" "api" "worker" "frontend" "nginx" "prometheus" "grafana")
    
    for service in "${services[@]}"; do
        local status=$(docker-compose -f docker-compose.prod.yml ps -q "$service" 2>/dev/null | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null || echo "not_found")
        
        case "$status" in
            "running")
                print_status "OK" "$service: Running"
                ;;
            "exited"|"dead")
                print_status "ERROR" "$service: Stopped"
                ;;
            "restarting")
                print_status "WARNING" "$service: Restarting"
                ;;
            "not_found")
                print_status "ERROR" "$service: Not found"
                ;;
            *)
                print_status "WARNING" "$service: $status"
                ;;
        esac
    done
}

# Network connectivity
show_network_status() {
    print_section "Network Connectivity"
    
    # Check external connectivity
    if ping -c 1 8.8.8.8 &> /dev/null; then
        print_status "OK" "External connectivity (8.8.8.8)"
    else
        print_status "ERROR" "No external connectivity"
    fi
    
    # Check DNS resolution
    if nslookup google.com &> /dev/null; then
        print_status "OK" "DNS resolution"
    else
        print_status "ERROR" "DNS resolution failed"
    fi
    
    # Check listening ports
    local required_ports=(22 80 443 5432 6379 8000 3000 9090 3001)
    for port in "${required_ports[@]}"; do
        if ss -tlnp | grep -q ":$port "; then
            print_status "OK" "Port $port listening"
        else
            print_status "WARNING" "Port $port not listening"
        fi
    done
}

# Application health
show_application_health() {
    print_section "Application Health"
    
    # API health
    if curl -f -s --max-time 10 "http://localhost:8000/health" > /dev/null 2>&1; then
        print_status "OK" "API health endpoint"
    else
        print_status "ERROR" "API health endpoint not responding"
    fi
    
    # Frontend
    if curl -f -s --max-time 10 "http://localhost:3000" > /dev/null 2>&1; then
        print_status "OK" "Frontend responding"
    else
        print_status "ERROR" "Frontend not responding"
    fi
    
    # Database
    cd "$PROJECT_DIR"
    if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        print_status "OK" "Database accepting connections"
        
        # Database size
        local db_size=$(docker-compose -f docker-compose.prod.yml exec -T postgres \
            psql -U postgres -d selextract -t -c "SELECT pg_size_pretty(pg_database_size('selextract'));" 2>/dev/null | xargs || echo "unknown")
        print_status "INFO" "Database size: $db_size"
        
        # Active connections
        local active_conn=$(docker-compose -f docker-compose.prod.yml exec -T postgres \
            psql -U postgres -d selextract -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null | xargs || echo "unknown")
        print_status "INFO" "Active DB connections: $active_conn"
    else
        print_status "ERROR" "Database not accepting connections"
    fi
    
    # Redis
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
        print_status "OK" "Redis responding"
        
        # Redis memory
        local redis_memory=$(docker-compose -f docker-compose.prod.yml exec -T redis \
            redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r' || echo "unknown")
        print_status "INFO" "Redis memory: $redis_memory"
    else
        print_status "ERROR" "Redis not responding"
    fi
    
    # Workers
    local worker_count=$(docker-compose -f docker-compose.prod.yml ps -q worker | wc -l)
    if [[ $worker_count -gt 0 ]]; then
        print_status "OK" "Workers running ($worker_count)"
        
        # Check if workers are processing tasks
        local active_tasks=$(docker-compose -f docker-compose.prod.yml exec -T worker \
            celery -A main inspect active 2>/dev/null | grep -c "task_id" || echo "0")
        print_status "INFO" "Active tasks: $active_tasks"
    else
        print_status "ERROR" "No workers running"
    fi
}

# Monitoring status
show_monitoring_status() {
    print_section "Monitoring Systems"
    
    # Prometheus
    if curl -f -s --max-time 10 "http://localhost:9090/-/healthy" > /dev/null 2>&1; then
        print_status "OK" "Prometheus healthy"
        
        # Check targets
        local targets_up=$(curl -s "http://localhost:9090/api/v1/targets" 2>/dev/null | grep -o '"health":"up"' | wc -l || echo "0")
        print_status "INFO" "Prometheus targets up: $targets_up"
    else
        print_status "ERROR" "Prometheus not responding"
    fi
    
    # Grafana
    if curl -f -s --max-time 10 "http://localhost:3001/api/health" > /dev/null 2>&1; then
        print_status "OK" "Grafana healthy"
    else
        print_status "ERROR" "Grafana not responding"
    fi
    
    # Check for firing alerts
    local firing_alerts=$(curl -s "http://localhost:9090/api/v1/alerts" 2>/dev/null | grep -o '"state":"firing"' | wc -l || echo "0")
    if [[ $firing_alerts -gt 0 ]]; then
        print_status "WARNING" "$firing_alerts alerts firing"
    else
        print_status "OK" "No alerts firing"
    fi
}

# Security status
show_security_status() {
    print_section "Security Status"
    
    # SSH configuration
    if grep -q "PasswordAuthentication no" /etc/ssh/sshd_config 2>/dev/null; then
        print_status "OK" "SSH password authentication disabled"
    else
        print_status "WARNING" "SSH password authentication may be enabled"
    fi
    
    # Firewall status
    if command -v ufw &>/dev/null; then
        if ufw status | grep -q "Status: active"; then
            print_status "OK" "UFW firewall active"
        else
            print_status "WARNING" "UFW firewall inactive"
        fi
    fi
    
    # fail2ban status
    if systemctl is-active --quiet fail2ban 2>/dev/null; then
        print_status "OK" "fail2ban active"
        
        # Check recent bans
        local banned_ips=$(fail2ban-client status 2>/dev/null | grep "Currently banned" | grep -o "[0-9]*" || echo "0")
        if [[ $banned_ips -gt 0 ]]; then
            print_status "INFO" "Currently banned IPs: $banned_ips"
        fi
    else
        print_status "WARNING" "fail2ban not active"
    fi
    
    # SSL certificates
    local cert_file="/etc/nginx/ssl/selextract.com/fullchain.pem"
    if [[ -f "$cert_file" ]]; then
        local expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate 2>/dev/null | cut -d= -f2)
        local days_until_expiry=$(( ($(date -d "$expiry_date" +%s) - $(date +%s)) / 86400 ))
        
        if [[ $days_until_expiry -lt 7 ]]; then
            print_status "CRITICAL" "SSL certificate expires in $days_until_expiry days"
        elif [[ $days_until_expiry -lt 30 ]]; then
            print_status "WARNING" "SSL certificate expires in $days_until_expiry days"
        else
            print_status "OK" "SSL certificate valid ($days_until_expiry days remaining)"
        fi
    else
        print_status "ERROR" "SSL certificate not found"
    fi
}

# Backup status
show_backup_status() {
    print_section "Backup Status"
    
    local backup_dir="/opt/backups"
    if [[ ! -d "$backup_dir" ]]; then
        print_status "ERROR" "Backup directory not found"
        return 1
    fi
    
    # Find most recent backup
    local latest_backup=$(find "$backup_dir" -maxdepth 1 -type d -name "20*" | sort | tail -1)
    
    if [[ -z "$latest_backup" ]]; then
        print_status "ERROR" "No backups found"
        return 1
    fi
    
    local backup_age=$(( ($(date +%s) - $(stat -c %Y "$latest_backup")) / 86400 ))
    
    if [[ $backup_age -gt 7 ]]; then
        print_status "CRITICAL" "Latest backup is $backup_age days old"
    elif [[ $backup_age -gt 3 ]]; then
        print_status "WARNING" "Latest backup is $backup_age days old"
    else
        print_status "OK" "Latest backup is $backup_age days old"
    fi
    
    # Count total backups
    local backup_count=$(find "$backup_dir" -maxdepth 1 -type d -name "20*" | wc -l)
    print_status "INFO" "Total backups: $backup_count"
    
    # Backup size
    local latest_backup_size=$(du -sh "$latest_backup" 2>/dev/null | cut -f1 || echo "unknown")
    print_status "INFO" "Latest backup size: $latest_backup_size"
}

# Summary
show_summary() {
    print_section "Summary"
    
    local status="HEALTHY"
    local issues=0
    
    # Quick health checks
    if ! docker info &> /dev/null; then
        status="CRITICAL"
        ((issues++))
    fi
    
    if ! curl -f -s --max-time 5 "http://localhost:8000/health" > /dev/null 2>&1; then
        status="CRITICAL"
        ((issues++))
    fi
    
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $disk_usage -gt 90 ]]; then
        status="CRITICAL"
        ((issues++))
    elif [[ $disk_usage -gt 80 ]] && [[ "$status" == "HEALTHY" ]]; then
        status="WARNING"
        ((issues++))
    fi
    
    local mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [[ $mem_usage -gt 95 ]]; then
        status="CRITICAL"
        ((issues++))
    elif [[ $mem_usage -gt 85 ]] && [[ "$status" == "HEALTHY" ]]; then
        status="WARNING"
        ((issues++))
    fi
    
    print_status "$status" "Overall system status: $status"
    if [[ $issues -gt 0 ]]; then
        print_status "INFO" "Issues detected: $issues"
        print_status "INFO" "Run detailed health check: ./scripts/health-check.sh"
    fi
    
    print_status "INFO" "Report generated: $(date)"
}

# Main function
main() {
    load_environment
    
    print_header "Selextract Cloud System Status"
    
    show_system_info
    show_resource_usage
    show_docker_status
    show_service_status
    show_network_status
    show_application_health
    show_monitoring_status
    show_security_status
    show_backup_status
    show_summary
}

# Handle command line arguments
case "${1:-}" in
    --json)
        OUTPUT_FORMAT="json"
        echo "JSON output not yet implemented"
        exit 1
        ;;
    --brief)
        show_summary
        ;;
    --help)
        echo "Usage: $0 [--brief|--json|--help]"
        echo ""
        echo "Options:"
        echo "  --brief  Show only summary status"
        echo "  --json   Output in JSON format (not implemented)"
        echo "  --help   Show this help message"
        ;;
    *)
        main
        ;;
esac