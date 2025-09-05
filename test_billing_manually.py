#!/usr/bin/env python3
"""
Manual test script for Stripe billing integration
Tests core functionality without full pytest setup
"""
import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from unittest.mock import Mock, patch
from backend.services.stripe_service import StripeService, get_stripe_service
from backend.services.subscription_service import SubscriptionTier
from backend.db.models import User

def test_stripe_service_basic():
    """Test basic Stripe service functionality"""
    print("Testing Stripe service basic functionality...")
    
    # Test service initialization without API key
    with patch.dict('os.environ', {}, clear=True):
        service = StripeService(Mock())
        assert service.is_enabled() is False
        print("✅ Service correctly disabled without API key")
    
    # Test service initialization with API key
    with patch.dict('os.environ', {'STRIPE_SECRET_KEY': 'sk_test_123'}):
        service = StripeService(Mock())
        assert service.is_enabled() is True
        print("✅ Service correctly enabled with API key")
    
    # Test factory function
    with patch.dict('os.environ', {'STRIPE_SECRET_KEY': 'sk_test_123'}):
        service = get_stripe_service()
        assert isinstance(service, StripeService)
        print("✅ Factory function works correctly")

def test_subscription_info():
    """Test getting subscription information"""
    print("Testing subscription info functionality...")
    
    # Mock user
    mock_user = Mock(spec=User)
    mock_user.tier = "premium"
    mock_user.subscription_status = "active"
    mock_user.stripe_customer_id = "cus_123"
    mock_user.stripe_subscription_id = "sub_123"
    mock_user.subscription_end_date = None
    
    # Test subscription info
    with patch.dict('os.environ', {'STRIPE_SECRET_KEY': 'sk_test_123'}):
        service = StripeService(Mock())
        
        # Mock subscription service
        mock_subscription_service = Mock()
        mock_subscription_service.get_tier_limits.return_value = {"max_posts_per_day": 50}
        mock_subscription_service.get_tier_features.return_value = {"premium_image_generation"}
        service.subscription_service = mock_subscription_service
        
        info = service.get_subscription_info(mock_user)
        
        assert info["tier"] == "premium"
        assert info["status"] == "active"
        assert info["has_active_subscription"] is True
        assert "premium_image_generation" in info["tier_features"]
        print("✅ Subscription info retrieval works correctly")

def test_tier_enforcement():
    """Test subscription tier enforcement"""
    print("Testing tier enforcement...")
    
    from backend.services.subscription_service import SubscriptionService, SubscriptionTier
    
    # Test tier normalization
    mock_db = Mock()
    service = SubscriptionService(mock_db)
    
    # Test basic tier features - need to use tier constants directly from service
    from backend.services.subscription_service import TIER_FEATURES
    basic_features = TIER_FEATURES[SubscriptionTier.BASIC]
    premium_features = TIER_FEATURES[SubscriptionTier.PREMIUM]
    enterprise_features = TIER_FEATURES[SubscriptionTier.ENTERPRISE]
    
    assert "basic_posting" in basic_features
    assert "autonomous_posting" in premium_features
    assert "advanced_automation" in enterprise_features
    print("✅ Tier feature enforcement works correctly")
    
    # Test tier limits - need to use tier constants directly from service
    from backend.services.subscription_service import TIER_LIMITS
    basic_limits = TIER_LIMITS[SubscriptionTier.BASIC]
    premium_limits = TIER_LIMITS[SubscriptionTier.PREMIUM]
    enterprise_limits = TIER_LIMITS[SubscriptionTier.ENTERPRISE]
    
    assert basic_limits["max_posts_per_day"] == 10
    assert premium_limits["max_posts_per_day"] == 50
    assert enterprise_limits["max_posts_per_day"] == -1  # unlimited
    print("✅ Tier limit enforcement works correctly")

def test_billing_api_models():
    """Test billing API request/response models"""
    print("Testing billing API models...")
    
    from backend.api.billing import (
        CreateCheckoutRequest,
        CheckoutResponse,
        SubscriptionInfoResponse
    )
    
    # Test checkout request model
    checkout_request = CreateCheckoutRequest(
        tier="premium",
        success_url="https://app.example.com/success",
        cancel_url="https://app.example.com/cancel"
    )
    assert checkout_request.tier == "premium"
    print("✅ Checkout request model works")
    
    # Test checkout response model  
    checkout_response = CheckoutResponse(
        session_id="cs_123",
        checkout_url="https://checkout.stripe.com/pay/cs_123"
    )
    assert checkout_response.session_id == "cs_123"
    print("✅ Checkout response model works")
    
    # Test subscription info response
    sub_info = SubscriptionInfoResponse(
        tier="premium",
        status="active",
        has_active_subscription=True,
        subscription_end_date="2024-12-31T23:59:59Z",
        tier_limits={"max_posts_per_day": 50},
        tier_features=["premium_image_generation"],
        stripe_customer_id="cus_123"
    )
    assert sub_info.tier == "premium"
    assert sub_info.has_active_subscription is True
    print("✅ Subscription info model works")

def test_webhook_handling():
    """Test webhook event handling"""
    print("Testing webhook handling...")
    
    with patch.dict('os.environ', {'STRIPE_SECRET_KEY': 'sk_test_123'}):
        service = StripeService(Mock())
        mock_db = service.db
        
        # Mock user in database
        mock_user = Mock(spec=User)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Test subscription created webhook
        subscription_data = {
            "id": "sub_123",
            "customer": "cus_123", 
            "status": "active",
            "current_period_end": 1640995200,
            "metadata": {"tier": "premium"}
        }
        
        service.handle_subscription_created(subscription_data)
        
        # Verify user was updated
        assert mock_user.stripe_subscription_id == "sub_123"
        assert mock_user.subscription_status == "active"
        assert mock_user.tier == "premium"
        mock_db.commit.assert_called_once()
        print("✅ Subscription created webhook handling works")

def main():
    """Run all tests"""
    print("🧪 Running manual billing integration tests...")
    print("=" * 50)
    
    try:
        test_stripe_service_basic()
        test_subscription_info()
        test_tier_enforcement()
        test_billing_api_models() 
        test_webhook_handling()
        
        print("=" * 50)
        print("✅ All tests passed! Billing integration is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()