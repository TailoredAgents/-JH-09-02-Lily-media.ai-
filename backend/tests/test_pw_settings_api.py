"""
Unit tests for PW-SETTINGS-ADD-001: Pressure Washing Settings API

Tests cover:
- Request validation for all namespaces
- GET/PUT endpoint functionality
- Cache invalidation behavior
- Audit logging
- Error handling and edge cases
- Multi-tenant isolation
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.api.pw_settings import (
    router,
    PricingSettingsRequest,
    WeatherSettingsRequest, 
    DMSettingsRequest,
    SchedulingSettingsRequest,
    get_settings_resolver,
    log_settings_audit
)
from backend.middleware.tenant_context import TenantContext
from backend.auth.dependencies import AuthUser
from backend.services.settings_resolver import SettingsResolver, PWSettings
from backend.core.audit_logger import AuditEventType

# Create test app
app = FastAPI()
app.include_router(router)

class TestPricingSettingsValidation:
    """Test validation of pricing settings requests"""
    
    def test_valid_pricing_settings(self):
        """Test valid pricing settings request"""
        valid_data = {
            "base_rates": {
                "concrete": 0.18,
                "brick": 0.20
            },
            "minimum_job_price": 175.0,
            "soft_wash_multiplier": 1.4,
            "seasonal_multipliers": {
                "spring": 1.2,
                "summer": 1.0,
                "fall": 1.1,
                "winter": 0.8
            }
        }
        
        settings = PricingSettingsRequest(**valid_data)
        assert settings.minimum_job_price == 175.0
        assert settings.base_rates["concrete"] == 0.18
        assert len(settings.seasonal_multipliers) == 4
    
    def test_invalid_base_rates_surface_type(self):
        """Test rejection of invalid surface types"""
        invalid_data = {
            "base_rates": {
                "invalid_surface": 0.15  # Invalid surface type
            }
        }
        
        with pytest.raises(ValueError, match="Invalid surface type"):
            PricingSettingsRequest(**invalid_data)
    
    def test_negative_base_rates(self):
        """Test rejection of negative base rates"""
        invalid_data = {
            "base_rates": {
                "concrete": -0.10  # Negative rate
            }
        }
        
        with pytest.raises(ValueError, match="Base rate for .* must be positive"):
            PricingSettingsRequest(**invalid_data)
    
    def test_incomplete_seasonal_multipliers(self):
        """Test rejection of incomplete seasonal multipliers"""
        invalid_data = {
            "seasonal_multipliers": {
                "spring": 1.2,
                "summer": 1.0
                # Missing fall and winter
            }
        }
        
        with pytest.raises(ValueError, match="Missing required seasons"):
            PricingSettingsRequest(**invalid_data)
    
    def test_negative_seasonal_multipliers(self):
        """Test rejection of negative seasonal multipliers"""
        invalid_data = {
            "seasonal_multipliers": {
                "spring": 1.2,
                "summer": 1.0,
                "fall": 1.1,
                "winter": -0.5  # Negative multiplier
            }
        }
        
        with pytest.raises(ValueError, match="Seasonal multiplier for .* must be positive"):
            PricingSettingsRequest(**invalid_data)
    
    def test_field_constraints(self):
        """Test field validation constraints"""
        # Test minimum job price constraints
        with pytest.raises(ValueError):
            PricingSettingsRequest(minimum_job_price=25.0)  # Below minimum
        
        with pytest.raises(ValueError):
            PricingSettingsRequest(minimum_job_price=1500.0)  # Above maximum
        
        # Test soft wash multiplier constraints
        with pytest.raises(ValueError):
            PricingSettingsRequest(soft_wash_multiplier=0.5)  # Below minimum
        
        with pytest.raises(ValueError):
            PricingSettingsRequest(soft_wash_multiplier=5.0)  # Above maximum


class TestWeatherSettingsValidation:
    """Test validation of weather settings requests"""
    
    def test_valid_weather_settings(self):
        """Test valid weather settings request"""
        valid_data = {
            "rain_delay_threshold_inches": 0.2,
            "max_wind_speed_roof": 12.0,
            "max_wind_speed_general": 20.0,
            "min_temperature_f": 40.0,
            "max_temperature_f": 85.0,
            "auto_reschedule_enabled": True,
            "advance_notice_hours": 48,
            "weather_severity_actions": {
                "light": "proceed",
                "moderate": "reschedule",
                "severe": "cancel_day"
            }
        }
        
        settings = WeatherSettingsRequest(**valid_data)
        assert settings.rain_delay_threshold_inches == 0.2
        assert settings.auto_reschedule_enabled is True
        assert len(settings.weather_severity_actions) == 3
    
    def test_invalid_weather_severity(self):
        """Test rejection of invalid weather severity levels"""
        invalid_data = {
            "weather_severity_actions": {
                "invalid_severity": "proceed"  # Invalid severity
            }
        }
        
        with pytest.raises(ValueError, match="Invalid weather severity"):
            WeatherSettingsRequest(**invalid_data)
    
    def test_invalid_severity_actions(self):
        """Test rejection of invalid severity actions"""
        invalid_data = {
            "weather_severity_actions": {
                "light": "invalid_action"  # Invalid action
            }
        }
        
        with pytest.raises(ValueError, match="Invalid action"):
            WeatherSettingsRequest(**invalid_data)
    
    def test_field_constraints(self):
        """Test weather field validation constraints"""
        # Test rain threshold constraints
        with pytest.raises(ValueError):
            WeatherSettingsRequest(rain_delay_threshold_inches=-0.1)  # Below minimum
        
        with pytest.raises(ValueError):
            WeatherSettingsRequest(rain_delay_threshold_inches=3.0)  # Above maximum
        
        # Test wind speed constraints
        with pytest.raises(ValueError):
            WeatherSettingsRequest(max_wind_speed_roof=3.0)  # Below minimum
        
        with pytest.raises(ValueError):
            WeatherSettingsRequest(advance_notice_hours=200)  # Above maximum


class TestDMSettingsValidation:
    """Test validation of DM settings requests"""
    
    def test_valid_dm_settings(self):
        """Test valid DM settings request"""
        valid_data = {
            "auto_response_enabled": True,
            "response_delay_minutes": 5,
            "require_photos_for_quote": True,
            "max_photos_per_inquiry": 8,
            "ballpark_accuracy_margin": 0.30,
            "qualification_questions": [
                "What type of surface?",
                "Approximate size?",
                "Preferred timing?"
            ],
            "quiet_hours": {
                "start": "22:00",
                "end": "07:00"
            }
        }
        
        settings = DMSettingsRequest(**valid_data)
        assert settings.auto_response_enabled is True
        assert len(settings.qualification_questions) == 3
        assert settings.quiet_hours["start"] == "22:00"
    
    def test_invalid_qualification_questions(self):
        """Test rejection of invalid qualification questions"""
        # Empty question
        invalid_data = {
            "qualification_questions": ["", "Valid question"]
        }
        
        with pytest.raises(ValueError, match="Qualification questions cannot be empty"):
            DMSettingsRequest(**invalid_data)
        
        # Too long question
        invalid_data = {
            "qualification_questions": ["x" * 250]  # Over 200 character limit
        }
        
        with pytest.raises(ValueError, match="Qualification questions must be under 200 characters"):
            DMSettingsRequest(**invalid_data)
    
    def test_invalid_quiet_hours(self):
        """Test rejection of invalid quiet hours"""
        # Missing end time
        invalid_data = {
            "quiet_hours": {
                "start": "22:00"
                # Missing 'end'
            }
        }
        
        with pytest.raises(ValueError, match="Quiet hours must include 'start' and 'end' times"):
            DMSettingsRequest(**invalid_data)
        
        # Invalid time format
        invalid_data = {
            "quiet_hours": {
                "start": "25:00",  # Invalid hour
                "end": "07:00"
            }
        }
        
        with pytest.raises(ValueError, match="Invalid time format"):
            DMSettingsRequest(**invalid_data)
    
    def test_field_constraints(self):
        """Test DM field validation constraints"""
        # Test response delay constraints
        with pytest.raises(ValueError):
            DMSettingsRequest(response_delay_minutes=70)  # Above maximum
        
        # Test photos constraints
        with pytest.raises(ValueError):
            DMSettingsRequest(max_photos_per_inquiry=25)  # Above maximum
        
        # Test accuracy margin constraints
        with pytest.raises(ValueError):
            DMSettingsRequest(ballpark_accuracy_margin=1.5)  # Above maximum


class TestSchedulingSettingsValidation:
    """Test validation of scheduling settings requests"""
    
    def test_valid_scheduling_settings(self):
        """Test valid scheduling settings request"""
        valid_data = {
            "business_hours_start": "08:30",
            "business_hours_end": "17:30",
            "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "default_job_duration_hours": 2.5,
            "buffer_time_minutes": 45,
            "max_jobs_per_day": 8,
            "allow_rush_jobs": True,
            "rush_job_multiplier": 1.8
        }
        
        settings = SchedulingSettingsRequest(**valid_data)
        assert settings.business_hours_start == "08:30"
        assert len(settings.working_days) == 5
        assert settings.default_job_duration_hours == 2.5
    
    def test_invalid_working_days(self):
        """Test rejection of invalid working days"""
        invalid_data = {
            "working_days": ["monday", "invalid_day"]
        }
        
        with pytest.raises(ValueError, match="Invalid working day"):
            SchedulingSettingsRequest(**invalid_data)
    
    def test_invalid_time_format(self):
        """Test rejection of invalid time formats"""
        # Missing leading zero
        with pytest.raises(ValueError):
            SchedulingSettingsRequest(business_hours_start="9:00")
        
        # Invalid hour
        with pytest.raises(ValueError):
            SchedulingSettingsRequest(business_hours_end="25:00")
    
    def test_case_insensitive_working_days(self):
        """Test that working days are converted to lowercase"""
        data = {
            "working_days": ["MONDAY", "Tuesday", "wednesday"]
        }
        
        settings = SchedulingSettingsRequest(**data)
        assert settings.working_days == ["monday", "tuesday", "wednesday"]


class TestSettingsAPIEndpoints:
    """Test the actual API endpoints"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
        self.mock_tenant_context = Mock(spec=TenantContext)
        self.mock_tenant_context.organization_id = "org_123"
        self.mock_tenant_context.user = Mock(spec=AuthUser)
        self.mock_tenant_context.user.user_id = "456"
        self.mock_tenant_context.role = "admin"
        
        self.mock_resolver = Mock(spec=SettingsResolver)
        self.mock_db = Mock(spec=Session)
        
        # Mock organization
        self.mock_org = Mock()
        self.mock_org.id = "org_123"
        self.mock_org.settings = {}
    
    @patch('backend.api.pw_settings.get_tenant_context')
    @patch('backend.api.pw_settings.get_settings_resolver')
    def test_get_all_settings(self, mock_get_resolver, mock_get_tenant):
        """Test GET /api/pw-settings/ endpoint"""
        mock_get_tenant.return_value = self.mock_tenant_context
        mock_get_resolver.return_value = self.mock_resolver
        
        # Mock settings response
        mock_settings = PWSettings()
        self.mock_resolver.get_settings.return_value = mock_settings
        
        response = self.client.get("/api/pw-settings/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "organization_id" in data
        assert "pricing" in data
        assert "weather" in data
        assert "dm" in data
        assert "scheduling" in data
        assert "last_updated" in data
        
        # Verify resolver was called correctly
        self.mock_resolver.get_settings.assert_called_once_with(
            org_id="org_123",
            user_id=456
        )
    
    @patch('backend.api.pw_settings.get_tenant_context')
    @patch('backend.api.pw_settings.get_settings_resolver')
    def test_get_pricing_settings(self, mock_get_resolver, mock_get_tenant):
        """Test GET /api/pw-settings/pricing endpoint"""
        mock_get_tenant.return_value = self.mock_tenant_context
        mock_get_resolver.return_value = self.mock_resolver
        
        # Mock pricing settings response
        from backend.services.settings_resolver import PricingSettings
        mock_pricing = PricingSettings()
        self.mock_resolver.get_namespace_settings.return_value = mock_pricing
        
        response = self.client.get("/api/pw-settings/pricing")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["namespace"] == "pricing"
        assert "settings" in data
        assert "organization_id" in data
        
        # Verify resolver was called correctly  
        from backend.services.settings_resolver import SettingsNamespace
        self.mock_resolver.get_namespace_settings.assert_called_once_with(
            org_id="org_123",
            namespace=SettingsNamespace.PRICING,
            user_id=456
        )
    
    @patch('backend.api.pw_settings.get_tenant_context')
    @patch('backend.api.pw_settings.get_settings_resolver')
    @patch('backend.api.pw_settings.get_db')
    @patch('backend.api.pw_settings.log_settings_audit')
    def test_update_pricing_settings(self, mock_log_audit, mock_get_db, mock_get_resolver, mock_get_tenant):
        """Test PUT /api/pw-settings/pricing endpoint"""
        mock_get_tenant.return_value = self.mock_tenant_context
        mock_get_resolver.return_value = self.mock_resolver
        mock_get_db.return_value = self.mock_db
        mock_log_audit.return_value = AsyncMock()
        
        # Mock database query
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_org
        
        valid_update = {
            "minimum_job_price": 200.0,
            "base_rates": {
                "concrete": 0.20
            }
        }
        
        response = self.client.put("/api/pw-settings/pricing", json=valid_update)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["namespace"] == "pricing"
        assert data["organization_id"] == "org_123"
        assert data["cache_invalidated"] is True
        assert data["audit_logged"] is True
        assert "minimum_job_price" in data["changes_applied"]
        
        # Verify database operations
        self.mock_db.commit.assert_called_once()
        
        # Verify cache invalidation
        self.mock_resolver.invalidate_cache.assert_called_once_with("org_123")
        
        # Verify audit logging was attempted
        mock_log_audit.assert_called_once()
    
    @patch('backend.api.pw_settings.get_tenant_context')
    @patch('backend.api.pw_settings.get_settings_resolver')
    @patch('backend.api.pw_settings.get_db')
    def test_update_settings_validation_error(self, mock_get_db, mock_get_resolver, mock_get_tenant):
        """Test PUT endpoint with validation errors"""
        mock_get_tenant.return_value = self.mock_tenant_context
        mock_get_resolver.return_value = self.mock_resolver
        mock_get_db.return_value = self.mock_db
        
        # Invalid update data (negative price)
        invalid_update = {
            "minimum_job_price": -100.0
        }
        
        response = self.client.put("/api/pw-settings/pricing", json=invalid_update)
        
        # Should return validation error
        assert response.status_code == 422  # Validation error
    
    @patch('backend.api.pw_settings.get_tenant_context')
    @patch('backend.api.pw_settings.get_settings_resolver')
    @patch('backend.api.pw_settings.get_db')
    def test_update_settings_organization_not_found(self, mock_get_db, mock_get_resolver, mock_get_tenant):
        """Test PUT endpoint when organization is not found"""
        mock_get_tenant.return_value = self.mock_tenant_context
        mock_get_resolver.return_value = self.mock_resolver
        mock_get_db.return_value = self.mock_db
        
        # Mock organization not found
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        valid_update = {
            "minimum_job_price": 200.0
        }
        
        response = self.client.put("/api/pw-settings/pricing", json=valid_update)
        
        assert response.status_code == 404
        data = response.json()
        assert "Organization not found" in data["detail"]
    
    @patch('backend.api.pw_settings.get_tenant_context')
    @patch('backend.api.pw_settings.get_settings_resolver')
    @patch('backend.api.pw_settings.get_db')
    def test_update_settings_database_error(self, mock_get_db, mock_get_resolver, mock_get_tenant):
        """Test PUT endpoint with database error"""
        mock_get_tenant.return_value = self.mock_tenant_context
        mock_get_resolver.return_value = self.mock_resolver
        mock_get_db.return_value = self.mock_db
        
        # Mock database error
        self.mock_db.query.side_effect = Exception("Database connection error")
        
        valid_update = {
            "minimum_job_price": 200.0
        }
        
        response = self.client.put("/api/pw-settings/pricing", json=valid_update)
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to update pricing settings" in data["detail"]
        
        # Verify rollback was called
        self.mock_db.rollback.assert_called_once()


class TestCacheInvalidation:
    """Test cache invalidation behavior"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_resolver = Mock(spec=SettingsResolver)
        self.client = TestClient(app)
        self.mock_tenant_context = Mock(spec=TenantContext)
        self.mock_tenant_context.organization_id = "org_123"
        self.mock_tenant_context.user = Mock(spec=AuthUser)
        self.mock_tenant_context.user.user_id = "456"
    
    @patch('backend.api.pw_settings.get_tenant_context')
    @patch('backend.api.pw_settings.get_settings_resolver')
    def test_manual_cache_invalidation(self, mock_get_resolver, mock_get_tenant):
        """Test manual cache invalidation endpoint"""
        mock_get_tenant.return_value = self.mock_tenant_context
        mock_get_resolver.return_value = self.mock_resolver
        
        response = self.client.post("/api/pw-settings/cache/invalidate")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "cache invalidated" in data["message"]
        
        # Verify cache invalidation was called
        self.mock_resolver.invalidate_cache.assert_called_once_with("org_123")
    
    @patch('backend.api.pw_settings.get_tenant_context')
    @patch('backend.api.pw_settings.get_settings_resolver')
    def test_cache_invalidation_on_settings_update(self, mock_get_resolver, mock_get_tenant):
        """Test that cache is invalidated on settings updates"""
        mock_get_tenant.return_value = self.mock_tenant_context
        mock_get_resolver.return_value = self.mock_resolver
        
        # This is tested in the update endpoints above
        # Cache invalidation should happen automatically on PUT requests
        pass


class TestAuditLogging:
    """Test audit logging functionality"""
    
    @patch('backend.api.pw_settings.log_settings_audit')
    async def test_audit_logging_function(self, mock_log_audit):
        """Test the audit logging helper function"""
        mock_tenant_context = Mock(spec=TenantContext)
        mock_tenant_context.user = Mock(spec=AuthUser)
        mock_tenant_context.user.user_id = "456"
        mock_tenant_context.organization_id = "org_123"
        mock_tenant_context.role = "admin"
        
        mock_db = Mock()
        changes = {"minimum_job_price": 200.0}
        
        await log_settings_audit(
            namespace="pricing",
            action="update", 
            tenant_context=mock_tenant_context,
            changes=changes,
            db=mock_db
        )
        
        # Verify audit logging was called with correct parameters
        mock_log_audit.assert_called_once_with(
            event_type=AuditEventType.SETTINGS_UPDATED,
            user_id=456,
            organization_id="org_123",
            details={
                "namespace": "pricing",
                "action": "update",
                "changes": changes,
                "role": "admin"
            },
            db=mock_db
        )


class TestUtilityEndpoints:
    """Test utility endpoints"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
    
    def test_get_default_settings(self):
        """Test GET /api/pw-settings/defaults endpoint"""
        response = self.client.get("/api/pw-settings/defaults")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "pricing" in data
        assert "weather" in data
        assert "dm" in data
        assert "scheduling" in data
        
        # Verify pricing defaults
        pricing = data["pricing"]
        assert "minimum_job_price" in pricing
        assert "base_rates" in pricing
        assert "seasonal_multipliers" in pricing
    
    def test_get_settings_schema(self):
        """Test GET /api/pw-settings/schema/{namespace} endpoint"""
        # Test pricing schema
        response = self.client.get("/api/pw-settings/schema/pricing")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["namespace"] == "pricing"
        assert "schema" in data
        assert "properties" in data["schema"]
        
        # Test invalid namespace
        response = self.client.get("/api/pw-settings/schema/invalid")
        
        assert response.status_code == 400
        data = response.json()
        assert "Unknown namespace" in data["detail"]


class TestMultiTenantIsolation:
    """Test multi-tenant isolation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
    
    @patch('backend.api.pw_settings.get_tenant_context')
    def test_tenant_context_required(self, mock_get_tenant):
        """Test that tenant context is required for all endpoints"""
        # Mock tenant context dependency failure
        mock_get_tenant.side_effect = HTTPException(
            status_code=400,
            detail="Missing X-Organization-ID header"
        )
        
        response = self.client.get("/api/pw-settings/")
        
        assert response.status_code == 400
        data = response.json()
        assert "X-Organization-ID" in data["detail"]
    
    @patch('backend.api.pw_settings.get_tenant_context')
    @patch('backend.api.pw_settings.get_settings_resolver')
    def test_organization_isolation(self, mock_get_resolver, mock_get_tenant):
        """Test that settings are isolated by organization"""
        mock_tenant_context = Mock(spec=TenantContext)
        mock_tenant_context.organization_id = "org_456"  # Different org
        mock_tenant_context.user = Mock(spec=AuthUser)
        mock_tenant_context.user.user_id = "789"
        
        mock_get_tenant.return_value = mock_tenant_context
        mock_resolver = Mock(spec=SettingsResolver)
        mock_get_resolver.return_value = mock_resolver
        
        # Mock settings response
        mock_settings = PWSettings()
        mock_resolver.get_settings.return_value = mock_settings
        
        response = self.client.get("/api/pw-settings/")
        
        assert response.status_code == 200
        
        # Verify resolver was called with correct organization ID
        mock_resolver.get_settings.assert_called_once_with(
            org_id="org_456",  # Should use the correct org ID
            user_id=789
        )


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
        self.mock_tenant_context = Mock(spec=TenantContext)
        self.mock_tenant_context.organization_id = "org_123"
        self.mock_tenant_context.user = Mock(spec=AuthUser)
        self.mock_tenant_context.user.user_id = "456"
    
    @patch('backend.api.pw_settings.get_tenant_context')
    @patch('backend.api.pw_settings.get_settings_resolver')
    def test_resolver_error_handling(self, mock_get_resolver, mock_get_tenant):
        """Test handling of resolver errors"""
        mock_get_tenant.return_value = self.mock_tenant_context
        mock_resolver = Mock(spec=SettingsResolver)
        mock_get_resolver.return_value = mock_resolver
        
        # Mock resolver error
        mock_resolver.get_settings.side_effect = Exception("Resolver error")
        
        response = self.client.get("/api/pw-settings/")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve settings" in data["detail"]
    
    @patch('backend.api.pw_settings.get_tenant_context')
    @patch('backend.api.pw_settings.get_settings_resolver')
    def test_cache_invalidation_error_handling(self, mock_get_resolver, mock_get_tenant):
        """Test handling of cache invalidation errors"""
        mock_get_tenant.return_value = self.mock_tenant_context
        mock_resolver = Mock(spec=SettingsResolver)
        mock_get_resolver.return_value = mock_resolver
        
        # Mock cache invalidation error
        mock_resolver.invalidate_cache.side_effect = Exception("Cache error")
        
        response = self.client.post("/api/pw-settings/cache/invalidate")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to invalidate settings cache" in data["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])