#!/usr/bin/env python3
"""
Emergency fix for social inbox schema issues
Drops and recreates tables with correct UUID schema
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_social_inbox_schema():
    """Drop and recreate social inbox tables with correct UUID schema"""
    
    # Get database URL from environment - CRITICAL: Never hard-code credentials
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ CRITICAL: DATABASE_URL environment variable must be set")
        sys.exit(1)
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            logger.info("🔧 Starting social inbox schema fix...")
            
            # Drop existing tables in correct order (foreign keys first)
            tables_to_drop = [
                'interaction_responses',
                'response_templates', 
                'social_interactions',
                'social_platform_connections'
            ]
            
            for table in tables_to_drop:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    logger.info(f"✅ Dropped {table}")
                except Exception as e:
                    logger.warning(f"Could not drop {table}: {e}")
            
            conn.commit()
            
            # Recreate tables with correct UUID schema
            logger.info("🏗️ Creating social_platform_connections table...")
            conn.execute(text("""
                CREATE TABLE social_platform_connections (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    platform VARCHAR NOT NULL,
                    platform_user_id VARCHAR NOT NULL,
                    platform_username VARCHAR NOT NULL,
                    platform_display_name VARCHAR,
                    profile_image_url VARCHAR,
                    profile_url VARCHAR,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    scope VARCHAR,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE,
                    UNIQUE(user_id, platform)
                )
            """))
            
            logger.info("🏗️ Creating social_interactions table...")
            conn.execute(text("""
                CREATE TABLE social_interactions (
                    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    connection_id INTEGER REFERENCES social_platform_connections(id),
                    platform VARCHAR NOT NULL,
                    interaction_type VARCHAR NOT NULL,
                    platform_interaction_id VARCHAR NOT NULL,
                    parent_id VARCHAR,
                    thread_id VARCHAR,
                    author_platform_id VARCHAR NOT NULL,
                    author_username VARCHAR NOT NULL,
                    author_display_name VARCHAR,
                    author_profile_image VARCHAR,
                    content TEXT,
                    media_urls JSON DEFAULT '[]',
                    hashtags JSON DEFAULT '[]',
                    mentions JSON DEFAULT '[]',
                    sentiment VARCHAR,
                    intent VARCHAR,
                    priority_score FLOAT DEFAULT 0.0,
                    status VARCHAR DEFAULT 'unread',
                    response_strategy VARCHAR,
                    escalation_reason TEXT,
                    platform_created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    platform_updated_at TIMESTAMP WITH TIME ZONE,
                    received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP WITH TIME ZONE,
                    metadata JSON DEFAULT '{}',
                    UNIQUE(platform, platform_interaction_id)
                )
            """))
            
            logger.info("🏗️ Creating response_templates table...")
            conn.execute(text("""
                CREATE TABLE response_templates (
                    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR NOT NULL,
                    description TEXT,
                    trigger_type VARCHAR NOT NULL,
                    trigger_conditions JSON DEFAULT '{}',
                    keywords JSON DEFAULT '[]',
                    platforms JSON DEFAULT '[]',
                    response_text TEXT NOT NULL,
                    variables JSON DEFAULT '[]',
                    personality_style VARCHAR DEFAULT 'professional',
                    tone VARCHAR DEFAULT 'helpful',
                    auto_approve BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    priority INTEGER DEFAULT 1,
                    usage_count INTEGER DEFAULT 0,
                    avg_satisfaction FLOAT DEFAULT 0.0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            
            logger.info("🏗️ Creating interaction_responses table...")
            conn.execute(text("""
                CREATE TABLE interaction_responses (
                    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
                    interaction_id VARCHAR NOT NULL REFERENCES social_interactions(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    response_text TEXT NOT NULL,
                    media_urls JSON DEFAULT '[]',
                    response_type VARCHAR DEFAULT 'manual',
                    template_id VARCHAR REFERENCES response_templates(id),
                    ai_confidence_score FLOAT DEFAULT 0.0,
                    platform VARCHAR NOT NULL,
                    platform_response_id VARCHAR,
                    platform_url VARCHAR,
                    status VARCHAR DEFAULT 'draft',
                    sent_at TIMESTAMP WITH TIME ZONE,
                    failure_reason TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            
            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS ix_social_platform_connections_user_id ON social_platform_connections (user_id)",
                "CREATE INDEX IF NOT EXISTS ix_social_platform_connections_platform ON social_platform_connections (platform)",
                "CREATE INDEX IF NOT EXISTS ix_social_interactions_user_id ON social_interactions (user_id)",
                "CREATE INDEX IF NOT EXISTS ix_social_interactions_platform ON social_interactions (platform)",
                "CREATE INDEX IF NOT EXISTS ix_social_interactions_status ON social_interactions (status)",
                "CREATE INDEX IF NOT EXISTS ix_social_interactions_received_at ON social_interactions (received_at)",
                "CREATE INDEX IF NOT EXISTS ix_response_templates_user_id ON response_templates (user_id)",
                "CREATE INDEX IF NOT EXISTS ix_response_templates_trigger_type ON response_templates (trigger_type)",
                "CREATE INDEX IF NOT EXISTS ix_interaction_responses_interaction_id ON interaction_responses (interaction_id)",
                "CREATE INDEX IF NOT EXISTS ix_interaction_responses_user_id ON interaction_responses (user_id)"
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                except Exception as e:
                    logger.warning(f"Could not create index: {e}")
            
            conn.commit()
            logger.info("✅ Social inbox schema fix completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Schema fix failed: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = fix_social_inbox_schema()
    sys.exit(0 if success else 1)