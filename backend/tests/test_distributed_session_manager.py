"""
Test suite for Distributed Session Manager (P0-13c)
Tests session revocation, refresh token rotation, and token blacklisting
"""
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.distributed_session_manager import (
    DistributedSessionManager,
    SessionState,
    RevocationReason,
    SessionInfo,
    TokenInfo,
    distributed_session_manager
)
from backend.core.security import jwt_handler

@pytest.fixture
def session_manager():
    """Create session manager for testing"""
    # Mock Redis for testing
    with patch('backend.services.distributed_session_manager.REDIS_AVAILABLE', True):
        manager = DistributedSessionManager("redis://localhost:6379")
        
        # Mock Redis client
        redis_mock = AsyncMock()
        redis_mock.ping = AsyncMock(return_value=True)
        redis_mock.set = AsyncMock(return_value=True)
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.exists = AsyncMock(return_value=False)
        redis_mock.setex = AsyncMock(return_value=True)
        redis_mock.smembers = AsyncMock(return_value=set())
        redis_mock.sadd = AsyncMock(return_value=True)
        redis_mock.expire = AsyncMock(return_value=True)
        redis_mock.delete = AsyncMock(return_value=True)
        redis_mock.close = AsyncMock()
        redis_mock.scan_iter = AsyncMock()
        
        # Mock connection pool
        pool_mock = AsyncMock()
        pool_mock.disconnect = AsyncMock()
        
        # Mock script registration
        script_mock = AsyncMock()
        script_mock.return_value = 1  # Success
        redis_mock.register_script = MagicMock(return_value=script_mock)
        
        manager.redis_client = redis_mock
        manager.connection_pool = pool_mock
        manager._session_create_script = script_mock
        manager._token_blacklist_script = script_mock
        manager._bulk_revocation_script = script_mock
        manager._cleanup_script = script_mock
        manager.is_initialized = True
        
        return manager

@pytest.mark.asyncio
class TestDistributedSessionManager:
    """Test distributed session management functionality"""
    
    async def test_session_creation(self, session_manager):
        """Test session creation with proper tracking"""
        user_id = 123
        client_info = {
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0...",
            "timestamp": time.time()
        }
        
        # Mock successful session creation
        session_manager._session_create_script.return_value = 1
        
        session = await session_manager.create_session(
            user_id=user_id,
            client_info=client_info,
            organization_id="org-123"
        )
        
        assert isinstance(session, SessionInfo)
        assert session.user_id == user_id
        assert session.organization_id == "org-123"
        assert session.state == SessionState.ACTIVE
        assert session.is_active()
        assert not session.is_expired()
        assert session.access_count == 1
        assert session.refresh_count == 0
        
        # Verify Redis calls
        session_manager._session_create_script.assert_called_once()
    
    async def test_session_retrieval(self, session_manager):
        """Test session retrieval and deserialization"""
        session_id = "test-session-123"
        
        # Mock session data in Redis
        mock_session_data = {
            "session_id": session_id,
            "user_id": 123,
            "organization_id": "org-123",
            "created_at": time.time(),
            "last_accessed": time.time(),
            "expires_at": time.time() + 3600,
            "state": "active",
            "client_info": {"ip_address": "192.168.1.1"},
            "revocation_reason": None,
            "revoked_at": None,
            "refresh_count": 0,
            "access_count": 1
        }
        
        import json
        session_manager.redis_client.get.return_value = json.dumps(mock_session_data)
        
        session = await session_manager.get_session(session_id)
        
        assert session is not None
        assert session.session_id == session_id
        assert session.user_id == 123
        assert session.state == SessionState.ACTIVE
        assert session.is_active()
        
        # Verify Redis call
        session_manager.redis_client.get.assert_called_once()
    
    async def test_session_activity_update(self, session_manager):
        """Test session activity tracking"""
        session_id = "test-session-123"
        
        # Mock existing session
        mock_session_data = {
            "session_id": session_id,
            "user_id": 123,
            "organization_id": "org-123",
            "created_at": time.time(),
            "last_accessed": time.time() - 100,  # Old access time
            "expires_at": time.time() + 3600,
            "state": "active",
            "client_info": {"ip_address": "192.168.1.1"},
            "revocation_reason": None,
            "revoked_at": None,
            "refresh_count": 0,
            "access_count": 1
        }
        
        import json
        session_manager.redis_client.get.return_value = json.dumps(mock_session_data)
        
        result = await session_manager.update_session_activity(session_id)
        
        assert result is True
        
        # Verify Redis get and set calls
        session_manager.redis_client.get.assert_called()
        session_manager.redis_client.set.assert_called()
    
    async def test_session_revocation(self, session_manager):
        """Test individual session revocation"""
        session_id = "test-session-123"
        
        # Mock existing active session
        mock_session_data = {
            "session_id": session_id,
            "user_id": 123,
            "organization_id": "org-123",
            "created_at": time.time(),
            "last_accessed": time.time(),
            "expires_at": time.time() + 3600,
            "state": "active",
            "client_info": {"ip_address": "192.168.1.1"},
            "revocation_reason": None,
            "revoked_at": None,
            "refresh_count": 0,
            "access_count": 1
        }
        
        import json
        session_manager.redis_client.get.return_value = json.dumps(mock_session_data)
        
        result = await session_manager.revoke_session(
            session_id, 
            RevocationReason.SUSPICIOUS_ACTIVITY
        )
        
        assert result is True
        
        # Verify session was marked as revoked
        session_manager.redis_client.set.assert_called()
        session_manager.redis_client.setex.assert_called()  # Revocation log
    
    async def test_bulk_session_revocation(self, session_manager):
        """Test revoking all user sessions"""
        user_id = 123
        session_ids = ["session-1", "session-2", "session-3"]
        
        # Mock user sessions in Redis
        session_manager.redis_client.smembers.return_value = session_ids
        
        # Mock session data for each session
        mock_session_data = {
            "session_id": "test-session",
            "user_id": user_id,
            "organization_id": "org-123",
            "created_at": time.time(),
            "last_accessed": time.time(),
            "expires_at": time.time() + 3600,
            "state": "active",
            "client_info": {"ip_address": "192.168.1.1"},
            "revocation_reason": None,
            "revoked_at": None,
            "refresh_count": 0,
            "access_count": 1
        }
        
        import json
        session_manager.redis_client.get.return_value = json.dumps(mock_session_data)
        
        revoked_count = await session_manager.revoke_all_user_sessions(
            user_id,
            RevocationReason.PASSWORD_CHANGE
        )
        
        assert revoked_count == len(session_ids)
        
        # Verify Redis calls for session lookup and updates
        session_manager.redis_client.smembers.assert_called_once()
        assert session_manager.redis_client.set.call_count == len(session_ids)
    
    async def test_token_blacklisting(self, session_manager):
        """Test token blacklisting with automatic expiry"""
        token = "test.jwt.token"
        user_id = 123
        session_id = "session-123"
        
        # Mock successful blacklisting
        session_manager._token_blacklist_script.return_value = 1
        
        result = await session_manager.blacklist_token(
            token,
            user_id,
            session_id,
            RevocationReason.TOKEN_ROTATION
        )
        
        assert result is True
        
        # Verify blacklist script was called
        session_manager._token_blacklist_script.assert_called_once()
    
    async def test_token_blacklist_check(self, session_manager):
        """Test checking if token is blacklisted"""
        token = "test.jwt.token"
        
        # Mock token exists in blacklist
        session_manager.redis_client.exists.return_value = 1
        
        is_blacklisted = await session_manager.is_token_blacklisted(token)
        
        assert is_blacklisted is True
        
        # Test token not blacklisted
        session_manager.redis_client.exists.return_value = 0
        is_blacklisted = await session_manager.is_token_blacklisted(token)
        
        assert is_blacklisted is False
        
        # Verify Redis calls
        assert session_manager.redis_client.exists.call_count == 2
    
    async def test_refresh_token_rotation(self, session_manager):
        """Test refresh token rotation with blacklisting"""
        old_token = "old.refresh.token"
        user_id = 123
        session_id = "session-123"
        
        # Mock existing session
        mock_session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "organization_id": "org-123",
            "created_at": time.time(),
            "last_accessed": time.time(),
            "expires_at": time.time() + 3600,
            "state": "active",
            "client_info": {"ip_address": "192.168.1.1"},
            "revocation_reason": None,
            "revoked_at": None,
            "refresh_count": 0,
            "access_count": 1
        }
        
        import json
        session_manager.redis_client.get.return_value = json.dumps(mock_session_data)
        session_manager._token_blacklist_script.return_value = 1
        
        # Mock JWT creation
        with patch.object(jwt_handler, 'create_refresh_token', return_value="new.refresh.token"):
            new_token = await session_manager.rotate_refresh_token(
                old_token,
                user_id,
                session_id
            )
        
        assert new_token == "new.refresh.token"
        
        # Verify old token was blacklisted
        session_manager._token_blacklist_script.assert_called_once()
        
        # Verify session refresh count was updated
        session_manager.redis_client.set.assert_called()
    
    async def test_session_cleanup(self, session_manager):
        """Test cleanup of expired sessions and tokens"""
        # Mock cleanup script results
        session_cleanup_result = [5, 100]  # 5 cleaned, 100 processed
        token_cleanup_result = [3, 50]     # 3 cleaned, 50 processed
        
        session_manager._cleanup_script.side_effect = [
            session_cleanup_result,
            token_cleanup_result
        ]
        
        stats = await session_manager.cleanup_expired_sessions()
        
        assert stats['sessions_cleaned'] == 5
        assert stats['sessions_processed'] == 100
        assert stats['tokens_cleaned'] == 3
        assert stats['tokens_processed'] == 50
        assert 'cleanup_time' in stats
        
        # Verify cleanup script was called twice
        assert session_manager._cleanup_script.call_count == 2
    
    async def test_session_analytics(self, session_manager):
        """Test session analytics collection"""
        user_id = 123
        
        # Mock user sessions
        session_ids = ["session-1", "session-2"]
        session_manager.redis_client.smembers.return_value = session_ids
        
        # Mock session data
        mock_active_session = {
            "state": "active",
            "expires_at": time.time() + 3600,
            "user_id": user_id
        }
        
        mock_revoked_session = {
            "state": "revoked",
            "expires_at": time.time() + 3600,
            "revocation_reason": "user_logout",
            "user_id": user_id
        }
        
        import json
        session_manager.redis_client.get.side_effect = [
            json.dumps(mock_active_session),
            json.dumps(mock_revoked_session)
        ]
        
        analytics = await session_manager.get_session_analytics(user_id)
        
        assert analytics['total_sessions'] == 2
        assert analytics['active_sessions'] == 1
        assert analytics['revoked_sessions'] == 1
        assert analytics['expired_sessions'] == 0
        assert 'timestamp' in analytics
    
    async def test_health_check(self, session_manager):
        """Test session manager health check"""
        health = await session_manager.health_check()
        
        assert health['status'] == 'healthy'
        assert health['redis_connected'] is True
        assert health['session_store_available'] is True
        assert health['error'] is None
        
        # Verify Redis operations
        session_manager.redis_client.ping.assert_called()
        session_manager.redis_client.set.assert_called()
        session_manager.redis_client.get.assert_called()
        session_manager.redis_client.delete.assert_called()
    
    async def test_connection_cleanup(self, session_manager):
        """Test proper cleanup of Redis connections"""
        await session_manager.close()
        
        # Verify connections were closed
        session_manager.redis_client.close.assert_called_once()
        session_manager.connection_pool.disconnect.assert_called_once()

@pytest.mark.asyncio
class TestSessionRevocationScenarios:
    """Test various session revocation scenarios"""
    
    async def test_suspicious_activity_revocation(self, session_manager):
        """Test automatic revocation on suspicious activity"""
        session_id = "suspicious-session"
        
        # Mock session with suspicious activity indicators
        mock_session_data = {
            "session_id": session_id,
            "user_id": 123,
            "organization_id": "org-123",
            "created_at": time.time(),
            "last_accessed": time.time(),
            "expires_at": time.time() + 3600,
            "state": "active",
            "client_info": {
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0..."
            },
            "revocation_reason": None,
            "revoked_at": None,
            "refresh_count": 0,
            "access_count": 1001  # Very high access count
        }
        
        import json
        session_manager.redis_client.get.return_value = json.dumps(mock_session_data)
        
        # Revoke for suspicious activity
        result = await session_manager.revoke_session(
            session_id,
            RevocationReason.SUSPICIOUS_ACTIVITY
        )
        
        assert result is True
        
        # Verify revocation was logged
        session_manager.redis_client.setex.assert_called()
    
    async def test_security_breach_bulk_revocation(self, session_manager):
        """Test bulk revocation on security breach"""
        user_id = 456
        session_ids = ["breach-session-1", "breach-session-2", "breach-session-3"]
        
        session_manager.redis_client.smembers.return_value = session_ids
        
        # Mock session data
        mock_session_data = {
            "user_id": user_id,
            "state": "active",
            "expires_at": time.time() + 3600,
            "client_info": {"ip_address": "10.0.0.1"}
        }
        
        import json
        session_manager.redis_client.get.return_value = json.dumps(mock_session_data)
        
        revoked_count = await session_manager.revoke_all_user_sessions(
            user_id,
            RevocationReason.SECURITY_BREACH
        )
        
        assert revoked_count == len(session_ids)
    
    async def test_device_limit_enforcement(self, session_manager):
        """Test session revocation for device limit enforcement"""
        user_id = 789
        
        # Simulate user exceeding device limit
        session_ids = [f"device-session-{i}" for i in range(6)]  # 6 sessions, limit is 5
        session_manager.redis_client.smembers.return_value = session_ids
        
        # Mock oldest session (should be revoked first)
        oldest_session_data = {
            "session_id": "device-session-0",
            "user_id": user_id,
            "created_at": time.time() - 3600,  # Oldest
            "state": "active"
        }
        
        import json
        session_manager.redis_client.get.return_value = json.dumps(oldest_session_data)
        
        # Revoke oldest session
        result = await session_manager.revoke_session(
            "device-session-0",
            RevocationReason.DEVICE_LIMIT
        )
        
        assert result is True

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])