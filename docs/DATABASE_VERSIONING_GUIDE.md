# Database Versioning Guide for Selextract Cloud

## Overview

This guide documents the complete database versioning system for Selextract Cloud, implementing production-ready migration management following the standards defined in [rules.md](../.roo/rules/rules.md).

## Architecture

### Components

- **Alembic**: Database migration tool connected to SQLAlchemy models
- **Migration Scripts**: Automated management and safety procedures  
- **CI/CD Integration**: Validation and automated deployment
- **Backup System**: Automatic backups before production migrations

### Directory Structure

```
api/
├── alembic/                    # Migration configuration
│   ├── env.py                 # Environment configuration
│   ├── script.py.mako         # Migration template
│   └── versions/              # Migration files
├── alembic.ini                # Alembic configuration
└── models.py                  # SQLAlchemy models

scripts/
├── db-migrate.sh              # Main migration management script
└── ci/
    └── migration-validation.sh # CI/CD validation script
```

## Migration Workflow

### Development Workflow

1. **Modify Models**: Update SQLAlchemy models in [`api/models.py`](../api/models.py)
2. **Generate Migration**: 
   ```bash
   DATABASE_URL="postgresql://..." ./scripts/db-migrate.sh generate "Add user preferences"
   ```
3. **Review Migration**: Check the generated file in [`api/alembic/versions/`](../api/alembic/versions/)
4. **Test Migration**:
   ```bash
   DATABASE_URL="postgresql://..." ./scripts/db-migrate.sh migrate development
   ```
5. **Validate**: Run validation checks
   ```bash
   DATABASE_URL="postgresql://..." ./scripts/db-migrate.sh validate
   ```

### Production Deployment

1. **Backup Creation**: Automatic backup before migration
2. **Migration Execution**: Safe deployment with rollback capability
3. **Validation**: Post-migration integrity checks

```bash
# Production migration (includes automatic backup)
DATABASE_URL="postgresql://..." ./scripts/db-migrate.sh migrate production
```

## Migration Commands

### Primary Commands

| Command | Description | Example |
|---------|-------------|---------|
| `migrate <env> [target]` | Run migrations | `./scripts/db-migrate.sh migrate development` |
| `rollback <env> <target>` | Rollback migration | `./scripts/db-migrate.sh rollback development -1` |
| `generate <message>` | Generate new migration | `./scripts/db-migrate.sh generate "Add indexes"` |
| `status` | Show current status | `./scripts/db-migrate.sh status` |
| `validate` | Validate migrations | `./scripts/db-migrate.sh validate` |
| `history` | Show migration history | `./scripts/db-migrate.sh history` |

### Environment Variables

- `DATABASE_URL`: Database connection string (required)
- `SELEXTRACT_DB_*`: Alternative database configuration variables

## Safety Features

### Automatic Backups

- **Production**: Automatic backup before every migration
- **Staging**: Backup before rollbacks
- **Location**: `./backups/` directory with timestamp

### Validation Checks

- Migration file syntax validation
- Database connection verification
- Model-migration consistency checks
- Reversibility validation

### Production Safeguards

- Interactive confirmation for production operations
- Rollback capability for all migrations
- Transaction-based DDL operations
- Comprehensive error handling

## Migration File Structure

### Standard Migration Template

```python
"""Migration description

Revision ID: abc123
Revises: def456
Create Date: 2025-01-01 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'abc123'
down_revision: Union[str, None] = 'def456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Migration changes
    pass

def downgrade() -> None:
    # Rollback changes
    pass
```

### Best Practices

1. **Descriptive Messages**: Use clear, specific migration messages
2. **Reversible Operations**: Always implement proper downgrade functions
3. **Small Changes**: Keep migrations focused and atomic
4. **Data Preservation**: Handle data migration carefully
5. **Index Management**: Add/remove indexes in separate migrations

## Task Schema Evolution

### Schema Versioning

Task configurations use versioned JSON schemas (e.g., `1.0`, `1.1`) for backward compatibility.

### Schema Migration

When task schemas change:

1. **Increment Version**: Update schema version in [`worker/task_schemas.py`](../worker/task_schemas.py)
2. **Migration Function**: Implement `migrate_task_config()` function
3. **Backward Compatibility**: Maintain support for previous versions
4. **Validation**: Update validation rules for new schema

### Example Schema Evolution

```python
def migrate_task_config(config: dict, from_version: str, to_version: str) -> dict:
    """Migrate task configuration between schema versions"""
    if from_version == "1.0" and to_version == "1.1":
        # Add new required fields with defaults
        config.setdefault("timeout_seconds", 300)
        config["schema_version"] = "1.1"
    return config
```

## CI/CD Integration

### Validation Pipeline

The [`scripts/ci/migration-validation.sh`](../scripts/ci/migration-validation.sh) script provides:

- Migration syntax validation
- Database connectivity checks
- Migration test execution
- Rollback capability verification

### Integration Points

- **Pre-commit**: Validate migration files
- **Pull Request**: Check migration consistency
- **Deployment**: Automated migration execution

## Troubleshooting

### Common Issues

1. **Migration Conflicts**: Use `alembic merge` to resolve
2. **Connection Issues**: Verify `DATABASE_URL` configuration
3. **Permission Errors**: Ensure database user has DDL permissions
4. **Schema Drift**: Run `alembic check` to detect inconsistencies

### Recovery Procedures

1. **Failed Migration**: Check error logs and rollback if needed
2. **Corrupted State**: Restore from backup and reapply migrations
3. **Schema Conflicts**: Use manual resolution and mark as resolved

### Monitoring

- Migration execution logs in application logs
- Database schema validation in health checks
- Backup verification in maintenance scripts

## Advanced Operations

### Manual Migration Management

```bash
# Check current revision
cd api && alembic current

# Show migration history  
cd api && alembic history

# Migrate to specific revision
cd api && alembic upgrade abc123

# Generate SQL without executing
cd api && alembic upgrade head --sql
```

### Custom Migration Operations

For complex migrations requiring custom logic:

1. Generate empty migration: `alembic revision -m "custom operation"`
2. Implement custom upgrade/downgrade logic
3. Test thoroughly in development environment
4. Document the custom operation

## Security Considerations

### Database Credentials

- Use environment variables for credentials
- Rotate credentials every 90 days
- Limit database user permissions to required operations
- Use SSL/TLS for database connections

### Migration Security

- Review all migrations for potential security issues
- Validate input data in migration scripts
- Use parameterized queries for data migrations
- Audit trail for all production migrations

## Compliance and Standards

This implementation follows:

- **Rules.md Section 5**: Database and Schema Integrity requirements
- **Production Standards**: Enterprise-grade migration practices
- **Security Guidelines**: Secure credential and data handling
- **Disaster Recovery**: Backup and rollback procedures

## Support and Maintenance

For issues with database versioning:

1. Check the [Troubleshooting Guide](#troubleshooting)
2. Review migration logs in `./logs/`
3. Validate environment configuration
4. Contact the development team for complex issues

---

**Last Updated**: 2025-08-01  
**Version**: 1.0  
**Maintainer**: Selextract Cloud Development Team