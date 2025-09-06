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
}