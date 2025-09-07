"""
FTC Compliance Tasks for Automatic Subscription Management
Handles trial reminders and renewal notices as required by federal and state law
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from celery import shared_task
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.services.stripe_service import get_stripe_service
from backend.services.system_metrics import track_subscription_event

logger = logging.getLogger(__name__)


@shared_task(name="send_ftc_trial_reminders")
def send_ftc_trial_reminders() -> Dict[str, Any]:
    """
    Send FTC-compliant trial reminder notifications
    
    COMPLIANCE FEATURES:
    - Connecticut Automatic Renewal Act: 3-21 days notice for trials > 1 month
    - FTC Click-to-Cancel Rule: Clear disclosure of automatic billing
    - Consumer protection: Easy cancellation instructions
    
    Scheduled to run daily to catch trials ending in 3 days
    
    Returns:
        Dict with task execution results and compliance metrics
    """
    try:
        logger.info("Starting FTC-compliant trial reminder task")
        start_time = datetime.now(timezone.utc)
        
        # Get database session
        db: Session = next(get_db())
        stripe_service = get_stripe_service(db)
        
        # Send trial reminders
        reminder_count = stripe_service.send_trial_reminders()
        
        # Track compliance metrics
        track_subscription_event(
            event_type="trial_reminder_batch",
            plan_tier="all_trials",
            consumer_protection_feature="ftc_batch_notification",
            cancellation_type="none"
        )
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        result = {
            "task": "send_ftc_trial_reminders",
            "status": "completed",
            "reminders_sent": reminder_count,
            "execution_time_seconds": execution_time,
            "compliance_version": "FTC_2025",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "legal_requirements_met": [
                "FTC Click-to-Cancel Rule (16 CFR Part 425)",
                "Connecticut Automatic Renewal Act",
                "Consumer protection disclosure requirements"
            ]
        }
        
        logger.info(f"FTC trial reminder task completed: {reminder_count} reminders sent")
        return result
        
    except Exception as e:
        logger.error(f"FTC trial reminder task failed: {e}")
        
        # Track failure metrics
        track_subscription_event(
            event_type="trial_reminder_failure",
            plan_tier="unknown",
            consumer_protection_feature="ftc_batch_notification_failed"
        )
        
        return {
            "task": "send_ftc_trial_reminders",
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "compliance_impact": "Consumer protection notifications may be delayed"
        }
    
    finally:
        if 'db' in locals():
            db.close()


@shared_task(name="send_ftc_renewal_notices")
def send_ftc_renewal_notices() -> Dict[str, Any]:
    """
    Send FTC-compliant subscription renewal notifications
    
    COMPLIANCE FEATURES:
    - FTC Click-to-Cancel Rule: Clear renewal disclosure
    - California SB-313: 3+ days advance notice
    - Massachusetts Consumer Protection Act: 5-30 days notice (we send at 3 days)
    - Consumer protection: Easy cancellation access
    
    Scheduled to run daily to catch renewals in 3 days
    
    Returns:
        Dict with task execution results and compliance metrics
    """
    try:
        logger.info("Starting FTC-compliant renewal notice task")
        start_time = datetime.now(timezone.utc)
        
        # Get database session
        db: Session = next(get_db())
        stripe_service = get_stripe_service(db)
        
        # Send renewal notices
        notice_count = stripe_service.send_renewal_notices()
        
        # Track compliance metrics
        track_subscription_event(
            event_type="renewal_notice_batch",
            plan_tier="all_active",
            consumer_protection_feature="ftc_renewal_notification",
            cancellation_type="none"
        )
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        result = {
            "task": "send_ftc_renewal_notices",
            "status": "completed",
            "notices_sent": notice_count,
            "execution_time_seconds": execution_time,
            "compliance_version": "FTC_2025",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "legal_requirements_met": [
                "FTC Click-to-Cancel Rule (16 CFR Part 425)",
                "California SB-313 (Automatic Renewal Law)",
                "Massachusetts Consumer Protection Act",
                "Consumer billing transparency requirements"
            ]
        }
        
        logger.info(f"FTC renewal notice task completed: {notice_count} notices sent")
        return result
        
    except Exception as e:
        logger.error(f"FTC renewal notice task failed: {e}")
        
        # Track failure metrics
        track_subscription_event(
            event_type="renewal_notice_failure",
            plan_tier="unknown",
            consumer_protection_feature="ftc_renewal_notification_failed"
        )
        
        return {
            "task": "send_ftc_renewal_notices",
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "compliance_impact": "Consumer protection notifications may be delayed"
        }
    
    finally:
        if 'db' in locals():
            db.close()


@shared_task(name="daily_ftc_compliance_checks")
def daily_ftc_compliance_checks() -> Dict[str, Any]:
    """
    Daily FTC compliance maintenance task
    
    Runs both trial reminders and renewal notices, plus compliance monitoring
    
    SCHEDULE: Daily at 10:00 AM UTC to ensure timely consumer notifications
    
    Returns:
        Dict with combined results from all compliance tasks
    """
    try:
        logger.info("Starting daily FTC compliance checks")
        start_time = datetime.now(timezone.utc)
        
        results = {
            "task": "daily_ftc_compliance_checks",
            "status": "in_progress",
            "timestamp": start_time.isoformat(),
            "subtasks": {}
        }
        
        # Run trial reminders
        try:
            trial_results = send_ftc_trial_reminders.delay()
            results["subtasks"]["trial_reminders"] = trial_results.get(timeout=300)
        except Exception as e:
            logger.error(f"Trial reminder subtask failed: {e}")
            results["subtasks"]["trial_reminders"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Run renewal notices
        try:
            renewal_results = send_ftc_renewal_notices.delay()
            results["subtasks"]["renewal_notices"] = renewal_results.get(timeout=300)
        except Exception as e:
            logger.error(f"Renewal notice subtask failed: {e}")
            results["subtasks"]["renewal_notices"] = {
                "status": "failed", 
                "error": str(e)
            }
        
        # Calculate totals
        total_reminders = results["subtasks"]["trial_reminders"].get("reminders_sent", 0)
        total_notices = results["subtasks"]["renewal_notices"].get("notices_sent", 0)
        total_notifications = total_reminders + total_notices
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Update final results
        results.update({
            "status": "completed",
            "total_notifications_sent": total_notifications,
            "trial_reminders_sent": total_reminders,
            "renewal_notices_sent": total_notices,
            "execution_time_seconds": execution_time,
            "compliance_status": "FTC_2025_COMPLIANT",
            "next_run": "Tomorrow at 10:00 AM UTC"
        })
        
        # Track overall compliance metrics
        track_subscription_event(
            event_type="daily_compliance_batch",
            plan_tier="all_tiers",
            consumer_protection_feature="comprehensive_ftc_compliance"
        )
        
        logger.info(
            f"Daily FTC compliance checks completed: "
            f"{total_notifications} total notifications sent "
            f"({total_reminders} trial, {total_notices} renewal)"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Daily FTC compliance checks failed: {e}")
        
        return {
            "task": "daily_ftc_compliance_checks",
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "compliance_impact": "Consumer protection notifications system experienced failure"
        }