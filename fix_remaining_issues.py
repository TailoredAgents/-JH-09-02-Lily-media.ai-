#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Remaining Database Issues

Fix the remaining issues from the previous script:
1. Create indexes without CONCURRENTLY 
2. Update Alembic version with shorter name
"""
import sys
import os
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import create_engine, text

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

def create_missing_indexes(engine):
    """Create indexes for new columns without CONCURRENTLY"""
    print("🔧 Creating missing indexes...")
    
    with engine.connect() as conn:
        try:
            # Index for notifications.type (without CONCURRENTLY)
            try:
                conn.execute(text("CREATE INDEX ix_notifications_type ON notifications (type)"))
                conn.commit()
                print("   ✅ Created index on notifications.type")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print("   ⚠️  Index creation failed for notifications.type: {}".format(e))
                else:
                    print("   ✅ Index already exists on notifications.type")
            
            # Index for memories.importance_score  
            try:
                conn.execute(text("CREATE INDEX ix_memories_importance_score ON memories (importance_score)"))
                conn.commit()
                print("   ✅ Created index on memories.importance_score")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print("   ⚠️  Index creation failed for memories.importance_score: {}".format(e))
                else:
                    print("   ✅ Index already exists on memories.importance_score")
            
            # Index for content.content_type
            try:
                conn.execute(text("CREATE INDEX ix_content_content_type ON content (content_type)"))
                conn.commit()
                print("   ✅ Created index on content.content_type")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print("   ⚠️  Index creation failed for content.content_type: {}".format(e))
                else:
                    print("   ✅ Index already exists on content.content_type")
            
            return True
            
        except Exception as e:
            print("❌ Error creating indexes: {}".format(e))
            return False

def update_alembic_version(engine):
    """Update Alembic version with shorter name"""
    print("🔧 Updating Alembic version...")
    
    with engine.connect() as conn:
        try:
            # Use shorter version name (within 32 char limit)
            conn.execute(text("""
                UPDATE alembic_version 
                SET version_num = '002_structure_fixes'
            """))
            conn.commit()
            print("✅ Alembic version updated to: 002_structure_fixes")
            return True
        except Exception as e:
            print("❌ Error updating Alembic version: {}".format(e))
            return False

def verify_fixes(engine):
    """Verify that all fixes were applied correctly"""
    print("🔍 Verifying fixes...")
    
    with engine.connect() as conn:
        try:
            # Check public_id constraints
            result = conn.execute(text("""
                SELECT column_name, is_nullable 
                FROM information_schema.columns 
                WHERE table_name IN ('users', 'content_logs') 
                AND column_name = 'public_id'
            """))
            
            for row in result:
                nullable_status = "NULL" if row[1] == 'YES' else "NOT NULL"
                print("   • public_id in table with '{}' column: {}".format(row[0], nullable_status))
            
            # Check new columns exist
            new_columns = [
                ('notifications', 'type'),
                ('memories', 'importance_score'),
                ('content', 'content_data'),
                ('content', 'content_type')
            ]
            
            for table, column in new_columns:
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{}' AND column_name = '{}'
                """.format(table, column)))
                
                if result.fetchone():
                    print("   ✅ Column {}.{} exists".format(table, column))
                else:
                    print("   ❌ Column {}.{} missing".format(table, column))
            
            # Check current Alembic version
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            print("   • Current Alembic version: {}".format(version))
            
            return True
            
        except Exception as e:
            print("❌ Error during verification: {}".format(e))
            return False

def main():
    """Main fix function"""
    print("🚀 Fixing Remaining Database Issues...")
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
        
        # Apply remaining fixes
        success = True
        
        success &= create_missing_indexes(engine)
        print("")
        
        success &= update_alembic_version(engine)
        print("")
        
        success &= verify_fixes(engine)
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 Remaining issues fixed successfully!")
            print("\nCompleted fixes:")
            print("  • Indexes created for new columns")  
            print("  • Alembic version updated")
            print("  • All fixes verified")
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