"""
Unit tests for circuit breaker (Phase 8)
Tests transitions: closed → open → half-open → closed
Updated to use fakeredis for reliable testing
"""
import time
import pytest
from unittest.mock import Mock, MagicMock
import redis

from backend.services.rate_limit import CircuitBreaker


class TestCircuitBreaker:
    """Test circuit breaker functionality with reliable Redis testing"""
    
    def test_init_with_fake_redis(self, fake_redis):
        """Test circuit breaker initialization with fake Redis"""
        breaker = CircuitBreaker(
            redis_client=fake_redis,
            key_prefix="test_cb",
            fail_threshold=3,
            cooldown_s=60
        )
        
        assert breaker.redis == fake_redis
        assert breaker.key_prefix == "test_cb"
        assert breaker.fail_threshold == 3
        assert breaker.cooldown_s == 60
    
    def test_init_with_custom_params(self, fake_redis):
        """Test circuit breaker initialization with custom parameters"""
        breaker = CircuitBreaker(
            redis_client=fake_redis,
            key_prefix="custom",
            fail_threshold=5,
            cooldown_s=120
        )
        
        assert breaker.key_prefix == "custom"
        assert breaker.fail_threshold == 5
        assert breaker.cooldown_s == 120
    
    def test_allow_closed_state(self, fake_redis):
        """Test allow() in closed state (normal operation)"""
        breaker = CircuitBreaker(
            redis_client=fake_redis,
            key_prefix="test_cb",
            fail_threshold=3,
            cooldown_s=60
        )
        
        # Mock Redis to return closed state
        fake_redis.eval = lambda *args, **kwargs: 1  # Allow request
        
        result = breaker.allow("org123", "meta")
        
        assert result is True
    
    def test_allow_open_state_within_cooldown(self, fake_redis):
        """Test allow() in open state within cooldown period"""
        breaker = CircuitBreaker(
            redis_client=fake_redis,
            key_prefix="test_cb",
            fail_threshold=3,
            cooldown_s=60
        )
        
        # Mock Redis to return open state within cooldown
        fake_redis.eval = lambda *args, **kwargs: 0  # Block request
        
        result = breaker.allow("org123", "meta")
        
        assert result is False
    
    def test_allow_open_state_after_cooldown(self):
        """Test allow() transitions to half-open after cooldown"""
        # Mock Redis to return allow (transition to half-open)
        self.mock_redis.eval.return_value = 1  # Allow test request
        
        result = self.breaker.allow("org123", "meta")
        
        assert result is True
    
    def test_allow_half_open_state(self):
        """Test allow() in half-open state (test request allowed)"""
        self.mock_redis.eval.return_value = 1  # Allow test request
        
        result = self.breaker.allow("org123", "meta")
        
        assert result is True
    
    def test_allow_redis_error_fail_open(self):
        """Test fail-open behavior when Redis is unavailable"""
        self.mock_redis.eval.side_effect = redis.RedisError("Connection failed")
        
        # Should allow request despite Redis error
        result = self.breaker.allow("org123", "meta")
        
        assert result is True
    
    def test_record_success_closed_state(self):
        """Test recording success in closed state"""
        # Should reset failure count
        self.breaker.record_success("org123", "meta")
        
        # Verify Redis script was called
        self.mock_redis.eval.assert_called_once()
    
    def test_record_success_half_open_state(self):
        """Test recording success in half-open state (transition to closed)"""
        self.breaker.record_success("org123", "meta")
        
        # Should call Redis to transition to closed state
        self.mock_redis.eval.assert_called_once()
    
    def test_record_success_redis_error(self):
        """Test recording success with Redis error"""
        self.mock_redis.eval.side_effect = redis.RedisError("Connection failed")
        
        # Should not raise exception
        self.breaker.record_success("org123", "meta")
    
    def test_record_failure_below_threshold(self):
        """Test recording failure below threshold (stays closed)"""
        self.mock_redis.eval.return_value = 2  # 2 failures, below threshold
        
        self.breaker.record_failure("org123", "meta")
        
        self.mock_redis.eval.assert_called_once()
    
    def test_record_failure_at_threshold(self):
        """Test recording failure at threshold (opens circuit)"""
        self.mock_redis.eval.return_value = 3  # 3 failures, at threshold
        
        self.breaker.record_failure("org123", "meta")
        
        # Should call Redis to open circuit
        self.mock_redis.eval.assert_called_once()
    
    def test_record_failure_half_open_state(self):
        """Test recording failure in half-open state (back to open)"""
        self.mock_redis.eval.return_value = 1  # 1 failure in half-open
        
        self.breaker.record_failure("org123", "meta")
        
        # Should call Redis to transition back to open
        self.mock_redis.eval.assert_called_once()
    
    def test_record_failure_redis_error(self):
        """Test recording failure with Redis error"""
        self.mock_redis.eval.side_effect = redis.RedisError("Connection failed")
        
        # Should not raise exception
        self.breaker.record_failure("org123", "meta")
    
    def test_get_state_closed(self):
        """Test getting circuit breaker state when closed"""
        # Mock Redis to return closed state data
        self.mock_redis.hmget.return_value = [b'2', b'1234567890.0', b'closed']
        
        state = self.breaker.get_state("org123", "meta")
        
        assert state['state'] == 'closed'
        assert state['failures'] == 2
        assert state['last_failure'] == 1234567890.0
        assert state['threshold'] == 3
        assert state['cooldown_s'] == 60
        assert 'remaining_cooldown_s' not in state
    
    def test_get_state_open_with_cooldown(self):
        """Test getting circuit breaker state when open with remaining cooldown"""
        now = time.time()
        last_failure = now - 30  # 30 seconds ago
        
        # Mock Redis to return open state
        self.mock_redis.hmget.return_value = [b'5', str(last_failure).encode(), b'open']
        
        state = self.breaker.get_state("org123", "meta")
        
        assert state['state'] == 'open'
        assert state['failures'] == 5
        assert state['last_failure'] == last_failure
        assert 'remaining_cooldown_s' in state
        
        # Should have remaining cooldown time
        remaining = state['remaining_cooldown_s']
        assert 25 <= remaining <= 35  # Approximately 30 seconds remaining
    
    def test_get_state_new_circuit(self):
        """Test getting state for new circuit (no Redis data)"""
        # Mock Redis to return None values (new circuit)
        self.mock_redis.hmget.return_value = [None, None, None]
        
        state = self.breaker.get_state("org123", "meta")
        
        assert state['state'] == 'closed'
        assert state['failures'] == 0
        assert state['last_failure'] == 0
        assert state['threshold'] == 3
        assert state['cooldown_s'] == 60
    
    def test_get_state_redis_error(self):
        """Test getting state with Redis error"""
        self.mock_redis.hmget.side_effect = redis.RedisError("Connection failed")
        
        state = self.breaker.get_state("org123", "meta")
        
        # Should return default closed state
        assert state['state'] == 'closed'
        assert state['failures'] == 0
        assert state['last_failure'] == 0
    
    def test_tenant_isolation(self):
        """Test that different orgs have separate circuit breakers"""
        self.mock_redis.eval.return_value = 1
        
        # Check different orgs
        result1 = self.breaker.allow("org123", "meta")
        result2 = self.breaker.allow("org456", "meta")
        
        assert result1 is True
        assert result2 is True
        
        # Verify different keys were used
        assert self.mock_redis.eval.call_count == 2
        calls = self.mock_redis.eval.call_args_list
        
        key1 = calls[0][0][1]  # First call, second argument (key)
        key2 = calls[1][0][1]  # Second call, second argument (key)
        
        assert key1 != key2
        assert "org123" in key1
        assert "org456" in key2
    
    def test_platform_isolation(self):
        """Test that different platforms have separate circuit breakers"""
        self.mock_redis.eval.return_value = 1
        
        # Check different platforms
        result1 = self.breaker.allow("org123", "meta")
        result2 = self.breaker.allow("org123", "x")
        
        assert result1 is True
        assert result2 is True
        
        # Verify different keys were used
        assert self.mock_redis.eval.call_count == 2
        calls = self.mock_redis.eval.call_args_list
        
        key1 = calls[0][0][1]
        key2 = calls[1][0][1]
        
        assert key1 != key2
        assert "meta" in key1
        assert "x" in key2
    
    def test_failure_threshold_transition(self):
        """Test complete failure threshold transition workflow"""
        org_id = "org123"
        platform = "meta"
        
        # Start in closed state - allow requests
        self.mock_redis.eval.return_value = 1
        assert self.breaker.allow(org_id, platform) is True
        
        # Record failures up to threshold
        self.mock_redis.eval.return_value = 1  # First failure
        self.breaker.record_failure(org_id, platform)
        
        self.mock_redis.eval.return_value = 2  # Second failure
        self.breaker.record_failure(org_id, platform)
        
        self.mock_redis.eval.return_value = 3  # Third failure - should open circuit
        self.breaker.record_failure(org_id, platform)
        
        # Now in open state - should block requests
        self.mock_redis.eval.return_value = 0
        assert self.breaker.allow(org_id, platform) is False
        
        # After cooldown - should allow test request (half-open)
        self.mock_redis.eval.return_value = 1
        assert self.breaker.allow(org_id, platform) is True
        
        # Success in half-open - should close circuit
        self.breaker.record_success(org_id, platform)
        
        # Verify Redis operations were called appropriately
        assert self.mock_redis.eval.call_count >= 6