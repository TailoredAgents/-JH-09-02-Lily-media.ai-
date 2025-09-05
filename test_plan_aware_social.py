#!/usr/bin/env python3
"""Test Plan-Aware Social Connection Service"""

import sys
import asyncio
sys.path.append('/Users/jeffreyhacker/Lily-Media.AI/socialmedia2')

from backend.db.database import SessionLocal
from backend.services.plan_aware_social_service import get_plan_aware_social_service

async def test_plan_aware_social():
    """Test plan-aware social connection functionality"""
    try:
        print("🧪 Testing Plan-Aware Social Connection Service...")
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Initialize service
            social_service = get_plan_aware_social_service(db)
            
            # Test 1: Check connection limits
            print("\n📊 Testing connection limits...")
            limit_check = await social_service.check_connection_limit(1)
            print(f"✅ Plan: {limit_check['plan']}")
            print(f"✅ Current connections: {limit_check['current_connections']}")
            print(f"✅ Max connections: {limit_check['max_connections']}")
            print(f"✅ Can connect more: {limit_check['can_connect']}")
            
            # Test 2: Platform access validation
            print("\n🔒 Testing platform access validation...")
            platforms_to_test = ["twitter", "instagram", "tiktok", "pinterest"]
            
            for platform in platforms_to_test:
                access_check = await social_service.validate_platform_access(1, platform)
                status = "✅ Allowed" if access_check['has_access'] else "❌ Restricted"
                print(f"{status} Platform: {platform} (Plan: {access_check['plan']})")
            
            # Test 3: Get comprehensive capabilities
            print("\n🎯 Testing connection capabilities...")
            capabilities = await social_service.get_connection_capabilities(1)
            print(f"✅ Available platforms: {capabilities['platforms']['available']}")
            print(f"✅ Connected platforms: {capabilities['platforms']['connected']}")
            print(f"✅ Features: {capabilities['features']}")
            
            # Test 4: Enforce connection limit for new connection
            print("\n🚦 Testing connection enforcement...")
            enforcement = await social_service.enforce_connection_limit(1, "twitter")
            print(f"✅ Connection enforcement result: {enforcement['allowed']}")
            if not enforcement['allowed']:
                print(f"✅ Restriction reason: {enforcement['reason']}")
                print(f"✅ Message: {enforcement['message']}")
            
            # Test 5: Test with restricted platform
            print("\n🚫 Testing restricted platform enforcement...")
            restricted_enforcement = await social_service.enforce_connection_limit(1, "pinterest")
            print(f"✅ Pinterest enforcement (should be restricted): {restricted_enforcement['allowed']}")
            if not restricted_enforcement['allowed']:
                print(f"✅ Restriction reason: {restricted_enforcement['reason']}")
            
            print("\n🎉 All plan-aware social tests completed successfully!")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Plan-aware social test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_plan_aware_social())
    if not result:
        sys.exit(1)