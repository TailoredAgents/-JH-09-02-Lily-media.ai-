#!/usr/bin/env python3
"""
Test script for startup health gates
P1-3b: Verify startup health gates implementation
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_health_gates():
    """Test the startup health gates"""
    try:
        from backend.core.startup_health_gates import StartupHealthGates
        
        print("🔍 Testing Startup Health Gates...")
        print("-" * 50)
        
        health_gates = StartupHealthGates()
        result = await health_gates.run_health_gates()
        
        print(f"\n📊 HEALTH GATES SUMMARY:")
        print(f"Overall Status: {result.overall_status.value.upper()}")
        print(f"Ready for Traffic: {'✅ YES' if result.ready_for_traffic else '❌ NO'}")
        print(f"Duration: {result.total_duration_ms:.1f}ms")
        print(f"Passed: {result.passed_checks}")
        print(f"Failed: {result.failed_checks}")
        print(f"Warnings: {result.warning_checks}")
        print(f"Skipped: {result.skipped_checks}")
        
        print(f"\n📋 DETAILED RESULTS:")
        for check in result.check_results:
            status_icon = {
                'pass': '✅',
                'fail': '❌', 
                'warn': '⚠️',
                'skip': '⏭️'
            }.get(check.status.value, '❓')
            
            print(f"{status_icon} {check.name}: {check.message} ({check.duration_ms:.1f}ms)")
            
            if check.details and check.status.value in ['fail', 'warn']:
                for key, value in check.details.items():
                    if isinstance(value, list) and len(value) > 0:
                        print(f"    {key}: {len(value)} items")
                        for item in value[:3]:  # Show first 3 items
                            print(f"      - {item}")
                        if len(value) > 3:
                            print(f"      ... and {len(value) - 3} more")
        
        print(f"\n🎯 RESULT: Health gates {'PASSED' if result.ready_for_traffic else 'FAILED'}")
        return result.ready_for_traffic
        
    except Exception as e:
        print(f"❌ Error testing health gates: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_health_gates())
    sys.exit(0 if success else 1)