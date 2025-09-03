"""
Redis test fixtures using fakeredis
Provides isolated Redis test environment without external dependencies
"""
import pytest
from unittest.mock import Mock, patch
import logging

logger = logging.getLogger(__name__)

# Try to import fakeredis, fallback to mock if not available
try:
    import fakeredis
    FAKEREDIS_AVAILABLE = True
    logger.info("fakeredis available for testing")
except ImportError:
    FAKEREDIS_AVAILABLE = False
    logger.warning("fakeredis not available, using mock Redis for tests")


@pytest.fixture(scope="function")
def fake_redis():
    """
    Provide fake Redis instance for testing
    Uses fakeredis if available, otherwise provides mock
    """
    if FAKEREDIS_AVAILABLE:
        # Create isolated fake Redis instance for each test
        fake_redis_client = fakeredis.FakeRedis(decode_responses=False)
        return fake_redis_client
    else:
        # Fallback to comprehensive mock
        mock_redis = Mock()
        
        # Mock Redis operations with realistic behavior
        _mock_data = {}
        _mock_expiry = {}
        
        def mock_get(key):
            if key in _mock_data and key not in _mock_expiry:
                return _mock_data[key]
            return None
        
        def mock_set(key, value, ex=None):
            _mock_data[key] = value
            if ex:
                _mock_expiry[key] = ex
            return True
        
        def mock_setex(key, time, value):
            _mock_data[key] = value
            _mock_expiry[key] = time
            return True
        
        def mock_delete(*keys):
            count = 0
            for key in keys:
                if key in _mock_data:
                    del _mock_data[key]
                    if key in _mock_expiry:
                        del _mock_expiry[key]
                    count += 1
            return count
        
        def mock_exists(key):
            return key in _mock_data
        
        def mock_keys(pattern):
            import fnmatch
            return [k for k in _mock_data.keys() if fnmatch.fnmatch(k, pattern)]
        
        def mock_flushall():
            _mock_data.clear()
            _mock_expiry.clear()
            return True
        
        def mock_ping():
            return True
        
        def mock_info(section=None):
            return {
                'used_memory': 1024,
                'used_memory_peak': 2048,
                'connected_clients': 1
            }
        
        # Hash operations for rate limiting
        def mock_hmget(key, *fields):
            hash_data = _mock_data.get(key, {})
            return [hash_data.get(field) for field in fields]
        
        def mock_hmset(key, mapping):
            if key not in _mock_data:
                _mock_data[key] = {}
            _mock_data[key].update(mapping)
            return True
        
        def mock_expire(key, time):
            if key in _mock_data:
                _mock_expiry[key] = time
            return True
        
        # Multiple operations
        def mock_mget(keys):
            return [_mock_data.get(key) for key in keys]
        
        # Lua script execution (simplified)
        def mock_eval(script, numkeys, *keys_and_args):
            # For rate limiting, return success
            return [1, 50]  # Success + remaining tokens
        
        # Set up all mock methods
        mock_redis.get = mock_get
        mock_redis.set = mock_set
        mock_redis.setex = mock_setex
        mock_redis.delete = mock_delete
        mock_redis.exists = mock_exists
        mock_redis.keys = mock_keys
        mock_redis.flushall = mock_flushall
        mock_redis.ping = mock_ping
        mock_redis.info = mock_info
        mock_redis.hmget = mock_hmget
        mock_redis.hmset = mock_hmset
        mock_redis.expire = mock_expire
        mock_redis.mget = mock_mget
        mock_redis.eval = mock_eval
        
        # Additional methods for comprehensive coverage
        mock_redis.flushdb = mock_flushall
        mock_redis.dbsize = lambda: len(_mock_data)
        mock_redis.ttl = lambda key: _mock_expiry.get(key, -1)
        
        return mock_redis


@pytest.fixture(scope="function")  
def fake_async_redis():
    """
    Provide fake async Redis instance for testing
    """
    if FAKEREDIS_AVAILABLE:
        # Create async fake Redis instance
        fake_async_redis_client = fakeredis.aioredis.FakeRedis(decode_responses=False)
        return fake_async_redis_client
    else:
        # Mock async Redis with async methods
        mock_async_redis = Mock()
        
        # Storage for mock data
        _async_mock_data = {}
        _async_mock_expiry = {}
        
        async def async_mock_get(key):
            if key in _async_mock_data and key not in _async_mock_expiry:
                return _async_mock_data[key]
            return None
        
        async def async_mock_set(key, value, ex=None):
            _async_mock_data[key] = value
            if ex:
                _async_mock_expiry[key] = ex
            return True
        
        async def async_mock_setex(key, time, value):
            _async_mock_data[key] = value
            _async_mock_expiry[key] = time
            return True
        
        async def async_mock_delete(*keys):
            count = 0
            for key in keys:
                if key in _async_mock_data:
                    del _async_mock_data[key]
                    if key in _async_mock_expiry:
                        del _async_mock_expiry[key]
                    count += 1
            return count
        
        async def async_mock_exists(key):
            return key in _async_mock_data
        
        async def async_mock_keys(pattern):
            import fnmatch
            return [k for k in _async_mock_data.keys() if fnmatch.fnmatch(k, pattern)]
        
        async def async_mock_ping():
            return True
        
        async def async_mock_info(section=None):
            return {
                'used_memory': 1024,
                'used_memory_peak': 2048,
                'connected_clients': 1
            }
        
        async def async_mock_mget(keys):
            return [_async_mock_data.get(key) for key in keys]
        
        async def async_mock_close():
            _async_mock_data.clear()
            _async_mock_expiry.clear()
        
        # Scan iterator for pattern invalidation
        async def async_mock_scan_iter(match=None):
            import fnmatch
            for key in _async_mock_data.keys():
                if match is None or fnmatch.fnmatch(key, match):
                    yield key
        
        # Set up async methods
        mock_async_redis.get = async_mock_get
        mock_async_redis.set = async_mock_set
        mock_async_redis.setex = async_mock_setex
        mock_async_redis.delete = async_mock_delete
        mock_async_redis.exists = async_mock_exists
        mock_async_redis.keys = async_mock_keys
        mock_async_redis.ping = async_mock_ping
        mock_async_redis.info = async_mock_info
        mock_async_redis.mget = async_mock_mget
        mock_async_redis.close = async_mock_close
        mock_async_redis.scan_iter = async_mock_scan_iter
        
        return mock_async_redis


@pytest.fixture(scope="function")
def mock_redis_cache(fake_async_redis):
    """
    Mock the RedisCache service with fake Redis backend
    """
    from backend.services.redis_cache import RedisCache
    
    # Create RedisCache instance with mocked Redis
    cache = RedisCache()
    cache.redis_client = fake_async_redis
    cache.is_connected = True
    cache._connection_initialized = True
    
    return cache


@pytest.fixture(scope="function")
def mock_rate_limiter(fake_redis):
    """
    Mock the TokenBucket rate limiter with fake Redis backend
    """
    from backend.services.rate_limit import TokenBucket
    
    # Create TokenBucket with fake Redis
    rate_limiter = TokenBucket(
        redis_client=fake_redis,
        refill_rate=60,  # 60 requests per minute
        capacity=60,
        window_s=60
    )
    
    return rate_limiter


@pytest.fixture(scope="function")
def redis_test_config():
    """
    Configuration for Redis testing
    """
    return {
        "use_fakeredis": FAKEREDIS_AVAILABLE,
        "redis_url": "redis://fake-redis:6379/0" if FAKEREDIS_AVAILABLE else "mock://redis",
        "test_key_prefix": "test:",
        "cleanup_keys": True
    }


@pytest.fixture(autouse=True)
def patch_redis_connections(fake_redis, fake_async_redis):
    """
    Automatically patch Redis connections in tests
    This fixture runs for every test automatically
    """
    # Patch synchronous Redis connections
    with patch('redis.Redis') as mock_redis_class, \
         patch('redis.from_url') as mock_redis_from_url, \
         patch('redis.asyncio.Redis') as mock_async_redis_class, \
         patch('redis.asyncio.from_url') as mock_async_redis_from_url:
        
        # Configure sync Redis mocks
        mock_redis_class.return_value = fake_redis
        mock_redis_from_url.return_value = fake_redis
        
        # Configure async Redis mocks
        mock_async_redis_class.return_value = fake_async_redis
        mock_async_redis_from_url.return_value = fake_async_redis
        
        yield {
            'sync_redis': fake_redis,
            'async_redis': fake_async_redis
        }


@pytest.fixture(scope="function")
def clean_redis(fake_redis, fake_async_redis):
    """
    Clean Redis data before and after test
    """
    # Clean before test
    if FAKEREDIS_AVAILABLE:
        fake_redis.flushall()
    
    yield
    
    # Clean after test 
    if FAKEREDIS_AVAILABLE:
        fake_redis.flushall()


class RedisTestHelper:
    """
    Helper class for Redis testing operations
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def setup_test_data(self, data_dict):
        """Set up test data in Redis"""
        for key, value in data_dict.items():
            if isinstance(value, str):
                self.redis.set(key, value)
            elif isinstance(value, dict):
                self.redis.hmset(key, value)
            else:
                # Use JSON for complex data
                import json
                self.redis.set(key, json.dumps(value))
    
    def verify_key_exists(self, key):
        """Verify a key exists in Redis"""
        return self.redis.exists(key)
    
    def get_all_keys(self):
        """Get all keys from Redis"""
        return self.redis.keys("*")
    
    def cleanup_test_keys(self, prefix="test:"):
        """Clean up test keys with given prefix"""
        keys = self.redis.keys(f"{prefix}*")
        if keys:
            self.redis.delete(*keys)


@pytest.fixture
def redis_helper(fake_redis):
    """
    Provide Redis test helper
    """
    return RedisTestHelper(fake_redis)


# Test validation fixtures
@pytest.fixture
def validate_redis_test_setup():
    """
    Validate that Redis test setup is working correctly
    """
    def _validate():
        tests_passed = []
        
        # Test 1: fakeredis availability check
        if FAKEREDIS_AVAILABLE:
            tests_passed.append("fakeredis_available")
        else:
            tests_passed.append("fakeredis_mock_fallback")
        
        # Test 2: Basic Redis operations
        fake_client = fakeredis.FakeRedis() if FAKEREDIS_AVAILABLE else Mock()
        if FAKEREDIS_AVAILABLE:
            fake_client.set("test_key", "test_value")
            assert fake_client.get("test_key") == b"test_value"
            tests_passed.append("basic_operations")
        else:
            tests_passed.append("mock_operations")
        
        return {
            "tests_passed": tests_passed,
            "fakeredis_available": FAKEREDIS_AVAILABLE,
            "total_tests": len(tests_passed)
        }
    
    return _validate