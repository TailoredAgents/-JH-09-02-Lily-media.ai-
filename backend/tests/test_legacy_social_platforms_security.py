"""
Security tests for legacy social platforms API - BLOCKER #2 Fix

Verifies that legacy social connection endpoints now properly enforce plan limits
and cannot be used to bypass subscription restrictions.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session

from backend.api.social_platforms import router
from backend.db.models import User
from backend.tests.conftest import test_client, test_db, test_user


class TestLegacySocialPlatformsSecurity:
    """Test plan enforcement on legacy social platforms endpoints"""
    
    def test_legacy_connect_endpoint_enforces_plan_limits(self, test_client: TestClient, test_db: Session, test_user: User):
        """Test that legacy /api/social/connect/{platform} endpoint enforces plan limits"""
        
        # Mock the plan service to deny connection
        with patch('backend.api.social_platforms.get_plan_aware_social_service') as mock_plan_service:
            mock_service = AsyncMock()
            mock_service.enforce_connection_limit.return_value = {
                "allowed": False,
                "reason": "connection_limit_exceeded", 
                "message": "Free plan allows only 1 platform connection",
                "current_usage": {"connected_platforms": 1},
                "limits": {"max_platforms": 1},
                "suggested_plans": [{"plan": "pro", "connections": 25}]
            }
            mock_plan_service.return_value = mock_service
            
            # Attempt to connect to Twitter via legacy endpoint
            response = test_client.get(
                "/api/social/connect/twitter",
                headers={"Authorization": f"Bearer {test_user.id}"}  # Mock auth
            )
            
            # Should be blocked with 403 Forbidden
            assert response.status_code == 403
            error_detail = response.json()["detail"]
            assert error_detail["error"] == "connection_not_allowed"
            assert error_detail["reason"] == "connection_limit_exceeded"
            assert "suggested_plans" in error_detail
            
            # Verify plan service was called
            mock_service.enforce_connection_limit.assert_called_once_with(
                user_id=test_user.id,
                platform="twitter"
            )
    
    def test_legacy_connect_endpoint_allows_valid_connections(self, test_client: TestClient, test_db: Session, test_user: User):
        """Test that legacy endpoint allows connections when plan permits"""
        
        with patch('backend.api.social_platforms.get_plan_aware_social_service') as mock_plan_service:
            with patch('backend.api.social_platforms.twitter_client') as mock_twitter:
                mock_service = AsyncMock()
                mock_service.enforce_connection_limit.return_value = {
                    "allowed": True,
                    "user_id": test_user.id,
                    "platform": "twitter"
                }
                mock_plan_service.return_value = mock_service
                
                # Mock Twitter OAuth response
                mock_twitter.get_oauth_authorization_url.return_value = (
                    "https://twitter.com/oauth/authorize?oauth_token=abc123",
                    "oauth_state_123"
                )
                
                response = test_client.get(
                    "/api/social/connect/twitter",
                    headers={"Authorization": f"Bearer {test_user.id}"}
                )
                
                # Should succeed with OAuth URL
                assert response.status_code == 200
                data = response.json()
                assert "authorization_url" in data
                assert data["platform"] == "twitter"
                
                # Verify plan enforcement was checked
                mock_service.enforce_connection_limit.assert_called_once()
    
    def test_legacy_callback_endpoint_enforces_plan_limits(self, test_client: TestClient, test_db: Session, test_user: User):
        """Test that legacy OAuth callback endpoint also enforces plan limits"""
        
        with patch('backend.api.social_platforms.get_plan_aware_social_service') as mock_plan_service:
            mock_service = AsyncMock()
            mock_service.enforce_connection_limit.return_value = {
                "allowed": False,
                "reason": "platform_not_allowed",
                "message": "Twitter not available on Free plan"
            }
            mock_plan_service.return_value = mock_service
            
            # Mock OAuth callback parameters
            response = test_client.get(
                "/api/social/callback/twitter?code=oauth_code_123&state={}:twitter".format(test_user.id)
            )
            
            # Should redirect with plan error
            assert response.status_code == 302
            location = response.headers["location"]
            assert "error=plan_limit" in location
            assert "reason=platform_not_allowed" in location
            
            # Verify plan service was called for callback too
            mock_service.enforce_connection_limit.assert_called_once_with(
                user_id=test_user.id,
                platform="twitter"
            )
    
    def test_unsupported_platform_validation(self, test_client: TestClient, test_user: User):
        """Test that unsupported platforms are rejected before plan enforcement"""
        
        response = test_client.get(
            "/api/social/connect/unsupported_platform",
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        assert response.status_code == 400
        assert "Unsupported platform" in response.json()["detail"]
    
    def test_security_logging_tracks_legacy_usage(self, test_client: TestClient, test_db: Session, test_user: User):
        """Test that security logging tracks usage of legacy endpoints"""
        
        with patch('backend.api.social_platforms.get_plan_aware_social_service') as mock_plan_service:
            with patch('backend.api.social_platforms.twitter_client') as mock_twitter:
                with patch('backend.api.social_platforms.log_content_event') as mock_log:
                    mock_service = AsyncMock()
                    mock_service.enforce_connection_limit.return_value = {"allowed": True}
                    mock_plan_service.return_value = mock_service
                    
                    mock_twitter.get_oauth_authorization_url.return_value = ("https://auth.url", "state")
                    
                    test_client.get(
                        "/api/social/connect/twitter",
                        headers={"Authorization": f"Bearer {test_user.id}"}
                    )
                    
                    # Verify security logging includes legacy endpoint tracking
                    mock_log.assert_called_once()
                    logged_data = mock_log.call_args[1]["additional_data"]
                    assert logged_data["endpoint_type"] == "legacy_social_platforms"
                    assert logged_data["plan_enforcement"] == "enabled"
    
    def test_plan_bypass_attempt_logging(self, test_client: TestClient, test_db: Session, test_user: User, caplog):
        """Test that plan bypass attempts are logged for security monitoring"""
        
        with patch('backend.api.social_platforms.get_plan_aware_social_service') as mock_plan_service:
            mock_service = AsyncMock()
            mock_service.enforce_connection_limit.return_value = {
                "allowed": False,
                "reason": "connection_limit_exceeded",
                "message": "Plan limit reached"
            }
            mock_plan_service.return_value = mock_service
            
            test_client.get(
                "/api/social/connect/twitter",
                headers={"Authorization": f"Bearer {test_user.id}"}
            )
            
            # Verify security warning was logged
            assert any(
                "Legacy connection attempt blocked" in record.message and 
                f"user {test_user.id}" in record.message
                for record in caplog.records
                if record.levelname == "WARNING"
            )


class TestSecurityComplianceVerification:
    """Verify the legacy endpoints comply with modern security standards"""
    
    def test_all_connection_paths_use_plan_aware_service(self):
        """Verify all social connection paths utilize PlanAwareSocialService"""
        
        # This test verifies the architectural requirement from the audit
        # that all social connection paths must utilize PlanAwareSocialService
        
        import ast
        import inspect
        from backend.api import social_platforms
        
        source = inspect.getsource(social_platforms.initiate_oauth_connection)
        tree = ast.parse(source)
        
        # Verify the function calls get_plan_aware_social_service
        function_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                function_calls.append(node.func.id)
        
        assert "get_plan_aware_social_service" in function_calls, \
            "Legacy connect endpoint must call get_plan_aware_social_service"
    
    def test_oauth_callback_includes_plan_validation(self):
        """Verify OAuth callback includes plan validation"""
        
        import ast
        import inspect
        from backend.api import social_platforms
        
        source = inspect.getsource(social_platforms.oauth_callback)
        tree = ast.parse(source)
        
        # Verify the callback function calls plan enforcement
        function_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                function_calls.append(node.func.id)
        
        assert "get_plan_aware_social_service" in function_calls, \
            "Legacy OAuth callback must call get_plan_aware_social_service"
    
    def test_no_direct_database_connection_bypass(self):
        """Verify endpoints don't create connections directly without plan checks"""
        
        import ast
        import inspect
        from backend.api import social_platforms
        
        # Check both connection endpoints
        for func_name in ["initiate_oauth_connection", "oauth_callback"]:
            func = getattr(social_platforms, func_name)
            source = inspect.getsource(func)
            tree = ast.parse(source)
            
            # Look for plan enforcement calls
            has_plan_check = False
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and 
                    isinstance(node.func, ast.Attribute) and
                    isinstance(node.func.value, ast.Name) and
                    "plan_service" in node.func.value.id and
                    "enforce_connection_limit" in node.func.attr):
                    has_plan_check = True
                    break
            
            assert has_plan_check, f"{func_name} must include plan enforcement before database operations"