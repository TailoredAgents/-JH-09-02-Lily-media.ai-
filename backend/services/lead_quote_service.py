"""
PW-DM-REPLACE-001: Lead to Quote Service

Service for automatically generating draft quotes from leads with sufficient surface data.
Converts leads with extracted surface/area information into draft quotes.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.db.models import Lead, Quote
from backend.services.quote_service import QuoteService, QuoteCreationRequest
from backend.services.settings_resolver import SettingsResolver
from backend.core.audit_logger import get_audit_logger, AuditEventType

logger = logging.getLogger(__name__)


class LeadQuoteService:
    """
    Service for generating draft quotes from leads with surface data
    """
    
    def __init__(self):
        self.settings_resolver = SettingsResolver()
        self.quote_service = QuoteService(self.settings_resolver)
    
    def can_generate_quote(self, lead: Lead) -> bool:
        """
        Check if a lead has enough information to generate a quote
        
        Args:
            lead: Lead object to check
            
        Returns:
            bool: True if quote can be generated
        """
        # Must have pricing intent that suggests they want a quote
        if lead.pricing_intent not in ["quote_request", "price_inquiry"]:
            return False
        
        # Must have at least one surface with area information
        if not lead.extracted_surfaces:
            return False
            
        has_area_data = False
        for surface_data in lead.extracted_surfaces.values():
            if isinstance(surface_data, dict) and surface_data.get("area"):
                has_area_data = True
                break
        
        if not has_area_data:
            return False
        
        # Must have customer email (or we need to create a generic one)
        # For now, we'll require at least contact info
        if not (lead.contact_name or lead.contact_email):
            return False
            
        return True
    
    def generate_draft_quote(
        self, 
        lead: Lead, 
        db: Session, 
        user_id: int
    ) -> Optional[Quote]:
        """
        Generate a draft quote from lead data
        
        Args:
            lead: Lead object with surface data
            db: Database session
            user_id: User ID for audit (system user for auto-generation)
            
        Returns:
            Quote object if generated successfully, None otherwise
        """
        try:
            if not self.can_generate_quote(lead):
                logger.debug(f"Lead {lead.id} does not have sufficient data for quote generation")
                return None
            
            # Convert lead data to quote creation request format
            surfaces_dict = self._convert_lead_surfaces_to_quote_format(lead.extracted_surfaces)
            
            # Determine customer email (required for quote)
            customer_email = lead.contact_email or f"{lead.contact_name or 'customer'}@lead-{lead.id}.temp"
            
            # Create quote request
            quote_request = QuoteCreationRequest(
                organization_id=lead.organization_id,
                customer_email=customer_email,
                service_types=lead.requested_services,
                surfaces=surfaces_dict,
                customer_name=lead.contact_name,
                customer_phone=lead.contact_phone,
                customer_address=lead.contact_address,
                location=self._extract_location_from_lead(lead),
                customer_tier="standard",  # Default tier for lead-generated quotes
                rush_job=False,  # Auto-generated quotes are not rush jobs
                notes=f"Auto-generated from lead {lead.id} ({lead.source_platform} DM)",
                customer_notes="Quote generated from your inquiry. Please review and let us know if you have any questions!",
                source="lead_auto_generation",
                source_metadata={
                    "lead_id": lead.id,
                    "interaction_id": lead.interaction_id,
                    "source_platform": lead.source_platform,
                    "pricing_intent": lead.pricing_intent,
                    "priority_score": lead.priority_score
                },
                quote_validity_days=30
            )
            
            # Generate the quote
            quote = self.quote_service.create_quote(quote_request, db, user_id)
            
            # Link the quote to the lead
            quote.lead_id = lead.id
            db.commit()
            db.refresh(quote)
            
            # Log audit event
            audit_logger = get_audit_logger()
            audit_logger.log_event(
                event_type=AuditEventType.LEAD_CONVERTED_TO_QUOTE,
                user_id=str(user_id),
                organization_id=lead.organization_id,
                details={
                    "lead_id": lead.id,
                    "quote_id": quote.id,
                    "auto_generated": True,
                    "surfaces": list(surfaces_dict.keys()),
                    "total": float(quote.total),
                    "currency": quote.currency
                }
            )
            
            logger.info(f"Auto-generated draft quote {quote.id} from lead {lead.id}")
            return quote
            
        except Exception as e:
            logger.error(f"Error generating quote from lead {lead.id}: {str(e)}")
            raise
    
    def _convert_lead_surfaces_to_quote_format(self, extracted_surfaces: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Convert lead's extracted surfaces to quote service format
        
        Args:
            extracted_surfaces: Lead's extracted_surfaces field
            
        Returns:
            Dict in format expected by PricingService
        """
        surfaces_dict = {}
        
        for surface_name, surface_data in extracted_surfaces.items():
            if isinstance(surface_data, dict) and surface_data.get("area"):
                surfaces_dict[surface_name] = {
                    "area": surface_data["area"],
                    "difficulty": "medium",  # Default difficulty for auto-generated quotes
                    "condition": "fair"  # Default condition
                }
        
        return surfaces_dict
    
    def _extract_location_from_lead(self, lead: Lead) -> Optional[Dict[str, Any]]:
        """
        Extract location information from lead data
        
        Args:
            lead: Lead object
            
        Returns:
            Location dict or None
        """
        if lead.contact_address:
            return {
                "address": lead.contact_address,
                "distance_miles": 0.0,  # Default - would need geocoding to calculate actual distance
                "zip_code": None  # Would need to extract from address
            }
        
        return None
    
    def try_auto_quote_for_lead(
        self, 
        lead: Lead, 
        db: Session, 
        user_id: int
    ) -> Optional[Quote]:
        """
        Convenience method to try auto-generating a quote for a lead
        
        This is called after lead creation to see if we can immediately 
        create a draft quote from the extracted data.
        
        Args:
            lead: Newly created lead
            db: Database session
            user_id: User ID for audit
            
        Returns:
            Quote if generated, None if not enough data or generation failed
        """
        try:
            if self.can_generate_quote(lead):
                return self.generate_draft_quote(lead, db, user_id)
            else:
                logger.debug(f"Lead {lead.id} does not qualify for auto-quote generation")
                return None
                
        except Exception as e:
            logger.error(f"Failed to auto-generate quote for lead {lead.id}: {e}")
            # Don't propagate error - auto-quote is optional
            return None


def get_lead_quote_service() -> LeadQuoteService:
    """Factory function to get lead quote service instance"""
    return LeadQuoteService()


# Convenience function for integration
def try_create_draft_quote_for_lead(
    lead_id: str,
    db: Session,
    user_id: int
) -> Optional[Quote]:
    """
    Convenience function to try creating a draft quote for a lead by ID
    
    Used by webhook handlers and other services to attempt auto-quote generation.
    
    Args:
        lead_id: Lead ID to generate quote for
        db: Database session
        user_id: User ID for audit
        
    Returns:
        Quote if generated successfully, None otherwise
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        logger.warning(f"Lead {lead_id} not found for auto-quote generation")
        return None
    
    service = get_lead_quote_service()
    return service.try_auto_quote_for_lead(lead, db, user_id)