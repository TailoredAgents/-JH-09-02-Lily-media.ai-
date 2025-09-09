"""
PW-DM-REPLACE-001: DM Lead Creation Service

Service for detecting pricing intent in DMs and creating leads from social interactions.
Converts DMs with pressure washing inquiries into actionable sales leads.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.db.models import SocialInteraction, Lead, User, Organization
from backend.core.audit_logger import get_audit_logger, AuditEventType

logger = logging.getLogger(__name__)


class DMIntentDetector:
    """
    Simple keyword-based intent detection for pressure washing DMs
    
    Detects pricing intent and extracts basic surface/area information from DM content.
    Can be enhanced with ML/AI classification in the future.
    """
    
    # Keywords that indicate pricing intent
    PRICING_KEYWORDS = {
        "quote_request": [
            "quote", "estimate", "how much", "cost", "price", "pricing", 
            "what would you charge", "what do you charge", "how much would"
        ],
        "price_inquiry": [
            "expensive", "cheap", "affordable", "budget", "rates", 
            "ballpark", "rough idea", "starting at"
        ],
        "service_interest": [
            "pressure wash", "power wash", "clean", "washing", "cleaning",
            "driveway", "house", "deck", "patio", "concrete", "siding"
        ]
    }
    
    # Surface type keywords for extraction
    SURFACE_KEYWORDS = {
        "driveway": ["driveway", "drive way", "drive-way"],
        "house_siding": ["house", "siding", "vinyl", "home exterior"],
        "deck": ["deck", "wooden deck", "wood deck"],
        "patio": ["patio", "patio area"],
        "concrete": ["concrete", "concrete pad", "cement"],
        "walkway": ["walkway", "walk way", "sidewalk", "side walk"],
        "fence": ["fence", "fencing"],
        "roof": ["roof", "roofing"]
    }
    
    # Area/size extraction patterns
    AREA_PATTERNS = [
        r"(\d+)\s*(?:sq\.?\s*ft\.?|square feet|sqft)",  # "1500 sq ft", "2000 square feet"
        r"(\d+)\s*x\s*(\d+)",  # "20 x 30"
        r"(\d+)\s*by\s*(\d+)",  # "20 by 30"
        r"(\d+)\s*(?:foot|ft\.?)\s*(?:by|x)\s*(\d+)\s*(?:foot|ft\.?)",  # "20 foot by 30 foot"
    ]
    
    def detect_intent(self, content: str) -> Optional[str]:
        """
        Detect pricing intent in DM content
        
        Returns:
            str: Intent type ("quote_request", "price_inquiry", "service_interest") or None
        """
        content_lower = content.lower()
        
        # Check for quote request keywords (highest priority)
        for keyword in self.PRICING_KEYWORDS["quote_request"]:
            if keyword in content_lower:
                return "quote_request"
        
        # Check for price inquiry keywords
        for keyword in self.PRICING_KEYWORDS["price_inquiry"]:
            if keyword in content_lower:
                return "price_inquiry"
        
        # Check for general service interest
        service_count = 0
        for keyword in self.PRICING_KEYWORDS["service_interest"]:
            if keyword in content_lower:
                service_count += 1
        
        # If multiple service keywords found, likely service interest
        if service_count >= 2:
            return "service_interest"
        
        return None
    
    def extract_surfaces(self, content: str) -> Dict[str, Any]:
        """
        Extract surface types and potential area information from DM content
        
        Returns:
            Dict with detected surfaces and any area information
        """
        content_lower = content.lower()
        extracted_surfaces = {}
        
        # Detect surface types
        for surface_type, keywords in self.SURFACE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    extracted_surfaces[surface_type] = {"mentioned": True}
                    
                    # Try to find area information near this surface mention
                    area = self._extract_area_near_keyword(content, keyword)
                    if area:
                        extracted_surfaces[surface_type]["area"] = area
                    
                    break
        
        return extracted_surfaces
    
    def _extract_area_near_keyword(self, content: str, keyword: str) -> Optional[float]:
        """
        Try to extract area information near a surface keyword
        """
        content_lower = content.lower()
        keyword_pos = content_lower.find(keyword)
        
        if keyword_pos == -1:
            return None
        
        # Look for area patterns within 50 characters before/after the keyword
        start = max(0, keyword_pos - 50)
        end = min(len(content), keyword_pos + len(keyword) + 50)
        nearby_text = content[start:end]
        
        for pattern in self.AREA_PATTERNS:
            match = re.search(pattern, nearby_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 1:
                    # Single number (assume square feet)
                    return float(groups[0])
                elif len(groups) == 2:
                    # Two dimensions (calculate area)
                    return float(groups[0]) * float(groups[1])
        
        return None
    
    def calculate_priority_score(self, intent: str, extracted_surfaces: Dict[str, Any], content: str) -> float:
        """
        Calculate priority score (0-100) based on intent strength and available details
        """
        score = 0.0
        
        # Base score by intent type
        intent_scores = {
            "quote_request": 80.0,  # Highest priority - direct quote request
            "price_inquiry": 60.0,  # Medium priority - interested in pricing
            "service_interest": 40.0  # Lower priority - general interest
        }
        
        score = intent_scores.get(intent, 0.0)
        
        # Bonus for surface information
        score += len(extracted_surfaces) * 5.0
        
        # Bonus for area information
        for surface_data in extracted_surfaces.values():
            if surface_data.get("area"):
                score += 10.0
        
        # Bonus for contact information in message
        content_lower = content.lower()
        if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', content):  # Phone number
            score += 5.0
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content):  # Email
            score += 5.0
        if any(word in content_lower for word in ["address", "location", "live at", "located"]):
            score += 3.0
        
        return min(score, 100.0)  # Cap at 100


class DMLeadService:
    """
    Service for creating leads from social media DMs with pricing intent
    """
    
    def __init__(self):
        self.intent_detector = DMIntentDetector()
    
    def create_lead_from_dm(
        self, 
        interaction: SocialInteraction, 
        organization_id: str,
        db: Session, 
        user_id: int
    ) -> Optional[Lead]:
        """
        Analyze a DM interaction and create a lead if pricing intent is detected
        
        Args:
            interaction: SocialInteraction record from DM
            organization_id: Organization ID for multi-tenancy
            db: Database session
            user_id: User ID creating the lead (for audit)
        
        Returns:
            Lead object if created, None if no intent detected
        """
        try:
            # Only process DMs
            if interaction.interaction_type != "dm":
                logger.debug(f"Interaction {interaction.id} is not a DM, skipping lead creation")
                return None
            
            # Detect intent in the DM content
            intent = self.intent_detector.detect_intent(interaction.content)
            if not intent:
                logger.debug(f"No pricing intent detected in interaction {interaction.id}")
                return None
            
            logger.info(f"Detected {intent} intent in DM {interaction.id}")
            
            # Extract surface and area information
            extracted_surfaces = self.intent_detector.extract_surfaces(interaction.content)
            
            # Calculate priority score
            priority_score = self.intent_detector.calculate_priority_score(
                intent, extracted_surfaces, interaction.content
            )
            
            # Determine requested services based on detected surfaces and intent
            requested_services = self._determine_services(extracted_surfaces, intent)
            
            # Extract contact information from DM author
            contact_name = interaction.author_display_name or interaction.author_username
            
            # Create lead
            lead = Lead(
                organization_id=organization_id,
                interaction_id=interaction.id,
                source_platform=interaction.platform,
                contact_name=contact_name,
                contact_email=None,  # Would need additional extraction or API call
                contact_phone=None,  # Would need additional extraction
                contact_address=None,  # Would need additional extraction or customer input
                requested_services=requested_services,
                pricing_intent=intent,
                extracted_surfaces=extracted_surfaces,
                extracted_details={
                    "author_platform_id": interaction.author_platform_id,
                    "author_username": interaction.author_username,
                    "author_profile_url": interaction.author_profile_url,
                    "original_message": interaction.content,
                    "platform_metadata": interaction.platform_metadata
                },
                status="new",
                priority_score=priority_score,
                created_by_id=user_id
            )
            
            db.add(lead)
            db.commit()
            db.refresh(lead)
            
            # Log audit event
            audit_logger = get_audit_logger()
            audit_logger.log_event(
                event_type=AuditEventType.LEAD_CREATED,
                user_id=str(user_id),
                organization_id=organization_id,
                details={
                    "lead_id": lead.id,
                    "interaction_id": interaction.id,
                    "source_platform": interaction.platform,
                    "intent": intent,
                    "priority_score": priority_score,
                    "surfaces_detected": list(extracted_surfaces.keys()),
                    "services_requested": requested_services
                }
            )
            
            logger.info(f"Created lead {lead.id} from DM interaction {interaction.id} with {intent} intent")
            
            # PW-DM-REPLACE-001: Try to auto-generate draft quote if lead has sufficient surface data
            try:
                from backend.services.lead_quote_service import get_lead_quote_service
                lead_quote_service = get_lead_quote_service()
                draft_quote = lead_quote_service.try_auto_quote_for_lead(lead, db, user_id)
                
                if draft_quote:
                    logger.info(f"Auto-generated draft quote {draft_quote.id} for lead {lead.id}")
                else:
                    logger.debug(f"Lead {lead.id} did not qualify for auto-quote generation")
                    
            except Exception as e:
                logger.error(f"Failed to auto-generate quote for lead {lead.id}: {e}")
                # Don't fail lead creation if auto-quote fails
            
            return lead
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating lead from DM {interaction.id}: {str(e)}")
            raise
    
    def _determine_services(self, extracted_surfaces: Dict[str, Any], intent: str) -> List[str]:
        """
        Determine requested services based on detected surfaces and intent
        """
        services = []
        
        # Map surfaces to services
        surface_to_service = {
            "driveway": "driveway_cleaning",
            "house_siding": "house_washing", 
            "deck": "deck_cleaning",
            "patio": "patio_cleaning",
            "concrete": "concrete_cleaning",
            "walkway": "walkway_cleaning",
            "fence": "fence_cleaning",
            "roof": "roof_cleaning"
        }
        
        # Add services based on detected surfaces
        for surface in extracted_surfaces.keys():
            if surface in surface_to_service:
                service = surface_to_service[surface]
                if service not in services:
                    services.append(service)
        
        # If no specific services detected but has intent, add general service
        if not services and intent in ["quote_request", "price_inquiry", "service_interest"]:
            services.append("pressure_washing")
        
        return services


# Audit event types for leads (add to audit_logger.py)
class LeadAuditEventType:
    LEAD_CREATED = "lead_created"
    LEAD_UPDATED = "lead_updated" 
    LEAD_STATUS_CHANGED = "lead_status_changed"
    LEAD_CONVERTED_TO_QUOTE = "lead_converted_to_quote"


def get_dm_lead_service() -> DMLeadService:
    """Factory function to get DM lead service instance"""
    return DMLeadService()


# Convenience functions for webhook integration
def create_lead_from_dm_interaction(
    interaction_id: str,
    organization_id: str, 
    db: Session,
    user_id: int
) -> Optional[Lead]:
    """
    Convenience function to create a lead from an interaction ID
    
    Used by webhook handlers to process DMs after they're stored.
    """
    interaction = db.query(SocialInteraction).filter(
        SocialInteraction.id == interaction_id
    ).first()
    
    if not interaction:
        logger.warning(f"Interaction {interaction_id} not found for lead creation")
        return None
    
    service = get_dm_lead_service()
    return service.create_lead_from_dm(interaction, organization_id, db, user_id)