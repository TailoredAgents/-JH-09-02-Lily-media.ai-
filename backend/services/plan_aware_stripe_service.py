"""
Plan-Aware Stripe Service
Integrates Stripe billing with our Plan-based subscription system
"""
import os
import logging
import stripe
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.db.database import get_db
from backend.db.models import User, Plan
from backend.services.plan_service import PlanService
from backend.core.config import get_settings

logger = logging.getLogger(__name__)

class PlanAwareStripeError(Exception):
    """Base exception for Plan-aware Stripe operations"""
    pass

class PlanAwareStripeService:
    """
    Enhanced Stripe integration service that works with our Plan model
    
    Features:
    - Plan-based subscription management
    - Integration with PlanService
    - Automatic plan assignment on successful payment
    - Trial period management
    - Multi-currency support (future)
    """
    
    def __init__(self, db: Session = None):
        """Initialize Plan-aware Stripe service"""
        self.db = db or next(get_db())
        self.settings = get_settings()
        self.plan_service = PlanService(self.db)
        
        # Initialize Stripe with API key
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        if not stripe.api_key:
            logger.warning("STRIPE_SECRET_KEY not configured - Stripe functionality will be disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Plan-aware Stripe service initialized successfully")
    
    def is_enabled(self) -> bool:
        """Check if Stripe is properly configured and enabled"""
        return self.enabled
    
    def get_or_create_stripe_customer(self, user: User) -> str:
        """Get existing Stripe customer ID or create new one"""
        if user.stripe_customer_id:
            try:
                # Verify customer still exists in Stripe
                stripe.Customer.retrieve(user.stripe_customer_id)
                return user.stripe_customer_id
            except stripe.error.InvalidRequestError:
                logger.warning(f"Stripe customer {user.stripe_customer_id} not found, creating new one")
                user.stripe_customer_id = None
        
        return self.create_stripe_customer(user)
    
    def create_stripe_customer(self, user: User) -> str:
        """Create a new Stripe customer for the user"""
        if not self.is_enabled():
            raise PlanAwareStripeError("Stripe is not configured")
        
        try:
            customer_data = {
                "email": user.email,
                "name": user.full_name or user.username,
                "description": f"Lily Media AI User: {user.email}",
                "metadata": {
                    "user_id": str(user.id),
                    "signup_date": user.created_at.isoformat() if user.created_at else "",
                    "system": "lily-media-ai"
                }
            }
            
            customer = stripe.Customer.create(**customer_data)
            
            # Update user record with Stripe customer ID
            user.stripe_customer_id = customer.id
            self.db.commit()
            
            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise PlanAwareStripeError(f"Failed to create customer: {e}")
    
    def create_checkout_session_for_plan(
        self, 
        user: User, 
        plan: Plan,
        success_url: str,
        cancel_url: str,
        annual_billing: bool = False
    ) -> Dict[str, str]:
        """
        Create a Stripe Checkout session for plan subscription
        
        Args:
            user: User object
            plan: Plan object from database
            success_url: URL to redirect on successful payment
            cancel_url: URL to redirect on cancelled payment
            annual_billing: Whether to use annual pricing
            
        Returns:
            Dictionary with checkout session ID and URL
        """
        if not self.is_enabled():
            raise PlanAwareStripeError("Stripe is not configured")
        
        try:
            customer_id = self.get_or_create_stripe_customer(user)
            
            # Use appropriate Stripe price ID based on billing cycle
            if annual_billing and plan.stripe_annual_price_id:
                price_id = plan.stripe_annual_price_id
                price_amount = plan.annual_price
            else:
                price_id = plan.stripe_monthly_price_id
                price_amount = plan.monthly_price
            
            if not price_id:
                raise PlanAwareStripeError(f"No Stripe price ID configured for plan: {plan.name}")
            
            session_data = {
                "customer": customer_id,
                "payment_method_types": ["card"],
                "line_items": [{
                    "price": price_id,
                    "quantity": 1,
                }],
                "mode": "subscription",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": {
                    "user_id": str(user.id),
                    "plan_id": str(plan.id),
                    "plan_name": plan.name,
                    "billing_cycle": "annual" if annual_billing else "monthly",
                    "price_amount": str(price_amount),
                    "system": "lily-media-ai"
                },
                "subscription_data": {
                    "metadata": {
                        "user_id": str(user.id),
                        "plan_id": str(plan.id),
                        "plan_name": plan.name,
                        "billing_cycle": "annual" if annual_billing else "monthly",
                        "system": "lily-media-ai"
                    },
                    "trial_period_days": plan.trial_days if plan.trial_days > 0 else None
                },
                # Allow customer to apply promo codes
                "allow_promotion_codes": True,
            }
            
            session = stripe.checkout.Session.create(**session_data)
            
            logger.info(f"Created checkout session {session.id} for user {user.id}, plan {plan.name}")
            
            return {
                "session_id": session.id,
                "checkout_url": session.url,
                "plan_name": plan.name,
                "price": str(price_amount),
                "billing_cycle": "annual" if annual_billing else "monthly",
                "trial_days": plan.trial_days if plan.trial_days > 0 else 0
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise PlanAwareStripeError(f"Failed to create checkout session: {e}")
    
    def create_customer_portal_session(self, user: User, return_url: str) -> str:
        """Create a Stripe customer portal session for subscription management"""
        if not self.is_enabled():
            raise PlanAwareStripeError("Stripe is not configured")
        
        if not user.stripe_customer_id:
            raise PlanAwareStripeError("User has no Stripe customer ID")
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=user.stripe_customer_id,
                return_url=return_url,
            )
            
            logger.info(f"Created customer portal session for user {user.id}")
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create customer portal session: {e}")
            raise PlanAwareStripeError(f"Failed to create customer portal session: {e}")
    
    def handle_subscription_created(self, subscription_data: Dict[str, Any]) -> None:
        """Handle subscription.created webhook event"""
        try:
            customer_id = subscription_data["customer"]
            subscription_id = subscription_data["id"]
            status = subscription_data["status"]
            
            # Find user by Stripe customer ID
            user = self.db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if not user:
                logger.error(f"No user found for Stripe customer {customer_id}")
                return
            
            # Get plan info from subscription metadata
            metadata = subscription_data.get("metadata", {})
            plan_id = metadata.get("plan_id")
            plan_name = metadata.get("plan_name")
            
            # Find and assign the plan
            if plan_id:
                plan = self.db.query(Plan).filter(Plan.id == int(plan_id)).first()
                if plan:
                    user.plan_id = plan.id
                    logger.info(f"Assigned plan {plan.name} (ID: {plan.id}) to user {user.id}")
            elif plan_name:
                plan = self.db.query(Plan).filter(Plan.name == plan_name).first()
                if plan:
                    user.plan_id = plan.id
                    logger.info(f"Assigned plan {plan.name} to user {user.id}")
            
            # Update subscription info
            user.stripe_subscription_id = subscription_id
            user.subscription_status = "active" if status == "active" else status
            
            if status == "active":
                current_period_end = subscription_data.get("current_period_end")
                if current_period_end:
                    user.subscription_end_date = datetime.fromtimestamp(current_period_end, tz=timezone.utc)
            
            self.db.commit()
            logger.info(f"Updated user {user.id} subscription: {plan_name}, status: {status}")
            
        except Exception as e:
            logger.error(f"Error handling subscription created: {e}")
            self.db.rollback()
    
    def handle_subscription_updated(self, subscription_data: Dict[str, Any]) -> None:
        """Handle subscription.updated webhook event"""
        try:
            customer_id = subscription_data["customer"]
            status = subscription_data["status"]
            
            user = self.db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if not user:
                logger.error(f"No user found for Stripe customer {customer_id}")
                return
            
            # Update subscription status
            user.subscription_status = "active" if status == "active" else status
            
            if status == "active":
                current_period_end = subscription_data.get("current_period_end")
                if current_period_end:
                    user.subscription_end_date = datetime.fromtimestamp(current_period_end, tz=timezone.utc)
            elif status in ["canceled", "incomplete_expired"]:
                user.subscription_status = "cancelled"
                # Keep the plan_id but they lose access until resubscribed
            
            self.db.commit()
            logger.info(f"Updated user {user.id} subscription status: {status}")
            
        except Exception as e:
            logger.error(f"Error handling subscription updated: {e}")
            self.db.rollback()
    
    def handle_subscription_deleted(self, subscription_data: Dict[str, Any]) -> None:
        """Handle subscription.deleted webhook event"""
        try:
            customer_id = subscription_data["customer"]
            
            user = self.db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if not user:
                logger.error(f"No user found for Stripe customer {customer_id}")
                return
            
            # Cancel subscription but keep plan reference for potential reactivation
            user.subscription_status = "cancelled"
            user.stripe_subscription_id = None
            user.subscription_end_date = None
            
            self.db.commit()
            logger.info(f"Cancelled subscription for user {user.id}")
            
        except Exception as e:
            logger.error(f"Error handling subscription deleted: {e}")
            self.db.rollback()
    
    def handle_invoice_payment_succeeded(self, invoice_data: Dict[str, Any]) -> None:
        """Handle invoice.payment_succeeded webhook event"""
        try:
            customer_id = invoice_data["customer"]
            subscription_id = invoice_data.get("subscription")
            
            if not subscription_id:
                return  # Not a subscription invoice
            
            user = self.db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if not user:
                logger.error(f"No user found for Stripe customer {customer_id}")
                return
            
            # Update subscription status to active on successful payment
            user.subscription_status = "active"
            
            # Update subscription end date
            if invoice_data.get("period_end"):
                user.subscription_end_date = datetime.fromtimestamp(invoice_data["period_end"], tz=timezone.utc)
            
            self.db.commit()
            logger.info(f"Processed successful payment for user {user.id}")
            
        except Exception as e:
            logger.error(f"Error handling invoice payment succeeded: {e}")
            self.db.rollback()
    
    def handle_invoice_payment_failed(self, invoice_data: Dict[str, Any]) -> None:
        """Handle invoice.payment_failed webhook event"""
        try:
            customer_id = invoice_data["customer"]
            
            user = self.db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if not user:
                logger.error(f"No user found for Stripe customer {customer_id}")
                return
            
            # Mark subscription as past due
            user.subscription_status = "past_due"
            self.db.commit()
            
            logger.info(f"Marked user {user.id} subscription as past_due")
            
        except Exception as e:
            logger.error(f"Error handling invoice payment failed: {e}")
            self.db.rollback()
    
    def get_user_billing_info(self, user: User) -> Dict[str, Any]:
        """Get comprehensive billing information for user"""
        # Get current plan capabilities
        capabilities = self.plan_service.get_user_capabilities(user.id)
        
        billing_info = {
            "user_id": user.id,
            "stripe_customer_id": user.stripe_customer_id,
            "stripe_subscription_id": user.stripe_subscription_id,
            "subscription_status": user.subscription_status or "none",
            "subscription_end_date": user.subscription_end_date.isoformat() if user.subscription_end_date else None,
            "has_active_subscription": user.subscription_status == "active",
            "current_plan": {
                "id": capabilities.plan.id if capabilities.plan else None,
                "name": capabilities.get_plan_name(),
                "display_name": capabilities.plan.display_name if capabilities.plan else "Free",
                "monthly_price": float(capabilities.plan.monthly_price) if capabilities.plan else 0,
                "annual_price": float(capabilities.plan.annual_price) if capabilities.plan and capabilities.plan.annual_price else None,
                "trial_days": capabilities.plan.trial_days if capabilities.plan else 0,
                "limits": {
                    "max_social_profiles": capabilities.plan.max_social_profiles if capabilities.plan else 1,
                    "max_posts_per_day": capabilities.plan.max_posts_per_day if capabilities.plan else 3,
                    "max_users": capabilities.plan.max_users if capabilities.plan else 1,
                },
                "features": capabilities.get_feature_list() if capabilities.plan else []
            },
            "can_upgrade": True,
            "stripe_configured": self.is_enabled()
        }
        
        return billing_info


def get_plan_aware_stripe_service(db: Session = None) -> PlanAwareStripeService:
    """Factory function to get Plan-aware Stripe service instance"""
    return PlanAwareStripeService(db)