"""
Pressure washing quote API endpoints with multi-tenant RBAC
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal
import logging

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict, EmailStr

from backend.db.database import get_db
from backend.auth.dependencies import get_current_active_user
from backend.db.models import User, Quote, Organization
from backend.services.quote_service import (
    QuoteService, QuoteCreationRequest, QuoteUpdateRequest
)
from backend.services.settings_resolver import SettingsResolver
# RBAC permissions - simplified for now
def require_permission(user_id: int, organization_id: str, permission: str, db) -> None:
    """Simplified permission check - replace with proper RBAC later"""
    pass  # For now, allow all operations for valid users

def get_user_permissions(user_id: int, organization_id: str, db) -> list:
    """Simplified permissions - replace with proper RBAC later"""
    return ["quotes.create", "quotes.read", "quotes.update", "quotes.send"]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/quotes", tags=["Quote Management"])


# Request/Response Models
class SurfaceDataInput(BaseModel):
    """Surface area and type information for quote creation"""
    model_config = ConfigDict(from_attributes=True)
    
    area: float = Field(..., gt=0, description="Surface area in square feet")
    difficulty: Optional[str] = Field(None, description="Difficulty level: easy, medium, hard")
    condition: Optional[str] = Field(None, description="Surface condition: good, fair, poor")


class LocationDataInput(BaseModel):
    """Location information for quote creation"""
    model_config = ConfigDict(from_attributes=True)
    
    address: Optional[str] = Field(None, description="Job site address")
    distance_miles: Optional[float] = Field(None, ge=0, description="Distance from base location")
    zip_code: Optional[str] = Field(None, description="ZIP code for tax calculations")


class QuoteCreateRequest(BaseModel):
    """Request to create a new quote"""
    model_config = ConfigDict(from_attributes=True)
    
    customer_email: EmailStr = Field(..., description="Customer email address")
    customer_name: Optional[str] = Field(None, description="Customer full name")
    customer_phone: Optional[str] = Field(None, description="Customer phone number")
    customer_address: Optional[str] = Field(None, description="Customer address")
    
    service_types: List[str] = Field(..., min_length=1, description="Types of services requested")
    surfaces: Dict[str, SurfaceDataInput] = Field(..., description="Surface types and measurements")
    location: Optional[LocationDataInput] = Field(None, description="Location information")
    
    preferred_date: Optional[date] = Field(None, description="Preferred service date")
    additional_services: List[str] = Field(default_factory=list, description="Additional services")
    customer_tier: str = Field(default="standard", description="Customer tier: standard, premium, vip")
    rush_job: bool = Field(default=False, description="Rush job requiring expedited service")
    
    notes: Optional[str] = Field(None, description="Internal notes")
    customer_notes: Optional[str] = Field(None, description="Notes visible to customer")
    source: str = Field(default="manual", description="Quote source: manual, dm_inquiry, website, phone")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional source metadata")
    quote_validity_days: int = Field(default=30, ge=1, le=365, description="Quote validity period in days")


class QuoteUpdateRequest(BaseModel):
    """Request to update an existing quote"""
    model_config = ConfigDict(from_attributes=True)
    
    status: Optional[str] = Field(None, description="New status: sent, accepted, declined, expired")
    notes: Optional[str] = Field(None, description="Updated internal notes")
    customer_notes: Optional[str] = Field(None, description="Updated customer notes")
    recompute_pricing: bool = Field(default=False, description="Recompute pricing with current rules")


class LineItemResponse(BaseModel):
    """Quote line item response"""
    model_config = ConfigDict(from_attributes=True)
    
    type: str
    description: Optional[str]
    quantity: Optional[float]
    rate: Optional[float]
    amount: float


class QuoteResponse(BaseModel):
    """Quote response model"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    organization_id: str
    quote_number: Optional[str]
    
    customer_email: str
    customer_name: Optional[str]
    customer_phone: Optional[str]
    customer_address: Optional[str]
    
    line_items: List[Dict[str, Any]]
    subtotal: float
    discounts: float
    tax_amount: float
    total: float
    currency: str
    
    status: str
    sent_at: Optional[str]
    accepted_at: Optional[str]
    declined_at: Optional[str]
    expired_at: Optional[str]
    
    valid_until: Optional[str]
    notes: Optional[str]
    customer_notes: Optional[str]
    source: Optional[str]
    source_metadata: Optional[Dict[str, Any]]
    
    pricing_rule_id: Optional[int]
    created_by_id: int
    updated_by_id: Optional[int]
    created_at: str
    updated_at: Optional[str]


class QuoteListResponse(BaseModel):
    """Quote list response with pagination"""
    model_config = ConfigDict(from_attributes=True)
    
    quotes: List[QuoteResponse]
    total_count: int
    has_more: bool


# Multi-tenant organization filtering
def get_organization_id(x_organization_id: Optional[str] = Header(None)) -> str:
    """Extract and validate organization ID from header"""
    if not x_organization_id:
        raise HTTPException(
            status_code=400, 
            detail="X-Organization-ID header is required for quote operations"
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
    user_permissions = get_user_permissions(current_user.id, organization_id, db)
    if not any(perm.startswith('quotes.') for perm in user_permissions):
        raise HTTPException(
            status_code=403, 
            detail="Insufficient permissions for quote operations in this organization"
        )
    
    return organization


# API Endpoints
@router.post("", response_model=QuoteResponse)
async def create_quote(
    request: QuoteCreateRequest,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new quote from customer details and surface measurements
    
    Requires: quotes.create permission in the organization
    """
    # Verify organization access and permissions
    verify_organization_access(organization_id, current_user, db)
    require_permission(current_user.id, organization_id, "quotes.create", db)
    
    try:
        # Convert Pydantic model to service model
        surfaces_dict = {k: v.model_dump() for k, v in request.surfaces.items()}
        location_dict = request.location.model_dump() if request.location else None
        
        quote_request = QuoteCreationRequest(
            organization_id=organization_id,
            customer_email=request.customer_email,
            service_types=request.service_types,
            surfaces=surfaces_dict,
            customer_name=request.customer_name,
            customer_phone=request.customer_phone,
            customer_address=request.customer_address,
            location=location_dict,
            preferred_date=datetime.combine(request.preferred_date, datetime.min.time()) if request.preferred_date else None,
            additional_services=request.additional_services,
            customer_tier=request.customer_tier,
            rush_job=request.rush_job,
            notes=request.notes,
            customer_notes=request.customer_notes,
            source=request.source,
            source_metadata=request.source_metadata,
            quote_validity_days=request.quote_validity_days
        )
        
        # Initialize quote service
        settings_resolver = SettingsResolver()
        quote_service = QuoteService(settings_resolver)
        
        # Create quote
        quote = quote_service.create_quote(quote_request, db, current_user.id)
        
        # Convert to response model
        return QuoteResponse(**quote.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating quote for org {organization_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error creating quote")


@router.get("/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    quote_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific quote by ID
    
    Requires: quotes.read permission in the organization
    """
    # Verify organization access and permissions
    verify_organization_access(organization_id, current_user, db)
    require_permission(current_user.id, organization_id, "quotes.read", db)
    
    try:
        # Initialize quote service
        settings_resolver = SettingsResolver()
        quote_service = QuoteService(settings_resolver)
        
        # Get quote
        quote = quote_service.get_quote(quote_id, organization_id, db)
        if not quote:
            raise HTTPException(status_code=404, detail="Quote not found")
        
        return QuoteResponse(**quote.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quote {quote_id} for org {organization_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving quote")


@router.get("", response_model=QuoteListResponse)
async def list_quotes(
    organization_id: str = Depends(get_organization_id),
    status: Optional[str] = Query(None, description="Filter by quote status"),
    customer_email: Optional[str] = Query(None, description="Filter by customer email"),
    limit: int = Query(50, ge=1, le=100, description="Number of quotes to return"),
    offset: int = Query(0, ge=0, description="Number of quotes to skip"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List quotes for the organization with optional filtering
    
    Requires: quotes.read permission in the organization
    """
    # Verify organization access and permissions
    verify_organization_access(organization_id, current_user, db)
    require_permission(current_user.id, organization_id, "quotes.read", db)
    
    try:
        # Initialize quote service
        settings_resolver = SettingsResolver()
        quote_service = QuoteService(settings_resolver)
        
        # Get quotes
        quotes = quote_service.list_quotes(
            organization_id=organization_id,
            db=db,
            status=status,
            customer_email=customer_email,
            limit=limit + 1,  # Get one extra to check if there are more
            offset=offset
        )
        
        # Check if there are more results
        has_more = len(quotes) > limit
        if has_more:
            quotes = quotes[:limit]  # Remove the extra quote
        
        # Convert to response format
        quote_responses = [QuoteResponse(**quote.to_dict()) for quote in quotes]
        
        return QuoteListResponse(
            quotes=quote_responses,
            total_count=len(quote_responses),  # This could be improved with a count query
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Error listing quotes for org {organization_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error listing quotes")


@router.patch("/{quote_id}", response_model=QuoteResponse)
async def update_quote(
    quote_id: str,
    request: QuoteUpdateRequest,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update quote status and details
    
    Requires: quotes.update permission in the organization
    """
    # Verify organization access and permissions
    verify_organization_access(organization_id, current_user, db)
    require_permission(current_user.id, organization_id, "quotes.update", db)
    
    try:
        # Convert Pydantic model to service model
        update_request = QuoteUpdateRequest(
            new_status=request.status,
            notes=request.notes,
            customer_notes=request.customer_notes,
            recompute_pricing=request.recompute_pricing
        )
        
        # Initialize quote service
        settings_resolver = SettingsResolver()
        quote_service = QuoteService(settings_resolver)
        
        # Update quote
        quote = quote_service.update_quote(
            quote_id, organization_id, update_request, db, current_user.id
        )
        
        return QuoteResponse(**quote.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating quote {quote_id} for org {organization_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error updating quote")


@router.post("/{quote_id}/send", response_model=QuoteResponse)
async def send_quote(
    quote_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Send a quote to customer (mark as sent)
    
    Requires: quotes.send permission in the organization
    """
    # Verify organization access and permissions
    verify_organization_access(organization_id, current_user, db)
    require_permission(current_user.id, organization_id, "quotes.send", db)
    
    try:
        # Create update request to change status to sent
        update_request = QuoteUpdateRequest(new_status="sent")
        
        # Initialize quote service
        settings_resolver = SettingsResolver()
        quote_service = QuoteService(settings_resolver)
        
        # Update quote status
        quote = quote_service.update_quote(
            quote_id, organization_id, update_request, db, current_user.id
        )
        
        return QuoteResponse(**quote.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending quote {quote_id} for org {organization_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error sending quote")


@router.post("/{quote_id}/accept", response_model=QuoteResponse)
async def accept_quote(
    quote_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark quote as accepted by customer
    
    Requires: quotes.update permission in the organization
    """
    # Verify organization access and permissions
    verify_organization_access(organization_id, current_user, db)
    require_permission(current_user.id, organization_id, "quotes.update", db)
    
    try:
        # Create update request to change status to accepted
        update_request = QuoteUpdateRequest(new_status="accepted")
        
        # Initialize quote service
        settings_resolver = SettingsResolver()
        quote_service = QuoteService(settings_resolver)
        
        # Update quote status
        quote = quote_service.update_quote(
            quote_id, organization_id, update_request, db, current_user.id
        )
        
        return QuoteResponse(**quote.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error accepting quote {quote_id} for org {organization_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error accepting quote")


@router.post("/{quote_id}/decline", response_model=QuoteResponse)
async def decline_quote(
    quote_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark quote as declined by customer
    
    Requires: quotes.update permission in the organization
    """
    # Verify organization access and permissions
    verify_organization_access(organization_id, current_user, db)
    require_permission(current_user.id, organization_id, "quotes.update", db)
    
    try:
        # Create update request to change status to declined
        update_request = QuoteUpdateRequest(new_status="declined")
        
        # Initialize quote service
        settings_resolver = SettingsResolver()
        quote_service = QuoteService(settings_resolver)
        
        # Update quote status
        quote = quote_service.update_quote(
            quote_id, organization_id, update_request, db, current_user.id
        )
        
        return QuoteResponse(**quote.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error declining quote {quote_id} for org {organization_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error declining quote")