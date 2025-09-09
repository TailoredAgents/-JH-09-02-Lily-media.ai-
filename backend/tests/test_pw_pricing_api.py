"""
Unit tests for pressure washing pricing API endpoints
"""

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch
import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.api.pw_pricing import router
from backend.db.models import User, Organization, PricingRule
from backend.services.pricing_service import PricingQuote


class TestPricingAPIModels:
    """Test Pydantic models for pricing API"""
    
    def test_surface_data_model(self):
        """Test SurfaceData model validation"""
        from backend.api.pw_pricing import SurfaceData
        
        # Valid surface data
        surface = SurfaceData(area=1000.0, difficulty="medium", condition="good")
        assert surface.area == 1000.0
        assert surface.difficulty == "medium"
        assert surface.condition == "good"
        
        # Test minimum area validation
        with pytest.raises(ValueError):
            SurfaceData(area=0.0)  # Should fail - area must be > 0
    
    def test_location_data_model(self):
        """Test LocationData model validation"""
        from backend.api.pw_pricing import LocationData
        
        location = LocationData(
            address="123 Main St",
            distance_miles=10.5,
            zip_code="12345"
        )
        assert location.address == "123 Main St"
        assert location.distance_miles == 10.5
        assert location.zip_code == "12345"
        
        # Test distance validation
        with pytest.raises(ValueError):
            LocationData(distance_miles=-1.0)  # Should fail - distance must be >= 0
    
    def test_quote_request_model(self):
        """Test QuoteRequest model validation"""
        from backend.api.pw_pricing import QuoteRequest, SurfaceData, LocationData
        
        request_data = {
            "service_types": ["pressure_wash", "soft_wash"],
            "surfaces": {
                "driveway": {"area": 1000.0, "difficulty": "medium"},
                "roof": {"area": 1500.0, "condition": "good"}
            },
            "location": {
                "address": "123 Main St",
                "distance_miles": 10.0,
                "zip_code": "12345"
            },
            "preferred_date": "2025-06-15",
            "additional_services": ["window_cleaning"],
            "customer_tier": "premium",
            "rush_job": True,
            "metadata": {"source": "website"}
        }
        
        request = QuoteRequest(**request_data)
        assert len(request.service_types) == 2
        assert "pressure_wash" in request.service_types
        assert "driveway" in request.surfaces
        assert request.surfaces["driveway"].area == 1000.0
        assert request.preferred_date == date(2025, 6, 15)
        assert request.customer_tier == "premium"
        assert request.rush_job is True
        
        # Test minimum service types validation
        with pytest.raises(ValueError):
            QuoteRequest(service_types=[], surfaces={"deck": {"area": 500}})
    
    def test_pricing_rule_create_model(self):
        """Test PricingRuleCreate model validation"""
        from backend.api.pw_pricing import PricingRuleCreate
        
        rule_data = {
            "name": "Test Pricing Rule",
            "description": "Test rule description",
            "currency": "USD",
            "min_job_total": 150.00,
            "base_rates": {
                "pressure_wash": {
                    "surfaces": {"driveway": 0.15}
                }
            },
            "travel_settings": {
                "free_radius_miles": 10,
                "rate_per_mile": 2.50
            },
            "business_rules": {
                "tax_rate": 8.25
            }
        }
        
        rule = PricingRuleCreate(**rule_data)
        assert rule.name == "Test Pricing Rule"
        assert rule.currency == "USD"
        assert rule.min_job_total == Decimal('150.00')
        
        # Test currency validation
        with pytest.raises(ValueError):
            PricingRuleCreate(**{**rule_data, "currency": "INVALID"})


class TestPricingAPIEndpoints:
    """Test pricing API endpoints"""
    
    @pytest.fixture
    def mock_app(self):
        """Create test app with pricing router"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return app
    
    @pytest.fixture
    def client(self, mock_app):
        """Create test client"""
        return TestClient(mock_app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock current user"""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.is_active = True
        return user
    
    @pytest.fixture
    def mock_organization(self):
        """Mock organization"""
        org = Mock(spec=Organization)
        org.id = "org-123"
        org.name = "Test Organization"
        return org
    
    @pytest.fixture
    def mock_pricing_rule(self):
        """Mock pricing rule"""
        rule = Mock(spec=PricingRule)
        rule.id = 1
        rule.organization_id = "org-123"
        rule.name = "Test Pricing Rule"
        rule.currency = "USD"
        rule.min_job_total = Decimal('150.00')
        rule.base_rates = {"pressure_wash": {"surfaces": {"driveway": 0.15}}}
        rule.bundles = []
        rule.seasonal_modifiers = {}
        rule.travel_settings = {"free_radius_miles": 10, "rate_per_mile": 2.50}
        rule.additional_services = {}
        rule.business_rules = {"tax_rate": 8.25}
        rule.is_active = True
        rule.priority = 0
        rule.effective_from = None
        rule.effective_until = None
        rule.version = 1
        rule.created_by_id = 1
        rule.updated_by_id = None
        rule.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        rule.updated_at = None
        return rule
    
    @pytest.fixture
    def mock_dependencies(self, mock_user, mock_organization):
        """Mock FastAPI dependencies"""
        with patch('backend.api.pw_pricing.get_current_active_user') as mock_get_user, \
             patch('backend.api.pw_pricing.get_db') as mock_get_db, \
             patch('backend.api.pw_pricing.verify_organization_access') as mock_verify_org, \
             patch('backend.api.pw_pricing.require_permission') as mock_require_perm:
            
            mock_get_user.return_value = mock_user
            mock_get_db.return_value = Mock(spec=Session)
            mock_verify_org.return_value = mock_organization
            mock_require_perm.return_value = True
            
            yield {
                'get_user': mock_get_user,
                'get_db': mock_get_db,
                'verify_org': mock_verify_org,
                'require_perm': mock_require_perm
            }
    
    def test_compute_quote_success(self, client, mock_dependencies):
        """Test successful quote computation"""
        with patch('backend.api.pw_pricing.PricingService') as mock_service_class, \
             patch('backend.api.pw_pricing.SettingsResolver') as mock_resolver_class:
            
            # Mock pricing service and quote
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_resolver_class.return_value = Mock()
            
            mock_quote = PricingQuote()
            mock_quote.base_total = Decimal('400.00')
            mock_quote.total = Decimal('460.00')
            mock_quote.currency = "USD"
            mock_quote.breakdown = [{"type": "base_service", "amount": 400.00}]
            mock_quote.applied_rules = ["Test Rule"]
            mock_quote.warning_messages = []
            mock_quote.valid_until = datetime(2025, 7, 1, tzinfo=timezone.utc)
            
            mock_service.compute_quote.return_value = mock_quote
            
            # Make request
            request_data = {
                "service_types": ["pressure_wash"],
                "surfaces": {
                    "driveway": {"area": 1000.0}
                },
                "location": {"distance_miles": 5.0},
                "customer_tier": "standard"
            }
            
            response = client.post(
                "/api/v1/pricing/quote",
                json=request_data,
                headers={"X-Organization-ID": "org-123"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 460.00
            assert data["currency"] == "USD"
            assert len(data["breakdown"]) == 1
            assert len(data["applied_rules"]) == 1
    
    def test_compute_quote_missing_org_header(self, client, mock_dependencies):
        """Test quote computation without organization header"""
        request_data = {
            "service_types": ["pressure_wash"],
            "surfaces": {"driveway": {"area": 1000.0}}
        }
        
        response = client.post("/api/v1/pricing/quote", json=request_data)
        assert response.status_code == 400
        assert "X-Organization-ID header is required" in response.json()["detail"]
    
    def test_compute_quote_invalid_request(self, client, mock_dependencies):
        """Test quote computation with invalid request data"""
        request_data = {
            "service_types": [],  # Invalid - empty list
            "surfaces": {"driveway": {"area": 1000.0}}
        }
        
        response = client.post(
            "/api/v1/pricing/quote",
            json=request_data,
            headers={"X-Organization-ID": "org-123"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_compute_quote_no_pricing_rule(self, client, mock_dependencies):
        """Test quote computation when no pricing rule exists"""
        with patch('backend.api.pw_pricing.PricingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.compute_quote.side_effect = ValueError("No active pricing rules found")
            
            request_data = {
                "service_types": ["pressure_wash"],
                "surfaces": {"driveway": {"area": 1000.0}}
            }
            
            response = client.post(
                "/api/v1/pricing/quote",
                json=request_data,
                headers={"X-Organization-ID": "org-123"}
            )
            
            assert response.status_code == 400
            assert "No active pricing rules found" in response.json()["detail"]
    
    def test_create_pricing_rule_success(self, client, mock_dependencies, mock_pricing_rule):
        """Test successful pricing rule creation"""
        mock_db = mock_dependencies['get_db'].return_value
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock(side_effect=lambda rule: setattr(rule, 'id', 1))
        
        rule_data = {
            "name": "Test Pricing Rule",
            "currency": "USD",
            "min_job_total": 150.00,
            "base_rates": {
                "pressure_wash": {"surfaces": {"driveway": 0.15}}
            },
            "travel_settings": {"free_radius_miles": 10},
            "business_rules": {"tax_rate": 8.25}
        }
        
        with patch('backend.api.pw_pricing.PricingRule') as mock_rule_class:
            mock_rule_instance = mock_pricing_rule
            mock_rule_class.return_value = mock_rule_instance
            
            response = client.post(
                "/api/v1/pricing/rules",
                json=rule_data,
                headers={"X-Organization-ID": "org-123"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Test Pricing Rule"
            assert data["currency"] == "USD"
            assert data["organization_id"] == "org-123"
            
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
    
    def test_create_pricing_rule_database_error(self, client, mock_dependencies):
        """Test pricing rule creation with database error"""
        mock_db = mock_dependencies['get_db'].return_value
        mock_db.add = Mock()
        mock_db.commit = Mock(side_effect=Exception("Database error"))
        mock_db.rollback = Mock()
        
        rule_data = {
            "name": "Test Rule",
            "currency": "USD",
            "min_job_total": 150.00,
            "base_rates": {"pressure_wash": {"surfaces": {"driveway": 0.15}}},
            "travel_settings": {"free_radius_miles": 10},
            "business_rules": {"tax_rate": 8.25}
        }
        
        response = client.post(
            "/api/v1/pricing/rules",
            json=rule_data,
            headers={"X-Organization-ID": "org-123"}
        )
        
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]
        mock_db.rollback.assert_called_once()
    
    def test_list_pricing_rules_success(self, client, mock_dependencies, mock_pricing_rule):
        """Test successful pricing rules listing"""
        mock_db = mock_dependencies['get_db'].return_value
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_pricing_rule]
        
        response = client.get(
            "/api/v1/pricing/rules",
            headers={"X-Organization-ID": "org-123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Pricing Rule"
        assert data[0]["organization_id"] == "org-123"
    
    def test_list_pricing_rules_active_only(self, client, mock_dependencies, mock_pricing_rule):
        """Test pricing rules listing with active_only filter"""
        mock_db = mock_dependencies['get_db'].return_value
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_pricing_rule]
        
        response = client.get(
            "/api/v1/pricing/rules?active_only=true",
            headers={"X-Organization-ID": "org-123"}
        )
        
        assert response.status_code == 200
        # Verify that active filter was applied
        assert mock_query.filter.call_count >= 2  # org filter + active filter
    
    def test_get_pricing_rule_success(self, client, mock_dependencies, mock_pricing_rule):
        """Test successful pricing rule retrieval by ID"""
        mock_db = mock_dependencies['get_db'].return_value
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_pricing_rule
        
        response = client.get(
            "/api/v1/pricing/rules/1",
            headers={"X-Organization-ID": "org-123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Test Pricing Rule"
        assert data["organization_id"] == "org-123"
    
    def test_get_pricing_rule_not_found(self, client, mock_dependencies):
        """Test pricing rule retrieval when rule doesn't exist"""
        mock_db = mock_dependencies['get_db'].return_value
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        response = client.get(
            "/api/v1/pricing/rules/999",
            headers={"X-Organization-ID": "org-123"}
        )
        
        assert response.status_code == 404
        assert "Pricing rule not found" in response.json()["detail"]
    
    def test_organization_access_verification(self, client, mock_user):
        """Test organization access verification"""
        with patch('backend.api.pw_pricing.get_current_active_user') as mock_get_user, \
             patch('backend.api.pw_pricing.get_db') as mock_get_db, \
             patch('backend.api.pw_pricing.verify_organization_access') as mock_verify_org:
            
            mock_get_user.return_value = mock_user
            mock_get_db.return_value = Mock(spec=Session)
            mock_verify_org.side_effect = Exception("Organization not found")
            
            request_data = {
                "service_types": ["pressure_wash"],
                "surfaces": {"driveway": {"area": 1000.0}}
            }
            
            response = client.post(
                "/api/v1/pricing/quote",
                json=request_data,
                headers={"X-Organization-ID": "org-invalid"}
            )
            
            # Should propagate the exception from verify_organization_access
            assert response.status_code == 500
    
    def test_permission_requirements(self, client, mock_dependencies):
        """Test RBAC permission requirements"""
        # Mock permission check to fail
        mock_dependencies['require_perm'].side_effect = Exception("Insufficient permissions")
        
        request_data = {
            "service_types": ["pressure_wash"],
            "surfaces": {"driveway": {"area": 1000.0}}
        }
        
        response = client.post(
            "/api/v1/pricing/quote",
            json=request_data,
            headers={"X-Organization-ID": "org-123"}
        )
        
        # Should propagate the permission exception
        assert response.status_code == 500


class TestPricingAPIHelpers:
    """Test pricing API helper functions"""
    
    def test_get_organization_id_header(self):
        """Test organization ID header extraction"""
        from backend.api.pw_pricing import get_organization_id
        
        # Valid header
        org_id = get_organization_id("org-123")
        assert org_id == "org-123"
        
        # Missing header
        with pytest.raises(Exception):  # Should raise HTTPException
            get_organization_id(None)
    
    def test_verify_organization_access_success(self, mock_user):
        """Test successful organization access verification"""
        from backend.api.pw_pricing import verify_organization_access
        
        mock_org = Mock(spec=Organization)
        mock_org.id = "org-123"
        
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_org
        
        with patch('backend.api.pw_pricing.get_user_permissions') as mock_get_perms:
            mock_get_perms.return_value = ["pricing.quote", "pricing.rules.read"]
            
            result = verify_organization_access("org-123", mock_user, mock_db)
            assert result == mock_org
    
    def test_verify_organization_access_not_found(self, mock_user):
        """Test organization access when organization doesn't exist"""
        from backend.api.pw_pricing import verify_organization_access
        
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(Exception):  # Should raise HTTPException
            verify_organization_access("org-invalid", mock_user, mock_db)
    
    def test_verify_organization_access_no_permissions(self, mock_user):
        """Test organization access when user has no pricing permissions"""
        from backend.api.pw_pricing import verify_organization_access
        
        mock_org = Mock(spec=Organization)
        mock_org.id = "org-123"
        
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_org
        
        with patch('backend.api.pw_pricing.get_user_permissions') as mock_get_perms:
            mock_get_perms.return_value = ["content.create", "content.read"]  # No pricing permissions
            
            with pytest.raises(Exception):  # Should raise HTTPException
                verify_organization_access("org-123", mock_user, mock_db)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])