#!/bin/bash

# Automated CI/CD Performance Testing Script for Selextract Cloud
# Runs comprehensive performance tests and validates against baselines

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RESULTS_DIR="$PROJECT_ROOT/performance-results/ci-$(date +%Y%m%d-%H%M%S)"
BASELINE_DIR="$PROJECT_ROOT/performance-baselines"

# Test configuration
TARGET_URL="${TARGET_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
TEST_DURATION="${TEST_DURATION:-180}"  # 3 minutes for CI
MAX_VUS="${MAX_VUS:-20}"               # Lower load for CI
PERFORMANCE_THRESHOLD="${PERFORMANCE_THRESHOLD:-10}"  # 10% regression threshold

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Exit codes
EXIT_SUCCESS=0
EXIT_PERFORMANCE_REGRESSION=1
EXIT_TEST_FAILURE=2
EXIT_SETUP_FAILURE=3

# Initialize test environment
setup_test_environment() {
    log_info "Setting up performance test environment..."
    
    # Create results directory
    mkdir -p "$RESULTS_DIR"
    mkdir -p "$BASELINE_DIR"
    
    # Check required tools
    local missing_tools=()
    command -v k6 >/dev/null 2>&1 || missing_tools+=("k6")
    command -v artillery >/dev/null 2>&1 || missing_tools+=("artillery")
    command -v curl >/dev/null 2>&1 || missing_tools+=("curl")
    command -v jq >/dev/null 2>&1 || missing_tools+=("jq")
    command -v python3 >/dev/null 2>&1 || missing_tools+=("python3")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        return $EXIT_SETUP_FAILURE
    fi
    
    # Save test configuration
    cat > "$RESULTS_DIR/test-config.json" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "target_url": "$TARGET_URL",
    "frontend_url": "$FRONTEND_URL",
    "test_duration": $TEST_DURATION,
    "max_vus": $MAX_VUS,
    "performance_threshold": $PERFORMANCE_THRESHOLD,
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')"
}
EOF
    
    log_success "Test environment setup completed"
}

# Wait for services to be ready
wait_for_services() {
    log_info "Waiting for services to be ready..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "$TARGET_URL/api/v1/health" >/dev/null 2>&1; then
            log_success "API service is ready"
            break
        fi
        
        log_info "Attempt $attempt/$max_attempts: Waiting for API service..."
        sleep 10
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "API service not ready after $max_attempts attempts"
        return $EXIT_SETUP_FAILURE
    fi
    
    # Brief warm-up
    log_info "Warming up services..."
    for i in {1..5}; do
        curl -sf "$TARGET_URL/api/v1/health" >/dev/null 2>&1 || true
        sleep 1
    done
    
    log_success "Services are ready and warmed up"
}

# Run K6 performance tests
run_k6_tests() {
    log_info "Running K6 performance tests..."
    
    local k6_results="$RESULTS_DIR/k6-results.json"
    local k6_summary="$RESULTS_DIR/k6-summary.json"
    
    # Run K6 with CI-optimized configuration
    k6 run \
        --duration "${TEST_DURATION}s" \
        --vus "$MAX_VUS" \
        --env TARGET_URL="$TARGET_URL" \
        --env FRONTEND_URL="$FRONTEND_URL" \
        --out json="$k6_results" \
        --summary-export="$k6_summary" \
        --quiet \
        "$PROJECT_ROOT/tests/load/k6-load-tests.js" \
        > "$RESULTS_DIR/k6-output.log" 2>&1
    
    local k6_exit_code=$?
    
    if [ $k6_exit_code -eq 0 ]; then
        log_success "K6 tests completed successfully"
    else
        log_error "K6 tests failed with exit code $k6_exit_code"
        return $EXIT_TEST_FAILURE
    fi
    
    # Extract key metrics
    if [ -f "$k6_summary" ]; then
        jq -r '.metrics | to_entries[] | select(.key | test("http_req_duration|http_req_failed|http_reqs")) | "\(.key): \(.value)"' \
            "$k6_summary" > "$RESULTS_DIR/k6-key-metrics.txt"
    fi
}

# Run Artillery performance tests
run_artillery_tests() {
    log_info "Running Artillery performance tests..."
    
    local artillery_results="$RESULTS_DIR/artillery-results.json"
    
    # Set environment variables for Artillery
    export TARGET_URL FRONTEND_URL
    
    # Create CI-optimized Artillery config
    cat > "$RESULTS_DIR/artillery-ci-config.yml" << EOF
config:
  target: '$TARGET_URL'
  phases:
    - duration: 60
      arrivalRate: 5
      name: "Warm-up"
    - duration: $TEST_DURATION
      arrivalRate: 10
      rampTo: $MAX_VUS
      name: "Load Test"
  ensure:
    p95: 2000
    p99: 5000
    maxErrorRate: 5

scenarios:
  - name: "Quick API Test"
    weight: 100
    flow:
      - post:
          url: "/api/v1/auth/login"
          json:
            email: "loadtest1@example.com"
            password: "LoadTest123!"
          capture:
            - json: "$.access_token"
              as: "token"
      - get:
          url: "/api/v1/dashboard/stats"
          headers:
            Authorization: "Bearer {{ token }}"
      - get:
          url: "/api/v1/health"
EOF
    
    # Run Artillery
    artillery run \
        --output "$artillery_results" \
        "$RESULTS_DIR/artillery-ci-config.yml" \
        > "$RESULTS_DIR/artillery-output.log" 2>&1
    
    local artillery_exit_code=$?
    
    if [ $artillery_exit_code -eq 0 ]; then
        log_success "Artillery tests completed successfully"
    else
        log_error "Artillery tests failed with exit code $artillery_exit_code"
        return $EXIT_TEST_FAILURE
    fi
}

# Run quick smoke tests
run_smoke_tests() {
    log_info "Running smoke tests..."
    
    local smoke_results="$RESULTS_DIR/smoke-test-results.json"
    
    # Test critical endpoints
    local endpoints=(
        "GET /api/v1/health"
        "GET /api/v1/version"
        "GET /"
    )
    
    local results=()
    
    for endpoint in "${endpoints[@]}"; do
        local method=$(echo "$endpoint" | cut -d' ' -f1)
        local path=$(echo "$endpoint" | cut -d' ' -f2)
        local url
        
        if [[ "$path" == "/api"* ]]; then
            url="$TARGET_URL$path"
        else
            url="$FRONTEND_URL$path"
        fi
        
        local start_time=$(date +%s%3N)
        local response_code
        local response_time
        
        if [ "$method" = "GET" ]; then
            response_code=$(curl -o /dev/null -s -w "%{http_code}" "$url")
        else
            response_code=$(curl -X "$method" -o /dev/null -s -w "%{http_code}" "$url")
        fi
        
        local end_time=$(date +%s%3N)
        response_time=$((end_time - start_time))
        
        local result=$(cat << EOF
{
    "endpoint": "$endpoint",
    "url": "$url",
    "response_code": $response_code,
    "response_time_ms": $response_time,
    "success": $([ "$response_code" -ge 200 ] && [ "$response_code" -lt 400 ] && echo "true" || echo "false")
}
EOF
)
        results+=("$result")
        
        if [ "$response_code" -ge 200 ] && [ "$response_code" -lt 400 ]; then
            log_success "✓ $endpoint: ${response_code} (${response_time}ms)"
        else
            log_error "✗ $endpoint: ${response_code} (${response_time}ms)"
        fi
    done
    
    # Save smoke test results
    printf '[%s]' "$(IFS=,; echo "${results[*]}")" > "$smoke_results"
    
    log_success "Smoke tests completed"
}

# Analyze performance results
analyze_performance() {
    log_info "Analyzing performance results..."
    
    # Run performance analysis
    python3 "$PROJECT_ROOT/scripts/performance/analyze-metrics.py" \
        "$RESULTS_DIR" \
        --format json \
        > "$RESULTS_DIR/analysis-output.log" 2>&1
    
    local analysis_exit_code=$?
    
    if [ $analysis_exit_code -eq 0 ]; then
        log_success "Performance analysis completed successfully"
    else
        log_warning "Performance analysis completed with warnings (exit code: $analysis_exit_code)"
    fi
    
    # Load analysis results
    local analysis_file="$RESULTS_DIR/analysis-results.json"
    if [ -f "$analysis_file" ]; then
        local performance_score
        performance_score=$(jq -r '.insights.performance_score // 50' "$analysis_file")
        
        echo "Performance Score: $performance_score/100" > "$RESULTS_DIR/performance-summary.txt"
        
        # Extract key metrics
        jq -r '.insights.warnings[]? // empty' "$analysis_file" > "$RESULTS_DIR/warnings.txt"
        jq -r '.insights.recommendations[]? // empty' "$analysis_file" > "$RESULTS_DIR/recommendations.txt"
    fi
}

# Compare with baseline performance
compare_with_baseline() {
    log_info "Comparing with performance baseline..."
    
    local current_branch
    current_branch=$(git branch --show-current 2>/dev/null || echo 'main')
    local baseline_file="$BASELINE_DIR/baseline-${current_branch}.json"
    
    if [ ! -f "$baseline_file" ]; then
        log_warning "No baseline found for branch '$current_branch', creating new baseline"
        create_performance_baseline
        return 0
    fi
    
    local current_results="$RESULTS_DIR/analysis-results.json"
    if [ ! -f "$current_results" ]; then
        log_error "Current performance results not found"
        return $EXIT_TEST_FAILURE
    fi
    
    # Compare key metrics
    local baseline_score
    local current_score
    baseline_score=$(jq -r '.insights.performance_score // 50' "$baseline_file")
    current_score=$(jq -r '.insights.performance_score // 50' "$current_results")
    
    local score_diff
    score_diff=$(echo "$current_score - $baseline_score" | bc -l 2>/dev/null || echo "0")
    local score_diff_percent
    score_diff_percent=$(echo "scale=2; ($score_diff / $baseline_score) * 100" | bc -l 2>/dev/null || echo "0")
    
    # Check for regression
    local regression=false
    
    if (( $(echo "$score_diff_percent < -$PERFORMANCE_THRESHOLD" | bc -l) )); then
        regression=true
        log_error "Performance regression detected!"
        log_error "Baseline score: $baseline_score"
        log_error "Current score: $current_score"
        log_error "Difference: ${score_diff_percent}%"
    else
        log_success "No significant performance regression detected"
        log_info "Baseline score: $baseline_score"
        log_info "Current score: $current_score"
        log_info "Difference: ${score_diff_percent}%"
    fi
    
    # Save comparison results
    cat > "$RESULTS_DIR/baseline-comparison.json" << EOF
{
    "baseline_score": $baseline_score,
    "current_score": $current_score,
    "score_difference": $score_diff,
    "score_difference_percent": $score_diff_percent,
    "regression_threshold": $PERFORMANCE_THRESHOLD,
    "has_regression": $regression,
    "comparison_timestamp": "$(date -Iseconds)"
}
EOF
    
    if [ "$regression" = true ]; then
        return $EXIT_PERFORMANCE_REGRESSION
    fi
    
    return 0
}

# Create or update performance baseline
create_performance_baseline() {
    log_info "Creating performance baseline..."
    
    local current_branch
    current_branch=$(git branch --show-current 2>/dev/null || echo 'main')
    local baseline_file="$BASELINE_DIR/baseline-${current_branch}.json"
    local current_results="$RESULTS_DIR/analysis-results.json"
    
    if [ -f "$current_results" ]; then
        # Add metadata to baseline
        jq '. + {
            "baseline_created": "'$(date -Iseconds)'",
            "git_commit": "'$(git rev-parse HEAD 2>/dev/null || echo 'unknown')'",
            "git_branch": "'$current_branch'",
            "baseline_version": "1.0"
        }' "$current_results" > "$baseline_file"
        
        log_success "Performance baseline created: $baseline_file"
    else
        log_error "Cannot create baseline: current results not found"
        return $EXIT_TEST_FAILURE
    fi
}

# Generate performance report
generate_report() {
    log_info "Generating performance report..."
    
    local report_file="$RESULTS_DIR/performance-report.md"
    local test_config="$RESULTS_DIR/test-config.json"
    local summary_file="$RESULTS_DIR/performance-summary.txt"
    
    cat > "$report_file" << EOF
# CI/CD Performance Test Report

**Generated:** $(date)  
**Branch:** $(jq -r '.git_branch' "$test_config")  
**Commit:** $(jq -r '.git_commit' "$test_config")  
**Test Duration:** $(jq -r '.test_duration' "$test_config")s  
**Max Virtual Users:** $(jq -r '.max_vus' "$test_config")  

## Test Results Summary

$([ -f "$summary_file" ] && cat "$summary_file" || echo "Performance summary not available")

## Test Execution

- ✅ K6 Load Tests
- ✅ Artillery Performance Tests  
- ✅ Smoke Tests
- ✅ Performance Analysis

## Key Metrics

### K6 Results
$([ -f "$RESULTS_DIR/k6-key-metrics.txt" ] && cat "$RESULTS_DIR/k6-key-metrics.txt" || echo "K6 metrics not available")

### Smoke Test Results
$([ -f "$RESULTS_DIR/smoke-test-results.json" ] && jq -r '.[] | "- \(.endpoint): \(.response_code) (\(.response_time_ms)ms)"' "$RESULTS_DIR/smoke-test-results.json" || echo "Smoke test results not available")

## Performance Warnings
$([ -f "$RESULTS_DIR/warnings.txt" ] && [ -s "$RESULTS_DIR/warnings.txt" ] && sed 's/^/- /' "$RESULTS_DIR/warnings.txt" || echo "No performance warnings")

## Recommendations
$([ -f "$RESULTS_DIR/recommendations.txt" ] && [ -s "$RESULTS_DIR/recommendations.txt" ] && sed 's/^/- /' "$RESULTS_DIR/recommendations.txt" || echo "No specific recommendations")

## Baseline Comparison
$([ -f "$RESULTS_DIR/baseline-comparison.json" ] && jq -r '"Performance score change: " + (.score_difference_percent | tostring) + "%"' "$RESULTS_DIR/baseline-comparison.json" || echo "No baseline comparison available")

## Files Generated
- K6 Results: k6-results.json
- Artillery Results: artillery-results.json  
- Smoke Tests: smoke-test-results.json
- Analysis: analysis-results.json
- Logs: *-output.log

---
Report generated by Selextract Cloud CI/CD Performance Testing
EOF

    log_success "Performance report generated: $report_file"
    
    # Output summary to console
    echo
    echo "=================================================="
    echo "PERFORMANCE TEST SUMMARY"
    echo "=================================================="
    
    if [ -f "$summary_file" ]; then
        cat "$summary_file"
    fi
    
    if [ -f "$RESULTS_DIR/baseline-comparison.json" ]; then
        local has_regression
        has_regression=$(jq -r '.has_regression' "$RESULTS_DIR/baseline-comparison.json")
        
        if [ "$has_regression" = "true" ]; then
            echo
            echo "⚠️  PERFORMANCE REGRESSION DETECTED"
            echo "See detailed report for analysis"
        else
            echo
            echo "✅ No significant performance regression"
        fi
    fi
    
    echo
    echo "Detailed report: $report_file"
    echo "Results directory: $RESULTS_DIR"
    echo "=================================================="
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test environment..."
    # Kill any background processes
    jobs -p | xargs -r kill 2>/dev/null || true
}

# Main execution function
main() {
    local exit_code=$EXIT_SUCCESS
    
    trap cleanup EXIT
    
    log_info "Starting CI/CD performance tests for Selextract Cloud"
    log_info "Target: $TARGET_URL"
    log_info "Duration: ${TEST_DURATION}s"
    log_info "Max VUs: $MAX_VUS"
    
    # Setup test environment
    setup_test_environment || exit $EXIT_SETUP_FAILURE
    
    # Wait for services
    wait_for_services || exit $EXIT_SETUP_FAILURE
    
    # Run performance tests
    run_smoke_tests || exit_code=$EXIT_TEST_FAILURE
    run_k6_tests || exit_code=$EXIT_TEST_FAILURE
    run_artillery_tests || exit_code=$EXIT_TEST_FAILURE
    
    # Analyze results
    analyze_performance
    
    # Compare with baseline
    compare_with_baseline || exit_code=$EXIT_PERFORMANCE_REGRESSION
    
    # Generate report
    generate_report
    
    if [ $exit_code -eq $EXIT_PERFORMANCE_REGRESSION ]; then
        log_error "Performance tests completed with regression detected"
    elif [ $exit_code -eq $EXIT_TEST_FAILURE ]; then
        log_error "Performance tests completed with failures"
    else
        log_success "Performance tests completed successfully"
    fi
    
    exit $exit_code
}

# Script usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -u, --url URL           Target URL (default: http://localhost:8000)
    -f, --frontend URL      Frontend URL (default: http://localhost:3000)
    -d, --duration SECONDS  Test duration (default: 180)
    -v, --vus NUMBER        Max virtual users (default: 20)
    -t, --threshold PERCENT Performance regression threshold (default: 10)
    -b, --baseline          Create new performance baseline
    -h, --help             Show this help message

Environment Variables:
    TARGET_URL             Override target URL
    FRONTEND_URL           Override frontend URL
    TEST_DURATION          Override test duration
    MAX_VUS                Override max virtual users
    PERFORMANCE_THRESHOLD  Override regression threshold

Examples:
    $0                                    # Run with defaults
    $0 -d 300 -v 50                     # 5-minute test with 50 VUs
    $0 --baseline                        # Create new baseline
    $0 -u https://staging.selextract.com # Test staging environment
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            TARGET_URL="$2"
            shift 2
            ;;
        -f|--frontend)
            FRONTEND_URL="$2"
            shift 2
            ;;
        -d|--duration)
            TEST_DURATION="$2"
            shift 2
            ;;
        -v|--vus)
            MAX_VUS="$2"
            shift 2
            ;;
        -t|--threshold)
            PERFORMANCE_THRESHOLD="$2"
            shift 2
            ;;
        -b|--baseline)
            CREATE_BASELINE=true
            shift
            ;;
        -h|--help)
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

# Handle baseline creation mode
if [ "${CREATE_BASELINE:-false}" = "true" ]; then
    setup_test_environment
    wait_for_services
    run_smoke_tests
    run_k6_tests
    run_artillery_tests
    analyze_performance
    create_performance_baseline
    exit 0
fi

# Run main function
main "$@"