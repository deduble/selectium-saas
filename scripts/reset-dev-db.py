#!/usr/bin/env python3
"""
Reset development database with new schema
"""
import os
import sys
import asyncio
import logging

# Add the api directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from database import reset_database, init_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Reset and reinitialize the development database"""
    try:
        # Check if we're in development
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production":
            logger.error("Cannot reset database in production!")
            return False
        
        logger.info("Resetting development database...")
        await reset_database()
        
        logger.info("Reinitializing database with new schema...")
        await init_database()
        
        logger.info("Database reset completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)