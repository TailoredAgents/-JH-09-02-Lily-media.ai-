"""
Pressure washing pricing API with multi-tenant RBAC
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
import logging

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from backend.db.database import get_db
from backend.core.security import get_current_active_user
from backend.db.models import User, PricingRule, Organization
from backend.services.pricing_service import PricingService, PricingQuoteRequest
from backend.services.settings_resolver import SettingsResolver
from backend.core.rbac import require_permission, get_user_permissions

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/pricing", tags=["Pricing Engine"])


# Request/Response Models
class SurfaceData(BaseModel):
    """Surface area and type information"""
    model_config = ConfigDict(from_attributes=True)
    
    area: float = Field(..., gt=0, description="Surface area in square feet")
    difficulty: Optional[str] = Field(None, description="Difficulty level: easy, medium, hard")
    condition: Optional[str] = Field(None, description="Surface condition: good, fair, poor")


class LocationData(BaseModel):
    """Location and travel information"""
    model_config = ConfigDict(from_attributes=True)
    
    address: Optional[str] = Field(None, description="Job site address")
    distance_miles: Optional[float] = Field(None, ge=0, description="Distance from base location")
    zip_code: Optional[str] = Field(None, description="ZIP code for tax calculations")


class QuoteRequest(BaseModel):
    """Pricing quote request"""
    model_config = ConfigDict(from_attributes=True)
    
    service_types: List[str] = Field(..., min_length=1, description="Types of services requested")
    surfaces: Dict[str, SurfaceData] = Field(..., description="Surface types and measurements")
    location: Optional[LocationData] = Field(None, description="Location information")
    preferred_date: Optional[date] = Field(None, description="Preferred service date")
    additional_services: List[str] = Field(default_factory=list, description="Additional services")
    customer_tier: str = Field(default="standard", description="Customer tier: standard, premium, vip")
    rush_job: bool = Field(default=False, description="Rush job requiring expedited service")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional request metadata")


class QuoteResponse(BaseModel):
    """Pricing quote response"""
    model_config = ConfigDict(from_attributes=True)
    
    base_total: float = Field(..., description="Base service total")
    bundle_discount: float = Field(..., description="Bundle discount amount (negative)")
    seasonal_modifier: float = Field(..., description="Seasonal pricing adjustment")
    travel_fee: float = Field(..., description="Travel/distance fee")
    rush_fee: float = Field(..., description="Rush job fee")
    additional_services_total: float = Field(..., description="Additional services total")
    subtotal: float = Field(..., description="Subtotal before tax")
    tax_rate: float = Field(..., description="Tax rate percentage")
    tax_amount: float = Field(..., description="Tax amount")
    total: float = Field(..., description="Final total amount")
    currency: str = Field(..., description="Currency code")
    breakdown: List[Dict[str, Any]] = Field(..., description="Detailed pricing breakdown")
    applied_rules: List[str] = Field(..., description="Applied pricing rules")
    warning_messages: List[str] = Field(..., description="Warning messages")
    valid_until: Optional[str] = Field(None, description="Quote expiration datetime")


class PricingRuleCreate(BaseModel):
    """Create pricing rule request"""
    model_config = ConfigDict(from_attributes=True)
    
    name: str = Field(..., min_length=1, max_length=255, description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$", description="ISO currency code")
    min_job_total: Decimal = Field(..., gt=0, description="Minimum job total")
    base_rates: Dict[str, Any] = Field(..., description="Base service rates")
    bundles: List[Dict[str, Any]] = Field(default_factory=list, description="Service bundles")
    seasonal_modifiers: Dict[str, float] = Field(default_factory=dict, description="Seasonal pricing modifiers")
    travel_settings: Dict[str, Any] = Field(..., description="Travel fee settings")
    additional_services: Dict[str, Any] = Field(default_factory=dict, description="Additional services pricing")
    business_rules: Dict[str, Any] = Field(..., description="Business rules and constraints")
    is_active: bool = Field(default=True, description="Whether rule is active")
    priority: int = Field(default=0, description="Rule priority (higher = more precedence)")
    effective_from: Optional[datetime] = Field(None, description="Rule effective start date")
    effective_until: Optional[datetime] = Field(None, description="Rule effective end date")


class PricingRuleResponse(BaseModel):
    """Pricing rule response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    organization_id: str
    name: str
    description: Optional[str]
    currency: str
    min_job_total: float
    base_rates: Dict[str, Any]
    bundles: List[Dict[str, Any]]
    seasonal_modifiers: Dict[str, float]
    travel_settings: Dict[str, Any]
    additional_services: Dict[str, Any]
    business_rules: Dict[str, Any]
    is_active: bool
    priority: int
    effective_from: Optional[str]
    effective_until: Optional[str]
    version: int
    created_by_id: int
    updated_by_id: Optional[int]
    created_at: str
    updated_at: Optional[str]


# Multi-tenant organization filtering
def get_organization_id(x_organization_id: Optional[str] = Header(None)) -> str:
    """Extract and validate organization ID from header"""
    if not x_organization_id:
        raise HTTPException(
            status_code=400, 
            detail="X-Organization-ID header is required for pricing operations"
        )
    return x_organization_id


def verify_organization_access(
    organization_id: str,
    current_user: User,
    db: Session
) -> Organization:
    """Verify user has access to organization and return org object"""
    # Check if organization exists
    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check if user belongs to organization (owner or member)
    # This should integrate with your actual RBAC system
    user_permissions = get_user_permissions(current_user.id, organization_id, db)
    if not any(perm.startswith('pricing.') for perm in user_permissions):
        raise HTTPException(
            status_code=403, 
            detail="Insufficient permissions for pricing operations in this organization"
        )
    
    return organization


# API Endpoints
@router.post("/quote", response_model=QuoteResponse)
async def compute_quote(
    request: QuoteRequest,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Compute a pricing quote for pressure washing services
    
    Requires: pricing.quote permission in the organization
    """
    # Verify organization access and permissions
    verify_organization_access(organization_id, current_user, db)
    require_permission(current_user.id, organization_id, "pricing.quote", db)
    
    try:
        # Convert Pydantic model to service model
        surfaces_dict = {k: v.model_dump() for k, v in request.surfaces.items()}
        location_dict = request.location.model_dump() if request.location else None
        
        quote_request = PricingQuoteRequest(
            organization_id=organization_id,
            service_types=request.service_types,
            surfaces=surfaces_dict,
            location=location_dict,
            preferred_date=request.preferred_date,
            additional_services=request.additional_services,
            customer_tier=request.customer_tier,
            rush_job=request.rush_job,
            metadata=request.metadata
        )
        
        # Initialize pricing service
        settings_resolver = SettingsResolver()
        pricing_service = PricingService(settings_resolver)
        
        # Compute quote
        quote = pricing_service.compute_quote(quote_request, db, current_user.id)
        
        # Convert to response model
        response_data = quote.to_dict()
        return QuoteResponse(**response_data)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error computing quote for org {organization_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error computing quote")


@router.post("/rules", response_model=PricingRuleResponse)
async def create_pricing_rule(
    rule_data: PricingRuleCreate,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new pricing rule for the organization
    
    Requires: pricing.rules.create permission in the organization
    """
    # Verify organization access and permissions
    verify_organization_access(organization_id, current_user, db)
    require_permission(current_user.id, organization_id, "pricing.rules.create", db)
    
    try:
        # Create new pricing rule
        pricing_rule = PricingRule(
            organization_id=organization_id,
            name=rule_data.name,
            description=rule_data.description,
            currency=rule_data.currency,
            min_job_total=rule_data.min_job_total,
            base_rates=rule_data.base_rates,
            bundles=rule_data.bundles,
            seasonal_modifiers=rule_data.seasonal_modifiers,
            travel_settings=rule_data.travel_settings,
            additional_services=rule_data.additional_services,
            business_rules=rule_data.business_rules,
            is_active=rule_data.is_active,
            priority=rule_data.priority,
            effective_from=rule_data.effective_from,
            effective_until=rule_data.effective_until,
            version=1,
            created_by_id=current_user.id
        )
        
        db.add(pricing_rule)
        db.commit()
        db.refresh(pricing_rule)
        
        # Convert to response format
        return PricingRuleResponse(
            id=pricing_rule.id,
            organization_id=pricing_rule.organization_id,
            name=pricing_rule.name,
            description=pricing_rule.description,
            currency=pricing_rule.currency,
            min_job_total=float(pricing_rule.min_job_total),
            base_rates=pricing_rule.base_rates,
            bundles=pricing_rule.bundles,
            seasonal_modifiers=pricing_rule.seasonal_modifiers,
            travel_settings=pricing_rule.travel_settings,
            additional_services=pricing_rule.additional_services,
            business_rules=pricing_rule.business_rules,
            is_active=pricing_rule.is_active,
            priority=pricing_rule.priority,
            effective_from=pricing_rule.effective_from.isoformat() if pricing_rule.effective_from else None,
            effective_until=pricing_rule.effective_until.isoformat() if pricing_rule.effective_until else None,
            version=pricing_rule.version,
            created_by_id=pricing_rule.created_by_id,
            updated_by_id=pricing_rule.updated_by_id,
            created_at=pricing_rule.created_at.isoformat(),
            updated_at=pricing_rule.updated_at.isoformat() if pricing_rule.updated_at else None
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating pricing rule for org {organization_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error creating pricing rule")


@router.get("/rules", response_model=List[PricingRuleResponse])
async def list_pricing_rules(
    organization_id: str = Depends(get_organization_id),
    active_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List pricing rules for the organization
    
    Requires: pricing.rules.read permission in the organization
    """
    # Verify organization access and permissions
    verify_organization_access(organization_id, current_user, db)
    require_permission(current_user.id, organization_id, "pricing.rules.read", db)
    
    try:
        query = db.query(PricingRule).filter(PricingRule.organization_id == organization_id)
        
        if active_only:
            query = query.filter(PricingRule.is_active == True)
        
        pricing_rules = query.order_by(
            PricingRule.priority.desc(),
            PricingRule.created_at.desc()
        ).all()
        
        return [
            PricingRuleResponse(
                id=rule.id,
                organization_id=rule.organization_id,
                name=rule.name,
                description=rule.description,
                currency=rule.currency,
                min_job_total=float(rule.min_job_total),
                base_rates=rule.base_rates,
                bundles=rule.bundles,
                seasonal_modifiers=rule.seasonal_modifiers,
                travel_settings=rule.travel_settings,
                additional_services=rule.additional_services,
                business_rules=rule.business_rules,
                is_active=rule.is_active,
                priority=rule.priority,
                effective_from=rule.effective_from.isoformat() if rule.effective_from else None,
                effective_until=rule.effective_until.isoformat() if rule.effective_until else None,
                version=rule.version,
                created_by_id=rule.created_by_id,
                updated_by_id=rule.updated_by_id,
                created_at=rule.created_at.isoformat(),
                updated_at=rule.updated_at.isoformat() if rule.updated_at else None
            )
            for rule in pricing_rules
        ]
        
    except Exception as e:
        logger.error(f"Error listing pricing rules for org {organization_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error listing pricing rules")


@router.get("/rules/{rule_id}", response_model=PricingRuleResponse)
async def get_pricing_rule(
    rule_id: int,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific pricing rule by ID
    
    Requires: pricing.rules.read permission in the organization
    """
    # Verify organization access and permissions
    verify_organization_access(organization_id, current_user, db)
    require_permission(current_user.id, organization_id, "pricing.rules.read", db)
    
    try:
        pricing_rule = db.query(PricingRule).filter(
            PricingRule.id == rule_id,
            PricingRule.organization_id == organization_id
        ).first()
        
        if not pricing_rule:
            raise HTTPException(status_code=404, detail="Pricing rule not found")
        
        return PricingRuleResponse(
            id=pricing_rule.id,
            organization_id=pricing_rule.organization_id,
            name=pricing_rule.name,
            description=pricing_rule.description,
            currency=pricing_rule.currency,
            min_job_total=float(pricing_rule.min_job_total),
            base_rates=pricing_rule.base_rates,
            bundles=pricing_rule.bundles,
            seasonal_modifiers=pricing_rule.seasonal_modifiers,
            travel_settings=pricing_rule.travel_settings,
            additional_services=pricing_rule.additional_services,
            business_rules=pricing_rule.business_rules,
            is_active=pricing_rule.is_active,
            priority=pricing_rule.priority,
            effective_from=pricing_rule.effective_from.isoformat() if pricing_rule.effective_from else None,
            effective_until=pricing_rule.effective_until.isoformat() if pricing_rule.effective_until else None,
            version=pricing_rule.version,
            created_by_id=pricing_rule.created_by_id,
            updated_by_id=pricing_rule.updated_by_id,
            created_at=pricing_rule.created_at.isoformat(),
            updated_at=pricing_rule.updated_at.isoformat() if pricing_rule.updated_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pricing rule {rule_id} for org {organization_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving pricing rule")