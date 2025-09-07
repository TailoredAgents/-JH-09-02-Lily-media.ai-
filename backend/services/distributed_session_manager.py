"""
Distributed Session Management Service - P0-13c Implementation
Stronger session revocation and refresh token rotation using Redis

This service provides:
- Distributed session storage and tracking
- Real-time session revocation across all app instances  
- Token blacklisting and rotation
- Session analytics and security monitoring
- Automatic cleanup and expiry management
"""
import asyncio
import time
import json
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import asynccontextmanager

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from backend.core.config import get_settings
from backend.core.security import jwt_handler

logger = logging.getLogger(__name__)
settings = get_settings()

class SessionState(Enum):
    """Session states"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUSPICIOUS = "suspicious"

class RevocationReason(Enum):
    """Reasons for session revocation"""
    USER_LOGOUT = "user_logout"
    ADMIN_REVOKE = "admin_revoke"
    SECURITY_BREACH = "security_breach"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    TOKEN_ROTATION = "token_rotation"
    POLICY_VIOLATION = "policy_violation"
    PASSWORD_CHANGE = "password_change"
    DEVICE_LIMIT = "device_limit"

@dataclass
class SessionInfo:
    """Session information structure"""
    session_id: str
    user_id: int
    organization_id: Optional[str]
    created_at: float
    last_accessed: float
    expires_at: float
    state: SessionState
    client_info: Dict[str, Any]
    revocation_reason: Optional[RevocationReason] = None
    revoked_at: Optional[float] = None
    refresh_count: int = 0
    access_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return time.time() > self.expires_at
    
    def is_active(self) -> bool:
        """Check if session is active and valid"""
        return self.state == SessionState.ACTIVE and not self.is_expired()

@dataclass
class TokenInfo:
    """Token information for blacklisting"""
    token_hash: str
    user_id: int
    session_id: str
    expires_at: float
    revoked_at: float
    reason: RevocationReason
    
class DistributedSessionManager:
    """
    Distributed session management with Redis
    
    Features:
    - Distributed session storage across app instances
    - Real-time session revocation and blacklisting
    - Token rotation with blacklist management
    - Session analytics and monitoring
    - Automatic cleanup and expiry management
    - Security breach detection and response
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize distributed session manager"""
        self.redis_url = redis_url or settings.redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
        self.is_initialized = False
        
        # Configuration
        self.session_ttl = getattr(settings, 'session_ttl_seconds', 86400 * 7)  # 7 days
        self.access_token_ttl = getattr(settings, 'jwt_access_ttl_seconds', 900)  # 15 minutes
        self.refresh_token_ttl = getattr(settings, 'jwt_refresh_ttl_seconds', 604800)  # 7 days
        self.cleanup_interval = 3600  # 1 hour
        
        # Redis key prefixes
        self.session_prefix = "session"
        self.token_blacklist_prefix = "blacklist"
        self.user_sessions_prefix = "user_sessions"
        self.revocation_log_prefix = "revocations"
        
        logger.info("Distributed session manager initialized - Redis required for P0-13c")
    
    async def initialize(self):
        """Initialize Redis connection and Lua scripts"""
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis is required for distributed session management (P0-13c)")
        
        if self.is_initialized:
            return
        
        try:
            # Create connection pool
            self.connection_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                health_check_interval=30,
                socket_connect_timeout=5,
                socket_timeout=10
            )
            
            self.redis_client = redis.Redis(
                connection_pool=self.connection_pool,
                socket_connect_timeout=5,
                socket_timeout=10
            )
            
            # Test connection
            await self.redis_client.ping()
            
            # Load Lua scripts for atomic operations
            await self._load_lua_scripts()
            
            self.is_initialized = True
            logger.info("Distributed session manager initialized successfully with Redis")
            
        except Exception as e:
            logger.error(f"Failed to initialize distributed session manager: {e}")
            raise RuntimeError(f"Redis connection required for session management: {e}")
    
    async def _load_lua_scripts(self):
        """Load Lua scripts for atomic session operations"""
        
        # Session creation with user session tracking
        session_create_lua = """
            local session_key = KEYS[1]
            local user_sessions_key = KEYS[2]
            local session_data = ARGV[1]
            local session_ttl = tonumber(ARGV[2])
            local session_id = ARGV[3]
            
            -- Store session data
            redis.call('SET', session_key, session_data, 'EX', session_ttl)
            
            -- Add to user sessions set
            redis.call('SADD', user_sessions_key, session_id)
            redis.call('EXPIRE', user_sessions_key, session_ttl)
            
            return 1
        """
        
        # Token blacklisting with automatic expiry
        token_blacklist_lua = """
            local token_key = KEYS[1]
            local token_info = ARGV[1]
            local expires_at = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            
            -- Only blacklist if token hasn't expired
            if expires_at > now then
                local ttl = expires_at - now
                redis.call('SET', token_key, token_info, 'EX', ttl)
                return 1
            end
            
            return 0
        """
        
        # Bulk session revocation
        bulk_revocation_lua = """
            local user_sessions_key = KEYS[1]
            local revocation_reason = ARGV[1]
            local revoked_at = ARGV[2]
            
            -- Get all sessions for user
            local session_ids = redis.call('SMEMBERS', user_sessions_key)
            local revoked_count = 0
            
            for i = 1, #session_ids do
                local session_key = 'session:' .. session_ids[i]
                local session_data = redis.call('GET', session_key)
                
                if session_data then
                    -- Update session state to revoked
                    local session = cjson.decode(session_data)
                    session.state = 'revoked'
                    session.revocation_reason = revocation_reason
                    session.revoked_at = tonumber(revoked_at)
                    
                    -- Save updated session
                    redis.call('SET', session_key, cjson.encode(session), 'KEEPTTL')
                    revoked_count = revoked_count + 1
                end
            end
            
            return revoked_count
        """
        
        # Session cleanup
        cleanup_lua = """
            local prefix = ARGV[1]
            local now = tonumber(ARGV[2])
            local batch_size = tonumber(ARGV[3])
            
            local cursor = 0
            local cleaned = 0
            local processed = 0
            
            repeat
                local result = redis.call('SCAN', cursor, 'MATCH', prefix .. '*', 'COUNT', batch_size)
                cursor = tonumber(result[1])
                local keys = result[2]
                
                for i = 1, #keys do
                    processed = processed + 1
                    local data = redis.call('GET', keys[i])
                    
                    if data then
                        local session = cjson.decode(data)
                        if session.expires_at and session.expires_at < now then
                            redis.call('DEL', keys[i])
                            cleaned = cleaned + 1
                        end
                    end
                end
            until cursor == 0 or processed >= batch_size * 10
            
            return {cleaned, processed}
        """
        
        # Register Lua scripts
        self._session_create_script = self.redis_client.register_script(session_create_lua)
        self._token_blacklist_script = self.redis_client.register_script(token_blacklist_lua)
        self._bulk_revocation_script = self.redis_client.register_script(bulk_revocation_lua)
        self._cleanup_script = self.redis_client.register_script(cleanup_lua)
        
        logger.info("Session management Lua scripts loaded successfully")
    
    def _generate_session_id(self, user_id: int, client_info: Dict[str, Any]) -> str:
        """Generate unique session ID"""
        components = [
            str(user_id),
            str(time.time()),
            client_info.get('user_agent', ''),
            client_info.get('ip_address', ''),
        ]
        session_string = '|'.join(components)
        return hashlib.sha256(session_string.encode()).hexdigest()
    
    def _hash_token(self, token: str) -> str:
        """Hash token for blacklist storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _get_session_key(self, session_id: str) -> str:
        """Get Redis key for session"""
        return f"{self.session_prefix}:{session_id}"
    
    def _get_token_blacklist_key(self, token_hash: str) -> str:
        """Get Redis key for blacklisted token"""
        return f"{self.token_blacklist_prefix}:{token_hash}"
    
    def _get_user_sessions_key(self, user_id: int) -> str:
        """Get Redis key for user sessions set"""
        return f"{self.user_sessions_prefix}:{user_id}"
    
    async def create_session(
        self,
        user_id: int,
        client_info: Dict[str, Any],
        organization_id: Optional[str] = None,
        custom_ttl: Optional[int] = None
    ) -> SessionInfo:
        """
        Create new session with distributed tracking
        
        Args:
            user_id: User ID
            client_info: Client information (IP, user-agent, etc.)
            organization_id: Organization ID for tenant isolation
            custom_ttl: Custom TTL in seconds
            
        Returns:
            SessionInfo with session details
        """
        if not self.is_initialized:
            await self.initialize()
        
        session_id = self._generate_session_id(user_id, client_info)
        now = time.time()
        ttl = custom_ttl or self.session_ttl
        
        session_info = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            organization_id=organization_id,
            created_at=now,
            last_accessed=now,
            expires_at=now + ttl,
            state=SessionState.ACTIVE,
            client_info=client_info,
            refresh_count=0,
            access_count=1
        )
        
        try:
            # Store session atomically
            session_key = self._get_session_key(session_id)
            user_sessions_key = self._get_user_sessions_key(user_id)
            session_data = json.dumps(asdict(session_info), default=str)
            
            await self._session_create_script(
                keys=[session_key, user_sessions_key],
                args=[session_data, ttl, session_id]
            )
            
            logger.info(f"Session created: {session_id} for user {user_id}")
            return session_info
            
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get session information
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            SessionInfo if found and valid, None otherwise
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            session_key = self._get_session_key(session_id)
            session_data = await self.redis_client.get(session_key)
            
            if not session_data:
                return None
            
            data = json.loads(session_data)
            session_info = SessionInfo(**{
                **data,
                'state': SessionState(data['state']),
                'revocation_reason': RevocationReason(data['revocation_reason']) if data.get('revocation_reason') else None
            })
            
            return session_info
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def update_session_activity(self, session_id: str) -> bool:
        """
        Update session last accessed time
        
        Args:
            session_id: Session ID to update
            
        Returns:
            True if updated successfully
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            session_info = await self.get_session(session_id)
            if not session_info or not session_info.is_active():
                return False
            
            # Update activity
            session_info.last_accessed = time.time()
            session_info.access_count += 1
            
            # Save updated session
            session_key = self._get_session_key(session_id)
            session_data = json.dumps(asdict(session_info), default=str)
            
            await self.redis_client.set(session_key, session_data, keepttl=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session activity {session_id}: {e}")
            return False
    
    async def revoke_session(
        self,
        session_id: str,
        reason: RevocationReason = RevocationReason.USER_LOGOUT
    ) -> bool:
        """
        Revoke specific session
        
        Args:
            session_id: Session ID to revoke
            reason: Reason for revocation
            
        Returns:
            True if revoked successfully
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            session_info = await self.get_session(session_id)
            if not session_info:
                return False
            
            # Update session state
            session_info.state = SessionState.REVOKED
            session_info.revocation_reason = reason
            session_info.revoked_at = time.time()
            
            # Save updated session
            session_key = self._get_session_key(session_id)
            session_data = json.dumps(asdict(session_info), default=str)
            
            await self.redis_client.set(session_key, session_data, keepttl=True)
            
            # Log revocation
            await self._log_revocation(session_info, reason)
            
            logger.info(f"Session revoked: {session_id} (reason: {reason.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke session {session_id}: {e}")
            return False
    
    async def revoke_all_user_sessions(
        self,
        user_id: int,
        reason: RevocationReason = RevocationReason.USER_LOGOUT,
        except_session_id: Optional[str] = None
    ) -> int:
        """
        Revoke all sessions for a user
        
        Args:
            user_id: User ID whose sessions to revoke
            reason: Reason for revocation
            except_session_id: Session ID to keep active (optional)
            
        Returns:
            Number of sessions revoked
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            user_sessions_key = self._get_user_sessions_key(user_id)
            session_ids = await self.redis_client.smembers(user_sessions_key)
            
            revoked_count = 0
            
            for session_id in session_ids:
                if except_session_id and session_id == except_session_id:
                    continue
                
                if await self.revoke_session(session_id, reason):
                    revoked_count += 1
            
            logger.info(f"Revoked {revoked_count} sessions for user {user_id} (reason: {reason.value})")
            return revoked_count
            
        except Exception as e:
            logger.error(f"Failed to revoke all sessions for user {user_id}: {e}")
            return 0
    
    async def blacklist_token(
        self,
        token: str,
        user_id: int,
        session_id: str,
        reason: RevocationReason = RevocationReason.TOKEN_ROTATION
    ) -> bool:
        """
        Add token to blacklist
        
        Args:
            token: JWT token to blacklist
            user_id: User ID
            session_id: Session ID
            reason: Reason for blacklisting
            
        Returns:
            True if blacklisted successfully
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Decode token to get expiry
            from jose import jwt
            try:
                payload = jwt.get_unverified_claims(token)
                expires_at = payload.get('exp', time.time() + 3600)
            except:
                expires_at = time.time() + 3600  # Default 1 hour
            
            token_hash = self._hash_token(token)
            token_info = TokenInfo(
                token_hash=token_hash,
                user_id=user_id,
                session_id=session_id,
                expires_at=expires_at,
                revoked_at=time.time(),
                reason=reason
            )
            
            # Blacklist token with automatic expiry
            token_key = self._get_token_blacklist_key(token_hash)
            token_data = json.dumps(asdict(token_info), default=str)
            
            result = await self._token_blacklist_script(
                keys=[token_key],
                args=[token_data, expires_at, time.time()]
            )
            
            if result:
                logger.info(f"Token blacklisted: {token_hash[:8]}... (reason: {reason.value})")
                return True
            else:
                logger.debug(f"Token already expired, not blacklisted: {token_hash[:8]}...")
                return True
                
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted
        
        Args:
            token: JWT token to check
            
        Returns:
            True if blacklisted
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            token_hash = self._hash_token(token)
            token_key = self._get_token_blacklist_key(token_hash)
            
            result = await self.redis_client.exists(token_key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False
    
    async def rotate_refresh_token(
        self,
        old_token: str,
        user_id: int,
        session_id: str
    ) -> Optional[str]:
        """
        Rotate refresh token with blacklisting
        
        Args:
            old_token: Old refresh token to revoke
            user_id: User ID
            session_id: Session ID
            
        Returns:
            New refresh token if successful
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Blacklist old token
            await self.blacklist_token(
                old_token,
                user_id,
                session_id,
                RevocationReason.TOKEN_ROTATION
            )
            
            # Update session refresh count
            session_info = await self.get_session(session_id)
            if session_info:
                session_info.refresh_count += 1
                session_key = self._get_session_key(session_id)
                session_data = json.dumps(asdict(session_info), default=str)
                await self.redis_client.set(session_key, session_data, keepttl=True)
            
            # Generate new refresh token
            token_data = {"sub": str(user_id), "session_id": session_id}
            new_token = jwt_handler.create_refresh_token(token_data)
            
            logger.info(f"Refresh token rotated for user {user_id} session {session_id}")
            return new_token
            
        except Exception as e:
            logger.error(f"Failed to rotate refresh token: {e}")
            return None
    
    async def get_user_sessions(self, user_id: int) -> List[SessionInfo]:
        """
        Get all active sessions for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of SessionInfo objects
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            user_sessions_key = self._get_user_sessions_key(user_id)
            session_ids = await self.redis_client.smembers(user_sessions_key)
            
            sessions = []
            
            for session_id in session_ids:
                session_info = await self.get_session(session_id)
                if session_info:
                    sessions.append(session_info)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []
    
    async def cleanup_expired_sessions(self, batch_size: int = 100) -> Dict[str, int]:
        """
        Clean up expired sessions and blacklisted tokens
        
        Args:
            batch_size: Number of keys to process in each batch
            
        Returns:
            Dictionary with cleanup statistics
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            now = time.time()
            
            # Clean up sessions
            session_result = await self._cleanup_script(
                keys=[],
                args=[f"{self.session_prefix}:*", now, batch_size]
            )
            
            # Clean up blacklisted tokens
            blacklist_result = await self._cleanup_script(
                keys=[],
                args=[f"{self.token_blacklist_prefix}:*", now, batch_size]
            )
            
            stats = {
                'sessions_cleaned': session_result[0],
                'sessions_processed': session_result[1],
                'tokens_cleaned': blacklist_result[0],
                'tokens_processed': blacklist_result[1],
                'cleanup_time': time.time() - now
            }
            
            if stats['sessions_cleaned'] > 0 or stats['tokens_cleaned'] > 0:
                logger.info(f"Session cleanup completed: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return {}
    
    async def _log_revocation(self, session_info: SessionInfo, reason: RevocationReason):
        """Log session revocation for audit purposes"""
        try:
            log_key = f"{self.revocation_log_prefix}:{session_info.user_id}:{int(time.time())}"
            log_data = {
                'session_id': session_info.session_id,
                'user_id': session_info.user_id,
                'organization_id': session_info.organization_id,
                'reason': reason.value,
                'revoked_at': time.time(),
                'client_info': session_info.client_info
            }
            
            # Store log entry with 30-day TTL
            await self.redis_client.setex(
                log_key,
                30 * 24 * 3600,  # 30 days
                json.dumps(log_data, default=str)
            )
            
        except Exception as e:
            logger.error(f"Failed to log session revocation: {e}")
    
    async def get_session_analytics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get session analytics and statistics
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            Dictionary with session analytics
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            analytics = {
                'timestamp': time.time(),
                'total_sessions': 0,
                'active_sessions': 0,
                'revoked_sessions': 0,
                'expired_sessions': 0,
                'blacklisted_tokens': 0
            }
            
            if user_id:
                # User-specific analytics
                sessions = await self.get_user_sessions(user_id)
                analytics['total_sessions'] = len(sessions)
                
                for session in sessions:
                    if session.is_active():
                        analytics['active_sessions'] += 1
                    elif session.state == SessionState.REVOKED:
                        analytics['revoked_sessions'] += 1
                    elif session.is_expired():
                        analytics['expired_sessions'] += 1
            else:
                # Global analytics (approximate)
                # Count sessions by pattern matching
                session_keys = []
                async for key in self.redis_client.scan_iter(match=f"{self.session_prefix}:*"):
                    session_keys.append(key)
                
                analytics['total_sessions'] = len(session_keys)
                
                # Sample analysis for performance
                sample_size = min(100, len(session_keys))
                if sample_size > 0:
                    import random
                    sample_keys = random.sample(session_keys, sample_size)
                    
                    active_ratio = 0
                    revoked_ratio = 0
                    expired_ratio = 0
                    
                    for key in sample_keys:
                        try:
                            session_data = await self.redis_client.get(key)
                            if session_data:
                                data = json.loads(session_data)
                                if data.get('state') == 'active':
                                    active_ratio += 1
                                elif data.get('state') == 'revoked':
                                    revoked_ratio += 1
                                else:
                                    expired_ratio += 1
                        except:
                            continue
                    
                    # Extrapolate to total
                    total_sessions = analytics['total_sessions']
                    analytics['active_sessions'] = int((active_ratio / sample_size) * total_sessions)
                    analytics['revoked_sessions'] = int((revoked_ratio / sample_size) * total_sessions)
                    analytics['expired_sessions'] = int((expired_ratio / sample_size) * total_sessions)
                
                # Count blacklisted tokens
                blacklist_count = 0
                async for key in self.redis_client.scan_iter(match=f"{self.token_blacklist_prefix}:*"):
                    blacklist_count += 1
                analytics['blacklisted_tokens'] = blacklist_count
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get session analytics: {e}")
            return {'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on session management service"""
        health = {
            'status': 'unhealthy',
            'redis_connected': False,
            'session_store_available': False,
            'error': None
        }
        
        try:
            if not self.is_initialized:
                await self.initialize()
            
            # Test Redis connection
            await self.redis_client.ping()
            health['redis_connected'] = True
            
            # Test session operations
            test_session_id = f"health_check_{int(time.time())}"
            test_key = self._get_session_key(test_session_id)
            
            await self.redis_client.set(test_key, '{"test": true}', ex=10)
            result = await self.redis_client.get(test_key)
            
            if result:
                health['session_store_available'] = True
                health['status'] = 'healthy'
                
                # Clean up test data
                await self.redis_client.delete(test_key)
            
        except Exception as e:
            health['error'] = str(e)
            logger.error(f"Session manager health check failed: {e}")
        
        return health
    
    async def close(self):
        """Close Redis connections gracefully"""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Distributed session manager connections closed")
            except Exception as e:
                logger.error(f"Error closing session manager connections: {e}")
        
        if self.connection_pool:
            try:
                await self.connection_pool.disconnect()
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")

# Global distributed session manager instance
distributed_session_manager = DistributedSessionManager()

@asynccontextmanager
async def session_manager_context():
    """Context manager for session manager lifecycle"""
    try:
        await distributed_session_manager.initialize()
        yield distributed_session_manager
    finally:
        await distributed_session_manager.close()