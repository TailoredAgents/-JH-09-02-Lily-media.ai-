#!/usr/bin/env python3
"""
Direct deployment script for Plan model
Bypasses Alembic migration issues and applies schema directly
"""

import sys
sys.path.append('/Users/jeffreyhacker/Lily-Media.AI/socialmedia2')

from backend.db.database import engine
from backend.db.models import Plan, User, Base
from sqlalchemy import text, inspect

def create_plan_model_directly():
    """
    Create Plan model directly in database, bypassing Alembic issues
    """
    try:
        print("🚀 Starting direct Plan model deployment...")
        
        # Use global engine
        db_engine = engine
        
        # Check if plans table already exists
        inspector = inspect(db_engine)
        existing_tables = inspector.get_table_names()
        
        if 'plans' in existing_tables:
            print("✅ Plans table already exists, skipping creation")
        else:
            # Create plans table directly using SQLAlchemy
            print("📊 Creating plans table...")
            Plan.__table__.create(db_engine, checkfirst=True)
            print("✅ Plans table created successfully")
        
        # Check if plan_id column exists in users table
        user_columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'plan_id' not in user_columns:
            print("🔗 Adding plan_id column to users table...")
            with db_engine.connect() as conn:
                # Add plan_id column
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN plan_id INTEGER REFERENCES plans(id)
                """))
                conn.commit()
            print("✅ plan_id column added to users table")
        else:
            print("✅ plan_id column already exists in users table")
        
        # Seed plan data
        print("🌱 Seeding plan data...")
        with db_engine.connect() as conn:
            # Check if plans already exist
            result = conn.execute(text("SELECT COUNT(*) FROM plans"))
            count = result.scalar()
            
            if count == 0:
                # Insert starter plan
                conn.execute(text("""
                    INSERT INTO plans (
                        name, display_name, description, monthly_price, annual_price, 
                        trial_days, max_social_profiles, max_users, max_workspaces,
                        max_posts_per_day, max_posts_per_week, features, 
                        full_ai, enhanced_autopilot, ai_inbox, crm_integration,
                        advanced_analytics, predictive_analytics, white_label,
                        basic_ai_only, premium_ai_models, image_generation_limit,
                        autopilot_posts_per_day, autopilot_research_enabled, 
                        autopilot_ad_campaigns, is_active, is_popular, sort_order,
                        created_at
                    ) VALUES (
                        'starter', 'Starter', 
                        'Perfect for individuals getting started with AI-powered social media management',
                        29.00, 290.00, 14, 5, 1, 1, 5, 25,
                        '{"basic_content_generation": true, "basic_scheduling": true, "basic_analytics": true, "email_support": true}',
                        false, false, false, false, false, false, false, true, false,
                        10, 1, false, false, true, false, 1, NOW()
                    )
                """))
                
                # Insert pro plan
                conn.execute(text("""
                    INSERT INTO plans (
                        name, display_name, description, monthly_price, annual_price, 
                        trial_days, max_social_profiles, max_users, max_workspaces,
                        max_posts_per_day, max_posts_per_week, features, 
                        full_ai, enhanced_autopilot, ai_inbox, crm_integration,
                        advanced_analytics, predictive_analytics, white_label,
                        basic_ai_only, premium_ai_models, image_generation_limit,
                        autopilot_posts_per_day, autopilot_research_enabled, 
                        autopilot_ad_campaigns, is_active, is_popular, sort_order,
                        created_at
                    ) VALUES (
                        'pro', 'Pro', 
                        'Advanced features for growing businesses and marketing teams',
                        79.00, 790.00, 14, 25, 5, 3, 15, 100,
                        '{"advanced_content_generation": true, "multi_platform_scheduling": true, "advanced_analytics": true, "team_collaboration": true, "priority_support": true, "custom_branding": true}',
                        true, true, true, false, true, false, false, false, true,
                        50, 5, true, true, true, true, 2, NOW()
                    )
                """))
                
                # Insert enterprise plan
                conn.execute(text("""
                    INSERT INTO plans (
                        name, display_name, description, monthly_price, annual_price, 
                        trial_days, max_social_profiles, max_users, max_workspaces,
                        max_posts_per_day, max_posts_per_week, features, 
                        full_ai, enhanced_autopilot, ai_inbox, crm_integration,
                        advanced_analytics, predictive_analytics, white_label,
                        basic_ai_only, premium_ai_models, image_generation_limit,
                        autopilot_posts_per_day, autopilot_research_enabled, 
                        autopilot_ad_campaigns, is_active, is_popular, sort_order,
                        created_at
                    ) VALUES (
                        'enterprise', 'Enterprise', 
                        'Full-featured solution for large organizations with custom requirements',
                        199.00, 1990.00, 30, 100, 25, 10, 50, 300,
                        '{"enterprise_content_generation": true, "unlimited_scheduling": true, "enterprise_analytics": true, "advanced_team_management": true, "dedicated_support": true, "white_label_branding": true, "custom_integrations": true, "sso_support": true}',
                        true, true, true, true, true, true, true, false, true,
                        200, 15, true, true, true, false, 3, NOW()
                    )
                """))
                
                conn.commit()
                print("✅ Plan data seeded successfully")
                
                # Migrate existing users to Starter plan
                starter_result = conn.execute(text("SELECT id FROM plans WHERE name = 'starter' LIMIT 1"))
                starter_plan_id = starter_result.scalar()
                
                if starter_plan_id:
                    conn.execute(text(f"UPDATE users SET plan_id = {starter_plan_id} WHERE plan_id IS NULL"))
                    conn.commit()
                    print("✅ Existing users migrated to Starter plan")
                    
            else:
                print("✅ Plan data already exists, skipping seed")
        
        print("🎉 Plan model deployment completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during Plan model deployment: {e}")
        return False

if __name__ == "__main__":
    result = create_plan_model_directly()
    if not result:
        sys.exit(1)
    print("✅ Plan model ready for use!")