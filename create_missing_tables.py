#!/usr/bin/env python3
"""
Create missing database tables for production deployment
Focus on key tables needed for autonomous posting system
"""

import os
import sys
import logging
from sqlalchemy import create_engine, inspect, MetaData
from sqlalchemy.orm import sessionmaker

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.db.database import Base
from backend.core.config import get_settings
from backend.db.models import *  # Import all models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_missing_tables():
    """Identify which tables are missing from the database"""
    settings = get_settings()
    database_url = settings.get_database_url()
    
    logger.info(f"Connecting to database: {database_url}")
    engine = create_engine(database_url)
    
    # Get existing tables from database
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    
    # Get expected tables from models
    expected_tables = set(Base.metadata.tables.keys())
    
    missing_tables = expected_tables - existing_tables
    
    logger.info(f"Existing tables ({len(existing_tables)}): {sorted(existing_tables)}")
    logger.info(f"Expected tables ({len(expected_tables)}): {sorted(expected_tables)}")
    logger.info(f"Missing tables ({len(missing_tables)}): {sorted(missing_tables)}")
    
    return engine, missing_tables, existing_tables

def create_missing_tables():
    """Create missing tables using SQLAlchemy"""
    try:
        engine, missing_tables, existing_tables = get_missing_tables()
        
        if not missing_tables:
            logger.info("✅ All required tables already exist!")
            return True
            
        logger.info(f"🔧 Creating {len(missing_tables)} missing tables...")
        
        # Create only the missing tables
        missing_metadata = MetaData()
        for table_name in missing_tables:
            if table_name in Base.metadata.tables:
                table = Base.metadata.tables[table_name]
                table.tometadata(missing_metadata)
        
        # Create the missing tables
        missing_metadata.create_all(engine)
        
        # Verify tables were created
        inspector = inspect(engine)
        new_existing_tables = set(inspector.get_table_names())
        newly_created = new_existing_tables - existing_tables
        
        logger.info(f"✅ Successfully created {len(newly_created)} tables: {sorted(newly_created)}")
        
        # Check if all expected tables now exist
        remaining_missing = missing_tables - newly_created
        if remaining_missing:
            logger.warning(f"⚠️  Some tables still missing: {sorted(remaining_missing)}")
            return False
        else:
            logger.info("🎉 All required tables now exist!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to create missing tables"""
    logger.info("🚀 Starting database table creation for autonomous posting system...")
    
    success = create_missing_tables()
    
    if success:
        logger.info("✅ Database table creation completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Database table creation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()