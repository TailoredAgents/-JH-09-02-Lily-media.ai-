#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Database Scan and Validation
"""
import os
import sys
import logging
from sqlalchemy import create_engine, inspect, text

# Add backend to path
sys.path.insert(0, '/Users/jeffreyhacker/Lily-Media.AI/socialmedia2/backend')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Production database URL
DATABASE_URL = "postgresql://socialmedia:BbsIYQtjBnhKwRL3F9kXbv1wrtsVxuTg@dpg-d2ln7eer433s739509lg-a.oregon-postgres.render.com/socialmedia_uq72?sslmode=require"

def main():
    """Main scan function"""
    try:
        logger.info("Connecting to production database...")
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_timeout=30)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info("Connected to PostgreSQL: " + version)
        
        inspector = inspect(engine)
        
        # Get all tables
        tables = inspector.get_table_names()
        logger.info("Found " + str(len(tables)) + " tables in database")
        
        # Check each table
        for table_name in tables:
            logger.info("\nAnalyzing table: " + table_name)
            
            # Get columns
            columns = inspector.get_columns(table_name)
            logger.info("  Columns: " + str(len(columns)))
            
            for col in columns:
                logger.info("    - " + col['name'] + ": " + str(col['type']) + " (nullable: " + str(col['nullable']) + ")")
            
            # Get primary keys
            primary_keys = inspector.get_pk_constraint(table_name)
            if primary_keys['constrained_columns']:
                logger.info("  Primary keys: " + str(primary_keys['constrained_columns']))
            
            # Get foreign keys
            foreign_keys = inspector.get_foreign_keys(table_name)
            if foreign_keys:
                logger.info("  Foreign keys: " + str(len(foreign_keys)))
                for fk in foreign_keys:
                    logger.info("    - " + str(fk['constrained_columns']) + " -> " + fk['referred_table'] + "." + str(fk['referred_columns']))
            
            # Get indexes
            indexes = inspector.get_indexes(table_name)
            if indexes:
                logger.info("  Indexes: " + str(len(indexes)))
                for idx in indexes:
                    logger.info("    - " + idx['name'] + ": " + str(idx['column_names']))
            
            # Check row count
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = result.fetchone()[0]
                logger.info("  Row count: " + str(row_count))
        
        # Check PostgreSQL extensions
        logger.info("\nChecking PostgreSQL extensions:")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT extname, extversion FROM pg_extension"))
            extensions = result.fetchall()
            for ext_name, ext_version in extensions:
                logger.info("  Extension: " + ext_name + " v" + ext_version)
        
        # Check if critical extensions are available
        critical_extensions = ['pgvector', 'uuid-ossp']
        logger.info("\nChecking for critical extensions:")
        for ext in critical_extensions:
            try:
                with engine.connect() as conn:
                    conn.execute(text(f"SELECT 1 FROM pg_extension WHERE extname = '{ext}'"))
                    logger.info("  " + ext + ": INSTALLED")
            except:
                logger.warning("  " + ext + ": NOT INSTALLED")
        
        logger.info("\nDatabase scan completed successfully!")
        
    except Exception as e:
        logger.error("Database scan failed: " + str(e))
        raise

if __name__ == "__main__":
    main()