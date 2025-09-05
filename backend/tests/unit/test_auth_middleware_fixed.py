"""
Unit tests for fixed authentication middleware - critical for R1 resolution
Tests the fixes for broken Auth0 references and Redis integration
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

from backend.auth.middleware import JWTValidationMiddleware
from backend.auth.jwt_handler import jwt_handler


@pytest.fixture
def mock_redis():
    """Mock Redis cache"""
    mock_redis = AsyncMock()
    return mock_redis


@pytest.fixture
def auth_middleware(mock_redis):
    """Authentication middleware with mocked Redis"""
    middleware = JWTValidationMiddleware()
    middleware.redis = mock_redis
    return middleware


class TestAuthMiddlewareFixed:
    """Test suite for fixed authentication middleware"""

    @pytest.mark.asyncio
    async def test_validate_token_with_redis_cache_hit(self, auth_middleware, mock_redis):
        """Test successful token validation with Redis cache hit"""
        # Arrange
        token = "valid_jwt_token"
        cached_payload = {"user_id": 123, "email": "test@example.com"}
        
        mock_redis.get.return_value = '{"user_id": 123, "email": "test@example.com"}'
        mock_redis.exists.return_value = False  # Not blacklisted
        
        # Act
        result = await auth_middleware._validate_token(token)
        
        # Assert
        assert result == cached_payload
        mock_redis.get.assert_called_once_with(f"jwt_cache:{token}")
        mock_redis.exists.assert_called_once_with(f"jwt_blacklist:{token}")

    @pytest.mark.asyncio
    async def test_validate_token_cache_miss_valid_token(self, auth_middleware, mock_redis):
        """Test token validation with cache miss but valid JWT"""
        # Arrange
        token = "valid_jwt_token"
        payload = {"user_id": 123, "email": "test@example.com"}
        
        mock_redis.get.return_value = None  # Cache miss
        mock_redis.exists.return_value = False  # Not blacklisted
        mock_redis.set.return_value = True
        
        with patch.object(jwt_handler, 'verify_token', return_value=payload):
            # Act
            result = await auth_middleware._validate_token(token)
            
            # Assert
            assert result == payload
            jwt_handler.verify_token.assert_called_once_with(token)
            
            # Verify token was cached
            mock_redis.set.assert_called_once_with(
                f"jwt_cache:{token}",
                '{"user_id": 123, "email": "test@example.com"}',
                ex=1800  # 30 minutes
            )

    @pytest.mark.asyncio
    async def test_validate_token_blacklisted_raises_exception(self, auth_middleware, mock_redis):
        """Test that blacklisted tokens raise HTTPException"""
        # Arrange
        token = "blacklisted_token"
        mock_redis.exists.return_value = True  # Token is blacklisted
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware._validate_token(token)
        
        assert exc_info.value.status_code == 401
        assert "Token has been revoked" in str(exc_info.value.detail)
        mock_redis.exists.assert_called_once_with(f"jwt_blacklist:{token}")

    @pytest.mark.asyncio
    async def test_validate_token_invalid_jwt_raises_exception(self, auth_middleware, mock_redis):
        """Test that invalid JWT tokens raise HTTPException"""
        # Arrange
        token = "invalid_jwt_token"
        
        mock_redis.get.return_value = None  # Cache miss
        mock_redis.exists.return_value = False  # Not blacklisted
        
        with patch.object(jwt_handler, 'verify_token', side_effect=Exception("Invalid token")):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await auth_middleware._validate_token(token)
            
            assert exc_info.value.status_code == 401
            assert "Invalid token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_is_token_cached_and_valid_returns_payload(self, auth_middleware, mock_redis):
        """Test cached token retrieval with valid payload"""
        # Arrange
        token = "cached_token"
        cached_data = '{"user_id": 456, "email": "cached@example.com"}'
        mock_redis.get.return_value = cached_data
        
        # Act
        result = await auth_middleware._is_token_cached_and_valid(token)
        
        # Assert
        expected = {"user_id": 456, "email": "cached@example.com"}
        assert result == expected
        mock_redis.get.assert_called_once_with(f"jwt_cache:{token}")

    @pytest.mark.asyncio
    async def test_is_token_cached_and_valid_handles_json_error(self, auth_middleware, mock_redis):
        """Test that invalid JSON in cache returns None"""
        # Arrange
        token = "token_with_bad_cache"
        mock_redis.get.return_value = "invalid_json_data"
        mock_redis.delete = AsyncMock()
        
        # Act
        result = await auth_middleware._is_token_cached_and_valid(token)
        
        # Assert
        assert result is None
        # Verify bad cache entry was deleted
        mock_redis.delete.assert_called_once_with(f"jwt_cache:{token}")

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_true(self, auth_middleware, mock_redis):
        """Test blacklisted token detection returns True"""
        # Arrange
        token = "blacklisted_token"
        mock_redis.exists.return_value = True
        
        # Act
        result = await auth_middleware._is_token_blacklisted(token)
        
        # Assert
        assert result is True
        mock_redis.exists.assert_called_once_with(f"jwt_blacklist:{token}")

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false(self, auth_middleware, mock_redis):
        """Test non-blacklisted token detection returns False"""
        # Arrange
        token = "valid_token"
        mock_redis.exists.return_value = False
        
        # Act
        result = await auth_middleware._is_token_blacklisted(token)
        
        # Assert
        assert result is False
        mock_redis.exists.assert_called_once_with(f"jwt_blacklist:{token}")

    @pytest.mark.asyncio
    async def test_cache_token_success(self, auth_middleware, mock_redis):
        """Test successful token caching"""
        # Arrange
        token = "new_token"
        payload = {"user_id": 789, "email": "new@example.com"}
        mock_redis.set.return_value = True
        
        # Act
        await auth_middleware._cache_token(token, payload)
        
        # Assert
        expected_key = f"jwt_cache:{token}"
        expected_value = '{"user_id": 789, "email": "new@example.com"}'
        mock_redis.set.assert_called_once_with(expected_key, expected_value, ex=1800)

    @pytest.mark.asyncio
    async def test_blacklist_token_success(self, auth_middleware, mock_redis):
        """Test successful token blacklisting"""
        # Arrange
        token = "token_to_blacklist"
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        
        # Act
        await auth_middleware.blacklist_token(token)
        
        # Assert
        # Verify token was blacklisted
        blacklist_key = f"jwt_blacklist:{token}"
        mock_redis.set.assert_called_with(blacklist_key, "1", ex=86400)  # 24 hours
        
        # Verify token was removed from cache
        cache_key = f"jwt_cache:{token}"
        mock_redis.delete.assert_called_with(cache_key)

    @pytest.mark.asyncio
    async def test_redis_connection_error_fallback(self, auth_middleware):
        """Test fallback behavior when Redis is unavailable"""
        # Arrange
        token = "test_token"
        payload = {"user_id": 123, "email": "test@example.com"}
        
        # Mock Redis to raise connection error
        mock_redis_error = AsyncMock()
        mock_redis_error.get.side_effect = Exception("Redis connection failed")
        auth_middleware.redis = mock_redis_error
        
        with patch.object(jwt_handler, 'verify_token', return_value=payload):
            # Act
            result = await auth_middleware._validate_token(token)
            
            # Assert
            assert result == payload
            jwt_handler.verify_token.assert_called_once_with(token)

    def test_no_auth0_references(self):
        """Test that Auth0 references have been completely removed"""
        import backend.auth.middleware as middleware_module
        import inspect
        
        # Get the source code of the middleware module
        source = inspect.getsource(middleware_module)
        
        # Assert no Auth0 references exist
        auth0_terms = ['auth0', 'Auth0', 'AUTH0', 'auth0_verifier']
        for term in auth0_terms:
            assert term not in source, f"Found Auth0 reference: {term}"

    @pytest.mark.asyncio
    async def test_validate_token_no_auth0_fallback(self, auth_middleware, mock_redis):
        """Test that there's no Auth0 fallback in token validation"""
        # Arrange
        token = "test_token"
        
        mock_redis.get.return_value = None  # Cache miss
        mock_redis.exists.return_value = False  # Not blacklisted
        
        with patch.object(jwt_handler, 'verify_token', side_effect=Exception("JWT validation failed")):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await auth_middleware._validate_token(token)
            
            # Should fail with JWT error, not try Auth0
            assert "JWT validation failed" in str(exc_info.value.detail)
            assert exc_info.value.status_code == 401


class TestAuthMiddlewareRedisIntegration:
    """Test Redis integration specifically"""

    @pytest.mark.asyncio
    async def test_redis_cache_key_format_consistency(self, auth_middleware, mock_redis):
        """Test that Redis cache keys follow consistent format"""
        token = "test_token_123"
        payload = {"user_id": 1}
        
        mock_redis.get.return_value = None
        mock_redis.exists.return_value = False
        mock_redis.set.return_value = True
        
        with patch.object(jwt_handler, 'verify_token', return_value=payload):
            await auth_middleware._validate_token(token)
            
            # Check cache key format
            cache_calls = [call for call in mock_redis.set.call_args_list if 'jwt_cache:' in str(call)]
            assert len(cache_calls) == 1
            
            cache_key = cache_calls[0][0][0]
            assert cache_key == f"jwt_cache:{token}"

    @pytest.mark.asyncio
    async def test_redis_blacklist_key_format_consistency(self, auth_middleware, mock_redis):
        """Test that Redis blacklist keys follow consistent format"""
        token = "blacklist_test_token"
        
        await auth_middleware.blacklist_token(token)
        
        # Check blacklist key format
        blacklist_calls = [call for call in mock_redis.set.call_args_list if 'jwt_blacklist:' in str(call)]
        assert len(blacklist_calls) == 1
        
        blacklist_key = blacklist_calls[0][0][0]
        assert blacklist_key == f"jwt_blacklist:{token}"

    @pytest.mark.asyncio 
    async def test_cache_expiration_times(self, auth_middleware, mock_redis):
        """Test that cache expiration times are appropriate"""
        token = "expiration_test_token"
        payload = {"user_id": 1}
        
        await auth_middleware._cache_token(token, payload)
        
        # Check cache expiration (30 minutes = 1800 seconds)
        cache_call = mock_redis.set.call_args
        assert cache_call[1]['ex'] == 1800

        # Test blacklist expiration
        mock_redis.reset_mock()
        await auth_middleware.blacklist_token(token)
        
        blacklist_call = [call for call in mock_redis.set.call_args_list if 'jwt_blacklist:' in str(call)][0]
        assert blacklist_call[1]['ex'] == 86400  # 24 hours


class TestAuthMiddlewareErrorHandling:
    """Test error handling in authentication middleware"""

    @pytest.mark.asyncio
    async def test_malformed_token_handling(self, auth_middleware, mock_redis):
        """Test handling of malformed JWT tokens"""
        malformed_tokens = [
            "",
            None,
            "not.a.jwt",
            "too.few.parts",
            "header.payload.signature.extra"
        ]
        
        for token in malformed_tokens:
            mock_redis.reset_mock()
            mock_redis.get.return_value = None
            mock_redis.exists.return_value = False
            
            with patch.object(jwt_handler, 'verify_token', side_effect=Exception("Malformed token")):
                with pytest.raises(HTTPException):
                    await auth_middleware._validate_token(token)

    @pytest.mark.asyncio
    async def test_concurrent_token_validation(self, auth_middleware, mock_redis):
        """Test concurrent token validation doesn't cause issues"""
        import asyncio
        
        token = "concurrent_test_token"
        payload = {"user_id": 1}
        
        mock_redis.get.return_value = None
        mock_redis.exists.return_value = False
        mock_redis.set.return_value = True
        
        with patch.object(jwt_handler, 'verify_token', return_value=payload):
            # Run multiple validations concurrently
            tasks = [auth_middleware._validate_token(token) for _ in range(10)]
            results = await asyncio.gather(*tasks)
            
            # All should return the same payload
            assert all(result == payload for result in results)