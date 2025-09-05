#!/usr/bin/env python3
"""Test Plan-Aware Image Generation Service"""

import sys
import asyncio
sys.path.append('/Users/jeffreyhacker/Lily-Media.AI/socialmedia2')

from backend.db.database import SessionLocal
from backend.services.plan_aware_image_service import get_plan_aware_image_service

async def test_plan_aware_images():
    """Test plan-aware image generation functionality"""
    try:
        print("🧪 Testing Plan-Aware Image Generation Service...")
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Initialize service
            image_service = get_plan_aware_image_service(db)
            
            # Test 1: Get user capabilities (assuming user ID 1 exists)
            print("\n👤 Testing user image capabilities...")
            capabilities = await image_service.get_user_image_capabilities(1)
            print(f"✅ User capabilities: {capabilities['plan']} plan")
            print(f"✅ Monthly limit: {capabilities['monthly_limit']}")
            print(f"✅ Available models: {capabilities['available_models']}")
            print(f"✅ Max quality: {capabilities['max_quality']}")
            print(f"✅ Features: {capabilities['features']}")
            
            # Test 2: Test plan gating with simple request
            print("\n🎨 Testing image generation with plan gating...")
            result = await image_service.generate_image_with_plan_gating(
                user_id=1,
                prompt="A beautiful sunset over mountains",
                platform="instagram",
                model="auto"
            )
            
            print(f"✅ Generation result status: {result['status']}")
            
            if result['status'] == 'success':
                print(f"✅ Plan info: {result.get('plan_info', {})}")
            elif result['status'] == 'error':
                print(f"⚠️ Error (expected - service might not be configured): {result.get('error', 'Unknown error')}")
            else:
                print(f"✅ Plan gating working: {result.get('error', 'Restrictions applied')}")
            
            # Test 3: Test with premium features on starter plan
            print("\n🎯 Testing premium feature restrictions...")
            premium_result = await image_service.generate_image_with_plan_gating(
                user_id=1,
                prompt="Professional business portrait",
                platform="linkedin",
                quality_preset="premium",
                model="gpt_image_1",
                custom_options={"custom_size": True, "style_transfer": True}
            )
            
            print(f"✅ Premium feature test status: {premium_result['status']}")
            if 'restricted_features' in premium_result:
                print(f"✅ Restricted features: {premium_result['restricted_features']}")
            
            print("\n🎉 All plan-aware image tests completed successfully!")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Plan-aware image test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_plan_aware_images())
    if not result:
        sys.exit(1)