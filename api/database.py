import os
import logging
from typing import AsyncGenerator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session
from contextlib import asynccontextmanager

from models import Base

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration and connection management"""
    
    def __init__(self):
        self.database_url = self._get_database_url()
        self.engine: Optional[AsyncEngine] = None
        self.async_session: Optional[async_sessionmaker[AsyncSession]] = None
        
    def _get_database_url(self) -> str:
        """Get database URL from environment with proper async driver"""
        # Try standardized variables first, fallback to legacy
        database_url = os.getenv("DATABASE_URL")
        
        # Construct from standardized components if DATABASE_URL not provided
        if not database_url:
            db_host = os.getenv("SELEXTRACT_DB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
            db_port = os.getenv("SELEXTRACT_DB_PORT", os.getenv("POSTGRES_PORT", "5432"))
            db_name = os.getenv("SELEXTRACT_DB_NAME", os.getenv("POSTGRES_DB", "selextract"))
            db_user = os.getenv("SELEXTRACT_DB_USER", os.getenv("POSTGRES_USER", "postgres"))
            db_password = os.getenv("SELEXTRACT_DB_PASSWORD", os.getenv("POSTGRES_PASSWORD"))
            
            if not db_password:
                raise ValueError("Database password is required (SELEXTRACT_DB_PASSWORD or POSTGRES_PASSWORD)")
            
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Convert to async URL if needed
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not database_url.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql:// or postgresql+asyncpg:// scheme")
        
        return database_url
    
    def create_engine(self) -> AsyncEngine:
        """Create async SQLAlchemy engine with optimal settings"""
        if self.engine is not None:
            return self.engine
            
        # Engine configuration for production - use standardized variables with fallbacks
        engine_kwargs = {
            "echo": os.getenv("SELEXTRACT_DEBUG", os.getenv("SQL_ECHO", "false")).lower() == "true",
            "pool_size": int(os.getenv("SELEXTRACT_DB_POOL_SIZE", os.getenv("DB_POOL_SIZE", "10"))),
            "max_overflow": int(os.getenv("SELEXTRACT_DB_MAX_OVERFLOW", os.getenv("DB_MAX_OVERFLOW", "20"))),
            "pool_timeout": int(os.getenv("SELEXTRACT_DB_POOL_TIMEOUT", os.getenv("DB_POOL_TIMEOUT", "30"))),
            "pool_recycle": int(os.getenv("SELEXTRACT_DB_POOL_RECYCLE", os.getenv("DB_POOL_RECYCLE", "3600"))),  # 1 hour
            "pool_pre_ping": True,  # Validate connections before use
        }
        
        # For testing with SQLite
        if self.database_url.startswith("sqlite"):
            engine_kwargs.update({
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
                "pool_size": 1,
                "max_overflow": 0,
            })
        
        self.engine = create_async_engine(self.database_url, **engine_kwargs)
        
        # Add connection event listeners
        self._setup_engine_events()
        
        logger.info(f"Database engine created with pool_size={engine_kwargs['pool_size']}")
        return self.engine
    
    def _setup_engine_events(self):
        """Setup database engine event listeners"""
        if not self.engine:
            return
            
        @event.listens_for(self.engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance (if using SQLite)"""
            if "sqlite" in self.database_url:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()
        
        @event.listens_for(self.engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log connection checkout (debug only)"""
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Connection checked out from pool")
        
        @event.listens_for(self.engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log connection checkin (debug only)"""
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Connection checked in to pool")
    
    def create_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Create async session factory"""
        if self.async_session is not None:
            return self.async_session
            
        if self.engine is None:
            self.create_engine()
            
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )
        
        logger.info("Database session factory created")
        return self.async_session
    
    async def create_tables(self):
        """Create all database tables"""
        if not self.engine:
            self.create_engine()
            
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))
            
            logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.warning(f"Table creation skipped (tables may already exist): {e}")
    
    async def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        if not self.engine:
            self.create_engine()
            
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.warning("All database tables dropped")
    
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
    
    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            if not self.async_session:
                self.create_session_factory()
                
            async with self.async_session() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

# Global database configuration instance
db_config = DatabaseConfig()

# Create synchronous engine for compatibility
def _get_sync_database_url() -> str:
    """Get synchronous database URL for legacy compatibility"""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        # Construct from standardized components
        db_host = os.getenv("SELEXTRACT_DB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
        db_port = os.getenv("SELEXTRACT_DB_PORT", os.getenv("POSTGRES_PORT", "5432"))
        db_name = os.getenv("SELEXTRACT_DB_NAME", os.getenv("POSTGRES_DB", "selextract"))
        db_user = os.getenv("SELEXTRACT_DB_USER", os.getenv("POSTGRES_USER", "postgres"))
        db_password = os.getenv("SELEXTRACT_DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "password"))
        
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Convert async URL to sync for compatibility
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    return database_url

SYNC_DATABASE_URL = _get_sync_database_url()
engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get database session for sync operations"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def create_tables():
    """Create all database tables using sync engine"""
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.warning(f"Table creation skipped (tables may already exist): {e}")

# Dependency function for FastAPI
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session"""
    if not db_config.async_session:
        db_config.create_session_factory()
        
    async with db_config.async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions"""
    if not db_config.async_session:
        db_config.create_session_factory()
        
    async with db_config.async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database transaction error: {e}")
            raise
        finally:
            await session.close()

# Database initialization functions
async def init_database():
    """Initialize database with tables and default data"""
    logger.info("Initializing database...")
    
    # Create engine and tables
    db_config.create_engine()
    await db_config.create_tables()
    
    # Verify default subscription plans exist
    async with get_db_session() as session:
        from models import SubscriptionPlan
        from sqlalchemy import select
        
        result = await session.execute(select(SubscriptionPlan))
        plans = result.scalars().all()
        
        if not plans:
            logger.warning("No subscription plans found. Please run the database initialization script.")
        else:
            logger.info(f"Found {len(plans)} subscription plans in database")
    
    logger.info("Database initialization completed")

async def reset_database():
    """Reset database (development only)"""
    if os.getenv("ENVIRONMENT") == "production":
        raise RuntimeError("Cannot reset database in production environment")
    
    logger.warning("Resetting database...")
    await db_config.drop_tables()
    await db_config.create_tables()
    logger.info("Database reset completed")

# Database utilities
class DatabaseUtils:
    """Utility functions for database operations"""
    
    @staticmethod
    async def execute_raw_sql(sql: str, params: Optional[dict] = None) -> any:
        """Execute raw SQL query"""
        async with get_db_session() as session:
            result = await session.execute(sql, params or {})
            return result
    
    @staticmethod
    async def get_table_count(table_name: str) -> int:
        """Get row count for a table"""
        async with get_db_session() as session:
            result = await session.execute(f"SELECT COUNT(*) FROM {table_name}")
            return result.scalar()
    
    @staticmethod
    async def vacuum_database():
        """Vacuum database (PostgreSQL/SQLite optimization)"""
        if "postgresql" in db_config.database_url:
            await DatabaseUtils.execute_raw_sql("VACUUM ANALYZE")
        elif "sqlite" in db_config.database_url:
            await DatabaseUtils.execute_raw_sql("VACUUM")
    
    @staticmethod
    async def get_database_stats() -> dict:
        """Get basic database statistics"""
        stats = {}
        
        try:
            from models import User, Task, TaskLog, UserSubscription, APIKey, UsageAnalytics
            
            async with get_db_session() as session:
                # Count records in each table
                for model in [User, Task, TaskLog, UserSubscription, APIKey, UsageAnalytics]:
                    result = await session.execute(f"SELECT COUNT(*) FROM {model.__tablename__}")
                    stats[model.__tablename__] = result.scalar()
                
                # Additional useful stats
                result = await session.execute(
                    "SELECT status, COUNT(*) FROM tasks GROUP BY status"
                )
                task_statuses = {row[0]: row[1] for row in result.fetchall()}
                stats["task_statuses"] = task_statuses
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            stats["error"] = str(e)
        
        return stats

# Application lifespan management
@asynccontextmanager
async def lifespan_manager():
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting up application...")
    db_config.create_engine()
    db_config.create_session_factory()
    
    # Verify database connectivity
    if not await db_config.health_check():
        raise RuntimeError("Database connectivity check failed")
    
    logger.info("Application startup completed")
    
    try:
        yield
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        await db_config.close()
        logger.info("Application shutdown completed")

# Legacy compatibility
DATABASE_URL = SYNC_DATABASE_URL

# Export commonly used items
__all__ = [
    "db_config",
    "engine",
    "SessionLocal",
    "get_db",
    "create_tables",
    "get_database_session",
    "get_db_session",
    "init_database",
    "reset_database",
    "DatabaseUtils",
    "lifespan_manager",
    "DATABASE_URL",
    "SYNC_DATABASE_URL"
]