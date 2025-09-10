"""
Encryption Key Rotation Tasks

Automated Celery tasks for encryption key rotation, compliance monitoring,
and security maintenance. Implements scheduled key rotation based on 
security policies and compliance requirements.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from celery import Task
from sqlalchemy.orm import Session

from backend.tasks.celery_app import celery_app
from backend.db.database import get_db
from backend.services.key_rotation_service import (
    KeyRotationService, KeyType, get_key_rotation_service
)
from backend.services.automated_key_rotation_scheduler import (
    AutomatedKeyRotationScheduler, get_key_rotation_scheduler
)
from backend.core.audit_logger import audit_logger, AuditEventType

logger = logging.getLogger(__name__)

class KeyRotationTask(Task):
    """Base task class for key rotation operations with error handling"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Key rotation task {task_id} failed: {exc}")
        # Log failure for audit trail
        audit_logger.log_event(
            AuditEventType.SECURITY_EVENT,
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

@celery_app.task(bind=True, base=KeyRotationTask, name="key_rotation_health_check")
def key_rotation_health_check(self):
    """
    Key rotation system health check
    
    Monitors key rotation system health, checks for overdue keys,
    and generates alerts for keys requiring immediate attention.
    """
    logger.info("Starting key rotation health check")
    
    try:
        key_service = get_key_rotation_service()
        schedule = key_service.get_key_rotation_schedule()
        
        health_status = {
            "status": "healthy",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "overdue_key_types": schedule["overdue_key_types"],
            "total_key_types": len(schedule["key_types"]),
            "issues": [],
            "warnings": []
        }
        
        # Check for critical issues
        for key_type_str, details in schedule["key_types"].items():
            if details.get("status") == "no_keys":
                health_status["issues"].append(f"CRITICAL: No active keys for {key_type_str}")
                health_status["status"] = "critical"
            elif details.get("is_overdue"):
                days_overdue = details["oldest_key_age_days"] - details["rotation_interval_days"]
                
                if days_overdue > (details["rotation_interval_days"] * 0.5):  # >50% overdue
                    health_status["issues"].append(f"CRITICAL: {key_type_str} keys severely overdue ({days_overdue} days)")
                    health_status["status"] = "critical"
                else:
                    health_status["warnings"].append(f"WARNING: {key_type_str} keys overdue ({days_overdue} days)")
                    if health_status["status"] == "healthy":
                        health_status["status"] = "warning"
        
        # Log health check results
        audit_logger.log_event(
            AuditEventType.SECURITY_EVENT,
            user_id=None,
            details={
                "action": "key_rotation_health_check",
                "status": health_status["status"],
                "overdue_key_types": health_status["overdue_key_types"],
                "total_issues": len(health_status["issues"]),
                "total_warnings": len(health_status["warnings"]),
                "timestamp": health_status["checked_at"]
            },
            ip_address="system",
            user_agent="celery-worker"
        )
        
        # Log critical issues
        if health_status["status"] == "critical":
            logger.error(f"Key rotation health check: CRITICAL issues found: {health_status['issues']}")
        elif health_status["status"] == "warning":
            logger.warning(f"Key rotation health check: Warnings found: {health_status['warnings']}")
        else:
            logger.info("Key rotation health check: All systems healthy")
        
        return health_status
        
    except Exception as e:
        logger.error(f"Key rotation health check failed: {e}")
        audit_logger.log_event(
            AuditEventType.SECURITY_EVENT,
            user_id=None,
            details={
                "action": "key_rotation_health_check",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            ip_address="system",
            user_agent="celery-worker"
        )
        raise

@celery_app.task(bind=True, base=KeyRotationTask, name="automated_key_rotation_check")
def automated_key_rotation_check(self):
    """
    Automated key rotation schedule check
    
    Checks all key types for rotation requirements and schedules
    rotations for keys that are due according to policy.
    """
    logger.info("Starting automated key rotation check")
    
    try:
        key_service = get_key_rotation_service()
        results = {}
        scheduled_count = 0
        
        # Check each key type for rotation needs
        for key_type in KeyType:
            try:
                logger.info(f"Checking rotation schedule for {key_type.value}")
                
                # Schedule rotation if due (not forced)
                result = key_service.schedule_key_rotation(key_type, force=False)
                results[key_type.value] = result
                
                if result["action"] == "rotation_scheduled":
                    scheduled_count += 1
                    logger.info(f"Scheduled rotation for {key_type.value}: {result['event_id']}")
                elif result["action"] == "rotation_not_due":
                    logger.debug(f"Rotation not due for {key_type.value}: {result.get('rotation_due_in_days')} days remaining")
                
            except Exception as e:
                logger.error(f"Error checking rotation for {key_type.value}: {e}")
                results[key_type.value] = {
                    "action": "error",
                    "error": str(e)
                }
        
        # Log rotation scheduling results
        audit_logger.log_event(
            AuditEventType.SECURITY_EVENT,
            user_id=None,
            details={
                "action": "automated_key_rotation_check",
                "scheduled_count": scheduled_count,
                "total_key_types": len(KeyType),
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            ip_address="system",
            user_agent="celery-worker"
        )
        
        logger.info(f"Automated key rotation check completed: {scheduled_count} rotations scheduled")
        
        return {
            "status": "completed",
            "scheduled_count": scheduled_count,
            "total_key_types": len(KeyType),
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Automated key rotation check failed: {e}")
        raise

@celery_app.task(bind=True, base=KeyRotationTask, name="execute_scheduled_key_rotations")
def execute_scheduled_key_rotations(self, max_rotations: int = 3):
    """
    Execute scheduled key rotations
    
    Executes pending key rotation events that have been scheduled.
    Processes a limited number of rotations per run to avoid system overload.
    """
    logger.info("Starting execution of scheduled key rotations")
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        key_service = get_key_rotation_service()
        
        # Get pending rotation events (this would need to be implemented in key service)
        # For now, we'll check each key type and execute if needed
        execution_results = {}
        executed_count = 0
        
        # Get all scheduled rotations from the service
        schedule = key_service.get_key_rotation_schedule()
        
        for key_type_str, details in schedule["key_types"].items():
            if executed_count >= max_rotations:
                logger.info(f"Reached maximum rotations limit ({max_rotations}), stopping")
                break
                
            # Check if there are pending rotations for this key type
            # This is a simplified check - in production, you'd have a proper event queue
            if details.get("pending_rotation_events"):
                try:
                    key_type = KeyType(key_type_str)
                    
                    # Get the pending event ID (simplified)
                    event_id = details["pending_rotation_events"][0]  # Get first pending
                    
                    logger.info(f"Executing rotation for {key_type.value}: {event_id}")
                    
                    # Execute the rotation
                    result = key_service.execute_key_rotation(
                        db=db,
                        event_id=event_id,
                        batch_size=1000  # Process in batches
                    )
                    
                    execution_results[key_type.value] = result
                    executed_count += 1
                    
                    # Log successful execution
                    audit_logger.log_event(
                        AuditEventType.SECURITY_EVENT,
                        user_id=None,
                        details={
                            "action": "key_rotation_executed",
                            "key_type": key_type.value,
                            "event_id": event_id,
                            "records_migrated": result["records_migrated"],
                            "duration_seconds": result["duration_seconds"],
                            "status": result["status"],
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        ip_address="system",
                        user_agent="celery-worker"
                    )
                    
                    logger.info(f"Key rotation completed for {key_type.value}: {result['records_migrated']} records migrated")
                    
                except Exception as e:
                    logger.error(f"Failed to execute rotation for {key_type_str}: {e}")
                    execution_results[key_type_str] = {
                        "status": "failed",
                        "error": str(e)
                    }
        
        logger.info(f"Scheduled key rotation execution completed: {executed_count} rotations executed")
        
        return {
            "status": "completed",
            "executed_count": executed_count,
            "max_rotations": max_rotations,
            "results": execution_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Scheduled key rotation execution failed: {e}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True, base=KeyRotationTask, name="key_rotation_cleanup")
def key_rotation_cleanup(self):
    """
    Key rotation cleanup task
    
    Cleans up expired and deprecated keys that have passed their
    grace period after rotation. Maintains security hygiene.
    """
    logger.info("Starting key rotation cleanup")
    
    try:
        key_service = get_key_rotation_service()
        result = key_service.cleanup_expired_keys()
        
        # Log cleanup results
        audit_logger.log_event(
            AuditEventType.SECURITY_EVENT,
            user_id=None,
            details={
                "action": "key_rotation_cleanup",
                "cleaned_keys": result["cleaned_keys"],
                "key_details": result["keys"],
                "cleanup_date": result["cleanup_date"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            ip_address="system",
            user_agent="celery-worker"
        )
        
        if result["cleaned_keys"] > 0:
            logger.info(f"Key cleanup completed: {result['cleaned_keys']} expired keys cleaned")
        else:
            logger.info("Key cleanup completed: No expired keys found")
        
        return {
            "status": "completed",
            "cleaned_keys": result["cleaned_keys"],
            "cleanup_date": result["cleanup_date"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Key rotation cleanup failed: {e}")
        raise

@celery_app.task(bind=True, base=KeyRotationTask, name="key_rotation_compliance_report")
def generate_key_rotation_compliance_report(self):
    """
    Generate key rotation compliance report
    
    Creates comprehensive compliance report covering key rotation status,
    policy adherence, and security recommendations.
    """
    logger.info("Generating key rotation compliance report")
    
    try:
        key_service = get_key_rotation_service()
        report = key_service.generate_key_rotation_report()
        
        # Log report generation
        audit_logger.log_event(
            AuditEventType.COMPLIANCE_EVENT,
            user_id=None,
            details={
                "action": "key_rotation_compliance_report",
                "total_key_types": len(report["key_details"]),
                "overdue_keys": len([k for k, v in report["key_details"].items() if v.get("is_overdue")]),
                "recommendations_count": len(report["recommendations"]),
                "report_generated_at": report["generated_at"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            ip_address="system",
            user_agent="celery-worker"
        )
        
        # Log warnings for overdue keys
        overdue_keys = [k for k, v in report["key_details"].items() if v.get("is_overdue")]
        if overdue_keys:
            logger.warning(f"Key rotation compliance report: {len(overdue_keys)} key types overdue: {overdue_keys}")
        
        logger.info("Key rotation compliance report generated successfully")
        
        return {
            "status": "completed",
            "report": report,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Key rotation compliance report generation failed: {e}")
        raise

@celery_app.task(bind=True, base=KeyRotationTask, name="emergency_key_rotation")
def emergency_key_rotation_task(self, key_type: str, reason: str = "emergency_security_incident"):
    """
    Emergency key rotation task
    
    Performs immediate key rotation for security incidents or when
    key compromise is suspected. Bypasses normal scheduling.
    """
    logger.warning(f"Starting emergency key rotation for {key_type}: {reason}")
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        key_service = get_key_rotation_service()
        
        # Validate key type
        try:
            key_type_enum = KeyType(key_type)
        except ValueError:
            raise ValueError(f"Invalid key type: {key_type}")
        
        # Schedule emergency rotation (forced)
        schedule_result = key_service.schedule_key_rotation(key_type_enum, force=True)
        
        if schedule_result["action"] != "rotation_scheduled":
            logger.warning(f"Emergency rotation not scheduled: {schedule_result['action']}")
            return {
                "status": "not_needed",
                "action": schedule_result["action"],
                "key_type": key_type,
                "reason": reason
            }
        
        # Execute rotation immediately
        event_id = schedule_result["event_id"]
        execute_result = key_service.execute_key_rotation(
            db=db,
            event_id=event_id,
            batch_size=500  # Smaller batches for emergency
        )
        
        # Log emergency rotation
        audit_logger.log_event(
            AuditEventType.SECURITY_EVENT,
            user_id=None,
            details={
                "action": "emergency_key_rotation",
                "key_type": key_type,
                "reason": reason,
                "event_id": event_id,
                "records_migrated": execute_result["records_migrated"],
                "duration_seconds": execute_result["duration_seconds"],
                "status": execute_result["status"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            ip_address="system",
            user_agent="celery-worker"
        )
        
        logger.warning(f"Emergency key rotation completed for {key_type}: {execute_result['records_migrated']} records migrated")
        
        return {
            "status": "completed",
            "key_type": key_type,
            "reason": reason,
            "event_id": event_id,
            "execution_result": execute_result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Emergency key rotation failed for {key_type}: {e}")
        # Log failure
        audit_logger.log_event(
            AuditEventType.SECURITY_EVENT,
            user_id=None,
            details={
                "action": "emergency_key_rotation_failed",
                "key_type": key_type,
                "reason": reason,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            ip_address="system",
            user_agent="celery-worker"
        )
        raise
    finally:
        db.close()

@celery_app.task(bind=True, base=KeyRotationTask, name="key_usage_monitoring")
def key_usage_monitoring_task(self):
    """
    Key usage monitoring task
    
    Monitors key usage patterns, detects anomalies, and generates
    alerts for suspicious key usage activity.
    """
    logger.info("Starting key usage monitoring")
    
    try:
        key_service = get_key_rotation_service()
        
        # Get all active keys and their usage stats
        usage_stats = {}
        alerts = []
        
        for key_type in KeyType:
            try:
                active_keys = key_service.get_active_keys(key_type)
                usage_stats[key_type.value] = {
                    "total_keys": len(active_keys),
                    "keys": active_keys
                }
                
                # Check for usage anomalies
                for key in active_keys:
                    # Example anomaly detection (customize based on your needs)
                    if key.get("usage_count", 0) > 1000000:  # Very high usage
                        alerts.append(f"High usage detected for {key_type.value} key {key['key_id']}: {key['usage_count']} operations")
                    
                    # Check for old unused keys
                    if key.get("usage_count", 0) == 0 and key.get("age_days", 0) > 7:
                        alerts.append(f"Unused key detected for {key_type.value}: {key['key_id']} ({key['age_days']} days old)")
                
            except Exception as e:
                logger.error(f"Error monitoring usage for {key_type.value}: {e}")
                usage_stats[key_type.value] = {"error": str(e)}
        
        # Log monitoring results
        audit_logger.log_event(
            AuditEventType.SECURITY_EVENT,
            user_id=None,
            details={
                "action": "key_usage_monitoring",
                "total_key_types": len(KeyType),
                "alerts_count": len(alerts),
                "alerts": alerts[:10],  # Limit alerts in log
                "usage_summary": {k: {"total_keys": v.get("total_keys", 0)} for k, v in usage_stats.items()},
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            ip_address="system",
            user_agent="celery-worker"
        )
        
        if alerts:
            logger.warning(f"Key usage monitoring: {len(alerts)} alerts generated")
            for alert in alerts:
                logger.warning(f"Key usage alert: {alert}")
        else:
            logger.info("Key usage monitoring: No anomalies detected")
        
        return {
            "status": "completed",
            "usage_stats": usage_stats,
            "alerts": alerts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Key usage monitoring failed: {e}")
        raise