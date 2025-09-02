"""
Celery tasks for Phase 8 resilient publishing
Handles connection-based publishing with rate limiting and retries
"""
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from celery import Task
from sqlalchemy.orm import Session

from backend.tasks.celery_app import celery
from backend.db.database import get_db, SessionLocal
from backend.db.models import SocialConnection, ContentSchedule
from backend.services.publish_runner import get_publish_runner, PublishPayload
from backend.services.rate_limit import RetryableError, FatalError

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Base task class with callbacks for success/failure"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        logger.info(f"Task {task_id} succeeded: {retval}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails completely"""
        logger.error(f"Task {task_id} failed: {exc}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        logger.warning(f"Task {task_id} retrying: {exc}")


@celery.task(
    bind=True,
    base=CallbackTask,
    max_retries=6,
    autoretry_for=(RetryableError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_backoff_max=300,  # Max 5 minutes
    name='publish_tasks.publish_via_connection'
)
def publish_via_connection(
    self,
    connection_id: str,
    payload_dict: Dict[str, Any],
    content_hash: str,
    scheduled_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    Publish content via connection with resilient retry logic
    
    Args:
        connection_id: UUID of the SocialConnection
        payload_dict: Serialized PublishPayload
        content_hash: Content hash for idempotency
        scheduled_time: ISO timestamp when content was scheduled
        
    Returns:
        Dictionary with publish results
    """
    db = SessionLocal()
    
    try:
        logger.info(
            f"Starting publish task for connection {connection_id}, "
            f"attempt {self.request.retries + 1}"
        )
        
        # Load connection
        connection = db.query(SocialConnection).filter(
            SocialConnection.id == connection_id
        ).first()
        
        if not connection:
            raise FatalError(f"Connection {connection_id} not found")
        
        if not connection.is_active:
            raise FatalError(f"Connection {connection_id} is not active")
        
        # Check idempotency - see if we already published this successfully
        if content_hash:
            existing_success = db.query(ContentSchedule).filter(
                ContentSchedule.connection_id == connection_id,
                ContentSchedule.content_hash == content_hash,
                ContentSchedule.status == 'published'
            ).first()
            
            if existing_success:
                logger.info(f"Content already published successfully: {existing_success.platform_post_id}")
                return {
                    'success': True,
                    'platform_post_id': existing_success.platform_post_id,
                    'message': 'Already published (idempotency)',
                    'connection_id': connection_id,
                    'platform': connection.platform
                }
        
        # Reconstruct payload
        payload = PublishPayload(
            content=payload_dict['content'],
            media_urls=payload_dict.get('media_urls', []),
            content_hash=content_hash,
            scheduled_time=datetime.fromisoformat(scheduled_time) if scheduled_time else None,
            idempotency_key=payload_dict.get('idempotency_key')
        )
        
        # Run resilient publish
        runner = get_publish_runner()
        # Run async publish pipeline from synchronous Celery task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(runner.run_publish(
                connection=connection,
                payload=payload,
                db=db,
                attempt=self.request.retries
            ))
        finally:
            loop.close()
        
        # Handle result
        if result.success:
            # Update ContentSchedule record if it exists
            if payload.idempotency_key:
                schedule = db.query(ContentSchedule).filter(
                    ContentSchedule.idempotency_key == payload.idempotency_key
                ).first()
                
                if schedule:
                    schedule.status = 'published'
                    schedule.published_at = datetime.now(timezone.utc)
                    schedule.platform_post_id = result.platform_post_id
                    db.commit()
            
            return {
                'success': True,
                'platform_post_id': result.platform_post_id,
                'message': 'Published successfully',
                'connection_id': connection_id,
                'platform': connection.platform,
                'metrics': result.metrics
            }
        
        elif result.should_retry:
            # Raise retryable error to trigger Celery retry
            retry_delay = result.retry_after_s or 60
            
            # Update ContentSchedule status to show it's retrying
            if payload.idempotency_key:
                schedule = db.query(ContentSchedule).filter(
                    ContentSchedule.idempotency_key == payload.idempotency_key
                ).first()
                
                if schedule:
                    schedule.status = f'retrying_attempt_{self.request.retries + 1}'
                    schedule.error_message = result.error_message
                    db.commit()
            
            logger.warning(
                f"Retrying publish for connection {connection_id} in {retry_delay}s: "
                f"{result.error_message}"
            )
            
            # Use Celery's retry mechanism with custom countdown
            raise self.retry(
                countdown=int(retry_delay),
                exc=RetryableError(result.error_message)
            )
        
        else:
            # Fatal error - don't retry
            if payload.idempotency_key:
                schedule = db.query(ContentSchedule).filter(
                    ContentSchedule.idempotency_key == payload.idempotency_key
                ).first()
                
                if schedule:
                    schedule.status = 'failed'
                    schedule.error_message = result.error_message
                    db.commit()
            
            return {
                'success': False,
                'error_message': result.error_message,
                'connection_id': connection_id,
                'platform': connection.platform,
                'metrics': result.metrics
            }
            
    except RetryableError:
        # This will be caught by Celery's autoretry_for
        raise
        
    except FatalError as e:
        logger.error(f"Fatal error in publish task: {e}")
        
        # Mark as failed in database
        if payload_dict.get('idempotency_key'):
            try:
                schedule = db.query(ContentSchedule).filter(
                    ContentSchedule.idempotency_key == payload_dict['idempotency_key']
                ).first()
                
                if schedule:
                    schedule.status = 'failed'
                    schedule.error_message = str(e)
                    db.commit()
            except Exception as db_error:
                logger.error(f"Error updating schedule status: {db_error}")
        
        return {
            'success': False,
            'error_message': str(e),
            'connection_id': connection_id,
            'platform': getattr(connection, 'platform', 'unknown'),
            'is_fatal': True
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in publish task: {e}")
        
        # Treat unexpected errors as retryable with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=RetryableError(f"Unexpected error: {str(e)}"))
        else:
            # Max retries exceeded
            if payload_dict.get('idempotency_key'):
                try:
                    schedule = db.query(ContentSchedule).filter(
                        ContentSchedule.idempotency_key == payload_dict['idempotency_key']
                    ).first()
                    
                    if schedule:
                        schedule.status = 'failed'
                        schedule.error_message = f"Max retries exceeded: {str(e)}"
                        db.commit()
                except Exception as db_error:
                    logger.error(f"Error updating schedule status: {db_error}")
            
            return {
                'success': False,
                'error_message': f"Max retries exceeded: {str(e)}",
                'connection_id': connection_id,
                'platform': 'unknown',
                'max_retries_exceeded': True
            }
    
    finally:
        db.close()


@celery.task(
    bind=True,
    name='publish_tasks.get_publish_status'
)
def get_publish_status(self, org_id: str, platform: str) -> Dict[str, Any]:
    """
    Get current publishing status for organization and platform
    
    Args:
        org_id: Organization ID
        platform: Platform name
        
    Returns:
        Dictionary with current rate limiting and circuit breaker status
    """
    try:
        runner = get_publish_runner()
        return runner.get_rate_limit_status(org_id, platform)
        
    except Exception as e:
        logger.error(f"Error getting publish status: {e}")
        return {
            'error': str(e),
            'rate_limit': {
                'remaining': 0,
                'limit': 60
            },
            'circuit_breaker': {
                'state': 'unknown'
            }
        }


@celery.task(
    bind=True,
    name='publish_tasks.reset_circuit_breaker'
)
def reset_circuit_breaker(self, org_id: str, platform: str) -> Dict[str, Any]:
    """
    Manually reset circuit breaker for organization and platform
    
    Args:
        org_id: Organization ID
        platform: Platform name
        
    Returns:
        Dictionary with reset status
    """
    try:
        from backend.services.rate_limit import get_circuit_breaker
        
        cb = get_circuit_breaker()
        
        # Manual reset by clearing Redis state
        key = f"{cb.key_prefix}:{org_id}:{platform}"
        cb.redis.delete(key)
        
        logger.info(f"Circuit breaker reset for org {org_id} platform {platform}")
        
        return {
            'success': True,
            'message': f'Circuit breaker reset for {org_id}:{platform}'
        }
        
    except Exception as e:
        logger.error(f"Error resetting circuit breaker: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# Helper function to enqueue publish tasks
def enqueue_publish_task(
    connection_id: str,
    content: str,
    media_urls: list,
    content_hash: str,
    scheduled_time: Optional[datetime] = None,
    idempotency_key: Optional[str] = None,
    delay_s: float = 0
) -> str:
    """
    Enqueue a publish task
    
    Args:
        connection_id: UUID of the SocialConnection
        content: Content to publish
        media_urls: List of media URLs
        content_hash: Content hash for idempotency
        scheduled_time: When content was scheduled
        idempotency_key: Unique key for this schedule
        delay_s: Delay before executing task
        
    Returns:
        Celery task ID
    """
    payload_dict = {
        'content': content,
        'media_urls': media_urls,
        'idempotency_key': idempotency_key
    }
    
    scheduled_time_str = scheduled_time.isoformat() if scheduled_time else None
    
    if delay_s > 0:
        # Schedule task for future execution
        eta = datetime.now(timezone.utc).timestamp() + delay_s
        task = publish_via_connection.apply_async(
            args=[connection_id, payload_dict, content_hash, scheduled_time_str],
            eta=datetime.fromtimestamp(eta, tz=timezone.utc)
        )
    else:
        # Execute immediately
        task = publish_via_connection.delay(
            connection_id, payload_dict, content_hash, scheduled_time_str
        )
    
    logger.info(f"Enqueued publish task {task.id} for connection {connection_id}")
    return task.id
