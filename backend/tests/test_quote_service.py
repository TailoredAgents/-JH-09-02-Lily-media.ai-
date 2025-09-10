"""
Comprehensive unit tests for quote service functionality
"""

import pytest
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from backend.services.quote_service import (
    QuoteService,
    QuoteCreationRequest,
    QuoteUpdateRequest,
    create_quote_from_surfaces,
    update_quote_status
)
from backend.services.settings_resolver import SettingsResolver
from backend.db.models import Quote, PricingRule, Organization, User


class TestQuoteCreationRequest:
    """Test quote creation request model"""
    
    def test_quote_creation_request_basic(self):
        """Test basic quote creation request"""
        surfaces = {"driveway": {"area": 1000, "difficulty": "medium"}}
        
        request = QuoteCreationRequest(
            organization_id="org-123",
            customer_email="customer@example.com",
            service_types=["pressure_wash"],
            surfaces=surfaces
        )
        
        assert request.organization_id == "org-123"
        assert request.customer_email == "customer@example.com"
        assert request.service_types == ["pressure_wash"]
        assert request.surfaces == surfaces
        assert request.customer_tier == "standard"
        assert request.rush_job is False
        assert request.source == "manual"
        assert request.quote_validity_days == 30
    
    def test_quote_creation_request_full(self):
        """Test quote creation request with all fields"""
        surfaces = {"driveway": {"area": 1000}, "deck": {"area": 500}}
        location = {"address": "123 Main St", "distance_miles": 10.0}
        preferred_date = datetime(2025, 6, 15)
        
        request = QuoteCreationRequest(
            organization_id="org-123",
            customer_email="customer@example.com",
            service_types=["pressure_wash", "soft_wash"],
            surfaces=surfaces,
            customer_name="John Doe",
            customer_phone="555-1234",
            customer_address="123 Main St",
            location=location,
            preferred_date=preferred_date,
            additional_services=["window_cleaning"],
            customer_tier="premium",
            rush_job=True,
            notes="Internal notes",
            customer_notes="Customer visible notes",
            source="dm_inquiry",
            source_metadata={"platform": "instagram"},
            quote_validity_days=14
        )
        
        assert request.customer_name == "John Doe"
        assert request.customer_phone == "555-1234"
        assert request.location == location
        assert request.preferred_date == preferred_date
        assert request.additional_services == ["window_cleaning"]
        assert request.customer_tier == "premium"
        assert request.rush_job is True
        assert request.source == "dm_inquiry"
        assert request.quote_validity_days == 14


class TestQuoteUpdateRequest:
    """Test quote update request model"""
    
    def test_quote_update_request_status_only(self):
        """Test quote update request with status change only"""
        request = QuoteUpdateRequest(new_status="sent")
        
        assert request.new_status == "sent"
        assert request.notes is None
        assert request.customer_notes is None
        assert request.recompute_pricing is False
    
    def test_quote_update_request_full(self):
        """Test quote update request with all fields"""
        request = QuoteUpdateRequest(
            new_status="accepted",
            notes="Updated notes",
            customer_notes="Updated customer notes",
            recompute_pricing=True
        )
        
        assert request.new_status == "accepted"
        assert request.notes == "Updated notes"
        assert request.customer_notes == "Updated customer notes"
        assert request.recompute_pricing is True


class TestQuoteService:
    """Test quote service functionality"""
    
    @pytest.fixture
    def mock_settings_resolver(self):
        """Mock settings resolver"""
        return Mock(spec=SettingsResolver)
    
    @pytest.fixture
    def mock_pricing_service(self):
        """Mock pricing service"""
        pricing_service = Mock()
        
        # Mock pricing quote
        from backend.services.pricing_service import PricingQuote
        mock_quote = PricingQuote()
        mock_quote.subtotal = Decimal('500.00')
        mock_quote.bundle_discount = Decimal('-50.00')  # Negative discount
        mock_quote.tax_amount = Decimal('40.00')
        mock_quote.total = Decimal('490.00')
        mock_quote.currency = "USD"
        mock_quote.breakdown = [
            {"type": "base_service", "service": "pressure_wash", "amount": 500.00},
            {"type": "bundle_discount", "amount": -50.00}
        ]
        mock_quote.applied_rules = ["Standard Pricing"]
        
        pricing_service.compute_quote.return_value = mock_quote
        return pricing_service
    
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
        rule.name = "Standard Pricing"
        rule.is_active = True
        return rule
    
    @pytest.fixture
    def mock_db_session(self, mock_organization, mock_pricing_rule):
        """Mock database session"""
        db = Mock(spec=Session)
        
        # Mock query chains
        org_query = Mock()
        org_query.filter.return_value.first.return_value = mock_organization
        
        pricing_rule_query = Mock()
        pricing_rule_query.filter.return_value.first.return_value = mock_pricing_rule
        
        # Setup query routing
        def mock_query(model):
            if model == Organization:
                return org_query
            elif model == PricingRule:
                return pricing_rule_query
            else:
                return Mock()
        
        db.query.side_effect = mock_query
        return db
    
    @pytest.fixture
    def quote_service(self, mock_settings_resolver):
        """Create quote service instance"""
        return QuoteService(mock_settings_resolver)
    
    def test_create_quote_success(self, quote_service, mock_db_session, mock_pricing_service):
        """Test successful quote creation"""
        with patch.object(quote_service, 'pricing_service', mock_pricing_service):
            # Create quote request
            request = QuoteCreationRequest(
                organization_id="org-123",
                customer_email="customer@example.com",
                service_types=["pressure_wash"],
                surfaces={"driveway": {"area": 1000}}
            )
            
            # Mock UUID generation
            mock_uuid = Mock()
            mock_uuid.__str__ = Mock(return_value="quote-123")
            with patch('uuid.uuid4', return_value=mock_uuid):
                quote = quote_service.create_quote(request, mock_db_session, user_id=1)
            
            # Verify quote was created
            assert quote is not None
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
    
    def test_create_quote_organization_not_found(self, quote_service, mock_pricing_service):
        """Test quote creation when organization doesn't exist"""
        db = Mock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = None
        
        request = QuoteCreationRequest(
            organization_id="org-invalid",
            customer_email="customer@example.com",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}}
        )
        
        with patch.object(quote_service, 'pricing_service', mock_pricing_service):
            with pytest.raises(ValueError, match="Organization org-invalid not found"):
                quote_service.create_quote(request, db, user_id=1)
    
    def test_get_quote_success(self, quote_service, mock_db_session):
        """Test successful quote retrieval"""
        # Mock quote
        mock_quote = Mock(spec=Quote)
        mock_quote.id = "quote-123"
        mock_quote.organization_id = "org-123"
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_quote
        
        quote = quote_service.get_quote("quote-123", "org-123", mock_db_session)
        
        assert quote == mock_quote
    
    def test_get_quote_not_found(self, quote_service):
        """Test quote retrieval when quote doesn't exist"""
        db = Mock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = None
        
        quote = quote_service.get_quote("quote-invalid", "org-123", db)
        
        assert quote is None
    
    def test_list_quotes_basic(self, quote_service, mock_db_session):
        """Test basic quote listing"""
        # Mock quotes
        mock_quotes = [
            Mock(spec=Quote, id="quote-1", organization_id="org-123"),
            Mock(spec=Quote, id="quote-2", organization_id="org-123")
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_quotes
        
        mock_db_session.query.return_value = mock_query
        
        quotes = quote_service.list_quotes("org-123", mock_db_session)
        
        assert len(quotes) == 2
        assert quotes == mock_quotes
    
    def test_list_quotes_with_filters(self, quote_service, mock_db_session):
        """Test quote listing with status and customer email filters"""
        mock_quotes = [Mock(spec=Quote, id="quote-1")]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_quotes
        
        mock_db_session.query.return_value = mock_query
        
        quotes = quote_service.list_quotes(
            "org-123", 
            mock_db_session,
            status="sent",
            customer_email="customer@example.com",
            limit=10,
            offset=5
        )
        
        assert len(quotes) == 1
        # Verify filtering was applied (called multiple times)
        assert mock_query.filter.call_count >= 2
    
    def test_update_quote_status_transition(self, quote_service, mock_db_session):
        """Test quote status update with valid transition"""
        # Mock existing quote
        mock_quote = Mock(spec=Quote)
        mock_quote.id = "quote-123"
        mock_quote.organization_id = "org-123"
        mock_quote.status = "draft"
        mock_quote.can_transition_to.return_value = True
        mock_quote.notes = "Old notes"
        mock_quote.customer_notes = "Old customer notes"
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_quote
        
        # Create update request
        request = QuoteUpdateRequest(
            new_status="sent",
            notes="Updated notes",
            customer_notes="Updated customer notes"
        )
        
        updated_quote = quote_service.update_quote(
            "quote-123", "org-123", request, mock_db_session, user_id=1
        )
        
        assert updated_quote == mock_quote
        assert mock_quote.status == "sent"
        assert mock_quote.notes == "Updated notes"
        assert mock_quote.customer_notes == "Updated customer notes"
        assert mock_quote.updated_by_id == 1
        mock_db_session.commit.assert_called_once()
    
    def test_update_quote_invalid_transition(self, quote_service, mock_db_session):
        """Test quote status update with invalid transition"""
        # Mock existing quote
        mock_quote = Mock(spec=Quote)
        mock_quote.id = "quote-123"
        mock_quote.organization_id = "org-123"
        mock_quote.status = "accepted"
        mock_quote.can_transition_to.return_value = False
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_quote
        
        # Create update request with invalid transition
        request = QuoteUpdateRequest(new_status="draft")
        
        with pytest.raises(ValueError, match="Invalid status transition"):
            quote_service.update_quote(
                "quote-123", "org-123", request, mock_db_session, user_id=1
            )
        
        mock_db_session.rollback.assert_called_once()
    
    def test_update_quote_not_found(self, quote_service):
        """Test quote update when quote doesn't exist"""
        db = Mock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = None
        
        request = QuoteUpdateRequest(new_status="sent")
        
        with pytest.raises(ValueError, match="Quote quote-invalid not found"):
            quote_service.update_quote(
                "quote-invalid", "org-123", request, db, user_id=1
            )
    
    def test_expire_quotes(self, quote_service):
        """Test bulk quote expiration"""
        # Mock expired quotes
        expired_quote_1 = Mock(spec=Quote)
        expired_quote_1.status = "sent"
        expired_quote_2 = Mock(spec=Quote)
        expired_quote_2.status = "sent"
        
        db = Mock(spec=Session)
        db.query.return_value.filter.return_value.all.return_value = [
            expired_quote_1, expired_quote_2
        ]
        
        count = quote_service.expire_quotes(db)
        
        assert count == 2
        assert expired_quote_1.status == "expired"
        assert expired_quote_2.status == "expired"
        assert expired_quote_1.expired_at is not None
        assert expired_quote_2.expired_at is not None
        db.commit.assert_called_once()
    
    def test_generate_quote_number_first(self, quote_service):
        """Test quote number generation for first quote"""
        db = Mock(spec=Session)
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        
        with patch('backend.services.quote_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "202506"
            
            quote_number = quote_service._generate_quote_number("org-123", db)
            
            assert quote_number == "Q-202506-0001"
    
    def test_generate_quote_number_increment(self, quote_service):
        """Test quote number generation with existing quotes"""
        # Mock existing quote
        mock_existing_quote = Mock(spec=Quote)
        mock_existing_quote.quote_number = "Q-202506-0005"
        
        db = Mock(spec=Session)
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_existing_quote
        
        with patch('backend.services.quote_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "202506"
            
            quote_number = quote_service._generate_quote_number("org-123", db)
            
            assert quote_number == "Q-202506-0006"


class TestQuoteModel:
    """Test Quote model functionality"""
    
    def test_quote_to_dict(self):
        """Test quote to_dict conversion"""
        quote = Quote(
            id="quote-123",
            organization_id="org-123",
            customer_email="customer@example.com",
            subtotal=Decimal('500.00'),
            total=Decimal('540.00'),
            currency="USD",
            status="draft"
        )
        
        result = quote.to_dict()
        
        assert result["id"] == "quote-123"
        assert result["organization_id"] == "org-123"
        assert result["customer_email"] == "customer@example.com"
        assert result["subtotal"] == 500.00
        assert result["total"] == 540.00
        assert result["currency"] == "USD"
        assert result["status"] == "draft"
    
    def test_quote_is_expired_true(self):
        """Test is_expired property when quote is expired"""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        
        quote = Quote(valid_until=past_date)
        
        assert quote.is_expired is True
    
    def test_quote_is_expired_false(self):
        """Test is_expired property when quote is not expired"""
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        
        quote = Quote(valid_until=future_date)
        
        assert quote.is_expired is False
    
    def test_quote_is_expired_no_date(self):
        """Test is_expired property when no valid_until date"""
        quote = Quote(valid_until=None)
        
        assert quote.is_expired is False
    
    def test_quote_can_transition_to_valid(self):
        """Test valid status transitions"""
        quote = Quote(status="draft")
        
        assert quote.can_transition_to("sent") is True
        assert quote.can_transition_to("declined") is True
        assert quote.can_transition_to("accepted") is False
        assert quote.can_transition_to("expired") is False
    
    def test_quote_can_transition_to_terminal(self):
        """Test transitions from terminal states"""
        accepted_quote = Quote(status="accepted")
        declined_quote = Quote(status="declined")
        expired_quote = Quote(status="expired")
        
        assert accepted_quote.can_transition_to("sent") is False
        assert declined_quote.can_transition_to("accepted") is False
        assert expired_quote.can_transition_to("sent") is False


def test_create_quote_from_surfaces_convenience():
    """Test convenience function for creating quotes"""
    with patch('backend.services.quote_service.QuoteService') as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_quote = Mock(spec=Quote)
        mock_service.create_quote.return_value = mock_quote
        
        mock_db = Mock()
        mock_settings_resolver = Mock()
        
        result = create_quote_from_surfaces(
            organization_id="org-123",
            customer_email="customer@example.com",
            service_types=["pressure_wash"],
            surfaces={"driveway": {"area": 1000}},
            db=mock_db,
            user_id=1,
            settings_resolver=mock_settings_resolver
        )
        
        assert result == mock_quote
        mock_service_class.assert_called_once_with(mock_settings_resolver)
        mock_service.create_quote.assert_called_once()


def test_update_quote_status_convenience():
    """Test convenience function for updating quote status"""
    with patch('backend.services.quote_service.QuoteService') as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_quote = Mock(spec=Quote)
        mock_service.update_quote.return_value = mock_quote
        
        mock_db = Mock()
        mock_settings_resolver = Mock()
        
        result = update_quote_status(
            quote_id="quote-123",
            organization_id="org-123",
            new_status="sent",
            db=mock_db,
            user_id=1,
            settings_resolver=mock_settings_resolver,
            notes="Quote sent to customer"
        )
        
        assert result == mock_quote
        mock_service_class.assert_called_once_with(mock_settings_resolver)
        mock_service.update_quote.assert_called_once()