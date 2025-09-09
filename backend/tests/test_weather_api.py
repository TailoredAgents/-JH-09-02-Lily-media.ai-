"""
PW-WEATHER-ADD-001: Integration tests for Weather API

Tests for weather API endpoints including manual weather checks,
admin-triggered rescheduling, and single job rescheduling.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.api.weather import router
from backend.services.weather_service import WeatherForecast, WeatherCondition
from backend.services.job_rescheduler import RescheduleResult
from backend.services.settings_resolver import WeatherSettings, BadWeatherThreshold
from backend.db.models import Job, User, Organization
from backend.middleware.tenant_context import TenantContext


@pytest.fixture
def mock_tenant_context():
    """Mock tenant context for tests"""
    context = TenantContext(
        organization_id="test-org-123",
        user_id=42,
        roles=["admin"],
        is_super_admin=False
    )
    return context


@pytest.fixture
def mock_user():
    """Mock user for tests"""
    user = Mock(spec=User)
    user.id = 42
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_db():
    """Mock database session for tests"""
    return Mock(spec=Session)


@pytest.fixture
def sample_job():
    """Sample job for tests"""
    job = Mock(spec=Job)
    job.id = "job-123"
    job.organization_id = "test-org-123"
    job.address = "123 Test Street, Atlanta, GA"
    job.scheduled_for = datetime.now(timezone.utc) + timedelta(days=1)
    job.duration_minutes = 120
    return job


@pytest.fixture
def sample_weather_settings():
    """Sample weather settings for tests"""
    return WeatherSettings(
        bad_weather_threshold=BadWeatherThreshold(
            rain_probability=70.0,
            wind_speed_mph=25.0,
            temp_low_f=35.0
        ),
        lookahead_days=3,
        auto_reschedule=True
    )


class TestWeatherCheckEndpoint:
    """Tests for GET /api/v1/weather/check endpoint"""
    
    @pytest.mark.asyncio
    @patch('backend.api.weather.get_weather_service')
    @patch('backend.api.weather.get_settings')
    async def test_check_job_weather_success(
        self, mock_get_settings, mock_get_weather_service, 
        mock_tenant_context, mock_user, mock_db, sample_job, sample_weather_settings
    ):
        """Test successful weather check for a job"""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = sample_job
        mock_get_settings.return_value = sample_weather_settings
        
        # Mock weather service
        mock_weather_service = Mock()
        forecasts = [
            WeatherForecast(
                date=sample_job.scheduled_for,
                temperature_high_f=75.0,
                temperature_low_f=45.0,
                rain_probability=30.0,
                wind_speed_mph=15.0,
                condition=WeatherCondition.CLEAR
            )
        ]
        
        mock_weather_service.get_forecast = AsyncMock(return_value=forecasts)
        mock_weather_service.evaluate_weather_risk.return_value = {
            "overall_risk": False,
            "risky_days": [],
            "safe_days": [sample_job.scheduled_for],
            "next_safe_day": sample_job.scheduled_for
        }
        mock_get_weather_service.return_value = mock_weather_service
        
        # Import and test the endpoint function directly
        from backend.api.weather import check_job_weather
        
        response = await check_job_weather(
            job_id="job-123",
            tenant_context=mock_tenant_context,
            current_user=mock_user,
            db=mock_db
        )
        
        assert response.job_id == "job-123"
        assert response.job_address == "123 Test Street, Atlanta, GA"
        assert response.reschedule_recommended is False
        assert len(response.weather_forecast) == 1
        assert response.weather_forecast[0]["condition"] == "clear"
    
    @pytest.mark.asyncio
    async def test_check_job_weather_job_not_found(
        self, mock_tenant_context, mock_user, mock_db
    ):
        """Test weather check with non-existent job"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        from backend.api.weather import check_job_weather
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await check_job_weather(
                job_id="nonexistent-job",
                tenant_context=mock_tenant_context,
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('backend.api.weather.get_settings')
    async def test_check_job_weather_no_scheduled_date(
        self, mock_get_settings, mock_tenant_context, mock_user, mock_db, sample_weather_settings
    ):
        """Test weather check for job without scheduled date"""
        job_without_schedule = Mock(spec=Job)
        job_without_schedule.scheduled_for = None
        
        mock_db.query.return_value.filter.return_value.first.return_value = job_without_schedule
        mock_get_settings.return_value = sample_weather_settings
        
        from backend.api.weather import check_job_weather
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await check_job_weather(
                job_id="job-no-schedule",
                tenant_context=mock_tenant_context,
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 400
        assert "scheduled date" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('backend.api.weather.get_weather_service')
    @patch('backend.api.weather.get_settings')
    async def test_check_job_weather_service_error(
        self, mock_get_settings, mock_get_weather_service,
        mock_tenant_context, mock_user, mock_db, sample_job, sample_weather_settings
    ):
        """Test weather check with weather service error"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_job
        mock_get_settings.return_value = sample_weather_settings
        
        # Mock weather service to raise error
        mock_weather_service = Mock()
        mock_weather_service.get_forecast = AsyncMock(side_effect=Exception("API Error"))
        mock_get_weather_service.return_value = mock_weather_service
        
        from backend.api.weather import check_job_weather
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await check_job_weather(
                job_id="job-123",
                tenant_context=mock_tenant_context,
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 500
        assert "Failed to check weather" in str(exc_info.value.detail)


class TestReschedulingRunEndpoint:
    """Tests for POST /api/v1/weather/run endpoint"""
    
    @pytest.mark.asyncio
    @patch('backend.api.weather.get_job_rescheduler')
    @patch('backend.api.weather.get_settings')
    async def test_run_weather_rescheduling_success(
        self, mock_get_settings, mock_get_job_rescheduler,
        mock_tenant_context, mock_user, mock_db, sample_weather_settings
    ):
        """Test successful rescheduling run"""
        mock_get_settings.return_value = sample_weather_settings
        
        # Mock rescheduler results
        reschedule_results = [
            RescheduleResult(
                job_id="job-1",
                original_date=datetime.now(timezone.utc),
                new_date=datetime.now(timezone.utc) + timedelta(days=1),
                reschedule_reason="High wind speed",
                success=True
            ),
            RescheduleResult(
                job_id="job-2", 
                original_date=datetime.now(timezone.utc),
                new_date=None,
                reschedule_reason="No safe window found",
                success=False,
                error_message="No available slots"
            )
        ]
        
        mock_rescheduler = Mock()
        mock_rescheduler.run_rescheduling_check = AsyncMock(return_value=reschedule_results)
        mock_get_job_rescheduler.return_value = mock_rescheduler
        
        from backend.api.weather import run_weather_rescheduling, RescheduleRunRequest
        from fastapi import BackgroundTasks
        
        request = RescheduleRunRequest()
        background_tasks = BackgroundTasks()
        
        response = await run_weather_rescheduling(
            request=request,
            background_tasks=background_tasks,
            tenant_context=mock_tenant_context,
            current_user=mock_user,
            db=mock_db
        )
        
        assert response.organization_id == "test-org-123"
        assert response.total_jobs_checked == 2
        assert response.jobs_rescheduled == 1
        assert response.jobs_failed == 1
        assert len(response.reschedule_results) == 2
    
    @pytest.mark.asyncio
    @patch('backend.api.weather.get_settings')
    async def test_run_weather_rescheduling_disabled_without_force(
        self, mock_get_settings, mock_tenant_context, mock_user, mock_db
    ):
        """Test rescheduling run fails when disabled and not forced"""
        # Weather settings with auto_reschedule disabled
        disabled_settings = WeatherSettings(auto_reschedule=False)
        mock_get_settings.return_value = disabled_settings
        
        from backend.api.weather import run_weather_rescheduling, RescheduleRunRequest
        from fastapi import BackgroundTasks, HTTPException
        
        request = RescheduleRunRequest(force=False)
        background_tasks = BackgroundTasks()
        
        with pytest.raises(HTTPException) as exc_info:
            await run_weather_rescheduling(
                request=request,
                background_tasks=background_tasks,
                tenant_context=mock_tenant_context,
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 400
        assert "disabled" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('backend.api.weather.get_job_rescheduler')
    @patch('backend.api.weather.get_settings')
    async def test_run_weather_rescheduling_forced_when_disabled(
        self, mock_get_settings, mock_get_job_rescheduler,
        mock_tenant_context, mock_user, mock_db
    ):
        """Test rescheduling run works when forced even if disabled"""
        # Weather settings with auto_reschedule disabled
        disabled_settings = WeatherSettings(auto_reschedule=False)
        mock_get_settings.return_value = disabled_settings
        
        # Mock successful rescheduling
        mock_rescheduler = Mock()
        mock_rescheduler.run_rescheduling_check = AsyncMock(return_value=[])
        mock_get_job_rescheduler.return_value = mock_rescheduler
        
        from backend.api.weather import run_weather_rescheduling, RescheduleRunRequest
        from fastapi import BackgroundTasks
        
        request = RescheduleRunRequest(force=True)
        background_tasks = BackgroundTasks()
        
        response = await run_weather_rescheduling(
            request=request,
            background_tasks=background_tasks,
            tenant_context=mock_tenant_context,
            current_user=mock_user,
            db=mock_db
        )
        
        assert response.organization_id == "test-org-123"
        assert response.total_jobs_checked == 0


class TestSingleJobReschedulingEndpoint:
    """Tests for POST /api/v1/weather/reschedule/job/{job_id} endpoint"""
    
    @pytest.mark.asyncio
    @patch('backend.api.weather.get_job_rescheduler')
    async def test_reschedule_single_job_success(
        self, mock_get_job_rescheduler, mock_tenant_context, mock_user, mock_db, sample_job
    ):
        """Test successful single job rescheduling"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_job
        
        # Mock successful rescheduling result
        reschedule_result = RescheduleResult(
            job_id="job-123",
            original_date=sample_job.scheduled_for,
            new_date=sample_job.scheduled_for + timedelta(days=1),
            reschedule_reason="High rain probability: 80%",
            success=True
        )
        
        mock_rescheduler = Mock()
        mock_rescheduler.check_single_job = AsyncMock(return_value=reschedule_result)
        mock_get_job_rescheduler.return_value = mock_rescheduler
        
        from backend.api.weather import reschedule_single_job
        
        response = await reschedule_single_job(
            job_id="job-123",
            tenant_context=mock_tenant_context,
            current_user=mock_user,
            db=mock_db
        )
        
        assert response["job_id"] == "job-123"
        assert response["action_taken"] == "rescheduled"
        assert response["success"] is True
        assert "High rain probability" in response["reschedule_reason"]
    
    @pytest.mark.asyncio
    @patch('backend.api.weather.get_job_rescheduler')
    async def test_reschedule_single_job_no_action_needed(
        self, mock_get_job_rescheduler, mock_tenant_context, mock_user, mock_db, sample_job
    ):
        """Test single job rescheduling when no action is needed"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_job
        
        # Mock no rescheduling needed (good weather)
        mock_rescheduler = Mock()
        mock_rescheduler.check_single_job = AsyncMock(return_value=None)
        mock_get_job_rescheduler.return_value = mock_rescheduler
        
        from backend.api.weather import reschedule_single_job
        
        response = await reschedule_single_job(
            job_id="job-123",
            tenant_context=mock_tenant_context,
            current_user=mock_user,
            db=mock_db
        )
        
        assert response["job_id"] == "job-123"
        assert response["action_taken"] == "none"
        assert "weather conditions are acceptable" in response["reason"]
    
    @pytest.mark.asyncio
    async def test_reschedule_single_job_not_found(
        self, mock_tenant_context, mock_user, mock_db
    ):
        """Test single job rescheduling with non-existent job"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        from backend.api.weather import reschedule_single_job
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await reschedule_single_job(
                job_id="nonexistent-job",
                tenant_context=mock_tenant_context,
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_reschedule_single_job_wrong_status(
        self, mock_tenant_context, mock_user, mock_db
    ):
        """Test single job rescheduling for job in wrong status"""
        completed_job = Mock(spec=Job)
        completed_job.id = "job-completed"
        completed_job.status = "completed"
        completed_job.organization_id = "test-org-123"
        
        mock_db.query.return_value.filter.return_value.first.return_value = completed_job
        
        from backend.api.weather import reschedule_single_job
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await reschedule_single_job(
                job_id="job-completed",
                tenant_context=mock_tenant_context,
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 400
        assert "not in scheduled status" in str(exc_info.value.detail)


class TestWeatherStatusEndpoint:
    """Tests for GET /api/v1/weather/status endpoint"""
    
    @pytest.mark.asyncio
    @patch('backend.api.weather.get_weather_service')
    async def test_get_weather_service_status(
        self, mock_get_weather_service, mock_tenant_context
    ):
        """Test weather service status endpoint"""
        # Mock weather service with configured provider
        mock_provider = Mock()
        mock_provider.validate_config.return_value = True
        
        mock_weather_service = Mock()
        mock_weather_service.provider = mock_provider
        mock_get_weather_service.return_value = mock_weather_service
        
        from backend.api.weather import get_weather_service_status
        
        response = await get_weather_service_status(
            tenant_context=mock_tenant_context
        )
        
        assert "weather_provider" in response
        assert response["provider_configured"] is True
        assert response["service_available"] is True