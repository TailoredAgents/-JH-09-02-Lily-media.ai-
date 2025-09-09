"""
Distributed Redis-Only Rate Limiter Service
P0-13b: Migrate rate limiters to Redis for distributed deployments

This service provides Redis-only rate limiting without in-memory fallbacks,
ensuring consistent rate limiting across multiple application instances.
"""
import asyncio
import time
import logging
from typing import Dict, Optional, Any, List, Tuple, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    
from backend.core.config import get_settings
from backend.services.redis_cache import redis_cache
from backend.core.structured_logging import structured_logger_service

logger = logging.getLogger(__name__)

class RateLimitResult(Enum):
    """Rate limit check results"""
    ALLOWED = "allowed"
    RATE_LIMITED = "rate_limited"
    REDIS_ERROR = "redis_error"

@dataclass
class RateLimitInfo:
    """Rate limit status information"""
    result: RateLimitResult
    remaining: int
    reset_time: float
    retry_after: Optional[int] = None
    limit_type: Optional[str] = None
    message: Optional[str] = None

@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_second: int = 10
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 20
    burst_window_seconds: int = 10
    
class DistributedRateLimiter:
    """
    Production-ready distributed rate limiter using Redis only
    
    Features:
    - Redis-only storage (no in-memory fallbacks)
    - Sliding window rate limiting
    - Multiple time windows (second, minute, hour)
    - Burst protection
    - Circuit breaker integration
    - Tenant/organization isolation
    - Connection pooling and error handling
    - Atomic operations using Lua scripts
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize distributed rate limiter"""
        self.settings = get_settings()
        self.redis_url = redis_url or self.settings.redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
        self.is_initialized = False
        
        # Rate limiting configuration
        self.default_config = RateLimitConfig()
        
        # Lua scripts for atomic operations
        self._sliding_window_script = None
        self._burst_protection_script = None
        
        logger.info("Distributed rate limiter initialized - Redis only, no fallbacks")
    
    async def initialize(self):
        """Initialize Redis connection and Lua scripts"""
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis is required for distributed rate limiting - no fallbacks available")
        
        if self.is_initialized:
            return
        
        try:
            # Create connection pool for better performance
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
            
            # Load Lua scripts
            await self._load_lua_scripts()
            
            self.is_initialized = True
            logger.info("Distributed rate limiter initialized successfully with Redis connection")
            
        except Exception as e:
            logger.error(f"Failed to initialize distributed rate limiter: {e}")
            raise RuntimeError(f"Redis connection required for distributed rate limiting: {e}")
    
    async def _load_lua_scripts(self):
        """Load Lua scripts for atomic rate limiting operations"""
        
        # Sliding window rate limiting script
        sliding_window_lua = """
            local key = KEYS[1]
            local window = tonumber(ARGV[1])
            local limit = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local expiry = tonumber(ARGV[4])
            
            -- Remove expired entries
            redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
            
            -- Count current requests in window
            local current = redis.call('ZCARD', key)
            
            if current < limit then
                -- Add new request
                redis.call('ZADD', key, now, now)
                redis.call('EXPIRE', key, expiry)
                
                local remaining = limit - current - 1
                local reset_time = now + window
                
                return {1, remaining, reset_time}
            else
                -- Rate limited
                local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
                local reset_time = oldest[2] and (tonumber(oldest[2]) + window) or (now + window)
                
                return {0, 0, reset_time}
            end
        """
        
        # Burst protection script  
        burst_protection_lua = """
            local key = KEYS[1]
            local burst_limit = tonumber(ARGV[1])
            local burst_window = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            
            -- Remove old burst entries
            redis.call('ZREMRANGEBYSCORE', key, 0, now - burst_window)
            
            -- Check burst count
            local burst_count = redis.call('ZCARD', key)
            
            if burst_count >= burst_limit then
                -- Burst limit exceeded
                local retry_after = burst_window
                return {0, 0, now + retry_after, retry_after}
            else
                -- Add burst entry
                redis.call('ZADD', key, now, now)
                redis.call('EXPIRE', key, burst_window * 2)
                
                local remaining = burst_limit - burst_count - 1
                return {1, remaining, now + burst_window, 0}
            end
        """
        
        # Multi-window rate limit script
        multi_window_lua = """
            local second_key = KEYS[1]
            local minute_key = KEYS[2]
            local hour_key = KEYS[3]
            local burst_key = KEYS[4]
            
            local second_limit = tonumber(ARGV[1])
            local minute_limit = tonumber(ARGV[2])
            local hour_limit = tonumber(ARGV[3])
            local burst_limit = tonumber(ARGV[4])
            local burst_window = tonumber(ARGV[5])
            local now = tonumber(ARGV[6])
            
            -- Check burst first
            redis.call('ZREMRANGEBYSCORE', burst_key, 0, now - burst_window)
            local burst_count = redis.call('ZCARD', burst_key)
            
            if burst_count >= burst_limit then
                return {'burst', 0, now + burst_window, burst_window}
            end
            
            -- Check per-second limit
            redis.call('ZREMRANGEBYSCORE', second_key, 0, now - 1)
            local second_count = redis.call('ZCARD', second_key)
            
            if second_count >= second_limit then
                local oldest_second = redis.call('ZRANGE', second_key, 0, 0, 'WITHSCORES')
                local reset_time = oldest_second[2] and (tonumber(oldest_second[2]) + 1) or (now + 1)
                return {'second', 0, reset_time, math.ceil(reset_time - now)}
            end
            
            -- Check per-minute limit
            redis.call('ZREMRANGEBYSCORE', minute_key, 0, now - 60)
            local minute_count = redis.call('ZCARD', minute_key)
            
            if minute_count >= minute_limit then
                local oldest_minute = redis.call('ZRANGE', minute_key, 0, 0, 'WITHSCORES')
                local reset_time = oldest_minute[2] and (tonumber(oldest_minute[2]) + 60) or (now + 60)
                return {'minute', minute_limit - minute_count, reset_time, math.ceil(reset_time - now)}
            end
            
            -- Check per-hour limit
            redis.call('ZREMRANGEBYSCORE', hour_key, 0, now - 3600)
            local hour_count = redis.call('ZCARD', hour_key)
            
            if hour_count >= hour_limit then
                local oldest_hour = redis.call('ZRANGE', hour_key, 0, 0, 'WITHSCORES')
                local reset_time = oldest_hour[2] and (tonumber(oldest_hour[2]) + 3600) or (now + 3600)
                return {'hour', hour_limit - hour_count, reset_time, math.ceil(reset_time - now)}
            end
            
            -- All limits passed - record request
            redis.call('ZADD', burst_key, now, now)
            redis.call('EXPIRE', burst_key, burst_window * 2)
            
            redis.call('ZADD', second_key, now, now)
            redis.call('EXPIRE', second_key, 10)
            
            redis.call('ZADD', minute_key, now, now)
            redis.call('EXPIRE', minute_key, 120)
            
            redis.call('ZADD', hour_key, now, now)
            redis.call('EXPIRE', hour_key, 7200)
            
            -- Return success with remaining counts
            local remaining_second = second_limit - second_count - 1
            local remaining_minute = minute_limit - minute_count - 1
            local remaining_hour = hour_limit - hour_count - 1
            
            return {'allowed', remaining_minute, now + 60, 0}
        """
        
        # Register scripts
        self._sliding_window_script = self.redis_client.register_script(sliding_window_lua)
        self._burst_protection_script = self.redis_client.register_script(burst_protection_lua)
        self._multi_window_script = self.redis_client.register_script(multi_window_lua)
        
        logger.info("Rate limiting Lua scripts loaded successfully")
    
    def _get_rate_limit_keys(self, identifier: str, org_id: Optional[str] = None) -> Dict[str, str]:
        """Generate rate limit keys for different time windows"""
        base_key = f"rate_limit:{org_id or 'global'}:{identifier}"
        
        return {
            "second": f"{base_key}:second",
            "minute": f"{base_key}:minute", 
            "hour": f"{base_key}:hour",
            "burst": f"{base_key}:burst"
        }
    
    async def check_rate_limit(
        self,
        identifier: str,
        org_id: Optional[str] = None,
        config: Optional[RateLimitConfig] = None
    ) -> RateLimitInfo:
        """
        Check if request is within rate limits
        
        Args:
            identifier: Unique identifier (IP, user ID, API key, etc.)
            org_id: Organization ID for tenant isolation
            config: Rate limiting configuration (uses default if not provided)
            
        Returns:
            RateLimitInfo with the result
        """
        if not self.is_initialized:
            await self.initialize()
        
        rate_config = config or self.default_config
        keys = self._get_rate_limit_keys(identifier, org_id)
        now = time.time()
        
        try:
            result = await self._multi_window_script(
                keys=[keys["second"], keys["minute"], keys["hour"], keys["burst"]],
                args=[
                    rate_config.requests_per_second,
                    rate_config.requests_per_minute,
                    rate_config.requests_per_hour,
                    rate_config.burst_limit,
                    rate_config.burst_window_seconds,
                    now
                ]
            )
            
            limit_type, remaining, reset_time, retry_after = result
            
            if limit_type == 'allowed':
                # Log successful rate limit check
                structured_logger_service.log_rate_limit_allowed(
                    identifier=identifier,
                    limit_type="multi_window",
                    limit_value=getattr(rate_config, f"requests_per_{limit_type.split('_')[0] if '_' in limit_type else 'minute'}", rate_config.requests_per_minute),
                    remaining=int(remaining),
                    reset_time=float(reset_time),
                    organization_id=org_id
                )
                
                return RateLimitInfo(
                    result=RateLimitResult.ALLOWED,
                    remaining=int(remaining),
                    reset_time=float(reset_time)
                )
            else:
                # Log rate limit exceeded
                limit_value = getattr(rate_config, f"requests_per_{limit_type}", rate_config.requests_per_minute)
                if limit_type == "burst":
                    limit_value = rate_config.burst_limit
                
                structured_logger_service.log_rate_limit_exceeded(
                    identifier=identifier,
                    limit_type=limit_type,
                    limit_value=limit_value,
                    current_usage=limit_value - int(remaining),
                    reset_time=float(reset_time),
                    retry_after=int(retry_after),
                    organization_id=org_id
                )
                
                return RateLimitInfo(
                    result=RateLimitResult.RATE_LIMITED,
                    remaining=int(remaining),
                    reset_time=float(reset_time),
                    retry_after=int(retry_after),
                    limit_type=limit_type,
                    message=f"Rate limit exceeded: {limit_type} limit reached"
                )
            
        except Exception as e:
            logger.error(f"Rate limit check failed for {identifier}: {e}")
            
            # For distributed systems, we fail closed (deny) rather than open
            # This prevents rate limit bypass during Redis failures
            return RateLimitInfo(
                result=RateLimitResult.REDIS_ERROR,
                remaining=0,
                reset_time=now + 60,  # Try again in 1 minute
                retry_after=60,
                message=f"Rate limiting service unavailable: {str(e)}"
            )
    
    async def get_rate_limit_status(
        self,
        identifier: str,
        org_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current rate limit status without consuming quota"""
        if not self.is_initialized:
            await self.initialize()
        
        keys = self._get_rate_limit_keys(identifier, org_id)
        now = time.time()
        
        try:
            # Get counts for different windows
            pipe = self.redis_client.pipeline()
            
            # Clean up expired entries and get counts
            for window, key in [("second", keys["second"]), ("minute", keys["minute"]), 
                              ("hour", keys["hour"]), ("burst", keys["burst"])]:
                if window == "second":
                    pipe.zremrangebyscore(key, 0, now - 1)
                elif window == "minute":
                    pipe.zremrangebyscore(key, 0, now - 60)
                elif window == "hour":
                    pipe.zremrangebyscore(key, 0, now - 3600)
                elif window == "burst":
                    pipe.zremrangebyscore(key, 0, now - self.default_config.burst_window_seconds)
                
                pipe.zcard(key)
            
            results = await pipe.execute()
            
            # Extract counts (every 2nd result is a count)
            counts = results[1::2]
            
            return {
                "identifier": identifier,
                "org_id": org_id,
                "timestamp": now,
                "current_usage": {
                    "second": counts[0],
                    "minute": counts[1], 
                    "hour": counts[2],
                    "burst": counts[3]
                },
                "limits": {
                    "second": self.default_config.requests_per_second,
                    "minute": self.default_config.requests_per_minute,
                    "hour": self.default_config.requests_per_hour,
                    "burst": self.default_config.burst_limit
                },
                "remaining": {
                    "second": max(0, self.default_config.requests_per_second - counts[0]),
                    "minute": max(0, self.default_config.requests_per_minute - counts[1]),
                    "hour": max(0, self.default_config.requests_per_hour - counts[2]),
                    "burst": max(0, self.default_config.burst_limit - counts[3])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get rate limit status for {identifier}: {e}")
            return {
                "error": str(e),
                "identifier": identifier,
                "org_id": org_id
            }
    
    async def reset_rate_limit(
        self,
        identifier: str,
        org_id: Optional[str] = None
    ) -> bool:
        """Reset rate limit for identifier (admin function)"""
        if not self.is_initialized:
            await self.initialize()
        
        keys = self._get_rate_limit_keys(identifier, org_id)
        
        try:
            await self.redis_client.delete(*keys.values())
            logger.info(f"Rate limit reset for {identifier} (org: {org_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset rate limit for {identifier}: {e}")
            return False
    
    async def get_top_rate_limited(
        self,
        org_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top rate-limited identifiers for monitoring"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            pattern = f"rate_limit:{org_id or 'global'}:*:minute"
            top_limited = []
            
            async for key in self.redis_client.scan_iter(match=pattern):
                count = await self.redis_client.zcard(key)
                if count > 0:
                    # Extract identifier from key
                    key_parts = key.split(":")
                    identifier = ":".join(key_parts[2:-1])  # Remove prefix and suffix
                    
                    top_limited.append({
                        "identifier": identifier,
                        "requests_in_minute": count,
                        "key": key
                    })
            
            # Sort by request count and return top N
            top_limited.sort(key=lambda x: x["requests_in_minute"], reverse=True)
            return top_limited[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get top rate limited identifiers: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on rate limiting service"""
        health = {
            "status": "unhealthy",
            "redis_connected": False,
            "scripts_loaded": False,
            "error": None
        }
        
        try:
            if not self.is_initialized:
                await self.initialize()
            
            # Test Redis connection
            await self.redis_client.ping()
            health["redis_connected"] = True
            
            # Test script execution
            test_result = await self._sliding_window_script(
                keys=["test:health_check"],
                args=[60, 100, time.time(), 120]
            )
            
            if test_result:
                health["scripts_loaded"] = True
                health["status"] = "healthy"
                
                # Clean up test key
                await self.redis_client.delete("test:health_check")
            
        except Exception as e:
            health["error"] = str(e)
            logger.error(f"Rate limiter health check failed: {e}")
        
        return health
    
    async def close(self):
        """Close Redis connections gracefully"""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Distributed rate limiter connections closed")
            except Exception as e:
                logger.error(f"Error closing rate limiter connections: {e}")
        
        if self.connection_pool:
            try:
                await self.connection_pool.disconnect()
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")

# Global distributed rate limiter instance
distributed_rate_limiter = DistributedRateLimiter()

# Context manager for automatic initialization and cleanup
@asynccontextmanager
async def rate_limiter_context():
    """Context manager for rate limiter lifecycle management"""
    try:
        await distributed_rate_limiter.initialize()
        yield distributed_rate_limiter
    finally:
        await distributed_rate_limiter.close()