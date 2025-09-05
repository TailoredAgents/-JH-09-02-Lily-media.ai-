#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create Essential Missing Tables

Creates the most critical missing tables based on the comprehensive analysis:
1. Multi-tenant tables (teams, roles, permissions, user_organization_roles)
2. Content management tables (content_drafts, content_schedules)
3. User credential tables (user_credentials)
4. Social platform tables (social_posts)
5. Admin tables (admin_sessions, admin_audit_logs)
"""
import sys
import os
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import create_engine, text

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

def create_multi_tenant_tables(conn):
    """Create multi-tenant support tables"""
    print("1. Creating multi-tenant tables...")
    
    # Create teams table
    print("   → Creating teams table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS teams (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            organization_id INTEGER NOT NULL REFERENCES organizations(id),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create roles table
    print("   → Creating roles table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS roles (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            permissions TEXT[],
            is_system_role BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create permissions table
    print("   → Creating permissions table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS permissions (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            resource VARCHAR(100) NOT NULL,
            action VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create user_organization_roles table
    print("   → Creating user_organization_roles table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_organization_roles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            organization_id INTEGER NOT NULL REFERENCES organizations(id),
            role_id INTEGER NOT NULL REFERENCES roles(id),
            assigned_by_id INTEGER REFERENCES users(id),
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            UNIQUE(user_id, organization_id, role_id)
        )
    """))
    
    # Create indexes
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_teams_organization_id ON teams (organization_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_teams_public_id ON teams (public_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_roles_public_id ON roles (public_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_permissions_public_id ON permissions (public_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_org_roles_user_id ON user_organization_roles (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_org_roles_org_id ON user_organization_roles (organization_id)"))

def create_content_management_tables(conn):
    """Create content management tables"""
    print("2. Creating content management tables...")
    
    # Create content_drafts table
    print("   → Creating content_drafts table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS content_drafts (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            organization_id INTEGER REFERENCES organizations(id),
            title VARCHAR(255),
            content TEXT NOT NULL,
            content_type VARCHAR(50) DEFAULT 'post',
            platform VARCHAR(50),
            metadata JSONB DEFAULT '{}',
            status VARCHAR(50) DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create content_schedules table
    print("   → Creating content_schedules table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS content_schedules (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            organization_id INTEGER REFERENCES organizations(id),
            content_draft_id INTEGER REFERENCES content_drafts(id),
            platform VARCHAR(50) NOT NULL,
            scheduled_for TIMESTAMP NOT NULL,
            timezone VARCHAR(100) DEFAULT 'UTC',
            status VARCHAR(50) DEFAULT 'scheduled',
            published_at TIMESTAMP,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create indexes
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_drafts_user_id ON content_drafts (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_drafts_org_id ON content_drafts (organization_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_drafts_status ON content_drafts (status)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_schedules_user_id ON content_schedules (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_schedules_scheduled_for ON content_schedules (scheduled_for)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_schedules_status ON content_schedules (status)"))

def create_user_credentials_table(conn):
    """Create user credentials table for social platform credentials"""
    print("3. Creating user_credentials table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_credentials (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            organization_id INTEGER REFERENCES organizations(id),
            platform VARCHAR(50) NOT NULL,
            credential_type VARCHAR(50) DEFAULT 'oauth',
            access_token TEXT,
            refresh_token TEXT,
            token_expires_at TIMESTAMP,
            scopes TEXT[],
            platform_user_id VARCHAR(255),
            platform_username VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            encrypted_data JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, organization_id, platform, credential_type)
        )
    """))
    
    # Create indexes
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_credentials_user_id ON user_credentials (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_credentials_platform ON user_credentials (platform)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_credentials_is_active ON user_credentials (is_active)"))

def create_social_posts_table(conn):
    """Create social posts table"""
    print("4. Creating social_posts table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS social_posts (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            organization_id INTEGER REFERENCES organizations(id),
            connection_id INTEGER REFERENCES social_connections(id),
            platform VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            media_urls TEXT[],
            hashtags TEXT[],
            mentions TEXT[],
            scheduled_for TIMESTAMP,
            published_at TIMESTAMP,
            platform_post_id VARCHAR(255),
            status VARCHAR(50) DEFAULT 'draft',
            engagement_metrics JSONB DEFAULT '{}',
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create indexes
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_social_posts_user_id ON social_posts (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_social_posts_platform ON social_posts (platform)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_social_posts_status ON social_posts (status)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_social_posts_published_at ON social_posts (published_at)"))

def create_admin_tables(conn):
    """Create admin support tables"""
    print("5. Creating admin tables...")
    
    # Create admin_sessions table
    print("   → Creating admin_sessions table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS admin_sessions (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            admin_user_id INTEGER NOT NULL REFERENCES admin_users(id),
            session_token VARCHAR(255) NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            ip_address VARCHAR(45),
            user_agent TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create admin_audit_logs table
    print("   → Creating admin_audit_logs table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            admin_user_id INTEGER REFERENCES admin_users(id),
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(50),
            resource_id VARCHAR(255),
            details JSONB DEFAULT '{}',
            ip_address VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create indexes
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_sessions_admin_user_id ON admin_sessions (admin_user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_sessions_expires_at ON admin_sessions (expires_at)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_admin_user_id ON admin_audit_logs (admin_user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_action ON admin_audit_logs (action)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_created_at ON admin_audit_logs (created_at)"))

def create_workflow_execution_table(conn):
    """Create workflow execution table"""
    print("6. Creating workflow_executions table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS workflow_executions (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            organization_id INTEGER REFERENCES organizations(id),
            workflow_name VARCHAR(255) NOT NULL,
            workflow_type VARCHAR(100) DEFAULT 'content_generation',
            input_data JSONB DEFAULT '{}',
            output_data JSONB DEFAULT '{}',
            status VARCHAR(50) DEFAULT 'pending',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            execution_time_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create indexes
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workflow_executions_user_id ON workflow_executions (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workflow_executions_status ON workflow_executions (status)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workflow_executions_started_at ON workflow_executions (started_at)"))

def main():
    """Main table creation function"""
    print("🚀 Creating Essential Missing Tables...")
    print("📅 Creation started at: {}".format(datetime.now()))
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
        
        # Create tables in transaction
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                create_multi_tenant_tables(conn)
                create_content_management_tables(conn) 
                create_user_credentials_table(conn)
                create_social_posts_table(conn)
                create_admin_tables(conn)
                create_workflow_execution_table(conn)
                
                # Update Alembic version
                print("7. Updating Alembic version...")
                conn.execute(text("""
                    UPDATE alembic_version 
                    SET version_num = '003_essential_tables'
                """))
                
                trans.commit()
                
                print("\n" + "=" * 60)
                print("🎉 Essential tables created successfully!")
                print("\nTables created:")
                print("  • teams - Team management")
                print("  • roles - Role-based access control")
                print("  • permissions - Permission management")
                print("  • user_organization_roles - User role assignments")
                print("  • content_drafts - Content draft management")
                print("  • content_schedules - Content scheduling")
                print("  • user_credentials - Social platform credentials")
                print("  • social_posts - Social media posts")
                print("  • admin_sessions - Admin session management")
                print("  • admin_audit_logs - Admin audit trail")
                print("  • workflow_executions - Workflow tracking")
                print("\n  • Alembic version updated to: 003_essential_tables")
                return 0
                
            except Exception as e:
                trans.rollback()
                print("❌ Error creating tables: {}".format(e))
                return 1
            
    except Exception as e:
        print("❌ Error during table creation: {}".format(e))
        return 1
    finally:
        if engine:
            engine.dispose()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)