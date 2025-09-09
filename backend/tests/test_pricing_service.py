"""
Comprehensive unit tests for pressure washing pricing engine
"""

import pytest
from datetime import datetime, timezone, date
from decimal import Decimal
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from backend.services.pricing_service import (
    PricingService,
    PricingQuoteRequest,
    PricingQuote,
    compute_pricing_quote
)
from backend.services.settings_resolver import SettingsResolver, PricingSettings
from backend.db.models import PricingRule, Organization, User


class TestPricingQuoteRequest:
    """Test pricing quote request model"""
    
    def test_quote_request_creation(self):
        """Test basic quote request creation"""
        surfaces = {"driveway": {"area": 1000, "difficulty": "medium"}}
        location = {"address": "123 Main St", "distance_miles": 5.0}
        
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash", "soft_wash"],
            surfaces=surfaces,
            location=location,
            preferred_date=date(2025, 6, 15),
            additional_services=["window_cleaning"],
            customer_tier="premium",
            rush_job=True
        )
        
        assert request.organization_id == "org-123"
        assert request.service_types == ["pressure_wash", "soft_wash"]
        assert request.surfaces == surfaces
        assert request.location == location
        assert request.preferred_date == date(2025, 6, 15)
        assert request.additional_services == ["window_cleaning"]
        assert request.customer_tier == "premium"
        assert request.rush_job is True
    
    def test_quote_request_defaults(self):
        """Test quote request with default values"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"deck": {"area": 500}}
        )
        
        assert request.additional_services == []
        assert request.customer_tier == "standard"
        assert request.rush_job is False
        assert request.metadata == {}


class TestPricingQuote:
    """Test pricing quote model"""
    
    def test_quote_initialization(self):
        """Test quote initialization with default values"""
        quote = PricingQuote()
        
        assert quote.base_total == Decimal('0.00')
        assert quote.bundle_discount == Decimal('0.00')
        assert quote.seasonal_modifier == Decimal('0.00')
        assert quote.travel_fee == Decimal('0.00')
        assert quote.rush_fee == Decimal('0.00')
        assert quote.additional_services_total == Decimal('0.00')
        assert quote.subtotal == Decimal('0.00')
        assert quote.tax_rate == Decimal('0.00')
        assert quote.tax_amount == Decimal('0.00')
        assert quote.total == Decimal('0.00')
        assert quote.currency == "USD"
        assert quote.breakdown == []
        assert quote.applied_rules == []
        assert quote.warning_messages == []
        assert quote.valid_until is None
    
    def test_quote_to_dict(self):
        """Test quote conversion to dictionary"""
        quote = PricingQuote()
        quote.base_total = Decimal('500.00')
        quote.total = Decimal('575.00')
        quote.currency = "USD"
        quote.breakdown = [{"type": "test", "amount": 500.00}]
        quote.applied_rules = ["Test Rule"]
        quote.warning_messages = ["Test warning"]
        quote.valid_until = datetime(2025, 7, 1, 23, 59, 59, tzinfo=timezone.utc)
        
        result = quote.to_dict()
        
        assert result["base_total"] == 500.00
        assert result["total"] == 575.00
        assert result["currency"] == "USD"
        assert result["breakdown"] == [{"type": "test", "amount": 500.00}]
        assert result["applied_rules"] == ["Test Rule"]
        assert result["warning_messages"] == ["Test warning"]
        assert result["valid_until"] == "2025-07-01T23:59:59+00:00"


class TestPricingService:
    """Test pricing service functionality"""
    
    @pytest.fixture
    def mock_settings_resolver(self):
        """Mock settings resolver"""
        resolver = Mock(spec=SettingsResolver)
        pricing_settings = PricingSettings(
            currency="USD",
            tax_rate=8.25,
            min_job_value=150.00,
            max_travel_distance=50.0
        )
        resolver.get_pricing_settings.return_value = pricing_settings
        return resolver
    
    @pytest.fixture
    def mock_pricing_rule(self):
        """Mock pricing rule with comprehensive test data"""
        return PricingRule(
            id=1,
            organization_id="org-123",
            name="Standard Pricing",
            currency="USD",
            min_job_total=Decimal('150.00'),
            base_rates={
                "pressure_wash": {
                    "surfaces": {
                        "driveway": 0.15,
                        "deck": 0.12,
                        "siding": 0.08,
                        "concrete": 0.10
                    }
                },
                "soft_wash": {
                    "surfaces": {
                        "roof": 0.25,
                        "siding": 0.18
                    }
                }
            },
            bundles=[
                {
                    "name": "Complete Exterior",
                    "services": ["pressure_wash", "soft_wash"],
                    "discount_type": "percentage",
                    "discount_value": 15
                }
            ],
            seasonal_modifiers={
                "6": 10,  # June - peak season
                "12": -20,  # December - off season
                "summer": 15,
                "winter": -25
            },
            travel_settings={
                "free_radius_miles": 10,
                "rate_per_mile": 2.50,
                "minimum_fee": 25.00
            },
            additional_services={
                "window_cleaning": {
                    "price": 75.00,
                    "description": "Exterior window cleaning"
                },
                "gutter_cleaning": {
                    "price": 125.00,
                    "description": "Gutter cleaning and inspection"
                }
            },
            business_rules={
                "tax_rate": 8.25,
                "quote_validity_days": 30,
                "rush_fee": {
                    "enabled": True,
                    "type": "percentage",
                    "value": 25
                },
                "customer_tiers": {
                    "premium": {
                        "discount_percent": 10
                    },
                    "vip": {
                        "discount_percent": 20
                    }
                }
            },
            is_active=True,
            priority=0,
            version=1,
            created_by_id=1,
            created_at=datetime.now(timezone.utc),
            updated_at=None
        )
    
    @pytest.fixture
    def mock_db_session(self, mock_pricing_rule):
        """Mock database session"""
        db = Mock(spec=Session)
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_pricing_rule
        return db
    
    @pytest.fixture
    def pricing_service(self, mock_settings_resolver):
        """Create pricing service instance"""
        return PricingService(mock_settings_resolver)
    
    def test_get_active_pricing_rule(self, pricing_service, mock_db_session, mock_pricing_rule):
        """Test getting active pricing rule"""
        rule = pricing_service._get_active_pricing_rule("org-123", mock_db_session)
        
        assert rule == mock_pricing_rule
        assert rule.organization_id == "org-123"
        assert rule.is_active is True
    
    def test_get_active_pricing_rule_not_found(self, pricing_service):
        """Test handling when no active pricing rule is found"""
        db = Mock(spec=Session)
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        
        rule = pricing_service._get_active_pricing_rule("org-999", db)
        assert rule is None
    
    def test_calculate_base_pricing_single_service(self, pricing_service, mock_pricing_rule):
        """Test base pricing calculation for single service"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}}
        )
        
        quote = PricingQuote()
        pricing_service._calculate_base_pricing(request, mock_pricing_rule, quote)
        
        # driveway: 1000 * 0.15 = 150.00
        assert quote.base_total == Decimal('150.00')
        assert len(quote.breakdown) == 1
        assert quote.breakdown[0]["service"] == "pressure_wash"
        assert quote.breakdown[0]["surface"] == "driveway"
        assert quote.breakdown[0]["area"] == 1000
        assert quote.breakdown[0]["rate"] == 0.15
        assert quote.breakdown[0]["amount"] == 150.00
    
    def test_calculate_base_pricing_multiple_services(self, pricing_service, mock_pricing_rule):
        """Test base pricing calculation for multiple services"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash", "soft_wash"],
            surfaces={
                "driveway": {"area": 1000},
                "roof": {"area": 2000}
            }
        )
        
        quote = PricingQuote()
        pricing_service._calculate_base_pricing(request, mock_pricing_rule, quote)
        
        # driveway: 1000 * 0.15 = 150.00
        # roof: 2000 * 0.25 = 500.00
        # total: 650.00
        assert quote.base_total == Decimal('650.00')
        assert len(quote.breakdown) == 2
    
    def test_calculate_base_pricing_unknown_service(self, pricing_service, mock_pricing_rule):
        """Test handling of unknown service type"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["unknown_service"],
            surfaces={"driveway": {"area": 1000}}
        )
        
        quote = PricingQuote()
        pricing_service._calculate_base_pricing(request, mock_pricing_rule, quote)
        
        assert quote.base_total == Decimal('0.00')
        assert len(quote.warning_messages) == 1
        assert "No base rate found for service type: unknown_service" in quote.warning_messages[0]
    
    def test_apply_bundle_discounts(self, pricing_service, mock_pricing_rule):
        """Test bundle discount application"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash", "soft_wash"],
            surfaces={"driveway": {"area": 1000}}
        )
        
        quote = PricingQuote()
        quote.base_total = Decimal('500.00')
        pricing_service._apply_bundle_discounts(request, mock_pricing_rule, quote)
        
        # 15% discount: 500.00 * 0.15 = 75.00 (negative)
        assert quote.bundle_discount == Decimal('-75.00')
        assert len(quote.breakdown) == 1
        assert quote.breakdown[0]["type"] == "bundle_discount"
        assert quote.breakdown[0]["discount_type"] == "percentage"
        assert quote.breakdown[0]["discount_value"] == 15
        assert quote.breakdown[0]["amount"] == -75.00
    
    def test_apply_bundle_discounts_no_match(self, pricing_service, mock_pricing_rule):
        """Test bundle discount when services don't match"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],  # Only one service
            surfaces={"driveway": {"area": 1000}}
        )
        
        quote = PricingQuote()
        quote.base_total = Decimal('500.00')
        pricing_service._apply_bundle_discounts(request, mock_pricing_rule, quote)
        
        # No bundle discount should be applied
        assert quote.bundle_discount == Decimal('0.00')
        assert len(quote.breakdown) == 0
    
    def test_apply_seasonal_modifiers_month(self, pricing_service, mock_pricing_rule):
        """Test seasonal modifier application by month"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}},
            preferred_date=date(2025, 6, 15)  # June
        )
        
        quote = PricingQuote()
        quote.base_total = Decimal('500.00')
        pricing_service._apply_seasonal_modifiers(request, mock_pricing_rule, quote)
        
        # June: 10% modifier = 500.00 * 0.10 = 50.00
        assert quote.seasonal_modifier == Decimal('50.00')
        assert len(quote.breakdown) == 1
        assert quote.breakdown[0]["type"] == "seasonal_modifier"
        assert quote.breakdown[0]["month"] == 6
        assert quote.breakdown[0]["modifier_percent"] == 10
        assert quote.breakdown[0]["amount"] == 50.00
    
    def test_apply_seasonal_modifiers_season(self, pricing_service, mock_pricing_rule):
        """Test seasonal modifier application by season"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}},
            preferred_date=date(2025, 7, 15)  # Summer (no specific month rule)
        )
        
        quote = PricingQuote()
        quote.base_total = Decimal('500.00')
        pricing_service._apply_seasonal_modifiers(request, mock_pricing_rule, quote)
        
        # Summer: 15% modifier = 500.00 * 0.15 = 75.00
        assert quote.seasonal_modifier == Decimal('75.00')
        assert len(quote.breakdown) == 1
        assert quote.breakdown[0]["type"] == "seasonal_modifier"
        assert quote.breakdown[0]["season"] == "summer"
        assert quote.breakdown[0]["modifier_percent"] == 15
    
    def test_apply_seasonal_modifiers_no_date(self, pricing_service, mock_pricing_rule):
        """Test seasonal modifier when no date provided"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}}
        )
        
        quote = PricingQuote()
        quote.base_total = Decimal('500.00')
        pricing_service._apply_seasonal_modifiers(request, mock_pricing_rule, quote)
        
        # No modifier should be applied
        assert quote.seasonal_modifier == Decimal('0.00')
        assert len(quote.breakdown) == 0
    
    def test_calculate_travel_fees_within_free_radius(self, pricing_service, mock_pricing_rule):
        """Test travel fee calculation within free radius"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}},
            location={"distance_miles": 5.0}  # Within 10 mile free radius
        )
        
        quote = PricingQuote()
        pricing_service._calculate_travel_fees(request, mock_pricing_rule, quote)
        
        # No travel fee within free radius
        assert quote.travel_fee == Decimal('0.00')
        assert len(quote.breakdown) == 0
    
    def test_calculate_travel_fees_beyond_free_radius(self, pricing_service, mock_pricing_rule):
        """Test travel fee calculation beyond free radius"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}},
            location={"distance_miles": 20.0}  # Beyond 10 mile free radius
        )
        
        quote = PricingQuote()
        pricing_service._calculate_travel_fees(request, mock_pricing_rule, quote)
        
        # 10 billable miles * $2.50 = $25.00 (meets minimum fee)
        assert quote.travel_fee == Decimal('25.00')
        assert len(quote.breakdown) == 1
        assert quote.breakdown[0]["type"] == "travel_fee"
        assert quote.breakdown[0]["total_distance"] == 20.0
        assert quote.breakdown[0]["free_radius"] == 10.0
        assert quote.breakdown[0]["billable_distance"] == 10.0
        assert quote.breakdown[0]["rate_per_mile"] == 2.50
        assert quote.breakdown[0]["amount"] == 25.00
    
    def test_calculate_travel_fees_minimum_fee(self, pricing_service, mock_pricing_rule):
        """Test travel fee minimum fee enforcement"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}},
            location={"distance_miles": 12.0}  # 2 billable miles
        )
        
        quote = PricingQuote()
        pricing_service._calculate_travel_fees(request, mock_pricing_rule, quote)
        
        # 2 billable miles * $2.50 = $5.00, but minimum is $25.00
        assert quote.travel_fee == Decimal('25.00')
    
    def test_apply_rush_fees_enabled(self, pricing_service, mock_pricing_rule):
        """Test rush fee application when enabled"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}},
            rush_job=True
        )
        
        quote = PricingQuote()
        quote.base_total = Decimal('500.00')
        pricing_service._apply_rush_fees(request, mock_pricing_rule, quote)
        
        # 25% rush fee: 500.00 * 0.25 = 125.00
        assert quote.rush_fee == Decimal('125.00')
        assert len(quote.breakdown) == 1
        assert quote.breakdown[0]["type"] == "rush_fee"
        assert quote.breakdown[0]["fee_type"] == "percentage"
        assert quote.breakdown[0]["fee_value"] == 25
        assert quote.breakdown[0]["amount"] == 125.00
    
    def test_apply_rush_fees_not_requested(self, pricing_service, mock_pricing_rule):
        """Test rush fee when not requested"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}},
            rush_job=False
        )
        
        quote = PricingQuote()
        quote.base_total = Decimal('500.00')
        pricing_service._apply_rush_fees(request, mock_pricing_rule, quote)
        
        # No rush fee should be applied
        assert quote.rush_fee == Decimal('0.00')
        assert len(quote.breakdown) == 0
    
    def test_calculate_additional_services(self, pricing_service, mock_pricing_rule):
        """Test additional services calculation"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}},
            additional_services=["window_cleaning", "gutter_cleaning"]
        )
        
        quote = PricingQuote()
        pricing_service._calculate_additional_services(request, mock_pricing_rule, quote)
        
        # window_cleaning: $75 + gutter_cleaning: $125 = $200
        assert quote.additional_services_total == Decimal('200.00')
        assert len(quote.breakdown) == 2
        assert quote.breakdown[0]["type"] == "additional_service"
        assert quote.breakdown[0]["service"] == "window_cleaning"
        assert quote.breakdown[0]["amount"] == 75.00
        assert quote.breakdown[1]["service"] == "gutter_cleaning"
        assert quote.breakdown[1]["amount"] == 125.00
    
    def test_calculate_additional_services_unknown(self, pricing_service, mock_pricing_rule):
        """Test additional services with unknown service"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}},
            additional_services=["unknown_service"]
        )
        
        quote = PricingQuote()
        pricing_service._calculate_additional_services(request, mock_pricing_rule, quote)
        
        assert quote.additional_services_total == Decimal('0.00')
        assert len(quote.warning_messages) == 1
        assert "Additional service not found: unknown_service" in quote.warning_messages[0]
    
    def test_apply_business_rules_customer_tier(self, pricing_service, mock_pricing_rule):
        """Test customer tier discount application"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}},
            customer_tier="premium"
        )
        
        quote = PricingQuote()
        quote.base_total = Decimal('500.00')
        pricing_service._apply_business_rules(request, mock_pricing_rule, quote)
        
        # Premium tier gets 10% discount: 500.00 - (500.00 * 0.10) = 450.00
        assert quote.base_total == Decimal('450.00')
        assert len(quote.breakdown) == 1
        assert quote.breakdown[0]["type"] == "customer_tier_discount"
        assert quote.breakdown[0]["tier"] == "premium"
        assert quote.breakdown[0]["discount_percent"] == 10
        assert quote.breakdown[0]["amount"] == -50.00
    
    def test_calculate_taxes(self, pricing_service, mock_pricing_rule):
        """Test tax calculation"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}}
        )
        
        # Mock pricing settings with tax rate
        pricing_settings = Mock()
        pricing_settings.tax_rate = 8.25
        
        quote = PricingQuote()
        quote.subtotal = Decimal('500.00')
        pricing_service._calculate_taxes(request, mock_pricing_rule, pricing_settings, quote)
        
        # Tax: 500.00 * 0.0825 = 41.25
        assert quote.tax_rate == Decimal('8.25')
        assert quote.tax_amount == Decimal('41.25')
        assert quote.total == Decimal('541.25')
        assert len(quote.breakdown) == 1
        assert quote.breakdown[0]["type"] == "tax"
        assert quote.breakdown[0]["tax_rate"] == 8.25
        assert quote.breakdown[0]["amount"] == 41.25
    
    def test_get_season_mapping(self, pricing_service):
        """Test season mapping from months"""
        assert pricing_service._get_season(1) == "winter"
        assert pricing_service._get_season(3) == "spring"
        assert pricing_service._get_season(6) == "summer"
        assert pricing_service._get_season(9) == "fall"
        assert pricing_service._get_season(12) == "winter"
    
    @patch('backend.services.pricing_service.datetime')
    def test_set_quote_validity(self, mock_datetime, pricing_service, mock_pricing_rule):
        """Test quote validity period setting"""
        # Mock current time
        mock_now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        quote = PricingQuote()
        pricing_service._set_quote_validity(mock_pricing_rule, quote)
        
        # Should set validity for 30 days from now at end of day
        assert quote.valid_until is not None
    
    def test_compute_quote_integration(self, pricing_service, mock_db_session, mock_pricing_rule, mock_settings_resolver):
        """Test complete quote computation integration"""
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash", "soft_wash"],
            surfaces={
                "driveway": {"area": 1000},  # 1000 * 0.15 = 150
                "roof": {"area": 1000}       # 1000 * 0.25 = 250
            },
            location={"distance_miles": 20.0},
            preferred_date=date(2025, 6, 15),  # June - 10% modifier
            additional_services=["window_cleaning"],  # +75
            customer_tier="premium",  # 10% tier discount
            rush_job=True  # 25% rush fee
        )
        
        quote = pricing_service.compute_quote(request, mock_db_session, user_id=1)
        
        # Verify quote was computed
        assert quote.currency == "USD"
        assert quote.total > Decimal('0.00')
        assert len(quote.applied_rules) > 0
        assert len(quote.breakdown) > 0
        
        # Check minimum job total enforcement
        if quote.total < mock_pricing_rule.min_job_total:
            assert quote.total == mock_pricing_rule.min_job_total
    
    def test_compute_quote_no_pricing_rule(self, pricing_service, mock_settings_resolver):
        """Test quote computation when no pricing rule exists"""
        db = Mock(spec=Session)
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        
        request = PricingQuoteRequest(
            organization_id="org-999",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}}
        )
        
        with pytest.raises(ValueError, match="No active pricing rules found"):
            pricing_service.compute_quote(request, db, user_id=1)
    
    def test_compute_quote_minimum_job_total(self, pricing_service, mock_db_session, mock_pricing_rule, mock_settings_resolver):
        """Test minimum job total enforcement"""
        # Create a small job that's below minimum
        request = PricingQuoteRequest(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 100}}  # Very small area
        )
        
        quote = pricing_service.compute_quote(request, mock_db_session, user_id=1)
        
        # Should be adjusted to minimum job total
        assert quote.total >= mock_pricing_rule.min_job_total
        if any("minimum" in msg.lower() for msg in quote.warning_messages):
            assert any("type" in item and item["type"] == "minimum_adjustment" for item in quote.breakdown)


def test_compute_pricing_quote_convenience_function():
    """Test the convenience function for computing quotes"""
    with patch('backend.services.pricing_service.PricingService') as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_quote = PricingQuote()
        mock_service.compute_quote.return_value = mock_quote
        
        mock_db = Mock()
        mock_settings_resolver = Mock()
        
        result = compute_pricing_quote(
            organization_id="org-123",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}},
            db=mock_db,
            user_id=1,
            settings_resolver=mock_settings_resolver
        )
        
        assert result == mock_quote
        mock_service_class.assert_called_once_with(mock_settings_resolver)
        mock_service.compute_quote.assert_called_once()