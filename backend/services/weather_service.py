"""
PW-WEATHER-ADD-001: Weather service with provider abstraction

Provider-agnostic weather service for forecast retrieval and weather condition evaluation.
Supports multiple weather providers through injectable provider pattern.
"""

import os
import json
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Protocol
from dataclasses import dataclass
from enum import Enum

import requests
import aiohttp
from pydantic import BaseModel, Field

from backend.services.settings_resolver import BadWeatherThreshold


class WeatherCondition(str, Enum):
    """Weather condition classifications"""
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy" 
    CLOUDY = "cloudy"
    LIGHT_RAIN = "light_rain"
    MODERATE_RAIN = "moderate_rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORMS = "thunderstorms"
    SNOW = "snow"
    SLEET = "sleet"
    FOG = "fog"
    WINDY = "windy"


@dataclass
class WeatherForecast:
    """
    Normalized weather forecast structure
    
    Provider-agnostic format for weather data from various APIs
    """
    date: datetime
    temperature_high_f: float
    temperature_low_f: float
    temperature_current_f: Optional[float] = None
    rain_probability: float = 0.0  # Percentage (0-100)
    precipitation_inches: float = 0.0
    wind_speed_mph: float = 0.0
    wind_direction: Optional[str] = None
    humidity: Optional[float] = None
    condition: WeatherCondition = WeatherCondition.CLEAR
    condition_description: Optional[str] = None
    uv_index: Optional[int] = None
    
    def is_bad_weather(self, threshold: BadWeatherThreshold) -> bool:
        """
        Check if weather conditions exceed bad weather thresholds
        
        Args:
            threshold: Weather thresholds for rescheduling decisions
            
        Returns:
            True if weather conditions are bad enough to reschedule
        """
        if self.rain_probability >= threshold.rain_probability:
            return True
            
        if self.wind_speed_mph >= threshold.wind_speed_mph:
            return True
            
        if self.temperature_low_f <= threshold.temp_low_f:
            return True
            
        # Additional checks for severe conditions
        if self.condition in [
            WeatherCondition.HEAVY_RAIN,
            WeatherCondition.THUNDERSTORMS,
            WeatherCondition.SNOW,
            WeatherCondition.SLEET
        ]:
            return True
            
        return False


class WeatherProvider(ABC):
    """Abstract base class for weather providers"""
    
    @abstractmethod
    async def get_forecast(
        self, 
        latitude: float, 
        longitude: float, 
        days: int = 3
    ) -> List[WeatherForecast]:
        """
        Get weather forecast for location
        
        Args:
            latitude: Location latitude
            longitude: Location longitude  
            days: Number of days to forecast
            
        Returns:
            List of daily weather forecasts
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration (API keys, etc.)"""
        pass


class OpenWeatherMapProvider(WeatherProvider):
    """OpenWeatherMap API provider implementation"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    def validate_config(self) -> bool:
        """Validate OpenWeatherMap API configuration"""
        return bool(self.api_key)
    
    async def get_forecast(
        self, 
        latitude: float, 
        longitude: float, 
        days: int = 3
    ) -> List[WeatherForecast]:
        """Get forecast from OpenWeatherMap API"""
        if not self.validate_config():
            raise ValueError("OpenWeatherMap API key not configured")
            
        url = f"{self.base_url}/forecast"
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self.api_key,
            "units": "imperial",  # Fahrenheit
            "cnt": min(days * 8, 40)  # 3-hour intervals, max 5 days
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"OpenWeatherMap API error: {response.status}")
                    
                data = await response.json()
                return self._parse_openweather_response(data)
    
    def _parse_openweather_response(self, data: Dict) -> List[WeatherForecast]:
        """Parse OpenWeatherMap response into normalized format"""
        forecasts = []
        daily_data = {}
        
        # Group 3-hour forecasts by date
        for item in data.get("list", []):
            dt = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
            date_key = dt.date()
            
            if date_key not in daily_data:
                daily_data[date_key] = {
                    "temps": [],
                    "rain_probs": [],
                    "precipitations": [],
                    "winds": [],
                    "conditions": []
                }
            
            daily_data[date_key]["temps"].append(item["main"]["temp"])
            daily_data[date_key]["rain_probs"].append(
                item.get("pop", 0) * 100  # Convert to percentage
            )
            daily_data[date_key]["precipitations"].append(
                item.get("rain", {}).get("3h", 0) / 25.4  # mm to inches
            )
            daily_data[date_key]["winds"].append(item["wind"]["speed"])
            daily_data[date_key]["conditions"].append(
                self._map_openweather_condition(item["weather"][0])
            )
        
        # Create daily forecasts
        for date_key, day_data in daily_data.items():
            forecast = WeatherForecast(
                date=datetime.combine(date_key, datetime.min.time(), timezone.utc),
                temperature_high_f=max(day_data["temps"]),
                temperature_low_f=min(day_data["temps"]),
                rain_probability=max(day_data["rain_probs"]),
                precipitation_inches=sum(day_data["precipitations"]),
                wind_speed_mph=max(day_data["winds"]),
                condition=max(day_data["conditions"], key=lambda c: c.value)
            )
            forecasts.append(forecast)
            
        return sorted(forecasts, key=lambda f: f.date)
    
    def _map_openweather_condition(self, weather_data: Dict) -> WeatherCondition:
        """Map OpenWeatherMap condition codes to internal enum"""
        condition_id = weather_data.get("id", 800)
        
        if condition_id == 800:  # Clear sky
            return WeatherCondition.CLEAR
        elif condition_id == 801:  # Few clouds
            return WeatherCondition.PARTLY_CLOUDY
        elif 802 <= condition_id <= 804:  # Scattered to overcast clouds
            return WeatherCondition.CLOUDY
        elif 500 <= condition_id <= 501:  # Light rain
            return WeatherCondition.LIGHT_RAIN
        elif 502 <= condition_id <= 504:  # Moderate to heavy rain
            return WeatherCondition.MODERATE_RAIN
        elif condition_id >= 520:  # Heavy rain/showers
            return WeatherCondition.HEAVY_RAIN
        elif 200 <= condition_id <= 232:  # Thunderstorms
            return WeatherCondition.THUNDERSTORMS
        elif 600 <= condition_id <= 622:  # Snow
            return WeatherCondition.SNOW
        elif condition_id == 511 or 611 <= condition_id <= 616:  # Sleet/freezing rain
            return WeatherCondition.SLEET
        elif 701 <= condition_id <= 781:  # Fog/mist/haze
            return WeatherCondition.FOG
        else:
            return WeatherCondition.CLOUDY


class MockWeatherProvider(WeatherProvider):
    """Mock provider for testing and development"""
    
    def __init__(self, mock_conditions: Optional[List[WeatherForecast]] = None):
        self.mock_conditions = mock_conditions or []
    
    def validate_config(self) -> bool:
        """Mock provider is always valid"""
        return True
    
    async def get_forecast(
        self, 
        latitude: float, 
        longitude: float, 
        days: int = 3
    ) -> List[WeatherForecast]:
        """Return mock forecast data"""
        if self.mock_conditions:
            return self.mock_conditions[:days]
            
        # Generate default mock data
        forecasts = []
        base_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(days):
            forecast = WeatherForecast(
                date=base_date + timedelta(days=i),
                temperature_high_f=75.0,
                temperature_low_f=45.0,
                rain_probability=20.0,
                precipitation_inches=0.0,
                wind_speed_mph=10.0,
                condition=WeatherCondition.PARTLY_CLOUDY
            )
            forecasts.append(forecast)
            
        return forecasts


class WeatherService:
    """
    PW-WEATHER-ADD-001: Weather service with provider abstraction
    
    Provides weather forecasting capabilities with pluggable providers
    """
    
    def __init__(self, provider: Optional[WeatherProvider] = None):
        """
        Initialize weather service with optional provider
        
        Args:
            provider: Weather provider instance. If None, will auto-select based on config
        """
        if provider:
            self.provider = provider
        else:
            self.provider = self._create_default_provider()
    
    def _create_default_provider(self) -> WeatherProvider:
        """Create default weather provider based on environment configuration"""
        provider_type = os.getenv("WEATHER_PROVIDER", "openweather").lower()
        
        if provider_type == "openweather":
            return OpenWeatherMapProvider()
        elif provider_type == "mock":
            return MockWeatherProvider()
        else:
            # Default to mock for development
            return MockWeatherProvider()
    
    async def get_forecast(
        self, 
        latitude: float, 
        longitude: float, 
        date_range: int = 3
    ) -> List[WeatherForecast]:
        """
        Get weather forecast for location and date range
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            date_range: Number of days to forecast
            
        Returns:
            List of weather forecasts in normalized format
        """
        try:
            return await self.provider.get_forecast(latitude, longitude, date_range)
        except Exception as e:
            # Log error and return empty forecast rather than failing
            # In production, this should use proper logging
            print(f"Weather service error: {e}")
            return []
    
    def evaluate_weather_risk(
        self, 
        forecasts: List[WeatherForecast],
        threshold: BadWeatherThreshold
    ) -> Dict[str, Any]:
        """
        Evaluate weather risk for given forecasts and thresholds
        
        Args:
            forecasts: List of weather forecasts to evaluate
            threshold: Weather thresholds for risk assessment
            
        Returns:
            Risk evaluation with recommendations
        """
        risky_days = []
        safe_days = []
        
        for forecast in forecasts:
            if forecast.is_bad_weather(threshold):
                risky_days.append({
                    "date": forecast.date,
                    "reasons": self._get_risk_reasons(forecast, threshold)
                })
            else:
                safe_days.append(forecast.date)
        
        return {
            "overall_risk": len(risky_days) > 0,
            "risky_days": risky_days,
            "safe_days": safe_days,
            "next_safe_day": safe_days[0] if safe_days else None,
            "total_days_evaluated": len(forecasts)
        }
    
    def _get_risk_reasons(
        self, 
        forecast: WeatherForecast, 
        threshold: BadWeatherThreshold
    ) -> List[str]:
        """Get list of reasons why weather is risky"""
        reasons = []
        
        if forecast.rain_probability >= threshold.rain_probability:
            reasons.append(f"High rain probability: {forecast.rain_probability}%")
            
        if forecast.wind_speed_mph >= threshold.wind_speed_mph:
            reasons.append(f"High wind speed: {forecast.wind_speed_mph} mph")
            
        if forecast.temperature_low_f <= threshold.temp_low_f:
            reasons.append(f"Low temperature: {forecast.temperature_low_f}°F")
            
        if forecast.condition in [
            WeatherCondition.HEAVY_RAIN,
            WeatherCondition.THUNDERSTORMS,
            WeatherCondition.SNOW,
            WeatherCondition.SLEET
        ]:
            reasons.append(f"Severe weather condition: {forecast.condition}")
            
        return reasons


# Global service instance
_weather_service_instance: Optional[WeatherService] = None


def get_weather_service() -> WeatherService:
    """Get global weather service instance"""
    global _weather_service_instance
    if _weather_service_instance is None:
        _weather_service_instance = WeatherService()
    return _weather_service_instance


def set_weather_service(service: WeatherService) -> None:
    """Set global weather service instance (mainly for testing)"""
    global _weather_service_instance
    _weather_service_instance = service