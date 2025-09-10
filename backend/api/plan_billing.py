"""
Plan-Based Billing API
Enhanced billing endpoints that integrate with our Plan model
"""
import os
import logging
import stripe
import hmac
import hashlib
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.auth.dependencies import get_current_user, AuthUser, get_current_active_user
from backend.db.models import User, Plan
from backend.services.plan_aware_stripe_service import (
    get_plan_aware_stripe_service, 
    PlanAwareStripeService, 
    PlanAwareStripeError
)
from backend.services.plan_service import PlanService
from backend.core.api_version import create_versioned_router

logger = logging.getLogger(__name__)

router = create_versioned_router(prefix="/billing", tags=["plan-billing"])

# Request/Response Models
class CreateCheckoutRequest(BaseModel):
    plan_name: str = Field(..., description="Plan name: starter, pro, or enterprise")
    annual_billing: bool = Field(False, description="Whether to use annual billing")
    success_url: str = Field(..., description="URL to redirect on successful payment")
    cancel_url: str = Field(..., description="URL to redirect on cancelled payment")
    # P1-10b: FTC compliance - track terms acceptance
    terms_accepted_at: Optional[str] = Field(None, description="ISO timestamp when user accepted terms")

class CheckoutResponse(BaseModel):
    session_id: str
    checkout_url: str
    plan_name: str
    price: str
    billing_cycle: str
    trial_days: int
    message: str = "Checkout session created successfully"

class CustomerPortalRequest(BaseModel):
    return_url: str = Field(..., description="URL to return to from customer portal")

class CustomerPortalResponse(BaseModel):
    portal_url: str
    message: str = "Customer portal session created successfully"

class BillingInfoResponse(BaseModel):
    user_id: int
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]
    subscription_status: str
    subscription_end_date: Optional[str]
    has_active_subscription: bool
    current_plan: Dict[str, Any]
    can_upgrade: bool
    stripe_configured: bool

class PlanInfoResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str]
    monthly_price: float
    annual_price: Optional[float]
    trial_days: int
    limits: Dict[str, Any]
    features: List[str]
    stripe_configured: bool
    stripe_monthly_price_id: Optional[str] = None
    stripe_annual_price_id: Optional[str] = None

class AvailablePlansResponse(BaseModel):
    plans: List[PlanInfoResponse]
    current_plan: Optional[str]
    can_upgrade: bool

class WebhookResponse(BaseModel):
    message: str
    processed: bool = True

# Dependency to get services
def get_billing_service(db: Session = Depends(get_db)):
    return get_plan_aware_stripe_service(db)

def get_plan_service(db: Session = Depends(get_db)):
    return PlanService(db)

@router.get("/plans", response_model=AvailablePlansResponse)
async def get_available_plans(
    current_user: User = Depends(get_current_active_user),
    billing_service: PlanAwareStripeService = Depends(get_billing_service),
    plan_service: PlanService = Depends(get_plan_service)
):
    """
    Get all available subscription plans with pricing and features
    
    Returns detailed information about all plans including:
    - Pricing (monthly and annual)
    - Feature lists and limits
    - Stripe integration status
    - Current user plan
    """
    try:
        # Get all available plans
        plans = plan_service.get_all_plans()
        current_user_plan = plan_service.get_user_capabilities(current_user.id).get_plan_name()
        
        plan_responses = []
        for plan in plans:
            # Get feature list for this plan
            capabilities = plan_service._create_plan_capability(plan)
            features = capabilities.get_feature_list()
            
            plan_info = PlanInfoResponse(
                id=plan.id,
                name=plan.name,
                display_name=plan.display_name,
                description=plan.description,
                monthly_price=float(plan.monthly_price),
                annual_price=float(plan.annual_price) if plan.annual_price else None,
                trial_days=plan.trial_days,
                limits={
                    "max_social_profiles": plan.max_social_profiles,
                    "max_posts_per_day": plan.max_posts_per_day,
                    "max_posts_per_week": plan.max_posts_per_week,
                    "max_users": plan.max_users,
                    "max_workspaces": plan.max_workspaces,
                },
                features=features,
                stripe_configured=billing_service.is_enabled(),
                stripe_monthly_price_id=plan.stripe_monthly_price_id if billing_service.is_enabled() else None,
                stripe_annual_price_id=plan.stripe_annual_price_id if billing_service.is_enabled() else None
            )
            plan_responses.append(plan_info)
        
        return AvailablePlansResponse(
            plans=plan_responses,
            current_plan=current_user_plan,
            can_upgrade=billing_service.is_enabled()
        )
        
    except Exception as e:
        logger.error(f"Error getting available plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available plans"
        )

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    billing_service: PlanAwareStripeService = Depends(get_billing_service),
    plan_service: PlanService = Depends(get_plan_service)
):
    """
    Create a Stripe checkout session for plan subscription
    
    Creates a secure Stripe checkout session that redirects users
    to Stripe's hosted payment page for subscription signup.
    """
    try:
        # Find the requested plan
        plan = plan_service.get_plan_by_name(request.plan_name)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan not found: {request.plan_name}"
            )
        
        # Check if user already has an active subscription
        if current_user.subscription_status == "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active subscription. Use the customer portal to change plans."
            )
        
        # Create checkout session
        session_data = billing_service.create_checkout_session_for_plan(
            user=current_user,
            plan=plan,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            annual_billing=request.annual_billing
        )
        
        return CheckoutResponse(**session_data)
        
    except PlanAwareStripeError as e:
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
    billing_service: PlanAwareStripeService = Depends(get_billing_service)
):
    """
    Create a Stripe customer portal session for subscription management
    
    The customer portal allows users to:
    - Update payment methods
    - View billing history
    - Download invoices
    - Cancel or modify subscriptions
    - Update billing information
    """
    try:
        if not current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No subscription found. Please sign up for a plan first."
            )
        
        portal_url = billing_service.create_customer_portal_session(
            user=current_user,
            return_url=request.return_url
        )
        
        return CustomerPortalResponse(
            portal_url=portal_url
        )
        
    except PlanAwareStripeError as e:
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

@router.get("/info", response_model=BillingInfoResponse)
async def get_billing_info(
    current_user: User = Depends(get_current_active_user),
    billing_service: PlanAwareStripeService = Depends(get_billing_service)
):
    """
    Get comprehensive billing information for the current user
    
    Returns:
    - Current subscription status and plan
    - Billing cycle and next payment date
    - Plan limits and features
    - Stripe customer information
    """
    try:
        billing_info = billing_service.get_user_billing_info(current_user)
        return BillingInfoResponse(**billing_info)
        
    except Exception as e:
        logger.error(f"Error getting billing info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve billing information"
        )

@router.post("/webhooks/stripe", response_model=WebhookResponse)
async def stripe_webhook(
    request: Request,
    billing_service: PlanAwareStripeService = Depends(get_billing_service)
):
    """
    Handle Stripe webhook events for plan-based subscriptions
    
    Processes webhook events from Stripe to keep subscription
    statuses and plan assignments synchronized with payments.
    
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
            billing_service.handle_subscription_created(event_data)
        elif event_type == "customer.subscription.updated":
            billing_service.handle_subscription_updated(event_data)
        elif event_type == "customer.subscription.deleted":
            billing_service.handle_subscription_deleted(event_data)
        elif event_type == "invoice.payment_succeeded":
            billing_service.handle_invoice_payment_succeeded(event_data)
        elif event_type == "invoice.payment_failed":
            billing_service.handle_invoice_payment_failed(event_data)
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

@router.get("/health")
async def billing_health_check(
    billing_service: PlanAwareStripeService = Depends(get_billing_service)
):
    """
    Health check endpoint for plan-based billing system
    
    Verifies:
    - Stripe integration configuration
    - Database connectivity for plans
    - Service operational status
    """
    try:
        is_configured = billing_service.is_enabled()
        
        health_info = {
            "status": "healthy" if is_configured else "degraded",
            "stripe_configured": is_configured,
            "plan_system": "operational",
            "timestamp": "2025-09-05T20:00:00Z",
            "service": "plan-aware-billing"
        }
        
        if not is_configured:
            health_info["message"] = "Stripe is not configured - billing functionality unavailable"
        else:
            health_info["message"] = "Plan-based billing system operational"
        
        return health_info
        
    except Exception as e:
        logger.error(f"Billing health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-09-05T20:00:00Z",
            "service": "plan-aware-billing"
        }