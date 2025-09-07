"""
Celery tasks for webhook processing with enhanced reliability
Handles asynchronous processing of webhook events with retries, DLQ, and idempotency
Enhanced with P0-11c reliability improvements
"""
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from celery import Celery
from celery.exceptions import Retry

from backend.core.config import get_settings
from backend.services.meta_webhook_service import get_meta_webhook_service
from backend.core.dlq import handle_task_failure, get_dlq_manager, TaskFailureReason
from backend.services.webhook_reliability_service import (
    get_webhook_reliability_service, 
    WebhookDeliveryStatus,
    WebhookProcessingResult
)

logger = logging.getLogger(__name__)

# Initialize Celery app (this should match your main Celery configuration)
settings = get_settings()
celery_app = Celery('webhook_tasks')

# Configure Celery for webhook processing with reliability enhancements
celery_app.conf.update(
    # Task routing
    task_routes={
        'backend.tasks.webhook_tasks.process_meta_event': {'queue': 'webhook_processing'},
        'backend.tasks.webhook_tasks.watchdog_scan': {'queue': 'webhook_watchdog'},
        'backend.tasks.webhook_tasks.webhook_recovery_scan': {'queue': 'webhook_recovery'},
        'backend.tasks.webhook_tasks.webhook_cleanup_task': {'queue': 'webhook_maintenance'},
    },
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=5,
    
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    
    # Result backend for task monitoring
    result_expires=3600,  # 1 hour
)

# Dead Letter Queue configuration
DLQ_MAX_RETRIES = 5
DLQ_RETRY_DELAYS = [60, 300, 900, 3600, 14400]  # 1m, 5m, 15m, 1h, 4h


@celery_app.task(
    bind=True,
    name='backend.tasks.webhook_tasks.process_meta_event',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
    reject_on_worker_lost=True
)
def process_meta_event(self, entry: Dict[str, Any], event_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single Meta webhook entry with enhanced reliability
    
    Args:
        self: Celery task instance (for retries)
        entry: Webhook entry data from Meta
        event_info: Basic event information for logging
        
    Returns:
        Processing result with status and details
    """
    try:
        task_id = self.request.id
        start_time = datetime.now(timezone.utc)
        
        logger.info(f"Processing Meta webhook entry: task_id={task_id}, entry_id={event_info.get('entry_id')}")
        
        # Get services
        webhook_service = get_meta_webhook_service()
        reliability_service = get_webhook_reliability_service()
        
        # Generate idempotency key for duplicate detection
        idempotency_key = reliability_service.generate_idempotency_key(
            platform="meta",
            event_data=entry,
            signature=event_info.get('signature')
        )
        
        # Check for duplicate processing
        is_duplicate, previous_result = asyncio.run(
            reliability_service.check_idempotency(
                idempotency_key=idempotency_key,
                platform="meta",
                event_type=event_info.get('event_type', 'unknown'),
                organization_id=entry.get('organization_id'),
                user_id=entry.get('user_id')
            )
        )
        
        if is_duplicate:
            logger.info(
                f"Duplicate Meta webhook detected, skipping: task_id={task_id}, "
                f"idempotency_key={idempotency_key[:12]}..., previous_result={previous_result}"
            )
            
            return {
                "status": "skipped",
                "task_id": task_id,
                "entry_id": event_info.get('entry_id'),
                "processing_result": "idempotent_skip",
                "idempotency_key": idempotency_key[:12] + "...",
                "previous_processing": previous_result.value if previous_result else None
            }
        
        # Track delivery attempt start
        webhook_id = f"meta_{entry.get('id', task_id)}_{int(start_time.timestamp())}"
        
        asyncio.run(
            reliability_service.track_delivery_attempt(
                webhook_id=webhook_id,
                platform="meta",
                event_type=event_info.get('event_type', 'unknown'),
                delivery_status=WebhookDeliveryStatus.PROCESSING,
                attempt_number=self.request.retries + 1,
                organization_id=entry.get('organization_id'),
                user_id=entry.get('user_id')
            )
        )
        
        # Normalize the entry
        normalized_entry = webhook_service.normalize_webhook_entry(entry)
        
        # Process different types of events
        result = asyncio.run(_process_normalized_entry(normalized_entry, event_info))
        
        # Calculate processing time
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        processing_time_ms = int(processing_time * 1000)
        
        # Determine processing result
        processing_result = WebhookProcessingResult.SUCCESS
        if result.get('error'):
            processing_result = WebhookProcessingResult.TEMPORARY_FAILURE
        
        # Record successful processing
        asyncio.run(
            reliability_service.record_processing_result(
                idempotency_key=idempotency_key,
                platform="meta",
                event_type=event_info.get('event_type', 'unknown'),
                processing_result=processing_result,
                processing_time_ms=processing_time_ms,
                event_summary={
                    'entry_id': event_info.get('entry_id'),
                    'events_processed': result.get('events_processed', 0),
                    'entry_type': result.get('entry_type', 'unknown')
                },
                organization_id=entry.get('organization_id'),
                user_id=entry.get('user_id'),
                webhook_id=webhook_id
            )
        )
        
        # Track successful delivery
        asyncio.run(
            reliability_service.track_delivery_attempt(
                webhook_id=webhook_id,
                platform="meta",
                event_type=event_info.get('event_type', 'unknown'),
                delivery_status=WebhookDeliveryStatus.DELIVERED,
                attempt_number=self.request.retries + 1,
                response_time=processing_time,
                status_code=200,
                organization_id=entry.get('organization_id'),
                user_id=entry.get('user_id')
            )
        )
        
        # Log successful processing
        logger.info(
            f"Successfully processed Meta webhook entry: task_id={task_id}, "
            f"entry_id={event_info.get('entry_id')}, "
            f"processing_time={processing_time:.2f}s, "
            f"events_processed={result.get('events_processed', 0)}, "
            f"idempotency_key={idempotency_key[:12]}..."
        )
        
        return {
            "status": "success",
            "task_id": task_id,
            "entry_id": event_info.get('entry_id'),
            "processing_time": processing_time,
            "events_processed": result.get('events_processed', 0),
            "details": result
        }
        
    except Exception as e:
        logger.error(f"Error processing Meta webhook entry: {e}")
        
        # Get reliability service for failure tracking
        try:
            reliability_service = get_webhook_reliability_service()
            webhook_id = f"meta_{entry.get('id', task_id)}_{int(start_time.timestamp())}"
            
            # Track failed delivery attempt
            asyncio.run(
                reliability_service.track_delivery_attempt(
                    webhook_id=webhook_id,
                    platform="meta",
                    event_type=event_info.get('event_type', 'unknown'),
                    delivery_status=WebhookDeliveryStatus.FAILED,
                    attempt_number=self.request.retries + 1,
                    error_message=str(e),
                    organization_id=entry.get('organization_id'),
                    user_id=entry.get('user_id')
                )
            )
            
            # Generate idempotency key for failure recording
            idempotency_key = reliability_service.generate_idempotency_key(
                platform="meta",
                event_data=entry,
                signature=event_info.get('signature')
            )
            
            # Record processing failure
            processing_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            # Determine processing result based on error type
            processing_result = WebhookProcessingResult.TEMPORARY_FAILURE
            if not _is_retryable_error(e):
                processing_result = WebhookProcessingResult.PERMANENT_FAILURE
            elif 'auth' in str(e).lower():
                processing_result = WebhookProcessingResult.AUTH_FAILURE
            elif 'rate' in str(e).lower():
                processing_result = WebhookProcessingResult.RATE_LIMITED
            
            asyncio.run(
                reliability_service.record_processing_result(
                    idempotency_key=idempotency_key,
                    platform="meta",
                    event_type=event_info.get('event_type', 'unknown'),
                    processing_result=processing_result,
                    processing_time_ms=processing_time_ms,
                    event_summary={
                        'entry_id': event_info.get('entry_id'),
                        'error': str(e)[:200],  # Truncate error message
                        'retry_count': self.request.retries
                    },
                    organization_id=entry.get('organization_id'),
                    user_id=entry.get('user_id'),
                    webhook_id=webhook_id
                )
            )
            
        except Exception as reliability_error:
            logger.error(f"Failed to track webhook reliability metrics: {reliability_error}")
        
        # Determine if this is a retryable error
        retryable = _is_retryable_error(e)
        
        if retryable and self.request.retries < DLQ_MAX_RETRIES:
            # Calculate retry delay
            retry_count = self.request.retries
            retry_delay = DLQ_RETRY_DELAYS[min(retry_count, len(DLQ_RETRY_DELAYS) - 1)]
            
            logger.warning(
                f"Retrying Meta webhook processing: task_id={self.request.id}, "
                f"retry_count={retry_count}, delay={retry_delay}s, error={e}"
            )
            
            # Retry with exponential backoff
            raise self.retry(countdown=retry_delay, exc=e)
        else:
            # Send to Dead Letter Queue using our comprehensive DLQ system
            handle_task_failure(
                task_id=self.request.id,
                task_name="process_meta_event",
                queue_name=getattr(self.request, 'delivery_info', {}).get('routing_key', 'webhook_processing'),
                error=e,
                traceback_str="",  # Could get full traceback if needed
                retry_count=self.request.retries,
                organization_id=entry.get('organization_id'),  # Extract from entry if available
                user_id=entry.get('user_id'),  # Extract from entry if available
                task_args=(entry, event_info),
                task_kwargs={}
            )
            
            logger.error(
                f"Meta webhook processing failed permanently: task_id={self.request.id}, "
                f"retries={self.request.retries}, error={e}, sent_to_dlq=True"
            )
            
            return {
                "status": "failed",
                "task_id": self.request.id,
                "entry_id": event_info.get('entry_id'),
                "error": str(e),
                "retries": self.request.retries,
                "sent_to_dlq": True,
                "webhook_id": webhook_id if 'webhook_id' in locals() else None
            }


async def _process_normalized_entry(entry: Dict[str, Any], event_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a normalized webhook entry
    
    Args:
        entry: Normalized webhook entry
        event_info: Event information for logging
        
    Returns:
        Processing result
    """
    events_processed = 0
    results = []
    
    try:
        # Process changes (Page events like posts, comments, etc.)
        for change in entry.get("changes", []):
            result = await _process_page_change(change, entry, event_info)
            results.append(result)
            if result.get("processed", False):
                events_processed += 1
        
        # Process messaging events
        for message in entry.get("messaging", []):
            result = await _process_messaging_event(message, entry, event_info)
            results.append(result)
            if result.get("processed", False):
                events_processed += 1
        
        return {
            "events_processed": events_processed,
            "results": results,
            "entry_type": entry.get("object_type", "unknown")
        }
        
    except Exception as e:
        logger.error(f"Error in normalized entry processing: {e}")
        return {
            "events_processed": 0,
            "results": [],
            "error": str(e)
        }


async def _process_page_change(change: Dict[str, Any], entry: Dict[str, Any], event_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a Page change event (feed, mentions, etc.)
    
    Args:
        change: Change data
        entry: Full entry data
        event_info: Event information
        
    Returns:
        Processing result
    """
    try:
        field = change.get("field")
        value = change.get("value", {})
        
        logger.info(f"Processing Page change: field={field}, entry_id={entry.get('entry_id')}")
        
        # Route to appropriate processors based on field type
        if field == "feed":
            return await _process_feed_event(value, entry, event_info)
        elif field == "mentions":
            return await _process_mention_event(value, entry, event_info)
        elif field == "messaging":
            return await _process_messaging_change(value, entry, event_info)
        else:
            logger.info(f"Unhandled Page change field: {field}")
            return {"processed": False, "reason": "unhandled_field", "field": field}
            
    except Exception as e:
        logger.error(f"Error processing Page change: {e}")
        return {"processed": False, "error": str(e)}


async def _process_messaging_event(message: Dict[str, Any], entry: Dict[str, Any], event_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a messaging event
    
    Args:
        message: Message data
        entry: Full entry data
        event_info: Event information
        
    Returns:
        Processing result
    """
    try:
        sender_id = message.get("sender")
        recipient_id = message.get("recipient")
        message_text = message.get("message", {}).get("text")
        
        logger.info(f"Processing messaging event: sender={sender_id}, recipient={recipient_id}")
        
        # TODO: Route to your existing reply/engagement pipelines
        # For now, just log the event
        
        return {
            "processed": True,
            "event_type": "messaging",
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "has_text": bool(message_text)
        }
        
    except Exception as e:
        logger.error(f"Error processing messaging event: {e}")
        return {"processed": False, "error": str(e)}


async def _process_feed_event(value: Dict[str, Any], entry: Dict[str, Any], event_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a feed event (posts, comments, etc.)
    
    Args:
        value: Feed event data
        entry: Full entry data
        event_info: Event information
        
    Returns:
        Processing result
    """
    try:
        verb = value.get("verb")  # add, edit, remove
        item = value.get("item")  # post, comment, etc.
        
        logger.info(f"Processing feed event: verb={verb}, item={item}")
        
        # TODO: Route to your existing content/performance pipelines
        # For now, just log the event
        
        return {
            "processed": True,
            "event_type": "feed",
            "verb": verb,
            "item": item,
            "post_id": value.get("post_id"),
            "comment_id": value.get("comment_id")
        }
        
    except Exception as e:
        logger.error(f"Error processing feed event: {e}")
        return {"processed": False, "error": str(e)}


async def _process_mention_event(value: Dict[str, Any], entry: Dict[str, Any], event_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a mention event
    
    Args:
        value: Mention event data
        entry: Full entry data
        event_info: Event information
        
    Returns:
        Processing result
    """
    try:
        logger.info(f"Processing mention event: entry_id={entry.get('entry_id')}")
        
        # TODO: Route to your existing reply/engagement pipelines
        # For now, just log the event
        
        return {
            "processed": True,
            "event_type": "mention",
            "mention_data": value
        }
        
    except Exception as e:
        logger.error(f"Error processing mention event: {e}")
        return {"processed": False, "error": str(e)}


async def _process_messaging_change(value: Dict[str, Any], entry: Dict[str, Any], event_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a messaging change event
    
    Args:
        value: Messaging change data
        entry: Full entry data
        event_info: Event information
        
    Returns:
        Processing result
    """
    try:
        logger.info(f"Processing messaging change: entry_id={entry.get('entry_id')}")
        
        # TODO: Route to your existing messaging pipelines
        # For now, just log the event
        
        return {
            "processed": True,
            "event_type": "messaging_change",
            "change_data": value
        }
        
    except Exception as e:
        logger.error(f"Error processing messaging change: {e}")
        return {"processed": False, "error": str(e)}


def _is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable
    
    Args:
        error: Exception that occurred
        
    Returns:
        True if error should be retried, False otherwise
    """
    # Network errors, temporary service unavailability, rate limits
    retryable_errors = [
        "ConnectionError",
        "TimeoutError", 
        "HTTPError",
        "TemporaryFailure",
        "RateLimitError"
    ]
    
    error_name = type(error).__name__
    error_message = str(error).lower()
    
    # Check error type
    if error_name in retryable_errors:
        return True
    
    # Check error message for retryable conditions
    retryable_messages = [
        "timeout",
        "connection",
        "rate limit",
        "service unavailable",
        "temporary",
        "502",
        "503",
        "504"
    ]
    
    for msg in retryable_messages:
        if msg in error_message:
            return True
    
    return False


async def _send_webhook_to_dlq(
    entry: Dict[str, Any], 
    event_info: Dict[str, Any], 
    error: str, 
    retries: int,
    task_id: str = None,
    organization_id: int = None,
    user_id: int = None
) -> bool:
    """
    Send failed webhook event to Dead Letter Queue using our comprehensive DLQ system
    
    Args:
        entry: Original webhook entry
        event_info: Event information
        error: Error message
        retries: Number of retries attempted
        task_id: Celery task ID
        organization_id: Organization ID for tenant isolation
        user_id: User ID if applicable
        
    Returns:
        True if successfully sent to DLQ, False otherwise
    """
    try:
        # Determine failure reason based on error
        if 'rate limit' in error.lower():
            failure_reason = TaskFailureReason.RATE_LIMIT
        elif 'timeout' in error.lower():
            failure_reason = TaskFailureReason.TIMEOUT
        elif 'auth' in error.lower() or 'unauthorized' in error.lower():
            failure_reason = TaskFailureReason.AUTH_ERROR
        elif 'network' in error.lower() or 'connection' in error.lower():
            failure_reason = TaskFailureReason.NETWORK_ERROR
        else:
            failure_reason = TaskFailureReason.EXTERNAL_API_ERROR
        
        # Use our comprehensive DLQ manager
        with get_dlq_manager() as dlq:
            dlq.record_task_failure(
                task_id=task_id or f"webhook_{int(datetime.now(timezone.utc).timestamp())}",
                task_name="process_meta_event",
                queue_name="webhook_processing",
                failure_reason=failure_reason,
                error_message=error,
                args=(entry, event_info),
                kwargs={},
                organization_id=organization_id,
                user_id=user_id,
                retry_count=retries,
                metadata={
                    "platform": "meta",
                    "event_type": event_info.get("event_type"),
                    "entry_id": event_info.get("entry_id"),
                    "failed_at": datetime.now(timezone.utc).isoformat()
                }
            )
        
        logger.info(f"Successfully sent webhook event to DLQ: task_id={task_id}, retries={retries}")
        return True
        
    except Exception as dlq_error:
        logger.error(f"Failed to send webhook to DLQ: {dlq_error}")
        # Still log the original failure even if DLQ fails
        logger.error(f"Original webhook failure: {json.dumps({
            'entry': entry,
            'event_info': event_info,
            'error': error,
            'retries': retries
        }, indent=2)}")
        return False


@celery_app.task(
    bind=True,
    name='backend.tasks.webhook_tasks.watchdog_scan',
    acks_late=True
)
def watchdog_scan(self) -> Dict[str, Any]:
    """
    Scan Dead Letter Queue and retry/alert on failures
    
    Returns:
        Watchdog scan results
    """
    try:
        logger.info("Starting webhook watchdog scan")
        
        scan_time = datetime.now(timezone.utc)
        
        # Use our comprehensive DLQ system to scan for failed webhooks
        with get_dlq_manager() as dlq:
            # Get webhook-related failed tasks
            failed_webhooks = dlq.get_failed_tasks(
                queue_name="webhook_processing",
                requires_manual_review=True,
                limit=50
            )
            
            # Get recent failures (last 24 hours)
            recent_failures = dlq.get_failed_tasks(
                queue_name="webhook_processing",
                limit=100
            )
            
            # Get DLQ health statistics
            health_stats = dlq.get_queue_health_stats()
            
            entries_requiring_review = len(failed_webhooks)
            recent_failure_count = len([f for f in recent_failures if 
                (datetime.now(timezone.utc) - f.moved_to_dlq_at).days < 1])
            
            # Log critical webhook failures
            if entries_requiring_review > 0:
                logger.warning(f"Found {entries_requiring_review} webhook entries requiring manual review")
                
                # Alert if too many recent failures
                if recent_failure_count > 10:
                    logger.error(f"ALERT: {recent_failure_count} webhook failures in last 24 hours")
            
            # TODO: Add alerting integration (email, Slack, PagerDuty, etc.)
            # For now, log the critical issues
        
        result = {
            "scan_time": scan_time.isoformat(),
            "dlq_entries_found": entries_requiring_review,
            "recent_failures_24h": recent_failure_count,
            "total_webhook_failures": health_stats.get("failures_by_queue", {}).get("webhook_processing", 0),
            "entries_reprocessed": 0,  # TODO: Implement reprocessing logic
            "alerts_sent": 1 if recent_failure_count > 10 else 0,
            "status": "completed",
            "health_stats": health_stats
        }
        
        logger.info(f"Webhook watchdog scan completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Webhook watchdog scan failed: {e}")
        return {
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "error": str(e)
        }


@celery_app.task(
    bind=True,
    name='backend.tasks.webhook_tasks.webhook_recovery_scan',
    acks_late=True
)
def webhook_recovery_scan(self, limit: int = 50) -> Dict[str, Any]:
    """
    Enhanced webhook recovery scan using the reliability service
    
    Args:
        self: Celery task instance
        limit: Maximum number of failed webhooks to process
        
    Returns:
        Recovery scan results
    """
    try:
        logger.info(f"Starting webhook recovery scan: limit={limit}")
        
        scan_start = datetime.now(timezone.utc)
        
        # Get reliability service
        reliability_service = get_webhook_reliability_service()
        
        # Process failed webhooks for recovery
        recovery_results = asyncio.run(
            reliability_service.process_failed_webhooks_recovery(limit=limit)
        )
        
        # Get webhook reliability statistics
        reliability_stats = reliability_service.get_webhook_reliability_stats()
        
        scan_time = (datetime.now(timezone.utc) - scan_start).total_seconds()
        
        result = {
            "recovery_scan": recovery_results,
            "reliability_stats": reliability_stats.get('delivery_statistics', {}),
            "scan_duration_seconds": scan_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "completed"
        }
        
        logger.info(
            f"Webhook recovery scan completed: {recovery_results.get('recovery_attempts', 0)} attempts, "
            f"{recovery_results.get('successful_recoveries', 0)} successes, "
            f"scan_duration={scan_time:.2f}s"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Webhook recovery scan failed: {e}")
        return {
            "recovery_scan": {"error": str(e)},
            "scan_duration_seconds": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "failed"
        }


@celery_app.task(
    bind=True,
    name='backend.tasks.webhook_tasks.webhook_cleanup_task',
    acks_late=True
)
def webhook_cleanup_task(self, batch_size: int = 1000) -> Dict[str, Any]:
    """
    Webhook reliability maintenance task for cleanup
    
    Args:
        self: Celery task instance
        batch_size: Number of records to process per batch
        
    Returns:
        Cleanup results
    """
    try:
        logger.info(f"Starting webhook cleanup task: batch_size={batch_size}")
        
        cleanup_start = datetime.now(timezone.utc)
        
        # Get reliability service
        reliability_service = get_webhook_reliability_service()
        
        # Clean up expired records
        cleanup_results = asyncio.run(
            reliability_service.cleanup_expired_records(batch_size=batch_size)
        )
        
        cleanup_time = (datetime.now(timezone.utc) - cleanup_start).total_seconds()
        
        result = {
            "cleanup_results": cleanup_results,
            "cleanup_duration_seconds": cleanup_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "completed" if not cleanup_results.get('error') else "failed"
        }
        
        logger.info(
            f"Webhook cleanup completed: "
            f"{cleanup_results.get('expired_idempotency_records_deleted', 0)} idempotency records, "
            f"{cleanup_results.get('old_delivered_records_deleted', 0)} delivered records, "
            f"{cleanup_results.get('old_abandoned_records_deleted', 0)} abandoned records deleted, "
            f"cleanup_duration={cleanup_time:.2f}s"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Webhook cleanup task failed: {e}")
        return {
            "cleanup_results": {"error": str(e)},
            "cleanup_duration_seconds": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "failed"
        }