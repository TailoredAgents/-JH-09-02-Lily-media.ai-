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
    Create a Stripe checkout session for subscription signup
    
    This endpoint creates a Stripe checkout session that redirects users
    to Stripe's hosted payment page for secure subscription signup.
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
        
        # Create checkout session
        session_data = stripe_service.create_checkout_session(
            user=current_user,
            tier=tier,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            organization=organization
        )
        
        return CheckoutResponse(
            session_id=session_data["session_id"],
            checkout_url=session_data["checkout_url"]
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
    Get available subscription plans with features and pricing
    
    Returns detailed information about all subscription tiers
    including features, limits, and pricing information.
    """
    try:
        plans = {
            "basic": {
                "name": "Basic",
                "price_monthly": 9.99,
                "price_yearly": 99.99,
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
                }
            },
            "premium": {
                "name": "Premium",
                "price_monthly": 29.99,
                "price_yearly": 299.99,
                "popular": True,
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
                }
            },
            "enterprise": {
                "name": "Enterprise",
                "price_monthly": 99.99,
                "price_yearly": 999.99,
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
                }
            }
        }
        
        return {"plans": plans}
        
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
            "timestamp": "2025-09-05T16:00:00Z"
        }
        
        if not is_configured:
            health_info["message"] = "Stripe is not configured - billing functionality unavailable"
        
        return health_info
        
    except Exception as e:
        logger.error(f"Billing health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-09-05T16:00:00Z"
        }