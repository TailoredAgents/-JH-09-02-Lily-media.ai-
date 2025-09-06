"""
Dead Letter Queue (DLQ) Implementation for Failed Tasks
Handles task failures with retry logic and permanent failure storage
"""
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func

from backend.core.config import get_settings
from backend.db.database import get_db

logger = logging.getLogger(__name__)

Base = declarative_base()

class TaskFailureReason(str, Enum):
    """Task failure categorization"""
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    NETWORK_ERROR = "network_error"
    INVALID_DATA = "invalid_data"
    EXTERNAL_API_ERROR = "external_api_error"
    INTERNAL_ERROR = "internal_error"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    TENANT_ISOLATION_VIOLATION = "tenant_isolation_violation"

class DeadLetterTask(Base):
    """
    Dead Letter Queue table for permanently failed tasks
    """
    __tablename__ = "dead_letter_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Task identification
    task_id = Column(String, unique=True, nullable=False, index=True)
    task_name = Column(String, nullable=False, index=True)
    queue_name = Column(String, nullable=False, index=True)
    
    # Tenant isolation
    organization_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    
    # Task data
    original_args = Column(JSON, nullable=True)
    original_kwargs = Column(JSON, nullable=True)
    
    # Failure information
    failure_reason = Column(String, nullable=False, index=True)  # TaskFailureReason enum
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    original_eta = Column(DateTime, nullable=True)
    first_failure_at = Column(DateTime, default=func.now(), nullable=False)
    last_retry_at = Column(DateTime, nullable=True)
    moved_to_dlq_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Processing status
    is_requeued = Column(Boolean, default=False)
    requeued_at = Column(DateTime, nullable=True)
    requires_manual_review = Column(Boolean, default=False)
    
    # Metadata
    task_metadata = Column(JSON, nullable=True)  # Additional context data
    
    def __repr__(self):
        return f"<DeadLetterTask(task_id={self.task_id}, task_name={self.task_name}, reason={self.failure_reason})>"

class DLQManager:
    """
    Dead Letter Queue Manager
    
    Handles failed task storage, retry logic, and monitoring
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize DLQ Manager
        
        Args:
            db: Optional database session (uses get_db() if None)
        """
        self.db = db
        self._should_close_db = db is None
        
        if self.db is None:
            self.db = next(get_db())
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_db and self.db:
            self.db.close()
    
    def record_task_failure(
        self,
        task_id: str,
        task_name: str,
        queue_name: str,
        failure_reason: TaskFailureReason,
        error_message: str,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        error_traceback: Optional[str] = None,
        organization_id: Optional[int] = None,
        user_id: Optional[int] = None,
        retry_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeadLetterTask:
        """
        Record a failed task in the DLQ
        
        Args:
            task_id: Unique task identifier
            task_name: Name of the failed task
            queue_name: Queue the task was running in
            failure_reason: Categorized failure reason
            error_message: Human-readable error message
            args: Original task arguments
            kwargs: Original task keyword arguments
            error_traceback: Full error traceback
            organization_id: Tenant organization ID (if applicable)
            user_id: User ID (if applicable)
            retry_count: Number of retries attempted
            metadata: Additional context data
            
        Returns:
            DeadLetterTask record
        """
        try:
            # Check if task already exists in DLQ
            existing = self.db.query(DeadLetterTask).filter(
                DeadLetterTask.task_id == task_id
            ).first()
            
            if existing:
                # Update existing record
                existing.last_retry_at = func.now()
                existing.retry_count = retry_count
                existing.error_message = error_message
                existing.error_traceback = error_traceback
                existing.failure_reason = failure_reason.value
                
                if metadata:
                    existing.task_metadata = {**(existing.task_metadata or {}), **metadata}
                
                dlq_task = existing
                logger.info(f"Updated existing DLQ record for task {task_id}")
            else:
                # Create new DLQ record
                dlq_task = DeadLetterTask(
                    task_id=task_id,
                    task_name=task_name,
                    queue_name=queue_name,
                    organization_id=organization_id,
                    user_id=user_id,
                    original_args=list(args) if args else None,
                    original_kwargs=dict(kwargs) if kwargs else None,
                    failure_reason=failure_reason.value,
                    error_message=error_message,
                    error_traceback=error_traceback,
                    retry_count=retry_count,
                    requires_manual_review=self._requires_manual_review(failure_reason),
                    task_metadata=metadata
                )
                
                self.db.add(dlq_task)
                logger.info(f"Created new DLQ record for task {task_id}")
            
            self.db.commit()
            
            # Log security violations separately
            if failure_reason == TaskFailureReason.TENANT_ISOLATION_VIOLATION:
                logger.error(
                    f"SECURITY: Tenant isolation violation in task {task_id} - "
                    f"user_id={user_id}, organization_id={organization_id}"
                )
            
            return dlq_task
            
        except Exception as e:
            logger.error(f"Failed to record DLQ task {task_id}: {e}")
            self.db.rollback()
            raise
    
    def _requires_manual_review(self, failure_reason: TaskFailureReason) -> bool:
        """
        Determine if a failure reason requires manual review
        
        Args:
            failure_reason: The failure reason
            
        Returns:
            True if manual review is required
        """
        manual_review_reasons = {
            TaskFailureReason.TENANT_ISOLATION_VIOLATION,
            TaskFailureReason.INVALID_DATA,
            TaskFailureReason.INTERNAL_ERROR,
        }
        
        return failure_reason in manual_review_reasons
    
    def get_failed_tasks(
        self,
        queue_name: Optional[str] = None,
        failure_reason: Optional[TaskFailureReason] = None,
        organization_id: Optional[int] = None,
        requires_manual_review: Optional[bool] = None,
        limit: int = 100
    ) -> List[DeadLetterTask]:
        """
        Retrieve failed tasks from DLQ
        
        Args:
            queue_name: Filter by queue name
            failure_reason: Filter by failure reason
            organization_id: Filter by organization (tenant isolation)
            requires_manual_review: Filter by manual review requirement
            limit: Maximum number of records to return
            
        Returns:
            List of DeadLetterTask records
        """
        try:
            query = self.db.query(DeadLetterTask)
            
            if queue_name:
                query = query.filter(DeadLetterTask.queue_name == queue_name)
            
            if failure_reason:
                query = query.filter(DeadLetterTask.failure_reason == failure_reason.value)
            
            if organization_id is not None:
                query = query.filter(DeadLetterTask.organization_id == organization_id)
            
            if requires_manual_review is not None:
                query = query.filter(DeadLetterTask.requires_manual_review == requires_manual_review)
            
            # Order by most recent failures first
            query = query.order_by(DeadLetterTask.moved_to_dlq_at.desc())
            
            return query.limit(limit).all()
            
        except Exception as e:
            logger.error(f"Failed to retrieve DLQ tasks: {e}")
            return []
    
    def requeue_task(self, task_id: str) -> bool:
        """
        Mark a task as requeued for manual retry
        
        Args:
            task_id: Task ID to requeue
            
        Returns:
            True if successfully requeued
        """
        try:
            dlq_task = self.db.query(DeadLetterTask).filter(
                DeadLetterTask.task_id == task_id
            ).first()
            
            if not dlq_task:
                logger.warning(f"DLQ task {task_id} not found for requeue")
                return False
            
            dlq_task.is_requeued = True
            dlq_task.requeued_at = func.now()
            
            self.db.commit()
            
            logger.info(f"Marked DLQ task {task_id} as requeued")
            return True
            
        except Exception as e:
            logger.error(f"Failed to requeue DLQ task {task_id}: {e}")
            self.db.rollback()
            return False
    
    def cleanup_old_tasks(self, days_old: int = 30) -> int:
        """
        Clean up old DLQ records
        
        Args:
            days_old: Delete records older than this many days
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Only delete successfully requeued tasks or very old failed tasks
            deleted_count = self.db.query(DeadLetterTask).filter(
                DeadLetterTask.moved_to_dlq_at < cutoff_date,
                DeadLetterTask.is_requeued == True
            ).delete()
            
            self.db.commit()
            
            logger.info(f"Cleaned up {deleted_count} old DLQ records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old DLQ tasks: {e}")
            self.db.rollback()
            return 0
    
    def get_queue_health_stats(self) -> Dict[str, Any]:
        """
        Get DLQ health statistics
        
        Returns:
            Dictionary with DLQ health metrics
        """
        try:
            total_failed = self.db.query(DeadLetterTask).count()
            
            # Failed tasks by queue
            queue_stats = self.db.query(
                DeadLetterTask.queue_name,
                func.count(DeadLetterTask.id).label('count')
            ).group_by(DeadLetterTask.queue_name).all()
            
            # Failed tasks by reason
            reason_stats = self.db.query(
                DeadLetterTask.failure_reason,
                func.count(DeadLetterTask.id).label('count')
            ).group_by(DeadLetterTask.failure_reason).all()
            
            # Tasks requiring manual review
            manual_review_count = self.db.query(DeadLetterTask).filter(
                DeadLetterTask.requires_manual_review == True,
                DeadLetterTask.is_requeued == False
            ).count()
            
            # Recent failures (last 24 hours)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_failures = self.db.query(DeadLetterTask).filter(
                DeadLetterTask.moved_to_dlq_at >= recent_cutoff
            ).count()
            
            return {
                "total_failed_tasks": total_failed,
                "manual_review_required": manual_review_count,
                "recent_failures_24h": recent_failures,
                "failures_by_queue": {queue: count for queue, count in queue_stats},
                "failures_by_reason": {reason: count for reason, count in reason_stats},
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get DLQ health stats: {e}")
            return {"error": str(e)}


def get_dlq_manager(db: Optional[Session] = None) -> DLQManager:
    """
    Get DLQ manager instance
    
    Args:
        db: Optional database session
        
    Returns:
        DLQManager instance
    """
    return DLQManager(db=db)


# Celery task failure handler
def handle_task_failure(
    task_id: str,
    task_name: str,
    queue_name: str,
    error: Exception,
    traceback_str: str,
    retry_count: int = 0,
    organization_id: Optional[int] = None,
    user_id: Optional[int] = None,
    task_args: Optional[tuple] = None,
    task_kwargs: Optional[dict] = None
) -> None:
    """
    Handle Celery task failure and record in DLQ
    
    Args:
        task_id: Failed task ID
        task_name: Failed task name
        queue_name: Queue name
        error: Exception that caused failure
        traceback_str: Error traceback
        retry_count: Number of retries attempted
        organization_id: Tenant organization ID
        user_id: User ID
        task_args: Original task arguments
        task_kwargs: Original task keyword arguments
    """
    try:
        # Categorize the failure reason
        failure_reason = _categorize_failure(error)
        
        with get_dlq_manager() as dlq:
            dlq.record_task_failure(
                task_id=task_id,
                task_name=task_name,
                queue_name=queue_name,
                failure_reason=failure_reason,
                error_message=str(error),
                error_traceback=traceback_str,
                retry_count=retry_count,
                organization_id=organization_id,
                user_id=user_id,
                args=task_args,
                kwargs=task_kwargs,
                metadata={
                    "error_type": type(error).__name__,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
    except Exception as dlq_error:
        # Log but don't raise - DLQ failures shouldn't break the main application
        logger.error(f"Failed to record task failure in DLQ: {dlq_error}")


def _categorize_failure(error: Exception) -> TaskFailureReason:
    """
    Categorize failure based on exception type and message
    
    Args:
        error: The exception that caused the failure
        
    Returns:
        TaskFailureReason enum value
    """
    error_type = type(error).__name__
    error_message = str(error).lower()
    
    # Timeout errors
    if 'timeout' in error_message or error_type in ['TimeoutError', 'ConnectTimeout']:
        return TaskFailureReason.TIMEOUT
    
    # Rate limiting
    if 'rate limit' in error_message or 'too many requests' in error_message:
        return TaskFailureReason.RATE_LIMIT
    
    # Authentication errors
    if 'auth' in error_message or 'unauthorized' in error_message or 'forbidden' in error_message:
        return TaskFailureReason.AUTH_ERROR
    
    # Network errors
    if 'connection' in error_message or 'network' in error_message or error_type in ['ConnectionError', 'ConnectTimeoutError']:
        return TaskFailureReason.NETWORK_ERROR
    
    # Data validation
    if 'validation' in error_message or 'invalid' in error_message or error_type in ['ValidationError', 'ValueError']:
        return TaskFailureReason.INVALID_DATA
    
    # Tenant isolation violations
    if 'organization' in error_message and ('not belong' in error_message or 'isolation' in error_message):
        return TaskFailureReason.TENANT_ISOLATION_VIOLATION
    
    # External API errors
    if 'api' in error_message or error_type in ['HTTPError', 'RequestException']:
        return TaskFailureReason.EXTERNAL_API_ERROR
    
    # Default to internal error
    return TaskFailureReason.INTERNAL_ERROR