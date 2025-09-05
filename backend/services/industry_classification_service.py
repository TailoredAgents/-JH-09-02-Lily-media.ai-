"""
Autonomous Industry Classification Service

This service automatically classifies companies and organizations into industries 
for targeted content generation and research.
"""
import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.db.models import Organization, User
from backend.agents.tools import openai_tool
from backend.core.observability import get_observability_manager

logger = logging.getLogger(__name__)

# Industry mapping with research topics
INDUSTRY_RESEARCH_MAPPING = {
    "technology": {
        "display_name": "Technology & Software",
        "research_topics": ["technology trends", "software development", "digital transformation", "tech startups"],
        "keywords": ["software", "tech", "AI", "SaaS", "platform", "digital", "development", "programming"]
    },
    "healthcare": {
        "display_name": "Healthcare & Medical",
        "research_topics": ["healthcare innovation", "medical technology", "patient care", "health trends"],
        "keywords": ["health", "medical", "clinic", "hospital", "wellness", "pharmacy", "treatment"]
    },
    "finance": {
        "display_name": "Finance & Banking",
        "research_topics": ["financial services", "fintech", "banking trends", "investment strategies"],
        "keywords": ["bank", "finance", "investment", "fintech", "insurance", "accounting", "wealth"]
    },
    "retail": {
        "display_name": "Retail & E-commerce",
        "research_topics": ["retail trends", "e-commerce", "consumer behavior", "retail technology"],
        "keywords": ["retail", "store", "shop", "e-commerce", "consumer", "merchandise", "sales"]
    },
    "restaurant": {
        "display_name": "Food & Restaurant",
        "research_topics": ["food industry", "restaurant trends", "culinary innovation", "hospitality"],
        "keywords": ["restaurant", "food", "dining", "culinary", "cafe", "catering", "hospitality"]
    },
    "law_firm": {
        "display_name": "Legal Services",
        "research_topics": ["legal technology", "law practice", "legal trends", "compliance"],
        "keywords": ["law", "legal", "attorney", "lawyer", "court", "litigation", "compliance"]
    },
    "consulting": {
        "display_name": "Consulting & Professional Services",
        "research_topics": ["business consulting", "professional services", "management trends", "strategy"],
        "keywords": ["consulting", "advisory", "strategy", "management", "professional services"]
    },
    "manufacturing": {
        "display_name": "Manufacturing & Industrial",
        "research_topics": ["manufacturing trends", "industrial automation", "supply chain", "production"],
        "keywords": ["manufacturing", "factory", "production", "industrial", "supply chain", "logistics"]
    },
    "education": {
        "display_name": "Education & Training",
        "research_topics": ["education technology", "learning trends", "academic innovation", "training"],
        "keywords": ["education", "school", "university", "learning", "training", "academic", "teaching"]
    },
    "real_estate": {
        "display_name": "Real Estate & Property",
        "research_topics": ["real estate trends", "property market", "construction", "urban development"],
        "keywords": ["real estate", "property", "construction", "housing", "commercial", "residential"]
    },
    "marketing": {
        "display_name": "Marketing & Advertising",
        "research_topics": ["marketing trends", "digital marketing", "advertising innovation", "brand strategy"],
        "keywords": ["marketing", "advertising", "branding", "agency", "creative", "media", "campaign"]
    },
    "general": {
        "display_name": "General Business",
        "research_topics": ["business trends", "entrepreneurship", "small business", "general industry"],
        "keywords": ["business", "company", "enterprise", "startup", "general"]
    }
}

class IndustryClassificationService:
    """Service for automatic industry classification and research topic generation"""
    
    def __init__(self):
        self.observability = get_observability_manager()
    
    async def classify_company_industry(self, company_name: str, company_description: str = "") -> Tuple[str, float]:
        """
        Automatically classify a company's industry using AI analysis
        
        Args:
            company_name: The company name
            company_description: Optional company description
            
        Returns:
            Tuple of (industry_code, confidence_score)
        """
        
        try:
            # Create a sophisticated prompt for industry classification
            prompt = f"""You are an expert business analyst. Classify the following company into one of these specific industry categories:

COMPANY: {company_name}
DESCRIPTION: {company_description or "No description provided"}

INDUSTRY OPTIONS (choose exactly one):
- technology: Software, SaaS, AI, tech platforms, development
- healthcare: Medical, wellness, clinics, pharmaceuticals, health services
- finance: Banking, fintech, investment, insurance, accounting
- retail: E-commerce, stores, consumer products, merchandise
- restaurant: Food service, dining, catering, hospitality
- law_firm: Legal services, attorneys, law practice
- consulting: Business consulting, professional services, strategy
- manufacturing: Production, factories, industrial, logistics
- education: Schools, training, learning platforms, academic
- real_estate: Property, construction, housing, commercial real estate
- marketing: Advertising agencies, marketing services, branding
- general: If none of the above clearly fit

ANALYSIS CRITERIA:
1. Company name indicates industry (e.g., "TechCorp" suggests technology)
2. Description mentions specific industry terms
3. Business model alignment with industry categories

RESPONSE FORMAT: Return only the industry code (e.g., "technology") and confidence score 0-1.
FORMAT: industry_code,confidence_score

Example: technology,0.85"""

            response = await openai_tool.generate_text(prompt, max_tokens=50)
            
            if response and "," in response:
                # Parse the response
                parts = response.strip().split(",")
                industry_code = parts[0].strip().lower()
                
                try:
                    confidence_score = float(parts[1].strip())
                except (ValueError, IndexError):
                    confidence_score = 0.7  # Default confidence
                
                # Validate industry code
                if industry_code in INDUSTRY_RESEARCH_MAPPING:
                    logger.info(f"Classified {company_name} as {industry_code} with confidence {confidence_score}")
                    return industry_code, confidence_score
                else:
                    logger.warning(f"Unknown industry code {industry_code} for {company_name}, defaulting to general")
                    return "general", 0.5
            else:
                # Fallback: keyword-based classification
                return await self._fallback_keyword_classification(company_name, company_description)
                
        except Exception as e:
            logger.error(f"AI classification failed for {company_name}: {e}")
            return await self._fallback_keyword_classification(company_name, company_description)
    
    async def _fallback_keyword_classification(self, company_name: str, company_description: str) -> Tuple[str, float]:
        """Fallback keyword-based classification"""
        
        text_to_analyze = f"{company_name} {company_description}".lower()
        
        # Score each industry based on keyword matches
        industry_scores = {}
        
        for industry_code, industry_data in INDUSTRY_RESEARCH_MAPPING.items():
            score = 0
            for keyword in industry_data["keywords"]:
                if keyword.lower() in text_to_analyze:
                    score += 1
            
            if score > 0:
                # Normalize by number of keywords
                industry_scores[industry_code] = score / len(industry_data["keywords"])
        
        if industry_scores:
            # Get the highest scoring industry
            best_industry = max(industry_scores, key=industry_scores.get)
            confidence = min(industry_scores[best_industry] * 2, 1.0)  # Scale up but cap at 1.0
            
            logger.info(f"Keyword classification: {company_name} -> {best_industry} (confidence: {confidence})")
            return best_industry, confidence
        else:
            logger.info(f"No keyword matches for {company_name}, defaulting to general")
            return "general", 0.3
    
    def get_industry_research_topics(self, industry_code: str) -> List[str]:
        """Get research topics for a specific industry"""
        
        industry_data = INDUSTRY_RESEARCH_MAPPING.get(industry_code, INDUSTRY_RESEARCH_MAPPING["general"])
        return industry_data["research_topics"]
    
    def get_industry_display_name(self, industry_code: str) -> str:
        """Get human-readable industry name"""
        
        industry_data = INDUSTRY_RESEARCH_MAPPING.get(industry_code, INDUSTRY_RESEARCH_MAPPING["general"])
        return industry_data["display_name"]
    
    async def auto_classify_user_industry(self, user_id: int, db: Session) -> Optional[str]:
        """
        Automatically classify user's industry based on their organization and research data
        
        Args:
            user_id: User ID to classify
            db: Database session
            
        Returns:
            Industry code or None if classification fails
        """
        
        try:
            # Get user and organization
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.default_organization_id:
                logger.warning(f"User {user_id} has no organization")
                return None
            
            organization = db.query(Organization).filter(Organization.id == user.default_organization_id).first()
            if not organization:
                logger.warning(f"Organization not found for user {user_id}")
                return None
            
            # If organization already has industry_type set and it's not 'general', use it
            if organization.industry_type and organization.industry_type != "general":
                if organization.industry_type in INDUSTRY_RESEARCH_MAPPING:
                    logger.info(f"Using existing industry classification: {organization.industry_type}")
                    return organization.industry_type
            
            # Otherwise, try to classify based on organization name and any available description
            company_name = organization.company_name or organization.name or f"Organization {organization.id}"
            description = ""  # Could add organization description field in future
            
            industry_code, confidence = await self.classify_company_industry(company_name, description)
            
            # Update organization if we have high confidence
            if confidence > 0.6:
                organization.industry_type = industry_code
                db.commit()
                logger.info(f"Updated organization {organization.id} industry to {industry_code}")
            
            return industry_code
            
        except Exception as e:
            logger.error(f"Failed to auto-classify industry for user {user_id}: {e}")
            return None
    
    def list_supported_industries(self) -> Dict[str, str]:
        """Get list of supported industries with display names"""
        
        return {
            code: data["display_name"] 
            for code, data in INDUSTRY_RESEARCH_MAPPING.items()
        }

# Create singleton instance
industry_classification_service = IndustryClassificationService()