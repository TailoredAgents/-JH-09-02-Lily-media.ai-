"""
Automated subscription cleanup tasks for billing state management
Part of P1-5c: Add automated subscription cleanup jobs

Handles:
- Expired trial cleanup
- Overdue payment handling  
- Cancelled subscription cleanup
- Stripe subscription sync
- Plan downgrade enforcement
"""

from backend.core.suppress_warnings import suppress_third_party_warnings
suppress_third_party_warnings()

from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.db.database import SessionLocal
from backend.db.models import User, Plan
from backend.services.subscription_service import SubscriptionService, SubscriptionTier
from backend.services.plan_service import PlanService
from backend.services.stripe_service import StripeService
from backend.core.config import get_settings

logger = get_task_logger(__name__)
settings = get_settings()


@shared_task(name="cleanup_expired_trials")
def cleanup_expired_trials() -> Dict[str, Any]:
    """
    Clean up users whose trial periods have expired
    Sets status to 'past_due' and downgrades to free plan
    """
    db = SessionLocal()
    
    try:
        # Find users with expired trials
        now = datetime.now(timezone.utc)
        
        # Users whose subscription_end_date has passed and still on trial/active status
        expired_users = (
            db.query(User)
            .filter(
                and_(
                    User.subscription_end_date < now,
                    User.subscription_status.in_(["active", "trialing"]),
                    User.is_active == True
                )
            )
            .all()
        )
        
        results = {
            "total_expired": len(expired_users),
            "processed": 0,
            "downgraded_to_free": 0,
            "stripe_sync_needed": [],
            "errors": []
        }
        
        plan_service = PlanService(db)
        free_plan = plan_service.get_free_plan()
        
        for user in expired_users:
            try:
                # Check if this is truly expired (not a Stripe sync issue)
                if user.stripe_subscription_id:
                    # Mark for Stripe verification
                    results["stripe_sync_needed"].append({
                        "user_id": user.id,
                        "stripe_subscription_id": user.stripe_subscription_id,
                        "expired_date": user.subscription_end_date.isoformat()
                    })
                    continue
                
                # Local trial expired - downgrade to free
                user.subscription_status = "expired"
                user.plan_id = free_plan.id if free_plan else None
                user.updated_at = datetime.now(timezone.utc)
                
                results["downgraded_to_free"] += 1
                results["processed"] += 1
                
                logger.info(f"Downgraded expired trial user {user.id} to free plan")
                
            except Exception as e:
                logger.error(f"Failed to cleanup expired trial for user {user.id}: {e}")
                results["errors"].append({
                    "user_id": user.id,
                    "error": str(e)
                })
        
        db.commit()
        
        logger.info(f"Trial cleanup completed: {results['processed']} users processed")
        return results
        
    except Exception as e:
        logger.error(f"Trial cleanup job failed: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task(name="handle_overdue_subscriptions")
def handle_overdue_subscriptions() -> Dict[str, Any]:
    """
    Handle subscriptions that are past due
    Implements grace period before suspension
    """
    db = SessionLocal()
    
    try:
        now = datetime.now(timezone.utc)
        
        # Grace period: 3 days after end date before suspension
        grace_period_cutoff = now - timedelta(days=3)
        
        # Find subscriptions past grace period
        overdue_users = (
            db.query(User)
            .filter(
                and_(
                    User.subscription_end_date < grace_period_cutoff,
                    User.subscription_status == "past_due",
                    User.is_active == True
                )
            )
            .all()
        )
        
        results = {
            "total_overdue": len(overdue_users),
            "suspended": 0,
            "stripe_webhooks_needed": [],
            "errors": []
        }
        
        plan_service = PlanService(db)
        free_plan = plan_service.get_free_plan()
        
        for user in overdue_users:
            try:
                # Check if user has Stripe subscription - handle via webhook
                if user.stripe_subscription_id:
                    results["stripe_webhooks_needed"].append({
                        "user_id": user.id,
                        "stripe_subscription_id": user.stripe_subscription_id,
                        "overdue_since": user.subscription_end_date.isoformat()
                    })
                    continue
                
                # Local subscription overdue - suspend to free tier
                user.subscription_status = "suspended"
                user.plan_id = free_plan.id if free_plan else None
                user.updated_at = datetime.now(timezone.utc)
                
                results["suspended"] += 1
                
                logger.warning(f"Suspended overdue user {user.id} - downgraded to free plan")
                
            except Exception as e:
                logger.error(f"Failed to handle overdue subscription for user {user.id}: {e}")
                results["errors"].append({
                    "user_id": user.id,
                    "error": str(e)
                })
        
        db.commit()
        
        logger.info(f"Overdue subscription handling completed: {results['suspended']} users suspended")
        return results
        
    except Exception as e:
        logger.error(f"Overdue subscription job failed: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task(name="cleanup_cancelled_subscriptions")
def cleanup_cancelled_subscriptions() -> Dict[str, Any]:
    """
    Clean up users with cancelled subscriptions
    Ensures they're moved to appropriate free tier
    """
    db = SessionLocal()
    
    try:
        now = datetime.now(timezone.utc)
        
        # Find cancelled subscriptions that have reached end date
        cancelled_users = (
            db.query(User)
            .filter(
                and_(
                    User.subscription_status == "cancelled",
                    or_(
                        User.subscription_end_date < now,
                        User.subscription_end_date.is_(None)
                    ),
                    User.is_active == True
                )
            )
            .all()
        )
        
        results = {
            "total_cancelled": len(cancelled_users),
            "processed": 0,
            "moved_to_free": 0,
            "errors": []
        }
        
        plan_service = PlanService(db)
        free_plan = plan_service.get_free_plan()
        
        for user in cancelled_users:
            try:
                # Move cancelled subscription to free tier
                old_plan_id = user.plan_id
                
                user.subscription_status = "free"
                user.plan_id = free_plan.id if free_plan else None
                user.stripe_subscription_id = None  # Clear Stripe reference
                user.subscription_end_date = None
                user.updated_at = datetime.now(timezone.utc)
                
                results["moved_to_free"] += 1
                results["processed"] += 1
                
                logger.info(f"Moved cancelled user {user.id} from plan {old_plan_id} to free plan")
                
            except Exception as e:
                logger.error(f"Failed to cleanup cancelled subscription for user {user.id}: {e}")
                results["errors"].append({
                    "user_id": user.id,
                    "error": str(e)
                })
        
        db.commit()
        
        logger.info(f"Cancelled subscription cleanup completed: {results['processed']} users processed")
        return results
        
    except Exception as e:
        logger.error(f"Cancelled subscription cleanup job failed: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task(name="sync_stripe_subscription_status")
def sync_stripe_subscription_status() -> Dict[str, Any]:
    """
    Sync subscription status with Stripe for users with active Stripe subscriptions
    Ensures local database matches Stripe state
    """
    db = SessionLocal()
    
    try:
        # Find users with Stripe subscriptions that may need sync
        stripe_users = (
            db.query(User)
            .filter(
                and_(
                    User.stripe_subscription_id.isnot(None),
                    User.subscription_status.in_(["active", "past_due", "trialing"]),
                    User.is_active == True
                )
            )
            .limit(100)  # Process in batches to avoid Stripe rate limits
            .all()
        )
        
        results = {
            "total_checked": len(stripe_users),
            "updated": 0,
            "cancelled": 0,
            "errors": [],
            "stripe_api_calls": 0
        }
        
        if not stripe_users:
            return results
        
        stripe_service = StripeService()
        plan_service = PlanService(db)
        
        for user in stripe_users:
            try:
                # Get subscription status from Stripe
                try:
                    subscription_info = stripe_service.get_subscription_info(user)
                    results["stripe_api_calls"] += 1
                    
                    if not subscription_info or not subscription_info.get("subscription"):
                        # Subscription not found in Stripe - mark as cancelled
                        user.subscription_status = "cancelled"
                        user.stripe_subscription_id = None
                        results["cancelled"] += 1
                        logger.warning(f"Stripe subscription not found for user {user.id} - marked as cancelled")
                        continue
                    
                    stripe_subscription = subscription_info["subscription"]
                    stripe_status = stripe_subscription.get("status", "cancelled")
                    stripe_end_timestamp = stripe_subscription.get("current_period_end")
                    
                    if stripe_end_timestamp:
                        stripe_end = datetime.fromtimestamp(stripe_end_timestamp, timezone.utc)
                    else:
                        stripe_end = user.subscription_end_date
                        
                except Exception as stripe_error:
                    logger.error(f"Failed to get Stripe subscription for user {user.id}: {stripe_error}")
                    # Continue to next user on Stripe API error
                    results["errors"].append({
                        "user_id": user.id,
                        "stripe_subscription_id": user.stripe_subscription_id,
                        "error": f"Stripe API error: {str(stripe_error)}"
                    })
                    continue
                
                # Update local status to match Stripe
                status_mapping = {
                    "active": "active",
                    "past_due": "past_due", 
                    "canceled": "cancelled",
                    "cancelled": "cancelled",
                    "unpaid": "past_due",
                    "incomplete": "past_due",
                    "trialing": "active"  # We consider trialing as active
                }
                
                new_status = status_mapping.get(stripe_status, "cancelled")
                
                if user.subscription_status != new_status or user.subscription_end_date != stripe_end:
                    user.subscription_status = new_status
                    user.subscription_end_date = stripe_end
                    user.updated_at = datetime.now(timezone.utc)
                    results["updated"] += 1
                    
                    logger.info(f"Updated user {user.id} subscription: {stripe_status} -> {new_status}")
                
            except Exception as e:
                logger.error(f"Failed to sync Stripe subscription for user {user.id}: {e}")
                results["errors"].append({
                    "user_id": user.id,
                    "stripe_subscription_id": user.stripe_subscription_id,
                    "error": str(e)
                })
        
        db.commit()
        
        logger.info(f"Stripe sync completed: {results['updated']} users updated, {results['stripe_api_calls']} API calls")
        return results
        
    except Exception as e:
        logger.error(f"Stripe sync job failed: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task(name="enforce_plan_limits")
def enforce_plan_limits() -> Dict[str, Any]:
    """
    Enforce plan limits for users who may have exceeded their quotas
    Disables features or downgrades users who exceed limits
    """
    db = SessionLocal()
    
    try:
        # Find users who may be over limits (active users only)
        active_users = (
            db.query(User)
            .filter(
                and_(
                    User.is_active == True,
                    User.subscription_status.in_(["active", "free"])
                )
            )
            .limit(1000)  # Process in batches
            .all()
        )
        
        results = {
            "total_checked": len(active_users),
            "enforced": 0,
            "warnings_sent": 0,
            "errors": []
        }
        
        plan_service = PlanService(db)
        
        for user in active_users:
            try:
                capabilities = plan_service.get_user_capabilities(user.id)
                
                # Check various plan limits (this would be expanded based on usage tracking)
                limits_exceeded = []
                
                # For now, just ensure plan consistency
                if user.plan_id:
                    plan = db.query(Plan).filter(Plan.id == user.plan_id).first()
                    if plan:
                        # Ensure subscription status matches plan type
                        if plan.name == "free" and user.subscription_status not in ["free", "expired"]:
                            user.subscription_status = "free"
                            results["enforced"] += 1
                            logger.info(f"Corrected subscription status for free plan user {user.id}")
                        
                        elif plan.name != "free" and user.subscription_status == "free":
                            # User has paid plan but free status - check if subscription expired
                            if user.subscription_end_date and user.subscription_end_date < datetime.now(timezone.utc):
                                # Move to free plan
                                free_plan = plan_service.get_free_plan()
                                user.plan_id = free_plan.id if free_plan else None
                                user.subscription_status = "expired"
                                results["enforced"] += 1
                                logger.info(f"Downgraded expired user {user.id} to free plan")
                
            except Exception as e:
                logger.error(f"Failed to enforce plan limits for user {user.id}: {e}")
                results["errors"].append({
                    "user_id": user.id,
                    "error": str(e)
                })
        
        db.commit()
        
        logger.info(f"Plan limit enforcement completed: {results['enforced']} users enforced")
        return results
        
    except Exception as e:
        logger.error(f"Plan limit enforcement job failed: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task(name="cleanup_orphaned_subscriptions")
def cleanup_orphaned_subscriptions() -> Dict[str, Any]:
    """
    Clean up orphaned subscription data
    Removes stale Stripe references and inconsistent states
    """
    db = SessionLocal()
    
    try:
        results = {
            "orphaned_stripe_refs": 0,
            "inconsistent_states": 0,
            "cleaned": 0,
            "errors": []
        }
        
        # Find users with Stripe customer ID but no subscription ID
        orphaned_customers = (
            db.query(User)
            .filter(
                and_(
                    User.stripe_customer_id.isnot(None),
                    User.stripe_subscription_id.is_(None),
                    User.subscription_status.in_(["active", "past_due", "trialing"])
                )
            )
            .all()
        )
        
        for user in orphaned_customers:
            try:
                # Clean up inconsistent state
                user.subscription_status = "free"
                user.subscription_end_date = None
                results["orphaned_stripe_refs"] += 1
                results["cleaned"] += 1
                
                logger.info(f"Cleaned orphaned Stripe customer reference for user {user.id}")
                
            except Exception as e:
                logger.error(f"Failed to clean orphaned subscription for user {user.id}: {e}")
                results["errors"].append({
                    "user_id": user.id,
                    "error": str(e)
                })
        
        # Find users with inconsistent subscription states
        inconsistent_users = (
            db.query(User)
            .filter(
                and_(
                    User.subscription_status == "active",
                    User.subscription_end_date < datetime.now(timezone.utc),
                    User.stripe_subscription_id.is_(None)
                )
            )
            .all()
        )
        
        for user in inconsistent_users:
            try:
                # Fix inconsistent state
                user.subscription_status = "expired"
                results["inconsistent_states"] += 1
                results["cleaned"] += 1
                
                logger.info(f"Fixed inconsistent subscription state for user {user.id}")
                
            except Exception as e:
                logger.error(f"Failed to fix inconsistent state for user {user.id}: {e}")
                results["errors"].append({
                    "user_id": user.id,
                    "error": str(e)
                })
        
        db.commit()
        
        logger.info(f"Orphaned subscription cleanup completed: {results['cleaned']} issues resolved")
        return results
        
    except Exception as e:
        logger.error(f"Orphaned subscription cleanup job failed: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# Batch cleanup task that runs multiple cleanup operations
@shared_task(name="daily_subscription_maintenance")
def daily_subscription_maintenance() -> Dict[str, Any]:
    """
    Daily subscription maintenance - runs all cleanup tasks in sequence
    Orchestrates the complete subscription cleanup workflow
    """
    results = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "tasks_completed": [],
        "total_errors": 0
    }
    
    # List of cleanup tasks to run
    cleanup_tasks = [
        ("expired_trials", cleanup_expired_trials),
        ("overdue_subscriptions", handle_overdue_subscriptions),
        ("cancelled_subscriptions", cleanup_cancelled_subscriptions),
        ("stripe_sync", sync_stripe_subscription_status),
        ("plan_limits", enforce_plan_limits),
        ("orphaned_subscriptions", cleanup_orphaned_subscriptions)
    ]
    
    for task_name, task_func in cleanup_tasks:
        try:
            logger.info(f"Starting subscription cleanup task: {task_name}")
            task_result = task_func()
            
            results["tasks_completed"].append({
                "task": task_name,
                "success": task_result.get("success", True),
                "result": task_result
            })
            
            if not task_result.get("success", True):
                results["total_errors"] += 1
            
            logger.info(f"Completed subscription cleanup task: {task_name}")
            
        except Exception as e:
            logger.error(f"Failed to run subscription cleanup task {task_name}: {e}")
            results["tasks_completed"].append({
                "task": task_name,
                "success": False,
                "error": str(e)
            })
            results["total_errors"] += 1
    
    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    results["success"] = results["total_errors"] == 0
    
    logger.info(f"Daily subscription maintenance completed with {results['total_errors']} errors")
    return results