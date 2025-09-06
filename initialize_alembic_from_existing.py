#!/usr/bin/env python3
"""
Initialize Alembic from Existing Database

This script creates a baseline Alembic migration from the current database state.
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from alembic import command
from alembic.config import Config

DATABASE_URL = "os.getenv("DATABASE_URL")

def initialize_alembic_baseline():
    """Initialize Alembic with current database as baseline."""
    
    print("🚀 Initializing Alembic from existing database...")
    
    try:
        # Connect to database
        engine = create_engine(DATABASE_URL)
        
        # Create alembic_version table and set baseline
        with engine.connect() as conn:
            # Create alembic_version table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                );
            """))
            
            # Set baseline version (this marks current schema as migration 0)
            baseline_version = "baseline_existing_schema"
            
            # Remove any existing version first
            conn.execute(text("DELETE FROM alembic_version;"))
            
            # Insert baseline version
            conn.execute(text(
                "INSERT INTO alembic_version (version_num) VALUES (:version);"
            ), {"version": baseline_version})
            
            conn.commit()
            
            print("✅ Created alembic_version table")
            print("✅ Set baseline version: {}".format(baseline_version))
        
        return True
        
    except Exception as e:
        print("❌ Error initializing Alembic: {}".format(e))
        return False

def create_baseline_migration():
    """Create a baseline migration file that represents current schema."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    migration_content = '''"""Baseline migration from existing database schema

Revision ID: baseline_existing_schema
Revises: 
Create Date: {timestamp}

This migration represents the current state of the production database
as of {date}. It serves as a baseline for future migrations.

Current tables:
- admin_users
- company_knowledge  
- content
- content_logs
- inbox_settings
- interaction_responses
- knowledge_base_entries
- memories
- notifications
- registration_keys (to be deprecated)
- response_templates
- social_interactions
- social_platform_connections
- social_responses
- user_settings
- users

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'baseline_existing_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Baseline migration - no changes needed.
    
    This migration represents the existing database state.
    All tables already exist in production.
    """
    pass


def downgrade():
    """Cannot downgrade from baseline."""
    raise NotImplementedError("Cannot downgrade from baseline migration")
'''.format(timestamp=timestamp, date=datetime.now().strftime("%Y-%m-%d"))

    # Write baseline migration file
    migration_file = "alembic/versions/000_baseline_existing_schema.py"
    
    try:
        with open(migration_file, 'w') as f:
            f.write(migration_content)
        
        print("✅ Created baseline migration: {}".format(migration_file))
        return True
        
    except Exception as e:
        print("❌ Error creating baseline migration: {}".format(e))
        return False

def main():
    """Main initialization function."""
    print("📋 Database Schema Initialization")
    print("=" * 50)
    
    # Step 1: Initialize Alembic version table
    if not initialize_alembic_baseline():
        print("❌ Failed to initialize Alembic. Exiting.")
        return 1
    
    # Step 2: Create baseline migration file
    if not create_baseline_migration():
        print("❌ Failed to create baseline migration. Exiting.")
        return 1
    
    print("\n🎉 Alembic initialization completed successfully!")
    print("\nNext steps:")
    print("1. Run: alembic current (should show: baseline_existing_schema)")
    print("2. Create new migrations for missing tables")
    print("3. Apply migrations: alembic upgrade head")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)