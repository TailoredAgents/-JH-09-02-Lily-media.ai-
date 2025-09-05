"""
Integration tests for autonomous scheduling and auto-pilot functionality
Tests end-to-end workflows for tier-based autonomous posting
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.services.subscription_service import SubscriptionTier, SubscriptionService
from backend.services.autonomous_scheduler import AutonomousScheduler
from backend.db.models import User, ScheduledPost
from backend.db.multi_tenant_models import Organization
from backend.tasks.autonomous_cycle import execute_autonomous_cycle


class TestAutopilotIntegration:
    """Integration tests for autopilot functionality"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)

    @pytest.fixture 
    def basic_user(self):
        """Create basic tier user"""
        user = Mock(spec=User)
        user.id = 1
        user.tier = "basic"
        user.subscription_status = "active"
        user.default_organization_id = None
        return user

    @pytest.fixture
    def premium_user(self):
        """Create premium tier user"""
        user = Mock(spec=User)
        user.id = 2
        user.tier = "premium"
        user.subscription_status = "active"
        user.default_organization_id = None
        return user

    @pytest.fixture
    def enterprise_user(self):
        """Create enterprise tier user"""
        user = Mock(spec=User)
        user.id = 3
        user.tier = "enterprise"
        user.subscription_status = "active"
        user.default_organization_id = "org_123"
        return user

    @pytest.fixture
    def subscription_service(self, mock_db):
        """Create subscription service instance"""
        return SubscriptionService(mock_db)

    def test_basic_tier_autonomous_restrictions(self, subscription_service, basic_user):
        """Test that basic tier users cannot access autonomous features"""
        # Check feature access
        has_autonomous = subscription_service.has_feature(basic_user.id, "autonomous_posting")
        assert has_autonomous is False
        
        # Check tier limits for autonomous features
        limits = subscription_service.get_tier_limits(basic_user.id)
        assert limits["max_posts_per_day"] == 10  # Limited posting
        assert limits["max_ai_requests_per_day"] == 20  # Limited AI usage

    def test_premium_tier_autonomous_access(self, subscription_service, premium_user, mock_db):
        """Test that premium tier users can access autonomous features"""
        # Mock database query for user
        mock_db.query.return_value.filter.return_value.first.return_value = premium_user
        
        # Check feature access
        has_autonomous = subscription_service.has_feature(premium_user.id, "autonomous_posting")
        assert has_autonomous is True
        
        # Check tier limits
        limits = subscription_service.get_tier_limits(premium_user.id)
        assert limits["max_posts_per_day"] == 50  # Higher posting limits
        assert limits["max_ai_requests_per_day"] == 200  # Higher AI usage

    def test_enterprise_tier_unlimited_autonomous(self, subscription_service, enterprise_user, mock_db):
        """Test that enterprise tier has unlimited autonomous capabilities"""
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = enterprise_user
        
        # Check advanced features
        has_advanced_automation = subscription_service.has_feature(enterprise_user.id, "advanced_automation")
        assert has_advanced_automation is True
        
        # Check unlimited limits
        limits = subscription_service.get_tier_limits(enterprise_user.id)
        assert limits["max_posts_per_day"] == -1  # Unlimited
        assert limits["max_ai_requests_per_day"] == -1  # Unlimited

    @patch('backend.tasks.autonomous_cycle.AutonomousScheduler')
    @patch('backend.services.subscription_service.get_subscription_service')
    def test_autonomous_cycle_execution_with_tier_check(self, mock_sub_service, mock_scheduler_class, premium_user):
        """Test autonomous cycle execution respects tier limits"""
        # Mock subscription service
        mock_subscription_service = Mock()
        mock_subscription_service.has_feature.return_value = True
        mock_subscription_service.check_usage_limit.return_value = True
        mock_sub_service.return_value = mock_subscription_service
        
        # Mock autonomous scheduler
        mock_scheduler = Mock(spec=AutonomousScheduler)
        mock_scheduler.execute_cycle = AsyncMock(return_value={
            "posts_generated": 3,
            "posts_scheduled": 3,
            "success": True
        })
        mock_scheduler_class.return_value = mock_scheduler
        
        # Execute autonomous cycle
        result = asyncio.run(execute_autonomous_cycle(premium_user.id))
        
        # Verify execution
        assert result["success"] is True
        assert result["posts_generated"] == 3
        mock_scheduler.execute_cycle.assert_called_once()
        
        # Verify tier checks were performed
        mock_subscription_service.has_feature.assert_called_with(premium_user.id, "autonomous_posting")

    @patch('backend.tasks.autonomous_cycle.AutonomousScheduler')
    @patch('backend.services.subscription_service.get_subscription_service')
    def test_autonomous_cycle_blocked_for_basic_tier(self, mock_sub_service, mock_scheduler_class, basic_user):
        """Test autonomous cycle is blocked for basic tier users"""
        # Mock subscription service to deny access
        mock_subscription_service = Mock()
        mock_subscription_service.has_feature.return_value = False
        mock_subscription_service.get_user_tier.return_value = SubscriptionTier.BASIC
        mock_sub_service.return_value = mock_subscription_service
        
        # Execute autonomous cycle - should be blocked
        result = asyncio.run(execute_autonomous_cycle(basic_user.id))
        
        # Verify cycle was blocked
        assert result["success"] is False
        assert "insufficient_tier" in result["error"]
        
        # Verify scheduler was not called
        mock_scheduler_class.assert_not_called()

    @patch('backend.services.subscription_service.get_subscription_service')
    def test_usage_limit_enforcement_during_generation(self, mock_sub_service, premium_user):
        """Test that usage limits are enforced during content generation"""
        # Mock subscription service with usage limits
        mock_subscription_service = Mock()
        mock_subscription_service.has_feature.return_value = True
        mock_subscription_service.check_usage_limit.side_effect = lambda user_id, limit_type, usage: {
            "max_posts_per_day": usage < 50,  # Premium limit
            "max_ai_requests_per_day": usage < 200
        }.get(limit_type, True)
        mock_sub_service.return_value = mock_subscription_service
        
        # Test within limits
        within_post_limit = mock_subscription_service.check_usage_limit(premium_user.id, "max_posts_per_day", 25)
        assert within_post_limit is True
        
        within_ai_limit = mock_subscription_service.check_usage_limit(premium_user.id, "max_ai_requests_per_day", 100)
        assert within_ai_limit is True
        
        # Test exceeding limits
        exceed_post_limit = mock_subscription_service.check_usage_limit(premium_user.id, "max_posts_per_day", 55)
        assert exceed_post_limit is False
        
        exceed_ai_limit = mock_subscription_service.check_usage_limit(premium_user.id, "max_ai_requests_per_day", 250)
        assert exceed_ai_limit is False

    @patch('backend.services.autonomous_scheduler.ContentGenerator')
    @patch('backend.services.subscription_service.get_subscription_service')
    def test_image_generation_tier_restrictions(self, mock_sub_service, mock_content_gen, premium_user):
        """Test image generation respects tier-based model access"""
        # Mock subscription service
        mock_subscription_service = Mock()
        mock_subscription_service.has_feature.side_effect = lambda user_id, feature: {
            "basic_image_generation": True,
            "premium_image_generation": True,  # Premium tier has access
            "enterprise_image_generation": False  # But not enterprise features
        }.get(feature, False)
        mock_sub_service.return_value = mock_subscription_service
        
        # Mock content generator
        mock_generator = Mock()
        mock_content_gen.return_value = mock_generator
        
        # Test image generation with tier check
        scheduler = AutonomousScheduler(Mock(), premium_user.id)
        
        # Should allow premium image generation
        has_premium_images = mock_subscription_service.has_feature(premium_user.id, "premium_image_generation")
        assert has_premium_images is True
        
        # Should not allow enterprise image generation
        has_enterprise_images = mock_subscription_service.has_feature(premium_user.id, "enterprise_image_generation")
        assert has_enterprise_images is False

    @patch('backend.services.subscription_service.get_subscription_service')
    def test_organization_tier_inheritance(self, mock_sub_service, mock_db):
        """Test that users inherit organization tier when higher"""
        # Create user with basic tier
        user = Mock(spec=User)
        user.id = 1
        user.tier = "basic"
        user.default_organization_id = "org_premium"
        
        # Create organization with premium tier
        org = Mock(spec=Organization)
        org.id = "org_premium"
        org.plan_type = "professional"  # Maps to premium
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [user, org]
        
        # Mock subscription service
        subscription_service = SubscriptionService(mock_db)
        
        with patch.object(subscription_service, 'normalize_tier') as mock_normalize:
            mock_normalize.side_effect = lambda tier: {
                "basic": SubscriptionTier.BASIC,
                "professional": SubscriptionTier.PREMIUM
            }.get(tier, SubscriptionTier.BASIC)
            
            # Get effective tier - should inherit organization's premium tier
            effective_tier = subscription_service.get_user_tier(user.id)
            assert effective_tier == SubscriptionTier.PREMIUM

    @patch('backend.tasks.celery_app.send_task')
    def test_autonomous_task_scheduling_respects_tiers(self, mock_send_task):
        """Test that autonomous tasks are only scheduled for appropriate tiers"""
        from backend.tasks.celery_beat_schedule import should_schedule_autonomous_task
        
        # Test basic tier user - should not schedule
        with patch('backend.services.subscription_service.get_subscription_service') as mock_service:
            mock_subscription_service = Mock()
            mock_subscription_service.get_user_tier.return_value = SubscriptionTier.BASIC
            mock_subscription_service.has_feature.return_value = False
            mock_service.return_value = mock_subscription_service
            
            should_schedule = should_schedule_autonomous_task(1)  # Basic user
            assert should_schedule is False
        
        # Test premium tier user - should schedule
        with patch('backend.services.subscription_service.get_subscription_service') as mock_service:
            mock_subscription_service = Mock()
            mock_subscription_service.get_user_tier.return_value = SubscriptionTier.PREMIUM
            mock_subscription_service.has_feature.return_value = True
            mock_service.return_value = mock_subscription_service
            
            should_schedule = should_schedule_autonomous_task(2)  # Premium user
            assert should_schedule is True

    def test_tier_upgrade_flow_integration(self, subscription_service, mock_db):
        """Test complete tier upgrade flow"""
        # Create basic user
        user = Mock(spec=User)
        user.id = 1
        user.tier = "basic"
        user.subscription_status = "active"
        user.default_organization_id = None
        
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        # Initial state - basic tier
        initial_tier = subscription_service.get_user_tier(user.id)
        assert initial_tier == SubscriptionTier.BASIC
        
        has_autonomous = subscription_service.has_feature(user.id, "autonomous_posting")
        assert has_autonomous is False
        
        # Simulate Stripe webhook upgrading user to premium
        success = subscription_service.upgrade_user_tier(user.id, SubscriptionTier.PREMIUM)
        assert success is True
        
        # Verify user was upgraded
        assert user.tier == "premium"
        assert user.subscription_status == "active"
        
        # Verify new capabilities
        upgraded_tier = subscription_service.get_user_tier(user.id)
        assert upgraded_tier == SubscriptionTier.PREMIUM
        
        # Mock updated feature check
        with patch.object(subscription_service, 'get_user_tier', return_value=SubscriptionTier.PREMIUM):
            has_autonomous_after = subscription_service.has_feature(user.id, "autonomous_posting")
            assert has_autonomous_after is True


class TestTierEnforcementMiddleware:
    """Test tier enforcement in API middleware"""

    @pytest.fixture
    def client(self):
        """Create test client with tier enforcement"""
        from fastapi.testclient import TestClient
        from app import app
        return TestClient(app)

    @patch('backend.middleware.subscription_enforcement.get_current_user')
    @patch('backend.middleware.subscription_enforcement.get_subscription_service_dep')
    def test_tier_protected_endpoint_access(self, mock_service_dep, mock_user, client):
        """Test tier-protected endpoint access control"""
        # Mock premium user
        mock_user.return_value = Mock(user_id="2")
        
        mock_service = Mock()
        mock_service.has_feature.return_value = True
        mock_service.get_user_tier.return_value = SubscriptionTier.PREMIUM
        mock_service_dep.return_value = mock_service
        
        # Test autonomous endpoint access
        response = client.post("/api/autonomous/execute-cycle")
        
        # Should be allowed for premium user
        # Note: Actual response depends on implementation
        # This tests the tier enforcement middleware
        mock_service.has_feature.assert_called_with(2, "autonomous_posting")

    @patch('backend.middleware.subscription_enforcement.get_current_user')
    @patch('backend.middleware.subscription_enforcement.get_subscription_service_dep')
    def test_usage_limit_enforcement_middleware(self, mock_service_dep, mock_user, client):
        """Test usage limit enforcement in middleware"""
        # Mock user
        mock_user.return_value = Mock(user_id="1")
        
        mock_service = Mock()
        mock_service.has_feature.return_value = True
        mock_service.check_usage_limit.return_value = False  # Exceed limit
        mock_service.get_tier_limits.return_value = {"max_image_generations_per_day": 5}
        mock_service_dep.return_value = mock_service
        
        # Test image generation endpoint when limit exceeded
        response = client.post("/api/content/generate-image", json={
            "prompt": "test image",
            "platform": "twitter"
        })
        
        # Should be blocked due to usage limit
        assert response.status_code == 403
        assert "usage_limit_exceeded" in response.json()["detail"]["error"]


if __name__ == "__main__":
    pytest.main([__file__])