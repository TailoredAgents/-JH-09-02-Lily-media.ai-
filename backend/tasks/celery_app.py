# Import warning suppression FIRST before any other imports
from backend.core.suppress_warnings import suppress_third_party_warnings
suppress_third_party_warnings()

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
    result_expires=1800,  # Reduced to 30 minutes
    task_track_started=True,
    task_time_limit=5 * 60,  # 5 minutes (reduced from 10)
    task_soft_time_limit=4 * 60,  # 4 minutes (reduced from 8)
    
    # MEMORY OPTIMIZATION: Force single-process, serial execution
    worker_concurrency=1,  # Only 1 process at a time
    worker_prefetch_multiplier=1,  # Only 1 task prefetched
    worker_max_tasks_per_child=5,  # Restart after 5 tasks (was 10)
    worker_max_memory_per_child=200000,  # 200MB limit (was 300MB)
    
    # Use threads instead of processes to reduce memory overhead
    worker_pool='threads',  # Use thread pool instead of process pool
    worker_disable_rate_limits=True,
    worker_pool_restarts=True,
)

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
        'task': 'scan_dlq_watchdog',
        'schedule': 60.0 * 60.0,  # Every hour
        'options': {'queue': 'webhook_watchdog', 'expires': 1800},  # 30 min expiry
    },
}