"""
Data Retention Tasks

Automated Celery tasks for data retention policy enforcement and cleanup.
Runs comprehensive data retention operations on a scheduled basis to maintain
GDPR/CCPA compliance and optimize database performance.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from celery import Task
from sqlalchemy.orm import Session

from backend.tasks.celery_app import celery_app
from backend.db.database import get_db
from backend.services.data_retention_service import (
    DataRetentionService, DataCategory, get_data_retention_service
)
from backend.core.audit_logger import audit_logger, AuditEventType

logger = logging.getLogger(__name__)

class DataRetentionTask(Task):
    """Base task class for data retention operations with error handling"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Data retention task {task_id} failed: {exc}")
        # Log failure for audit trail
        audit_logger.log_event(
            AuditEventType.DATA_RETENTION_ACTION,
            user_id=None,
            details={
                "task_id": task_id,
                "task_name": self.name,
                "status": "failed",
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            ip_address="system",
            user_agent="celery-worker"
        )

@celery_app.task(bind=True, base=DataRetentionTask, name="data_retention_daily_cleanup")
def daily_data_retention_cleanup(self):
    """
    Daily automated data retention cleanup
    
    Performs cleanup for categories with automatic_cleanup=True and short retention periods.
    Focuses on non-critical data like cache, notifications, and system logs.
    """
    logger.info("Starting daily data retention cleanup")
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        retention_service = get_data_retention_service()
        cleanup_results = {}
        
        # Categories for daily cleanup (short retention periods)
        daily_cleanup_categories = [
            DataCategory.CACHE_DATA,
            DataCategory.NOTIFICATIONS, 
            DataCategory.SYSTEM_LOGS,
        ]
        
        total_cleaned = 0
        
        for category in daily_cleanup_categories:
            try:
                logger.info(f"Processing daily cleanup for {category.value}")
                
                result = retention_service.cleanup_expired_data(
                    db=db, 
                    category=category, 
                    dry_run=False
                )
                
                cleanup_results[category.value] = result
                total_cleaned += result.get("total_deleted", 0)
                
                # Log successful cleanup
                if result.get("total_deleted", 0) > 0:
                    audit_logger.log_event(
                        AuditEventType.DATA_RETENTION_ACTION,
                        user_id=None,
                        details={
                            "action": "daily_cleanup",
                            "category": category.value,
                            "records_deleted": result.get("total_deleted", 0),
                            "deleted_counts": result.get("deleted_counts", {}),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        ip_address="system",
                        user_agent="celery-worker"
                    )
                
            except Exception as e:
                logger.error(f"Error in daily cleanup for {category.value}: {e}")
                cleanup_results[category.value] = {"error": str(e)}
        
        logger.info(f"Daily data retention cleanup completed. Total records cleaned: {total_cleaned}")
        
        return {
            "status": "completed",
            "total_cleaned": total_cleaned,
            "categories_processed": len(daily_cleanup_categories),
            "results": cleanup_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Daily data retention cleanup failed: {e}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True, base=DataRetentionTask, name="data_retention_weekly_cleanup")
def weekly_data_retention_cleanup(self):
    """
    Weekly automated data retention cleanup
    
    Performs cleanup for categories with medium retention periods.
    Focuses on user content, metrics, and workflow data.
    """
    logger.info("Starting weekly data retention cleanup")
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        retention_service = get_data_retention_service()
        cleanup_results = {}
        
        # Categories for weekly cleanup (medium retention periods)
        weekly_cleanup_categories = [
            DataCategory.USER_CONTENT,
            DataCategory.METRICS_DATA,
            DataCategory.AI_GENERATED,
            DataCategory.SOCIAL_CONNECTIONS,
            DataCategory.WORKFLOW_DATA,
            DataCategory.PERFORMANCE_DATA,
        ]
        
        total_cleaned = 0
        
        for category in weekly_cleanup_categories:
            try:
                logger.info(f"Processing weekly cleanup for {category.value}")
                
                result = retention_service.cleanup_expired_data(
                    db=db, 
                    category=category, 
                    dry_run=False
                )
                
                cleanup_results[category.value] = result
                total_cleaned += result.get("total_deleted", 0)
                
                # Log successful cleanup
                if result.get("total_deleted", 0) > 0:
                    audit_logger.log_event(
                        AuditEventType.DATA_RETENTION_ACTION,
                        user_id=None,
                        details={
                            "action": "weekly_cleanup",
                            "category": category.value,
                            "records_deleted": result.get("total_deleted", 0),
                            "deleted_counts": result.get("deleted_counts", {}),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        ip_address="system",
                        user_agent="celery-worker"
                    )
                
            except Exception as e:
                logger.error(f"Error in weekly cleanup for {category.value}: {e}")
                cleanup_results[category.value] = {"error": str(e)}
        
        logger.info(f"Weekly data retention cleanup completed. Total records cleaned: {total_cleaned}")
        
        return {
            "status": "completed",
            "total_cleaned": total_cleaned,
            "categories_processed": len(weekly_cleanup_categories),
            "results": cleanup_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Weekly data retention cleanup failed: {e}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True, base=DataRetentionTask, name="data_retention_monthly_cleanup")
def monthly_data_retention_cleanup(self):
    """
    Monthly automated data retention cleanup
    
    Performs cleanup for categories with long retention periods.
    Focuses on research data and security data (excluding audit logs).
    """
    logger.info("Starting monthly data retention cleanup")
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        retention_service = get_data_retention_service()
        cleanup_results = {}
        
        # Categories for monthly cleanup (long retention periods)
        monthly_cleanup_categories = [
            DataCategory.RESEARCH_DATA,
            DataCategory.SECURITY_DATA,  # Only includes RefreshTokenBlacklist, not audit logs
        ]
        
        total_cleaned = 0
        
        for category in monthly_cleanup_categories:
            try:
                logger.info(f"Processing monthly cleanup for {category.value}")
                
                result = retention_service.cleanup_expired_data(
                    db=db, 
                    category=category, 
                    dry_run=False
                )
                
                cleanup_results[category.value] = result
                total_cleaned += result.get("total_deleted", 0)
                
                # Log successful cleanup
                if result.get("total_deleted", 0) > 0:
                    audit_logger.log_event(
                        AuditEventType.DATA_RETENTION_ACTION,
                        user_id=None,
                        details={
                            "action": "monthly_cleanup",
                            "category": category.value,
                            "records_deleted": result.get("total_deleted", 0),
                            "deleted_counts": result.get("deleted_counts", {}),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        ip_address="system",
                        user_agent="celery-worker"
                    )
                
            except Exception as e:
                logger.error(f"Error in monthly cleanup for {category.value}: {e}")
                cleanup_results[category.value] = {"error": str(e)}
        
        logger.info(f"Monthly data retention cleanup completed. Total records cleaned: {total_cleaned}")
        
        return {
            "status": "completed",
            "total_cleaned": total_cleaned,
            "categories_processed": len(monthly_cleanup_categories),
            "results": cleanup_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Monthly data retention cleanup failed: {e}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True, base=DataRetentionTask, name="data_retention_health_report")
def generate_data_retention_health_report(self):
    """
    Generate data retention health report
    
    Analyzes current state of data retention across all categories
    and generates recommendations. Runs weekly to monitor compliance.
    """
    logger.info("Generating data retention health report")
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        retention_service = get_data_retention_service()
        
        # Generate comprehensive report
        report = retention_service.generate_retention_report(db)
        
        # Log report generation
        audit_logger.log_event(
            AuditEventType.DATA_RETENTION_ACTION,
            user_id=None,
            details={
                "action": "health_report_generated",
                "total_expired_records": report["total_expired_records"],
                "categories_with_expired_data": len(report["expired_data_summary"]),
                "recommendations_count": len(report["recommendations"]),
                "timestamp": report["generated_at"]
            },
            ip_address="system",
            user_agent="celery-worker"
        )
        
        # Log warnings if significant expired data found
        if report["total_expired_records"] > 1000:
            logger.warning(f"Data retention health check: {report['total_expired_records']} expired records found")
        
        if report["total_expired_records"] > 10000:
            logger.error(f"CRITICAL: Data retention health check: {report['total_expired_records']} expired records found")
            
            # Log critical alert
            audit_logger.log_event(
                AuditEventType.DATA_RETENTION_ACTION,
                user_id=None,
                details={
                    "action": "critical_retention_alert",
                    "total_expired_records": report["total_expired_records"],
                    "alert_level": "critical",
                    "requires_immediate_attention": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                ip_address="system",
                user_agent="celery-worker"
            )
        
        logger.info(f"Data retention health report completed. Found {report['total_expired_records']} expired records")
        
        return {
            "status": "completed",
            "report": report,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Data retention health report failed: {e}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True, base=DataRetentionTask, name="data_retention_emergency_cleanup")
def emergency_data_retention_cleanup(self, category: str, force: bool = False):
    """
    Emergency data retention cleanup for specific category
    
    Manual cleanup task that can be triggered for urgent data retention needs.
    Supports forced cleanup even for categories with automatic_cleanup=False.
    """
    logger.info(f"Starting emergency data retention cleanup for {category}")
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        retention_service = get_data_retention_service()
        
        # Validate category
        try:
            data_category = DataCategory(category)
        except ValueError:
            raise ValueError(f"Invalid category '{category}'. Valid categories: {[c.value for c in DataCategory]}")
        
        # Get policy and check if force is needed
        policy = retention_service.get_retention_policy(data_category)
        if not policy:
            raise ValueError(f"No retention policy found for category '{category}'")
        
        if not policy.automatic_cleanup and not force:
            raise ValueError(f"Category '{category}' has automatic cleanup disabled. Use force=True to override.")
        
        # Perform emergency cleanup
        result = retention_service.cleanup_expired_data(
            db=db,
            category=data_category,
            dry_run=False
        )
        
        # Log emergency cleanup
        audit_logger.log_event(
            AuditEventType.DATA_RETENTION_ACTION,
            user_id=None,
            details={
                "action": "emergency_cleanup",
                "category": category,
                "forced": force,
                "records_deleted": result.get("total_deleted", 0),
                "deleted_counts": result.get("deleted_counts", {}),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            ip_address="system",
            user_agent="celery-worker"
        )
        
        logger.info(f"Emergency cleanup completed for {category}. Records deleted: {result.get('total_deleted', 0)}")
        
        return {
            "status": "completed",
            "category": category,
            "forced": force,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Emergency data retention cleanup failed for {category}: {e}")
        raise
    finally:
        db.close()