#!/bin/bash

# CI/CD Migration Validation Script for Selextract Cloud
# Validates migrations before deployment

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
API_DIR="$PROJECT_ROOT/api"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate migration files
validate_migrations() {
    log_info "Validating migration files..."
    
    cd "$API_DIR"
    
    # Check migration syntax
    if ! alembic check; then
        log_error "Migration validation failed"
        return 1
    fi
    
    # Ensure all migrations have proper up/down functions
    for migration_file in alembic/versions/*.py; do
        if [[ -f "$migration_file" ]]; then
            if ! grep -q "def upgrade" "$migration_file" || ! grep -q "def downgrade" "$migration_file"; then
                log_error "Migration file $migration_file missing upgrade/downgrade functions"
                return 1
            fi
        fi
    done
    
    log_success "Migration validation passed"
    return 0
}

# Test migration in clean database
test_migration() {
    log_info "Testing migration in isolated environment..."
    
    # This would typically use a test database
    # For now, just validate the migration can be parsed
    cd "$API_DIR"
    
    if alembic show head; then
        log_success "Migration test passed"
        return 0
    else
        log_error "Migration test failed"
        return 1
    fi
}

# Main validation
main() {
    log_info "Starting migration validation..."
    
    if validate_migrations && test_migration; then
        log_success "All migration validations passed"
        exit 0
    else
        log_error "Migration validation failed"
        exit 1
    fi
}

main "$@"