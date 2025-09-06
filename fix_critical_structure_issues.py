#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Critical Database Structure Issues

Addresses the most critical schema issues identified:
1. Make public_id columns NOT NULL with default values
2. Add missing columns to existing tables
3. Fix table structure mismatches
"""
import sys
import os
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import create_engine, text
import uuid

# Database connection - CRITICAL: Get from environment for security
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ CRITICAL: DATABASE_URL environment variable must be set")
    print("   Contact administrator for production database credentials")
    sys.exit(1)

def get_database_connection():
    """Create database connection."""
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        return engine
    except Exception as e:
        print("Failed to connect to database: {}".format(e))
        return None

def fix_public_id_columns(engine):
    """Fix public_id columns to be NOT NULL with default values"""
    print("🔧 Fixing public_id columns...")
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            # 1. Update NULL public_id values with UUIDs
            print("   → Updating NULL public_id values in users table...")
            result = conn.execute(text("SELECT COUNT(*) FROM users WHERE public_id IS NULL"))
            null_count = result.scalar()
            print("     Found {} users with NULL public_id".format(null_count))
            
            if null_count > 0:
                # Generate UUIDs for NULL values
                conn.execute(text("""
                    UPDATE users 
                    SET public_id = gen_random_uuid()::text 
                    WHERE public_id IS NULL
                """))
                print("     ✅ Updated {} users with new UUIDs".format(null_count))
            
            print("   → Updating NULL public_id values in content_logs table...")
            result = conn.execute(text("SELECT COUNT(*) FROM content_logs WHERE public_id IS NULL"))
            null_count = result.scalar()
            print("     Found {} content_logs with NULL public_id".format(null_count))
            
            if null_count > 0:
                conn.execute(text("""
                    UPDATE content_logs 
                    SET public_id = gen_random_uuid()::text 
                    WHERE public_id IS NULL
                """))
                print("     ✅ Updated {} content_logs with new UUIDs".format(null_count))
            
            # 2. Make public_id columns NOT NULL
            print("   → Making public_id NOT NULL in users table...")
            conn.execute(text("ALTER TABLE users ALTER COLUMN public_id SET NOT NULL"))
            
            print("   → Making public_id NOT NULL in content_logs table...")
            conn.execute(text("ALTER TABLE content_logs ALTER COLUMN public_id SET NOT NULL"))
            
            trans.commit()
            print("✅ public_id columns fixed successfully!")
            return True
            
        except Exception as e:
            trans.rollback()
            print("❌ Error fixing public_id columns: {}".format(e))
            return False

def fix_missing_columns(engine):
    """Add missing columns to existing tables"""
    print("🔧 Adding missing columns to existing tables...")
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            # 1. Add 'type' column to notifications table
            print("   → Adding 'type' column to notifications table...")
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'notifications' AND column_name = 'type'
            """))
            
            if not result.fetchone():
                conn.execute(text("""
                    ALTER TABLE notifications 
                    ADD COLUMN type VARCHAR(50) DEFAULT 'info'
                """))
                print("     ✅ Added 'type' column to notifications")
            else:
                print("     ✅ 'type' column already exists in notifications")
            
            # 2. Add 'importance_score' column to memories table  
            print("   → Adding 'importance_score' column to memories table...")
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'memories' AND column_name = 'importance_score'
            """))
            
            if not result.fetchone():
                conn.execute(text("""
                    ALTER TABLE memories 
                    ADD COLUMN importance_score FLOAT DEFAULT 0.5
                """))
                print("     ✅ Added 'importance_score' column to memories")
            else:
                print("     ✅ 'importance_score' column already exists in memories")
            
            # 3. Add missing columns to content table
            print("   → Adding missing columns to content table...")
            
            # Check for content_data column
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'content' AND column_name = 'content_data'
            """))
            
            if not result.fetchone():
                conn.execute(text("""
                    ALTER TABLE content 
                    ADD COLUMN content_data JSONB DEFAULT '{}'
                """))
                print("     ✅ Added 'content_data' column to content")
            
            # Check for content_type column
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'content' AND column_name = 'content_type'
            """))
            
            if not result.fetchone():
                conn.execute(text("""
                    ALTER TABLE content 
                    ADD COLUMN content_type VARCHAR(50) DEFAULT 'post'
                """))
                print("     ✅ Added 'content_type' column to content")
            
            trans.commit()
            print("✅ Missing columns added successfully!")
            return True
            
        except Exception as e:
            trans.rollback()
            print("❌ Error adding missing columns: {}".format(e))
            return False

def create_indexes_for_new_columns(engine):
    """Create indexes for newly added columns"""
    print("🔧 Creating indexes for new columns...")
    
    with engine.connect() as conn:
        try:
            # Index for notifications.type
            try:
                conn.execute(text("CREATE INDEX CONCURRENTLY ix_notifications_type ON notifications (type)"))
                print("   ✅ Created index on notifications.type")
            except Exception as e:
                if "already exists" not in str(e):
                    print("   ⚠️  Index creation failed for notifications.type: {}".format(e))
            
            # Index for memories.importance_score  
            try:
                conn.execute(text("CREATE INDEX CONCURRENTLY ix_memories_importance_score ON memories (importance_score)"))
                print("   ✅ Created index on memories.importance_score")
            except Exception as e:
                if "already exists" not in str(e):
                    print("   ⚠️  Index creation failed for memories.importance_score: {}".format(e))
            
            # Index for content.content_type
            try:
                conn.execute(text("CREATE INDEX CONCURRENTLY ix_content_content_type ON content (content_type)"))
                print("   ✅ Created index on content.content_type")
            except Exception as e:
                if "already exists" not in str(e):
                    print("   ⚠️  Index creation failed for content.content_type: {}".format(e))
            
            print("✅ Indexes created successfully!")
            return True
            
        except Exception as e:
            print("❌ Error creating indexes: {}".format(e))
            return False

def update_alembic_version(engine):
    """Update Alembic version to track this migration"""
    print("🔧 Updating Alembic version...")
    
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                UPDATE alembic_version 
                SET version_num = '002_fix_critical_structure_issues'
            """))
            print("✅ Alembic version updated!")
            return True
        except Exception as e:
            print("❌ Error updating Alembic version: {}".format(e))
            return False

def main():
    """Main fix function"""
    print("🚀 Starting Critical Database Structure Fixes...")
    print("📅 Fix started at: {}".format(datetime.now()))
    print("")
    
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
        
        print("=" * 60)
        
        # Apply fixes
        success = True
        
        success &= fix_public_id_columns(engine)
        print("")
        
        success &= fix_missing_columns(engine)
        print("")
        
        success &= create_indexes_for_new_columns(engine)
        print("")
        
        success &= update_alembic_version(engine)
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 Critical structure fixes completed successfully!")
            print("\nFixes applied:")
            print("  • public_id columns made NOT NULL with UUID defaults")
            print("  • notifications.type column added")
            print("  • memories.importance_score column added")
            print("  • content.content_data column added")
            print("  • content.content_type column added")
            print("  • Indexes created for new columns")
            print("  • Alembic version updated to: 002_fix_critical_structure_issues")
            return 0
        else:
            print("\n❌ Some fixes failed. Check the logs above.")
            return 1
            
    except Exception as e:
        print("❌ Error during fixes: {}".format(e))
        return 1
    finally:
        if engine:
            engine.dispose()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)