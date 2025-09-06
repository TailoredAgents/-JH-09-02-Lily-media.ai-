#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Schema Deep Scan Tool - Python 2.7 Compatible

Connects to the PostgreSQL database and performs comprehensive schema analysis.
"""
import sys
import os
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ CRITICAL: DATABASE_URL environment variable must be set")
    sys.exit(1)

def get_database_connection():
    """Create database connection."""
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        return engine
    except Exception as e:
        print("Failed to connect to database: {}".format(e))
        return None

def analyze_schema_structure(engine):
    """Analyze the current database schema structure."""
    inspector = inspect(engine)
    
    print("=" * 80)
    print("DATABASE SCHEMA ANALYSIS")
    print("=" * 80)
    
    # Get all tables
    tables = inspector.get_table_names()
    print("\n📊 Found {} tables:".format(len(tables)))
    for table in sorted(tables):
        print("  • {}".format(table))
    
    return tables

def analyze_table_details(engine, table_name):
    """Analyze detailed table structure."""
    inspector = inspect(engine)
    
    print("\n🔍 ANALYZING TABLE: {}".format(table_name))
    print("-" * 50)
    
    try:
        # Get columns
        columns = inspector.get_columns(table_name)
        print("Columns ({}):".format(len(columns)))
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = ", DEFAULT: {}".format(col.get('default', 'None')) if col.get('default') else ""
            print("  • {}: {} {}{}".format(col['name'], col['type'], nullable, default))
        
        # Get indexes
        indexes = inspector.get_indexes(table_name)
        if indexes:
            print("\nIndexes ({}):".format(len(indexes)))
            for idx in indexes:
                unique = "UNIQUE " if idx['unique'] else ""
                print("  • {}{}: {}".format(unique, idx['name'], idx['column_names']))
        
        # Get foreign keys
        foreign_keys = inspector.get_foreign_keys(table_name)
        if foreign_keys:
            print("\nForeign Keys ({}):".format(len(foreign_keys)))
            for fk in foreign_keys:
                print("  • {}: {} → {}.{}".format(
                    fk['name'], fk['constrained_columns'], fk['referred_table'], fk['referred_columns']
                ))
        
        # Get constraints
        pk = inspector.get_pk_constraint(table_name)
        if pk and pk['constrained_columns']:
            print("\nPrimary Key: {}".format(pk['constrained_columns']))
        
        unique_constraints = inspector.get_unique_constraints(table_name)
        if unique_constraints:
            print("\nUnique Constraints ({}):".format(len(unique_constraints)))
            for uc in unique_constraints:
                print("  • {}: {}".format(uc['name'], uc['column_names']))
                
    except Exception as e:
        print("Error analyzing table {}: {}".format(table_name, e))

def check_migration_state(engine):
    """Check Alembic migration state."""
    print("\n📋 MIGRATION STATE ANALYSIS")
    print("-" * 50)
    
    try:
        with engine.connect() as conn:
            # Check if alembic_version table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'alembic_version'
                );
            """))
            
            has_alembic = result.scalar()
            print("Alembic version table exists: {}".format(has_alembic))
            
            if has_alembic:
                # Get current migration version
                result = conn.execute(text("SELECT version_num FROM alembic_version;"))
                current_version = result.scalar()
                print("Current migration version: {}".format(current_version))
            else:
                print("⚠️  No Alembic version table found - database may not be initialized")
                
    except Exception as e:
        print("Error checking migration state: {}".format(e))

def main():
    """Main analysis function."""
    print("🚀 Starting Deep Database Schema Scan...")
    print("📅 Scan started at: {}".format(datetime.now()))
    
    # Connect to database
    engine = get_database_connection()
    if not engine:
        print("❌ Failed to connect to database. Exiting.")
        return 1
    
    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            pg_version = result.scalar()
            print("📊 Connected to: {}".format(pg_version))
        
        # Perform analysis
        tables = analyze_schema_structure(engine)
        
        # Analyze key tables in detail
        key_tables = ['users', 'content_logs', 'goals', 'organizations', 'social_connections', 'alembic_version']
        
        for table in key_tables:
            if table in tables:
                analyze_table_details(engine, table)
        
        # Check migration state
        check_migration_state(engine)
        
        print("\n✅ Database scan completed successfully!")
        print("📊 Total tables analyzed: {}".format(len(tables)))
        
        return 0
        
    except Exception as e:
        print("❌ Error during database analysis: {}".format(e))
        return 1
    finally:
        if engine:
            engine.dispose()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)