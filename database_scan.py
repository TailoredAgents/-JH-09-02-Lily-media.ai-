#!/usr/bin/env python3
"""
Database Schema Deep Scan Tool

Connects to the PostgreSQL database and performs comprehensive schema analysis.
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import sqlalchemy as sa
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = "postgresql://socialmedia:BbsIYQtjBnhKwRL3F9kXbv1wrtsVxuTg@dpg-d2ln7eer433s739509lg-a.oregon-postgres.render.com/socialmedia_uq72"

def get_database_connection():
    """Create database connection."""
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        return engine
    except Exception as e:
        logger.error("Failed to connect to database: {}".format(e))
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
        print("  • {table}")
    
    return tables

def analyze_table_details(engine, table_name: str):
    """Analyze detailed table structure."""
    inspector = inspect(engine)
    
    print("\n🔍 ANALYZING TABLE: {table_name}")
    print("-" * 50)
    
    try:
        # Get columns
        columns = inspector.get_columns(table_name)
        print("Columns ({len(columns)}):")
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = ", DEFAULT: {col.get('default', 'None')}" if col.get('default') else ""
            print("  • {col['name']}: {col['type']} {nullable}{default}")
        
        # Get indexes
        indexes = inspector.get_indexes(table_name)
        if indexes:
            print("\nIndexes ({len(indexes)}):")
            for idx in indexes:
                unique = "UNIQUE " if idx['unique'] else ""
                print("  • {unique}{idx['name']}: {idx['column_names']}")
        
        # Get foreign keys
        foreign_keys = inspector.get_foreign_keys(table_name)
        if foreign_keys:
            print("\nForeign Keys ({len(foreign_keys)}):")
            for fk in foreign_keys:
                print("  • {fk['name']}: {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}")
        
        # Get constraints
        pk = inspector.get_pk_constraint(table_name)
        if pk and pk['constrained_columns']:
            print("\nPrimary Key: {pk['constrained_columns']}")
        
        unique_constraints = inspector.get_unique_constraints(table_name)
        if unique_constraints:
            print("\nUnique Constraints ({len(unique_constraints)}):")
            for uc in unique_constraints:
                print("  • {uc['name']}: {uc['column_names']}")
                
    except Exception as e:
        print("Error analyzing table {table_name}: {e}")

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
            print("Alembic version table exists: {has_alembic}")
            
            if has_alembic:
                # Get current migration version
                result = conn.execute(text("SELECT version_num FROM alembic_version;"))
                current_version = result.scalar()
                print("Current migration version: {current_version}")
                
                # Check for migration history if available
                try:
                    result = conn.execute(text("""
                        SELECT version_num, applied_at 
                        FROM alembic_version_history 
                        ORDER BY applied_at DESC 
                        LIMIT 10;
                    """))
                    history = result.fetchall()
                    if history:
                        print("\nRecent migration history:")
                        for row in history:
                            print("  • {row[0]} - {row[1]}")
                except:
                    pass  # Table might not exist
            else:
                print("⚠️  No Alembic version table found - database may not be initialized")
                
    except Exception as e:
        print("Error checking migration state: {e}")

def detect_schema_issues(engine):
    """Detect potential schema issues."""
    print("\n🔧 SCHEMA ISSUE DETECTION")
    print("-" * 50)
    
    issues = []
    inspector = inspect(engine)
    
    try:
        with engine.connect() as conn:
            # Check for missing indexes on foreign keys
            tables = inspector.get_table_names()
            
            for table_name in tables:
                foreign_keys = inspector.get_foreign_keys(table_name)
                indexes = inspector.get_indexes(table_name)
                index_columns = set()
                
                for idx in indexes:
                    for col in idx['column_names']:
                        index_columns.add(col)
                
                for fk in foreign_keys:
                    for col in fk['constrained_columns']:
                        if col not in index_columns:
                            issues.append("Missing index on FK column: {table_name}.{col}")
            
            # Check for tables without primary keys
            for table_name in tables:
                pk = inspector.get_pk_constraint(table_name)
                if not pk or not pk['constrained_columns']:
                    issues.append("Table without primary key: {table_name}")
            
            # Check for orphaned records (basic check)
            # This is a simplified check - in production you'd want more sophisticated analysis
            
            if issues:
                print("⚠️  Found potential issues:")
                for issue in issues:
                    print("  • {issue}")
            else:
                print("✅ No obvious schema issues detected")
                
    except Exception as e:
        print("Error during issue detection: {e}")
    
    return issues

def analyze_data_consistency(engine):
    """Analyze data consistency and integrity."""
    print("\n📈 DATA CONSISTENCY ANALYSIS")
    print("-" * 50)
    
    try:
        with engine.connect() as conn:
            # Check record counts
            tables = ['users', 'content_logs', 'goals', 'notifications', 'organizations']
            
            print("Record counts:")
            for table in tables:
                try:
                    result = conn.execute(text("SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print("  • {table}: {count:,} records")
                except Exception as e:
                    print("  • {table}: Error - {e}")
            
            # Check for NULL values in NOT NULL columns
            print("\nNULL value analysis:")
            
            # Check users table specifically
            try:
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(email) as users_with_email,
                        COUNT(username) as users_with_username,
                        COUNT(hashed_password) as users_with_password
                    FROM users
                """))
                
                row = result.fetchone()
                print("  • Users: {row[0]} total, {row[1]} with email, {row[2]} with username, {row[3]} with password")
                
                if row[0] != row[1] or row[0] != row[2]:
                    print("    ⚠️  Some users missing required fields!")
                    
            except Exception as e:
                print("  Error checking users table: {e}")
                
    except Exception as e:
        print("Error during consistency analysis: {e}")

def main():
    """Main analysis function."""
    print("🚀 Starting Deep Database Schema Scan...")
    print("📅 Scan started at: {datetime.now()}")
    
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
            print("📊 Connected to: {pg_version}")
        
        # Perform analysis
        tables = analyze_schema_structure(engine)
        
        # Analyze key tables in detail
        key_tables = ['users', 'content_logs', 'goals', 'organizations', 'social_connections']
        
        for table in key_tables:
            if table in tables:
                analyze_table_details(engine, table)
        
        # Check migration state
        check_migration_state(engine)
        
        # Detect issues
        issues = detect_schema_issues(engine)
        
        # Analyze data consistency
        analyze_data_consistency(engine)
        
        print("\n✅ Database scan completed successfully!")
        print("📊 Total tables analyzed: {len(tables)}")
        print("⚠️  Issues found: {len(issues)}")
        
        return 0 if len(issues) == 0 else 1
        
    except Exception as e:
        print("❌ Error during database analysis: {e}")
        return 1
    finally:
        if engine:
            engine.dispose()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)