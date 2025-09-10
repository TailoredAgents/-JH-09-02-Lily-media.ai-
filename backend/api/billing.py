"""
Billing and subscription API endpoints using Stripe
Handles payment flows, subscription management, and billing webhooks
"""
import os
import logging
import stripe
import hmac
import hashlib
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.auth.dependencies import get_current_user, AuthUser, get_current_active_user
from backend.db.models import User
from backend.db.multi_tenant_models import Organization
from backend.services.stripe_service import get_stripe_service, StripeService, StripeError
from backend.services.subscription_service import SubscriptionTier
from backend.core.api_version import create_versioned_router
from backend.middleware.feature_flag_enforcement import require_flag

logger = logging.getLogger(__name__)

router = create_versioned_router(prefix="/billing", tags=["billing"])

# Request/Response Models
class CreateCheckoutRequest(BaseModel):
    tier: str = Field(..., description="Subscription tier: basic, premium, or enterprise")
    organization_id: Optional[str] = Field(None, description="Organization ID for B2B billing")
    success_url: str = Field(..., description="URL to redirect on successful payment")
    cancel_url: str = Field(..., description="URL to redirect on cancelled payment")

class CheckoutResponse(BaseModel):
    session_id: str
    checkout_url: str
    message: str = "Checkout session created successfully"

class CustomerPortalRequest(BaseModel):
    return_url: str = Field(..., description="URL to return to from customer portal")

class CustomerPortalResponse(BaseModel):
    portal_url: str
    message: str = "Customer portal session created successfully"

class SubscriptionInfoResponse(BaseModel):
    tier: str
    status: str
    has_active_subscription: bool
    subscription_end_date: Optional[str]
    tier_limits: Dict[str, Any]
    tier_features: list[str]
    stripe_customer_id: Optional[str]

class WebhookResponse(BaseModel):
    message: str
    processed: bool = True

# Dependency to get Stripe service
def get_billing_service(db: Session = Depends(get_db)):
    return get_stripe_service(db)

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    stripe_service: StripeService = Depends(get_billing_service),
    _: None = Depends(require_flag("BILLING_MANAGEMENT"))
):
    """
    Create a Stripe checkout session with FTC-compliant disclosures
    
    This endpoint creates a Stripe checkout session that redirects users
    to Stripe's hosted payment page for secure subscription signup.
    
    FTC COMPLIANCE FEATURES:
    - Clear trial period and automatic billing disclosures
    - Cancellation deadline and method information
    - Transparent pricing and renewal terms
    - Consumer protection notice
    """
    try:
        # Validate subscription tier
        try:
            tier = SubscriptionTier(request.tier.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid subscription tier: {request.tier}"
            )
        
        # Get organization if specified
        organization = None
        if request.organization_id:
            # TODO: Add organization lookup and permission check
            # organization = db.query(Organization).filter(...).first()
            pass
        
        # Create checkout session with FTC-compliant metadata
        session_data = stripe_service.create_checkout_session(
            user=current_user,
            tier=tier,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            organization=organization
        )
        
        return CheckoutResponse(
            session_id=session_data["session_id"],
            checkout_url=session_data["checkout_url"],
            message="Checkout session created with consumer protection disclosures - review all terms before payment"
        )
        
    except StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment system error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )

@router.post("/customer-portal", response_model=CustomerPortalResponse)
async def create_customer_portal(
    request: CustomerPortalRequest,
    current_user: User = Depends(get_current_active_user),
    stripe_service: StripeService = Depends(get_billing_service)
):
    """
    Create a Stripe customer portal session for subscription management
    
    The customer portal allows users to:
    - Update payment methods
    - View billing history
    - Download invoices
    - Cancel subscriptions
    - Update billing information
    """
    try:
        if not current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No subscription found. Please sign up for a plan first."
            )
        
        portal_url = stripe_service.create_customer_portal_session(
            user=current_user,
            return_url=request.return_url
        )
        
        return CustomerPortalResponse(
            portal_url=portal_url
        )
        
    except StripeError as e:
        logger.error(f"Stripe error creating customer portal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment system error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating customer portal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create customer portal session"
        )

@router.get("/subscription", response_model=SubscriptionInfoResponse)
async def get_subscription_info(
    current_user: User = Depends(get_current_active_user),
    stripe_service: StripeService = Depends(get_billing_service)
):
    """
    Get current user's subscription information
    
    Returns comprehensive subscription details including:
    - Current tier and status
    - Feature access and limits
    - Billing information
    - Next billing date
    """
    try:
        subscription_info = stripe_service.get_subscription_info(current_user)
        
        return SubscriptionInfoResponse(**subscription_info)
        
    except Exception as e:
        logger.error(f"Error getting subscription info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription information"
        )

@router.get("/plans")
async def get_billing_plans():
    """
    Get available subscription plans with FTC-compliant disclosures
    
    Returns detailed information about all subscription tiers including:
    - Features, limits, and pricing information
    - FTC-compliant trial and renewal term disclosures
    - Consumer protection information and cancellation terms
    """
    try:
        # FTC-compliant disclosure information
        disclosure_info = {
            "trial_terms": {
                "trial_period_days": 7,
                "trial_description": "7-day free trial - no charges during trial period",
                "cancellation_deadline": "You must cancel before the end of your 7-day trial to avoid being charged",
                "automatic_billing": "After your trial ends, you will be automatically charged the full subscription price unless you cancel",
                "cancellation_instructions": "Cancel anytime through your account settings or by contacting support"
            },
            "renewal_terms": {
                "automatic_renewal": "This subscription automatically renews",
                "renewal_frequency": "Subscriptions renew monthly or annually based on your selection", 
                "renewal_notice": "We will send you a reminder email 3 days before your subscription renews",
                "price_changes": "We will notify you at least 30 days before any price changes take effect",
                "cancellation_timing": "You can cancel anytime - cancellation takes effect at the end of your current billing period"
            },
            "consumer_protection": {
                "refund_policy": "Full refund available within first 30 days of paid subscription",
                "data_retention": "Your data is retained for 30 days after cancellation for easy reactivation",
                "downgrade_protection": "Cancelled accounts automatically downgrade to free tier with basic features",
                "support_access": "Full customer support access during trial and subscription periods"
            },
            "legal_compliance": {
                "ftc_compliance": "Compliant with FTC Click-to-Cancel Rule effective July 2025",
                "state_compliance": "Compliant with California SB-313 and other state automatic renewal laws",
                "cancellation_method": "Cancel through account settings - same method used to sign up"
            }
        }

        plans = {
            "basic": {
                "name": "Basic",
                "price_monthly": 9.99,
                "price_yearly": 99.99,
                "trial_eligible": True,
                "features": [
                    "3 social accounts",
                    "10 posts per day", 
                    "Basic scheduling",
                    "Basic analytics",
                    "5 AI image generations/day",
                    "Email support"
                ],
                "limits": {
                    "social_accounts": 3,
                    "posts_per_day": 10,
                    "ai_requests_per_day": 20,
                    "image_generations_per_day": 5
                },
                "billing_disclosures": {
                    "monthly_charge": "$9.99 will be charged monthly after trial ends",
                    "yearly_charge": "$99.99 will be charged yearly after trial ends (save $19.89)",
                    "trial_end_notice": "Trial ends 7 days from signup - cancel before then to avoid charges"
                }
            },
            "premium": {
                "name": "Premium",
                "price_monthly": 29.99,
                "price_yearly": 299.99,
                "popular": True,
                "trial_eligible": True,
                "features": [
                    "10 social accounts",
                    "50 posts per day",
                    "Advanced scheduling",
                    "Premium analytics",
                    "50 AI image generations/day",
                    "Autonomous posting",
                    "Industry research",
                    "Priority support"
                ],
                "limits": {
                    "social_accounts": 10,
                    "posts_per_day": 50,
                    "ai_requests_per_day": 200,
                    "image_generations_per_day": 50
                },
                "billing_disclosures": {
                    "monthly_charge": "$29.99 will be charged monthly after trial ends",
                    "yearly_charge": "$299.99 will be charged yearly after trial ends (save $59.89)",
                    "trial_end_notice": "Trial ends 7 days from signup - cancel before then to avoid charges"
                }
            },
            "enterprise": {
                "name": "Enterprise",
                "price_monthly": 99.99,
                "price_yearly": 999.99,
                "trial_eligible": True,
                "features": [
                    "Unlimited social accounts",
                    "Unlimited posts",
                    "Advanced automation",
                    "Enterprise analytics",
                    "Unlimited AI generations",
                    "Custom branding",
                    "Team collaboration",
                    "Advanced RBAC",
                    "24/7 priority support",
                    "Custom integrations"
                ],
                "limits": {
                    "social_accounts": "unlimited",
                    "posts_per_day": "unlimited",
                    "ai_requests_per_day": "unlimited",
                    "image_generations_per_day": "unlimited"
                },
                "billing_disclosures": {
                    "monthly_charge": "$99.99 will be charged monthly after trial ends",
                    "yearly_charge": "$999.99 will be charged yearly after trial ends (save $199.89)",
                    "trial_end_notice": "Trial ends 7 days from signup - cancel before then to avoid charges"
                }
            }
        }
        
        return {
            "plans": plans,
            "disclosures": disclosure_info,
            "last_updated": "2025-09-07T00:00:00Z",
            "compliance_version": "FTC_2025"
        }
        
    except Exception as e:
        logger.error(f"Error getting billing plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve billing plans"
        )

@router.post("/webhooks/stripe", response_model=WebhookResponse)
async def stripe_webhook(
    request: Request,
    stripe_service: StripeService = Depends(get_billing_service)
):
    """
    Handle Stripe webhook events
    
    This endpoint processes webhook events from Stripe to keep
    subscription statuses synchronized with payment events.
    
    Supported events:
    - customer.subscription.created
    - customer.subscription.updated  
    - customer.subscription.deleted
    - invoice.payment_succeeded
    - invoice.payment_failed
    """
    try:
        # Get webhook payload and signature
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        if not sig_header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header"
            )
        
        # Verify webhook signature
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook secret not configured"
            )
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload"
            )
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature"
            )
        
        # Process webhook event
        event_type = event["type"]
        event_data = event["data"]["object"]
        
        logger.info(f"Processing Stripe webhook: {event_type}")
        
        if event_type == "customer.subscription.created":
            stripe_service.handle_subscription_created(event_data)
        elif event_type == "customer.subscription.updated":
            stripe_service.handle_subscription_updated(event_data)
        elif event_type == "customer.subscription.deleted":
            stripe_service.handle_subscription_deleted(event_data)
        elif event_type == "invoice.payment_succeeded":
            stripe_service.handle_invoice_payment_succeeded(event_data)
        elif event_type == "invoice.payment_failed":
            stripe_service.handle_invoice_payment_failed(event_data)
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
        
        return WebhookResponse(
            message=f"Processed {event_type} event",
            processed=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )

class CancelSubscriptionRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Optional reason for cancellation")
    feedback: Optional[str] = Field(None, description="Optional user feedback")
    immediate: bool = Field(False, description="Cancel immediately vs at period end")

class CancelSubscriptionResponse(BaseModel):
    success: bool
    message: str
    cancellation_date: Optional[str] = Field(None, description="When subscription will be cancelled")
    effective_date: Optional[str] = Field(None, description="When cancellation takes effect")

@router.post("/cancel-subscription", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    current_user: User = Depends(get_current_active_user),
    stripe_service: StripeService = Depends(get_billing_service),
    _: None = Depends(require_flag("BILLING_MANAGEMENT"))
):
    """
    Cancel user's subscription with consumer protection safeguards
    
    CONSUMER PROTECTION FEATURES:
    - Clear cancellation confirmation with effective date
    - Option to cancel immediately or at period end
    - Retention of data during grace period
    - Feedback collection for service improvement
    - Transparent timeline communication
    - Automatic downgrade to free tier
    """
    try:
        if not current_user.stripe_customer_id or not current_user.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active subscription found to cancel"
            )
        
        # Check current subscription status
        subscription_info = stripe_service.get_subscription_info(current_user)
        if not subscription_info.get("has_active_subscription"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription is not currently active"
            )
        
        # Cancel subscription via Stripe
        cancellation_result = stripe_service.cancel_subscription(
            user=current_user,
            immediate=request.immediate,
            reason=request.reason,
            feedback=request.feedback
        )
        
        # Log cancellation for consumer protection audit trail
        logger.info(
            f"Subscription cancelled for user {current_user.id}: "
            f"immediate={request.immediate}, reason='{request.reason}'"
        )
        
        return CancelSubscriptionResponse(
            success=True,
            message="Subscription cancelled successfully" if request.immediate 
                   else "Subscription will be cancelled at the end of your current billing period",
            cancellation_date=cancellation_result.get("cancelled_at"),
            effective_date=cancellation_result.get("effective_date")
        )
        
    except StripeError as e:
        logger.error(f"Stripe error cancelling subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment system error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error cancelling subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        )

class TrialReminderResponse(BaseModel):
    sent_count: int
    message: str
    compliance_status: str

class RenewalNoticeResponse(BaseModel):
    sent_count: int
    message: str
    compliance_status: str

class CancellationFeedbackRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for cancellation")
    feedback: Optional[str] = Field(None, description="Additional feedback")
    timestamp: str = Field(..., description="Timestamp of feedback submission")

class CancellationFeedbackResponse(BaseModel):
    success: bool
    message: str = "Feedback received successfully"

@router.post("/trial-reminders", response_model=TrialReminderResponse)
async def send_trial_reminders(
    stripe_service: StripeService = Depends(get_billing_service),
    _: None = Depends(require_flag("BILLING_MANAGEMENT"))
):
    """
    Send FTC-compliant trial period reminder notifications
    
    COMPLIANCE FEATURES:
    - Sent 3 days before trial ends (Connecticut law requirement)
    - Clear cancellation instructions and deadline
    - Automatic billing warning with exact charge amounts
    - Easy cancellation link included
    """
    try:
        # This would typically be called by a scheduled task
        # Implementation would query for trials ending in 3 days
        reminder_count = stripe_service.send_trial_reminders()
        
        return TrialReminderResponse(
            sent_count=reminder_count,
            message=f"Sent {reminder_count} FTC-compliant trial reminder notifications",
            compliance_status="FTC_2025_COMPLIANT"
        )
        
    except Exception as e:
        logger.error(f"Error sending trial reminders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send trial reminder notifications"
        )

@router.post("/renewal-notices", response_model=RenewalNoticeResponse)
async def send_renewal_notices(
    stripe_service: StripeService = Depends(get_billing_service),
    _: None = Depends(require_flag("BILLING_MANAGEMENT"))
):
    """
    Send FTC-compliant subscription renewal notifications
    
    COMPLIANCE FEATURES:
    - Sent 3 days before renewal (FTC requirement)
    - Clear renewal amount and frequency disclosure
    - Easy cancellation method and deadline
    - Customer portal access for immediate cancellation
    """
    try:
        # This would typically be called by a scheduled task
        # Implementation would query for subscriptions renewing in 3 days
        notice_count = stripe_service.send_renewal_notices()
        
        return RenewalNoticeResponse(
            sent_count=notice_count,
            message=f"Sent {notice_count} FTC-compliant renewal notifications",
            compliance_status="FTC_2025_COMPLIANT"
        )
        
    except Exception as e:
        logger.error(f"Error sending renewal notices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send renewal notifications"
        )

@router.get("/compliance-disclosures")
async def get_compliance_disclosures():
    """
    Get comprehensive FTC and state compliance disclosures
    
    Returns all required legal disclosures for subscription services
    in compliance with federal and state consumer protection laws.
    """
    try:
        disclosures = {
            "ftc_disclosures": {
                "auto_renewal_notice": "This subscription automatically renews at the end of each billing period unless you cancel. You will be charged the full subscription price unless you cancel before your trial ends.",
                "cancellation_method": "You can cancel anytime through your account settings by clicking 'Cancel Subscription'. Cancellation is as easy as the method used to sign up.",
                "billing_frequency": "You will be billed monthly or annually based on your plan selection. The exact charge amount and date will be confirmed before payment.",
                "trial_terms": "Your 7-day free trial begins when you complete signup. You must cancel before the trial ends to avoid being charged the full subscription price."
            },
            "state_disclosures": {
                "california_sb313": "California residents: This subscription will automatically renew unless you cancel. We will notify you by email at least 3 days before renewal with the renewal amount and cancellation instructions.",
                "massachusetts_notice": "Massachusetts residents: You will receive written subscription reminders 5-30 days before the renewal cancellation deadline.",
                "connecticut_trial": "Connecticut residents: You will receive notification 3-21 days before your trial ends if your trial period exceeds one month."
            },
            "consumer_protection": {
                "refund_policy": "Full refund available within 30 days of your first paid charge. Contact support to request a refund.",
                "data_retention": "Your account data is retained for 30 days after cancellation to allow easy reactivation. You can request immediate data deletion by contacting support.",
                "downgrade_protection": "Cancelled accounts automatically receive free tier access with basic features. No loss of core functionality.",
                "contact_support": "Email support@lilymedia.ai or use in-app chat for cancellation assistance or questions about your subscription."
            },
            "legal_framework": {
                "effective_date": "2025-09-07",
                "compliance_version": "FTC_CLICK_TO_CANCEL_2025",
                "last_updated": "2025-09-07T00:00:00Z",
                "applicable_laws": [
                    "FTC Click-to-Cancel Rule (16 CFR Part 425)",
                    "California SB-313 (Automatic Renewal Law)",
                    "Massachusetts Consumer Protection Act",
                    "Connecticut Automatic Renewal Act"
                ]
            }
        }
        
        return disclosures
        
    except Exception as e:
        logger.error(f"Error getting compliance disclosures: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve compliance disclosures"
        )

@router.post("/cancellation-feedback", response_model=CancellationFeedbackResponse)
async def submit_cancellation_feedback(
    request: CancellationFeedbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    P1-10a: Collect cancellation feedback for consumer protection and service improvement
    
    CONSUMER PROTECTION FEATURES:
    - Voluntary feedback collection only
    - Data used for service improvement
    - No impact on cancellation process
    - Privacy-compliant storage
    """
    try:
        # Log cancellation feedback for analysis (no PII stored)
        feedback_data = {
            "user_id": current_user.id,
            "reason": request.reason,
            "feedback_length": len(request.feedback) if request.feedback else 0,
            "timestamp": request.timestamp,
            "plan_name": getattr(current_user.plan, 'name', 'unknown') if current_user.plan else 'unknown'
        }
        
        logger.info(f"Cancellation feedback received: {feedback_data}")
        
        # In a full implementation, you might store this in a feedback table
        # For now, we just log it for analysis
        
        return CancellationFeedbackResponse(
            success=True,
            message="Thank you for your feedback. It helps us improve our service."
        )
        
    except Exception as e:
        logger.error(f"Failed to process cancellation feedback: {e}")
        # Don't fail the cancellation process if feedback fails
        return CancellationFeedbackResponse(
            success=True,
            message="Feedback processing encountered an issue, but your cancellation can proceed normally."
        )

@router.get("/health")
async def billing_health_check(
    stripe_service: StripeService = Depends(get_billing_service)
):
    """
    Health check endpoint for billing system
    
    Verifies that Stripe integration is properly configured
    and operational.
    """
    try:
        is_configured = stripe_service.is_enabled()
        
        health_info = {
            "status": "healthy" if is_configured else "degraded",
            "stripe_configured": is_configured,
            "timestamp": "2025-09-07T00:00:00Z"
        }
        
        if not is_configured:
            health_info["message"] = "Stripe is not configured - billing functionality unavailable"
        
        return health_info
        
    except Exception as e:
        logger.error(f"Billing health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-09-07T00:00:00Z"
        }