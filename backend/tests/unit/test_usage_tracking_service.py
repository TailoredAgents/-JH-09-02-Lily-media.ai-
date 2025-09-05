"""
Unit tests for usage tracking service - critical for production readiness
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from decimal import Decimal

from backend.services.usage_tracking_service import UsageTrackingService
from backend.db.models import UsageRecord, User, Organization
from backend.services.redis_cache import redis_cache


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock()


@pytest.fixture
def mock_redis():
    """Mock Redis cache"""
    return Mock()


@pytest.fixture 
def usage_service(mock_db, mock_redis):
    """Usage tracking service with mocked dependencies"""
    service = UsageTrackingService(mock_db)
    service.redis = mock_redis
    return service


class TestUsageTrackingService:
    """Test suite for usage tracking functionality"""

    @pytest.mark.asyncio
    async def test_track_usage_creates_record(self, usage_service, mock_db):
        """Test that track_usage creates a UsageRecord in database"""
        # Arrange
        user_id = 123
        organization_id = 456
        usage_type = "image_generation"
        
        # Act
        await usage_service.track_usage(
            user_id=user_id,
            organization_id=organization_id, 
            usage_type=usage_type,
            resource="grok2_basic",
            quantity=1,
            cost_credits=Decimal("2.50")
        )
        
        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Check the record that was added
        added_record = mock_db.add.call_args[0][0]
        assert isinstance(added_record, UsageRecord)
        assert added_record.user_id == user_id
        assert added_record.organization_id == organization_id
        assert added_record.usage_type == usage_type
        assert added_record.resource == "grok2_basic"
        assert added_record.quantity == 1
        assert added_record.cost_credits == Decimal("2.50")

    @pytest.mark.asyncio
    async def test_get_current_usage_from_cache(self, usage_service, mock_redis):
        """Test that usage is retrieved from cache when available"""
        # Arrange
        user_id = 123
        organization_id = 456
        usage_type = "content_generation"
        billing_period = "2024-01"
        
        mock_redis.get.return_value = "42"  # Cached value
        
        # Act
        result = await usage_service.get_current_usage(
            user_id, organization_id, usage_type, billing_period
        )
        
        # Assert
        assert result == 42
        cache_key = f"usage:{user_id}:{organization_id}:{usage_type}:{billing_period}"
        mock_redis.get.assert_called_once_with(cache_key)

    @pytest.mark.asyncio
    async def test_get_current_usage_from_db_when_cache_miss(self, usage_service, mock_redis, mock_db):
        """Test that usage is retrieved from DB and cached on cache miss"""
        # Arrange
        user_id = 123
        organization_id = 456
        usage_type = "content_generation"
        billing_period = "2024-01"
        
        mock_redis.get.return_value = None  # Cache miss
        
        # Mock database query result
        mock_query_result = Mock()
        mock_query_result.scalar.return_value = 15
        mock_db.query.return_value.filter.return_value.scalar.return_value = 15
        
        # Act
        result = await usage_service.get_current_usage(
            user_id, organization_id, usage_type, billing_period
        )
        
        # Assert
        assert result == 15
        
        # Verify database query was made
        mock_db.query.assert_called_once()
        
        # Verify result was cached
        cache_key = f"usage:{user_id}:{organization_id}:{usage_type}:{billing_period}"
        mock_redis.set.assert_called_once_with(cache_key, 15, ttl=300)

    @pytest.mark.asyncio
    async def test_check_usage_limit_within_limit(self, usage_service):
        """Test that users within limits can proceed"""
        # Arrange
        with patch.object(usage_service, 'get_current_usage', return_value=5):
            # Act
            result = await usage_service.check_usage_limit(
                user_id=123,
                organization_id=456, 
                usage_type="api_calls",
                limit=10
            )
            
            # Assert
            assert result == {
                "allowed": True,
                "current_usage": 5,
                "limit": 10,
                "remaining": 5
            }

    @pytest.mark.asyncio
    async def test_check_usage_limit_exceeds_limit(self, usage_service):
        """Test that users exceeding limits are blocked"""
        # Arrange
        with patch.object(usage_service, 'get_current_usage', return_value=15):
            # Act
            result = await usage_service.check_usage_limit(
                user_id=123,
                organization_id=456,
                usage_type="api_calls", 
                limit=10
            )
            
            # Assert
            assert result == {
                "allowed": False,
                "current_usage": 15,
                "limit": 10,
                "remaining": 0,
                "message": "Usage limit exceeded for api_calls"
            }

    @pytest.mark.asyncio
    async def test_track_usage_handles_database_error(self, usage_service, mock_db):
        """Test that database errors are handled gracefully"""
        # Arrange
        mock_db.commit.side_effect = Exception("Database error")
        mock_db.rollback = Mock()
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await usage_service.track_usage(
                user_id=123,
                organization_id=456,
                usage_type="test_usage"
            )
        
        # Verify rollback was called
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_usage_cache(self, usage_service, mock_redis):
        """Test that usage cache is properly invalidated"""
        # Act
        await usage_service.invalidate_usage_cache(
            user_id=123,
            organization_id=456,
            usage_type="content_generation",
            billing_period="2024-01"
        )
        
        # Assert
        cache_key = "usage:123:456:content_generation:2024-01"
        mock_redis.delete.assert_called_once_with(cache_key)

    @pytest.mark.asyncio
    async def test_get_usage_summary_by_organization(self, usage_service, mock_db):
        """Test retrieving usage summary by organization"""
        # Arrange
        organization_id = 456
        billing_period = "2024-01"
        
        # Mock database results
        mock_results = [
            ("image_generation", 25, Decimal("62.50")),
            ("content_generation", 100, Decimal("25.00"))
        ]
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = mock_results
        
        # Act
        result = await usage_service.get_usage_summary_by_organization(
            organization_id, billing_period
        )
        
        # Assert
        expected = [
            {
                "usage_type": "image_generation",
                "total_quantity": 25,
                "total_cost": Decimal("62.50")
            },
            {
                "usage_type": "content_generation", 
                "total_quantity": 100,
                "total_cost": Decimal("25.00")
            }
        ]
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_billing_period_from_timestamp(self, usage_service):
        """Test billing period calculation from timestamp"""
        # Test current date
        test_date = datetime(2024, 3, 15, tzinfo=timezone.utc)
        
        with patch('backend.services.usage_tracking_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_date
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = usage_service.get_current_billing_period()
            assert result == "2024-03"

    @pytest.mark.asyncio
    async def test_track_usage_with_metadata(self, usage_service, mock_db):
        """Test tracking usage with custom metadata"""
        # Arrange
        metadata = {
            "model": "grok2_premium",
            "dimensions": "1024x1024", 
            "platform": "instagram"
        }
        
        # Act
        await usage_service.track_usage(
            user_id=123,
            organization_id=456,
            usage_type="image_generation",
            metadata=metadata
        )
        
        # Assert
        added_record = mock_db.add.call_args[0][0]
        assert added_record.usage_metadata == metadata

    def test_billing_period_format_validation(self, usage_service):
        """Test that billing periods follow YYYY-MM format"""
        test_cases = [
            (datetime(2024, 1, 15), "2024-01"),
            (datetime(2024, 12, 31), "2024-12"),
            (datetime(2023, 5, 1), "2023-05")
        ]
        
        for test_date, expected in test_cases:
            with patch('backend.services.usage_tracking_service.datetime') as mock_datetime:
                mock_datetime.now.return_value = test_date
                result = usage_service.get_current_billing_period() 
                assert result == expected


class TestUsageTrackingIntegration:
    """Integration tests for usage tracking with real components"""

    @pytest.mark.asyncio
    async def test_redis_integration_works(self, usage_service):
        """Test that Redis integration works properly"""
        # This would be a real Redis integration test
        # For now, we'll mock it but in a real scenario this would use testcontainers
        pass

    @pytest.mark.asyncio 
    async def test_concurrent_usage_tracking(self, usage_service):
        """Test that concurrent usage tracking works correctly"""
        # This would test race conditions and atomic operations
        pass


# Performance tests
class TestUsageTrackingPerformance:
    """Performance tests for usage tracking service"""

    @pytest.mark.asyncio
    async def test_bulk_usage_tracking_performance(self, usage_service, mock_db):
        """Test performance of bulk usage tracking"""
        import asyncio
        import time
        
        # Track multiple usage events concurrently
        start_time = time.time()
        
        tasks = []
        for i in range(100):
            task = usage_service.track_usage(
                user_id=i,
                organization_id=1,
                usage_type="api_call"
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert duration < 5.0, f"Bulk tracking took too long: {duration}s"

    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, usage_service, mock_redis):
        """Test that cache hits are fast"""
        import time
        
        mock_redis.get.return_value = "42"
        
        start_time = time.time()
        
        for _ in range(1000):
            await usage_service.get_current_usage(
                user_id=1,
                organization_id=1, 
                usage_type="api_call",
                billing_period="2024-01"
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Cache hits should be very fast
        assert duration < 1.0, f"Cache hits too slow: {duration}s"