"""
PW-DM-ADD-002: Leads API

API endpoints for managing pressure washing leads, including media attachment 
and auto-quote generation integration.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from backend.db.database import get_db
from backend.auth.dependencies import get_current_active_user
from backend.db.models import User, Lead, MediaAsset, Quote
from backend.middleware.tenant_context import get_tenant_context, TenantContext, require_role
from backend.services.lead_quote_service import get_lead_quote_service
from backend.core.audit_logger import get_audit_logger, AuditEventType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/leads", tags=["Leads"])


# Request/Response Models

class MediaAttachmentRequest(BaseModel):
    """Request to attach media asset to lead"""
    model_config = ConfigDict(from_attributes=True)
    
    media_asset_id: str = Field(..., description="Media asset ID to attach to lead")
    description: Optional[str] = Field(None, description="Optional description of the media")
    tags: list[str] = Field(default_factory=list, description="Optional tags for the media")


class MediaAttachmentResponse(BaseModel):
    """Response from media attachment operation"""
    model_config = ConfigDict(from_attributes=True)
    
    success: bool
    message: str
    media_asset_id: str
    lead_id: str
    quote_generated: bool = False
    quote_id: Optional[str] = None
    quote_total: Optional[float] = None


class LeadResponse(BaseModel):
    """Lead details response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    organization_id: str
    interaction_id: Optional[str]
    source_platform: Optional[str]
    contact_name: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    requested_services: list[str]
    pricing_intent: Optional[str]
    extracted_surfaces: Dict[str, Any]
    status: str
    priority_score: float
    created_by_id: int
    created_at: str


# API Endpoints

@router.post("/{lead_id}/media/attach", response_model=MediaAttachmentResponse)
async def attach_media_to_lead(
    request: MediaAttachmentRequest,
    lead_id: str = Path(..., description="Lead ID"),
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Attach a media asset to a lead and trigger auto-quote generation/update
    
    This endpoint:
    1. Validates lead and media asset ownership within organization
    2. Links the media asset to the lead
    3. Attempts to generate or update quotes based on the new media
    4. Returns success status and any generated quote information
    """
    try:
        # Get and validate lead access (org-scoped)
        lead = db.query(Lead).filter(
            Lead.id == lead_id,
            Lead.organization_id == tenant_context.organization_id
        ).first()
        
        if not lead:
            raise HTTPException(
                status_code=404,
                detail="Lead not found or access denied"
            )
        
        # Get and validate media asset access (org-scoped)
        media_asset = db.query(MediaAsset).filter(
            MediaAsset.id == request.media_asset_id,
            MediaAsset.organization_id == tenant_context.organization_id,
            MediaAsset.status == "active"
        ).first()
        
        if not media_asset:
            raise HTTPException(
                status_code=404,
                detail="Media asset not found or access denied"
            )
        
        # Check if asset is already attached to this lead
        if media_asset.lead_id == lead_id:
            raise HTTPException(
                status_code=409,
                detail="Media asset is already attached to this lead"
            )
        
        # Check if asset is attached to a different lead
        if media_asset.lead_id and media_asset.lead_id != lead_id:
            raise HTTPException(
                status_code=409,
                detail="Media asset is already attached to a different lead"
            )
        
        # Check upload completion
        if not media_asset.upload_completed:
            raise HTTPException(
                status_code=409,
                detail="Media asset upload not completed"
            )
        
        # Attach media asset to lead
        media_asset.lead_id = lead_id
        media_asset.updated_by_id = current_user.id
        media_asset.updated_at = datetime.now(timezone.utc)
        
        # Update asset metadata if description provided
        if request.description:
            if not media_asset.asset_metadata:
                media_asset.asset_metadata = {}
            media_asset.asset_metadata["lead_description"] = request.description
        
        # Update asset tags if provided
        if request.tags:
            existing_tags = media_asset.tags or []
            media_asset.tags = list(set(existing_tags + request.tags))
        
        db.commit()
        
        # Log audit event
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            event_type=AuditEventType.LEAD_MEDIA_ATTACHED,
            user_id=str(current_user.id),
            organization_id=tenant_context.organization_id,
            details={
                "lead_id": lead_id,
                "media_asset_id": request.media_asset_id,
                "filename": media_asset.filename,
                "file_size": media_asset.file_size,
                "description": request.description,
                "tags": request.tags
            }
        )
        
        # Try to generate or update quote with new media information
        quote_generated = False
        quote_id = None
        quote_total = None
        
        try:
            lead_quote_service = get_lead_quote_service()
            
            # Check if lead already has a quote
            existing_quote = db.query(Quote).filter(
                Quote.lead_id == lead_id,
                Quote.organization_id == tenant_context.organization_id
            ).first()
            
            if existing_quote:
                # Update existing quote (this would be enhanced in the future)
                logger.info(f"Lead {lead_id} already has quote {existing_quote.id}, media attached for reference")
                quote_id = existing_quote.id
                quote_total = float(existing_quote.total)
                quote_generated = False  # Not newly generated
            else:
                # Try to generate new quote with media
                new_quote = lead_quote_service.try_auto_quote_for_lead(lead, db, current_user.id)
                if new_quote:
                    quote_generated = True
                    quote_id = new_quote.id
                    quote_total = float(new_quote.total)
                    logger.info(f"Generated new quote {quote_id} for lead {lead_id} with attached media")
                else:
                    logger.debug(f"Could not generate quote for lead {lead_id} even with media")
                    
        except Exception as e:
            logger.error(f"Error handling quote for lead {lead_id} after media attachment: {e}")
            # Don't fail the media attachment if quote handling fails
        
        # Send internal notification about media received
        try:
            from backend.services.notification_service import get_notification_service
            notification_service = get_notification_service()
            
            # This would send internal notification to team about new lead media
            await notification_service.send_lead_media_notification(
                lead_id=lead_id,
                media_asset_id=request.media_asset_id,
                organization_id=tenant_context.organization_id,
                user_id=current_user.id
            )
            
        except Exception as e:
            logger.error(f"Failed to send lead media notification for lead {lead_id}: {e}")
            # Don't fail the media attachment if notification fails
        
        return MediaAttachmentResponse(
            success=True,
            message="Media asset attached to lead successfully",
            media_asset_id=request.media_asset_id,
            lead_id=lead_id,
            quote_generated=quote_generated,
            quote_id=quote_id,
            quote_total=quote_total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error attaching media to lead {lead_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: str = Path(..., description="Lead ID"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get lead details by ID (org-scoped)
    """
    try:
        # Get lead with org-scoping
        lead = db.query(Lead).filter(
            Lead.id == lead_id,
            Lead.organization_id == tenant_context.organization_id
        ).first()
        
        if not lead:
            raise HTTPException(
                status_code=404,
                detail="Lead not found or access denied"
            )
        
        return LeadResponse(**lead.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lead {lead_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=dict)
async def list_leads(
    status: Optional[str] = Query(None, description="Filter by lead status"),
    source_platform: Optional[str] = Query(None, description="Filter by source platform"),
    limit: int = Query(50, ge=1, le=100, description="Number of leads to return"),
    offset: int = Query(0, ge=0, description="Number of leads to skip"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List leads for the organization with optional filtering
    """
    try:
        # Build org-scoped query
        query = db.query(Lead).filter(
            Lead.organization_id == tenant_context.organization_id
        )
        
        # Apply filters
        if status:
            query = query.filter(Lead.status == status)
        
        if source_platform:
            query = query.filter(Lead.source_platform == source_platform)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Get paginated results
        leads = query.order_by(
            Lead.priority_score.desc(),
            Lead.created_at.desc()
        ).offset(offset).limit(limit + 1).all()
        
        # Check if there are more results
        has_more = len(leads) > limit
        if has_more:
            leads = leads[:limit]
        
        # Convert to response format
        lead_responses = [LeadResponse(**lead.to_dict()) for lead in leads]
        
        return {
            "leads": lead_responses,
            "total_count": total_count,
            "has_more": has_more,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error listing leads: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Audit event types for lead media operations
class LeadMediaAuditEventType:
    """Lead media-specific audit event types"""
    LEAD_MEDIA_ATTACHED = "lead_media_attached"
    LEAD_MEDIA_NOTIFICATION_SENT = "lead_media_notification_sent"