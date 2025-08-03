#!/bin/bash

# Database Migration Management Script for Selextract Cloud
# This script provides safe, production-ready database migration operations
# Following the standards defined in rules.md Section 5.1

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
API_DIR="$PROJECT_ROOT/api"

# Color output
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

# Environment validation
validate_environment() {
    log_info "Validating environment..."
    
    # Check if we're in the correct directory
    if [[ ! -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
        log_error "Must be run from the project root directory"
        exit 1
    fi
    
    # Check if Alembic is configured
    if [[ ! -f "$API_DIR/alembic.ini" ]]; then
        log_error "Alembic configuration not found at $API_DIR/alembic.ini"
        exit 1
    fi
    
    # Check database connection
    if [[ -z "${DATABASE_URL:-}" ]]; then
        log_error "DATABASE_URL environment variable not set"
        exit 1
    fi
    
    log_success "Environment validation passed"
}

# Database backup before migration
create_backup() {
    local environment="$1"
    log_info "Creating database backup for $environment environment..."
    
    # Extract database info from DATABASE_URL
    local db_url="${DATABASE_URL}"
    local db_name=$(echo "$db_url" | sed -n 's/.*\/\([^?]*\).*/\1/p')
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="backup_${environment}_${timestamp}.sql"
    
    # Create backup using pg_dump
    if command -v pg_dump &> /dev/null; then
        pg_dump "$DATABASE_URL" > "$PROJECT_ROOT/backups/$backup_file"
        log_success "Database backup created: $backup_file"
        echo "$backup_file"
    else
        log_error "pg_dump not found. Install PostgreSQL client tools."
        exit 1
    fi
}

# Run migration with validation
run_migration() {
    local environment="$1"
    local target="${2:-head}"
    
    log_info "Running migration for $environment environment (target: $target)..."
    
    # Change to API directory for Alembic operations
    cd "$API_DIR"
    
    # Check current migration status
    log_info "Current migration status:"
    alembic current
    
    # Show pending migrations
    log_info "Pending migrations:"
    alembic show "$target"
    
    # Confirm migration in production
    if [[ "$environment" == "production" ]]; then
        log_warning "You are about to run migrations in PRODUCTION environment!"
        read -p "Are you sure you want to continue? (yes/no): " confirmation
        if [[ "$confirmation" != "yes" ]]; then
            log_info "Migration cancelled by user"
            exit 0
        fi
    fi
    
    # Run the migration
    log_info "Executing migration..."
    if alembic upgrade "$target"; then
        log_success "Migration completed successfully"
    else
        log_error "Migration failed"
        exit 1
    fi
    
    # Show final status
    log_info "Final migration status:"
    alembic current
    
    cd "$PROJECT_ROOT"
}

# Rollback migration
rollback_migration() {
    local environment="$1"
    local target="$2"
    
    log_warning "Rolling back migration for $environment environment to $target..."
    
    # Extra confirmation for rollback
    if [[ "$environment" == "production" ]]; then
        log_warning "You are about to ROLLBACK migrations in PRODUCTION!"
        read -p "Are you absolutely sure? Type 'ROLLBACK' to confirm: " confirmation
        if [[ "$confirmation" != "ROLLBACK" ]]; then
            log_info "Rollback cancelled by user"
            exit 0
        fi
    fi
    
    cd "$API_DIR"
    
    log_info "Current migration status:"
    alembic current
    
    log_info "Rolling back to: $target"
    if alembic downgrade "$target"; then
        log_success "Rollback completed successfully"
    else
        log_error "Rollback failed"
        exit 1
    fi
    
    log_info "Final migration status:"
    alembic current
    
    cd "$PROJECT_ROOT"
}

# Generate new migration
generate_migration() {
    local message="$1"
    
    log_info "Generating new migration: $message"
    
    cd "$API_DIR"
    
    # Check for model changes
    log_info "Checking for model changes..."
    if alembic revision --autogenerate -m "$message"; then
        log_success "Migration generated successfully"
        
        # Show the generated migration file
        local latest_migration=$(alembic heads)
        log_info "Generated migration: $latest_migration"
        
        # List migration files for review
        log_info "Please review the generated migration file before applying it:"
        ls -la alembic/versions/
    else
        log_error "Migration generation failed"
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Validate migration integrity
validate_migration() {
    log_info "Validating migration integrity..."
    
    cd "$API_DIR"
    
    # Check migration history
    log_info "Migration history:"
    alembic history
    
    # Check current status
    log_info "Current migration status:"
    alembic current
    
    # Validate migration scripts
    log_info "Validating migration scripts..."
    if alembic check; then
        log_success "Migration validation passed"
    else
        log_error "Migration validation failed"
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Display usage information
show_usage() {
    cat << EOF
Database Migration Management Script

Usage: $0 <command> [options]

Commands:
    migrate <env> [target]    - Run migrations (env: development|staging|production)
    rollback <env> <target>   - Rollback to specific migration
    generate <message>        - Generate new migration with message
    status                    - Show current migration status
    validate                  - Validate migration integrity
    history                   - Show migration history

Examples:
    $0 migrate development              # Migrate to latest
    $0 migrate production head          # Migrate production to latest
    $0 rollback development -1          # Rollback one migration
    $0 generate "Add user preferences"  # Generate new migration
    $0 status                          # Show current status

Environment Variables:
    DATABASE_URL - Database connection string (required)

EOF
}

# Main script logic
main() {
    # Ensure backups directory exists
    mkdir -p "$PROJECT_ROOT/backups"
    
    case "${1:-}" in
        "migrate")
            if [[ $# -lt 2 ]]; then
                log_error "Environment required for migrate command"
                show_usage
                exit 1
            fi
            
            local environment="$2"
            local target="${3:-head}"
            
            validate_environment
            
            # Create backup for production
            if [[ "$environment" == "production" ]]; then
                create_backup "$environment"
            fi
            
            run_migration "$environment" "$target"
            ;;
            
        "rollback")
            if [[ $# -lt 3 ]]; then
                log_error "Environment and target required for rollback command"
                show_usage
                exit 1
            fi
            
            local environment="$2"
            local target="$3"
            
            validate_environment
            
            # Create backup before rollback
            create_backup "$environment"
            
            rollback_migration "$environment" "$target"
            ;;
            
        "generate")
            if [[ $# -lt 2 ]]; then
                log_error "Message required for generate command"
                show_usage
                exit 1
            fi
            
            local message="$2"
            validate_environment
            generate_migration "$message"
            ;;
            
        "status")
            validate_environment
            cd "$API_DIR"
            log_info "Current migration status:"
            alembic current
            ;;
            
        "validate")
            validate_environment
            validate_migration
            ;;
            
        "history")
            validate_environment
            cd "$API_DIR"
            log_info "Migration history:"
            alembic history
            ;;
            
        *)
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"