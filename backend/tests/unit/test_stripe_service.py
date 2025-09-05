"""
Unit tests for Stripe payment and subscription service
Tests customer management, subscription lifecycle, and webhook processing
"""
import pytest
import stripe
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.services.stripe_service import (
    StripeService, 
    StripeError, 
    StripeCustomerError, 
    StripeSubscriptionError,
    get_stripe_service
)
from backend.services.subscription_service import SubscriptionTier
from backend.db.models import User
from backend.db.multi_tenant_models import Organization


class TestStripeService:
    """Test Stripe service functionality"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_user(self):
        """Mock user object"""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.full_name = "Test User"
        user.username = "testuser"
        user.stripe_customer_id = None
        user.stripe_subscription_id = None
        user.subscription_status = None
        user.tier = "basic"
        user.subscription_end_date = None
        return user

    @pytest.fixture
    def mock_organization(self):
        """Mock organization object"""
        org = Mock(spec=Organization)
        org.id = "org_123"
        org.name = "Test Organization"
        return org

    @pytest.fixture
    def stripe_service(self, mock_db):
        """Create StripeService instance with mocked dependencies"""
        with patch.dict('os.environ', {'STRIPE_SECRET_KEY': 'sk_test_123'}):
            service = StripeService(mock_db)
            return service

    def test_is_enabled_with_api_key(self, mock_db):
        """Test that service is enabled when API key is configured"""
        with patch.dict('os.environ', {'STRIPE_SECRET_KEY': 'sk_test_123'}):
            service = StripeService(mock_db)
            assert service.is_enabled() is True

    def test_is_enabled_without_api_key(self, mock_db):
        """Test that service is disabled when API key is missing"""
        with patch.dict('os.environ', {}, clear=True):
            service = StripeService(mock_db)
            assert service.is_enabled() is False

    @patch('stripe.Customer.create')
    def test_create_customer_individual(self, mock_create, stripe_service, mock_user, mock_db):
        """Test creating individual customer"""
        # Mock Stripe response
        mock_customer = Mock()
        mock_customer.id = "cus_123"
        mock_create.return_value = mock_customer
        
        # Test creation
        customer_id = stripe_service.create_customer(mock_user)
        
        # Verify Stripe API call
        mock_create.assert_called_once()
        create_args = mock_create.call_args[1]
        assert create_args["email"] == "test@example.com"
        assert create_args["name"] == "Test User"
        assert create_args["metadata"]["user_id"] == "1"
        assert create_args["metadata"]["billing_type"] == "individual"
        
        # Verify user update
        assert mock_user.stripe_customer_id == "cus_123"
        mock_db.commit.assert_called_once()
        assert customer_id == "cus_123"

    @patch('stripe.Customer.create')
    def test_create_customer_organization(self, mock_create, stripe_service, mock_user, mock_organization, mock_db):
        """Test creating organization customer"""
        # Mock Stripe response
        mock_customer = Mock()
        mock_customer.id = "cus_org_123"
        mock_create.return_value = mock_customer
        
        # Test creation
        customer_id = stripe_service.create_customer(mock_user, mock_organization)
        
        # Verify Stripe API call
        mock_create.assert_called_once()
        create_args = mock_create.call_args[1]
        assert create_args["email"] == "test@example.com"
        assert create_args["name"] == "Test Organization"
        assert create_args["metadata"]["organization_id"] == "org_123"
        assert create_args["metadata"]["billing_type"] == "organization"
        
        assert customer_id == "cus_org_123"

    @patch('stripe.Customer.create')
    def test_create_customer_stripe_error(self, mock_create, stripe_service, mock_user):
        """Test handling Stripe errors during customer creation"""
        # Mock Stripe error
        mock_create.side_effect = stripe.error.CardError("Card declined", None, None)
        
        # Test error handling
        with pytest.raises(StripeCustomerError):
            stripe_service.create_customer(mock_user)

    def test_create_customer_service_disabled(self, mock_db, mock_user):
        """Test error when service is disabled"""
        with patch.dict('os.environ', {}, clear=True):
            service = StripeService(mock_db)
            
            with pytest.raises(StripeError, match="Stripe is not configured"):
                service.create_customer(mock_user)

    @patch('stripe.Customer.retrieve')
    def test_get_or_create_customer_existing(self, mock_retrieve, stripe_service, mock_user):
        """Test getting existing customer"""
        mock_user.stripe_customer_id = "cus_existing"
        mock_retrieve.return_value = Mock()  # Customer exists
        
        customer_id = stripe_service.get_or_create_customer(mock_user)
        
        assert customer_id == "cus_existing"
        mock_retrieve.assert_called_once_with("cus_existing")

    @patch('stripe.Customer.retrieve')
    @patch('stripe.Customer.create')
    def test_get_or_create_customer_recreate(self, mock_create, mock_retrieve, stripe_service, mock_user, mock_db):
        """Test recreating customer when existing one is invalid"""
        mock_user.stripe_customer_id = "cus_invalid"
        mock_retrieve.side_effect = stripe.error.InvalidRequestError("No such customer", None)
        
        # Mock new customer creation
        mock_customer = Mock()
        mock_customer.id = "cus_new"
        mock_create.return_value = mock_customer
        
        customer_id = stripe_service.get_or_create_customer(mock_user)
        
        assert customer_id == "cus_new"
        assert mock_user.stripe_customer_id == "cus_new"

    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session(self, mock_create, stripe_service, mock_user):
        """Test creating checkout session"""
        # Mock customer creation
        mock_user.stripe_customer_id = "cus_123"
        
        # Mock checkout session
        mock_session = Mock()
        mock_session.id = "cs_123"
        mock_session.url = "https://checkout.stripe.com/pay/cs_123"
        mock_create.return_value = mock_session
        
        result = stripe_service.create_checkout_session(
            user=mock_user,
            tier=SubscriptionTier.PREMIUM,
            success_url="https://app.example.com/success",
            cancel_url="https://app.example.com/cancel"
        )
        
        assert result["session_id"] == "cs_123"
        assert result["checkout_url"] == "https://checkout.stripe.com/pay/cs_123"
        
        # Verify session creation parameters
        mock_create.assert_called_once()
        create_args = mock_create.call_args[1]
        assert create_args["customer"] == "cus_123"
        assert create_args["mode"] == "subscription"
        assert create_args["success_url"] == "https://app.example.com/success"

    def test_create_checkout_session_invalid_tier(self, stripe_service, mock_user):
        """Test error with invalid subscription tier"""
        mock_user.stripe_customer_id = "cus_123"
        
        with pytest.raises(ValueError):
            stripe_service.create_checkout_session(
                user=mock_user,
                tier=SubscriptionTier("invalid_tier"),  # Invalid tier
                success_url="https://app.example.com/success",
                cancel_url="https://app.example.com/cancel"
            )

    @patch('stripe.billing_portal.Session.create')
    def test_create_customer_portal_session(self, mock_create, stripe_service, mock_user):
        """Test creating customer portal session"""
        mock_user.stripe_customer_id = "cus_123"
        
        # Mock portal session
        mock_session = Mock()
        mock_session.url = "https://billing.stripe.com/session_123"
        mock_create.return_value = mock_session
        
        portal_url = stripe_service.create_customer_portal_session(
            user=mock_user,
            return_url="https://app.example.com/billing"
        )
        
        assert portal_url == "https://billing.stripe.com/session_123"
        mock_create.assert_called_once_with(
            customer="cus_123",
            return_url="https://app.example.com/billing"
        )

    def test_create_customer_portal_no_customer(self, stripe_service, mock_user):
        """Test error when user has no Stripe customer ID"""
        mock_user.stripe_customer_id = None
        
        with pytest.raises(StripeCustomerError):
            stripe_service.create_customer_portal_session(mock_user, "https://app.example.com")

    def test_handle_subscription_created(self, stripe_service, mock_db):
        """Test handling subscription.created webhook"""
        # Mock user in database
        mock_user = Mock(spec=User)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Mock subscription data
        subscription_data = {
            "id": "sub_123",
            "customer": "cus_123",
            "status": "active",
            "current_period_end": 1640995200,  # 2022-01-01
            "metadata": {
                "tier": "premium"
            }
        }
        
        stripe_service.handle_subscription_created(subscription_data)
        
        # Verify user updates
        assert mock_user.stripe_subscription_id == "sub_123"
        assert mock_user.subscription_status == "active"
        assert mock_user.tier == "premium"
        assert mock_user.subscription_end_date == datetime.fromtimestamp(1640995200, tz=timezone.utc)
        mock_db.commit.assert_called_once()

    def test_handle_subscription_created_no_user(self, stripe_service, mock_db):
        """Test handling webhook when user not found"""
        # Mock no user found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        subscription_data = {
            "id": "sub_123",
            "customer": "cus_nonexistent",
            "status": "active"
        }
        
        # Should not raise error, just log and return
        stripe_service.handle_subscription_created(subscription_data)
        mock_db.commit.assert_not_called()

    def test_handle_subscription_updated(self, stripe_service, mock_db):
        """Test handling subscription.updated webhook"""
        # Mock user in database
        mock_user = Mock(spec=User)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        subscription_data = {
            "id": "sub_123",
            "customer": "cus_123",
            "status": "canceled",
            "current_period_end": 1640995200
        }
        
        stripe_service.handle_subscription_updated(subscription_data)
        
        # Verify user updates for canceled subscription
        assert mock_user.subscription_status == "cancelled"
        assert mock_user.tier == "basic"  # Downgraded
        mock_db.commit.assert_called_once()

    def test_handle_subscription_deleted(self, stripe_service, mock_db):
        """Test handling subscription.deleted webhook"""
        # Mock user in database
        mock_user = Mock(spec=User)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        subscription_data = {
            "id": "sub_123",
            "customer": "cus_123"
        }
        
        stripe_service.handle_subscription_deleted(subscription_data)
        
        # Verify subscription cancellation
        assert mock_user.subscription_status == "cancelled"
        assert mock_user.stripe_subscription_id is None
        assert mock_user.tier == "basic"
        assert mock_user.subscription_end_date is None
        mock_db.commit.assert_called_once()

    def test_handle_invoice_payment_succeeded(self, stripe_service, mock_db):
        """Test handling invoice.payment_succeeded webhook"""
        # Mock user in database
        mock_user = Mock(spec=User)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        invoice_data = {
            "customer": "cus_123",
            "subscription": "sub_123",
            "period_end": 1640995200
        }
        
        stripe_service.handle_invoice_payment_succeeded(invoice_data)
        
        # Verify subscription activation
        assert mock_user.subscription_status == "active"
        assert mock_user.subscription_end_date == datetime.fromtimestamp(1640995200, tz=timezone.utc)
        mock_db.commit.assert_called_once()

    def test_handle_invoice_payment_failed(self, stripe_service, mock_db):
        """Test handling invoice.payment_failed webhook"""
        # Mock user in database
        mock_user = Mock(spec=User)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        invoice_data = {
            "customer": "cus_123"
        }
        
        stripe_service.handle_invoice_payment_failed(invoice_data)
        
        # Verify subscription marked as past due
        assert mock_user.subscription_status == "past_due"
        mock_db.commit.assert_called_once()

    def test_get_subscription_info(self, stripe_service, mock_user):
        """Test getting comprehensive subscription information"""
        mock_user.tier = "premium"
        mock_user.subscription_status = "active"
        mock_user.stripe_customer_id = "cus_123"
        mock_user.stripe_subscription_id = "sub_123"
        mock_user.subscription_end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
        
        # Mock subscription service
        stripe_service.subscription_service = Mock()
        stripe_service.subscription_service.get_tier_limits.return_value = {"max_posts_per_day": 50}
        stripe_service.subscription_service.get_tier_features.return_value = {"premium_image_generation"}
        
        info = stripe_service.get_subscription_info(mock_user)
        
        assert info["tier"] == "premium"
        assert info["status"] == "active"
        assert info["has_active_subscription"] is True
        assert info["subscription_end_date"] == "2024-12-31T00:00:00+00:00"
        assert info["tier_limits"]["max_posts_per_day"] == 50
        assert "premium_image_generation" in info["tier_features"]

    def test_get_stripe_service_factory(self):
        """Test factory function for getting service instance"""
        with patch.dict('os.environ', {'STRIPE_SECRET_KEY': 'sk_test_123'}):
            service = get_stripe_service()
            assert isinstance(service, StripeService)


if __name__ == "__main__":
    pytest.main([__file__])