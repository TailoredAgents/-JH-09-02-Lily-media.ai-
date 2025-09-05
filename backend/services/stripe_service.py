"""
Stripe payment and subscription service for SaaS billing
Handles customer management, subscriptions, and webhooks
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
from backend.db.models import User
from backend.db.multi_tenant_models import Organization
from backend.core.config import get_settings
from backend.services.subscription_service import SubscriptionTier, SubscriptionService

logger = logging.getLogger(__name__)

class StripeError(Exception):
    """Base exception for Stripe operations"""
    pass

class StripeCustomerError(StripeError):
    """Customer-related Stripe error"""
    pass

class StripeSubscriptionError(StripeError):
    """Subscription-related Stripe error"""
    pass

class StripeService:
    """
    Comprehensive Stripe integration service
    
    Features:
    - Customer management (create, retrieve, update)
    - Subscription lifecycle (create, update, cancel, reactivate)
    - Payment method management
    - Invoice and billing handling
    - Webhook processing
    - Usage-based billing support
    """
    
    # Stripe Price IDs for subscription tiers (these would be from your Stripe Dashboard)
    STRIPE_PRICE_IDS = {
        SubscriptionTier.BASIC: os.getenv("STRIPE_BASIC_PRICE_ID", "price_basic_monthly"),
        SubscriptionTier.PREMIUM: os.getenv("STRIPE_PREMIUM_PRICE_ID", "price_premium_monthly"),
        SubscriptionTier.ENTERPRISE: os.getenv("STRIPE_ENTERPRISE_PRICE_ID", "price_enterprise_monthly"),
    }
    
    def __init__(self, db: Session = None):
        """Initialize Stripe service with API key"""
        self.db = db or next(get_db())
        self.settings = get_settings()
        
        # Initialize Stripe with API key
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        if not stripe.api_key:
            logger.warning("STRIPE_SECRET_KEY not configured - Stripe functionality will be disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Stripe service initialized successfully")
        
        # Initialize subscription service for tier management
        self.subscription_service = SubscriptionService(self.db)
    
    def is_enabled(self) -> bool:
        """Check if Stripe is properly configured and enabled"""
        return self.enabled
    
    def create_customer(self, user: User, organization: Organization = None) -> str:
        """
        Create a Stripe customer for user/organization
        
        Args:
            user: User object
            organization: Optional organization (for B2B billing)
            
        Returns:
            Stripe customer ID
        """
        if not self.is_enabled():
            raise StripeError("Stripe is not configured")
        
        try:
            # Determine customer info based on organization vs individual
            if organization:
                customer_data = {
                    "email": user.email,
                    "name": organization.name,
                    "description": f"Organization: {organization.name} (Owner: {user.email})",
                    "metadata": {
                        "user_id": str(user.id),
                        "organization_id": organization.id,
                        "billing_type": "organization"
                    }
                }
            else:
                customer_data = {
                    "email": user.email,
                    "name": user.full_name or user.username,
                    "description": f"Individual user: {user.email}",
                    "metadata": {
                        "user_id": str(user.id),
                        "billing_type": "individual"
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
            raise StripeCustomerError(f"Failed to create customer: {e}")
    
    def get_or_create_customer(self, user: User, organization: Organization = None) -> str:
        """Get existing Stripe customer ID or create new one"""
        if user.stripe_customer_id:
            try:
                # Verify customer still exists in Stripe
                stripe.Customer.retrieve(user.stripe_customer_id)
                return user.stripe_customer_id
            except stripe.error.InvalidRequestError:
                # Customer doesn't exist, create new one
                logger.warning(f"Stripe customer {user.stripe_customer_id} not found, creating new one")
                user.stripe_customer_id = None
                
        return self.create_customer(user, organization)
    
    def create_checkout_session(
        self, 
        user: User, 
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str,
        organization: Organization = None
    ) -> Dict[str, str]:
        """
        Create a Stripe Checkout session for subscription signup
        
        Args:
            user: User object
            tier: Subscription tier to purchase
            success_url: URL to redirect on successful payment
            cancel_url: URL to redirect on cancelled payment
            organization: Optional organization for B2B billing
            
        Returns:
            Dictionary with checkout session ID and URL
        """
        if not self.is_enabled():
            raise StripeError("Stripe is not configured")
        
        try:
            customer_id = self.get_or_create_customer(user, organization)
            price_id = self.STRIPE_PRICE_IDS.get(tier)
            
            if not price_id:
                raise StripeError(f"No price configured for tier: {tier}")
            
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
                    "tier": tier.value,
                    "organization_id": organization.id if organization else ""
                },
                "subscription_data": {
                    "metadata": {
                        "user_id": str(user.id),
                        "tier": tier.value,
                        "organization_id": organization.id if organization else ""
                    }
                }
            }
            
            session = stripe.checkout.Session.create(**session_data)
            
            logger.info(f"Created checkout session {session.id} for user {user.id}, tier {tier}")
            
            return {
                "session_id": session.id,
                "checkout_url": session.url
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise StripeError(f"Failed to create checkout session: {e}")
    
    def create_customer_portal_session(self, user: User, return_url: str) -> str:
        """
        Create a Stripe customer portal session for subscription management
        
        Args:
            user: User object
            return_url: URL to return to from customer portal
            
        Returns:
            Customer portal URL
        """
        if not self.is_enabled():
            raise StripeError("Stripe is not configured")
        
        if not user.stripe_customer_id:
            raise StripeCustomerError("User has no Stripe customer ID")
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=user.stripe_customer_id,
                return_url=return_url,
            )
            
            logger.info(f"Created customer portal session for user {user.id}")
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create customer portal session: {e}")
            raise StripeError(f"Failed to create customer portal session: {e}")
    
    def handle_subscription_created(self, subscription: Dict[str, Any]) -> None:
        """Handle subscription.created webhook event"""
        try:
            customer_id = subscription["customer"]
            subscription_id = subscription["id"]
            status = subscription["status"]
            
            # Find user by Stripe customer ID
            user = self.db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if not user:
                logger.error(f"No user found for Stripe customer {customer_id}")
                return
            
            # Get tier from subscription metadata
            metadata = subscription.get("metadata", {})
            tier = metadata.get("tier", SubscriptionTier.BASIC.value)
            
            # Update user subscription info
            user.stripe_subscription_id = subscription_id
            user.subscription_status = "active" if status == "active" else status
            user.tier = tier
            
            if status == "active":
                # Set subscription end date based on current period end
                current_period_end = subscription.get("current_period_end")
                if current_period_end:
                    user.subscription_end_date = datetime.fromtimestamp(current_period_end, tz=timezone.utc)
            
            self.db.commit()
            
            logger.info(f"Updated user {user.id} subscription: {tier}, status: {status}")
            
        except Exception as e:
            logger.error(f"Error handling subscription created: {e}")
            self.db.rollback()
    
    def handle_subscription_updated(self, subscription: Dict[str, Any]) -> None:
        """Handle subscription.updated webhook event"""
        try:
            customer_id = subscription["customer"]
            subscription_id = subscription["id"]
            status = subscription["status"]
            
            user = self.db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if not user:
                logger.error(f"No user found for Stripe customer {customer_id}")
                return
            
            # Update subscription status
            user.subscription_status = "active" if status == "active" else status
            
            if status == "active":
                current_period_end = subscription.get("current_period_end")
                if current_period_end:
                    user.subscription_end_date = datetime.fromtimestamp(current_period_end, tz=timezone.utc)
            elif status in ["canceled", "incomplete_expired"]:
                user.subscription_status = "cancelled"
                user.tier = SubscriptionTier.BASIC.value  # Downgrade to basic
            
            self.db.commit()
            logger.info(f"Updated user {user.id} subscription status: {status}")
            
        except Exception as e:
            logger.error(f"Error handling subscription updated: {e}")
            self.db.rollback()
    
    def handle_subscription_deleted(self, subscription: Dict[str, Any]) -> None:
        """Handle subscription.deleted webhook event"""
        try:
            customer_id = subscription["customer"]
            
            user = self.db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if not user:
                logger.error(f"No user found for Stripe customer {customer_id}")
                return
            
            # Cancel subscription and downgrade to free tier
            user.subscription_status = "cancelled"
            user.stripe_subscription_id = None
            user.tier = SubscriptionTier.BASIC.value
            user.subscription_end_date = None
            
            self.db.commit()
            logger.info(f"Cancelled subscription for user {user.id}")
            
        except Exception as e:
            logger.error(f"Error handling subscription deleted: {e}")
            self.db.rollback()
    
    def handle_invoice_payment_succeeded(self, invoice: Dict[str, Any]) -> None:
        """Handle invoice.payment_succeeded webhook event"""
        try:
            customer_id = invoice["customer"]
            subscription_id = invoice.get("subscription")
            
            if not subscription_id:
                return  # Not a subscription invoice
            
            user = self.db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if not user:
                logger.error(f"No user found for Stripe customer {customer_id}")
                return
            
            # Update subscription status to active on successful payment
            user.subscription_status = "active"
            
            # Update subscription end date if available
            if invoice.get("period_end"):
                user.subscription_end_date = datetime.fromtimestamp(invoice["period_end"], tz=timezone.utc)
            
            self.db.commit()
            logger.info(f"Processed successful payment for user {user.id}")
            
        except Exception as e:
            logger.error(f"Error handling invoice payment succeeded: {e}")
            self.db.rollback()
    
    def handle_invoice_payment_failed(self, invoice: Dict[str, Any]) -> None:
        """Handle invoice.payment_failed webhook event"""
        try:
            customer_id = invoice["customer"]
            
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
    
    def get_subscription_info(self, user: User) -> Dict[str, Any]:
        """
        Get comprehensive subscription information for user
        
        Returns:
            Dictionary with subscription details
        """
        info = {
            "tier": user.tier,
            "status": user.subscription_status,
            "stripe_customer_id": user.stripe_customer_id,
            "stripe_subscription_id": user.stripe_subscription_id,
            "subscription_end_date": user.subscription_end_date.isoformat() if user.subscription_end_date else None,
            "has_active_subscription": user.subscription_status == "active"
        }
        
        # Get tier limits and features
        if user.tier:
            tier_enum = SubscriptionTier(user.tier)
            info.update({
                "tier_limits": self.subscription_service.get_tier_limits(tier_enum),
                "tier_features": list(self.subscription_service.get_tier_features(tier_enum))
            })
        
        return info


def get_stripe_service(db: Session = None) -> StripeService:
    """Factory function to get Stripe service instance"""
    return StripeService(db)