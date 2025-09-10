"""
PW-WEATHER-ADD-001: Unit tests for Weather Service

Tests for weather service business logic, provider abstraction,
and weather condition evaluation against thresholds.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock

from backend.services.weather_service import (
    WeatherService,
    WeatherForecast,
    WeatherCondition,
    OpenWeatherMapProvider,
    MockWeatherProvider,
    get_weather_service,
    set_weather_service
)
from backend.services.settings_resolver import BadWeatherThreshold


class TestWeatherForecast:
    """Unit tests for WeatherForecast data class"""
    
    def test_is_bad_weather_rain_threshold(self):
        """Test weather is bad when rain probability exceeds threshold"""
        threshold = BadWeatherThreshold(
            rain_probability=70.0,
            wind_speed_mph=25.0,
            temp_low_f=35.0
        )
        
        forecast = WeatherForecast(
            date=datetime.now(timezone.utc),
            temperature_high_f=75.0,
            temperature_low_f=45.0,
            rain_probability=80.0,  # Exceeds threshold
            wind_speed_mph=15.0,
            condition=WeatherCondition.PARTLY_CLOUDY
        )
        
        assert forecast.is_bad_weather(threshold) is True
    
    def test_is_bad_weather_wind_threshold(self):
        """Test weather is bad when wind speed exceeds threshold"""
        threshold = BadWeatherThreshold(
            rain_probability=70.0,
            wind_speed_mph=25.0,
            temp_low_f=35.0
        )
        
        forecast = WeatherForecast(
            date=datetime.now(timezone.utc),
            temperature_high_f=75.0,
            temperature_low_f=45.0,
            rain_probability=30.0,
            wind_speed_mph=30.0,  # Exceeds threshold
            condition=WeatherCondition.WINDY
        )
        
        assert forecast.is_bad_weather(threshold) is True
    
    def test_is_bad_weather_temperature_threshold(self):
        """Test weather is bad when temperature is too low"""
        threshold = BadWeatherThreshold(
            rain_probability=70.0,
            wind_speed_mph=25.0,
            temp_low_f=35.0
        )
        
        forecast = WeatherForecast(
            date=datetime.now(timezone.utc),
            temperature_high_f=40.0,
            temperature_low_f=30.0,  # Below threshold
            rain_probability=20.0,
            wind_speed_mph=15.0,
            condition=WeatherCondition.CLEAR
        )
        
        assert forecast.is_bad_weather(threshold) is True
    
    def test_is_bad_weather_severe_conditions(self):
        """Test weather is bad for severe conditions regardless of thresholds"""
        threshold = BadWeatherThreshold(
            rain_probability=70.0,
            wind_speed_mph=25.0,
            temp_low_f=35.0
        )
        
        severe_conditions = [
            WeatherCondition.HEAVY_RAIN,
            WeatherCondition.THUNDERSTORMS,
            WeatherCondition.SNOW,
            WeatherCondition.SLEET
        ]
        
        for condition in severe_conditions:
            forecast = WeatherForecast(
                date=datetime.now(timezone.utc),
                temperature_high_f=75.0,
                temperature_low_f=45.0,  # Above threshold
                rain_probability=20.0,  # Below threshold
                wind_speed_mph=15.0,  # Below threshold
                condition=condition  # But severe condition
            )
            
            assert forecast.is_bad_weather(threshold) is True, f"{condition} should be bad weather"
    
    def test_is_good_weather(self):
        """Test weather is good when all conditions are within thresholds"""
        threshold = BadWeatherThreshold(
            rain_probability=70.0,
            wind_speed_mph=25.0,
            temp_low_f=35.0
        )
        
        forecast = WeatherForecast(
            date=datetime.now(timezone.utc),
            temperature_high_f=75.0,
            temperature_low_f=45.0,  # Above threshold
            rain_probability=30.0,  # Below threshold
            wind_speed_mph=15.0,  # Below threshold
            condition=WeatherCondition.PARTLY_CLOUDY  # Good condition
        )
        
        assert forecast.is_bad_weather(threshold) is False


class TestMockWeatherProvider:
    """Unit tests for MockWeatherProvider"""
    
    def test_validate_config_always_true(self):
        """Test mock provider configuration is always valid"""
        provider = MockWeatherProvider()
        assert provider.validate_config() is True
    
    @pytest.mark.asyncio
    async def test_get_forecast_default_data(self):
        """Test mock provider returns default forecast data"""
        provider = MockWeatherProvider()
        
        forecasts = await provider.get_forecast(33.7490, -84.3880, 3)
        
        assert len(forecasts) == 3
        assert all(isinstance(f, WeatherForecast) for f in forecasts)
        assert all(f.condition == WeatherCondition.PARTLY_CLOUDY for f in forecasts)
        assert all(f.temperature_high_f == 75.0 for f in forecasts)
    
    @pytest.mark.asyncio
    async def test_get_forecast_custom_data(self):
        """Test mock provider returns custom forecast data"""
        custom_forecast = WeatherForecast(
            date=datetime.now(timezone.utc),
            temperature_high_f=85.0,
            temperature_low_f=55.0,
            rain_probability=90.0,
            wind_speed_mph=35.0,
            condition=WeatherCondition.HEAVY_RAIN
        )
        
        provider = MockWeatherProvider(mock_conditions=[custom_forecast])
        
        forecasts = await provider.get_forecast(33.7490, -84.3880, 1)
        
        assert len(forecasts) == 1
        assert forecasts[0].rain_probability == 90.0
        assert forecasts[0].condition == WeatherCondition.HEAVY_RAIN


class TestOpenWeatherMapProvider:
    """Unit tests for OpenWeatherMapProvider"""
    
    def test_validate_config_with_api_key(self):
        """Test provider validation with API key"""
        provider = OpenWeatherMapProvider(api_key="test_key")
        assert provider.validate_config() is True
    
    def test_validate_config_without_api_key(self):
        """Test provider validation without API key"""
        provider = OpenWeatherMapProvider(api_key=None)
        assert provider.validate_config() is False
    
    def test_map_openweather_condition_clear(self):
        """Test mapping OpenWeather clear sky condition"""
        provider = OpenWeatherMapProvider("test_key")
        
        weather_data = {"id": 800, "main": "Clear", "description": "clear sky"}
        condition = provider._map_openweather_condition(weather_data)
        
        assert condition == WeatherCondition.CLEAR
    
    def test_map_openweather_condition_rain(self):
        """Test mapping OpenWeather rain conditions"""
        provider = OpenWeatherMapProvider("test_key")
        
        test_cases = [
            (500, WeatherCondition.LIGHT_RAIN),
            (502, WeatherCondition.MODERATE_RAIN),
            (520, WeatherCondition.HEAVY_RAIN)
        ]
        
        for condition_id, expected in test_cases:
            weather_data = {"id": condition_id}
            condition = provider._map_openweather_condition(weather_data)
            assert condition == expected
    
    def test_map_openweather_condition_thunderstorms(self):
        """Test mapping OpenWeather thunderstorm conditions"""
        provider = OpenWeatherMapProvider("test_key")
        
        thunderstorm_ids = [200, 210, 232]
        
        for condition_id in thunderstorm_ids:
            weather_data = {"id": condition_id}
            condition = provider._map_openweather_condition(weather_data)
            assert condition == WeatherCondition.THUNDERSTORMS
    
    @pytest.mark.asyncio
    async def test_get_forecast_no_api_key_raises_error(self):
        """Test forecast request fails without API key"""
        provider = OpenWeatherMapProvider(api_key=None)
        
        with pytest.raises(ValueError, match="OpenWeatherMap API key not configured"):
            await provider.get_forecast(33.7490, -84.3880, 3)


class TestWeatherService:
    """Unit tests for WeatherService"""
    
    def test_init_with_provider(self):
        """Test WeatherService initialization with custom provider"""
        mock_provider = MockWeatherProvider()
        service = WeatherService(provider=mock_provider)
        
        assert service.provider is mock_provider
    
    @patch('backend.services.weather_service.os.getenv')
    def test_create_default_provider_openweather(self, mock_getenv):
        """Test default provider creation for OpenWeatherMap"""
        mock_getenv.return_value = "openweather"
        
        service = WeatherService()
        
        assert isinstance(service.provider, OpenWeatherMapProvider)
    
    @patch('backend.services.weather_service.os.getenv')
    def test_create_default_provider_mock(self, mock_getenv):
        """Test default provider creation for mock"""
        mock_getenv.return_value = "mock"
        
        service = WeatherService()
        
        assert isinstance(service.provider, MockWeatherProvider)
    
    @pytest.mark.asyncio
    async def test_get_forecast_success(self):
        """Test successful forecast retrieval"""
        mock_provider = Mock()
        mock_forecast = WeatherForecast(
            date=datetime.now(timezone.utc),
            temperature_high_f=75.0,
            temperature_low_f=45.0,
            rain_probability=30.0,
            wind_speed_mph=15.0,
            condition=WeatherCondition.CLEAR
        )
        mock_provider.get_forecast = AsyncMock(return_value=[mock_forecast])
        
        service = WeatherService(provider=mock_provider)
        
        forecasts = await service.get_forecast(33.7490, -84.3880, 3)
        
        assert len(forecasts) == 1
        assert forecasts[0] == mock_forecast
        mock_provider.get_forecast.assert_called_once_with(33.7490, -84.3880, 3)
    
    @pytest.mark.asyncio
    async def test_get_forecast_error_returns_empty(self):
        """Test forecast error handling returns empty list"""
        mock_provider = Mock()
        mock_provider.get_forecast = AsyncMock(side_effect=Exception("API Error"))
        
        service = WeatherService(provider=mock_provider)
        
        forecasts = await service.get_forecast(33.7490, -84.3880, 3)
        
        assert forecasts == []
    
    def test_evaluate_weather_risk_has_risk(self):
        """Test weather risk evaluation identifies risky weather"""
        service = WeatherService(provider=MockWeatherProvider())
        
        threshold = BadWeatherThreshold(
            rain_probability=50.0,
            wind_speed_mph=20.0,
            temp_low_f=40.0
        )
        
        # Bad weather forecast
        bad_forecast = WeatherForecast(
            date=datetime.now(timezone.utc),
            temperature_high_f=75.0,
            temperature_low_f=30.0,  # Below threshold
            rain_probability=80.0,  # Above threshold
            wind_speed_mph=15.0,
            condition=WeatherCondition.CLOUDY
        )
        
        # Good weather forecast
        good_forecast = WeatherForecast(
            date=datetime.now(timezone.utc) + timedelta(days=1),
            temperature_high_f=75.0,
            temperature_low_f=50.0,
            rain_probability=20.0,
            wind_speed_mph=10.0,
            condition=WeatherCondition.CLEAR
        )
        
        risk_assessment = service.evaluate_weather_risk([bad_forecast, good_forecast], threshold)
        
        assert risk_assessment["overall_risk"] is True
        assert len(risk_assessment["risky_days"]) == 1
        assert len(risk_assessment["safe_days"]) == 1
        assert risk_assessment["next_safe_day"] == good_forecast.date
    
    def test_evaluate_weather_risk_no_risk(self):
        """Test weather risk evaluation with all good weather"""
        service = WeatherService(provider=MockWeatherProvider())
        
        threshold = BadWeatherThreshold(
            rain_probability=70.0,
            wind_speed_mph=25.0,
            temp_low_f=35.0
        )
        
        good_forecasts = [
            WeatherForecast(
                date=datetime.now(timezone.utc) + timedelta(days=i),
                temperature_high_f=75.0,
                temperature_low_f=45.0,
                rain_probability=30.0,
                wind_speed_mph=15.0,
                condition=WeatherCondition.CLEAR
            )
            for i in range(3)
        ]
        
        risk_assessment = service.evaluate_weather_risk(good_forecasts, threshold)
        
        assert risk_assessment["overall_risk"] is False
        assert len(risk_assessment["risky_days"]) == 0
        assert len(risk_assessment["safe_days"]) == 3
    
    def test_get_risk_reasons(self):
        """Test risk reason generation"""
        service = WeatherService(provider=MockWeatherProvider())
        
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
            condition=WeatherCondition.THUNDERSTORMS  # Severe condition
        )
        
        reasons = service._get_risk_reasons(forecast, threshold)
        
        assert len(reasons) == 4  # 3 threshold violations + severe condition
        assert any("High rain probability" in reason for reason in reasons)
        assert any("High wind speed" in reason for reason in reasons)
        assert any("Low temperature" in reason for reason in reasons)
        assert any("Severe weather condition" in reason for reason in reasons)


class TestGlobalServiceManagement:
    """Test global service instance management"""
    
    def test_get_weather_service_singleton(self):
        """Test get_weather_service returns singleton instance"""
        service1 = get_weather_service()
        service2 = get_weather_service()
        
        assert service1 is service2
    
    def test_set_weather_service(self):
        """Test setting custom weather service instance"""
        original_service = get_weather_service()
        custom_service = WeatherService(provider=MockWeatherProvider())
        
        set_weather_service(custom_service)
        
        assert get_weather_service() is custom_service
        assert get_weather_service() is not original_service
        
        # Reset for other tests
        set_weather_service(original_service)