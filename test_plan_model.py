#!/usr/bin/env python3
"""Test Plan model database integration"""

import sys
sys.path.append('/Users/jeffreyhacker/Lily-Media.AI/socialmedia2')

from backend.db.database import engine
from sqlalchemy import text

def test_plan_model():
    """Test Plan model database integration"""
    try:
        print("🧪 Testing Plan model database integration...")
        
        with engine.connect() as conn:
            # Test Plan table query
            result = conn.execute(text('SELECT name, display_name, monthly_price, max_social_profiles FROM plans ORDER BY sort_order'))
            plans = result.fetchall()
            print('✅ Plan table query successful:')
            for plan in plans:
                print(f'  - {plan.display_name}: ${plan.monthly_price}/mo, {plan.max_social_profiles} profiles')
            
            # Test user-plan relationship
            user_result = conn.execute(text('SELECT COUNT(*) as count FROM users WHERE plan_id IS NOT NULL'))
            user_count = user_result.scalar()
            print(f'✅ Users with plans: {user_count}')
            
            print("🎉 Plan model integration test passed!")
            return True
            
    except Exception as e:
        print(f"❌ Plan model test failed: {e}")
        return False

if __name__ == "__main__":
    result = test_plan_model()
    if not result:
        sys.exit(1)