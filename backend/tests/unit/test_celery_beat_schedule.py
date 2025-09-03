"""
Unit tests for Celery Beat scheduler configuration
Validates beat schedule entries, queues, timing, and task registration
"""
import pytest
from datetime import timedelta
from backend.tasks.celery_app import celery_app


class TestCeleryBeatSchedule:
    """Test Celery Beat schedule configuration"""

    def test_beat_schedule_exists(self):
        """Verify beat_schedule is configured"""
        assert hasattr(celery_app.conf, 'beat_schedule')
        assert celery_app.conf.beat_schedule is not None
        assert len(celery_app.conf.beat_schedule) > 0

    def test_autonomous_daily_content_schedule(self):
        """Test autonomous daily content generation schedule"""
        schedule = celery_app.conf.beat_schedule.get('autonomous-daily-content')
        
        assert schedule is not None, "autonomous-daily-content schedule missing"
        assert schedule['task'] == 'autonomous_daily_content_generation'
        assert schedule['schedule'] == 60.0 * 60.0 * 24  # Daily (86400 seconds)
        assert schedule['options']['queue'] == 'autonomous'

    def test_autonomous_weekly_report_schedule(self):
        """Test autonomous weekly report schedule"""
        schedule = celery_app.conf.beat_schedule.get('autonomous-weekly-report')
        
        assert schedule is not None, "autonomous-weekly-report schedule missing"
        assert schedule['task'] == 'autonomous_weekly_report'
        assert schedule['schedule'] == 60.0 * 60.0 * 24 * 7  # Weekly (604800 seconds)
        assert schedule['options']['queue'] == 'reports'

    def test_autonomous_metrics_collection_schedule(self):
        """Test autonomous metrics collection schedule"""
        schedule = celery_app.conf.beat_schedule.get('autonomous-metrics-collection')
        
        assert schedule is not None, "autonomous-metrics-collection schedule missing"
        assert schedule['task'] == 'autonomous_metrics_collection'
        assert schedule['schedule'] == 60.0 * 60.0 * 24  # Daily (86400 seconds)
        assert schedule['options']['queue'] == 'metrics'

    def test_autonomous_content_posting_schedule(self):
        """Test autonomous content posting schedule"""
        schedule = celery_app.conf.beat_schedule.get('autonomous-content-posting')
        
        assert schedule is not None, "autonomous-content-posting schedule missing"
        assert schedule['task'] == 'autonomous_content_posting'
        assert schedule['schedule'] == 60.0 * 15  # Every 15 minutes (900 seconds)
        assert schedule['options']['queue'] == 'posting'

    def test_lightweight_research_schedule(self):
        """Test lightweight research schedule"""
        schedule = celery_app.conf.beat_schedule.get('lightweight-research')
        
        assert schedule is not None, "lightweight-research schedule missing"
        assert schedule['task'] == 'backend.tasks.lightweight_research_tasks.lightweight_daily_research'
        assert schedule['schedule'] == 60.0 * 60.0 * 8  # Every 8 hours (28800 seconds)
        assert schedule['options']['queue'] == 'research'
        assert schedule['options']['expires'] == 300  # 5 min expiry

    def test_token_health_audit_schedule(self):
        """Test token health audit schedule"""
        schedule = celery_app.conf.beat_schedule.get('token-health-audit')
        
        assert schedule is not None, "token-health-audit schedule missing"
        assert schedule['task'] == 'backend.tasks.token_health_tasks.audit_all_tokens'
        assert schedule['schedule'] == 60.0 * 60.0 * 24  # Daily (86400 seconds)
        assert schedule['options']['queue'] == 'token_health'
        assert schedule['options']['expires'] == 1800  # 30 min expiry

    def test_x_mentions_polling_schedule(self):
        """Test X mentions polling schedule"""
        schedule = celery_app.conf.beat_schedule.get('x-mentions-polling')
        
        assert schedule is not None, "x-mentions-polling schedule missing"
        assert schedule['task'] == 'backend.tasks.x_polling_tasks.poll_all_x_mentions'
        assert schedule['schedule'] == 60.0 * 15  # Every 15 minutes (900 seconds)
        assert schedule['options']['queue'] == 'x_polling'
        assert schedule['options']['expires'] == 600  # 10 min expiry

    def test_cleanup_old_audits_schedule(self):
        """Test cleanup old audits schedule"""
        schedule = celery_app.conf.beat_schedule.get('cleanup-old-audits')
        
        assert schedule is not None, "cleanup-old-audits schedule missing"
        assert schedule['task'] == 'backend.tasks.token_health_tasks.cleanup_old_audits'
        assert schedule['schedule'] == 60.0 * 60.0 * 24 * 7  # Weekly (604800 seconds)
        assert schedule['options']['queue'] == 'token_health'
        assert schedule['options']['expires'] == 3600  # 1 hour expiry

    def test_all_scheduled_tasks_have_required_fields(self):
        """Verify all scheduled tasks have required fields"""
        required_fields = ['task', 'schedule', 'options']
        required_option_fields = ['queue']
        
        for task_name, schedule_config in celery_app.conf.beat_schedule.items():
            # Check required top-level fields
            for field in required_fields:
                assert field in schedule_config, f"Task '{task_name}' missing required field '{field}'"
            
            # Check required option fields
            for field in required_option_fields:
                assert field in schedule_config['options'], f"Task '{task_name}' missing required option '{field}'"
            
            # Verify schedule is positive number
            assert isinstance(schedule_config['schedule'], (int, float)), f"Task '{task_name}' schedule must be numeric"
            assert schedule_config['schedule'] > 0, f"Task '{task_name}' schedule must be positive"
            
            # Verify task name is not empty
            assert schedule_config['task'].strip(), f"Task '{task_name}' has empty task name"
            
            # Verify queue is not empty
            assert schedule_config['options']['queue'].strip(), f"Task '{task_name}' has empty queue"

    def test_schedule_intervals_are_reasonable(self):
        """Test that schedule intervals are reasonable for production"""
        # Define reasonable bounds (in seconds)
        MIN_INTERVAL = 60  # 1 minute minimum
        MAX_INTERVAL = 60 * 60 * 24 * 7  # 1 week maximum
        
        for task_name, schedule_config in celery_app.conf.beat_schedule.items():
            interval = schedule_config['schedule']
            
            assert interval >= MIN_INTERVAL, f"Task '{task_name}' interval too short: {interval}s < {MIN_INTERVAL}s"
            assert interval <= MAX_INTERVAL, f"Task '{task_name}' interval too long: {interval}s > {MAX_INTERVAL}s"

    def test_critical_tasks_have_appropriate_frequencies(self):
        """Test that critical tasks have appropriate frequencies"""
        critical_tasks = {
            'autonomous-content-posting': 15 * 60,  # Should run every 15 minutes
            'x-mentions-polling': 15 * 60,          # Should run every 15 minutes
            'autonomous-daily-content': 24 * 60 * 60,  # Should run daily
            'token-health-audit': 24 * 60 * 60,       # Should run daily
        }
        
        for task_name, expected_interval in critical_tasks.items():
            schedule = celery_app.conf.beat_schedule.get(task_name)
            assert schedule is not None, f"Critical task '{task_name}' is missing from schedule"
            assert schedule['schedule'] == expected_interval, \
                f"Task '{task_name}' has incorrect interval: {schedule['schedule']}s != {expected_interval}s"

    def test_queue_assignments_are_logical(self):
        """Test that tasks are assigned to appropriate queues"""
        expected_queues = {
            'autonomous-daily-content': 'autonomous',
            'autonomous-weekly-report': 'reports',
            'autonomous-metrics-collection': 'metrics',
            'autonomous-content-posting': 'posting',
            'lightweight-research': 'research',
            'token-health-audit': 'token_health',
            'x-mentions-polling': 'x_polling',
            'cleanup-old-audits': 'token_health'
        }
        
        for task_name, expected_queue in expected_queues.items():
            schedule = celery_app.conf.beat_schedule.get(task_name)
            assert schedule is not None, f"Task '{task_name}' missing from schedule"
            actual_queue = schedule['options']['queue']
            assert actual_queue == expected_queue, \
                f"Task '{task_name}' in wrong queue: '{actual_queue}' != '{expected_queue}'"

    def test_expiry_settings_prevent_task_buildup(self):
        """Test that tasks with expiry settings prevent buildup"""
        tasks_with_expiry = {
            'lightweight-research': 300,      # 5 min
            'token-health-audit': 1800,       # 30 min
            'x-mentions-polling': 600,        # 10 min
            'cleanup-old-audits': 3600        # 1 hour
        }
        
        for task_name, expected_expiry in tasks_with_expiry.items():
            schedule = celery_app.conf.beat_schedule.get(task_name)
            assert schedule is not None, f"Task '{task_name}' missing from schedule"
            
            options = schedule['options']
            assert 'expires' in options, f"Task '{task_name}' missing expires option"
            assert options['expires'] == expected_expiry, \
                f"Task '{task_name}' wrong expiry: {options['expires']}s != {expected_expiry}s"

    def test_celery_app_configuration(self):
        """Test basic Celery app configuration"""
        # Test basic settings
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.accept_content == ["json"]
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True
        
        # Test memory optimization settings
        assert celery_app.conf.worker_concurrency == 1
        assert celery_app.conf.worker_prefetch_multiplier == 1
        assert celery_app.conf.worker_max_tasks_per_child == 5
        assert celery_app.conf.worker_pool == 'threads'

    def test_task_modules_are_included(self):
        """Test that all task modules are properly included"""
        expected_modules = [
            "backend.tasks.lightweight_research_tasks",
            "backend.tasks.posting_tasks",
            "backend.tasks.autonomous_scheduler",
            "backend.tasks.webhook_tasks",
            "backend.tasks.token_health_tasks",
            "backend.tasks.x_polling_tasks"
        ]
        
        for module in expected_modules:
            assert module in celery_app.conf.include, f"Task module '{module}' not included in Celery configuration"

    def test_no_duplicate_task_names(self):
        """Ensure no duplicate task names in beat schedule"""
        task_names = [config['task'] for config in celery_app.conf.beat_schedule.values()]
        unique_task_names = set(task_names)
        
        assert len(task_names) == len(unique_task_names), \
            f"Duplicate task names found in beat schedule: {[name for name in task_names if task_names.count(name) > 1]}"

    def test_schedule_keys_are_descriptive(self):
        """Test that schedule keys are descriptive and follow naming convention"""
        for schedule_key in celery_app.conf.beat_schedule.keys():
            # Should contain descriptive words
            assert len(schedule_key) > 5, f"Schedule key '{schedule_key}' too short"
            
            # Should use hyphen convention
            if '-' not in schedule_key:
                # Allow single words for very descriptive keys
                assert len(schedule_key) > 10, f"Schedule key '{schedule_key}' should use hyphens or be more descriptive"
            
            # Should not contain underscores (prefer hyphens for consistency)
            assert '_' not in schedule_key, f"Schedule key '{schedule_key}' should use hyphens instead of underscores"