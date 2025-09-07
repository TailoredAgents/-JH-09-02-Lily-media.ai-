"""
Unit tests for Distributed Rate Limiter - P0-13b
Tests for Redis-only rate limiting without fallbacks
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from backend.services.distributed_rate_limiter import (
    DistributedRateLimiter,
    RateLimitConfig,
    RateLimitResult,
    RateLimitInfo,
    distributed_rate_limiter,
    rate_limiter_context
)

class TestDistributedRateLimiter:
    """Test cases for DistributedRateLimiter"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        redis_mock = AsyncMock()
        redis_mock.ping = AsyncMock(return_value=True)
        redis_mock.register_script = Mock(return_value=AsyncMock())
        return redis_mock
    
    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """Rate limiter instance with mocked Redis"""
        limiter = DistributedRateLimiter("redis://localhost:6379/0")
        limiter.redis_client = mock_redis
        limiter.is_initialized = True
        return limiter
    
    @pytest.fixture
    def rate_config(self):
        """Standard rate limiting configuration"""
        return RateLimitConfig(
            requests_per_second=5,
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_limit=10,
            burst_window_seconds=10
        )

    @pytest.mark.asyncio
    async def test_initialization_success(self):
        """Test successful rate limiter initialization"""
        with patch('backend.services.distributed_rate_limiter.REDIS_AVAILABLE', True):
            with patch('backend.services.distributed_rate_limiter.redis') as mock_redis_module:
                mock_pool = AsyncMock()
                mock_client = AsyncMock()
                mock_client.ping = AsyncMock(return_value=True)
                
                mock_redis_module.ConnectionPool.from_url = Mock(return_value=mock_pool)
                mock_redis_module.Redis = Mock(return_value=mock_client)
                
                limiter = DistributedRateLimiter()
                await limiter.initialize()
                
                assert limiter.is_initialized
                assert limiter.redis_client == mock_client
                mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_redis_unavailable(self):
        """Test initialization when Redis is unavailable"""
        with patch('backend.services.distributed_rate_limiter.REDIS_AVAILABLE', False):
            limiter = DistributedRateLimiter()
            
            with pytest.raises(RuntimeError, match="Redis is required"):
                await limiter.initialize()

    @pytest.mark.asyncio
    async def test_initialization_connection_failure(self):
        """Test initialization when Redis connection fails"""
        with patch('backend.services.distributed_rate_limiter.REDIS_AVAILABLE', True):
            with patch('backend.services.distributed_rate_limiter.redis') as mock_redis_module:
                mock_redis_module.ConnectionPool.from_url.side_effect = Exception("Connection failed")
                
                limiter = DistributedRateLimiter()
                
                with pytest.raises(RuntimeError, match="Redis connection required"):
                    await limiter.initialize()

    def test_get_rate_limit_keys(self, rate_limiter):
        """Test rate limit key generation"""
        keys = rate_limiter._get_rate_limit_keys("test_user", "org_123")
        
        assert "rate_limit:org_123:test_user:second" in keys["second"]
        assert "rate_limit:org_123:test_user:minute" in keys["minute"]
        assert "rate_limit:org_123:test_user:hour" in keys["hour"]
        assert "rate_limit:org_123:test_user:burst" in keys["burst"]
        
        # Test global keys (no org)
        global_keys = rate_limiter._get_rate_limit_keys("test_user")
        assert "rate_limit:global:test_user:second" in global_keys["second"]

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, rate_limiter, rate_config, mock_redis):
        """Test rate limit check when request is allowed"""
        # Mock Lua script to return 'allowed'
        mock_script = AsyncMock()
        mock_script.return_value = ['allowed', 50, time.time() + 60, 0]
        rate_limiter._multi_window_script = mock_script
        
        result = await rate_limiter.check_rate_limit("test_user", "org_123", rate_config)
        
        assert result.result == RateLimitResult.ALLOWED
        assert result.remaining == 50
        mock_script.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_rate_limit_rate_limited(self, rate_limiter, rate_config, mock_redis):
        """Test rate limit check when rate limited"""
        # Mock Lua script to return rate limit exceeded
        mock_script = AsyncMock()
        mock_script.return_value = ['minute', 0, time.time() + 30, 30]
        rate_limiter._multi_window_script = mock_script
        
        result = await rate_limiter.check_rate_limit("test_user", "org_123", rate_config)
        
        assert result.result == RateLimitResult.RATE_LIMITED
        assert result.remaining == 0
        assert result.retry_after == 30
        assert result.limit_type == "minute"
        assert "Rate limit exceeded" in result.message

    @pytest.mark.asyncio
    async def test_check_rate_limit_redis_error(self, rate_limiter, rate_config, mock_redis):
        """Test rate limit check when Redis fails"""
        # Mock Lua script to raise exception
        mock_script = AsyncMock()
        mock_script.side_effect = Exception("Redis connection lost")
        rate_limiter._multi_window_script = mock_script
        
        result = await rate_limiter.check_rate_limit("test_user", "org_123", rate_config)
        
        assert result.result == RateLimitResult.REDIS_ERROR
        assert result.remaining == 0
        assert result.retry_after == 60
        assert "Rate limiting service unavailable" in result.message

    @pytest.mark.asyncio
    async def test_get_rate_limit_status(self, rate_limiter, mock_redis):
        """Test getting rate limit status"""
        # Mock Redis pipeline operations
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(return_value=[
            None, 5,   # second: cleanup + count
            None, 45,  # minute: cleanup + count  
            None, 500, # hour: cleanup + count
            None, 2    # burst: cleanup + count
        ])
        mock_redis.pipeline.return_value = mock_pipe
        
        status = await rate_limiter.get_rate_limit_status("test_user", "org_123")
        
        assert status["identifier"] == "test_user"
        assert status["org_id"] == "org_123"
        assert status["current_usage"]["second"] == 5
        assert status["current_usage"]["minute"] == 45
        assert status["current_usage"]["hour"] == 500
        assert status["current_usage"]["burst"] == 2

    @pytest.mark.asyncio
    async def test_reset_rate_limit(self, rate_limiter, mock_redis):
        """Test resetting rate limits for an identifier"""
        mock_redis.delete = AsyncMock(return_value=4)  # 4 keys deleted
        
        result = await rate_limiter.reset_rate_limit("test_user", "org_123")
        
        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_rate_limit_failure(self, rate_limiter, mock_redis):
        """Test rate limit reset when Redis fails"""
        mock_redis.delete = AsyncMock(side_effect=Exception("Redis error"))
        
        result = await rate_limiter.reset_rate_limit("test_user", "org_123")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_top_rate_limited(self, rate_limiter, mock_redis):
        """Test getting top rate-limited identifiers"""
        # Mock scan_iter to return some keys
        mock_redis.scan_iter = AsyncMock()
        mock_redis.scan_iter.return_value = [
            "rate_limit:org_123:user1:minute",
            "rate_limit:org_123:user2:minute"
        ]
        
        # Mock zcard to return counts
        mock_redis.zcard = AsyncMock(side_effect=[10, 5])
        
        result = await rate_limiter.get_top_rate_limited("org_123", limit=2)
        
        assert len(result) == 2
        assert result[0]["identifier"] == "user1"
        assert result[0]["requests_in_minute"] == 10
        assert result[1]["identifier"] == "user2" 
        assert result[1]["requests_in_minute"] == 5

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, rate_limiter, mock_redis):
        """Test health check when everything is working"""
        # Mock script execution for health check
        mock_script = AsyncMock()
        mock_script.return_value = [1, 99, time.time() + 60]  # Successful test
        rate_limiter._sliding_window_script = mock_script
        
        health = await rate_limiter.health_check()
        
        assert health["status"] == "healthy"
        assert health["redis_connected"] is True
        assert health["scripts_loaded"] is True
        assert health["error"] is None

    @pytest.mark.asyncio
    async def test_health_check_redis_down(self, rate_limiter, mock_redis):
        """Test health check when Redis is down"""
        mock_redis.ping.side_effect = Exception("Connection refused")
        
        health = await rate_limiter.health_check()
        
        assert health["status"] == "unhealthy"
        assert health["redis_connected"] is False
        assert "Connection refused" in health["error"]

    @pytest.mark.asyncio
    async def test_close(self, rate_limiter, mock_redis):
        """Test closing connections"""
        mock_pool = AsyncMock()
        rate_limiter.connection_pool = mock_pool
        
        await rate_limiter.close()
        
        mock_redis.close.assert_called_once()
        mock_pool.disconnect.assert_called_once()

class TestRateLimiterContext:
    """Test rate limiter context manager"""
    
    @pytest.mark.asyncio
    async def test_context_manager_success(self):
        """Test successful context manager usage"""
        with patch('backend.services.distributed_rate_limiter.distributed_rate_limiter') as mock_limiter:
            mock_limiter.initialize = AsyncMock()
            mock_limiter.close = AsyncMock()
            
            async with rate_limiter_context() as limiter:
                assert limiter == mock_limiter
            
            mock_limiter.initialize.assert_called_once()
            mock_limiter.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exception(self):
        """Test context manager with exception"""
        with patch('backend.services.distributed_rate_limiter.distributed_rate_limiter') as mock_limiter:
            mock_limiter.initialize = AsyncMock()
            mock_limiter.close = AsyncMock()
            
            with pytest.raises(ValueError):
                async with rate_limiter_context():
                    raise ValueError("Test exception")
            
            # Close should still be called
            mock_limiter.close.assert_called_once()

class TestRateLimitConfig:
    """Test RateLimitConfig data class"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = RateLimitConfig()
        
        assert config.requests_per_second == 10
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.burst_limit == 20
        assert config.burst_window_seconds == 10

    def test_custom_config(self):
        """Test custom configuration values"""
        config = RateLimitConfig(
            requests_per_second=5,
            requests_per_minute=100,
            requests_per_hour=2000,
            burst_limit=50,
            burst_window_seconds=30
        )
        
        assert config.requests_per_second == 5
        assert config.requests_per_minute == 100
        assert config.requests_per_hour == 2000
        assert config.burst_limit == 50
        assert config.burst_window_seconds == 30

class TestRateLimitInfo:
    """Test RateLimitInfo data class"""
    
    def test_allowed_info(self):
        """Test allowed rate limit info"""
        info = RateLimitInfo(
            result=RateLimitResult.ALLOWED,
            remaining=45,
            reset_time=time.time() + 60
        )
        
        assert info.result == RateLimitResult.ALLOWED
        assert info.remaining == 45
        assert info.retry_after is None
        assert info.limit_type is None

    def test_rate_limited_info(self):
        """Test rate limited info"""
        info = RateLimitInfo(
            result=RateLimitResult.RATE_LIMITED,
            remaining=0,
            reset_time=time.time() + 30,
            retry_after=30,
            limit_type="minute",
            message="Rate limit exceeded: minute limit reached"
        )
        
        assert info.result == RateLimitResult.RATE_LIMITED
        assert info.remaining == 0
        assert info.retry_after == 30
        assert info.limit_type == "minute"
        assert "Rate limit exceeded" in info.message

    def test_redis_error_info(self):
        """Test Redis error info"""
        info = RateLimitInfo(
            result=RateLimitResult.REDIS_ERROR,
            remaining=0,
            reset_time=time.time() + 60,
            retry_after=60,
            message="Rate limiting service unavailable: Connection failed"
        )
        
        assert info.result == RateLimitResult.REDIS_ERROR
        assert info.remaining == 0
        assert info.retry_after == 60
        assert "Rate limiting service unavailable" in info.message

@pytest.mark.integration
class TestDistributedRateLimiterIntegration:
    """Integration tests requiring real Redis (optional)"""
    
    @pytest.mark.skip(reason="Requires Redis server - enable for integration testing")
    @pytest.mark.asyncio
    async def test_real_redis_integration(self):
        """Test with real Redis server"""
        limiter = DistributedRateLimiter("redis://localhost:6379/1")  # Test DB
        
        try:
            await limiter.initialize()
            
            config = RateLimitConfig(requests_per_second=2, requests_per_minute=10)
            
            # First request should be allowed
            result1 = await limiter.check_rate_limit("integration_test", None, config)
            assert result1.result == RateLimitResult.ALLOWED
            
            # Second request should be allowed
            result2 = await limiter.check_rate_limit("integration_test", None, config)
            assert result2.result == RateLimitResult.ALLOWED
            
            # Third request should be rate limited
            result3 = await limiter.check_rate_limit("integration_test", None, config)
            assert result3.result == RateLimitResult.RATE_LIMITED
            
            # Clean up
            await limiter.reset_rate_limit("integration_test")
            
        finally:
            await limiter.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])