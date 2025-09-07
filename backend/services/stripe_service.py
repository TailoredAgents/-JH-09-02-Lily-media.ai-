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
from backend.services.system_metrics import track_cancellation, track_billing_webhook, track_subscription_event

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
            
            # Track billing webhook event for monitoring
            track_billing_webhook(
                event_type="subscription_created",
                status="processing",
                consumer_impact="new_subscription",
                error_category="none"
            )
            
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
            
            # Track successful webhook processing
            track_billing_webhook(
                event_type="subscription_created",
                status="completed",
                consumer_impact="subscription_activated",
                error_category="none"
            )
            
        except Exception as e:
            logger.error(f"Error handling subscription created: {e}")
            # Track failed webhook processing
            track_billing_webhook(
                event_type="subscription_created",
                status="failed",
                consumer_impact="subscription_activation_failed",
                error_category="processing_error"
            )
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
            
            # Track billing webhook event for monitoring
            track_billing_webhook(
                event_type="subscription_deleted",
                status="processing",
                consumer_impact="subscription_cancelled",
                error_category="none"
            )
            
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
    
    def cancel_subscription(
        self, 
        user: User, 
        immediate: bool = False, 
        reason: str = None, 
        feedback: str = None
    ) -> Dict[str, Any]:
        """
        Cancel user's subscription with consumer protection features
        
        Args:
            user: User whose subscription to cancel
            immediate: If True, cancel immediately; if False, cancel at period end
            reason: Optional cancellation reason for tracking
            feedback: Optional user feedback for service improvement
            
        Returns:
            Dictionary with cancellation details including dates
        """
        if not self.is_enabled():
            raise StripeError("Stripe is not configured")
        
        if not user.stripe_subscription_id:
            raise StripeError("User has no active subscription to cancel")
        
        try:
            # Cancel subscription in Stripe
            updated_subscription = stripe.Subscription.modify(
                user.stripe_subscription_id,
                cancel_at_period_end=not immediate,
                cancellation_details={
                    "comment": reason[:500] if reason else None,  # Stripe has 500 char limit
                    "feedback": "customer_service" if feedback else None
                },
                metadata={
                    "cancellation_reason": reason[:500] if reason else "user_requested",
                    "immediate": str(immediate),
                    "user_id": str(user.id)
                }
            )
            
            if immediate:
                # Cancel immediately
                cancelled_subscription = stripe.Subscription.delete(user.stripe_subscription_id)
                
                # Update user status immediately
                user.subscription_status = "cancelled"
                user.stripe_subscription_id = None
                user.tier = SubscriptionTier.BASIC.value
                user.subscription_end_date = None
                
                result = {
                    "cancelled_at": datetime.now(timezone.utc).isoformat(),
                    "effective_date": datetime.now(timezone.utc).isoformat(),
                    "access_until": datetime.now(timezone.utc).isoformat(),
                    "immediate": True
                }
                
            else:
                # Cancel at period end - user keeps access until then
                period_end = datetime.fromtimestamp(
                    updated_subscription["current_period_end"], 
                    timezone.utc
                )
                
                # Update user status to show pending cancellation
                user.subscription_status = "active"  # Still active until period end
                user.subscription_end_date = period_end
                
                result = {
                    "cancelled_at": datetime.now(timezone.utc).isoformat(),
                    "effective_date": period_end.isoformat(),
                    "access_until": period_end.isoformat(),
                    "immediate": False
                }
            
            # Store cancellation reason and feedback for analysis
            if reason or feedback:
                logger.info(
                    f"Subscription cancellation feedback - User {user.id}: "
                    f"Reason: {reason}, Feedback: {feedback}"
                )
            
            self.db.commit()
            
            # Track cancellation metrics for consumer protection monitoring
            reason_category = "pricing" if reason and ("cost" in reason.lower() or "price" in reason.lower()) else \
                            "feature" if reason and ("feature" in reason.lower() or "functionality" in reason.lower()) else \
                            "other" if reason else "no_reason"
            
            track_cancellation(
                method="in_app_api",
                immediate=immediate,
                reason=reason_category,
                consumer_satisfaction="unknown"  # Could be enhanced with post-cancellation survey
            )
            
            track_subscription_event(
                event_type="subscription_cancelled",
                plan_tier=user.tier or "unknown",
                cancellation_type="immediate" if immediate else "end_of_period",
                consumer_protection_feature="transparent_timeline"
            )
            
            logger.info(
                f"Subscription cancelled for user {user.id} - "
                f"immediate: {immediate}, effective: {result['effective_date']}"
            )
            
            return result
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error cancelling subscription: {e}")
            self.db.rollback()
            raise StripeError(f"Failed to cancel subscription: {e}")
        except Exception as e:
            logger.error(f"Unexpected error cancelling subscription: {e}")
            self.db.rollback()
            raise StripeError(f"Subscription cancellation failed: {e}")

    def send_trial_reminders(self) -> int:
        """
        Send FTC-compliant trial reminder notifications
        
        Sends reminders 3 days before trial ends as required by:
        - Connecticut Automatic Renewal Act (3-21 days notice)
        - FTC Click-to-Cancel Rule (clear disclosure)
        
        Returns:
            int: Number of reminders sent
        """
        try:
            if not self.is_enabled():
                logger.warning("Stripe not enabled - cannot send trial reminders")
                return 0
            
            # Query for users with trials ending in 3 days
            from datetime import timedelta
            three_days_from_now = datetime.now(timezone.utc) + timedelta(days=3)
            
            # This would query users whose trial_end_date is approximately 3 days away
            # Implementation would depend on your trial tracking system
            users_to_remind = self.db.query(User).filter(
                and_(
                    User.stripe_customer_id.isnot(None),
                    User.subscription_tier == "trial",
                    # Add trial end date filter here based on your schema
                )
            ).all()
            
            reminder_count = 0
            for user in users_to_remind:
                try:
                    # Send reminder email or notification
                    # This would integrate with your email service
                    self._send_trial_reminder_email(user)
                    reminder_count += 1
                    
                    # Track compliance metric
                    track_subscription_event(
                        event_type="trial_reminder_sent",
                        plan_tier=user.subscription_tier or "trial",
                        consumer_protection_feature="ftc_trial_notice"
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to send trial reminder to user {user.id}: {e}")
                    continue
            
            logger.info(f"Sent {reminder_count} FTC-compliant trial reminders")
            return reminder_count
            
        except Exception as e:
            logger.error(f"Error sending trial reminders: {e}")
            raise StripeError(f"Failed to send trial reminders: {e}")

    def send_renewal_notices(self) -> int:
        """
        Send FTC-compliant subscription renewal notifications
        
        Sends notices 3 days before renewal as required by:
        - FTC Click-to-Cancel Rule (clear renewal disclosure)
        - California SB-313 (3+ days advance notice)
        - Massachusetts Consumer Protection Act (5-30 days notice)
        
        Returns:
            int: Number of notices sent
        """
        try:
            if not self.is_enabled():
                logger.warning("Stripe not enabled - cannot send renewal notices")
                return 0
            
            # Query for subscriptions renewing in 3 days
            from datetime import timedelta
            three_days_from_now = datetime.now(timezone.utc) + timedelta(days=3)
            
            # Get active subscriptions from Stripe that will renew soon
            # This would typically query your subscription tracking system
            users_to_notify = self.db.query(User).filter(
                and_(
                    User.stripe_subscription_id.isnot(None),
                    User.subscription_status == "active",
                    # Add renewal date filter here based on your schema
                )
            ).all()
            
            notice_count = 0
            for user in users_to_notify:
                try:
                    # Get subscription details from Stripe
                    subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
                    
                    # Check if renewal is in ~3 days
                    renewal_timestamp = subscription.current_period_end
                    renewal_date = datetime.fromtimestamp(renewal_timestamp, timezone.utc)
                    days_until_renewal = (renewal_date - datetime.now(timezone.utc)).days
                    
                    if 2 <= days_until_renewal <= 4:  # 3 days +/- 1 for flexibility
                        # Send renewal notice email
                        self._send_renewal_notice_email(user, subscription)
                        notice_count += 1
                        
                        # Track compliance metric
                        track_subscription_event(
                            event_type="renewal_notice_sent",
                            plan_tier=user.subscription_tier or "unknown",
                            consumer_protection_feature="ftc_renewal_notice"
                        )
                        
                except Exception as e:
                    logger.error(f"Failed to send renewal notice to user {user.id}: {e}")
                    continue
            
            logger.info(f"Sent {notice_count} FTC-compliant renewal notices")
            return notice_count
            
        except Exception as e:
            logger.error(f"Error sending renewal notices: {e}")
            raise StripeError(f"Failed to send renewal notices: {e}")

    def _send_trial_reminder_email(self, user: User):
        """
        Send individual trial reminder email with FTC-compliant content
        
        This is a placeholder - would integrate with your email service
        """
        # Email content would include:
        # - Clear trial end date and time
        # - Exact charge amount and frequency after trial
        # - Direct cancellation link to account settings
        # - Customer service contact information
        # - Clear "no action needed to cancel" if user wants to cancel
        
        logger.info(f"Trial reminder email would be sent to user {user.id} ({user.email})")
        
        # Example email template structure:
        email_content = {
            "subject": "Your 7-day free trial ends in 3 days",
            "body": f"""
            Hi {user.email},
            
            Your Lily Media AI free trial ends in 3 days. 
            
            IMPORTANT: If you don't want to be charged, cancel before your trial ends.
            
            Trial ends: [TRIAL_END_DATE]
            Next charge: [SUBSCRIPTION_AMOUNT] on [BILLING_DATE]
            
            To cancel: Go to Account Settings > Subscription > Cancel
            Or contact support: support@lilymedia.ai
            
            Cancellation is as easy as signing up - just one click in your account settings.
            """,
            "compliance_version": "FTC_2025"
        }
        
        # Integration point for email service would be here

    def _send_renewal_notice_email(self, user: User, subscription):
        """
        Send individual renewal notice email with FTC-compliant content
        
        This is a placeholder - would integrate with your email service
        """
        # Email content would include:
        # - Exact renewal amount and date
        # - Billing frequency confirmation
        # - Direct cancellation link to customer portal
        # - Customer service contact information
        # - Clear "no action needed to continue" messaging
        
        renewal_amount = subscription.items.data[0].price.unit_amount / 100  # Convert from cents
        renewal_date = datetime.fromtimestamp(subscription.current_period_end, timezone.utc)
        
        logger.info(f"Renewal notice email would be sent to user {user.id} ({user.email})")
        
        # Example email template structure:
        email_content = {
            "subject": f"Your subscription renews in 3 days - ${renewal_amount}",
            "body": f"""
            Hi {user.email},
            
            Your Lily Media AI subscription automatically renews in 3 days.
            
            Renewal amount: ${renewal_amount}
            Renewal date: {renewal_date.strftime('%B %d, %Y')}
            Billing frequency: {subscription.items.data[0].price.recurring.interval}
            
            No action needed to continue your subscription.
            
            To cancel or modify: Go to Account Settings > Billing
            Or contact support: support@lilymedia.ai
            
            Questions? We're here to help at support@lilymedia.ai
            """,
            "compliance_version": "FTC_2025"
        }
        
        # Integration point for email service would be here


def get_stripe_service(db: Session = None) -> StripeService:
    """Factory function to get Stripe service instance"""
    return StripeService(db)