#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Database Migration Script

Applies the core missing tables migration directly to the database.
"""
import sys
import os
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects import postgresql
import uuid

# Database connection
DATABASE_URL = "postgresql://socialmedia:BbsIYQtjBnhKwRL3F9kXbv1wrtsVxuTg@dpg-d2ln7eer433s739509lg-a.oregon-postgres.render.com/socialmedia_uq72"

def get_database_connection():
    """Create database connection."""
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        return engine
    except Exception as e:
        print("Failed to connect to database: {}".format(e))
        return None

def apply_migration(engine):
    """Apply the core missing tables migration"""
    
    print("🚀 Applying core missing tables migration...")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # 1. Add public_id columns to existing tables
            print("1. Adding public_id columns to existing tables...")
            
            # Check if public_id already exists in users table
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'public_id'
            """))
            
            if not result.fetchone():
                print("   → Adding public_id to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN public_id VARCHAR(36)"))
                conn.execute(text("CREATE INDEX ix_users_public_id ON users (public_id)"))
                conn.execute(text("ALTER TABLE users ADD CONSTRAINT uq_users_public_id UNIQUE (public_id)"))
            else:
                print("   → public_id already exists in users table")
            
            # Check if public_id already exists in content_logs table
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'content_logs' AND column_name = 'public_id'
            """))
            
            if not result.fetchone():
                print("   → Adding public_id to content_logs table...")
                conn.execute(text("ALTER TABLE content_logs ADD COLUMN public_id VARCHAR(36)"))
                conn.execute(text("CREATE INDEX ix_content_logs_public_id ON content_logs (public_id)"))
                conn.execute(text("ALTER TABLE content_logs ADD CONSTRAINT uq_content_logs_public_id UNIQUE (public_id)"))
            else:
                print("   → public_id already exists in content_logs table")
            
            # 2. Create organizations table
            print("2. Creating organizations table...")
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'organizations'
            """))
            
            if not result.fetchone():
                print("   → Creating organizations table...")
                conn.execute(text("""
                    CREATE TABLE organizations (
                        id SERIAL PRIMARY KEY,
                        public_id VARCHAR(36) NOT NULL UNIQUE,
                        name VARCHAR(255) NOT NULL,
                        slug VARCHAR(100) NOT NULL UNIQUE,
                        description TEXT,
                        website VARCHAR(255),
                        industry VARCHAR(100),
                        size VARCHAR(50),
                        timezone VARCHAR(100) DEFAULT 'UTC',
                        billing_email VARCHAR(255),
                        subscription_plan VARCHAR(50) DEFAULT 'free',
                        subscription_status VARCHAR(50) DEFAULT 'active',
                        subscription_end_date TIMESTAMP,
                        max_users INTEGER DEFAULT 5,
                        max_social_accounts INTEGER DEFAULT 3,
                        created_by_id INTEGER REFERENCES users(id),
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create indexes
                conn.execute(text("CREATE INDEX ix_organizations_created_at ON organizations (created_at)"))
                conn.execute(text("CREATE INDEX ix_organizations_name ON organizations (name)"))
                conn.execute(text("CREATE INDEX ix_organizations_public_id ON organizations (public_id)"))
                conn.execute(text("CREATE INDEX ix_organizations_slug ON organizations (slug)"))
                conn.execute(text("CREATE INDEX ix_organizations_subscription_status ON organizations (subscription_status)"))
            else:
                print("   → organizations table already exists")
            
            # 3. Create goals table
            print("3. Creating goals table...")
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'goals'
            """))
            
            if not result.fetchone():
                print("   → Creating goals table...")
                conn.execute(text("""
                    CREATE TABLE goals (
                        id SERIAL PRIMARY KEY,
                        public_id VARCHAR(36) NOT NULL UNIQUE,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        organization_id INTEGER REFERENCES organizations(id),
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        category VARCHAR(100),
                        target_value FLOAT,
                        current_value FLOAT DEFAULT 0.0,
                        unit VARCHAR(50),
                        target_date TIMESTAMP,
                        status VARCHAR(50) DEFAULT 'active',
                        priority VARCHAR(20) DEFAULT 'medium',
                        is_public BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """))
                
                # Create indexes
                conn.execute(text("CREATE INDEX ix_goals_category ON goals (category)"))
                conn.execute(text("CREATE INDEX ix_goals_created_at ON goals (created_at)"))
                conn.execute(text("CREATE INDEX ix_goals_organization_id ON goals (organization_id)"))
                conn.execute(text("CREATE INDEX ix_goals_public_id ON goals (public_id)"))
                conn.execute(text("CREATE INDEX ix_goals_status ON goals (status)"))
                conn.execute(text("CREATE INDEX ix_goals_user_id ON goals (user_id)"))
            else:
                print("   → goals table already exists")
            
            # 4. Create goal_progress table
            print("4. Creating goal_progress table...")
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'goal_progress'
            """))
            
            if not result.fetchone():
                print("   → Creating goal_progress table...")
                conn.execute(text("""
                    CREATE TABLE goal_progress (
                        id SERIAL PRIMARY KEY,
                        goal_id INTEGER NOT NULL REFERENCES goals(id),
                        value FLOAT NOT NULL,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                conn.execute(text("CREATE INDEX ix_goal_progress_created_at ON goal_progress (created_at)"))
                conn.execute(text("CREATE INDEX ix_goal_progress_goal_id ON goal_progress (goal_id)"))
            else:
                print("   → goal_progress table already exists")
            
            # 5. Create milestones table
            print("5. Creating milestones table...")
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'milestones'
            """))
            
            if not result.fetchone():
                print("   → Creating milestones table...")
                conn.execute(text("""
                    CREATE TABLE milestones (
                        id SERIAL PRIMARY KEY,
                        goal_id INTEGER NOT NULL REFERENCES goals(id),
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        target_date TIMESTAMP,
                        completed_at TIMESTAMP,
                        is_completed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                conn.execute(text("CREATE INDEX ix_milestones_created_at ON milestones (created_at)"))
                conn.execute(text("CREATE INDEX ix_milestones_goal_id ON milestones (goal_id)"))
                conn.execute(text("CREATE INDEX ix_milestones_is_completed ON milestones (is_completed)"))
            else:
                print("   → milestones table already exists")
            
            # 6. Create social_connections table
            print("6. Creating social_connections table...")
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'social_connections'
            """))
            
            if not result.fetchone():
                print("   → Creating social_connections table...")
                conn.execute(text("""
                    CREATE TABLE social_connections (
                        id SERIAL PRIMARY KEY,
                        public_id VARCHAR(36) NOT NULL UNIQUE,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        organization_id INTEGER REFERENCES organizations(id),
                        platform VARCHAR(50) NOT NULL,
                        platform_user_id VARCHAR(255) NOT NULL,
                        platform_username VARCHAR(255),
                        platform_name VARCHAR(255),
                        access_token TEXT NOT NULL,
                        refresh_token TEXT,
                        token_expires_at TIMESTAMP,
                        scopes TEXT[],
                        profile_image_url VARCHAR(512),
                        follower_count INTEGER,
                        following_count INTEGER,
                        last_sync_at TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT uq_social_connections_platform_user UNIQUE (platform, platform_user_id)
                    )
                """))
                
                # Create indexes
                conn.execute(text("CREATE INDEX ix_social_connections_created_at ON social_connections (created_at)"))
                conn.execute(text("CREATE INDEX ix_social_connections_is_active ON social_connections (is_active)"))
                conn.execute(text("CREATE INDEX ix_social_connections_organization_id ON social_connections (organization_id)"))
                conn.execute(text("CREATE INDEX ix_social_connections_platform ON social_connections (platform)"))
                conn.execute(text("CREATE INDEX ix_social_connections_public_id ON social_connections (public_id)"))
                conn.execute(text("CREATE INDEX ix_social_connections_user_id ON social_connections (user_id)"))
            else:
                print("   → social_connections table already exists")
            
            # 7. Create social_audit table
            print("7. Creating social_audit table...")
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'social_audit'
            """))
            
            if not result.fetchone():
                print("   → Creating social_audit table...")
                conn.execute(text("""
                    CREATE TABLE social_audit (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        organization_id INTEGER REFERENCES organizations(id),
                        connection_id INTEGER REFERENCES social_connections(id),
                        action VARCHAR(100) NOT NULL,
                        resource_type VARCHAR(50) NOT NULL,
                        resource_id VARCHAR(255),
                        platform VARCHAR(50),
                        details JSONB DEFAULT '{}',
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        status VARCHAR(20) DEFAULT 'success',
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create indexes
                conn.execute(text("CREATE INDEX ix_social_audit_action ON social_audit (action)"))
                conn.execute(text("CREATE INDEX ix_social_audit_created_at ON social_audit (created_at)"))
                conn.execute(text("CREATE INDEX ix_social_audit_organization_id ON social_audit (organization_id)"))
                conn.execute(text("CREATE INDEX ix_social_audit_platform ON social_audit (platform)"))
                conn.execute(text("CREATE INDEX ix_social_audit_resource_type ON social_audit (resource_type)"))
                conn.execute(text("CREATE INDEX ix_social_audit_user_id ON social_audit (user_id)"))
            else:
                print("   → social_audit table already exists")
            
            # 8. Update alembic version
            print("8. Updating Alembic version...")
            conn.execute(text("UPDATE alembic_version SET version_num = '001_add_core_missing_tables'"))
            
            # Commit transaction
            trans.commit()
            print("\n✅ Migration completed successfully!")
            
            return True
            
        except Exception as e:
            # Rollback on error
            trans.rollback()
            print("\n❌ Migration failed: {}".format(e))
            return False

def main():
    """Main migration function"""
    print("🚀 Starting Core Missing Tables Migration...")
    print("📅 Migration started at: {}".format(datetime.now()))
    
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
        
        # Apply migration
        success = apply_migration(engine)
        
        if success:
            print("\n🎉 Database migration completed successfully!")
            print("\nNew tables created:")
            print("  • organizations - Multi-tenant organization support")
            print("  • goals - Goal tracking system")
            print("  • goal_progress - Goal progress tracking")
            print("  • milestones - Milestone management")
            print("  • social_connections - OAuth social platform connections")
            print("  • social_audit - Social platform audit trail")
            print("\nColumns added:")
            print("  • users.public_id - External UUID reference")
            print("  • content_logs.public_id - External UUID reference")
            return 0
        else:
            print("\n❌ Migration failed. Database unchanged.")
            return 1
            
    except Exception as e:
        print("❌ Error during migration: {}".format(e))
        return 1
    finally:
        if engine:
            engine.dispose()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)