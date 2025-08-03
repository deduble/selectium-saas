#!/bin/bash

# Selextract Cloud Deployment Validation Script
# Validates all configurations and scripts before production deployment

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VALIDATION_LOG="/tmp/validation-$(date +%Y%m%d_%H%M%S).log"
ERRORS=0
WARNINGS=0
PASSED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$VALIDATION_LOG"
}

pass() {
    echo -e "${GREEN}[PASS]${NC} $1" | tee -a "$VALIDATION_LOG"
    ((PASSED++))
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$VALIDATION_LOG"
    ((WARNINGS++))
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1" | tee -a "$VALIDATION_LOG"
    ((ERRORS++))
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$VALIDATION_LOG"
}

section() {
    echo -e "\n${CYAN}=== $1 ===${NC}" | tee -a "$VALIDATION_LOG"
}

# Check if file exists and is readable
check_file() {
    local file="$1"
    local description="$2"
    
    if [[ -f "$file" ]]; then
        if [[ -r "$file" ]]; then
            pass "$description exists and is readable"
            return 0
        else
            fail "$description exists but is not readable"
            return 1
        fi
    else
        fail "$description does not exist: $file"
        return 1
    fi
}

# Check if directory exists
check_directory() {
    local dir="$1"
    local description="$2"
    
    if [[ -d "$dir" ]]; then
        pass "$description exists"
        return 0
    else
        fail "$description does not exist: $dir"
        return 1
    fi
}

# Check if script is executable
check_executable() {
    local script="$1"
    local description="$2"
    
    if [[ -f "$script" ]]; then
        if [[ -x "$script" ]]; then
            pass "$description is executable"
            return 0
        else
            fail "$description is not executable"
            return 1
        fi
    else
        fail "$description does not exist: $script"
        return 1
    fi
}

# Validate JSON syntax
validate_json() {
    local file="$1"
    local description="$2"
    
    if [[ -f "$file" ]]; then
        if python3 -m json.tool "$file" >/dev/null 2>&1; then
            pass "$description has valid JSON syntax"
            return 0
        else
            fail "$description has invalid JSON syntax"
            return 1
        fi
    else
        fail "$description does not exist: $file"
        return 1
    fi
}

# Validate YAML syntax
validate_yaml() {
    local file="$1"
    local description="$2"
    
    if [[ -f "$file" ]]; then
        if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            pass "$description has valid YAML syntax"
            return 0
        else
            fail "$description has invalid YAML syntax"
            return 1
        fi
    else
        fail "$description does not exist: $file"
        return 1
    fi
}

# Check required files
check_required_files() {
    section "Required Files Validation"
    
    # Core configuration files
    check_file "$PROJECT_DIR/.env.prod" "Production environment file"
    check_file "$PROJECT_DIR/docker-compose.prod.yml" "Production Docker Compose file"
    check_file "$PROJECT_DIR/docker-compose.yml" "Development Docker Compose file"
    
    # Nginx configuration
    check_file "$PROJECT_DIR/nginx/nginx.conf" "Nginx main configuration"
    check_file "$PROJECT_DIR/nginx/sites-available/selextract.conf" "Nginx site configuration"
    
    # Monitoring configuration
    check_file "$PROJECT_DIR/monitoring/prometheus.yml" "Prometheus configuration"
    check_file "$PROJECT_DIR/monitoring/alert_rules.yml" "Prometheus alert rules"
    check_file "$PROJECT_DIR/monitoring/alertmanager.yml" "Alertmanager configuration"
    check_file "$PROJECT_DIR/monitoring/grafana/datasources/prometheus.yml" "Grafana datasource configuration"
    check_file "$PROJECT_DIR/monitoring/grafana/dashboards/selextract-overview.json" "Grafana dashboard"
    
    # Logging configuration
    check_file "$PROJECT_DIR/monitoring/loki/loki-config.yml" "Loki configuration"
    check_file "$PROJECT_DIR/monitoring/promtail/promtail-config.yml" "Promtail configuration"
    
    # Application files
    check_file "$PROJECT_DIR/api/main.py" "API main file"
    check_file "$PROJECT_DIR/api/requirements.txt" "API requirements"
    check_file "$PROJECT_DIR/worker/main.py" "Worker main file"
    check_file "$PROJECT_DIR/worker/requirements.txt" "Worker requirements"
    check_file "$PROJECT_DIR/frontend/package.json" "Frontend package.json"
    
    # Database files
    check_file "$PROJECT_DIR/db/init.sql" "Database initialization script"
}

# Check directories
check_required_directories() {
    section "Required Directories Validation"
    
    check_directory "$PROJECT_DIR/api" "API directory"
    check_directory "$PROJECT_DIR/worker" "Worker directory"
    check_directory "$PROJECT_DIR/frontend" "Frontend directory"
    check_directory "$PROJECT_DIR/nginx" "Nginx directory"
    check_directory "$PROJECT_DIR/monitoring" "Monitoring directory"
    check_directory "$PROJECT_DIR/scripts" "Scripts directory"
    check_directory "$PROJECT_DIR/docs" "Documentation directory"
}

# Check script permissions
check_script_permissions() {
    section "Script Permissions Validation"
    
    local scripts=(
        "deploy.sh"
        "backup.sh"
        "restore.sh"
        "update.sh"
        "health-check.sh"
        "maintenance.sh"
        "system-status.sh"
        "setup-ssl.sh"
        "security-hardening.sh"
        "validate-deployment.sh"
    )
    
    for script in "${scripts[@]}"; do
        check_executable "$PROJECT_DIR/scripts/$script" "Script: $script"
    done
}

# Validate configuration syntax
validate_configuration_syntax() {
    section "Configuration Syntax Validation"
    
    # Validate YAML files
    validate_yaml "$PROJECT_DIR/docker-compose.yml" "Development Docker Compose"
    validate_yaml "$PROJECT_DIR/docker-compose.prod.yml" "Production Docker Compose"
    validate_yaml "$PROJECT_DIR/monitoring/prometheus.yml" "Prometheus configuration"
    validate_yaml "$PROJECT_DIR/monitoring/alert_rules.yml" "Prometheus alert rules"
    validate_yaml "$PROJECT_DIR/monitoring/alertmanager.yml" "Alertmanager configuration"
    validate_yaml "$PROJECT_DIR/monitoring/grafana/datasources/prometheus.yml" "Grafana datasource"
    validate_yaml "$PROJECT_DIR/monitoring/loki/loki-config.yml" "Loki configuration"
    validate_yaml "$PROJECT_DIR/monitoring/promtail/promtail-config.yml" "Promtail configuration"
    
    # Validate JSON files
    validate_json "$PROJECT_DIR/monitoring/grafana/dashboards/selextract-overview.json" "Grafana dashboard"
    validate_json "$PROJECT_DIR/frontend/package.json" "Frontend package.json"
    
    # Validate Nginx configuration syntax
    if command -v nginx >/dev/null 2>&1; then
        if nginx -t -c "$PROJECT_DIR/nginx/nginx.conf" >/dev/null 2>&1; then
            pass "Nginx configuration syntax is valid"
        else
            fail "Nginx configuration syntax is invalid"
        fi
    else
        warn "Nginx not installed, cannot validate configuration syntax"
    fi
}

# Check environment configuration
check_environment_configuration() {
    section "Environment Configuration Validation"
    
    if [[ -f "$PROJECT_DIR/.env.prod" ]]; then
        local required_vars=(
            "POSTGRES_PASSWORD"
            "REDIS_PASSWORD"
            "JWT_SECRET_KEY"
            "NEXTAUTH_SECRET"
            "WEBSHARE_API_KEY"
            "LEMON_SQUEEZY_API_KEY"
            "GRAFANA_ADMIN_PASSWORD"
            "ADMIN_EMAIL"
        )
        
        for var in "${required_vars[@]}"; do
            if grep -q "^$var=" "$PROJECT_DIR/.env.prod" && ! grep -q "^$var=REPLACE_" "$PROJECT_DIR/.env.prod"; then
                pass "Environment variable $var is configured"
            else
                fail "Environment variable $var is not properly configured"
            fi
        done
        
        # Check for placeholder values
        local placeholders=$(grep -c "REPLACE_WITH" "$PROJECT_DIR/.env.prod" || echo "0")
        if [[ $placeholders -gt 0 ]]; then
            fail "$placeholders placeholder values found in .env.prod"
        else
            pass "No placeholder values found in .env.prod"
        fi
        
        # Check file permissions
        local perms=$(stat -c "%a" "$PROJECT_DIR/.env.prod")
        if [[ "$perms" == "600" ]]; then
            pass ".env.prod has correct permissions (600)"
        else
            warn ".env.prod permissions are $perms, should be 600"
        fi
    else
        fail "Production environment file not found"
    fi
}

# Check Docker configuration
check_docker_configuration() {
    section "Docker Configuration Validation"
    
    # Check if Docker is available
    if command -v docker >/dev/null 2>&1; then
        pass "Docker is installed"
        
        if docker info >/dev/null 2>&1; then
            pass "Docker daemon is running"
        else
            fail "Docker daemon is not running"
        fi
    else
        fail "Docker is not installed"
    fi
    
    # Check if Docker Compose is available
    if command -v docker-compose >/dev/null 2>&1; then
        pass "Docker Compose is installed"
    elif docker compose version >/dev/null 2>&1; then
        pass "Docker Compose (plugin) is available"
    else
        fail "Docker Compose is not available"
    fi
    
    # Validate Docker Compose files
    cd "$PROJECT_DIR"
    if docker-compose -f docker-compose.prod.yml config >/dev/null 2>&1; then
        pass "Production Docker Compose configuration is valid"
    else
        fail "Production Docker Compose configuration is invalid"
    fi
    
    # Check for required services in production compose
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
    
    for service in "${required_services[@]}"; do
        if docker-compose -f docker-compose.prod.yml config | grep -q "^  $service:"; then
            pass "Service $service is defined in production compose"
        else
            fail "Service $service is missing from production compose"
        fi
    done
}

# Check SSL configuration
check_ssl_configuration() {
    section "SSL Configuration Validation"
    
    # Check if SSL setup script exists and is executable
    check_executable "$PROJECT_DIR/scripts/setup-ssl.sh" "SSL setup script"
    
    # Check Nginx SSL configuration
    if [[ -f "$PROJECT_DIR/nginx/sites-available/selextract.conf" ]]; then
        if grep -q "ssl_certificate" "$PROJECT_DIR/nginx/sites-available/selextract.conf"; then
            pass "SSL certificate configuration found in Nginx"
        else
            warn "SSL certificate configuration not found in Nginx"
        fi
        
        if grep -q "ssl_certificate_key" "$PROJECT_DIR/nginx/sites-available/selextract.conf"; then
            pass "SSL certificate key configuration found in Nginx"
        else
            warn "SSL certificate key configuration not found in Nginx"
        fi
    fi
    
    # Check if certbot is available for Let's Encrypt
    if command -v certbot >/dev/null 2>&1; then
        pass "Certbot is installed"
    else
        warn "Certbot is not installed (required for Let's Encrypt)"
    fi
}

# Check security configuration
check_security_configuration() {
    section "Security Configuration Validation"
    
    # Check if security hardening script exists
    check_executable "$PROJECT_DIR/scripts/security-hardening.sh" "Security hardening script"
    
    # Check firewall tools
    if command -v ufw >/dev/null 2>&1; then
        pass "UFW firewall is installed"
    else
        warn "UFW firewall is not installed"
    fi
    
    # Check fail2ban
    if command -v fail2ban-client >/dev/null 2>&1; then
        pass "fail2ban is installed"
    else
        warn "fail2ban is not installed"
    fi
    
    # Check if security headers are configured in Nginx
    if [[ -f "$PROJECT_DIR/nginx/sites-available/selextract.conf" ]]; then
        local security_headers=(
            "X-Frame-Options"
            "X-Content-Type-Options"
            "X-XSS-Protection"
            "Strict-Transport-Security"
        )
        
        for header in "${security_headers[@]}"; do
            if grep -q "$header" "$PROJECT_DIR/nginx/sites-available/selextract.conf"; then
                pass "Security header $header is configured"
            else
                warn "Security header $header is not configured"
            fi
        done
    fi
}

# Check monitoring configuration
check_monitoring_configuration() {
    section "Monitoring Configuration Validation"
    
    # Check Prometheus configuration
    if command -v promtool >/dev/null 2>&1; then
        if promtool check config "$PROJECT_DIR/monitoring/prometheus.yml" >/dev/null 2>&1; then
            pass "Prometheus configuration is valid"
        else
            fail "Prometheus configuration is invalid"
        fi
        
        if promtool check rules "$PROJECT_DIR/monitoring/alert_rules.yml" >/dev/null 2>&1; then
            pass "Prometheus alert rules are valid"
        else
            fail "Prometheus alert rules are invalid"
        fi
    else
        warn "promtool not available, cannot validate Prometheus configuration"
    fi
    
    # Check if required metrics endpoints are configured
    local metrics_files=(
        "$PROJECT_DIR/api/metrics.py"
    )
    
    for file in "${metrics_files[@]}"; do
        if [[ -f "$file" ]]; then
            pass "Metrics file exists: $(basename "$file")"
        else
            warn "Metrics file missing: $(basename "$file")"
        fi
    done
}

# Check backup configuration
check_backup_configuration() {
    section "Backup Configuration Validation"
    
    check_executable "$PROJECT_DIR/scripts/backup.sh" "Backup script"
    check_executable "$PROJECT_DIR/scripts/restore.sh" "Restore script"
    
    # Check if backup directory would be created
    if [[ -n "${BACKUP_DIR:-}" ]]; then
        info "Backup directory configured: $BACKUP_DIR"
    else
        info "Using default backup directory: /opt/backups"
    fi
    
    # Check if remote backup is configured
    if grep -q "REMOTE_BACKUP_ENABLED=true" "$PROJECT_DIR/.env.prod" 2>/dev/null; then
        pass "Remote backup is enabled"
        
        # Check for remote backup configuration
        if grep -q "AWS_S3_BUCKET\|BACKBLAZE_BUCKET\|RSYNC_DESTINATION" "$PROJECT_DIR/.env.prod" 2>/dev/null; then
            pass "Remote backup destination is configured"
        else
            warn "Remote backup enabled but no destination configured"
        fi
    else
        warn "Remote backup is disabled"
    fi
}

# Test script functionality
test_script_functionality() {
    section "Script Functionality Testing"
    
    # Test health check script (dry run)
    if "$PROJECT_DIR/scripts/health-check.sh" --help >/dev/null 2>&1; then
        pass "Health check script help works"
    else
        fail "Health check script help failed"
    fi
    
    # Test maintenance script (dry run)
    if DRY_RUN=true "$PROJECT_DIR/scripts/maintenance.sh" cleanup >/dev/null 2>&1; then
        pass "Maintenance script dry run works"
    else
        fail "Maintenance script dry run failed"
    fi
    
    # Test system status script
    if "$PROJECT_DIR/scripts/system-status.sh" --brief >/dev/null 2>&1; then
        pass "System status script brief mode works"
    else
        fail "System status script brief mode failed"
    fi
    
    # Test deployment script help
    if "$PROJECT_DIR/scripts/deploy.sh" --help >/dev/null 2>&1; then
        pass "Deployment script help works"
    else
        fail "Deployment script help failed"
    fi
}

# Check documentation
check_documentation() {
    section "Documentation Validation"
    
    check_file "$PROJECT_DIR/docs/PRODUCTION_DEPLOYMENT_GUIDE.md" "Production deployment guide"
    check_file "$PROJECT_DIR/docs/OPERATIONS_RUNBOOK.md" "Operations runbook"
    check_file "$PROJECT_DIR/plan.md" "Project plan"
    
    # Check if README exists
    if [[ -f "$PROJECT_DIR/README.md" ]]; then
        pass "README.md exists"
    else
        warn "README.md does not exist"
    fi
}

# Generate validation report
generate_report() {
    section "Validation Summary"
    
    local total=$((PASSED + WARNINGS + ERRORS))
    
    info "Validation completed:"
    info "  Total checks: $total"
    info "  Passed: $PASSED"
    info "  Warnings: $WARNINGS"  
    info "  Errors: $ERRORS"
    
    if [[ $ERRORS -eq 0 ]] && [[ $WARNINGS -eq 0 ]]; then
        pass "✅ All validations passed! Deployment is ready for production."
        echo -e "\n${GREEN}🎉 DEPLOYMENT VALIDATION SUCCESSFUL 🎉${NC}"
        echo -e "${GREEN}Your Selextract Cloud deployment is ready for production!${NC}"
    elif [[ $ERRORS -eq 0 ]]; then
        warn "⚠️  Validation completed with warnings. Review warnings before deployment."
        echo -e "\n${YELLOW}⚠️  DEPLOYMENT VALIDATION COMPLETED WITH WARNINGS${NC}"
        echo -e "${YELLOW}Please review and address warnings before production deployment.${NC}"
    else
        fail "❌ Validation failed with $ERRORS errors. Fix errors before deployment."
        echo -e "\n${RED}❌ DEPLOYMENT VALIDATION FAILED${NC}"
        echo -e "${RED}Please fix all errors before attempting production deployment.${NC}"
    fi
    
    echo -e "\nFull validation log: $VALIDATION_LOG"
    
    # Create summary file
    local summary_file="$PROJECT_DIR/validation-summary.txt"
    cat > "$summary_file" << EOF
Selextract Cloud Deployment Validation Summary
==============================================
Date: $(date)
Total Checks: $total
Passed: $PASSED
Warnings: $WARNINGS
Errors: $ERRORS

Status: $(if [[ $ERRORS -eq 0 ]]; then echo "READY FOR DEPLOYMENT"; else echo "NOT READY - FIX ERRORS"; fi)

Full log: $VALIDATION_LOG
EOF
    
    info "Validation summary saved to: $summary_file"
}

# Main validation function
main() {
    echo -e "${CYAN}"
    cat << "EOF"
 ____       _           _                  _    
/ ___|  ___| | _____  _| |_ _ __ __ _  ___| |_  
\___ \ / _ \ |/ _ \ \/ / __| '__/ _` |/ __| __| 
 ___) |  __/ |  __/>  <| |_| | | (_| | (__| |_  
|____/ \___|_|\___/_/\_\\__|_|  \__,_|\___|\__| 
                                                
   Cloud Deployment Validation
EOF
    echo -e "${NC}"
    
    info "Starting comprehensive deployment validation..."
    info "Project directory: $PROJECT_DIR"
    info "Validation log: $VALIDATION_LOG"
    
    cd "$PROJECT_DIR"
    
    check_required_files
    check_required_directories
    check_script_permissions
    validate_configuration_syntax
    check_environment_configuration
    check_docker_configuration
    check_ssl_configuration
    check_security_configuration
    check_monitoring_configuration
    check_backup_configuration
    test_script_functionality
    check_documentation
    
    generate_report
    
    # Exit with appropriate code
    if [[ $ERRORS -gt 0 ]]; then
        exit 1
    elif [[ $WARNINGS -gt 0 ]]; then
        exit 2
    else
        exit 0
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help)
        echo "Usage: $0 [--help]"
        echo ""
        echo "Validates all Selextract Cloud deployment configurations and scripts."
        echo ""
        echo "Exit codes:"
        echo "  0 - All validations passed"
        echo "  1 - Validation failed with errors"
        echo "  2 - Validation completed with warnings"
        ;;
    *)
        main
        ;;
esac