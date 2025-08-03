#!/bin/bash

# Automated Performance Benchmarking Script for Selextract Cloud
# Runs comprehensive performance tests and generates reports

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BENCHMARK_DIR="$PROJECT_ROOT/performance-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_DIR="$BENCHMARK_DIR/$TIMESTAMP"

# Test configuration
TARGET_URL="${TARGET_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
TEST_DURATION="${TEST_DURATION:-300}"  # 5 minutes default
MAX_VUS="${MAX_VUS:-50}"               # Maximum virtual users
WARM_UP_TIME="${WARM_UP_TIME:-60}"     # Warm-up duration in seconds

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check for required tools
    command -v k6 >/dev/null 2>&1 || missing_deps+=("k6")
    command -v artillery >/dev/null 2>&1 || missing_deps+=("artillery")
    command -v locust >/dev/null 2>&1 || missing_deps+=("locust")
    command -v curl >/dev/null 2>&1 || missing_deps+=("curl")
    command -v jq >/dev/null 2>&1 || missing_deps+=("jq")
    command -v docker >/dev/null 2>&1 || missing_deps+=("docker")
    command -v python3 >/dev/null 2>&1 || missing_deps+=("python3")
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Install missing dependencies:"
        for dep in "${missing_deps[@]}"; do
            case $dep in
                k6)
                    echo "  curl https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz | tar xvz --strip-components 1"
                    ;;
                artillery)
                    echo "  npm install -g artillery"
                    ;;
                locust)
                    echo "  pip3 install locust"
                    ;;
                *)
                    echo "  Install $dep using your system package manager"
                    ;;
            esac
        done
        exit 1
    fi
    
    log_success "All prerequisites satisfied"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Check API health
    if ! curl -sf "$TARGET_URL/api/v1/health" >/dev/null; then
        log_error "API health check failed at $TARGET_URL"
        return 1
    fi
    
    # Check frontend health
    if ! curl -sf "$FRONTEND_URL" >/dev/null; then
        log_warning "Frontend health check failed at $FRONTEND_URL"
    fi
    
    # Check database connectivity
    if ! docker exec selextract-db-1 pg_isready -U postgres >/dev/null 2>&1; then
        log_error "Database health check failed"
        return 1
    fi
    
    # Check Redis connectivity
    if ! docker exec selextract-redis-1 redis-cli ping >/dev/null 2>&1; then
        log_error "Redis health check failed"
        return 1
    fi
    
    log_success "All services are healthy"
}

# System metrics collection
collect_system_metrics() {
    log_info "Collecting system metrics..."
    
    local metrics_file="$RESULTS_DIR/system-metrics-before.json"
    
    # CPU and memory usage
    cat > "$metrics_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "cpu": {
        "load_average": $(uptime | awk -F'load average:' '{print $2}' | tr -d ' '),
        "cores": $(nproc)
    },
    "memory": {
        "total_mb": $(free -m | awk 'NR==2{print $2}'),
        "used_mb": $(free -m | awk 'NR==2{print $3}'),
        "available_mb": $(free -m | awk 'NR==2{print $7}')
    },
    "disk": {
        "usage_percent": $(df / | awk 'NR==2{print $5}' | sed 's/%//'),
        "available_gb": $(df -BG / | awk 'NR==2{print $4}' | sed 's/G//')
    },
    "network": {
        "interfaces": $(ip -j link show | jq '[.[] | select(.operstate == "UP") | .ifname]')
    }
}
EOF

    # Docker container metrics
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" > "$RESULTS_DIR/docker-stats-before.txt"
    
    log_success "System metrics collected"
}

# Warm-up phase
warm_up_system() {
    log_info "Warming up system for $WARM_UP_TIME seconds..."
    
    # Simple warm-up requests
    for i in {1..10}; do
        curl -sf "$TARGET_URL/api/v1/health" >/dev/null || true
        sleep 1
    done
    
    # K6 warm-up
    k6 run --duration "${WARM_UP_TIME}s" --vus 5 \
        --env TARGET_URL="$TARGET_URL" \
        --quiet \
        --no-summary \
        "$PROJECT_ROOT/tests/load/k6-load-tests.js" >/dev/null 2>&1 || true
    
    log_success "System warm-up completed"
}

# Run K6 load tests
run_k6_tests() {
    log_info "Running K6 load tests..."
    
    local k6_results="$RESULTS_DIR/k6-results.json"
    local k6_summary="$RESULTS_DIR/k6-summary.txt"
    
    # Run K6 with custom scenarios
    k6 run \
        --duration "${TEST_DURATION}s" \
        --env TARGET_URL="$TARGET_URL" \
        --env FRONTEND_URL="$FRONTEND_URL" \
        --out json="$k6_results" \
        --summary-export="$k6_summary" \
        "$PROJECT_ROOT/tests/load/k6-load-tests.js" \
        > "$RESULTS_DIR/k6-output.log" 2>&1
    
    # Extract key metrics
    if [ -f "$k6_results" ]; then
        jq -r '.metrics | to_entries[] | select(.key | test("http_req_duration|http_req_failed|http_reqs")) | "\(.key): \(.value)"' \
            "$k6_results" > "$RESULTS_DIR/k6-key-metrics.txt"
    fi
    
    log_success "K6 tests completed"
}

# Run Artillery tests
run_artillery_tests() {
    log_info "Running Artillery tests..."
    
    local artillery_results="$RESULTS_DIR/artillery-results.json"
    
    # Set environment variables
    export TARGET_URL FRONTEND_URL
    
    # Run Artillery
    artillery run \
        --output "$artillery_results" \
        "$PROJECT_ROOT/tests/load/artillery-tests.yml" \
        > "$RESULTS_DIR/artillery-output.log" 2>&1
    
    # Generate HTML report
    if [ -f "$artillery_results" ]; then
        artillery report "$artillery_results" \
            --output "$RESULTS_DIR/artillery-report.html"
    fi
    
    log_success "Artillery tests completed"
}

# Run Locust tests
run_locust_tests() {
    log_info "Running Locust tests..."
    
    # Run Locust in headless mode
    cd "$PROJECT_ROOT/tests/load/locust"
    
    locust \
        --host="$TARGET_URL" \
        --users="$MAX_VUS" \
        --spawn-rate=5 \
        --run-time="${TEST_DURATION}s" \
        --headless \
        --csv="$RESULTS_DIR/locust" \
        --html="$RESULTS_DIR/locust-report.html" \
        > "$RESULTS_DIR/locust-output.log" 2>&1
    
    cd "$PROJECT_ROOT"
    
    log_success "Locust tests completed"
}

# Database performance test
test_database_performance() {
    log_info "Testing database performance..."
    
    local db_results="$RESULTS_DIR/database-performance.txt"
    
    # Run database-specific queries
    docker exec selextract-db-1 psql -U postgres -d selextract -c "
        \timing on
        -- Test simple select
        SELECT COUNT(*) FROM users;
        SELECT COUNT(*) FROM tasks;
        SELECT COUNT(*) FROM billing_usage;
        
        -- Test complex joins
        SELECT u.email, COUNT(t.id) as task_count, AVG(t.compute_units_used) as avg_compute_units
        FROM users u
        LEFT JOIN tasks t ON u.id = t.user_id
        WHERE t.created_at >= NOW() - INTERVAL '30 days'
        GROUP BY u.id, u.email
        ORDER BY task_count DESC
        LIMIT 10;
        
        -- Test aggregations
        SELECT 
            DATE_TRUNC('day', created_at) as day,
            COUNT(*) as tasks_created,
            SUM(compute_units_used) as total_compute_units
        FROM tasks
        WHERE created_at >= NOW() - INTERVAL '7 days'
        GROUP BY day
        ORDER BY day;
    " > "$db_results" 2>&1
    
    # Test connection pool performance
    echo "Testing connection pool..." >> "$db_results"
    for i in {1..20}; do
        {
            docker exec selextract-db-1 psql -U postgres -d selextract -c "SELECT NOW();"
        } &
    done
    wait
    
    log_success "Database performance test completed"
}

# Redis performance test
test_redis_performance() {
    log_info "Testing Redis performance..."
    
    local redis_results="$RESULTS_DIR/redis-performance.txt"
    
    # Test Redis performance
    docker exec selextract-redis-1 redis-benchmark \
        -t set,get,incr,lpush,rpush,lpop,rpop,sadd,hset,spop,zadd,zpopmin,lrange \
        -n 10000 \
        -q > "$redis_results"
    
    # Test specific operations
    echo "Custom Redis operations:" >> "$redis_results"
    docker exec selextract-redis-1 redis-cli --latency-history -i 1 >> "$redis_results" &
    local latency_pid=$!
    
    sleep 30  # Collect latency for 30 seconds
    kill $latency_pid 2>/dev/null || true
    
    log_success "Redis performance test completed"
}

# Worker performance test
test_worker_performance() {
    log_info "Testing worker performance..."
    
    local worker_results="$RESULTS_DIR/worker-performance.txt"
    
    # Get worker queue stats
    docker exec selextract-redis-1 redis-cli info | grep -E "connected_clients|used_memory|instantaneous_ops" > "$worker_results"
    
    # Test task processing capability
    echo "Worker processing test:" >> "$worker_results"
    python3 "$SCRIPT_DIR/test-worker-load.py" >> "$worker_results" 2>&1 || true
    
    log_success "Worker performance test completed"
}

# Collect final system metrics
collect_final_metrics() {
    log_info "Collecting final system metrics..."
    
    local metrics_file="$RESULTS_DIR/system-metrics-after.json"
    
    # CPU and memory usage after tests
    cat > "$metrics_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "cpu": {
        "load_average": $(uptime | awk -F'load average:' '{print $2}' | tr -d ' '),
        "cores": $(nproc)
    },
    "memory": {
        "total_mb": $(free -m | awk 'NR==2{print $2}'),
        "used_mb": $(free -m | awk 'NR==2{print $3}'),
        "available_mb": $(free -m | awk 'NR==2{print $7}')
    },
    "disk": {
        "usage_percent": $(df / | awk 'NR==2{print $5}' | sed 's/%//'),
        "available_gb": $(df -BG / | awk 'NR==2{print $4}' | sed 's/G//')
    }
}
EOF

    # Docker container metrics after tests
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" > "$RESULTS_DIR/docker-stats-after.txt"
    
    log_success "Final metrics collected"
}

# Generate performance report
generate_report() {
    log_info "Generating performance report..."
    
    local report_file="$RESULTS_DIR/performance-report.md"
    
    cat > "$report_file" << EOF
# Selextract Cloud Performance Benchmark Report

**Generated:** $(date)
**Duration:** ${TEST_DURATION} seconds
**Max Virtual Users:** ${MAX_VUS}
**Target:** $TARGET_URL

## Test Configuration

- **Test Duration:** ${TEST_DURATION}s
- **Maximum VUs:** $MAX_VUS
- **Warm-up Time:** ${WARM_UP_TIME}s
- **Target URL:** $TARGET_URL
- **Frontend URL:** $FRONTEND_URL

## System Information

**Before Tests:**
$(cat "$RESULTS_DIR/system-metrics-before.json" | jq -r '
"- CPU Load: " + (.cpu.load_average | tostring) + " (cores: " + (.cpu.cores | tostring) + ")",
"- Memory: " + (.memory.used_mb | tostring) + "MB / " + (.memory.total_mb | tostring) + "MB",
"- Disk Usage: " + (.disk.usage_percent | tostring) + "%"
')

**After Tests:**
$(cat "$RESULTS_DIR/system-metrics-after.json" | jq -r '
"- CPU Load: " + (.cpu.load_average | tostring) + " (cores: " + (.cpu.cores | tostring) + ")",
"- Memory: " + (.memory.used_mb | tostring) + "MB / " + (.memory.total_mb | tostring) + "MB",
"- Disk Usage: " + (.disk.usage_percent | tostring) + "%"
')

## Test Results Summary

### K6 Load Tests
$([ -f "$RESULTS_DIR/k6-key-metrics.txt" ] && cat "$RESULTS_DIR/k6-key-metrics.txt" || echo "K6 results not available")

### Artillery Tests
- Results: artillery-results.json
- Report: artillery-report.html

### Locust Tests
- Results: locust_stats.csv
- Report: locust-report.html

### Database Performance
$([ -f "$RESULTS_DIR/database-performance.txt" ] && head -20 "$RESULTS_DIR/database-performance.txt" || echo "Database performance results not available")

### Redis Performance
$([ -f "$RESULTS_DIR/redis-performance.txt" ] && head -10 "$RESULTS_DIR/redis-performance.txt" || echo "Redis performance results not available")

## Files Generated

- \`k6-results.json\` - Detailed K6 metrics
- \`artillery-results.json\` - Artillery test results
- \`locust_stats.csv\` - Locust statistics
- \`database-performance.txt\` - Database performance metrics
- \`redis-performance.txt\` - Redis performance metrics
- \`docker-stats-before.txt\` - Container stats before tests
- \`docker-stats-after.txt\` - Container stats after tests

## Recommendations

Based on the performance test results:

1. **Monitor Response Times:** Ensure 95th percentile stays under 2 seconds
2. **Database Optimization:** Check slow queries and add indexes as needed
3. **Redis Tuning:** Monitor memory usage and connection pooling
4. **Worker Scaling:** Consider worker scaling if task processing is slow
5. **Resource Allocation:** Adjust container resource limits based on usage

## Analysis

Run the following command to analyze detailed metrics:

\`\`\`bash
python3 scripts/performance/analyze-metrics.py $RESULTS_DIR
\`\`\`
EOF

    log_success "Performance report generated: $report_file"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    # Kill any remaining background processes
    jobs -p | xargs -r kill 2>/dev/null || true
}

# Main execution
main() {
    trap cleanup EXIT
    
    log_info "Starting Selextract Cloud performance benchmark"
    log_info "Results will be saved to: $RESULTS_DIR"
    
    # Create results directory
    mkdir -p "$RESULTS_DIR"
    
    # Save test configuration
    cat > "$RESULTS_DIR/test-config.json" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "target_url": "$TARGET_URL",
    "frontend_url": "$FRONTEND_URL",
    "test_duration": $TEST_DURATION,
    "max_vus": $MAX_VUS,
    "warm_up_time": $WARM_UP_TIME
}
EOF

    # Run benchmark steps
    check_prerequisites
    health_check
    collect_system_metrics
    warm_up_system
    
    # Run performance tests
    run_k6_tests
    run_artillery_tests
    run_locust_tests
    
    # Component-specific tests
    test_database_performance
    test_redis_performance
    test_worker_performance
    
    # Final collection and reporting
    collect_final_metrics
    generate_report
    
    log_success "Performance benchmark completed successfully!"
    log_info "Results available in: $RESULTS_DIR"
    log_info "View the report: $RESULTS_DIR/performance-report.md"
}

# Script usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -u, --url URL           Target URL (default: http://localhost:8000)
    -f, --frontend URL      Frontend URL (default: http://localhost:3000)
    -d, --duration SECONDS  Test duration in seconds (default: 300)
    -v, --vus NUMBER        Maximum virtual users (default: 50)
    -w, --warmup SECONDS    Warm-up time in seconds (default: 60)
    -h, --help             Show this help message

Environment Variables:
    TARGET_URL             Override target URL
    FRONTEND_URL           Override frontend URL
    TEST_DURATION          Override test duration
    MAX_VUS                Override maximum virtual users
    WARM_UP_TIME           Override warm-up time

Examples:
    $0                     # Run with defaults
    $0 -d 600 -v 100       # Run for 10 minutes with 100 VUs
    $0 -u https://prod.selextract.com -d 1800  # Production test
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
        -w|--warmup)
            WARM_UP_TIME="$2"
            shift 2
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

# Run main function
main "$@"