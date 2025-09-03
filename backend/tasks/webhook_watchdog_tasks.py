"""
Webhook Watchdog Celery Tasks
GA Checklist requirement: Retry/DLQ watchdog logging
"""
import logging
from celery import current_task
from backend.tasks.celery_app import celery_app
from backend.tasks.webhook_watchdog import get_webhook_watchdog

logger = logging.getLogger(__name__)


@celery_app.task(name="scan_dlq_watchdog", bind=True)
def scan_dlq_watchdog(self):
    """
    Scan Dead Letter Queue for failed webhook processing tasks
    
    GA Checklist: Retry/DLQ watchdog logging in place
    
    This task:
    - Scans the DLQ for failed webhook events
    - Attempts retries according to configured policy
    - Logs alerts for permanently failed entries
    - Manages entry lifecycle and cleanup
    
    Returns:
        Dict with scan results and actions taken
    """
    try:
        task_id = current_task.request.id if current_task else "manual"
        logger.info(f"Starting DLQ watchdog scan (task_id: {task_id})")
        
        # Get watchdog instance
        watchdog = get_webhook_watchdog()
        
        # Perform DLQ scan
        import asyncio
        scan_results = asyncio.run(watchdog.scan_dlq())
        
        # Log summary
        logger.info(f"DLQ watchdog scan completed: {scan_results.get('actions_taken', {})}")
        
        # Log any alerts
        alerts = scan_results.get('alerts', [])
        for alert in alerts:
            if alert.get('severity') == 'error':
                logger.error(f"DLQ Alert: {alert.get('message')}")
            else:
                logger.warning(f"DLQ Alert: {alert.get('message')}")
        
        return {
            "status": "completed",
            "task_id": task_id,
            "scan_results": scan_results,
            "total_alerts": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"DLQ watchdog scan failed: {e}")
        return {
            "status": "failed", 
            "task_id": task_id if 'task_id' in locals() else "unknown",
            "error": str(e)
        }


@celery_app.task(name="process_dlq_entry_retry", bind=True)
def process_dlq_entry_retry(self, entry_id: str):
    """
    Retry processing a specific DLQ entry
    
    Args:
        entry_id: ID of the DLQ entry to retry
        
    Returns:
        Dict with retry results
    """
    try:
        task_id = current_task.request.id if current_task else "manual"
        logger.info(f"Retrying DLQ entry {entry_id} (task_id: {task_id})")
        
        # Get watchdog instance
        watchdog = get_webhook_watchdog()
        
        # Process the specific entry
        import asyncio
        
        # Get the entry first
        entries = asyncio.run(watchdog._get_dlq_entries())
        target_entry = None
        
        for entry in entries:
            if entry.id == entry_id:
                target_entry = entry
                break
        
        if not target_entry:
            logger.warning(f"DLQ entry {entry_id} not found")
            return {
                "status": "not_found",
                "entry_id": entry_id,
                "task_id": task_id
            }
        
        # Process the entry
        result = asyncio.run(watchdog._process_dlq_entry(target_entry))
        
        logger.info(f"DLQ entry {entry_id} retry result: {result}")
        
        return {
            "status": "completed",
            "entry_id": entry_id,
            "task_id": task_id,
            "retry_result": result
        }
        
    except Exception as e:
        logger.error(f"DLQ entry retry failed for {entry_id}: {e}")
        return {
            "status": "failed",
            "entry_id": entry_id if 'entry_id' in locals() else "unknown",
            "task_id": task_id if 'task_id' in locals() else "unknown",
            "error": str(e)
        }


@celery_app.task(name="cleanup_old_dlq_entries", bind=True)
def cleanup_old_dlq_entries(self):
    """
    Clean up old DLQ entries that have expired
    
    Returns:
        Dict with cleanup results
    """
    try:
        task_id = current_task.request.id if current_task else "manual"
        logger.info(f"Starting DLQ cleanup (task_id: {task_id})")
        
        # Get watchdog instance
        watchdog = get_webhook_watchdog()
        
        # Cleanup expired entries
        import asyncio
        cleanup_count = asyncio.run(watchdog._cleanup_expired_entries())
        
        logger.info(f"DLQ cleanup completed: removed {cleanup_count} expired entries")
        
        return {
            "status": "completed",
            "task_id": task_id,
            "entries_removed": cleanup_count
        }
        
    except Exception as e:
        logger.error(f"DLQ cleanup failed: {e}")
        return {
            "status": "failed",
            "task_id": task_id if 'task_id' in locals() else "unknown", 
            "error": str(e)
        }