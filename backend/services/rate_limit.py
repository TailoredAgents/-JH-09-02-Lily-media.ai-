"""
Rate limiting service for Phase 8
Implements token bucket algorithm and circuit breaker pattern for tenant isolation
"""
import time
import math
import random
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
import redis
from redis import Redis

from backend.core.config import get_settings
from backend.core.structured_logging import structured_logger_service

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket rate limiter for per-tenant throttling"""
    
    def __init__(
        self, 
        redis_client: Redis, 
        key_prefix: str = "rate",
        refill_rate: int = 60,
        capacity: int = 60,
        window_s: int = 60
    ):
        """
        Initialize token bucket rate limiter
        
        Args:
            redis_client: Redis client for state storage
            key_prefix: Prefix for Redis keys
            refill_rate: Tokens added per window (requests per minute)
            capacity: Maximum tokens in bucket
            window_s: Time window in seconds for rate calculation
        """
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.refill_rate = refill_rate
        self.capacity = capacity
        self.window_s = window_s
    
    def acquire(self, org_id: str, platform: str, tokens: int = 1) -> bool:
        """
        Try to acquire tokens for a request
        
        Args:
            org_id: Organization ID for tenant isolation
            platform: Platform name (meta, x, etc.)
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False if rate limited
        """
        try:
            key = f"{self.key_prefix}:{org_id}:{platform}"
            now = time.time()
            
            # Use Redis Lua script for atomic bucket operations
            lua_script = """
                local key = KEYS[1]
                local now = tonumber(ARGV[1])
                local tokens_requested = tonumber(ARGV[2])
                local capacity = tonumber(ARGV[3])
                local refill_rate = tonumber(ARGV[4])
                local window_s = tonumber(ARGV[5])
                
                -- Get current bucket state
                local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
                local current_tokens = tonumber(bucket[1]) or capacity
                local last_refill = tonumber(bucket[2]) or now
                
                -- Calculate tokens to add based on time elapsed
                local elapsed = now - last_refill
                local tokens_to_add = math.floor(elapsed * refill_rate / window_s)
                
                -- Refill bucket (cap at capacity)
                current_tokens = math.min(capacity, current_tokens + tokens_to_add)
                
                -- Check if we can satisfy the request
                if current_tokens >= tokens_requested then
                    -- Consume tokens
                    current_tokens = current_tokens - tokens_requested
                    
                    -- Update bucket state
                    redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
                    redis.call('EXPIRE', key, window_s * 2)  -- TTL for cleanup
                    
                    return {1, current_tokens}  -- Success + remaining tokens
                else
                    -- Not enough tokens - update refill time but don't consume
                    redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
                    redis.call('EXPIRE', key, window_s * 2)
                    
                    return {0, current_tokens}  -- Rate limited + remaining tokens
                end
            """
            
            result = self.redis.eval(
                lua_script,
                1,
                key,
                str(now),
                str(tokens),
                str(self.capacity),
                str(self.refill_rate),
                str(self.window_s)
            )
            
            success = bool(result[0])
            remaining_tokens = int(result[1])
            
            if not success:
                logger.warning(
                    f"Rate limit exceeded for org {org_id} platform {platform}: "
                    f"{remaining_tokens}/{self.capacity} tokens remaining"
                )
                
                # Log structured rate limit exceeded event
                structured_logger_service.log_rate_limit_exceeded(
                    identifier=f"{org_id}:{platform}",
                    limit_type="token_bucket",
                    limit_value=self.capacity,
                    current_usage=self.capacity - remaining_tokens,
                    reset_time=self.get_reset_time(org_id, platform),
                    retry_after=int(60 / self.refill_rate),  # Approximate retry time
                    organization_id=org_id,
                    platform=platform
                )
            else:
                # Log successful rate limit check (at debug level)
                structured_logger_service.log_rate_limit_allowed(
                    identifier=f"{org_id}:{platform}",
                    limit_type="token_bucket", 
                    limit_value=self.capacity,
                    remaining=remaining_tokens,
                    reset_time=self.get_reset_time(org_id, platform),
                    organization_id=org_id,
                    platform=platform
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error in token bucket acquire for {org_id}:{platform}: {e}")
            # Fail open - allow request if Redis is unavailable
            return True
    
    def get_remaining(self, org_id: str, platform: str) -> int:
        """
        Get remaining tokens in bucket without consuming
        
        Args:
            org_id: Organization ID
            platform: Platform name
            
        Returns:
            Number of tokens remaining
        """
        try:
            key = f"{self.key_prefix}:{org_id}:{platform}"
            now = time.time()
            
            lua_script = """
                local key = KEYS[1]
                local now = tonumber(ARGV[1])
                local capacity = tonumber(ARGV[2])
                local refill_rate = tonumber(ARGV[3])
                local window_s = tonumber(ARGV[4])
                
                local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
                local current_tokens = tonumber(bucket[1]) or capacity
                local last_refill = tonumber(bucket[2]) or now
                
                local elapsed = now - last_refill
                local tokens_to_add = math.floor(elapsed * refill_rate / window_s)
                
                return math.min(capacity, current_tokens + tokens_to_add)
            """
            
            result = self.redis.eval(
                lua_script,
                1,
                key,
                str(now),
                str(self.capacity),
                str(self.refill_rate),
                str(self.window_s)
            )
            
            return int(result)
            
        except Exception as e:
            logger.error(f"Error getting remaining tokens for {org_id}:{platform}: {e}")
            return self.capacity
    
    def get_reset_time(self, org_id: str, platform: str) -> float:
        """
        Get time when bucket will be full again
        
        Args:
            org_id: Organization ID
            platform: Platform name
            
        Returns:
            Unix timestamp when bucket resets
        """
        try:
            key = f"{self.key_prefix}:{org_id}:{platform}"
            now = time.time()
            
            bucket_data = self.redis.hmget(key, 'tokens', 'last_refill')
            current_tokens = int(bucket_data[0]) if bucket_data[0] else self.capacity
            last_refill = float(bucket_data[1]) if bucket_data[1] else now
            
            # Calculate elapsed time and current token count after refill
            elapsed = now - last_refill
            tokens_to_add = math.floor(elapsed * self.refill_rate / self.window_s)
            actual_tokens = min(self.capacity, current_tokens + tokens_to_add)
            
            if actual_tokens >= self.capacity:
                return now  # Already full
            
            # Time to fill remaining tokens
            tokens_needed = self.capacity - actual_tokens
            time_to_fill = (tokens_needed * self.window_s) / self.refill_rate
            
            return now + time_to_fill
            
        except Exception as e:
            logger.error(f"Error getting reset time for {org_id}:{platform}: {e}")
            return time.time()


class CircuitBreaker:
    """Circuit breaker for tenant isolation during failures"""
    
    def __init__(
        self,
        redis_client: Redis,
        key_prefix: str = "cb",
        fail_threshold: int = 5,
        cooldown_s: int = 120
    ):
        """
        Initialize circuit breaker
        
        Args:
            redis_client: Redis client for state storage
            key_prefix: Prefix for Redis keys
            fail_threshold: Number of failures to open circuit
            cooldown_s: Seconds to wait before trying half-open
        """
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.fail_threshold = fail_threshold
        self.cooldown_s = cooldown_s
    
    def allow(self, org_id: str, platform: str) -> bool:
        """
        Check if requests are allowed through circuit breaker
        
        Args:
            org_id: Organization ID
            platform: Platform name
            
        Returns:
            True if requests allowed, False if circuit is open
        """
        try:
            key = f"{self.key_prefix}:{org_id}:{platform}"
            now = time.time()
            
            lua_script = """
                local key = KEYS[1]
                local now = tonumber(ARGV[1])
                local fail_threshold = tonumber(ARGV[2])
                local cooldown_s = tonumber(ARGV[3])
                
                -- Get circuit state
                local state = redis.call('HMGET', key, 'failures', 'last_failure', 'state')
                local failures = tonumber(state[1]) or 0
                local last_failure = tonumber(state[2]) or 0
                local circuit_state = state[3] or 'closed'
                
                -- State machine logic
                if circuit_state == 'open' then
                    -- Check if cooldown period has passed
                    if now - last_failure >= cooldown_s then
                        -- Transition to half-open
                        redis.call('HSET', key, 'state', 'half-open')
                        redis.call('EXPIRE', key, cooldown_s * 2)
                        return 1  -- Allow one test request
                    else
                        return 0  -- Still in cooldown
                    end
                elseif circuit_state == 'half-open' then
                    -- Allow test request
                    return 1
                else
                    -- Closed state - allow request
                    return 1
                end
            """
            
            result = self.redis.eval(
                lua_script,
                1,
                key,
                str(now),
                str(self.fail_threshold),
                str(self.cooldown_s)
            )
            
            allowed = bool(result)
            
            # Get current state for logging
            state_info = self.get_state(org_id, platform)
            current_state = state_info.get("state", "closed")
            
            if not allowed:
                logger.warning(f"Circuit breaker OPEN for org {org_id} platform {platform}")
                
                # Log structured circuit breaker event
                structured_logger_service.log_circuit_breaker_request_blocked(
                    circuit_name=f"{platform}_integration",
                    current_state=current_state,
                    cooldown_remaining=self.cooldown_s - (time.time() - state_info.get("last_failure", time.time())),
                    organization_id=org_id,
                    platform=platform
                )
            else:
                # Log allowed request
                structured_logger_service.log_circuit_breaker_request_allowed(
                    circuit_name=f"{platform}_integration", 
                    current_state=current_state,
                    organization_id=org_id,
                    platform=platform
                )
            
            return allowed
            
        except Exception as e:
            logger.error(f"Error checking circuit breaker for {org_id}:{platform}: {e}")
            # Fail open - allow request if Redis is unavailable
            return True
    
    def record_success(self, org_id: str, platform: str) -> None:
        """
        Record successful request
        
        Args:
            org_id: Organization ID
            platform: Platform name
        """
        try:
            key = f"{self.key_prefix}:{org_id}:{platform}"
            
            lua_script = """
                local key = KEYS[1]
                
                -- Get current state
                local state = redis.call('HGET', key, 'state') or 'closed'
                
                if state == 'half-open' then
                    -- Success in half-open -> transition to closed
                    redis.call('HMSET', key, 'failures', 0, 'state', 'closed')
                    redis.call('EXPIRE', key, 3600)  -- Keep state for 1 hour
                elseif state == 'closed' then
                    -- Reset failure count on success
                    redis.call('HSET', key, 'failures', 0)
                    redis.call('EXPIRE', key, 3600)
                end
            """
            
            self.redis.eval(lua_script, 1, key)
            
            # Log structured circuit breaker success
            state_info = self.get_state(org_id, platform)
            structured_logger_service.log_circuit_breaker_success(
                circuit_name=f"{platform}_integration",
                current_state=state_info.get("state", "closed"),
                success_count=1,  # We don't track success counts currently
                duration_ms=0,  # Duration would need to be passed in
                organization_id=org_id,
                platform=platform
            )
            
        except Exception as e:
            logger.error(f"Error recording success for {org_id}:{platform}: {e}")
    
    def record_failure(self, org_id: str, platform: str) -> None:
        """
        Record failed request
        
        Args:
            org_id: Organization ID
            platform: Platform name
        """
        try:
            key = f"{self.key_prefix}:{org_id}:{platform}"
            now = time.time()
            
            lua_script = """
                local key = KEYS[1]
                local now = tonumber(ARGV[1])
                local fail_threshold = tonumber(ARGV[2])
                
                -- Get current state
                local cb_data = redis.call('HMGET', key, 'failures', 'state')
                local failures = tonumber(cb_data[1]) or 0
                local state = cb_data[2] or 'closed'
                
                -- Increment failure count
                failures = failures + 1
                
                if state == 'half-open' then
                    -- Failure in half-open -> back to open
                    redis.call('HMSET', key, 'failures', failures, 'last_failure', now, 'state', 'open')
                    redis.call('EXPIRE', key, 3600)
                elseif failures >= fail_threshold then
                    -- Threshold exceeded -> open circuit
                    redis.call('HMSET', key, 'failures', failures, 'last_failure', now, 'state', 'open')
                    redis.call('EXPIRE', key, 3600)
                else
                    -- Still closed, just increment failures
                    redis.call('HMSET', key, 'failures', failures, 'last_failure', now)
                    redis.call('EXPIRE', key, 3600)
                end
                
                return failures
            """
            
            failures = self.redis.eval(
                lua_script,
                1,
                key,
                str(now),
                str(self.fail_threshold)
            )
            
            logger.warning(f"Failure recorded for org {org_id} platform {platform}: {failures} total")
            
            # Get updated state for structured logging
            state_info = self.get_state(org_id, platform)
            current_state = state_info.get("state", "closed")
            previous_state = "closed" if int(failures) == 1 else current_state
            
            # Log structured circuit breaker failure
            structured_logger_service.log_circuit_breaker_failure(
                circuit_name=f"{platform}_integration",
                error=Exception(f"Platform integration failure"),  # Generic error for now
                failure_count=int(failures),
                failure_threshold=self.fail_threshold,
                duration_ms=0,  # Duration would need to be passed in
                organization_id=org_id,
                platform=platform
            )
            
            # Log state change if threshold reached
            if int(failures) >= self.fail_threshold and previous_state != "open":
                structured_logger_service.log_circuit_breaker_state_change(
                    circuit_name=f"{platform}_integration",
                    previous_state=previous_state,
                    current_state="open",
                    failure_count=int(failures),
                    failure_threshold=self.fail_threshold,
                    reason=f"Failure threshold reached ({failures}/{self.fail_threshold})",
                    organization_id=org_id,
                    platform=platform
                )
            
        except Exception as e:
            logger.error(f"Error recording failure for {org_id}:{platform}: {e}")
    
    def get_state(self, org_id: str, platform: str) -> Dict[str, Any]:
        """
        Get current circuit breaker state
        
        Args:
            org_id: Organization ID
            platform: Platform name
            
        Returns:
            Dictionary with circuit breaker state info
        """
        try:
            key = f"{self.key_prefix}:{org_id}:{platform}"
            
            cb_data = self.redis.hmget(key, 'failures', 'last_failure', 'state')
            failures = int(cb_data[0]) if cb_data[0] else 0
            last_failure = float(cb_data[1]) if cb_data[1] else 0
            state = cb_data[2].decode() if cb_data[2] else 'closed'
            
            result = {
                'state': state,
                'failures': failures,
                'last_failure': last_failure,
                'threshold': self.fail_threshold,
                'cooldown_s': self.cooldown_s
            }
            
            if state == 'open' and last_failure > 0:
                remaining_cooldown = max(0, self.cooldown_s - (time.time() - last_failure))
                result['remaining_cooldown_s'] = remaining_cooldown
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting circuit breaker state for {org_id}:{platform}: {e}")
            return {
                'state': 'closed',
                'failures': 0,
                'last_failure': 0,
                'threshold': self.fail_threshold,
                'cooldown_s': self.cooldown_s
            }


class RetryableError(Exception):
    """Error that should trigger retry with backoff"""
    pass


class FatalError(Exception):
    """Error that should not be retried"""
    pass


def exponential_backoff_with_jitter(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """
    Calculate exponential backoff delay with jitter
    
    Args:
        attempt: Retry attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    # Add jitter: ±25% of calculated delay
    jitter = delay * 0.25 * (2 * random.random() - 1)
    return max(0.1, delay + jitter)


# Singleton instances
_token_bucket = None
_circuit_breaker = None


def get_token_bucket(redis_client: Optional[Redis] = None) -> TokenBucket:
    """
    Get token bucket rate limiter instance
    
    Args:
        redis_client: Redis client (will create default if not provided)
        
    Returns:
        TokenBucket instance
    """
    global _token_bucket
    
    if _token_bucket is None:
        if redis_client is None:
            # Create a simple Redis client for now
            try:
                import redis
                settings = get_settings()
                redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379/0')
                redis_client = redis.from_url(redis_url, decode_responses=False)
            except ImportError:
                # Mock Redis client if not available
                from unittest.mock import Mock
                redis_client = Mock()
                logger.warning("Redis not available, using mock client")
        
        settings = get_settings()
        
        _token_bucket = TokenBucket(
            redis_client=redis_client,
            key_prefix="rate",
            refill_rate=getattr(settings, 'publish_bucket_capacity', 60),
            capacity=getattr(settings, 'publish_bucket_capacity', 60),
            window_s=getattr(settings, 'publish_bucket_window_s', 60)
        )
    
    return _token_bucket


def get_circuit_breaker(redis_client: Optional[Redis] = None) -> CircuitBreaker:
    """
    Get circuit breaker instance
    
    Args:
        redis_client: Redis client (will create default if not provided)
        
    Returns:
        CircuitBreaker instance
    """
    global _circuit_breaker
    
    if _circuit_breaker is None:
        if redis_client is None:
            # Create a simple Redis client for now
            try:
                import redis
                settings = get_settings()
                redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379/0')
                redis_client = redis.from_url(redis_url, decode_responses=False)
            except ImportError:
                # Mock Redis client if not available
                from unittest.mock import Mock
                redis_client = Mock()
                logger.warning("Redis not available, using mock client")
        
        settings = get_settings()
        
        _circuit_breaker = CircuitBreaker(
            redis_client=redis_client,
            key_prefix="cb",
            fail_threshold=getattr(settings, 'cb_fail_threshold', 5),
            cooldown_s=getattr(settings, 'cb_cooldown_s', 120)
        )
    
    return _circuit_breaker