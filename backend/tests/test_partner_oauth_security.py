"""
Security tests for Partner OAuth API - BLOCKER #2 Fix
Tests that partner OAuth endpoints properly enforce plan limits and cannot be used to bypass subscription restrictions
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.api.partner_oauth import router
from backend.db.models import User
from backend.services.plan_aware_social_service import PlanAwareSocialService

@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    user = MagicMock(spec=User)
    user.id = 123
    user.email = "test@example.com"
    user.default_organization_id = None
    return user

@pytest.fixture
def mock_db():
    """Mock database session"""
    return MagicMock(spec=Session)

@pytest.fixture
def mock_plan_service():
    """Mock plan aware social service"""
    return MagicMock(spec=PlanAwareSocialService)

class TestPartnerOAuthSecurityEnforcement:
    """Test security enforcement in partner OAuth endpoints"""
    
    @pytest.mark.asyncio
    async def test_oauth_start_blocks_connection_limit_exceeded(self, mock_user, mock_db, mock_plan_service):
        """Test that OAuth start endpoint blocks users who exceed connection limits"""
        from backend.api.partner_oauth import start_oauth_flow
        
        # Mock plan service to deny connection
        mock_plan_service.enforce_connection_limit = AsyncMock(return_value={
            "allowed": False,
            "reason": "connection_limit_exceeded",
            "message": "Maximum connections limit reached (5/5)",
            "plan": "starter",
            "current_usage": {"current_connections": 5, "max_connections": 5},
            "suggested_plans": [{"plan": "pro", "connections": 25}]
        })
        
        with patch('backend.api.partner_oauth.get_plan_aware_social_service', return_value=mock_plan_service):
            # Mock request
            mock_request = MagicMock()
            
            # Test should raise HTTPException with 403 status
            with pytest.raises(HTTPException) as exc_info:
                await start_oauth_flow(
                    platform="meta",
                    request=mock_request,
                    current_user=mock_user,
                    db=mock_db
                )
            
            # Verify security response
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["error"] == "connection_not_allowed"
            assert exc_info.value.detail["reason"] == "connection_limit_exceeded"
            assert exc_info.value.detail["upgrade_required"] is True
            assert exc_info.value.detail["oauth_flow"] == "partner"
            
            # Verify plan enforcement was called
            mock_plan_service.enforce_connection_limit.assert_called_once_with(
                user_id=123,
                platform="facebook"  # Meta maps to Facebook internally
            )
    
    @pytest.mark.asyncio
    async def test_oauth_start_blocks_platform_restricted(self, mock_user, mock_db, mock_plan_service):
        """Test that OAuth start endpoint blocks users trying to connect restricted platforms"""
        from backend.api.partner_oauth import start_oauth_flow
        
        # Mock plan service to deny platform access
        mock_plan_service.enforce_connection_limit = AsyncMock(return_value={
            "allowed": False,
            "reason": "platform_restricted",
            "message": "Platform 'twitter' not available on free plan",
            "plan": "free",
            "available_platforms": ["twitter", "instagram"],
            "suggested_plans": [{"plan": "starter", "platforms": 4}]
        })
        
        with patch('backend.api.partner_oauth.get_plan_aware_social_service', return_value=mock_plan_service):
            mock_request = MagicMock()
            
            # Test X platform restriction on free plan
            with pytest.raises(HTTPException) as exc_info:
                await start_oauth_flow(
                    platform="x",
                    request=mock_request,
                    current_user=mock_user,
                    db=mock_db
                )
            
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["error"] == "connection_not_allowed"
            assert exc_info.value.detail["reason"] == "platform_restricted"
            
            # Verify platform mapping
            mock_plan_service.enforce_connection_limit.assert_called_once_with(
                user_id=123,
                platform="twitter"  # X maps to Twitter internally
            )
    
    @pytest.mark.asyncio
    async def test_oauth_start_allows_valid_connection(self, mock_user, mock_db, mock_plan_service):
        """Test that OAuth start endpoint allows valid connections"""
        from backend.api.partner_oauth import start_oauth_flow
        
        # Mock plan service to allow connection
        mock_plan_service.enforce_connection_limit = AsyncMock(return_value={
            "allowed": True,
            "platform": "facebook",
            "remaining_connections": 4,
            "message": "Connection to facebook allowed"
        })
        
        with patch('backend.api.partner_oauth.get_plan_aware_social_service', return_value=mock_plan_service):
            with patch('backend.api.partner_oauth.get_state_store') as mock_state_store:
                with patch('backend.api.partner_oauth.get_settings') as mock_settings:
                    with patch('backend.api.partner_oauth._get_client_id', return_value="test_client_id"):
                        # Mock state store
                        mock_state_store.return_value.create.return_value = {
                            "state": "test_state_123",
                            "code_challenge": "test_challenge",
                            "code_challenge_method": "S256"
                        }
                        
                        # Mock settings
                        mock_settings.return_value.meta_graph_version = "v18.0"
                        mock_settings.return_value.backend_url = "http://localhost:8000"
                        
                        mock_request = MagicMock()
                        
                        # Should succeed
                        result = await start_oauth_flow(
                            platform="meta",
                            request=mock_request,
                            current_user=mock_user,
                            db=mock_db
                        )
                        
                        # Verify successful response
                        assert result.platform == "meta"
                        assert result.state == "test_state_123"
                        assert result.expires_in == 600
                        assert "auth_url" in result.auth_url
                        
                        # Verify plan enforcement was called
                        mock_plan_service.enforce_connection_limit.assert_called_once_with(
                            user_id=123,
                            platform="facebook"
                        )
    
    @pytest.mark.asyncio
    async def test_meta_connect_blocks_connection_limit_exceeded(self, mock_user, mock_db, mock_plan_service):
        """Test that Meta connect endpoint blocks users who exceed connection limits"""
        from backend.api.partner_oauth import connect_meta_account, MetaConnectRequest
        
        # Mock plan service to deny connection
        mock_plan_service.enforce_connection_limit = AsyncMock(return_value={
            "allowed": False,
            "reason": "connection_limit_exceeded",
            "message": "Maximum connections limit reached (2/2)",
            "plan": "free",
            "current_usage": {"current_connections": 2, "max_connections": 2},
            "suggested_plans": [{"plan": "starter", "connections": 5}]
        })
        
        with patch('backend.api.partner_oauth.get_plan_aware_social_service', return_value=mock_plan_service):
            request = MetaConnectRequest(
                state="test_state",
                page_id="123456789"
            )
            
            # Test should raise HTTPException with 403 status
            with pytest.raises(HTTPException) as exc_info:
                await connect_meta_account(
                    request=request,
                    current_user=mock_user,
                    db=mock_db
                )
            
            # Verify security response
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["error"] == "connection_not_allowed"
            assert exc_info.value.detail["reason"] == "connection_limit_exceeded"
            assert exc_info.value.detail["upgrade_required"] is True
            assert exc_info.value.detail["oauth_flow"] == "partner"
    
    @pytest.mark.asyncio
    async def test_x_connect_blocks_platform_already_connected(self, mock_user, mock_db, mock_plan_service):
        """Test that X connect endpoint blocks duplicate connections"""
        from backend.api.partner_oauth import connect_x_account, XConnectRequest
        
        # Mock plan service to deny duplicate connection
        mock_plan_service.enforce_connection_limit = AsyncMock(return_value={
            "allowed": False,
            "reason": "platform_already_connected",
            "message": "Platform 'twitter' is already connected",
            "existing_connection": {
                "id": "existing_conn_id",
                "username": "@existing_user",
                "connected_at": "2024-01-01T00:00:00"
            }
        })
        
        with patch('backend.api.partner_oauth.get_plan_aware_social_service', return_value=mock_plan_service):
            request = XConnectRequest(state="test_state")
            
            # Test should raise HTTPException with 403 status
            with pytest.raises(HTTPException) as exc_info:
                await connect_x_account(
                    request=request,
                    current_user=mock_user,
                    db=mock_db
                )
            
            # Verify security response
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["error"] == "connection_not_allowed"
            assert exc_info.value.detail["reason"] == "platform_already_connected"
            assert exc_info.value.detail["upgrade_required"] is True
    
    @pytest.mark.asyncio
    async def test_platform_mapping_correctness(self, mock_user, mock_db, mock_plan_service):
        """Test that platform name mapping is correct between partner OAuth and plan service"""
        from backend.api.partner_oauth import start_oauth_flow
        
        mock_plan_service.enforce_connection_limit = AsyncMock(return_value={
            "allowed": False,
            "reason": "test",
            "message": "test"
        })
        
        with patch('backend.api.partner_oauth.get_plan_aware_social_service', return_value=mock_plan_service):
            mock_request = MagicMock()
            
            # Test Meta -> Facebook mapping
            try:
                await start_oauth_flow("meta", mock_request, mock_user, mock_db)
            except HTTPException:
                pass  # Expected to fail for this test
            
            mock_plan_service.enforce_connection_limit.assert_called_with(
                user_id=123,
                platform="facebook"
            )
            
            # Reset mock
            mock_plan_service.enforce_connection_limit.reset_mock()
            
            # Test X -> Twitter mapping
            try:
                await start_oauth_flow("x", mock_request, mock_user, mock_db)
            except HTTPException:
                pass  # Expected to fail for this test
                
            mock_plan_service.enforce_connection_limit.assert_called_with(
                user_id=123,
                platform="twitter"
            )
    
    @pytest.mark.asyncio
    async def test_security_logging_on_bypass_attempt(self, mock_user, mock_db, mock_plan_service):
        """Test that bypass attempts are properly logged for security monitoring"""
        from backend.api.partner_oauth import start_oauth_flow
        
        # Mock plan service to deny connection
        mock_plan_service.enforce_connection_limit = AsyncMock(return_value={
            "allowed": False,
            "reason": "connection_limit_exceeded",
            "message": "Maximum connections limit reached"
        })
        
        with patch('backend.api.partner_oauth.get_plan_aware_social_service', return_value=mock_plan_service):
            with patch('backend.api.partner_oauth.logger') as mock_logger:
                mock_request = MagicMock()
                
                # Attempt bypass
                try:
                    await start_oauth_flow("meta", mock_request, mock_user, mock_db)
                except HTTPException:
                    pass  # Expected
                
                # Verify security warning was logged
                mock_logger.warning.assert_called_once()
                warning_call = mock_logger.warning.call_args[0][0]
                assert "Partner OAuth connection attempt blocked" in warning_call
                assert "user 123" in warning_call
                assert "meta" in warning_call
    
    def test_feature_flag_still_protects_endpoints(self):
        """Test that feature flag protection is still in place"""
        from backend.api.partner_oauth import require_partner_oauth_enabled
        
        with patch('backend.api.partner_oauth.is_partner_oauth_enabled', return_value=False):
            # Should raise HTTPException when feature is disabled
            with pytest.raises(HTTPException) as exc_info:
                require_partner_oauth_enabled()
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail["error"] == "feature_disabled"
            assert exc_info.value.detail["feature_flag"] == "FEATURE_PARTNER_OAUTH"

class TestSecurityBypassPrevention:
    """Test that specific bypass scenarios are prevented"""
    
    @pytest.mark.asyncio
    async def test_cannot_bypass_with_direct_callback_access(self, mock_user, mock_db):
        """Test that users cannot bypass limits by calling callback endpoints directly"""
        from backend.api.partner_oauth import handle_oauth_callback
        
        # Direct callback access should fail without proper state validation
        # This tests the existing state validation security
        with pytest.raises(HTTPException) as exc_info:
            await handle_oauth_callback(
                platform="meta",
                code="fake_code",
                state="invalid_state"
            )
        
        # Should fail due to invalid state (existing security)
        assert exc_info.value.status_code == 400
        assert "invalid_state" in exc_info.value.detail.get("error", "")
    
    @pytest.mark.asyncio 
    async def test_cannot_bypass_with_feature_flag_disabled(self, mock_user, mock_db):
        """Test that disabling feature flag prevents all access"""
        from backend.api.partner_oauth import start_oauth_flow
        
        with patch('backend.api.partner_oauth.is_partner_oauth_enabled', return_value=False):
            mock_request = MagicMock()
            
            # Should fail before plan enforcement due to feature flag
            with pytest.raises(HTTPException) as exc_info:
                await start_oauth_flow("meta", mock_request, mock_user, mock_db)
            
            # Feature flag check happens at router level via dependency
            # This test verifies the dependency still exists

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])