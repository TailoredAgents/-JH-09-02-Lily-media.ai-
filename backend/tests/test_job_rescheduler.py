"""
PW-WEATHER-ADD-001: Unit tests for Job Rescheduler

Tests for automatic job rescheduling based on weather conditions,
business hours validation, and integration with job service.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta, time
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal

from backend.services.job_rescheduler import (
    JobRescheduler,
    RescheduleResult,
    BusinessHours,
    get_job_rescheduler,
    set_job_rescheduler
)
from backend.services.weather_service import WeatherForecast, WeatherCondition, MockWeatherProvider
from backend.services.settings_resolver import WeatherSettings, BadWeatherThreshold
from backend.db.models import Job


class TestBusinessHours:
    """Unit tests for BusinessHours data class"""
    
    def test_from_string_valid_hours(self):
        """Test creating BusinessHours from valid time strings"""
        hours = BusinessHours.from_string("08:00", "17:00")
        
        assert hours.start_time == time(8, 0)
        assert hours.end_time == time(17, 0)
        assert hours.is_closed is False
    
    def test_from_string_closed(self):
        """Test creating BusinessHours for closed day"""
        hours = BusinessHours.from_string("closed", "closed")
        
        assert hours.start_time is None
        assert hours.end_time is None
        assert hours.is_closed is True
    
    def test_from_string_invalid_format_defaults(self):
        """Test BusinessHours defaults to 8-5 for invalid format"""
        hours = BusinessHours.from_string("invalid", "format")
        
        assert hours.start_time == time(8, 0)
        assert hours.end_time == time(17, 0)
        assert hours.is_closed is False


class TestRescheduleResult:
    """Unit tests for RescheduleResult data class"""
    
    def test_reschedule_result_creation(self):
        """Test creating RescheduleResult with all fields"""
        original_date = datetime.now(timezone.utc)
        new_date = original_date + timedelta(days=1)
        
        result = RescheduleResult(
            job_id="job-123",
            original_date=original_date,
            new_date=new_date,
            reschedule_reason="High wind speed",
            success=True
        )
        
        assert result.job_id == "job-123"
        assert result.original_date == original_date
        assert result.new_date == new_date
        assert result.reschedule_reason == "High wind speed"
        assert result.success is True
        assert result.error_message is None


class TestJobRescheduler:
    """Unit tests for JobRescheduler"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_weather_service = Mock()
        self.mock_job_service = Mock()
        self.rescheduler = JobRescheduler(
            weather_service=self.mock_weather_service,
            job_service=self.mock_job_service
        )
        self.mock_db = Mock()
    
    def test_get_upcoming_jobs(self):
        """Test retrieval of upcoming jobs within lookahead window"""
        org_id = "org-123"
        lookahead_days = 3
        
        # Mock scheduled jobs
        now = datetime.now(timezone.utc)
        jobs = [
            Mock(id="job-1", scheduled_for=now + timedelta(days=1)),
            Mock(id="job-2", scheduled_for=now + timedelta(days=2))
        ]
        
        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = jobs
        self.mock_db.query.return_value = mock_query
        
        result = self.rescheduler._get_upcoming_jobs(org_id, lookahead_days, self.mock_db)
        
        assert len(result) == 2
        assert result == jobs
        
        # Verify query was called correctly
        self.mock_db.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.order_by.assert_called_once()
    
    def test_geocode_address_returns_default(self):
        """Test address geocoding returns Atlanta coordinates"""
        latitude, longitude = self.rescheduler._geocode_address("123 Main St, Atlanta, GA")
        
        assert latitude == 33.7490
        assert longitude == -84.3880
    
    def test_find_business_hour_slot_open_day(self):
        """Test finding slot within business hours on open day"""
        weather_settings = WeatherSettings(
            business_hours={
                "monday": {"start": "08:00", "end": "17:00"}
            },
            buffer_minutes=60
        )
        
        # Monday date
        test_date = datetime(2024, 1, 1, tzinfo=timezone.utc)  # This is a Monday
        
        slot = self.rescheduler._find_business_hour_slot(
            date=test_date,
            duration_minutes=120,
            weather_settings=weather_settings
        )
        
        # Should return 9:00 AM (8:00 + 60min buffer)
        expected = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
        assert slot == expected
    
    def test_find_business_hour_slot_closed_day(self):
        """Test finding slot on closed day returns None"""
        weather_settings = WeatherSettings(
            business_hours={
                "sunday": {"start": "closed", "end": "closed"}
            }
        )
        
        # Sunday date
        test_date = datetime(2024, 1, 7, tzinfo=timezone.utc)  # This is a Sunday
        
        slot = self.rescheduler._find_business_hour_slot(
            date=test_date,
            duration_minutes=120,
            weather_settings=weather_settings
        )
        
        assert slot is None
    
    def test_find_business_hour_slot_too_long_job(self):
        """Test finding slot for job that's too long for business hours"""
        weather_settings = WeatherSettings(
            business_hours={
                "monday": {"start": "08:00", "end": "17:00"}  # 9 hour window
            },
            buffer_minutes=60
        )
        
        test_date = datetime(2024, 1, 1, tzinfo=timezone.utc)  # Monday
        
        slot = self.rescheduler._find_business_hour_slot(
            date=test_date,
            duration_minutes=600,  # 10 hours - too long!
            weather_settings=weather_settings
        )
        
        assert slot is None
    
    def test_find_next_safe_slot(self):
        """Test finding next safe weather slot"""
        threshold = BadWeatherThreshold(
            rain_probability=50.0,
            wind_speed_mph=20.0,
            temp_low_f=35.0
        )
        
        weather_settings = WeatherSettings(
            bad_weather_threshold=threshold,
            business_hours={
                "monday": {"start": "08:00", "end": "17:00"},
                "tuesday": {"start": "08:00", "end": "17:00"}
            },
            buffer_minutes=30
        )
        
        # Bad weather today, good weather tomorrow
        today = datetime(2024, 1, 1, tzinfo=timezone.utc)  # Monday
        tomorrow = today + timedelta(days=1)  # Tuesday
        
        forecasts = [
            WeatherForecast(
                date=today,
                temperature_high_f=75.0,
                temperature_low_f=30.0,  # Too cold
                rain_probability=20.0,
                wind_speed_mph=15.0,
                condition=WeatherCondition.CLEAR
            ),
            WeatherForecast(
                date=tomorrow,
                temperature_high_f=75.0,
                temperature_low_f=45.0,  # Good temp
                rain_probability=20.0,
                wind_speed_mph=15.0,
                condition=WeatherCondition.CLEAR
            )
        ]
        
        safe_slot = self.rescheduler._find_next_safe_slot(
            forecasts=forecasts,
            weather_settings=weather_settings,
            current_job_duration=120
        )
        
        # Should find slot on Tuesday at 8:30 AM (8:00 + 30min buffer)
        expected = datetime(2024, 1, 2, 8, 30, tzinfo=timezone.utc)
        assert safe_slot == expected
    
    def test_generate_reschedule_reason(self):
        """Test generation of human-readable reschedule reason"""
        threshold = BadWeatherThreshold(
            rain_probability=50.0,
            wind_speed_mph=20.0,
            temp_low_f=40.0
        )
        
        forecast = WeatherForecast(
            date=datetime.now(timezone.utc),
            temperature_high_f=75.0,
            temperature_low_f=30.0,  # Below threshold
            rain_probability=80.0,  # Above threshold
            wind_speed_mph=25.0,  # Above threshold
            condition=WeatherCondition.CLOUDY
        )
        
        reason = self.rescheduler._generate_reschedule_reason(forecast, threshold)
        
        assert "Automatically rescheduled due to weather" in reason
        assert "80.0% chance of rain" in reason
        assert "25.0 mph winds" in reason
        assert "Low temperature (30.0°F)" in reason
    
    @pytest.mark.asyncio
    async def test_evaluate_and_reschedule_job_no_scheduled_time(self):
        """Test evaluation skips jobs without scheduled time"""
        job = Mock(scheduled_for=None)
        weather_settings = Mock()
        
        result = await self.rescheduler._evaluate_and_reschedule_job(
            job, weather_settings, self.mock_db, 1
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_evaluate_and_reschedule_job_good_weather(self):
        """Test evaluation skips rescheduling for good weather"""
        job = Mock()
        job.scheduled_for = datetime.now(timezone.utc) + timedelta(days=1)
        job.address = "123 Test St"
        job.duration_minutes = 120
        
        # Mock good weather forecast
        good_forecast = WeatherForecast(
            date=job.scheduled_for,
            temperature_high_f=75.0,
            temperature_low_f=45.0,
            rain_probability=20.0,
            wind_speed_mph=15.0,
            condition=WeatherCondition.CLEAR
        )
        good_forecast.is_bad_weather = Mock(return_value=False)
        
        self.mock_weather_service.get_forecast = AsyncMock(return_value=[good_forecast])
        
        weather_settings = Mock()
        weather_settings.lookahead_days = 3
        weather_settings.bad_weather_threshold = Mock()
        
        result = await self.rescheduler._evaluate_and_reschedule_job(
            job, weather_settings, self.mock_db, 1
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_evaluate_and_reschedule_job_success(self):
        """Test successful job rescheduling due to bad weather"""
        job = Mock()
        job.id = "job-123"
        job.scheduled_for = datetime.now(timezone.utc) + timedelta(days=1)
        job.address = "123 Test St"
        job.duration_minutes = 120
        job.organization_id = "org-456"
        
        # Mock bad weather forecast
        bad_forecast = WeatherForecast(
            date=job.scheduled_for,
            temperature_high_f=75.0,
            temperature_low_f=30.0,  # Bad weather
            rain_probability=80.0,
            wind_speed_mph=15.0,
            condition=WeatherCondition.CLOUDY
        )
        bad_forecast.is_bad_weather = Mock(return_value=True)
        bad_forecast.rain_probability = 80.0
        bad_forecast.wind_speed_mph = 15.0
        bad_forecast.temperature_low_f = 30.0
        bad_forecast.condition = WeatherCondition.CLOUDY
        
        # Mock good weather forecast for next day
        good_forecast = WeatherForecast(
            date=job.scheduled_for + timedelta(days=1),
            temperature_high_f=75.0,
            temperature_low_f=45.0,
            rain_probability=20.0,
            wind_speed_mph=15.0,
            condition=WeatherCondition.CLEAR
        )
        
        self.mock_weather_service.get_forecast = AsyncMock(return_value=[bad_forecast, good_forecast])
        
        weather_settings = Mock()
        weather_settings.lookahead_days = 3
        weather_settings.bad_weather_threshold = Mock()
        weather_settings.business_hours = {
            "tuesday": {"start": "08:00", "end": "17:00"}
        }
        weather_settings.buffer_minutes = 30
        
        # Mock successful rescheduling
        new_date = job.scheduled_for + timedelta(days=1)
        self.mock_job_service.reschedule_job.return_value = Mock()
        
        # Mock _find_next_safe_slot to return a specific date
        with patch.object(self.rescheduler, '_find_next_safe_slot', return_value=new_date):
            result = await self.rescheduler._evaluate_and_reschedule_job(
                job, weather_settings, self.mock_db, 1
            )
        
        assert result.success is True
        assert result.job_id == "job-123"
        assert result.new_date == new_date
        assert "Automatically rescheduled due to weather" in result.reschedule_reason
        
        # Verify job service was called
        self.mock_job_service.reschedule_job.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('backend.services.job_rescheduler.get_settings')
    async def test_run_rescheduling_check_disabled(self, mock_get_settings):
        """Test rescheduling check skips when auto-reschedule is disabled"""
        mock_get_settings.return_value = Mock(auto_reschedule=False)
        
        results = await self.rescheduler.run_rescheduling_check("org-123", self.mock_db, 1)
        
        assert results == []
    
    @pytest.mark.asyncio
    @patch('backend.services.job_rescheduler.get_settings')
    async def test_run_rescheduling_check_no_jobs(self, mock_get_settings):
        """Test rescheduling check with no upcoming jobs"""
        weather_settings = Mock()
        weather_settings.auto_reschedule = True
        weather_settings.lookahead_days = 3
        mock_get_settings.return_value = weather_settings
        
        # Mock empty job query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        self.mock_db.query.return_value = mock_query
        
        results = await self.rescheduler.run_rescheduling_check("org-123", self.mock_db, 1)
        
        assert results == []
    
    @pytest.mark.asyncio
    @patch('backend.services.job_rescheduler.get_settings')
    async def test_check_single_job_not_found(self, mock_get_settings):
        """Test single job check when job doesn't exist"""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = await self.rescheduler.check_single_job("nonexistent-job", self.mock_db, 1)
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch('backend.services.job_rescheduler.get_settings')
    async def test_check_single_job_wrong_status(self, mock_get_settings):
        """Test single job check when job is not scheduled"""
        job = Mock()
        job.status = "completed"
        self.mock_db.query.return_value.filter.return_value.first.return_value = job
        
        result = await self.rescheduler.check_single_job("job-123", self.mock_db, 1)
        
        assert result is None


class TestGlobalReschedulerManagement:
    """Test global rescheduler instance management"""
    
    def test_get_job_rescheduler_singleton(self):
        """Test get_job_rescheduler returns singleton instance"""
        rescheduler1 = get_job_rescheduler()
        rescheduler2 = get_job_rescheduler()
        
        assert rescheduler1 is rescheduler2
    
    def test_set_job_rescheduler(self):
        """Test setting custom rescheduler instance"""
        original_rescheduler = get_job_rescheduler()
        custom_rescheduler = JobRescheduler()
        
        set_job_rescheduler(custom_rescheduler)
        
        assert get_job_rescheduler() is custom_rescheduler
        assert get_job_rescheduler() is not original_rescheduler
        
        # Reset for other tests
        set_job_rescheduler(original_rescheduler)