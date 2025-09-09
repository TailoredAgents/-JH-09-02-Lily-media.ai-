"""
Unit tests for PW-SETTINGS-REPLACE-001: Central typed settings resolver

Tests cover:
- Default settings validation
- Hierarchical merging (plan -> org -> team -> user)
- Invalid input rejection
- Caching behavior
- Cache invalidation
- Namespace-specific access
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any

from backend.services.settings_resolver import (
    PWSettings,
    PricingSettings,
    WeatherSettings,
    DMSettings,
    SchedulingSettings,
    SettingsResolver,
    SettingsNamespace,
    SurfaceType,
    WeatherSeverity,
    create_settings_resolver,
    get_pricing_settings,
    get_weather_settings,
    get_dm_settings,
    get_scheduling_settings
)
from backend.db.models import Plan, Organization, Team, UserSetting, User


class TestPricingSettings:
    """Test PricingSettings validation and defaults"""
    
    def test_default_pricing_settings(self):
        """Test default pricing settings are valid"""
        settings = PricingSettings()
        
        assert settings.minimum_job_price == 150.0
        assert settings.base_rates[SurfaceType.CONCRETE] == 0.15
        assert settings.base_rates[SurfaceType.ROOF] == 0.30
        assert settings.soft_wash_multiplier == 1.3
        assert settings.travel_rate_per_mile == 2.0
        assert settings.free_travel_radius_miles == 15.0
        
        # Check seasonal multipliers
        assert len(settings.seasonal_multipliers) == 4
        assert "spring" in settings.seasonal_multipliers
        assert settings.seasonal_multipliers["spring"] == 1.2
    
    def test_invalid_base_rates_rejected(self):
        """Test that negative base rates are rejected"""
        with pytest.raises(ValueError, match="Base rate for .* must be positive"):
            PricingSettings(base_rates={
                SurfaceType.CONCRETE: -0.10  # Invalid negative rate
            })
    
    def test_invalid_seasonal_multipliers_rejected(self):
        """Test that invalid seasonal multipliers are rejected"""
        with pytest.raises(ValueError, match="Must include all seasons"):
            PricingSettings(seasonal_multipliers={
                "spring": 1.2,
                "summer": 1.0  # Missing fall and winter
            })
        
        with pytest.raises(ValueError, match="Seasonal multiplier for .* must be positive"):
            PricingSettings(seasonal_multipliers={
                "spring": 1.2,
                "summer": 1.0,
                "fall": 1.1,
                "winter": -0.8  # Invalid negative multiplier
            })
    
    def test_field_constraints(self):
        """Test field validation constraints"""
        with pytest.raises(ValueError):
            PricingSettings(minimum_job_price=-100.0)  # Below minimum
        
        with pytest.raises(ValueError):
            PricingSettings(minimum_job_price=2000.0)  # Above maximum
        
        with pytest.raises(ValueError):
            PricingSettings(soft_wash_multiplier=0.5)  # Below minimum
        
        with pytest.raises(ValueError):
            PricingSettings(travel_rate_per_mile=-1.0)  # Below minimum


class TestWeatherSettings:
    """Test WeatherSettings validation and defaults"""
    
    def test_default_weather_settings(self):
        """Test default weather settings are valid"""
        settings = WeatherSettings()
        
        assert settings.rain_delay_threshold_inches == 0.1
        assert settings.max_wind_speed_roof == 15.0
        assert settings.max_wind_speed_general == 25.0
        assert settings.min_temperature_f == 35.0
        assert settings.max_temperature_f == 95.0
        assert settings.auto_reschedule_enabled is True
        assert settings.advance_notice_hours == 24
        
        # Check weather severity actions
        assert len(settings.weather_severity_actions) == 3
        assert settings.weather_severity_actions[WeatherSeverity.LIGHT] == "proceed"
        assert settings.weather_severity_actions[WeatherSeverity.SEVERE] == "cancel_day"
    
    def test_temperature_validation(self):
        """Test temperature range validation"""
        with pytest.raises(ValueError, match="Max temperature must be greater than min temperature"):
            WeatherSettings(min_temperature_f=80.0, max_temperature_f=60.0)
    
    def test_field_constraints(self):
        """Test weather field validation constraints"""
        with pytest.raises(ValueError):
            WeatherSettings(rain_delay_threshold_inches=-0.1)  # Below minimum
        
        with pytest.raises(ValueError):
            WeatherSettings(max_wind_speed_roof=3.0)  # Below minimum
        
        with pytest.raises(ValueError):
            WeatherSettings(advance_notice_hours=200)  # Above maximum


class TestDMSettings:
    """Test DMSettings validation and defaults"""
    
    def test_default_dm_settings(self):
        """Test default DM settings are valid"""
        settings = DMSettings()
        
        assert settings.auto_response_enabled is True
        assert settings.response_delay_minutes == 2
        assert settings.require_photos_for_quote is True
        assert settings.max_photos_per_inquiry == 5
        assert settings.provide_ballpark_estimates is True
        assert settings.ballpark_accuracy_margin == 0.25
        assert settings.auto_qualify_threshold == 0.8
        assert settings.booking_link_in_response is True
        assert settings.follow_up_after_hours == 24
        
        # Check qualification questions
        assert len(settings.qualification_questions) == 4
        assert "What type of surface needs cleaning?" in settings.qualification_questions
    
    def test_field_constraints(self):
        """Test DM field validation constraints"""
        with pytest.raises(ValueError):
            DMSettings(response_delay_minutes=70)  # Above maximum
        
        with pytest.raises(ValueError):
            DMSettings(max_photos_per_inquiry=25)  # Above maximum
        
        with pytest.raises(ValueError):
            DMSettings(ballpark_accuracy_margin=1.5)  # Above maximum


class TestSchedulingSettings:
    """Test SchedulingSettings validation and defaults"""
    
    def test_default_scheduling_settings(self):
        """Test default scheduling settings are valid"""
        settings = SchedulingSettings()
        
        assert settings.business_hours_start == "08:00"
        assert settings.business_hours_end == "17:00"
        assert len(settings.working_days) == 6  # Monday-Saturday
        assert "monday" in settings.working_days
        assert "sunday" not in settings.working_days
        assert settings.default_job_duration_hours == 3.0
        assert settings.buffer_time_minutes == 30
        assert settings.min_advance_booking_hours == 24
        assert settings.max_advance_booking_days == 90
        assert settings.allow_rush_jobs is True
        assert settings.rush_job_multiplier == 1.5
        assert settings.max_jobs_per_day == 6
    
    def test_working_days_validation(self):
        """Test working days validation"""
        # Valid working days
        settings = SchedulingSettings(working_days=["monday", "tuesday", "wednesday"])
        assert settings.working_days == ["monday", "tuesday", "wednesday"]
        
        # Case insensitive
        settings = SchedulingSettings(working_days=["MONDAY", "Tuesday", "wednesday"])
        assert settings.working_days == ["monday", "tuesday", "wednesday"]
        
        # Invalid day
        with pytest.raises(ValueError, match="Invalid working day"):
            SchedulingSettings(working_days=["monday", "invalid_day"])
    
    def test_time_format_validation(self):
        """Test time format validation"""
        # Valid times
        SchedulingSettings(business_hours_start="09:00", business_hours_end="18:00")
        
        # Invalid time formats
        with pytest.raises(ValueError):
            SchedulingSettings(business_hours_start="9:00")  # Missing leading zero
        
        with pytest.raises(ValueError):
            SchedulingSettings(business_hours_end="25:00")  # Invalid hour


class TestPWSettings:
    """Test composite PWSettings model"""
    
    def test_default_complete_settings(self):
        """Test default complete settings are valid"""
        settings = PWSettings()
        
        assert isinstance(settings.pricing, PricingSettings)
        assert isinstance(settings.weather, WeatherSettings)
        assert isinstance(settings.dm, DMSettings)
        assert isinstance(settings.scheduling, SchedulingSettings)
        
        # Verify all nested settings are properly initialized
        assert settings.pricing.minimum_job_price == 150.0
        assert settings.weather.auto_reschedule_enabled is True
        assert settings.dm.auto_response_enabled is True
        assert settings.scheduling.max_jobs_per_day == 6
    
    def test_custom_settings_override(self):
        """Test that custom settings override defaults"""
        custom_pricing = PricingSettings(minimum_job_price=200.0)
        custom_weather = WeatherSettings(auto_reschedule_enabled=False)
        
        settings = PWSettings(
            pricing=custom_pricing,
            weather=custom_weather
        )
        
        assert settings.pricing.minimum_job_price == 200.0
        assert settings.weather.auto_reschedule_enabled is False
        # DM and scheduling should use defaults
        assert settings.dm.auto_response_enabled is True
        assert settings.scheduling.max_jobs_per_day == 6


class TestSettingsResolver:
    """Test SettingsResolver functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_db = Mock(spec=Session)
        self.resolver = SettingsResolver(self.mock_db, cache_ttl_seconds=60)
        
        # Mock Redis to avoid external dependencies
        self.redis_mock = MagicMock()
        
    def test_cache_key_generation(self):
        """Test cache key generation for different scenarios"""
        # Organization only
        key1 = self.resolver._get_cache_key("org123")
        assert key1 == "pw_settings:org:org123"
        
        # Organization + user
        key2 = self.resolver._get_cache_key("org123", user_id=456)
        assert key2 == "pw_settings:org:org123:user:456"
        
        # Full hierarchy
        key3 = self.resolver._get_cache_key("org123", user_id=456, team_id="team789", integration_id="int101")
        expected = "pw_settings:org:org123:team:team789:integration:int101:user:456"
        assert key3 == expected
    
    def test_settings_merge_hierarchy(self):
        """Test hierarchical merging of settings"""
        base_settings = {"pricing": {"minimum_job_price": 100.0}}
        override_settings = {"pricing": {"minimum_job_price": 200.0, "soft_wash_multiplier": 1.5}}
        
        merged = self.resolver._merge_settings_dicts(base_settings, override_settings)
        
        assert merged["pricing"]["minimum_job_price"] == 200.0  # Overridden
        assert merged["pricing"]["soft_wash_multiplier"] == 1.5  # Added
    
    def test_deep_merge_nested_settings(self):
        """Test deep merging of nested settings"""
        base = {
            "pricing": {
                "base_rates": {"concrete": 0.15, "brick": 0.18},
                "minimum_job_price": 150.0
            }
        }
        override = {
            "pricing": {
                "base_rates": {"concrete": 0.20},  # Override only concrete
                "travel_rate_per_mile": 3.0  # Add new field
            }
        }
        
        merged = self.resolver._merge_settings_dicts(base, override)
        
        assert merged["pricing"]["base_rates"]["concrete"] == 0.20  # Overridden
        assert merged["pricing"]["base_rates"]["brick"] == 0.18  # Preserved
        assert merged["pricing"]["minimum_job_price"] == 150.0  # Preserved
        assert merged["pricing"]["travel_rate_per_mile"] == 3.0  # Added
    
    def test_settings_validation_with_invalid_data(self):
        """Test that invalid settings return defaults"""
        invalid_settings = {
            "pricing": {
                "minimum_job_price": -100.0  # Invalid negative price
            }
        }
        
        validated = self.resolver._validate_settings(invalid_settings)
        
        # Should return default settings when validation fails
        assert isinstance(validated, PWSettings)
        assert validated.pricing.minimum_job_price == 150.0  # Default value
    
    def test_get_settings_with_mocked_entities(self):
        """Test get_settings with mocked database entities"""
        # Mock organization
        mock_org = Mock()
        mock_org.settings = {
            "pricing": {"minimum_job_price": 175.0}
        }
        
        # Mock user
        mock_user = Mock()
        mock_user.plan = None
        
        # Mock user settings
        mock_user_settings = Mock()
        mock_user_settings.auto_response_enabled = True
        mock_user_settings.auto_response_delay_minutes = 5
        mock_user_settings.business_hours_start = "09:00"
        mock_user_settings.business_hours_end = "18:00"
        mock_user_settings.business_days = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        
        # Set up database mocks
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_user,  # User query
            mock_org,   # Organization query
            mock_user_settings  # UserSettings query
        ]
        
        # Mock Redis cache miss
        with patch('backend.services.settings_resolver.REDIS_AVAILABLE', False):
            settings = self.resolver.get_settings(
                org_id="org123",
                user_id=456
            )
        
        # Verify settings were merged properly
        assert isinstance(settings, PWSettings)
        assert settings.pricing.minimum_job_price == 175.0  # From organization
        assert settings.dm.auto_response_enabled is True  # From user settings
        assert settings.dm.response_delay_minutes == 5  # From user settings
        assert settings.scheduling.business_hours_start == "09:00"  # From user settings
    
    @patch('backend.services.settings_resolver.redis_client')
    @patch('backend.services.settings_resolver.REDIS_AVAILABLE', True)
    def test_cache_hit(self, mock_redis):
        """Test cache hit behavior"""
        cached_data = {
            "pricing": {"minimum_job_price": 200.0},
            "weather": {"auto_reschedule_enabled": False},
            "dm": {"auto_response_enabled": True},
            "scheduling": {"max_jobs_per_day": 8}
        }
        
        mock_redis.get.return_value = json.dumps(cached_data)
        
        settings = self.resolver.get_settings("org123", user_id=456)
        
        assert isinstance(settings, PWSettings)
        assert settings.pricing.minimum_job_price == 200.0
        assert settings.weather.auto_reschedule_enabled is False
        assert settings.scheduling.max_jobs_per_day == 8
        
        mock_redis.get.assert_called_once()
    
    @patch('backend.services.settings_resolver.redis_client')
    @patch('backend.services.settings_resolver.REDIS_AVAILABLE', True)
    def test_cache_invalidation(self, mock_redis):
        """Test cache invalidation"""
        mock_redis.scan_iter.return_value = [
            "pw_settings:org:org123:user:456",
            "pw_settings:org:org123:user:789"
        ]
        
        self.resolver.invalidate_cache("org123")
        
        # Verify version increment and key deletion
        mock_redis.incr.assert_called_once_with("pw_settings_version:org:org123")
        assert mock_redis.delete.call_count == 2  # Two keys deleted
    
    def test_get_namespace_settings(self):
        """Test namespace-specific settings access"""
        # Mock full settings
        mock_full_settings = PWSettings()
        
        with patch.object(self.resolver, 'get_settings', return_value=mock_full_settings):
            pricing = self.resolver.get_namespace_settings("org123", SettingsNamespace.PRICING)
            weather = self.resolver.get_namespace_settings("org123", SettingsNamespace.WEATHER)
            dm = self.resolver.get_namespace_settings("org123", SettingsNamespace.DM)
            scheduling = self.resolver.get_namespace_settings("org123", SettingsNamespace.SCHEDULING)
        
        assert isinstance(pricing, PricingSettings)
        assert isinstance(weather, WeatherSettings)
        assert isinstance(dm, DMSettings)
        assert isinstance(scheduling, SchedulingSettings)
        
        # Test invalid namespace
        with pytest.raises(ValueError, match="Unknown namespace"):
            self.resolver.get_namespace_settings("org123", "invalid_namespace")
    
    def test_extract_user_namespace_settings(self):
        """Test extraction of namespace settings from UserSetting model"""
        mock_user_settings = Mock()
        mock_user_settings.auto_response_enabled = True
        mock_user_settings.auto_response_delay_minutes = 3
        mock_user_settings.business_hours_start = "08:30"
        mock_user_settings.business_hours_end = "17:30"
        mock_user_settings.business_days = ["monday", "tuesday", "wednesday"]
        
        # Test DM namespace extraction
        dm_settings = self.resolver._extract_user_namespace_settings(
            mock_user_settings, SettingsNamespace.DM
        )
        assert dm_settings["auto_response_enabled"] is True
        assert dm_settings["response_delay_minutes"] == 3
        
        # Test scheduling namespace extraction
        scheduling_settings = self.resolver._extract_user_namespace_settings(
            mock_user_settings, SettingsNamespace.SCHEDULING
        )
        assert scheduling_settings["business_hours_start"] == "08:30"
        assert scheduling_settings["business_hours_end"] == "17:30"
        assert scheduling_settings["working_days"] == ["monday", "tuesday", "wednesday"]
        
        # Test pricing namespace (should return empty for now)
        pricing_settings = self.resolver._extract_user_namespace_settings(
            mock_user_settings, SettingsNamespace.PRICING
        )
        assert pricing_settings == {}


class TestConvenienceFunctions:
    """Test convenience functions for namespace access"""
    
    def setup_method(self):
        self.mock_db = Mock(spec=Session)
    
    @patch('backend.services.settings_resolver.SettingsResolver')
    def test_get_pricing_settings(self, mock_resolver_class):
        """Test get_pricing_settings convenience function"""
        mock_resolver = Mock()
        mock_resolver.get_namespace_settings.return_value = PricingSettings()
        mock_resolver_class.return_value = mock_resolver
        
        result = get_pricing_settings(self.mock_db, "org123", user_id=456)
        
        assert isinstance(result, PricingSettings)
        mock_resolver.get_namespace_settings.assert_called_once_with(
            "org123", SettingsNamespace.PRICING, 456
        )
    
    @patch('backend.services.settings_resolver.SettingsResolver')
    def test_get_weather_settings(self, mock_resolver_class):
        """Test get_weather_settings convenience function"""
        mock_resolver = Mock()
        mock_resolver.get_namespace_settings.return_value = WeatherSettings()
        mock_resolver_class.return_value = mock_resolver
        
        result = get_weather_settings(self.mock_db, "org123")
        
        assert isinstance(result, WeatherSettings)
        mock_resolver.get_namespace_settings.assert_called_once_with(
            "org123", SettingsNamespace.WEATHER, None
        )
    
    @patch('backend.services.settings_resolver.SettingsResolver')
    def test_get_dm_settings(self, mock_resolver_class):
        """Test get_dm_settings convenience function"""
        mock_resolver = Mock()
        mock_resolver.get_namespace_settings.return_value = DMSettings()
        mock_resolver_class.return_value = mock_resolver
        
        result = get_dm_settings(self.mock_db, "org123", user_id=789)
        
        assert isinstance(result, DMSettings)
        mock_resolver.get_namespace_settings.assert_called_once_with(
            "org123", SettingsNamespace.DM, 789
        )
    
    @patch('backend.services.settings_resolver.SettingsResolver')
    def test_get_scheduling_settings(self, mock_resolver_class):
        """Test get_scheduling_settings convenience function"""
        mock_resolver = Mock()
        mock_resolver.get_namespace_settings.return_value = SchedulingSettings()
        mock_resolver_class.return_value = mock_resolver
        
        result = get_scheduling_settings(self.mock_db, "org123")
        
        assert isinstance(result, SchedulingSettings)
        mock_resolver.get_namespace_settings.assert_called_once_with(
            "org123", SettingsNamespace.SCHEDULING, None
        )
    
    def test_create_settings_resolver(self):
        """Test settings resolver factory function"""
        resolver = create_settings_resolver(self.mock_db)
        
        assert isinstance(resolver, SettingsResolver)
        assert resolver.db == self.mock_db
        assert resolver.cache_ttl == 300  # Default TTL


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def setup_method(self):
        self.mock_db = Mock(spec=Session)
        self.resolver = SettingsResolver(self.mock_db)
    
    def test_missing_organization_returns_defaults(self):
        """Test that missing organization returns default settings"""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with patch('backend.services.settings_resolver.REDIS_AVAILABLE', False):
            settings = self.resolver.get_settings("nonexistent_org")
        
        # Should return default settings
        assert isinstance(settings, PWSettings)
        assert settings.pricing.minimum_job_price == 150.0  # Default
    
    def test_database_error_returns_defaults(self):
        """Test that database errors return default settings"""
        self.mock_db.query.side_effect = Exception("Database connection error")
        
        with patch('backend.services.settings_resolver.REDIS_AVAILABLE', False):
            settings = self.resolver.get_settings("org123", user_id=456)
        
        # Should return default settings on error
        assert isinstance(settings, PWSettings)
        assert settings.pricing.minimum_job_price == 150.0  # Default
    
    @patch('backend.services.settings_resolver.redis_client')
    @patch('backend.services.settings_resolver.REDIS_AVAILABLE', True)
    def test_cache_error_falls_back_to_db(self, mock_redis):
        """Test that cache errors fall back to database"""
        mock_redis.get.side_effect = Exception("Redis connection error")
        
        # Mock successful database query
        mock_org = Mock()
        mock_org.settings = {"pricing": {"minimum_job_price": 180.0}}
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # User query
            mock_org,  # Organization query
            None   # UserSettings query
        ]
        
        settings = self.resolver.get_settings("org123")
        
        # Should still get organization settings despite cache error
        assert settings.pricing.minimum_job_price == 180.0
    
    def test_malformed_entity_settings_handled(self):
        """Test that malformed entity settings are handled gracefully"""
        # Mock organization with malformed settings
        mock_org = Mock()
        mock_org.settings = "not_a_dict"  # Invalid settings format
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_org
        
        with patch('backend.services.settings_resolver.REDIS_AVAILABLE', False):
            # Should not raise an exception
            settings = self.resolver.get_settings("org123")
            assert isinstance(settings, PWSettings)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])