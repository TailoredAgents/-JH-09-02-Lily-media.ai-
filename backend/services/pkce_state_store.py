"""
PKCE state storage service for partner OAuth flow
Manages server-side state and code_verifier storage in Redis
"""
import secrets
import hashlib
import base64
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from backend.core.config import get_settings
from backend.core.service_factory import register_service, get_service

logger = logging.getLogger(__name__)

class PKCEStateStore:
    """
    Manages OAuth state and PKCE parameters in Redis with secure server-side storage
    
    Key format: oauth:state:{state}
    TTL: 600 seconds (10 minutes)
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize with Redis client
        
        Args:
            redis_client: Optional Redis client, will create from settings if None
        """
        self.settings = get_settings()
        self.ttl = 600  # 10 minutes
        
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = self._create_redis_client()
    
    def _create_redis_client(self):
        """Create Redis client from settings"""
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis package not available. Install with: pip install redis")
        
        try:
            redis_client = redis.from_url(
                self.settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            redis_client.ping()
            logger.info("Connected to Redis for PKCE state storage")
            return redis_client
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise RuntimeError(f"Redis connection failed: {e}")
    
    def create(self, organization_id: str, platform: str) -> Dict[str, str]:
        """
        Generate PKCE parameters and state, store server-side
        
        Args:
            organization_id: Organization/tenant ID
            platform: OAuth platform (meta, x)
            
        Returns:
            Dictionary with state, code_challenge, code_challenge_method
            (Note: code_verifier is NOT returned, kept server-side)
            
        Raises:
            ValueError: If invalid parameters
            RuntimeError: If Redis operation fails
        """
        if not organization_id or not platform:
            raise ValueError("organization_id and platform are required")
        
        # Validate platform
        allowed_platforms = ["meta", "x"]
        if platform not in allowed_platforms:
            raise ValueError(f"Platform must be one of: {allowed_platforms}")
        
        try:
            # Generate secure random values
            state = secrets.token_urlsafe(32)
            code_verifier = secrets.token_urlsafe(64)
            nonce = secrets.token_urlsafe(16)
            
            # Calculate PKCE challenge
            challenge_bytes = hashlib.sha256(code_verifier.encode('ascii')).digest()
            code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('ascii').rstrip('=')
            
            # Create state data
            state_data = {
                "organization_id": organization_id,
                "platform": platform,
                "code_verifier": code_verifier,
                "nonce": nonce,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=self.ttl)).isoformat()
            }
            
            # Store in Redis with TTL
            redis_key = f"oauth:state:{state}"
            self.redis.setex(
                redis_key,
                self.ttl,
                json.dumps(state_data, separators=(',', ':'))
            )
            
            logger.info(f"Created PKCE state for org {organization_id}, platform {platform}")
            
            return {
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256"
            }
            
        except Exception as e:
            logger.error(f"Failed to create PKCE state: {e}")
            raise RuntimeError(f"PKCE state creation failed: {e}")
    
    def consume(self, state: str) -> Dict[str, Any]:
        """
        Retrieve and delete state data (one-time use)
        
        Args:
            state: OAuth state parameter
            
        Returns:
            Dictionary with organization_id, platform, code_verifier, etc.
            
        Raises:
            ValueError: If state is invalid or expired
        """
        if not state:
            raise ValueError("State parameter is required")
        
        try:
            redis_key = f"oauth:state:{state}"
            
            # Get and delete atomically using pipeline
            pipe = self.redis.pipeline()
            pipe.get(redis_key)
            pipe.delete(redis_key)
            results = pipe.execute()
            
            state_json = results[0]
            if not state_json:
                logger.warning(f"Invalid or expired state: {state[:8]}...")
                raise ValueError("Invalid or expired state")
            
            state_data = json.loads(state_json)
            
            # Verify expiration (extra safety)
            expires_at = datetime.fromisoformat(state_data["expires_at"])
            if datetime.now(timezone.utc) > expires_at:
                logger.warning(f"Expired state consumed: {state[:8]}...")
                raise ValueError("State has expired")
            
            logger.info(f"Consumed PKCE state for org {state_data.get('organization_id')}, platform {state_data.get('platform')}")
            
            return state_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted state data: {e}")
            raise ValueError("Invalid state data")
        except Exception as e:
            logger.error(f"Failed to consume state: {e}")
            raise ValueError("State consumption failed")
    
    def cache_tokens(self, state: str, tokens: Dict[str, Any], scopes: list) -> None:
        """
        Cache tokens temporarily for asset selection phase
        
        Args:
            state: OAuth state (used as cache key)
            tokens: Token data from OAuth exchange
            scopes: Granted scopes
        """
        try:
            cache_data = {
                "tokens": tokens,
                "scopes": scopes,
                "cached_at": datetime.now(timezone.utc).isoformat()
            }
            
            cache_key = f"oauth:tokens:{state}"
            # Cache for same TTL as original state
            self.redis.setex(
                cache_key,
                self.ttl,
                json.dumps(cache_data, separators=(',', ':'))
            )
            
            logger.info(f"Cached tokens for state {state[:8]}...")
            
        except Exception as e:
            logger.error(f"Failed to cache tokens: {e}")
            raise RuntimeError(f"Token caching failed: {e}")
    
    def read_tokens(self, state: str) -> Optional[Dict[str, Any]]:
        """
        Read cached tokens without consuming them
        
        Args:
            state: OAuth state
            
        Returns:
            Cached token data or None if not found/expired
        """
        try:
            cache_key = f"oauth:tokens:{state}"
            cached_json = self.redis.get(cache_key)
            
            if not cached_json:
                return None
            
            return json.loads(cached_json)
            
        except Exception as e:
            logger.error(f"Failed to read cached tokens: {e}")
            return None
    
    def cleanup_expired(self) -> int:
        """
        Cleanup expired state entries (Redis TTL should handle this automatically)
        
        Returns:
            Number of entries cleaned up
        """
        try:
            # This is mostly for monitoring - Redis TTL handles cleanup
            pattern = "oauth:state:*"
            count = 0
            
            for key in self.redis.scan_iter(match=pattern):
                # Check if expired (Redis should have already removed it)
                if not self.redis.exists(key):
                    count += 1
            
            if count > 0:
                logger.info(f"Found {count} expired state entries (cleaned by Redis TTL)")
            
            return count
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored states
        
        Returns:
            Dictionary with state storage statistics
        """
        try:
            state_pattern = "oauth:state:*"
            token_pattern = "oauth:tokens:*"
            
            state_keys = list(self.redis.scan_iter(match=state_pattern))
            token_keys = list(self.redis.scan_iter(match=token_pattern))
            
            return {
                "active_states": len(state_keys),
                "cached_tokens": len(token_keys),
                "redis_info": {
                    "connected": self.redis.ping(),
                    "memory_used": self.redis.info().get("used_memory_human", "unknown")
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}


# Register service with factory
register_service('pkce_state_store', PKCEStateStore, scope='singleton')

def get_state_store() -> PKCEStateStore:
    """Get PKCE state store instance from service factory"""
    return get_service('pkce_state_store')

def create_pkce_challenge(organization_id: str, platform: str) -> Dict[str, str]:
    """Convenience function to create PKCE challenge"""
    return get_state_store().create(organization_id, platform)

def consume_pkce_state(state: str) -> Dict[str, Any]:
    """Convenience function to consume PKCE state"""
    return get_state_store().consume(state)