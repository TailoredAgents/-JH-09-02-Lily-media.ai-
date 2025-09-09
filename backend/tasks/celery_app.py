# Import warning suppression FIRST before any other imports
from backend.core.suppress_warnings import suppress_third_party_warnings
suppress_third_party_warnings()

import os
from celery import Celery
from backend.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_social_media_agent",
    broker=settings.get_celery_broker_url(),
    backend=settings.get_celery_result_backend(),
    include=[
        "backend.tasks.lightweight_research_tasks",  # Memory optimized tasks
        "backend.tasks.posting_tasks",
        "backend.tasks.autonomous_scheduler",
        "backend.tasks.webhook_tasks",  # Webhook processing
        "backend.tasks.token_health_tasks",  # Token refresh and health
        "backend.tasks.x_polling_tasks",  # X mentions polling
        "backend.tasks.webhook_watchdog_tasks",  # GA Checklist: DLQ watchdog
        "backend.tasks.subscription_cleanup_tasks",  # P1-5c: Subscription cleanup jobs
        "backend.tasks.ftc_compliance_tasks",  # P1-10b: FTC compliance disclosures
        "backend.tasks.data_retention_tasks",  # P0-4b: Data retention policy enforcement
        "backend.tasks.key_rotation_tasks",  # P0-4c: Encryption key rotation and automation
        # Disabled heavy tasks to prevent memory issues
        # "backend.tasks.content_tasks",  # CrewAI - uses 500MB+
        # "backend.tasks.research_tasks",  # CrewAI - uses 500MB+ 
        # "backend.tasks.optimization_tasks",  # May be heavy
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=1800,  # 30 minutes
    task_track_started=True,
    task_time_limit=10 * 60,  # 10 minutes
    task_soft_time_limit=8 * 60,  # 8 minutes
    
    # PRODUCTION RESILIENCE: Multi-process concurrent execution
    worker_concurrency=int(os.getenv('CELERY_WORKER_CONCURRENCY', '4')),  # 4 concurrent workers
    worker_prefetch_multiplier=int(os.getenv('CELERY_WORKER_PREFETCH', '4')),  # Prefetch 4 tasks
    worker_max_tasks_per_child=int(os.getenv('CELERY_MAX_TASKS_PER_CHILD', '100')),  # Restart after 100 tasks
    worker_max_memory_per_child=int(os.getenv('CELERY_MAX_MEMORY_PER_CHILD', '500000')),  # 500MB limit
    
    # Use prefork for better performance and isolation
    worker_pool=os.getenv('CELERY_WORKER_POOL', 'prefork'),  # Use process pool for isolation
    worker_disable_rate_limits=False,  # Enable rate limiting
    worker_pool_restarts=True,
    
    # Task acknowledgment configuration for reliability
    task_acks_late=True,  # Acknowledge tasks only after completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker dies
    
    # Broker transport options for durable queues
    broker_transport_options={
        'visibility_timeout': 3600,  # 1 hour visibility timeout
        'fanout_prefix': True,
        'fanout_patterns': True,
        'priority_steps': list(range(10)),  # Support priority levels 0-9
    },
    
    # Queue routing and durability
    task_routes={
        # Default queue for general tasks
        'backend.tasks.posting_tasks.*': {'queue': 'posting', 'priority': 8},
        'backend.tasks.webhook_tasks.*': {'queue': 'webhooks', 'priority': 9},
        'backend.tasks.token_health_tasks.*': {'queue': 'token_health', 'priority': 7},
        'backend.tasks.x_polling_tasks.*': {'queue': 'x_polling', 'priority': 6},
        'backend.tasks.webhook_watchdog_tasks.*': {'queue': 'webhook_watchdog', 'priority': 9},
        'backend.tasks.lightweight_research_tasks.*': {'queue': 'research', 'priority': 5},
        'backend.tasks.autonomous_scheduler.*': {'queue': 'autonomous', 'priority': 4},
        'backend.tasks.subscription_cleanup_tasks.*': {'queue': 'subscription_cleanup', 'priority': 6},
        'backend.tasks.ftc_compliance_tasks.*': {'queue': 'ftc_compliance', 'priority': 8},
        'backend.tasks.data_retention_tasks.*': {'queue': 'data_retention', 'priority': 5},
        'backend.tasks.key_rotation_tasks.*': {'queue': 'key_rotation', 'priority': 9},
    },
    
    # Dead Letter Queue configuration
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    
    # Queue durability settings
    task_create_missing_queues=True,
    worker_direct=True,  # Direct acknowledgments
)

# Production autonomous schedule for fully automated operation
# Configure task queues with appropriate routing and durability
celery_app.conf.task_queues = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
        'durable': True,
        'auto_delete': False,
    },
    'posting': {
        'exchange': 'posting',
        'routing_key': 'posting',
        'durable': True,
        'auto_delete': False,
    },
    'webhooks': {
        'exchange': 'webhooks',
        'routing_key': 'webhooks',
        'durable': True,
        'auto_delete': False,
    },
    'token_health': {
        'exchange': 'token_health',
        'routing_key': 'token_health',
        'durable': True,
        'auto_delete': False,
    },
    'x_polling': {
        'exchange': 'x_polling',
        'routing_key': 'x_polling',
        'durable': True,
        'auto_delete': False,
    },
    'webhook_watchdog': {
        'exchange': 'webhook_watchdog',
        'routing_key': 'webhook_watchdog',
        'durable': True,
        'auto_delete': False,
    },
    'research': {
        'exchange': 'research',
        'routing_key': 'research',
        'durable': True,
        'auto_delete': False,
    },
    'autonomous': {
        'exchange': 'autonomous',
        'routing_key': 'autonomous',
        'durable': True,
        'auto_delete': False,
    },
    'subscription_cleanup': {
        'exchange': 'subscription_cleanup',
        'routing_key': 'subscription_cleanup',
        'durable': True,
        'auto_delete': False,
    },
    'ftc_compliance': {
        'exchange': 'ftc_compliance',
        'routing_key': 'ftc_compliance',
        'durable': True,
        'auto_delete': False,
    },
    'data_retention': {
        'exchange': 'data_retention',
        'routing_key': 'data_retention',
        'durable': True,
        'auto_delete': False,
    },
    'key_rotation': {
        'exchange': 'key_rotation',
        'routing_key': 'key_rotation',
        'durable': True,
        'auto_delete': False,
    },
}

# Production autonomous schedule for fully automated operation
celery_app.conf.beat_schedule = {
    # Daily autonomous content generation at 6 AM UTC
    'autonomous-daily-content': {
        'task': 'autonomous_daily_content_generation',
        'schedule': 60.0 * 60.0 * 24,  # Daily
        'options': {'queue': 'autonomous'},
    },
    
    # Weekly performance report on Sundays at 8 AM UTC  
    'autonomous-weekly-report': {
        'task': 'autonomous_weekly_report',
        'schedule': 60.0 * 60.0 * 24 * 7,  # Weekly
        'options': {'queue': 'reports'},
    },
    
    # Nightly metrics collection at 2 AM UTC
    'autonomous-metrics-collection': {
        'task': 'autonomous_metrics_collection',
        'schedule': 60.0 * 60.0 * 24,  # Daily
        'options': {'queue': 'metrics'},
    },
    
    # Process scheduled content every 15 minutes
    'autonomous-content-posting': {
        'task': 'autonomous_content_posting',
        'schedule': 60.0 * 15,  # Every 15 minutes
        'options': {'queue': 'posting'},
    },
    
    # Lightweight research tasks (memory optimized)
    'lightweight-research': {
        'task': 'backend.tasks.lightweight_research_tasks.lightweight_daily_research',
        'schedule': 60.0 * 60.0 * 8,  # Every 8 hours
        'options': {'queue': 'research', 'expires': 300},  # 5 min expiry
    },
    
    # Partner OAuth token health audit - daily at 2 AM UTC
    'token-health-audit': {
        'task': 'backend.tasks.token_health_tasks.audit_all_tokens',
        'schedule': 60.0 * 60.0 * 24,  # Daily
        'options': {'queue': 'token_health', 'expires': 1800},  # 30 min expiry
    },
    
    # X mentions polling - every 15 minutes
    'x-mentions-polling': {
        'task': 'backend.tasks.x_polling_tasks.poll_all_x_mentions',
        'schedule': 60.0 * 15,  # Every 15 minutes
        'options': {'queue': 'x_polling', 'expires': 600},  # 10 min expiry
    },
    
    # Cleanup old audit logs - weekly on Sundays at 3 AM UTC
    'cleanup-old-audits': {
        'task': 'backend.tasks.token_health_tasks.cleanup_old_audits',
        'schedule': 60.0 * 60.0 * 24 * 7,  # Weekly
        'options': {'queue': 'token_health', 'expires': 3600},  # 1 hour expiry
    },
    
    # GA Checklist: DLQ watchdog scan - every hour
    'dlq-watchdog-scan': {
        'task': 'backend.tasks.webhook_watchdog_tasks.scan_dlq_watchdog',
        'schedule': 60.0 * 60.0,  # Every hour
        'options': {'queue': 'webhook_watchdog', 'expires': 1800},  # 30 min expiry
    },
    
    # P1-5c: Subscription cleanup jobs
    # Daily subscription maintenance - comprehensive cleanup at 1 AM UTC
    'daily-subscription-maintenance': {
        'task': 'backend.tasks.subscription_cleanup_tasks.daily_subscription_maintenance',
        'schedule': 60.0 * 60.0 * 24,  # Daily
        'options': {'queue': 'subscription_cleanup', 'expires': 7200},  # 2 hour expiry
    },
    
    # Expired trial cleanup - every 6 hours
    'cleanup-expired-trials': {
        'task': 'backend.tasks.subscription_cleanup_tasks.cleanup_expired_trials',
        'schedule': 60.0 * 60.0 * 6,  # Every 6 hours
        'options': {'queue': 'subscription_cleanup', 'expires': 3600},  # 1 hour expiry
    },
    
    # Stripe subscription sync - every 4 hours
    'stripe-subscription-sync': {
        'task': 'backend.tasks.subscription_cleanup_tasks.sync_stripe_subscription_status',
        'schedule': 60.0 * 60.0 * 4,  # Every 4 hours
        'options': {'queue': 'subscription_cleanup', 'expires': 1800},  # 30 min expiry
    },
    
    # Overdue subscription handling - every 12 hours
    'handle-overdue-subscriptions': {
        'task': 'backend.tasks.subscription_cleanup_tasks.handle_overdue_subscriptions',
        'schedule': 60.0 * 60.0 * 12,  # Every 12 hours
        'options': {'queue': 'subscription_cleanup', 'expires': 3600},  # 1 hour expiry
    },
    
    # P1-10b: FTC-compliant trial and renewal disclosures
    # Daily FTC compliance checks - runs all consumer protection notifications at 10 AM UTC
    'daily-ftc-compliance': {
        'task': 'backend.tasks.ftc_compliance_tasks.daily_ftc_compliance_checks',
        'schedule': 60.0 * 60.0 * 24,  # Daily
        'options': {'queue': 'ftc_compliance', 'expires': 7200},  # 2 hour expiry
    },
    
    # Trial reminder notifications - every 6 hours for coverage
    'ftc-trial-reminders': {
        'task': 'backend.tasks.ftc_compliance_tasks.send_ftc_trial_reminders',
        'schedule': 60.0 * 60.0 * 6,  # Every 6 hours
        'options': {'queue': 'ftc_compliance', 'expires': 3600},  # 1 hour expiry
    },
    
    # Renewal notice notifications - every 6 hours for coverage
    'ftc-renewal-notices': {
        'task': 'backend.tasks.ftc_compliance_tasks.send_ftc_renewal_notices',
        'schedule': 60.0 * 60.0 * 6,  # Every 6 hours
        'options': {'queue': 'ftc_compliance', 'expires': 3600},  # 1 hour expiry
    },
    
    # P0-4b: Data retention policy enforcement
    # Daily data retention cleanup - cache, notifications, system logs at 3 AM UTC
    'daily-data-retention-cleanup': {
        'task': 'backend.tasks.data_retention_tasks.daily_data_retention_cleanup',
        'schedule': 60.0 * 60.0 * 24,  # Daily
        'options': {'queue': 'data_retention', 'expires': 7200},  # 2 hour expiry
    },
    
    # Weekly data retention cleanup - user content, metrics, workflows on Sundays at 4 AM UTC
    'weekly-data-retention-cleanup': {
        'task': 'backend.tasks.data_retention_tasks.weekly_data_retention_cleanup',
        'schedule': 60.0 * 60.0 * 24 * 7,  # Weekly
        'options': {'queue': 'data_retention', 'expires': 10800},  # 3 hour expiry
    },
    
    # Monthly data retention cleanup - research data, security data on 1st of month at 5 AM UTC
    'monthly-data-retention-cleanup': {
        'task': 'backend.tasks.data_retention_tasks.monthly_data_retention_cleanup',
        'schedule': 60.0 * 60.0 * 24 * 30,  # Monthly (approximate)
        'options': {'queue': 'data_retention', 'expires': 14400},  # 4 hour expiry
    },
    
    # Data retention health report - weekly on Mondays at 9 AM UTC for compliance monitoring
    'data-retention-health-report': {
        'task': 'backend.tasks.data_retention_tasks.generate_data_retention_health_report',
        'schedule': 60.0 * 60.0 * 24 * 7,  # Weekly
        'options': {'queue': 'data_retention', 'expires': 3600},  # 1 hour expiry
    },
    
    # P0-4c: Encryption key rotation schedule and automation
    # Key rotation health check - every 6 hours for continuous security monitoring
    'key-rotation-health-check': {
        'task': 'backend.tasks.key_rotation_tasks.key_rotation_health_check',
        'schedule': 60.0 * 60.0 * 6,  # Every 6 hours
        'options': {'queue': 'key_rotation', 'expires': 1800},  # 30 min expiry
    },
    
    # Automated key rotation check - daily at 1 AM UTC for policy compliance
    'automated-key-rotation-check': {
        'task': 'backend.tasks.key_rotation_tasks.automated_key_rotation_check',
        'schedule': 60.0 * 60.0 * 24,  # Daily
        'options': {'queue': 'key_rotation', 'expires': 7200},  # 2 hour expiry
    },
    
    # Execute scheduled key rotations - every 4 hours during maintenance windows
    'execute-scheduled-key-rotations': {
        'task': 'backend.tasks.key_rotation_tasks.execute_scheduled_key_rotations',
        'schedule': 60.0 * 60.0 * 4,  # Every 4 hours
        'options': {'queue': 'key_rotation', 'expires': 3600},  # 1 hour expiry
    },
    
    # Key rotation cleanup - weekly on Sundays at 6 AM UTC for security hygiene
    'key-rotation-cleanup': {
        'task': 'backend.tasks.key_rotation_tasks.key_rotation_cleanup',
        'schedule': 60.0 * 60.0 * 24 * 7,  # Weekly
        'options': {'queue': 'key_rotation', 'expires': 3600},  # 1 hour expiry
    },
    
    # Key rotation compliance report - monthly on 1st at 10 AM UTC
    'key-rotation-compliance-report': {
        'task': 'backend.tasks.key_rotation_tasks.generate_key_rotation_compliance_report',
        'schedule': 60.0 * 60.0 * 24 * 30,  # Monthly (approximate)
        'options': {'queue': 'key_rotation', 'expires': 7200},  # 2 hour expiry
    },
    
    # Key usage monitoring - every 8 hours for anomaly detection
    'key-usage-monitoring': {
        'task': 'backend.tasks.key_rotation_tasks.key_usage_monitoring_task',
        'schedule': 60.0 * 60.0 * 8,  # Every 8 hours
        'options': {'queue': 'key_rotation', 'expires': 3600},  # 1 hour expiry
    },
}