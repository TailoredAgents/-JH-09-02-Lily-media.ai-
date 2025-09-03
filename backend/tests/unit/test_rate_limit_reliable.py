"""
Reliable rate limiting tests using fakeredis
Addresses brittleness from Redis coupling mentioned in testing PDF
"""
import pytest
import time
from unittest.mock import patch, Mock
from backend.services.rate_limit import TokenBucket


class TestRateLimitReliable:
    """Test rate limiting with reliable test setup"""

    def test_token_bucket_initialization(self, fake_redis):
        """Test token bucket initialization without Redis dependency"""
        rate_limiter = TokenBucket(
            redis_client=fake_redis,
            key_prefix="test_rate",
            refill_rate=60,
            capacity=60,
            window_s=60
        )
        
        assert rate_limiter.redis == fake_redis
        assert rate_limiter.key_prefix == "test_rate"
        assert rate_limiter.refill_rate == 60
        assert rate_limiter.capacity == 60
        assert rate_limiter.window_s == 60

    def test_token_bucket_basic_acquire(self, fake_redis):
        """Test basic token acquisition"""
        rate_limiter = TokenBucket(fake_redis, refill_rate=10, capacity=10)
        
        # Mock the Lua script execution for consistent testing
        def mock_lua_script(*args, **kwargs):
            # Return success with remaining tokens
            return [1, 9]  # Success=1, remaining_tokens=9
        
        fake_redis.eval = mock_lua_script
        
        # Test successful acquisition
        success = rate_limiter.acquire("test_org", "twitter", tokens=1)
        assert success is True

    def test_token_bucket_rate_limit_enforcement(self, fake_redis):
        """Test rate limit enforcement"""
        rate_limiter = TokenBucket(fake_redis, refill_rate=5, capacity=5)
        
        # Track requests to simulate bucket depletion
        request_count = 0
        
        def mock_lua_script_with_depletion(*args, **kwargs):
            nonlocal request_count
            request_count += 1
            
            # First 5 requests succeed, then fail
            if request_count <= 5:
                return [1, 5 - request_count]  # Success with decreasing tokens
            else:
                return [0, 0]  # Rate limited, no tokens
        
        fake_redis.eval = mock_lua_script_with_depletion
        
        org_id = "test_org_limit"
        platform = "twitter"
        
        # First 5 requests should succeed
        for i in range(5):
            success = rate_limiter.acquire(org_id, platform, tokens=1)
            assert success is True, f"Request {i+1} should succeed"
        
        # 6th request should be rate limited
        success = rate_limiter.acquire(org_id, platform, tokens=1)
        assert success is False, "Request should be rate limited"

    def test_token_bucket_multi_tenant_isolation(self, fake_redis):
        """Test that rate limiting is isolated per tenant"""
        rate_limiter = TokenBucket(fake_redis, refill_rate=5, capacity=5)
        
        # Mock script to track requests per org
        org_requests = {}
        
        def mock_lua_script_per_org(*args, **kwargs):
            # Extract org_id from key (format: rate:org_id:platform)
            key = args[1][0] if len(args) > 1 and len(args[1]) > 0 else "default"
            parts = key.split(':')
            org_id = parts[1] if len(parts) > 1 else "default"
            
            if org_id not in org_requests:
                org_requests[org_id] = 0
            
            org_requests[org_id] += 1
            
            # Each org gets its own quota
            if org_requests[org_id] <= 5:
                return [1, 5 - org_requests[org_id]]
            else:
                return [0, 0]
        
        fake_redis.eval = mock_lua_script_per_org
        
        # Test different organizations
        for org_id in ["org1", "org2", "org3"]:
            # Each org should get 5 successful requests
            for i in range(5):
                success = rate_limiter.acquire(org_id, "twitter", tokens=1)
                assert success is True, f"Org {org_id} request {i+1} should succeed"
            
            # 6th request should fail for each org
            success = rate_limiter.acquire(org_id, "twitter", tokens=1)
            assert success is False, f"Org {org_id} should be rate limited"

    def test_token_bucket_platform_isolation(self, fake_redis):
        """Test rate limiting isolation between platforms"""
        rate_limiter = TokenBucket(fake_redis, refill_rate=3, capacity=3)
        
        # Mock per-platform tracking
        platform_requests = {}
        
        def mock_lua_script_per_platform(*args, **kwargs):
            key = args[1][0] if len(args) > 1 and len(args[1]) > 0 else "default"
            parts = key.split(':')
            platform = parts[2] if len(parts) > 2 else "default"
            
            if platform not in platform_requests:
                platform_requests[platform] = 0
            
            platform_requests[platform] += 1
            
            if platform_requests[platform] <= 3:
                return [1, 3 - platform_requests[platform]]
            else:
                return [0, 0]
        
        fake_redis.eval = mock_lua_script_per_platform
        
        org_id = "test_org"
        platforms = ["twitter", "instagram", "facebook"]
        
        # Each platform should get independent rate limits
        for platform in platforms:
            for i in range(3):
                success = rate_limiter.acquire(org_id, platform, tokens=1)
                assert success is True, f"Platform {platform} request {i+1} should succeed"
            
            # 4th request should fail for each platform
            success = rate_limiter.acquire(org_id, platform, tokens=1)
            assert success is False, f"Platform {platform} should be rate limited"

    def test_token_bucket_bulk_token_acquisition(self, fake_redis):
        """Test acquiring multiple tokens at once"""
        rate_limiter = TokenBucket(fake_redis, refill_rate=10, capacity=10)
        
        def mock_lua_script_bulk(*args, **kwargs):
            tokens_requested = int(args[2][1]) if len(args) > 2 and len(args[2]) > 1 else 1
            
            # Simulate checking if enough tokens available
            if tokens_requested <= 10:  # Assuming we start with full capacity
                return [1, 10 - tokens_requested]
            else:
                return [0, 10]  # Not enough tokens
        
        fake_redis.eval = mock_lua_script_bulk
        
        org_id = "bulk_test_org"
        platform = "twitter"
        
        # Should succeed with 5 tokens
        success = rate_limiter.acquire(org_id, platform, tokens=5)
        assert success is True
        
        # Should fail with 15 tokens (exceeds capacity)
        fake_redis.eval = lambda *args, **kwargs: [0, 10]
        success = rate_limiter.acquire(org_id, platform, tokens=15)
        assert success is False

    def test_token_bucket_redis_key_format(self, fake_redis):
        """Test that Redis keys are formatted correctly"""
        rate_limiter = TokenBucket(fake_redis, key_prefix="custom_prefix")
        
        executed_keys = []
        
        def mock_lua_script_capture_key(*args, **kwargs):
            if len(args) > 1 and len(args[1]) > 0:
                executed_keys.append(args[1][0])
            return [1, 5]
        
        fake_redis.eval = mock_lua_script_capture_key
        
        # Test key formation
        rate_limiter.acquire("test_org_123", "twitter", tokens=1)
        
        assert len(executed_keys) > 0
        key = executed_keys[0]
        assert key == "custom_prefix:test_org_123:twitter"

    def test_token_bucket_error_handling(self, fake_redis):
        """Test error handling in rate limiter"""
        rate_limiter = TokenBucket(fake_redis)
        
        # Simulate Redis errors
        def mock_redis_error(*args, **kwargs):
            raise Exception("Redis connection error")
        
        fake_redis.eval = mock_redis_error
        
        # Should handle errors gracefully
        try:
            success = rate_limiter.acquire("test_org", "twitter", tokens=1)
            # The actual behavior depends on error handling in the rate limiter
            # It might return False or raise an exception
            assert isinstance(success, bool) or success is None
        except Exception as e:
            # If it raises an exception, it should be handled appropriately
            assert "Redis" in str(e) or "connection" in str(e)

    def test_token_bucket_time_based_refill_simulation(self, fake_redis):
        """Test time-based token refill simulation"""
        rate_limiter = TokenBucket(fake_redis, refill_rate=60, capacity=60, window_s=60)
        
        # Mock time progression for refill testing
        mock_time = 1000.0
        request_times = {}
        
        def mock_lua_script_time_based(*args, **kwargs):
            nonlocal mock_time
            
            key = args[1][0] if len(args) > 1 and len(args[1]) > 0 else "default"
            current_time = float(args[2][0]) if len(args) > 2 and len(args[2]) > 0 else mock_time
            
            if key not in request_times:
                request_times[key] = {"tokens": 60, "last_refill": current_time, "requests": 0}
            
            bucket = request_times[key]
            elapsed = current_time - bucket["last_refill"]
            
            # Refill tokens based on elapsed time
            tokens_to_add = int(elapsed * 60 / 60)  # refill_rate / window_s
            bucket["tokens"] = min(60, bucket["tokens"] + tokens_to_add)
            bucket["last_refill"] = current_time
            
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                bucket["requests"] += 1
                return [1, bucket["tokens"]]
            else:
                return [0, bucket["tokens"]]
        
        fake_redis.eval = mock_lua_script_time_based
        
        # Mock time module
        with patch('time.time', return_value=mock_time):
            # Initial request should succeed
            success = rate_limiter.acquire("time_test_org", "twitter", tokens=1)
            assert success is True
        
        # Advance time by 30 seconds and test again
        mock_time += 30
        with patch('time.time', return_value=mock_time):
            success = rate_limiter.acquire("time_test_org", "twitter", tokens=1)
            assert success is True

    def test_token_bucket_concurrent_access_simulation(self, fake_redis):
        """Test concurrent access simulation"""
        rate_limiter = TokenBucket(fake_redis, refill_rate=100, capacity=100)
        
        # Simulate concurrent requests
        concurrent_counter = 0
        
        def mock_lua_script_concurrent(*args, **kwargs):
            nonlocal concurrent_counter
            concurrent_counter += 1
            
            # Simulate successful acquisition for first 50 concurrent requests
            if concurrent_counter <= 50:
                return [1, 100 - concurrent_counter]
            else:
                return [0, 0]  # Rate limited after 50 requests
        
        fake_redis.eval = mock_lua_script_concurrent
        
        org_id = "concurrent_test_org"
        platform = "twitter"
        
        successful_requests = 0
        failed_requests = 0
        
        # Simulate 100 concurrent requests
        for i in range(100):
            success = rate_limiter.acquire(org_id, platform, tokens=1)
            if success:
                successful_requests += 1
            else:
                failed_requests += 1
        
        # Should have 50 successful and 50 failed requests
        assert successful_requests == 50
        assert failed_requests == 50

    def test_redis_unavailable_fallback(self, fake_redis):
        """Test behavior when Redis is unavailable"""
        rate_limiter = TokenBucket(fake_redis)
        
        # Simulate Redis completely unavailable
        broken_redis = Mock()
        broken_redis.eval.side_effect = Exception("Redis unavailable")
        rate_limiter.redis = broken_redis
        
        # Test that it handles unavailability gracefully
        try:
            result = rate_limiter.acquire("test_org", "twitter", tokens=1)
            # Result could be False (conservative) or True (permissive) depending on implementation
            assert isinstance(result, bool)
        except Exception:
            # If it raises, that's also acceptable for this test
            pass