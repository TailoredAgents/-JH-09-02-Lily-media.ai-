"""
Unit tests for billing API endpoints
Tests checkout, customer portal, subscription info, and webhook handling
"""
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException

from backend.api.billing import router
from backend.services.stripe_service import StripeService, StripeError, StripeCustomerError
from backend.services.subscription_service import SubscriptionTier
from backend.db.models import User


class TestBillingAPI:
    """Test billing API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.stripe_customer_id = "cus_123"
        return user

    @pytest.fixture
    def mock_stripe_service(self):
        """Mock Stripe service"""
        service = Mock(spec=StripeService)
        service.is_enabled.return_value = True
        return service

    @patch('backend.api.billing.get_current_active_user')
    @patch('backend.api.billing.get_billing_service')
    def test_create_checkout_session_success(self, mock_get_service, mock_get_user, client, mock_user, mock_stripe_service):
        """Test successful checkout session creation"""
        mock_get_user.return_value = mock_user
        mock_get_service.return_value = mock_stripe_service
        
        # Mock Stripe service response
        mock_stripe_service.create_checkout_session.return_value = {
            "session_id": "cs_123",
            "checkout_url": "https://checkout.stripe.com/pay/cs_123"
        }
        
        response = client.post("/checkout", json={
            "tier": "premium",
            "success_url": "https://app.example.com/success",
            "cancel_url": "https://app.example.com/cancel"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "cs_123"
        assert data["checkout_url"] == "https://checkout.stripe.com/pay/cs_123"
        assert data["message"] == "Checkout session created successfully"
        
        # Verify service call
        mock_stripe_service.create_checkout_session.assert_called_once_with(
            user=mock_user,
            tier=SubscriptionTier.PREMIUM,
            success_url="https://app.example.com/success",
            cancel_url="https://app.example.com/cancel",
            organization=None
        )

    @patch('backend.api.billing.get_current_active_user')
    @patch('backend.api.billing.get_billing_service')
    def test_create_checkout_session_invalid_tier(self, mock_get_service, mock_get_user, client, mock_user, mock_stripe_service):
        """Test checkout session creation with invalid tier"""
        mock_get_user.return_value = mock_user
        mock_get_service.return_value = mock_stripe_service
        
        response = client.post("/checkout", json={
            "tier": "invalid_tier",
            "success_url": "https://app.example.com/success",
            "cancel_url": "https://app.example.com/cancel"
        })
        
        assert response.status_code == 400
        assert "Invalid subscription tier" in response.json()["detail"]

    @patch('backend.api.billing.get_current_active_user')
    @patch('backend.api.billing.get_billing_service')
    def test_create_checkout_session_stripe_error(self, mock_get_service, mock_get_user, client, mock_user, mock_stripe_service):
        """Test checkout session creation with Stripe error"""
        mock_get_user.return_value = mock_user
        mock_get_service.return_value = mock_stripe_service
        
        # Mock Stripe error
        mock_stripe_service.create_checkout_session.side_effect = StripeError("Payment system error")
        
        response = client.post("/checkout", json={
            "tier": "premium",
            "success_url": "https://app.example.com/success",
            "cancel_url": "https://app.example.com/cancel"
        })
        
        assert response.status_code == 500
        assert "Payment system error" in response.json()["detail"]

    @patch('backend.api.billing.get_current_active_user')
    @patch('backend.api.billing.get_billing_service')
    def test_create_customer_portal_success(self, mock_get_service, mock_get_user, client, mock_user, mock_stripe_service):
        """Test successful customer portal creation"""
        mock_get_user.return_value = mock_user
        mock_get_service.return_value = mock_stripe_service
        
        # Mock Stripe service response
        mock_stripe_service.create_customer_portal_session.return_value = "https://billing.stripe.com/session_123"
        
        response = client.post("/customer-portal", json={
            "return_url": "https://app.example.com/billing"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["portal_url"] == "https://billing.stripe.com/session_123"
        assert data["message"] == "Customer portal session created successfully"

    @patch('backend.api.billing.get_current_active_user')
    @patch('backend.api.billing.get_billing_service')
    def test_create_customer_portal_no_customer(self, mock_get_service, mock_get_user, client, mock_stripe_service):
        """Test customer portal creation without Stripe customer"""
        # Mock user without Stripe customer ID
        user = Mock(spec=User)
        user.stripe_customer_id = None
        mock_get_user.return_value = user
        mock_get_service.return_value = mock_stripe_service
        
        response = client.post("/customer-portal", json={
            "return_url": "https://app.example.com/billing"
        })
        
        assert response.status_code == 400
        assert "No subscription found" in response.json()["detail"]

    @patch('backend.api.billing.get_current_active_user')
    @patch('backend.api.billing.get_billing_service')
    def test_get_subscription_info_success(self, mock_get_service, mock_get_user, client, mock_user, mock_stripe_service):
        """Test successful subscription info retrieval"""
        mock_get_user.return_value = mock_user
        mock_get_service.return_value = mock_stripe_service
        
        # Mock subscription info
        mock_stripe_service.get_subscription_info.return_value = {
            "tier": "premium",
            "status": "active",
            "has_active_subscription": True,
            "subscription_end_date": "2024-12-31T00:00:00+00:00",
            "tier_limits": {"max_posts_per_day": 50},
            "tier_features": ["premium_image_generation", "autonomous_posting"],
            "stripe_customer_id": "cus_123"
        }
        
        response = client.get("/subscription")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "premium"
        assert data["status"] == "active"
        assert data["has_active_subscription"] is True
        assert data["tier_limits"]["max_posts_per_day"] == 50
        assert "premium_image_generation" in data["tier_features"]

    def test_get_billing_plans_success(self, client):
        """Test successful billing plans retrieval"""
        response = client.get("/plans")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify plan structure
        assert "plans" in data
        plans = data["plans"]
        
        # Check basic plan
        assert "basic" in plans
        basic = plans["basic"]
        assert basic["name"] == "Basic"
        assert basic["price_monthly"] == 9.99
        assert basic["limits"]["social_accounts"] == 3
        assert "3 social accounts" in basic["features"]
        
        # Check premium plan
        assert "premium" in plans
        premium = plans["premium"]
        assert premium["name"] == "Premium"
        assert premium["price_monthly"] == 29.99
        assert premium["popular"] is True
        assert premium["limits"]["social_accounts"] == 10
        assert "Autonomous posting" in premium["features"]
        
        # Check enterprise plan
        assert "enterprise" in plans
        enterprise = plans["enterprise"]
        assert enterprise["name"] == "Enterprise"
        assert enterprise["price_monthly"] == 99.99
        assert enterprise["limits"]["social_accounts"] == "unlimited"
        assert "24/7 priority support" in enterprise["features"]

    @patch('backend.api.billing.get_billing_service')
    @patch('os.getenv')
    def test_stripe_webhook_success(self, mock_getenv, mock_get_service, client, mock_stripe_service):
        """Test successful webhook processing"""
        mock_get_service.return_value = mock_stripe_service
        mock_getenv.return_value = "whsec_test_secret"
        
        # Mock webhook payload and signature
        webhook_payload = {
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                    "status": "active"
                }
            }
        }
        
        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = webhook_payload
            
            response = client.post(
                "/webhooks/stripe",
                data=json.dumps(webhook_payload),
                headers={"stripe-signature": "t=123,v1=signature"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["processed"] is True
        assert "customer.subscription.created" in data["message"]
        
        # Verify webhook handler called
        mock_stripe_service.handle_subscription_created.assert_called_once()

    @patch('backend.api.billing.get_billing_service')
    def test_stripe_webhook_missing_signature(self, mock_get_service, client, mock_stripe_service):
        """Test webhook processing without signature"""
        mock_get_service.return_value = mock_stripe_service
        
        response = client.post("/webhooks/stripe", json={"test": "data"})
        
        assert response.status_code == 400
        assert "Missing stripe-signature header" in response.json()["detail"]

    @patch('backend.api.billing.get_billing_service')
    @patch('os.getenv')
    def test_stripe_webhook_invalid_signature(self, mock_getenv, mock_get_service, client, mock_stripe_service):
        """Test webhook processing with invalid signature"""
        mock_get_service.return_value = mock_stripe_service
        mock_getenv.return_value = "whsec_test_secret"
        
        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.side_effect = stripe.error.SignatureVerificationError("Invalid signature", None)
            
            response = client.post(
                "/webhooks/stripe",
                data=json.dumps({"test": "data"}),
                headers={"stripe-signature": "invalid_signature"}
            )
        
        assert response.status_code == 400
        assert "Invalid signature" in response.json()["detail"]

    @patch('backend.api.billing.get_billing_service')
    @patch('os.getenv')
    def test_stripe_webhook_unhandled_event(self, mock_getenv, mock_get_service, client, mock_stripe_service):
        """Test webhook processing with unhandled event type"""
        mock_get_service.return_value = mock_stripe_service
        mock_getenv.return_value = "whsec_test_secret"
        
        # Mock unhandled webhook event
        webhook_payload = {
            "type": "customer.created",  # Unhandled event type
            "data": {
                "object": {
                    "id": "cus_123"
                }
            }
        }
        
        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = webhook_payload
            
            response = client.post(
                "/webhooks/stripe",
                data=json.dumps(webhook_payload),
                headers={"stripe-signature": "t=123,v1=signature"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["processed"] is True
        assert "customer.created" in data["message"]

    @patch('backend.api.billing.get_billing_service')
    def test_billing_health_check_enabled(self, mock_get_service, client, mock_stripe_service):
        """Test health check when billing is enabled"""
        mock_get_service.return_value = mock_stripe_service
        mock_stripe_service.is_enabled.return_value = True
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["stripe_configured"] is True

    @patch('backend.api.billing.get_billing_service')
    def test_billing_health_check_disabled(self, mock_get_service, client, mock_stripe_service):
        """Test health check when billing is disabled"""
        mock_get_service.return_value = mock_stripe_service
        mock_stripe_service.is_enabled.return_value = False
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["stripe_configured"] is False
        assert "billing functionality unavailable" in data["message"]

    @patch('backend.api.billing.get_billing_service')
    def test_billing_health_check_error(self, mock_get_service, client, mock_stripe_service):
        """Test health check with service error"""
        mock_get_service.return_value = mock_stripe_service
        mock_stripe_service.is_enabled.side_effect = Exception("Service error")
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "Service error" in data["error"]


class TestBillingIntegration:
    """Integration tests for billing API with authentication"""

    @pytest.fixture
    def app(self):
        """Create test app with billing routes"""
        from fastapi import FastAPI
        from backend.api.billing import router
        
        app = FastAPI()
        app.include_router(router, prefix="/api/billing")
        return app

    @pytest.fixture
    def authenticated_client(self, app):
        """Create authenticated test client"""
        client = TestClient(app)
        
        # Mock authentication
        with patch('backend.api.billing.get_current_active_user') as mock_auth:
            mock_user = Mock(spec=User)
            mock_user.id = 1
            mock_user.stripe_customer_id = "cus_123"
            mock_auth.return_value = mock_user
            yield client

    @patch('backend.api.billing.get_billing_service')
    def test_end_to_end_checkout_flow(self, mock_get_service, authenticated_client, mock_stripe_service):
        """Test complete checkout flow"""
        mock_get_service.return_value = mock_stripe_service
        mock_stripe_service.create_checkout_session.return_value = {
            "session_id": "cs_test_123",
            "checkout_url": "https://checkout.stripe.com/pay/cs_test_123"
        }
        
        # Test checkout session creation
        response = authenticated_client.post("/api/billing/checkout", json={
            "tier": "premium",
            "success_url": "https://app.example.com/success?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": "https://app.example.com/pricing"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"].startswith("cs_test_")
        assert "checkout.stripe.com" in data["checkout_url"]

    @patch('backend.api.billing.get_billing_service')
    def test_subscription_management_flow(self, mock_get_service, authenticated_client, mock_stripe_service):
        """Test subscription info and portal access"""
        mock_get_service.return_value = mock_stripe_service
        
        # Mock subscription info
        mock_stripe_service.get_subscription_info.return_value = {
            "tier": "premium",
            "status": "active",
            "has_active_subscription": True,
            "subscription_end_date": "2024-12-31T23:59:59+00:00",
            "tier_limits": {"max_posts_per_day": 50, "max_social_accounts": 10},
            "tier_features": ["premium_image_generation", "autonomous_posting"],
            "stripe_customer_id": "cus_123"
        }
        
        # Test subscription info
        response = authenticated_client.get("/api/billing/subscription")
        assert response.status_code == 200
        sub_data = response.json()
        assert sub_data["tier"] == "premium"
        assert sub_data["has_active_subscription"] is True
        
        # Mock customer portal
        mock_stripe_service.create_customer_portal_session.return_value = "https://billing.stripe.com/session_abc"
        
        # Test customer portal access
        response = authenticated_client.post("/api/billing/customer-portal", json={
            "return_url": "https://app.example.com/billing"
        })
        assert response.status_code == 200
        portal_data = response.json()
        assert "billing.stripe.com" in portal_data["portal_url"]


if __name__ == "__main__":
    pytest.main([__file__])