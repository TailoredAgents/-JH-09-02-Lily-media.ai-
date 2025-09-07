"""
Integration tests for distributed authentication middleware with session revocation
Tests P0-13c implementation: stronger session revocation and refresh token rotation
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, HTTPException
from starlette.responses import Response
from backend.middleware.distributed_auth_middleware import (
    DistributedAuthMiddleware,
    create_session_from_request
)
from backend.services.distributed_session_manager import (
    SessionState,
    RevocationReason,
    SessionInfo
)

@pytest.fixture
def mock_request():
    """Create mock FastAPI request"""
    request = MagicMock(spec=Request)
    request.url.path = "/api/test"
    request.method = "GET"
    request.headers = {
        "Authorization": "Bearer valid.jwt.token",
        "User-Agent": "Mozilla/5.0 Test Browser"
    }
    request.cookies = {"refresh_token": "valid.refresh.token"}
    request.client.host = "192.168.1.1"
    request.state = MagicMock()
    return request

@pytest.fixture
def mock_app():
    """Mock ASGI app"""
    async def app(request):
        return Response("OK", status_code=200)
    return app

@pytest.fixture
def auth_middleware(mock_app):
    """Create auth middleware instance"""
    return DistributedAuthMiddleware(mock_app)

@pytest.mark.asyncio 
class TestDistributedAuthMiddleware:
    """Test authentication middleware with session revocation"""
    
    async def test_successful_authentication_flow(self, auth_middleware, mock_request):
        """Test successful authentication with active session"""
        
        # Mock distributed session manager
        with patch('backend.middleware.distributed_auth_middleware.distributed_session_manager') as mock_session_mgr:
            mock_session_mgr.is_initialized = True
            mock_session_mgr.is_token_blacklisted = AsyncMock(return_value=False)
            mock_session_mgr.get_session = AsyncMock(return_value=SessionInfo(
                session_id="valid-session-123",
                user_id=123,
                organization_id="org-123", 
                created_at=time.time(),
                last_accessed=time.time(),
                expires_at=time.time() + 3600,
                state=SessionState.ACTIVE,
                client_info={"ip_address": "192.168.1.1"},
                access_count=1,
                refresh_count=0
            ))
            mock_session_mgr.update_session_activity = AsyncMock(return_value=True)
            
            # Mock JWT handler
            with patch('backend.middleware.distributed_auth_middleware.jwt_handler') as mock_jwt:
                mock_jwt.verify_token.return_value = {
                    "sub": "123",
                    "session_id": "valid-session-123",
                    "exp": time.time() + 3600
                }
                
                # Mock call_next
                async def mock_call_next(request):
                    return Response("Success", status_code=200)
                
                response = await auth_middleware.dispatch(mock_request, mock_call_next)
                
                assert response.status_code == 200
                assert mock_request.state.user_id == 123
                assert mock_request.state.session_id == "valid-session-123" 
                assert mock_request.state.organization_id == "org-123"
                
                # Verify session activity was updated
                mock_session_mgr.update_session_activity.assert_called_once_with("valid-session-123")
    
    async def test_blacklisted_token_rejection(self, auth_middleware, mock_request):
        """Test rejection of blacklisted tokens"""
        
        with patch('backend.middleware.distributed_auth_middleware.distributed_session_manager') as mock_session_mgr:
            mock_session_mgr.is_initialized = True
            mock_session_mgr.is_token_blacklisted = AsyncMock(return_value=True)
            
            async def mock_call_next(request):
                return Response("Should not reach here", status_code=200)
            
            response = await auth_middleware.dispatch(mock_request, mock_call_next)
            
            assert response.status_code == 403  # Forbidden for blacklisted token
            response_data = response.body.decode()
            assert "Token has been revoked" in response_data
            
            # Verify token blacklist was checked
            mock_session_mgr.is_token_blacklisted.assert_called_once()
    
    async def test_revoked_session_handling(self, auth_middleware, mock_request):
        """Test handling of revoked sessions"""
        
        with patch('backend.middleware.distributed_auth_middleware.distributed_session_manager') as mock_session_mgr:
            mock_session_mgr.is_initialized = True
            mock_session_mgr.is_token_blacklisted = AsyncMock(return_value=False)
            
            # Mock revoked session
            revoked_session = SessionInfo(
                session_id="revoked-session-123",
                user_id=123,
                organization_id="org-123",
                created_at=time.time() - 3600,
                last_accessed=time.time() - 1800,
                expires_at=time.time() + 3600,
                state=SessionState.REVOKED,
                client_info={"ip_address": "192.168.1.1"},
                revocation_reason=RevocationReason.SUSPICIOUS_ACTIVITY,
                revoked_at=time.time() - 900,
                access_count=5,
                refresh_count=0
            )
            
            mock_session_mgr.get_session = AsyncMock(return_value=revoked_session)
            mock_session_mgr.blacklist_token = AsyncMock(return_value=True)
            
            # Mock JWT handler
            with patch('backend.middleware.distributed_auth_middleware.jwt_handler') as mock_jwt:
                mock_jwt.verify_token.return_value = {
                    "sub": "123",
                    "session_id": "revoked-session-123"
                }
                
                async def mock_call_next(request):
                    return Response("Should not reach here", status_code=200)
                
                response = await auth_middleware.dispatch(mock_request, mock_call_next)
                
                assert response.status_code == 403
                response_data = response.body.decode()
                assert "revoked" in response_data.lower()
                
                # Verify token was blacklisted when session was revoked
                mock_session_mgr.blacklist_token.assert_called_once()
    
    async def test_token_refresh_on_expired_access_token(self, auth_middleware, mock_request):
        """Test automatic token refresh when access token expires"""
        
        with patch('backend.middleware.distributed_auth_middleware.distributed_session_manager') as mock_session_mgr:
            mock_session_mgr.is_initialized = True
            mock_session_mgr.is_token_blacklisted = AsyncMock(return_value=False)
            mock_session_mgr.get_session = AsyncMock(return_value=SessionInfo(
                session_id="valid-session-123",
                user_id=123,
                organization_id="org-123",
                created_at=time.time(),
                last_accessed=time.time(),
                expires_at=time.time() + 3600,
                state=SessionState.ACTIVE,
                client_info={"ip_address": "192.168.1.1"},
                access_count=1,
                refresh_count=0
            ))
            mock_session_mgr.rotate_refresh_token = AsyncMock(return_value="new.refresh.token")
            
            # Mock JWT handler
            with patch('backend.middleware.distributed_auth_middleware.jwt_handler') as mock_jwt:
                # First call (access token) raises expired exception
                # Second call (refresh token) succeeds
                mock_jwt.verify_token.side_effect = [
                    HTTPException(status_code=401, detail="Token expired"),
                    {
                        "sub": "123", 
                        "session_id": "valid-session-123",
                        "type": "refresh"
                    }
                ]
                mock_jwt.create_access_token.return_value = "new.access.token"
                
                async def mock_call_next(request):
                    return Response("Success", status_code=200)
                
                response = await auth_middleware.dispatch(mock_request, mock_call_next)
                
                assert response.status_code == 200
                
                # Verify refresh token was rotated
                mock_session_mgr.rotate_refresh_token.assert_called_once()
                
                # Verify new access token was created
                mock_jwt.create_access_token.assert_called_once()
    
    async def test_suspicious_activity_detection_and_revocation(self, auth_middleware, mock_request):
        """Test automatic revocation on suspicious activity detection"""
        
        # Modify request to trigger suspicious activity (high access count)
        mock_request.client.host = "10.0.0.1"  # Different IP
        
        with patch('backend.middleware.distributed_auth_middleware.distributed_session_manager') as mock_session_mgr:
            mock_session_mgr.is_initialized = True
            mock_session_mgr.is_token_blacklisted = AsyncMock(return_value=False)
            
            # Mock session with high access count (suspicious)
            suspicious_session = SessionInfo(
                session_id="suspicious-session-123",
                user_id=123,
                organization_id="org-123",
                created_at=time.time() - 600,  # 10 minutes ago
                last_accessed=time.time(),
                expires_at=time.time() + 3600,
                state=SessionState.ACTIVE,
                client_info={
                    "ip_address": "192.168.1.1",  # Different from current request IP
                    "user_agent": "Mozilla/5.0 Original Browser"
                },
                access_count=1500,  # Very high access count
                refresh_count=0
            )
            
            mock_session_mgr.get_session = AsyncMock(return_value=suspicious_session)
            mock_session_mgr.revoke_session = AsyncMock(return_value=True)
            mock_session_mgr.blacklist_token = AsyncMock(return_value=True)
            
            # Mock JWT handler
            with patch('backend.middleware.distributed_auth_middleware.jwt_handler') as mock_jwt:
                mock_jwt.verify_token.return_value = {
                    "sub": "123",
                    "session_id": "suspicious-session-123"
                }
                
                async def mock_call_next(request):
                    return Response("Should not reach here", status_code=200)
                
                response = await auth_middleware.dispatch(mock_request, mock_call_next)
                
                assert response.status_code == 403
                response_data = response.body.decode()
                assert "Suspicious activity detected" in response_data
                
                # Verify session was revoked for suspicious activity
                mock_session_mgr.revoke_session.assert_called_once_with(
                    "suspicious-session-123",
                    RevocationReason.SUSPICIOUS_ACTIVITY
                )
                
                # Verify token was blacklisted
                mock_session_mgr.blacklist_token.assert_called_once()
    
    async def test_exempt_path_bypasses_auth(self, auth_middleware, mock_request):
        """Test that exempt paths bypass authentication"""
        
        mock_request.url.path = "/health"  # Exempt path
        
        async def mock_call_next(request):
            return Response("Health OK", status_code=200)
        
        response = await auth_middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
        # Should not have set any auth state
        assert not hasattr(mock_request.state, 'user_id')
    
    async def test_options_request_bypasses_auth(self, auth_middleware, mock_request):
        """Test that OPTIONS requests bypass authentication"""
        
        mock_request.method = "OPTIONS"
        
        async def mock_call_next(request):
            return Response("OK", status_code=200)
        
        response = await auth_middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
        # Should not have set any auth state
        assert not hasattr(mock_request.state, 'user_id')
    
    async def test_missing_token_rejection(self, auth_middleware, mock_request):
        """Test rejection when no access token is provided"""
        
        mock_request.headers = {}  # No Authorization header
        
        async def mock_call_next(request):
            return Response("Should not reach here", status_code=200)
        
        response = await auth_middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 401
        response_data = response.body.decode()
        assert "No access token provided" in response_data
    
    async def test_session_creation_helper(self):
        """Test session creation helper function"""
        
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"User-Agent": "Test Browser"}
        mock_request.client.host = "192.168.1.1"
        
        with patch('backend.middleware.distributed_auth_middleware.distributed_session_manager') as mock_session_mgr:
            mock_session_mgr.create_session = AsyncMock()
            
            # Test the helper function
            session_coro = create_session_from_request(mock_request, 123, "org-123")
            
            # Verify it returns a coroutine that calls create_session with proper client info
            await session_coro
            
            mock_session_mgr.create_session.assert_called_once()
            call_args = mock_session_mgr.create_session.call_args
            
            assert call_args[1]['user_id'] == 123
            assert call_args[1]['organization_id'] == "org-123"
            assert call_args[1]['client_info']['ip_address'] == "192.168.1.1"
            assert call_args[1]['client_info']['user_agent'] == "Test Browser"

@pytest.mark.asyncio
class TestSuspiciousActivityDetection:
    """Test suspicious activity detection scenarios"""
    
    async def test_ip_address_change_detection(self, auth_middleware, mock_request):
        """Test detection of IP address changes"""
        
        # Change IP in request vs session
        mock_request.client.host = "10.0.0.1"
        
        with patch('backend.middleware.distributed_auth_middleware.distributed_session_manager') as mock_session_mgr:
            mock_session_mgr.is_initialized = True
            mock_session_mgr.is_token_blacklisted = AsyncMock(return_value=False)
            
            session_info = SessionInfo(
                session_id="session-123",
                user_id=123,
                organization_id="org-123",
                created_at=time.time(),
                last_accessed=time.time(),
                expires_at=time.time() + 3600,
                state=SessionState.ACTIVE,
                client_info={"ip_address": "192.168.1.1"},  # Different IP
                access_count=5,
                refresh_count=0
            )
            
            mock_session_mgr.get_session = AsyncMock(return_value=session_info)
            
            # Mock JWT handler
            with patch('backend.middleware.distributed_auth_middleware.jwt_handler') as mock_jwt:
                mock_jwt.verify_token.return_value = {
                    "sub": "123",
                    "session_id": "session-123"
                }
                
                async def mock_call_next(request):
                    return Response("Success", status_code=200)
                
                # Should still succeed (IP changes are logged but not auto-blocked)
                response = await auth_middleware.dispatch(mock_request, mock_call_next)
                
                assert response.status_code == 200
    
    async def test_user_agent_change_detection(self, auth_middleware, mock_request):
        """Test detection of significant user agent changes"""
        
        # Change browser type
        mock_request.headers["User-Agent"] = "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT)"
        
        with patch('backend.middleware.distributed_auth_middleware.distributed_session_manager') as mock_session_mgr:
            mock_session_mgr.is_initialized = True
            mock_session_mgr.is_token_blacklisted = AsyncMock(return_value=False)
            mock_session_mgr.revoke_session = AsyncMock(return_value=True)
            mock_session_mgr.blacklist_token = AsyncMock(return_value=True)
            
            session_info = SessionInfo(
                session_id="session-123",
                user_id=123,
                organization_id="org-123",
                created_at=time.time(),
                last_accessed=time.time(),
                expires_at=time.time() + 3600,
                state=SessionState.ACTIVE,
                client_info={
                    "ip_address": "192.168.1.1",
                    "user_agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/91.0.4472.124"  # Chrome vs IE
                },
                access_count=5,
                refresh_count=0
            )
            
            mock_session_mgr.get_session = AsyncMock(return_value=session_info)
            
            # Mock JWT handler
            with patch('backend.middleware.distributed_auth_middleware.jwt_handler') as mock_jwt:
                mock_jwt.verify_token.return_value = {
                    "sub": "123",
                    "session_id": "session-123"
                }
                
                async def mock_call_next(request):
                    return Response("Should be blocked", status_code=200)
                
                response = await auth_middleware.dispatch(mock_request, mock_call_next)
                
                # Should be blocked due to significant browser change
                assert response.status_code == 403
                
                # Verify session was revoked
                mock_session_mgr.revoke_session.assert_called_once_with(
                    "session-123",
                    RevocationReason.SUSPICIOUS_ACTIVITY
                )

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])