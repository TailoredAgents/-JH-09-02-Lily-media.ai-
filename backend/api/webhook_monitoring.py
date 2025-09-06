"""
Webhook Dead Letter Queue (DLQ) Monitoring API
Provides endpoints for monitoring, analyzing, and managing failed webhook processing
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.core.dlq import get_dlq_manager, TaskFailureReason, DeadLetterTask
from backend.auth.dependencies import get_current_user, AuthUser
from backend.middleware.tenant_context import get_tenant_context, TenantContext

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/webhook-monitoring", tags=["webhook-monitoring"])


@router.get("/dlq/status")
async def get_dlq_status(
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get Dead Letter Queue status and health metrics
    
    Returns:
        DLQ health statistics and recent failure summary
    """
    try:
        with get_dlq_manager(db) as dlq:
            # Get overall DLQ health stats
            health_stats = dlq.get_queue_health_stats()
            
            # Get organization-specific webhook failures
            org_webhook_failures = dlq.get_failed_tasks(
                queue_name="webhook_processing",
                organization_id=tenant_context.organization_id,
                limit=50
            )
            
            # Get recent failures (last 24 hours)
            recent_failures = [f for f in org_webhook_failures if 
                             (datetime.utcnow() - f.moved_to_dlq_at).days < 1]
            
            # Categorize failures by reason
            failure_by_reason = {}
            for failure in org_webhook_failures:
                reason = failure.failure_reason
                if reason not in failure_by_reason:
                    failure_by_reason[reason] = 0
                failure_by_reason[reason] += 1
            
            # Get manual review count
            manual_review_count = len([f for f in org_webhook_failures 
                                     if f.requires_manual_review and not f.is_requeued])
            
            return {
                "organization_id": tenant_context.organization_id,
                "dlq_health": {
                    "total_webhook_failures": len(org_webhook_failures),
                    "recent_failures_24h": len(recent_failures),
                    "manual_review_required": manual_review_count,
                    "failure_categories": failure_by_reason
                },
                "global_health": health_stats,
                "status": "healthy" if len(recent_failures) < 10 else "degraded" if len(recent_failures) < 50 else "critical",
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting DLQ status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get DLQ status: {e}")


@router.get("/dlq/failures")
async def get_webhook_failures(
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    failure_reason: Optional[str] = Query(None, description="Filter by failure reason"),
    requires_manual_review: Optional[bool] = Query(None, description="Filter by manual review requirement"),
    limit: int = Query(50, description="Maximum number of failures to return", le=200),
    offset: int = Query(0, description="Offset for pagination")
) -> Dict[str, Any]:
    """
    Get webhook processing failures for the organization
    
    Args:
        failure_reason: Filter by specific failure reason
        requires_manual_review: Filter by manual review requirement  
        limit: Maximum number of results
        offset: Pagination offset
        
    Returns:
        List of webhook failures with details
    """
    try:
        with get_dlq_manager(db) as dlq:
            # Convert string failure reason to enum if provided
            reason_filter = None
            if failure_reason:
                try:
                    reason_filter = TaskFailureReason(failure_reason)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid failure reason: {failure_reason}")
            
            # Get failed webhook tasks for the organization
            failed_tasks = dlq.get_failed_tasks(
                queue_name="webhook_processing",
                failure_reason=reason_filter,
                organization_id=tenant_context.organization_id,
                requires_manual_review=requires_manual_review,
                limit=limit + offset
            )[offset:offset + limit]
            
            # Format response
            failures = []
            for task in failed_tasks:
                failure_data = {
                    "task_id": task.task_id,
                    "task_name": task.task_name,
                    "failure_reason": task.failure_reason,
                    "error_message": task.error_message,
                    "retry_count": task.retry_count,
                    "first_failure_at": task.first_failure_at.isoformat(),
                    "moved_to_dlq_at": task.moved_to_dlq_at.isoformat(),
                    "requires_manual_review": task.requires_manual_review,
                    "is_requeued": task.is_requeued,
                    "user_id": task.user_id,
                    "metadata": task.task_metadata
                }
                failures.append(failure_data)
            
            return {
                "organization_id": tenant_context.organization_id,
                "failures": failures,
                "total_count": len(failures),
                "filters": {
                    "failure_reason": failure_reason,
                    "requires_manual_review": requires_manual_review
                },
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": len(failed_tasks) == limit  # Simplified check
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting webhook failures: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get webhook failures: {e}")


@router.post("/dlq/requeue/{task_id}")
async def requeue_webhook_failure(
    task_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Requeue a failed webhook task for retry
    
    Args:
        task_id: Task ID to requeue
        
    Returns:
        Requeue operation result
    """
    try:
        with get_dlq_manager(db) as dlq:
            # Verify the task belongs to the organization
            task = db.query(DeadLetterTask).filter(
                DeadLetterTask.task_id == task_id,
                DeadLetterTask.organization_id == tenant_context.organization_id
            ).first()
            
            if not task:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Webhook task {task_id} not found or access denied"
                )
            
            # Check if already requeued
            if task.is_requeued:
                return {
                    "task_id": task_id,
                    "status": "already_requeued",
                    "requeued_at": task.requeued_at.isoformat() if task.requeued_at else None
                }
            
            # Requeue the task
            success = dlq.requeue_task(task_id)
            
            if success:
                logger.info(f"Successfully requeued webhook task {task_id} for org {tenant_context.organization_id}")
                return {
                    "task_id": task_id,
                    "status": "requeued",
                    "requeued_at": datetime.utcnow().isoformat(),
                    "original_failure": task.failure_reason,
                    "retry_count": task.retry_count
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to requeue task")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requeuing webhook task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to requeue task: {e}")


@router.get("/dlq/analytics")
async def get_webhook_analytics(
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    days: int = Query(7, description="Number of days to analyze", ge=1, le=30)
) -> Dict[str, Any]:
    """
    Get webhook failure analytics for the organization
    
    Args:
        days: Number of days to analyze (1-30)
        
    Returns:
        Webhook failure analytics and trends
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with get_dlq_manager(db) as dlq:
            # Get all webhook failures for the organization in the time period
            all_failures = db.query(DeadLetterTask).filter(
                DeadLetterTask.organization_id == tenant_context.organization_id,
                DeadLetterTask.queue_name == "webhook_processing",
                DeadLetterTask.moved_to_dlq_at >= cutoff_date
            ).all()
            
            # Analyze by day
            daily_failures = {}
            for i in range(days):
                day = datetime.utcnow().date() - timedelta(days=i)
                daily_failures[day.isoformat()] = 0
            
            for failure in all_failures:
                day = failure.moved_to_dlq_at.date().isoformat()
                if day in daily_failures:
                    daily_failures[day] += 1
            
            # Analyze by failure reason
            reason_analysis = {}
            for failure in all_failures:
                reason = failure.failure_reason
                if reason not in reason_analysis:
                    reason_analysis[reason] = {
                        "count": 0,
                        "percentage": 0,
                        "avg_retries": 0,
                        "manual_review_required": 0
                    }
                
                reason_analysis[reason]["count"] += 1
                reason_analysis[reason]["avg_retries"] += failure.retry_count
                if failure.requires_manual_review:
                    reason_analysis[reason]["manual_review_required"] += 1
            
            # Calculate percentages and averages
            total_failures = len(all_failures)
            for reason, data in reason_analysis.items():
                data["percentage"] = round((data["count"] / total_failures * 100), 2) if total_failures > 0 else 0
                data["avg_retries"] = round(data["avg_retries"] / data["count"], 1) if data["count"] > 0 else 0
            
            # Get top error patterns
            error_patterns = {}
            for failure in all_failures:
                # Extract error pattern (first 100 chars of error message)
                error_pattern = failure.error_message[:100] if failure.error_message else "Unknown error"
                if error_pattern not in error_patterns:
                    error_patterns[error_pattern] = 0
                error_patterns[error_pattern] += 1
            
            # Sort error patterns by frequency
            top_errors = sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "organization_id": tenant_context.organization_id,
                "analysis_period": {
                    "days": days,
                    "start_date": cutoff_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat()
                },
                "summary": {
                    "total_failures": total_failures,
                    "daily_average": round(total_failures / days, 1),
                    "manual_review_required": sum([f for f in all_failures if f.requires_manual_review and not f.is_requeued]),
                    "requeued_count": sum([1 for f in all_failures if f.is_requeued])
                },
                "daily_trend": daily_failures,
                "failure_reasons": reason_analysis,
                "top_error_patterns": [{"pattern": pattern, "count": count} for pattern, count in top_errors],
                "generated_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error generating webhook analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate analytics: {e}")


@router.delete("/dlq/cleanup")
async def cleanup_old_webhook_failures(
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    days_old: int = Query(30, description="Delete failures older than this many days", ge=7, le=365)
) -> Dict[str, Any]:
    """
    Clean up old webhook failures (admin only)
    
    Args:
        days_old: Delete failures older than this many days
        
    Returns:
        Cleanup operation result
    """
    try:
        # Check if user has admin role
        if tenant_context.role not in ["admin", "owner"]:
            raise HTTPException(status_code=403, detail="Admin access required for cleanup operations")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Only clean up requeued tasks or very old tasks to preserve debugging data
        deleted_count = db.query(DeadLetterTask).filter(
            DeadLetterTask.organization_id == tenant_context.organization_id,
            DeadLetterTask.queue_name == "webhook_processing",
            DeadLetterTask.moved_to_dlq_at < cutoff_date,
            DeadLetterTask.is_requeued == True
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleaned up {deleted_count} old webhook failures for org {tenant_context.organization_id}")
        
        return {
            "organization_id": tenant_context.organization_id,
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "criteria": "requeued tasks only",
            "cleaned_up_by": tenant_context.user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during webhook failure cleanup: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {e}")


@router.get("/health")
async def webhook_health_check() -> Dict[str, Any]:
    """
    Health check endpoint for webhook monitoring system
    
    Returns:
        System health status
    """
    try:
        with get_dlq_manager() as dlq:
            health_stats = dlq.get_queue_health_stats()
            
            # Determine overall health
            total_failures = health_stats.get("total_failed_tasks", 0)
            recent_failures = health_stats.get("recent_failures_24h", 0)
            manual_review_required = health_stats.get("manual_review_required", 0)
            
            if recent_failures > 100:
                status = "critical"
                message = f"{recent_failures} webhook failures in last 24h"
            elif recent_failures > 50:
                status = "degraded"
                message = f"{recent_failures} webhook failures in last 24h"
            elif manual_review_required > 10:
                status = "warning"
                message = f"{manual_review_required} failures require manual review"
            else:
                status = "healthy"
                message = "All webhook systems operational"
            
            return {
                "status": status,
                "message": message,
                "metrics": {
                    "total_failed_tasks": total_failures,
                    "recent_failures_24h": recent_failures,
                    "manual_review_required": manual_review_required
                },
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0"
            }
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "message": f"Health check failed: {e}",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }