#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create All Remaining Missing Tables

Creates the final 15 missing tables identified in the comprehensive analysis:
1. api_key_revocations - API key security
2. content_categories - Content categorization  
3. content_items - Content item management
4. content_performance_snapshots - Content analytics
5. content_templates - Content templates
6. memory_content - Memory content relationships
7. metrics - System metrics
8. organization_invitations - Organization invites
9. platform_configs - Platform configurations
10. platform_metrics_snapshots - Platform analytics
11. refresh_token_blacklist - Token security
12. research_data - Research data storage
13. social_post_templates - Social post templates
14. system_settings - System configuration
15. user_management - User management tools
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

def create_api_security_tables(conn):
    """Create API security related tables"""
    print("1. Creating API security tables...")
    
    # api_key_revocations table
    print("   → Creating api_key_revocations table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS api_key_revocations (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            api_key_id VARCHAR(255) NOT NULL,
            revoked_by_id INTEGER REFERENCES admin_users(id),
            reason VARCHAR(255),
            revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            metadata JSONB DEFAULT '{}'
        )
    """))
    
    # refresh_token_blacklist table
    print("   → Creating refresh_token_blacklist table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS refresh_token_blacklist (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            token_jti VARCHAR(255) NOT NULL UNIQUE,
            blacklisted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            reason VARCHAR(255) DEFAULT 'logout',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create indexes
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_api_key_revocations_api_key_id ON api_key_revocations (api_key_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_api_key_revocations_revoked_at ON api_key_revocations (revoked_at)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_refresh_token_blacklist_token_jti ON refresh_token_blacklist (token_jti)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_refresh_token_blacklist_user_id ON refresh_token_blacklist (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_refresh_token_blacklist_expires_at ON refresh_token_blacklist (expires_at)"))

def create_content_advanced_tables(conn):
    """Create advanced content management tables"""
    print("2. Creating advanced content management tables...")
    
    # content_categories table
    print("   → Creating content_categories table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS content_categories (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            color VARCHAR(7) DEFAULT '#6B7280',
            icon VARCHAR(100),
            parent_id INTEGER REFERENCES content_categories(id),
            sort_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # content_items table
    print("   → Creating content_items table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS content_items (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            organization_id INTEGER REFERENCES organizations(id),
            category_id INTEGER REFERENCES content_categories(id),
            title VARCHAR(255) NOT NULL,
            slug VARCHAR(255),
            content TEXT NOT NULL,
            content_type VARCHAR(50) DEFAULT 'article',
            format VARCHAR(50) DEFAULT 'markdown',
            status VARCHAR(50) DEFAULT 'draft',
            featured_image_url VARCHAR(512),
            excerpt TEXT,
            tags TEXT[],
            metadata JSONB DEFAULT '{}',
            published_at TIMESTAMP,
            scheduled_for TIMESTAMP,
            view_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            share_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # content_templates table
    print("   → Creating content_templates table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS content_templates (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            organization_id INTEGER REFERENCES organizations(id),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            template_type VARCHAR(50) DEFAULT 'post',
            platform VARCHAR(50),
            template_content TEXT NOT NULL,
            variables JSONB DEFAULT '{}',
            preview_data JSONB DEFAULT '{}',
            is_public BOOLEAN DEFAULT FALSE,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # social_post_templates table
    print("   → Creating social_post_templates table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS social_post_templates (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            organization_id INTEGER REFERENCES organizations(id),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            platform VARCHAR(50) NOT NULL,
            content_template TEXT NOT NULL,
            media_template JSONB DEFAULT '{}',
            hashtags_template TEXT[],
            variables JSONB DEFAULT '{}',
            category VARCHAR(100),
            is_active BOOLEAN DEFAULT TRUE,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create indexes
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_categories_slug ON content_categories (slug)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_categories_parent_id ON content_categories (parent_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_items_user_id ON content_items (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_items_category_id ON content_items (category_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_items_status ON content_items (status)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_items_published_at ON content_items (published_at)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_templates_user_id ON content_templates (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_templates_platform ON content_templates (platform)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_social_post_templates_user_id ON social_post_templates (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_social_post_templates_platform ON social_post_templates (platform)"))

def create_analytics_tables(conn):
    """Create analytics and metrics tables"""
    print("3. Creating analytics and metrics tables...")
    
    # metrics table
    print("   → Creating metrics table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS metrics (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER REFERENCES users(id),
            organization_id INTEGER REFERENCES organizations(id),
            metric_name VARCHAR(255) NOT NULL,
            metric_type VARCHAR(50) DEFAULT 'counter',
            value DOUBLE PRECISION NOT NULL,
            unit VARCHAR(50),
            dimensions JSONB DEFAULT '{}',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            period VARCHAR(50) DEFAULT 'instant',
            source VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # content_performance_snapshots table
    print("   → Creating content_performance_snapshots table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS content_performance_snapshots (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            content_id INTEGER REFERENCES content(id),
            content_item_id INTEGER REFERENCES content_items(id),
            platform VARCHAR(50) NOT NULL,
            snapshot_date DATE NOT NULL,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            reach INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            engagement_rate DOUBLE PRECISION DEFAULT 0.0,
            performance_score DOUBLE PRECISION DEFAULT 0.0,
            raw_metrics JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # platform_metrics_snapshots table
    print("   → Creating platform_metrics_snapshots table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS platform_metrics_snapshots (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            organization_id INTEGER REFERENCES organizations(id),
            connection_id INTEGER REFERENCES social_connections(id),
            platform VARCHAR(50) NOT NULL,
            snapshot_date DATE NOT NULL,
            followers_count INTEGER DEFAULT 0,
            following_count INTEGER DEFAULT 0,
            posts_count INTEGER DEFAULT 0,
            engagement_rate DOUBLE PRECISION DEFAULT 0.0,
            reach INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            profile_views INTEGER DEFAULT 0,
            website_clicks INTEGER DEFAULT 0,
            raw_metrics JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create indexes
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_metrics_metric_name ON metrics (metric_name)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_metrics_timestamp ON metrics (timestamp)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_metrics_user_id ON metrics (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_performance_content_id ON content_performance_snapshots (content_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_performance_platform ON content_performance_snapshots (platform)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_performance_snapshot_date ON content_performance_snapshots (snapshot_date)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_platform_metrics_user_id ON platform_metrics_snapshots (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_platform_metrics_platform ON platform_metrics_snapshots (platform)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_platform_metrics_snapshot_date ON platform_metrics_snapshots (snapshot_date)"))

def create_organization_advanced_tables(conn):
    """Create advanced organization tables"""
    print("4. Creating advanced organization tables...")
    
    # organization_invitations table
    print("   → Creating organization_invitations table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS organization_invitations (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            organization_id INTEGER NOT NULL REFERENCES organizations(id),
            invited_by_id INTEGER NOT NULL REFERENCES users(id),
            email VARCHAR(255) NOT NULL,
            role_id INTEGER REFERENCES roles(id),
            invitation_token VARCHAR(255) NOT NULL UNIQUE,
            status VARCHAR(50) DEFAULT 'pending',
            message TEXT,
            expires_at TIMESTAMP NOT NULL,
            accepted_at TIMESTAMP,
            accepted_by_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create indexes
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_org_invitations_organization_id ON organization_invitations (organization_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_org_invitations_email ON organization_invitations (email)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_org_invitations_status ON organization_invitations (status)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_org_invitations_expires_at ON organization_invitations (expires_at)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_org_invitations_token ON organization_invitations (invitation_token)"))

def create_memory_and_research_tables(conn):
    """Create memory and research related tables"""
    print("5. Creating memory and research tables...")
    
    # memory_content table
    print("   → Creating memory_content table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS memory_content (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            memory_id INTEGER NOT NULL REFERENCES memories(id),
            content_id INTEGER REFERENCES content(id),
            content_item_id INTEGER REFERENCES content_items(id),
            relationship_type VARCHAR(50) DEFAULT 'referenced',
            relevance_score DOUBLE PRECISION DEFAULT 0.5,
            context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # research_data table
    print("   → Creating research_data table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS research_data (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            organization_id INTEGER REFERENCES organizations(id),
            title VARCHAR(255) NOT NULL,
            description TEXT,
            research_type VARCHAR(50) DEFAULT 'general',
            data_source VARCHAR(255),
            data_format VARCHAR(50) DEFAULT 'json',
            raw_data JSONB NOT NULL,
            processed_data JSONB DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            tags TEXT[],
            confidence_score DOUBLE PRECISION DEFAULT 0.0,
            is_validated BOOLEAN DEFAULT FALSE,
            validated_by_id INTEGER REFERENCES users(id),
            validated_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create indexes
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_memory_content_memory_id ON memory_content (memory_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_memory_content_content_id ON memory_content (content_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_memory_content_relationship ON memory_content (relationship_type)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_research_data_user_id ON research_data (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_research_data_research_type ON research_data (research_type)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_research_data_created_at ON research_data (created_at)"))

def create_platform_and_admin_tables(conn):
    """Create platform configuration and admin tables"""
    print("6. Creating platform configuration and admin tables...")
    
    # platform_configs table
    print("   → Creating platform_configs table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS platform_configs (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            platform VARCHAR(50) NOT NULL UNIQUE,
            display_name VARCHAR(255) NOT NULL,
            description TEXT,
            api_version VARCHAR(50),
            base_url VARCHAR(512),
            auth_type VARCHAR(50) DEFAULT 'oauth2',
            client_id VARCHAR(255),
            client_secret VARCHAR(255),
            scopes TEXT[],
            rate_limits JSONB DEFAULT '{}',
            features JSONB DEFAULT '{}',
            webhook_config JSONB DEFAULT '{}',
            is_enabled BOOLEAN DEFAULT TRUE,
            maintenance_mode BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # system_settings table
    print("   → Creating system_settings table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS system_settings (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            setting_key VARCHAR(255) NOT NULL UNIQUE,
            setting_value TEXT,
            value_type VARCHAR(50) DEFAULT 'string',
            category VARCHAR(100) DEFAULT 'general',
            description TEXT,
            is_encrypted BOOLEAN DEFAULT FALSE,
            is_public BOOLEAN DEFAULT FALSE,
            validation_rule TEXT,
            default_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by_id INTEGER REFERENCES admin_users(id)
        )
    """))
    
    # user_management table
    print("   → Creating user_management table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_management (
            id SERIAL PRIMARY KEY,
            public_id VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            managed_by_id INTEGER NOT NULL REFERENCES admin_users(id),
            action VARCHAR(100) NOT NULL,
            reason TEXT,
            previous_status VARCHAR(50),
            new_status VARCHAR(50),
            effective_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expiry_date TIMESTAMP,
            notes TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create indexes
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_platform_configs_platform ON platform_configs (platform)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_platform_configs_is_enabled ON platform_configs (is_enabled)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_system_settings_setting_key ON system_settings (setting_key)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_system_settings_category ON system_settings (category)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_management_user_id ON user_management (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_management_managed_by_id ON user_management (managed_by_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_management_action ON user_management (action)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_management_created_at ON user_management (created_at)"))

def main():
    """Main table creation function"""
    print("🚀 Creating ALL Remaining Missing Tables...")
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
        
        # Create all remaining tables in transaction
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                create_api_security_tables(conn)
                create_content_advanced_tables(conn) 
                create_analytics_tables(conn)
                create_organization_advanced_tables(conn)
                create_memory_and_research_tables(conn)
                create_platform_and_admin_tables(conn)
                
                # Update Alembic version
                print("7. Updating Alembic version...")
                conn.execute(text("""
                    UPDATE alembic_version 
                    SET version_num = '004_all_remaining_tables'
                """))
                
                trans.commit()
                
                print("\n" + "=" * 60)
                print("🎉 ALL remaining tables created successfully!")
                print("\nTables created (15 total):")
                
                print("\n📋 API Security:")
                print("  • api_key_revocations - API key security management")
                print("  • refresh_token_blacklist - Token security")
                
                print("\n📝 Advanced Content Management:")
                print("  • content_categories - Content categorization")
                print("  • content_items - Advanced content items")
                print("  • content_templates - Content templates")
                print("  • social_post_templates - Social post templates")
                
                print("\n📊 Analytics & Metrics:")
                print("  • metrics - System metrics tracking")
                print("  • content_performance_snapshots - Content analytics")
                print("  • platform_metrics_snapshots - Platform analytics")
                
                print("\n🏢 Organization Advanced:")
                print("  • organization_invitations - Organization invites")
                
                print("\n🧠 Memory & Research:")
                print("  • memory_content - Memory content relationships")
                print("  • research_data - Research data storage")
                
                print("\n⚙️ Platform & Admin:")
                print("  • platform_configs - Platform configurations") 
                print("  • system_settings - System configuration")
                print("  • user_management - User management tools")
                
                print("\n🔄 Migration:")
                print("  • Alembic version updated to: 004_all_remaining_tables")
                
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