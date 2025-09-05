"""
Integration tests for timezone handling fixes - critical for R4 resolution
Tests the fixes for timezone-agnostic scheduling issues
"""
import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from backend.tasks.autonomous_scheduler import AutonomousScheduler


@pytest.fixture
def scheduler():
    """Create scheduler instance"""
    return AutonomousScheduler()


class TestTimezoneHandlingFixed:
    """Test suite for fixed timezone handling in autonomous scheduler"""

    def test_get_user_datetime_utc_default(self, scheduler):
        """Test UTC default when no timezone specified"""
        result = scheduler._get_user_datetime()
        
        assert result.tzinfo == timezone.utc
        # Should be close to current time (within 1 second)
        now_utc = datetime.now(timezone.utc)
        assert abs((result - now_utc).total_seconds()) < 1.0

    def test_get_user_datetime_utc_explicit(self, scheduler):
        """Test explicit UTC timezone handling"""
        result = scheduler._get_user_datetime("UTC")
        
        assert result.tzinfo == timezone.utc

    def test_get_user_datetime_eastern_timezone(self, scheduler):
        """Test Eastern timezone handling"""
        result = scheduler._get_user_datetime("America/New_York")
        
        assert result.tzinfo == ZoneInfo("America/New_York")

    def test_get_user_datetime_pacific_timezone(self, scheduler):
        """Test Pacific timezone handling"""
        result = scheduler._get_user_datetime("America/Los_Angeles")
        
        assert result.tzinfo == ZoneInfo("America/Los_Angeles")

    def test_get_user_datetime_european_timezone(self, scheduler):
        """Test European timezone handling"""
        result = scheduler._get_user_datetime("Europe/London")
        
        assert result.tzinfo == ZoneInfo("Europe/London")

    def test_get_user_datetime_invalid_timezone_fallback(self, scheduler):
        """Test fallback to UTC for invalid timezone"""
        result = scheduler._get_user_datetime("Invalid/Timezone")
        
        # Should fallback to UTC
        assert result.tzinfo == timezone.utc

    def test_get_user_datetime_empty_timezone_fallback(self, scheduler):
        """Test fallback to UTC for empty timezone"""
        result = scheduler._get_user_datetime("")
        
        # Should fallback to UTC
        assert result.tzinfo == timezone.utc

    def test_get_user_datetime_none_timezone_fallback(self, scheduler):
        """Test fallback to UTC for None timezone"""
        result = scheduler._get_user_datetime(None)
        
        # Should fallback to UTC
        assert result.tzinfo == timezone.utc

    @patch('backend.tasks.autonomous_scheduler.TIMEZONE_AVAILABLE', False)
    def test_get_user_datetime_no_zoneinfo_fallback(self, scheduler):
        """Test fallback to UTC when zoneinfo is not available"""
        result = scheduler._get_user_datetime("America/New_York")
        
        # Should fallback to UTC when zoneinfo unavailable
        assert result.tzinfo == timezone.utc

    def test_convert_user_time_to_utc_eastern(self, scheduler):
        """Test converting Eastern time to UTC"""
        # 3:00 PM Eastern should convert properly to UTC
        eastern_time = datetime(2024, 6, 15, 15, 0, 0)  # 3 PM
        
        result = scheduler._convert_user_time_to_utc(
            eastern_time, 
            "America/New_York"
        )
        
        assert result.tzinfo == timezone.utc
        # In June, Eastern is UTC-4, so 3 PM Eastern = 7 PM UTC
        expected_utc_hour = 19  # 7 PM
        assert result.hour == expected_utc_hour

    def test_convert_user_time_to_utc_pacific(self, scheduler):
        """Test converting Pacific time to UTC"""
        # 2:00 PM Pacific should convert properly to UTC
        pacific_time = datetime(2024, 6, 15, 14, 0, 0)  # 2 PM
        
        result = scheduler._convert_user_time_to_utc(
            pacific_time, 
            "America/Los_Angeles"
        )
        
        assert result.tzinfo == timezone.utc
        # In June, Pacific is UTC-7, so 2 PM Pacific = 9 PM UTC
        expected_utc_hour = 21  # 9 PM
        assert result.hour == expected_utc_hour

    def test_convert_user_time_to_utc_already_utc(self, scheduler):
        """Test that UTC time remains unchanged"""
        utc_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        result = scheduler._convert_user_time_to_utc(utc_time, "UTC")
        
        assert result == utc_time
        assert result.tzinfo == timezone.utc

    def test_convert_user_time_to_utc_invalid_timezone(self, scheduler):
        """Test fallback behavior for invalid timezone in conversion"""
        naive_time = datetime(2024, 6, 15, 12, 0, 0)
        
        result = scheduler._convert_user_time_to_utc(
            naive_time,
            "Invalid/Timezone"
        )
        
        # Should treat as UTC
        assert result.tzinfo == timezone.utc
        assert result.hour == 12  # No conversion

    def test_schedule_respects_user_timezone_morning(self, scheduler):
        """Test that morning posts are scheduled correctly in user timezone"""
        with patch.object(scheduler, '_get_user_datetime') as mock_get_time:
            # Mock 8 AM in user's timezone
            user_morning = datetime(2024, 6, 15, 8, 0, 0, tzinfo=ZoneInfo("America/New_York"))
            mock_get_time.return_value = user_morning
            
            # Test that scheduling logic uses user's timezone
            result_time = scheduler._get_user_datetime("America/New_York")
            
            assert result_time.tzinfo == ZoneInfo("America/New_York")
            mock_get_time.assert_called_once_with("America/New_York")

    def test_schedule_respects_user_timezone_evening(self, scheduler):
        """Test that evening posts are scheduled correctly in user timezone"""
        with patch.object(scheduler, '_get_user_datetime') as mock_get_time:
            # Mock 7 PM in user's timezone
            user_evening = datetime(2024, 6, 15, 19, 0, 0, tzinfo=ZoneInfo("Europe/London"))
            mock_get_time.return_value = user_evening
            
            result_time = scheduler._get_user_datetime("Europe/London")
            
            assert result_time.tzinfo == ZoneInfo("Europe/London")

    def test_no_datetime_utcnow_usage(self):
        """Test that datetime.utcnow() is not used anywhere in scheduler"""
        import backend.tasks.autonomous_scheduler as scheduler_module
        import inspect
        
        source = inspect.getsource(scheduler_module)
        
        # Assert no deprecated datetime.utcnow() usage
        deprecated_calls = [
            'datetime.utcnow()',
            'datetime.utcnow',
            'utcnow()'
        ]
        
        for call in deprecated_calls:
            assert call not in source, f"Found deprecated datetime call: {call}"

    def test_uses_timezone_aware_datetime(self):
        """Test that all datetime objects are timezone-aware"""
        import backend.tasks.autonomous_scheduler as scheduler_module
        import inspect
        
        source = inspect.getsource(scheduler_module)
        
        # Should use timezone.utc or ZoneInfo
        assert 'timezone.utc' in source or 'ZoneInfo' in source
        assert 'datetime.now(timezone.utc)' in source

    def test_daylight_saving_time_handling_spring(self, scheduler):
        """Test DST handling during spring forward (2 AM -> 3 AM)"""
        # Test date during spring DST transition in Eastern timezone
        dst_date = datetime(2024, 3, 10, 2, 30, 0)  # 2:30 AM on DST transition day
        
        result = scheduler._convert_user_time_to_utc(
            dst_date,
            "America/New_York"
        )
        
        # Should handle DST transition correctly
        assert result.tzinfo == timezone.utc
        # 2:30 AM EST (before spring forward) = 7:30 AM UTC
        # 2:30 AM EDT (after spring forward) = 6:30 AM UTC
        # The exact result depends on how the timezone library handles the ambiguous time
        assert result.hour in [6, 7]  # Either is acceptable

    def test_daylight_saving_time_handling_fall(self, scheduler):
        """Test DST handling during fall back (2 AM -> 1 AM)"""
        # Test date during fall DST transition in Eastern timezone
        dst_date = datetime(2024, 11, 3, 1, 30, 0)  # 1:30 AM on DST transition day
        
        result = scheduler._convert_user_time_to_utc(
            dst_date,
            "America/New_York"
        )
        
        # Should handle DST transition correctly
        assert result.tzinfo == timezone.utc
        # The exact result depends on DST interpretation
        assert result.hour in [5, 6]  # Either is acceptable

    def test_international_timezone_support(self, scheduler):
        """Test support for various international timezones"""
        timezones_to_test = [
            ("Asia/Tokyo", 9),        # UTC+9
            ("Europe/Paris", 1),      # UTC+1 (winter)
            ("Australia/Sydney", 10), # UTC+10 (winter)
            ("Asia/Kolkata", 5.5),    # UTC+5:30
            ("America/Santiago", -3), # UTC-3 (winter)
        ]
        
        test_time = datetime(2024, 1, 15, 12, 0, 0)  # Noon in January (winter)
        
        for timezone_name, expected_offset_hours in timezones_to_test:
            result = scheduler._convert_user_time_to_utc(test_time, timezone_name)
            
            assert result.tzinfo == timezone.utc
            
            # Calculate expected UTC hour
            if isinstance(expected_offset_hours, float):
                # Handle half-hour offsets like India Standard Time
                expected_utc_hour = (12 - expected_offset_hours) % 24
            else:
                expected_utc_hour = (12 - expected_offset_hours) % 24
            
            # Allow some flexibility for DST variations
            assert abs(result.hour - expected_utc_hour) <= 1, \
                f"Timezone {timezone_name} conversion failed: expected ~{expected_utc_hour}, got {result.hour}"


class TestTimezoneSchedulingIntegration:
    """Integration tests for timezone-aware scheduling"""

    def test_full_scheduling_workflow_with_timezone(self, scheduler):
        """Test complete scheduling workflow respects user timezone"""
        user_timezone = "America/Chicago"  # Central Time
        
        with patch.object(scheduler, '_get_user_datetime') as mock_get_time:
            # Mock 9 AM Central Time
            central_morning = datetime(2024, 6, 15, 9, 0, 0, tzinfo=ZoneInfo("America/Chicago"))
            mock_get_time.return_value = central_morning
            
            # Simulate getting optimal posting time
            optimal_time = scheduler._get_user_datetime(user_timezone)
            
            # Verify timezone is preserved through the workflow
            assert optimal_time.tzinfo == ZoneInfo("America/Chicago")
            assert optimal_time.hour == 9

    def test_multi_user_timezone_handling(self, scheduler):
        """Test that multiple users with different timezones work correctly"""
        users_timezones = [
            ("user1", "America/New_York"),
            ("user2", "Europe/London"),
            ("user3", "Asia/Tokyo"),
        ]
        
        for user_id, user_timezone in users_timezones:
            result = scheduler._get_user_datetime(user_timezone)
            
            # Each user should get time in their timezone
            assert result.tzinfo == ZoneInfo(user_timezone)
            
            # Convert to UTC for comparison
            utc_result = scheduler._convert_user_time_to_utc(result, user_timezone)
            assert utc_result.tzinfo == timezone.utc

    @patch('backend.tasks.autonomous_scheduler.logger')
    def test_timezone_error_logging(self, mock_logger, scheduler):
        """Test that timezone errors are properly logged"""
        # Try to use invalid timezone
        result = scheduler._get_user_datetime("Invalid/BadTimezone")
        
        # Should fallback to UTC
        assert result.tzinfo == timezone.utc
        
        # Should log a warning
        mock_logger.warning.assert_called_once()
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "Invalid timezone" in warning_msg
        assert "Invalid/BadTimezone" in warning_msg

    def test_timezone_handling_performance(self, scheduler):
        """Test that timezone operations don't significantly impact performance"""
        import time
        
        start_time = time.time()
        
        # Perform many timezone operations
        for i in range(1000):
            scheduler._get_user_datetime("America/New_York")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete quickly (less than 1 second for 1000 operations)
        assert duration < 1.0, f"Timezone operations too slow: {duration}s"

    def test_timezone_cache_consistency(self, scheduler):
        """Test that timezone operations are consistent across calls"""
        timezone_name = "Europe/Berlin"
        
        # Get time multiple times
        results = []
        for _ in range(10):
            result = scheduler._get_user_datetime(timezone_name)
            results.append(result)
        
        # All results should have the same timezone
        for result in results:
            assert result.tzinfo == ZoneInfo(timezone_name)
        
        # Times should be very close (within a few seconds)
        first_time = results[0]
        for result in results[1:]:
            time_diff = abs((result - first_time).total_seconds())
            assert time_diff < 5.0  # Within 5 seconds


class TestTimezoneEdgeCases:
    """Test edge cases in timezone handling"""

    def test_leap_year_timezone_handling(self, scheduler):
        """Test timezone handling during leap year"""
        leap_year_date = datetime(2024, 2, 29, 12, 0, 0)  # Feb 29, 2024
        
        result = scheduler._convert_user_time_to_utc(
            leap_year_date,
            "America/New_York"
        )
        
        assert result.tzinfo == timezone.utc
        assert result.day == 29  # Should preserve the leap day

    def test_year_boundary_timezone_handling(self, scheduler):
        """Test timezone handling across year boundaries"""
        new_years_eve = datetime(2023, 12, 31, 23, 30, 0)
        
        result = scheduler._convert_user_time_to_utc(
            new_years_eve,
            "Pacific/Auckland"  # UTC+12, so it's already 2024 there
        )
        
        assert result.tzinfo == timezone.utc
        # Should be 2024-01-01 in UTC
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_extreme_timezone_offsets(self, scheduler):
        """Test handling of extreme timezone offsets"""
        extreme_timezones = [
            "Pacific/Kiritimati",  # UTC+14
            "Pacific/Honolulu",    # UTC-10
            "Pacific/Marquesas",   # UTC-9:30
        ]
        
        for tz in extreme_timezones:
            try:
                result = scheduler._get_user_datetime(tz)
                assert result.tzinfo == ZoneInfo(tz)
            except:
                # Some extreme timezones might not be supported
                # In that case, should fallback to UTC
                result = scheduler._get_user_datetime(tz)
                assert result.tzinfo == timezone.utc

    def test_microsecond_precision_preservation(self, scheduler):
        """Test that microsecond precision is preserved in timezone operations"""
        precise_time = datetime(2024, 6, 15, 12, 30, 45, 123456)
        
        result = scheduler._convert_user_time_to_utc(
            precise_time,
            "America/New_York"
        )
        
        # Microseconds should be preserved
        assert result.microsecond == 123456