"""
Alembic Environment Configuration for Selextract Cloud

This environment configuration connects Alembic migrations to the SQLAlchemy models
defined in api/models.py, following the production-ready standards from rules.md.
"""

import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add the parent directory to the Python path so we can import our models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our models and database configuration
try:
    from models import Base
    from database import SYNC_DATABASE_URL
except ImportError:
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from api.models import Base
        from api.database import SYNC_DATABASE_URL
    except ImportError as e:
        print(f"Failed to import models: {e}")
        print("Current working directory:", os.getcwd())
        print("Python path:", sys.path)
        raise

# This is the Alembic Config object
config = context.config

# Override sqlalchemy.url with DATABASE_URL environment variable if present
database_url = os.getenv('DATABASE_URL')
if not database_url:
    database_url = SYNC_DATABASE_URL

# Ensure we're using the synchronous PostgreSQL driver for migrations
if database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

config.set_main_option('sqlalchemy.url', database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = database_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            transaction_per_migration=True,
            transactional_ddl=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()