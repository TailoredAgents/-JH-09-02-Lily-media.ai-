#!/usr/bin/env python3
"""
Validation script for Celery Beat scheduler tests
Runs basic checks without requiring pytest installation
"""
import sys
import traceback
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def validate_celery_beat_schedule():
    """Validate Celery Beat schedule configuration"""
    try:
        from backend.tasks.celery_app import celery_app
        
        print("✅ Successfully imported celery_app")
        
        # Check beat_schedule exists
        if not hasattr(celery_app.conf, 'beat_schedule'):
            print("❌ beat_schedule not found in celery configuration")
            return False
        
        print("✅ beat_schedule found in celery configuration")
        
        # Check required scheduled tasks
        required_tasks = [
            'autonomous-daily-content',
            'autonomous-weekly-report',
            'autonomous-metrics-collection',
            'autonomous-content-posting',
            'lightweight-research',
            'token-health-audit',
            'x-mentions-polling',
            'cleanup-old-audits'
        ]
        
        beat_schedule = celery_app.conf.beat_schedule
        missing_tasks = []
        
        for task_name in required_tasks:
            if task_name not in beat_schedule:
                missing_tasks.append(task_name)
            else:
                schedule = beat_schedule[task_name]
                # Validate required fields
                required_fields = ['task', 'schedule', 'options']
                missing_fields = [field for field in required_fields if field not in schedule]
                
                if missing_fields:
                    print(f"❌ Task '{task_name}' missing fields: {missing_fields}")
                    return False
                
                # Validate queue in options
                if 'queue' not in schedule['options']:
                    print(f"❌ Task '{task_name}' missing queue option")
                    return False
                
                # Validate schedule is numeric and positive
                if not isinstance(schedule['schedule'], (int, float)) or schedule['schedule'] <= 0:
                    print(f"❌ Task '{task_name}' has invalid schedule: {schedule['schedule']}")
                    return False
                
                print(f"✅ Task '{task_name}' validated: {schedule['schedule']}s interval, queue '{schedule['options']['queue']}'")
        
        if missing_tasks:
            print(f"❌ Missing scheduled tasks: {missing_tasks}")
            return False
        
        print(f"✅ All {len(required_tasks)} scheduled tasks validated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error validating celery beat schedule: {e}")
        traceback.print_exc()
        return False

def validate_autonomous_scheduler():
    """Validate autonomous scheduler imports and basic functionality"""
    try:
        from backend.tasks.autonomous_scheduler import (
            AutonomousScheduler,
            daily_content_generation,
            weekly_report_generation,
            nightly_metrics_collection,
            process_scheduled_content
        )
        
        print("✅ Successfully imported autonomous scheduler tasks")
        
        # Test AutonomousScheduler instantiation
        scheduler = AutonomousScheduler()
        print("✅ AutonomousScheduler instantiated successfully")
        
        # Check that all task functions are callable
        task_functions = [
            daily_content_generation,
            weekly_report_generation,
            nightly_metrics_collection,
            process_scheduled_content
        ]
        
        for func in task_functions:
            if not callable(func):
                print(f"❌ Task function {func.__name__} is not callable")
                return False
            print(f"✅ Task function '{func.__name__}' is callable")
        
        return True
        
    except Exception as e:
        print(f"❌ Error validating autonomous scheduler: {e}")
        traceback.print_exc()
        return False

def validate_test_files():
    """Validate that test files can be imported"""
    try:
        # Test unit test file
        sys.path.insert(0, str(Path(__file__).parent / "backend" / "tests" / "unit"))
        import test_celery_beat_schedule
        print("✅ Unit test file 'test_celery_beat_schedule.py' imports successfully")
        
        # Test integration test file
        sys.path.insert(0, str(Path(__file__).parent / "backend" / "tests" / "integration"))
        import test_autonomous_scheduler_flow
        print("✅ Integration test file 'test_autonomous_scheduler_flow.py' imports successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Error validating test files: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all validation checks"""
    print("🔍 Validating Celery Beat Scheduler Tests")
    print("=" * 50)
    
    checks = [
        ("Celery Beat Schedule Configuration", validate_celery_beat_schedule),
        ("Autonomous Scheduler Tasks", validate_autonomous_scheduler),
        ("Test Files Import", validate_test_files)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}")
        print("-" * len(check_name))
        
        if check_func():
            print(f"✅ {check_name} - PASSED")
        else:
            print(f"❌ {check_name} - FAILED")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All validation checks PASSED!")
        print("Celery Beat scheduler tests are ready to run with pytest")
        return 0
    else:
        print("💥 Some validation checks FAILED!")
        print("Please fix the issues before running the full test suite")
        return 1

if __name__ == "__main__":
    sys.exit(main())