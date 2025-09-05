"""
Unit tests for subscription tier enforcement
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from unittest.mock import Mock, patch

from backend.middleware.subscription_enforcement import SubscriptionDependencies
from backend.services.subscription_service import SubscriptionTier
from backend.auth.dependencies import AuthUser


class TestSubscriptionEnforcement:
    """Test subscription tier enforcement functionality"""

    def test_require_feature_basic_tier_success(self):
        """Test that basic tier can access basic features"""
        # Mock current user
        mock_user = Mock(spec=AuthUser)
        mock_user.user_id = "1"
        
        # Mock subscription service
        mock_service = Mock()
        mock_service.has_feature.return_value = True
        
        # Test the dependency
        dependency = SubscriptionDependencies.require_feature("basic_posting")
        result = dependency(current_user=mock_user, subscription_service=mock_service)
        
        assert result is None
        mock_service.has_feature.assert_called_once_with(1, "basic_posting")

    def test_require_feature_insufficient_tier(self):
        """Test that insufficient tier raises HTTPException"""
        # Mock current user
        mock_user = Mock(spec=AuthUser)
        mock_user.user_id = "1"
        
        # Mock subscription service
        mock_service = Mock()
        mock_service.has_feature.return_value = False
        mock_service.get_user_tier.return_value = SubscriptionTier.BASIC
        
        # Test the dependency
        dependency = SubscriptionDependencies.require_feature("premium_image_generation")
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(current_user=mock_user, subscription_service=mock_service)
        
        assert exc_info.value.status_code == 403
        assert "insufficient_tier" in str(exc_info.value.detail)

    def test_require_tier_hierarchy_enforcement(self):
        """Test that tier hierarchy is properly enforced"""
        # Mock current user
        mock_user = Mock(spec=AuthUser)
        mock_user.user_id = "1"
        
        # Mock subscription service
        mock_service = Mock()
        mock_service.get_user_tier.return_value = SubscriptionTier.BASIC
        
        # Test requiring premium tier with basic user
        dependency = SubscriptionDependencies.require_tier(SubscriptionTier.PREMIUM)
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(current_user=mock_user, subscription_service=mock_service)
        
        assert exc_info.value.status_code == 403
        assert "insufficient_tier" in str(exc_info.value.detail)

    def test_check_usage_limit_within_limits(self):
        """Test that usage within limits passes"""
        # Mock current user
        mock_user = Mock(spec=AuthUser)
        mock_user.user_id = "1"
        
        # Mock subscription service
        mock_service = Mock()
        mock_service.get_tier_limits.return_value = {"max_image_generations_per_day": 5}
        
        # Test usage limit check
        dependency = SubscriptionDependencies.check_usage_limit("max_image_generations_per_day")
        result = dependency(current_user=mock_user, subscription_service=mock_service)
        
        assert result is None

    def test_check_usage_limit_no_feature_access(self):
        """Test that users without feature access get proper error"""
        # Mock current user
        mock_user = Mock(spec=AuthUser)
        mock_user.user_id = "1"
        
        # Mock subscription service
        mock_service = Mock()
        mock_service.get_tier_limits.return_value = {"max_image_generations_per_day": 0}
        mock_service.get_user_tier.return_value = SubscriptionTier.BASIC
        
        # Test usage limit check
        dependency = SubscriptionDependencies.check_usage_limit("max_image_generations_per_day")
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(current_user=mock_user, subscription_service=mock_service)
        
        assert exc_info.value.status_code == 403
        assert "feature_not_available" in str(exc_info.value.detail)

    def test_get_user_context(self):
        """Test that user context is properly returned"""
        # Mock current user
        mock_user = Mock(spec=AuthUser)
        mock_user.user_id = "1"
        
        # Mock subscription service
        mock_service = Mock()
        mock_service.get_user_tier.return_value = SubscriptionTier.PREMIUM
        mock_service.get_tier_features.return_value = {"premium_image_generation", "autonomous_posting"}
        mock_service.get_tier_limits.return_value = {"max_posts_per_day": 50}
        
        # Test user context dependency
        dependency = SubscriptionDependencies.get_user_context()
        result = dependency(current_user=mock_user, subscription_service=mock_service)
        
        assert result["user_id"] == 1
        assert result["tier"] == SubscriptionTier.PREMIUM
        assert "premium_image_generation" in result["features"]
        assert result["limits"]["max_posts_per_day"] == 50


class TestTierProtectedEndpoints:
    """Test API endpoints with tier protection"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from app import app
        return TestClient(app)

    @patch('backend.middleware.subscription_enforcement.get_current_user')
    @patch('backend.middleware.subscription_enforcement.get_subscription_service_dep')
    def test_image_generation_requires_basic_tier(self, mock_service_dep, mock_user, client):
        """Test that image generation requires at least basic tier"""
        # Mock user without basic image generation
        mock_user.return_value = Mock(user_id="1")
        
        mock_service = Mock()
        mock_service.has_feature.return_value = False
        mock_service.get_user_tier.return_value = SubscriptionTier.BASIC
        mock_service.get_tier_limits.return_value = {"max_image_generations_per_day": 0}
        mock_service_dep.return_value = mock_service
        
        # Test image generation endpoint
        response = client.post("/api/content/generate-image", json={
            "prompt": "test image",
            "platform": "twitter",
            "quality_preset": "standard",
            "tone": "professional"
        })
        
        assert response.status_code == 403
        assert "feature_not_available" in response.json()["detail"]["error"]

    @patch('backend.middleware.subscription_enforcement.get_current_user')
    @patch('backend.middleware.subscription_enforcement.get_subscription_service_dep')
    def test_autonomous_posting_requires_premium_tier(self, mock_service_dep, mock_user, client):
        """Test that autonomous posting requires premium tier"""
        # Mock basic tier user
        mock_user.return_value = Mock(user_id="1")
        
        mock_service = Mock()
        mock_service.has_feature.return_value = False
        mock_service.get_user_tier.return_value = SubscriptionTier.BASIC
        mock_service_dep.return_value = mock_service
        
        # Test autonomous execute cycle endpoint
        response = client.post("/api/autonomous/execute-cycle")
        
        assert response.status_code == 403
        assert "insufficient_tier" in response.json()["detail"]["error"]


if __name__ == "__main__":
    pytest.main([__file__])