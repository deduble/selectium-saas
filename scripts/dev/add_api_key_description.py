#!/usr/bin/env python3
"""
Add description column to api_keys table for development environment.
This is a quick fix for the missing column that's causing the API key creation bug.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load development environment variables
dev_env_path = os.path.join(os.path.dirname(__file__), '..', '..', 'dev', '.env.dev')
if os.path.exists(dev_env_path):
    load_dotenv(dev_env_path)
    print(f"Loaded environment from {dev_env_path}")

# Add the api directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'api'))

def get_database_url():
    """Get database URL from environment"""
    db_host = os.getenv("SELEXTRACT_DB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
    db_port = os.getenv("SELEXTRACT_DB_PORT", os.getenv("POSTGRES_PORT", "5432"))
    db_name = os.getenv("SELEXTRACT_DB_NAME", os.getenv("POSTGRES_DB", "selextract"))
    db_user = os.getenv("SELEXTRACT_DB_USER", os.getenv("POSTGRES_USER", "postgres"))
    db_password = os.getenv("SELEXTRACT_DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "password"))
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_description_column():
    """Add description column to api_keys table if it doesn't exist."""
    try:
        # Get database URL
        database_url = get_database_url()
        logger.info(f"Connecting to database...")
        
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Start a transaction
            trans = conn.begin()
            
            try:
                # Check if column already exists
                logger.info("Checking if description column exists...")
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'api_keys' AND column_name = 'description'
                """))
                
                if result.fetchone():
                    logger.info("Description column already exists. No action needed.")
                    trans.rollback()
                    return
                
                # Add the description column
                logger.info("Adding description column to api_keys table...")
                conn.execute(text("""
                    ALTER TABLE api_keys 
                    ADD COLUMN description VARCHAR(500)
                """))
                
                # Commit the transaction
                trans.commit()
                logger.info("Successfully added description column to api_keys table.")
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        logger.error(f"Failed to add description column: {e}")
        raise

if __name__ == "__main__":
    add_description_column()