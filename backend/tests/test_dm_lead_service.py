"""
Unit tests for PW-DM-REPLACE-001: DM Lead Creation Service

Tests for intent detection, lead creation from DMs, and auto-quote generation.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any

from backend.services.dm_lead_service import DMIntentDetector, DMLeadService, get_dm_lead_service
from backend.services.lead_quote_service import LeadQuoteService, get_lead_quote_service
from backend.db.models import SocialInteraction, Lead, Quote


class TestDMIntentDetector:
    """Test the intent detection functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.detector = DMIntentDetector()
    
    def test_detect_quote_request_intent(self):
        """Test detection of quote request intent"""
        test_cases = [
            "Can you give me a quote for pressure washing my driveway?",
            "How much would you charge to clean my house?",
            "I need an estimate for washing my deck",
            "What's the cost to pressure wash my patio?"
        ]
        
        for content in test_cases:
            intent = self.detector.detect_intent(content)
            assert intent == "quote_request", f"Failed to detect quote_request in: {content}"
    
    def test_detect_price_inquiry_intent(self):
        """Test detection of price inquiry intent"""
        test_cases = [
            "How expensive is pressure washing?",
            "Are your rates affordable?",
            "What's your ballpark pricing?",
            "Do you have budget-friendly options?"
        ]
        
        for content in test_cases:
            intent = self.detector.detect_intent(content)
            assert intent == "price_inquiry", f"Failed to detect price_inquiry in: {content}"
    
    def test_detect_service_interest_intent(self):
        """Test detection of service interest intent"""
        test_cases = [
            "Do you do pressure washing for driveways and patios?",
            "I need my house siding cleaned",
            "Can you clean concrete and deck areas?"
        ]
        
        for content in test_cases:
            intent = self.detector.detect_intent(content)
            assert intent == "service_interest", f"Failed to detect service_interest in: {content}"
    
    def test_no_intent_detected(self):
        """Test that non-relevant messages don't trigger intent"""
        test_cases = [
            "Hello there!",
            "Thanks for following back",
            "Great content as always",
            "Have a nice day"
        ]
        
        for content in test_cases:
            intent = self.detector.detect_intent(content)
            assert intent is None, f"False positive intent detected in: {content}"
    
    def test_extract_surfaces_basic(self):
        """Test basic surface extraction"""
        content = "Can you clean my driveway and deck?"
        surfaces = self.detector.extract_surfaces(content)
        
        assert "driveway" in surfaces
        assert "deck" in surfaces
        assert surfaces["driveway"]["mentioned"] is True
        assert surfaces["deck"]["mentioned"] is True
    
    def test_extract_surfaces_with_area(self):
        """Test surface extraction with area information"""
        content = "I have a 1500 sq ft driveway that needs cleaning"
        surfaces = self.detector.extract_surfaces(content)
        
        assert "driveway" in surfaces
        assert surfaces["driveway"]["mentioned"] is True
        assert surfaces["driveway"]["area"] == 1500.0
    
    def test_extract_surfaces_dimensions(self):
        """Test area extraction from dimensions"""
        content = "My patio is 20 by 30 feet and needs washing"
        surfaces = self.detector.extract_surfaces(content)
        
        assert "patio" in surfaces
        assert surfaces["patio"]["area"] == 600.0  # 20 * 30
    
    def test_calculate_priority_score_quote_request(self):
        """Test priority scoring for quote requests"""
        intent = "quote_request"
        surfaces = {"driveway": {"mentioned": True, "area": 1000}}
        content = "Can you quote my 1000 sq ft driveway? Call me at 555-1234"
        
        score = self.detector.calculate_priority_score(intent, surfaces, content)
        
        # Should be high score: 80 (quote_request) + 5 (surface) + 10 (area) + 5 (phone) = 100
        assert score == 100.0
    
    def test_calculate_priority_score_service_interest(self):
        """Test priority scoring for service interest"""
        intent = "service_interest"
        surfaces = {"deck": {"mentioned": True}}
        content = "Do you clean decks?"
        
        score = self.detector.calculate_priority_score(intent, surfaces, content)
        
        # Should be: 40 (service_interest) + 5 (surface) = 45
        assert score == 45.0


class TestDMLeadService:
    """Test the lead creation service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = DMLeadService()
        self.mock_db = Mock()
        self.mock_interaction = Mock(spec=SocialInteraction)
        self.mock_interaction.id = "interaction-123"
        self.mock_interaction.interaction_type = "dm"
        self.mock_interaction.platform = "facebook"
        self.mock_interaction.content = "Can you give me a quote for my 1500 sq ft driveway?"
        self.mock_interaction.author_display_name = "John Smith"
        self.mock_interaction.author_username = "johnsmith"
        self.mock_interaction.author_platform_id = "fb-12345"
        self.mock_interaction.author_profile_url = "https://facebook.com/johnsmith"
        self.mock_interaction.platform_metadata = {"source": "facebook_webhook"}
    
    def test_create_lead_from_dm_success(self):
        """Test successful lead creation from DM with intent"""
        organization_id = "org-123"
        user_id = 1
        
        with patch('backend.services.dm_lead_service.get_lead_quote_service') as mock_quote_service:
            mock_quote_service.return_value.try_auto_quote_for_lead.return_value = None
            
            lead = self.service.create_lead_from_dm(
                self.mock_interaction, organization_id, self.mock_db, user_id
            )
        
        # Verify lead was created
        assert lead is not None
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        
        # Verify lead properties
        assert lead.organization_id == organization_id
        assert lead.interaction_id == "interaction-123"
        assert lead.source_platform == "facebook"
        assert lead.contact_name == "John Smith"
        assert lead.pricing_intent == "quote_request"
        assert lead.status == "new"
        assert len(lead.requested_services) > 0
        assert "driveway" in lead.extracted_surfaces
    
    def test_create_lead_non_dm_skipped(self):
        """Test that non-DM interactions are skipped"""
        self.mock_interaction.interaction_type = "comment"
        
        lead = self.service.create_lead_from_dm(
            self.mock_interaction, "org-123", self.mock_db, 1
        )
        
        assert lead is None
        self.mock_db.add.assert_not_called()
    
    def test_create_lead_no_intent_skipped(self):
        """Test that DMs without pricing intent are skipped"""
        self.mock_interaction.content = "Thanks for following back!"
        
        lead = self.service.create_lead_from_dm(
            self.mock_interaction, "org-123", self.mock_db, 1
        )
        
        assert lead is None
        self.mock_db.add.assert_not_called()
    
    def test_create_lead_with_auto_quote_generation(self):
        """Test lead creation triggers auto-quote when appropriate"""
        organization_id = "org-123"
        user_id = 1
        mock_quote = Mock(spec=Quote)
        mock_quote.id = "quote-456"
        
        with patch('backend.services.dm_lead_service.get_lead_quote_service') as mock_quote_service:
            mock_quote_service.return_value.try_auto_quote_for_lead.return_value = mock_quote
            
            lead = self.service.create_lead_from_dm(
                self.mock_interaction, organization_id, self.mock_db, user_id
            )
        
        # Verify auto-quote was attempted
        mock_quote_service.return_value.try_auto_quote_for_lead.assert_called_once_with(
            lead, self.mock_db, user_id
        )
    
    def test_determine_services_from_surfaces(self):
        """Test service determination from extracted surfaces"""
        surfaces = {
            "driveway": {"mentioned": True},
            "house_siding": {"mentioned": True}
        }
        intent = "quote_request"
        
        services = self.service._determine_services(surfaces, intent)
        
        assert "driveway_cleaning" in services
        assert "house_washing" in services
        assert len(services) == 2
    
    def test_determine_services_fallback(self):
        """Test fallback service when no specific surfaces detected"""
        surfaces = {}
        intent = "quote_request"
        
        services = self.service._determine_services(surfaces, intent)
        
        assert "pressure_washing" in services
        assert len(services) == 1


class TestLeadQuoteService:
    """Test the lead to quote conversion service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = LeadQuoteService()
        self.mock_db = Mock()
        self.mock_lead = Mock(spec=Lead)
        self.mock_lead.id = "lead-123"
        self.mock_lead.organization_id = "org-123"
        self.mock_lead.pricing_intent = "quote_request"
        self.mock_lead.contact_name = "John Smith"
        self.mock_lead.contact_email = "john@example.com"
        self.mock_lead.contact_phone = "555-1234"
        self.mock_lead.contact_address = "123 Main St"
        self.mock_lead.requested_services = ["driveway_cleaning"]
        self.mock_lead.extracted_surfaces = {
            "driveway": {"mentioned": True, "area": 1500}
        }
        self.mock_lead.interaction_id = "interaction-123"
        self.mock_lead.source_platform = "facebook"
        self.mock_lead.priority_score = 90.0
    
    def test_can_generate_quote_success(self):
        """Test successful quote generation eligibility check"""
        result = self.service.can_generate_quote(self.mock_lead)
        assert result is True
    
    def test_can_generate_quote_no_intent(self):
        """Test quote generation fails without proper intent"""
        self.mock_lead.pricing_intent = "service_interest"
        result = self.service.can_generate_quote(self.mock_lead)
        assert result is False
    
    def test_can_generate_quote_no_surfaces(self):
        """Test quote generation fails without surface data"""
        self.mock_lead.extracted_surfaces = {}
        result = self.service.can_generate_quote(self.mock_lead)
        assert result is False
    
    def test_can_generate_quote_no_area_data(self):
        """Test quote generation fails without area information"""
        self.mock_lead.extracted_surfaces = {
            "driveway": {"mentioned": True}  # No area data
        }
        result = self.service.can_generate_quote(self.mock_lead)
        assert result is False
    
    def test_can_generate_quote_no_contact_info(self):
        """Test quote generation fails without contact information"""
        self.mock_lead.contact_name = None
        self.mock_lead.contact_email = None
        result = self.service.can_generate_quote(self.mock_lead)
        assert result is False
    
    @patch('backend.services.lead_quote_service.QuoteService')
    def test_generate_draft_quote_success(self, mock_quote_service_class):
        """Test successful draft quote generation"""
        mock_quote_service = Mock()
        mock_quote_service_class.return_value = mock_quote_service
        
        mock_quote = Mock(spec=Quote)
        mock_quote.id = "quote-456"
        mock_quote.total = 450.00
        mock_quote.currency = "USD"
        mock_quote_service.create_quote.return_value = mock_quote
        
        result = self.service.generate_draft_quote(self.mock_lead, self.mock_db, 1)
        
        assert result == mock_quote
        mock_quote_service.create_quote.assert_called_once()
        
        # Verify quote request parameters
        call_args = mock_quote_service.create_quote.call_args[0][0]
        assert call_args.organization_id == "org-123"
        assert call_args.customer_email == "john@example.com"
        assert call_args.service_types == ["driveway_cleaning"]
        assert "driveway" in call_args.surfaces
        assert call_args.surfaces["driveway"]["area"] == 1500
    
    def test_convert_lead_surfaces_to_quote_format(self):
        """Test conversion of lead surface data to quote format"""
        extracted_surfaces = {
            "driveway": {"mentioned": True, "area": 1500},
            "patio": {"mentioned": True, "area": 800}
        }
        
        result = self.service._convert_lead_surfaces_to_quote_format(extracted_surfaces)
        
        assert "driveway" in result
        assert "patio" in result
        assert result["driveway"]["area"] == 1500
        assert result["driveway"]["difficulty"] == "medium"
        assert result["patio"]["area"] == 800
        assert result["patio"]["condition"] == "fair"
    
    def test_extract_location_from_lead_with_address(self):
        """Test location extraction when lead has address"""
        result = self.service._extract_location_from_lead(self.mock_lead)
        
        assert result is not None
        assert result["address"] == "123 Main St"
        assert result["distance_miles"] == 0.0
    
    def test_extract_location_from_lead_no_address(self):
        """Test location extraction when lead has no address"""
        self.mock_lead.contact_address = None
        result = self.service._extract_location_from_lead(self.mock_lead)
        
        assert result is None
    
    @patch('backend.services.lead_quote_service.QuoteService')
    def test_try_auto_quote_for_lead_success(self, mock_quote_service_class):
        """Test successful auto-quote attempt"""
        mock_quote_service = Mock()
        mock_quote_service_class.return_value = mock_quote_service
        
        mock_quote = Mock(spec=Quote)
        mock_quote_service.create_quote.return_value = mock_quote
        
        result = self.service.try_auto_quote_for_lead(self.mock_lead, self.mock_db, 1)
        
        assert result == mock_quote
    
    def test_try_auto_quote_for_lead_not_qualified(self):
        """Test auto-quote attempt when lead not qualified"""
        self.mock_lead.pricing_intent = "service_interest"  # Not eligible
        
        result = self.service.try_auto_quote_for_lead(self.mock_lead, self.mock_db, 1)
        
        assert result is None
    
    @patch('backend.services.lead_quote_service.QuoteService')
    def test_try_auto_quote_for_lead_error_handling(self, mock_quote_service_class):
        """Test auto-quote error handling doesn't propagate"""
        mock_quote_service = Mock()
        mock_quote_service_class.return_value = mock_quote_service
        mock_quote_service.create_quote.side_effect = Exception("Database error")
        
        # Should not raise exception, should return None
        result = self.service.try_auto_quote_for_lead(self.mock_lead, self.mock_db, 1)
        assert result is None


class TestIntegrationFunctions:
    """Test integration and convenience functions"""
    
    def test_get_dm_lead_service(self):
        """Test factory function for DM lead service"""
        service = get_dm_lead_service()
        assert isinstance(service, DMLeadService)
    
    def test_get_lead_quote_service(self):
        """Test factory function for lead quote service"""
        service = get_lead_quote_service()
        assert isinstance(service, LeadQuoteService)
    
    @patch('backend.services.dm_lead_service.get_dm_lead_service')
    def test_create_lead_from_dm_interaction_success(self, mock_service_factory):
        """Test convenience function for creating lead from interaction ID"""
        from backend.services.dm_lead_service import create_lead_from_dm_interaction
        
        mock_db = Mock()
        mock_interaction = Mock(spec=SocialInteraction)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_interaction
        
        mock_service = Mock()
        mock_lead = Mock(spec=Lead)
        mock_service.create_lead_from_dm.return_value = mock_lead
        mock_service_factory.return_value = mock_service
        
        result = create_lead_from_dm_interaction("interaction-123", "org-123", mock_db, 1)
        
        assert result == mock_lead
        mock_service.create_lead_from_dm.assert_called_once_with(
            mock_interaction, "org-123", mock_db, 1
        )
    
    @patch('backend.services.dm_lead_service.get_dm_lead_service')
    def test_create_lead_from_dm_interaction_not_found(self, mock_service_factory):
        """Test convenience function when interaction not found"""
        from backend.services.dm_lead_service import create_lead_from_dm_interaction
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = create_lead_from_dm_interaction("nonexistent", "org-123", mock_db, 1)
        
        assert result is None


# Integration test scenarios
class TestLeadCreationIntegration:
    """Integration tests for the full lead creation pipeline"""
    
    @patch('backend.services.dm_lead_service.get_lead_quote_service')
    def test_full_dm_to_lead_to_quote_pipeline(self, mock_quote_service_factory):
        """Test complete pipeline from DM to lead to auto-generated quote"""
        # Set up mocks
        mock_db = Mock()
        mock_quote_service = Mock()
        mock_quote = Mock(spec=Quote)
        mock_quote.id = "quote-456"
        
        mock_quote_service.try_auto_quote_for_lead.return_value = mock_quote
        mock_quote_service_factory.return_value = mock_quote_service
        
        # Create test DM interaction
        interaction = Mock(spec=SocialInteraction)
        interaction.id = "interaction-123"
        interaction.interaction_type = "dm"
        interaction.platform = "facebook"
        interaction.content = "Can you quote my 1500 sq ft driveway cleaning?"
        interaction.author_display_name = "John Smith"
        interaction.author_username = "johnsmith"
        interaction.author_platform_id = "fb-12345"
        interaction.author_profile_url = "https://facebook.com/johnsmith"
        interaction.platform_metadata = {"source": "webhook"}
        
        # Run the service
        service = DMLeadService()
        lead = service.create_lead_from_dm(interaction, "org-123", mock_db, 1)
        
        # Verify lead was created
        assert lead is not None
        assert lead.pricing_intent == "quote_request"
        assert "driveway" in lead.extracted_surfaces
        assert lead.extracted_surfaces["driveway"]["area"] == 1500.0
        
        # Verify auto-quote was attempted
        mock_quote_service.try_auto_quote_for_lead.assert_called_once_with(lead, mock_db, 1)