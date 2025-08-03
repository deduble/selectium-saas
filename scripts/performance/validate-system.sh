#!/bin/bash

# Comprehensive Load Testing and Optimization System Validation
# Validates all components of the Selextract Cloud performance testing framework

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VALIDATION_REPORT="$PROJECT_ROOT/performance-validation-$(date +%Y%m%d-%H%M%S).md"

# Test configuration
TARGET_URL="${TARGET_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3001}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Validation results
VALIDATION_RESULTS=()
FAILED_CHECKS=0
TOTAL_CHECKS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_section() {
    echo
    echo -e "${PURPLE}=== $1 ===${NC}"
}

# Record validation result
record_result() {
    local test_name="$1"
    local status="$2"
    local details="$3"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if [ "$status" = "PASS" ]; then
        log_success "$test_name"
        VALIDATION_RESULTS+=("✅ $test_name: $details")
    elif [ "$status" = "WARN" ]; then
        log_warning "$test_name"
        VALIDATION_RESULTS+=("⚠️ $test_name: $details")
    else
        log_error "$test_name"
        VALIDATION_RESULTS+=("❌ $test_name: $details")
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

# Check if command exists
check_command() {
    local cmd="$1"
    local description="$2"
    
    if command -v "$cmd" >/dev/null 2>&1; then
        local version
        case "$cmd" in
            k6)
                version=$(k6 version 2>/dev/null | head -n1 || echo "unknown")
                ;;
            artillery)
                version=$(artillery version 2>/dev/null || echo "unknown")
                ;;
            docker)
                version=$(docker --version 2>/dev/null || echo "unknown")
                ;;
            docker-compose)
                version=$(docker-compose --version 2>/dev/null || echo "unknown")
                ;;
            python3)
                version=$(python3 --version 2>/dev/null || echo "unknown")
                ;;
            *)
                version=$(eval "$cmd --version" 2>/dev/null | head -n1 || echo "available")
                ;;
        esac
        record_result "$description" "PASS" "$version"
        return 0
    else
        record_result "$description" "FAIL" "Command not found"
        return 1
    fi
}

# Validate file exists
validate_file() {
    local file_path="$1"
    local description="$2"
    local optional="$3"
    
    if [ -f "$file_path" ]; then
        local size
        size=$(du -h "$file_path" | cut -f1)
        record_result "$description" "PASS" "File exists ($size)"
        return 0
    else
        if [ "$optional" = "true" ]; then
            record_result "$description" "WARN" "Optional file missing"
        else
            record_result "$description" "FAIL" "Required file missing"
        fi
        return 1
    fi
}

# Validate directory structure
validate_directory_structure() {
    local directories=(
        "tests/load"
        "scripts/performance"
        "scripts/ci"
        "config"
        "monitoring"
        "docs"
    )
    
    for dir in "${directories[@]}"; do
        if [ -d "$PROJECT_ROOT/$dir" ]; then
            record_result "Directory: $dir" "PASS" "Directory exists"
        else
            record_result "Directory: $dir" "FAIL" "Directory missing"
        fi
    done
}

# Validate configuration files
validate_configuration_files() {
    log_section "Configuration Files Validation"
    
    validate_file "$PROJECT_ROOT/config/nginx-optimized.conf" "Nginx optimization config" false
    validate_file "$PROJECT_ROOT/config/postgresql-performance.conf" "PostgreSQL performance config" false
    validate_file "$PROJECT_ROOT/config/redis-performance.conf" "Redis performance config" false
    validate_file "$PROJECT_ROOT/config/docker-performance.yml" "Docker performance config" false
}

# Validate load testing files
validate_load_testing_files() {
    log_section "Load Testing Files Validation"
    
    validate_file "$PROJECT_ROOT/tests/load/k6-load-tests.js" "K6 load tests" false
    validate_file "$PROJECT_ROOT/tests/load/artillery-tests.yml" "Artillery tests config" false
    validate_file "$PROJECT_ROOT/tests/load/locust/locustfile.py" "Locust test file" false
    validate_file "$PROJECT_ROOT/tests/load/test-data.csv" "Test data file" true
}

# Validate monitoring configuration
validate_monitoring_config() {
    log_section "Monitoring Configuration Validation"
    
    validate_file "$PROJECT_ROOT/monitoring/prometheus.yml" "Prometheus config" false
    validate_file "$PROJECT_ROOT/monitoring/performance-dashboard.json" "Performance dashboard" false
    validate_file "$PROJECT_ROOT/monitoring/grafana/dashboards/selextract-overview.json" "Grafana dashboard" true
}

# Validate scripts
validate_scripts() {
    log_section "Scripts Validation"
    
    validate_file "$PROJECT_ROOT/scripts/performance/benchmark.sh" "Performance benchmark script" false
    validate_file "$PROJECT_ROOT/scripts/performance/analyze-metrics.py" "Metrics analysis script" false
    validate_file "$PROJECT_ROOT/scripts/ci/performance-tests.sh" "CI performance tests" false
    
    # Check script permissions
    local scripts=(
        "$PROJECT_ROOT/scripts/performance/benchmark.sh"
        "$PROJECT_ROOT/scripts/ci/performance-tests.sh"
        "$PROJECT_ROOT/scripts/performance/validate-system.sh"
    )
    
    for script in "${scripts[@]}"; do
        if [ -f "$script" ] && [ -x "$script" ]; then
            record_result "Executable: $(basename "$script")" "PASS" "Script is executable"
        elif [ -f "$script" ]; then
            record_result "Executable: $(basename "$script")" "WARN" "Script exists but not executable"
        else
            record_result "Executable: $(basename "$script")" "FAIL" "Script missing"
        fi
    done
}

# Validate documentation
validate_documentation() {
    log_section "Documentation Validation"
    
    validate_file "$PROJECT_ROOT/docs/PERFORMANCE_ANALYSIS.md" "Performance analysis guide" false
    validate_file "$PROJECT_ROOT/docs/CAPACITY_PLANNING.md" "Capacity planning guide" false
    validate_file "$PROJECT_ROOT/README.md" "Project README" true
}

# Test service connectivity
test_service_connectivity() {
    log_section "Service Connectivity Tests"
    
    # Test API health endpoint
    if curl -sf "$TARGET_URL/api/v1/health" >/dev/null 2>&1; then
        record_result "API Health Check" "PASS" "API service responding"
    else
        record_result "API Health Check" "FAIL" "API service not responding"
    fi
    
    # Test frontend
    if curl -sf "$FRONTEND_URL" >/dev/null 2>&1; then
        record_result "Frontend Health Check" "PASS" "Frontend service responding"
    else
        record_result "Frontend Health Check" "WARN" "Frontend service not responding (may be expected)"
    fi
    
    # Test Prometheus
    if curl -sf "$PROMETHEUS_URL/api/v1/status/config" >/dev/null 2>&1; then
        record_result "Prometheus Health Check" "PASS" "Prometheus responding"
    else
        record_result "Prometheus Health Check" "WARN" "Prometheus not responding (may be expected)"
    fi
    
    # Test Grafana
    if curl -sf "$GRAFANA_URL/api/health" >/dev/null 2>&1; then
        record_result "Grafana Health Check" "PASS" "Grafana responding"
    else
        record_result "Grafana Health Check" "WARN" "Grafana not responding (may be expected)"
    fi
}

# Test load testing tools
test_load_testing_tools() {
    log_section "Load Testing Tools Validation"
    
    # Test K6
    if command -v k6 >/dev/null 2>&1; then
        if k6 version >/dev/null 2>&1; then
            record_result "K6 Tool Test" "PASS" "K6 working correctly"
        else
            record_result "K6 Tool Test" "FAIL" "K6 installed but not working"
        fi
    else
        record_result "K6 Tool Test" "FAIL" "K6 not installed"
    fi
    
    # Test Artillery
    if command -v artillery >/dev/null 2>&1; then
        if artillery version >/dev/null 2>&1; then
            record_result "Artillery Tool Test" "PASS" "Artillery working correctly"
        else
            record_result "Artillery Tool Test" "FAIL" "Artillery installed but not working"
        fi
    else
        record_result "Artillery Tool Test" "FAIL" "Artillery not installed"
    fi
    
    # Test Python and required packages
    if command -v python3 >/dev/null 2>&1; then
        # Test Locust
        if python3 -c "import locust" >/dev/null 2>&1; then
            record_result "Locust/Python Test" "PASS" "Locust package available"
        else
            record_result "Locust/Python Test" "WARN" "Python available but Locust not installed"
        fi
        
        # Test other required packages
        local packages=("requests" "matplotlib" "pandas" "numpy")
        local missing_packages=()
        
        for package in "${packages[@]}"; do
            if ! python3 -c "import $package" >/dev/null 2>&1; then
                missing_packages+=("$package")
            fi
        done
        
        if [ ${#missing_packages[@]} -eq 0 ]; then
            record_result "Python Dependencies" "PASS" "All required packages available"
        else
            record_result "Python Dependencies" "WARN" "Missing packages: ${missing_packages[*]}"
        fi
    else
        record_result "Python Test" "FAIL" "Python3 not available"
    fi
}

# Run quick performance tests
run_quick_tests() {
    log_section "Quick Performance Tests"
    
    # Simple API test
    if curl -sf "$TARGET_URL/api/v1/health" >/dev/null 2>&1; then
        local start_time end_time response_time
        start_time=$(date +%s%3N)
        
        if curl -sf "$TARGET_URL/api/v1/health" >/dev/null 2>&1; then
            end_time=$(date +%s%3N)
            response_time=$((end_time - start_time))
            
            if [ "$response_time" -lt 1000 ]; then
                record_result "API Response Time" "PASS" "${response_time}ms"
            elif [ "$response_time" -lt 2000 ]; then
                record_result "API Response Time" "WARN" "${response_time}ms (slow)"
            else
                record_result "API Response Time" "FAIL" "${response_time}ms (too slow)"
            fi
        else
            record_result "API Response Time" "FAIL" "Request failed"
        fi
    else
        record_result "API Response Time" "FAIL" "API not available"
    fi
    
    # Quick K6 test (if available)
    if command -v k6 >/dev/null 2>&1 && [ -f "$PROJECT_ROOT/tests/load/k6-load-tests.js" ]; then
        log_info "Running quick K6 validation test..."
        
        if k6 run --duration 10s --vus 1 --env TARGET_URL="$TARGET_URL" \
            "$PROJECT_ROOT/tests/load/k6-load-tests.js" >/dev/null 2>&1; then
            record_result "K6 Integration Test" "PASS" "K6 test executed successfully"
        else
            record_result "K6 Integration Test" "FAIL" "K6 test failed"
        fi
    else
        record_result "K6 Integration Test" "WARN" "K6 or test file not available"
    fi
}

# Test Docker and containers
test_docker_environment() {
    log_section "Docker Environment Validation"
    
    # Check Docker
    if command -v docker >/dev/null 2>&1; then
        if docker ps >/dev/null 2>&1; then
            local running_containers
            running_containers=$(docker ps --format "{{.Names}}" | grep -E "(selextract|api|frontend|worker|db|redis)" | wc -l)
            
            if [ "$running_containers" -gt 0 ]; then
                record_result "Docker Containers" "PASS" "$running_containers containers running"
            else
                record_result "Docker Containers" "WARN" "No Selextract containers running"
            fi
        else
            record_result "Docker Service" "FAIL" "Docker daemon not accessible"
        fi
    else
        record_result "Docker Installation" "FAIL" "Docker not installed"
    fi
    
    # Check Docker Compose
    if command -v docker-compose >/dev/null 2>&1; then
        record_result "Docker Compose" "PASS" "Docker Compose available"
        
        # Check compose files
        validate_file "$PROJECT_ROOT/docker-compose.yml" "Main compose file" false
        validate_file "$PROJECT_ROOT/config/docker-performance.yml" "Performance compose file" false
    else
        record_result "Docker Compose" "FAIL" "Docker Compose not installed"
    fi
}

# Generate validation report
generate_validation_report() {
    log_section "Generating Validation Report"
    
    cat > "$VALIDATION_REPORT" << EOF
# Selextract Cloud Performance System Validation Report

**Generated**: $(date)  
**Validation Script**: $0  
**Total Checks**: $TOTAL_CHECKS  
**Failed Checks**: $FAILED_CHECKS  
**Success Rate**: $(( (TOTAL_CHECKS - FAILED_CHECKS) * 100 / TOTAL_CHECKS ))%

## Executive Summary

$(if [ $FAILED_CHECKS -eq 0 ]; then
    echo "✅ **All validation checks passed successfully!** The load testing and optimization system is fully operational."
elif [ $FAILED_CHECKS -lt 5 ]; then
    echo "⚠️ **System mostly operational with minor issues.** $FAILED_CHECKS checks failed out of $TOTAL_CHECKS total."
else
    echo "❌ **System has significant issues.** $FAILED_CHECKS checks failed out of $TOTAL_CHECKS total. Review and fix issues before using."
fi)

## Validation Results

EOF

    # Add all validation results
    for result in "${VALIDATION_RESULTS[@]}"; do
        echo "- $result" >> "$VALIDATION_REPORT"
    done
    
    cat >> "$VALIDATION_REPORT" << EOF

## System Components Status

### Load Testing Tools
- **K6**: $(command -v k6 >/dev/null 2>&1 && echo "✅ Installed" || echo "❌ Not installed")
- **Artillery**: $(command -v artillery >/dev/null 2>&1 && echo "✅ Installed" || echo "❌ Not installed")
- **Locust**: $(python3 -c "import locust" >/dev/null 2>&1 && echo "✅ Available" || echo "❌ Not available")

### Infrastructure
- **Docker**: $(command -v docker >/dev/null 2>&1 && echo "✅ Installed" || echo "❌ Not installed")
- **Docker Compose**: $(command -v docker-compose >/dev/null 2>&1 && echo "✅ Installed" || echo "❌ Not installed")
- **Python 3**: $(command -v python3 >/dev/null 2>&1 && echo "✅ Available" || echo "❌ Not available")

### Services
- **API Service**: $(curl -sf "$TARGET_URL/api/v1/health" >/dev/null 2>&1 && echo "✅ Running" || echo "❌ Not accessible")
- **Frontend**: $(curl -sf "$FRONTEND_URL" >/dev/null 2>&1 && echo "✅ Running" || echo "❌ Not accessible")
- **Prometheus**: $(curl -sf "$PROMETHEUS_URL/api/v1/status/config" >/dev/null 2>&1 && echo "✅ Running" || echo "❌ Not accessible")
- **Grafana**: $(curl -sf "$GRAFANA_URL/api/health" >/dev/null 2>&1 && echo "✅ Running" || echo "❌ Not accessible")

## Quick Start Guide

$(if [ $FAILED_CHECKS -eq 0 ]; then
cat << 'QUICKSTART'
The system is ready to use! Here are the next steps:

### Running Load Tests

1. **K6 Load Testing**:
   ```bash
   k6 run --duration 300s --vus 50 tests/load/k6-load-tests.js
   ```

2. **Artillery Testing**:
   ```bash
   artillery run tests/load/artillery-tests.yml
   ```

3. **Locust Testing**:
   ```bash
   locust -f tests/load/locust/locustfile.py --host=$TARGET_URL
   ```

### Performance Monitoring

1. **Grafana Dashboard**: http://localhost:3001
2. **Prometheus Metrics**: http://localhost:9090
3. **Performance Dashboard**: Import monitoring/performance-dashboard.json

### Automated Testing

1. **CI/CD Performance Tests**:
   ```bash
   ./scripts/ci/performance-tests.sh
   ```

2. **Benchmark Testing**:
   ```bash
   ./scripts/performance/benchmark.sh
   ```

### Configuration

- Nginx optimization: config/nginx-optimized.conf
- PostgreSQL tuning: config/postgresql-performance.conf
- Redis optimization: config/redis-performance.conf
- Docker performance: config/docker-performance.yml
QUICKSTART
else
cat << 'ISSUES'
Please resolve the failed checks before using the system:

### Common Issues and Solutions

1. **Missing Tools**: Install required tools using package managers
   - K6: https://k6.io/docs/getting-started/installation/
   - Artillery: `npm install -g artillery`
   - Locust: `pip3 install locust`

2. **Service Not Running**: Start services using Docker Compose
   ```bash
   docker-compose up -d
   ```

3. **Permission Issues**: Make scripts executable
   ```bash
   chmod +x scripts/performance/*.sh scripts/ci/*.sh
   ```

4. **Missing Dependencies**: Install Python packages
   ```bash
   pip3 install requests matplotlib pandas numpy
   ```
ISSUES
fi)

## Documentation

- **Performance Analysis**: docs/PERFORMANCE_ANALYSIS.md
- **Capacity Planning**: docs/CAPACITY_PLANNING.md
- **Load Testing Guide**: tests/load/README.md (if available)

---

**Validation completed at**: $(date)
EOF

    log_success "Validation report generated: $VALIDATION_REPORT"
}

# Main validation function
main() {
    log_info "Starting comprehensive performance system validation"
    log_info "Project root: $PROJECT_ROOT"
    
    # Check required tools
    log_section "Required Tools Validation"
    check_command "curl" "cURL tool"
    check_command "jq" "jq JSON processor"
    check_command "docker" "Docker engine"
    check_command "docker-compose" "Docker Compose"
    check_command "python3" "Python 3"
    check_command "k6" "K6 load testing tool"
    check_command "artillery" "Artillery load testing tool"
    
    # Validate directory structure
    log_section "Directory Structure Validation"
    validate_directory_structure
    
    # Validate all files
    validate_configuration_files
    validate_load_testing_files
    validate_monitoring_config
    validate_scripts
    validate_documentation
    
    # Test environment
    test_docker_environment
    test_service_connectivity
    test_load_testing_tools
    
    # Run quick tests
    run_quick_tests
    
    # Generate report
    generate_validation_report
    
    # Final summary
    echo
    echo "================================================================"
    echo "PERFORMANCE SYSTEM VALIDATION SUMMARY"
    echo "================================================================"
    echo "Total Checks: $TOTAL_CHECKS"
    echo "Failed Checks: $FAILED_CHECKS"
    echo "Success Rate: $(( (TOTAL_CHECKS - FAILED_CHECKS) * 100 / TOTAL_CHECKS ))%"
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        echo
        log_success "🎉 All validation checks passed! System is ready for use."
        echo
        echo "Next steps:"
        echo "1. Review the validation report: $VALIDATION_REPORT"
        echo "2. Run comprehensive load tests: ./scripts/performance/benchmark.sh"
        echo "3. Set up monitoring dashboards"
        echo "4. Configure alerts and thresholds"
    elif [ $FAILED_CHECKS -lt 5 ]; then
        echo
        log_warning "⚠️ System is mostly operational with $FAILED_CHECKS minor issues."
        echo "Review the validation report and fix issues: $VALIDATION_REPORT"
    else
        echo
        log_error "❌ System has $FAILED_CHECKS significant issues."
        echo "Please fix critical issues before using the system."
        echo "See validation report for details: $VALIDATION_REPORT"
    fi
    
    echo "================================================================"
    
    # Exit with appropriate code
    if [ $FAILED_CHECKS -eq 0 ]; then
        exit 0
    elif [ $FAILED_CHECKS -lt 5 ]; then
        exit 1
    else
        exit 2
    fi
}

# Script usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Validates the complete Selextract Cloud load testing and optimization system.

Options:
    --target-url URL      Target API URL (default: http://localhost:8000)
    --frontend-url URL    Frontend URL (default: http://localhost:3000)
    --grafana-url URL     Grafana URL (default: http://localhost:3001)
    --prometheus-url URL  Prometheus URL (default: http://localhost:9090)
    --help               Show this help message

Examples:
    $0                                    # Validate with default URLs
    $0 --target-url https://api.example.com  # Validate remote API
    $0 --help                             # Show help

Exit Codes:
    0 - All checks passed
    1 - Minor issues (1-4 failed checks)
    2 - Major issues (5+ failed checks)
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --target-url)
            TARGET_URL="$2"
            shift 2
            ;;
        --frontend-url)
            FRONTEND_URL="$2"
            shift 2
            ;;
        --grafana-url)
            GRAFANA_URL="$2"
            shift 2
            ;;
        --prometheus-url)
            PROMETHEUS_URL="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Run main function
main "$@"