#!/usr/bin/env python3
"""Test PlanService functionality"""

import sys
sys.path.append('/Users/jeffreyhacker/Lily-Media.AI/socialmedia2')

from backend.db.database import engine, SessionLocal
from backend.services.plan_service import PlanService
from sqlalchemy import text

def test_plan_service():
    """Test PlanService functionality"""
    try:
        print("🧪 Testing PlanService functionality...")
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Initialize service
            plan_service = PlanService(db)
            
            # Test 1: Get all plans
            print("\n📋 Testing get_all_plans()...")
            plans = plan_service.get_all_plans()
            print(f"✅ Found {len(plans)} active plans:")
            for plan in plans:
                print(f"  - {plan.display_name}: ${plan.monthly_price}/mo")
            
            # Test 2: Get plan by name
            print("\n📋 Testing get_plan_by_name()...")
            starter_plan = plan_service.get_plan_by_name("starter")
            if starter_plan:
                print(f"✅ Starter plan found: {starter_plan.display_name}")
            else:
                print("❌ Starter plan not found")
                return False
            
            # Test 3: Get user capabilities (assuming user ID 1 exists)
            print("\n👤 Testing user capabilities...")
            # First, check if we have any users
            with engine.connect() as conn:
                user_result = conn.execute(text("SELECT id FROM users LIMIT 1"))
                user_row = user_result.first()
                
                if not user_row:
                    print("⚠️ No users found, creating test user...")
                    conn.execute(text("""
                        INSERT INTO users (email, username, is_active, plan_id)
                        VALUES ('test@example.com', 'testuser', true, 1)
                    """))
                    conn.commit()
                    user_id = conn.execute(text("SELECT id FROM users WHERE email = 'test@example.com'")).scalar()
                else:
                    user_id = user_row.id
                
                print(f"Using user ID: {user_id}")
                
            capabilities = plan_service.get_user_capabilities(user_id)
            print(f"✅ User plan: {capabilities.get_plan_name()}")
            print(f"✅ Has full AI: {capabilities.has_full_ai_access()}")
            print(f"✅ Max social profiles: {capabilities.plan.max_social_profiles if capabilities.plan else 1}")
            print(f"✅ Posts per day: {capabilities.plan.max_posts_per_day if capabilities.plan else 3}")
            
            # Test 4: Feature list
            print("\n🎯 Testing get_feature_list()...")
            features = capabilities.get_feature_list()
            print(f"✅ Feature list has {len(features)} features")
            print(f"  Plan: {features.get('plan_name')}")
            print(f"  Max profiles: {features.get('max_social_profiles')}")
            
            # Test 5: Plan comparison
            print("\n📊 Testing get_plan_comparison()...")
            comparison = plan_service.get_plan_comparison()
            print(f"✅ Plan comparison data for {len(comparison)} plans")
            for plan_data in comparison:
                print(f"  - {plan_data['display_name']}: ${plan_data['monthly_price']}/mo")
            
            print("\n🎉 All PlanService tests passed!")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ PlanService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_plan_service()
    if not result:
        sys.exit(1)