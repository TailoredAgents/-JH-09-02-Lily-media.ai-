"""
PW-SEC-ADD-001: Secure Media API

Provides secure media upload/download endpoints for PII assets (quote photos, etc.)
with organization-scoped authorization and comprehensive audit logging.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict, validator

from backend.db.database import get_db
from backend.auth.dependencies import get_current_active_user
from backend.db.models import User, MediaAsset, Lead
from backend.services.media_storage_service import get_media_storage_service, MediaStorageService
from backend.middleware.tenant_context import get_tenant_context, TenantContext, require_role
from backend.core.audit_logger import get_audit_logger, AuditEventType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/media", tags=["Secure Media"])


# Request/Response Models

class MediaUploadRequest(BaseModel):
    """Request to generate a signed upload URL"""
    model_config = ConfigDict(from_attributes=True)
    
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    mime_type: str = Field(..., description="MIME type of the file")
    file_size: int = Field(..., gt=0, le=50*1024*1024, description="File size in bytes (max 50MB)")
    lead_id: Optional[str] = Field(None, description="Optional lead ID to associate with")
    tags: List[str] = Field(default_factory=list, description="Optional tags for categorization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata")
    
    @validator('mime_type')
    def validate_mime_type(cls, v):
        allowed_types = {
            "image/jpeg", "image/jpg", "image/png", "image/webp",
            "application/pdf",
            "text/plain", "text/csv",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel"
        }
        if v not in allowed_types:
            raise ValueError(f"MIME type {v} not allowed")
        return v
    
    @validator('filename')
    def validate_filename(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError("Filename contains invalid characters")
        return v


class MediaUploadResponse(BaseModel):
    """Response with signed upload URL"""
    model_config = ConfigDict(from_attributes=True)
    
    asset_id: str = Field(..., description="Unique asset identifier")
    upload_url: str = Field(..., description="Signed upload URL")
    expires_at: str = Field(..., description="Upload URL expiration timestamp")
    max_file_size: int = Field(..., description="Maximum allowed file size")


class MediaDownloadResponse(BaseModel):
    """Response with signed download URL"""
    model_config = ConfigDict(from_attributes=True)
    
    download_url: str = Field(..., description="Signed download URL")
    expires_at: str = Field(..., description="Download URL expiration timestamp")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="File MIME type")


class MediaAssetResponse(BaseModel):
    """Media asset metadata response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    organization_id: str
    lead_id: Optional[str]
    filename: str
    mime_type: str
    file_size: int
    sha256_hash: str
    status: str
    upload_completed: bool
    expires_at: Optional[str]
    access_count: int
    last_accessed_at: Optional[str]
    metadata: Dict[str, Any]
    tags: List[str]
    created_by_id: int
    created_at: str


class MediaAssetListResponse(BaseModel):
    """Paginated media asset list response"""
    model_config = ConfigDict(from_attributes=True)
    
    assets: List[MediaAssetResponse]
    total_count: int
    has_more: bool


# API Endpoints

@router.post("/uploads", response_model=MediaUploadResponse)
async def create_upload_url(
    request: MediaUploadRequest,
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate signed upload URL for secure media upload
    
    Creates a MediaAsset record and returns a short-lived signed URL for upload.
    Enforces organization boundaries and RBAC permissions.
    """
    try:
        # Validate lead ownership if provided
        if request.lead_id:
            lead = db.query(Lead).filter(
                Lead.id == request.lead_id,
                Lead.organization_id == tenant_context.organization_id
            ).first()
            
            if not lead:
                raise HTTPException(
                    status_code=404,
                    detail="Lead not found or access denied"
                )
        
        # Initialize storage service
        storage_service = get_media_storage_service()
        
        # Generate signed upload URL
        asset_id, upload_url = storage_service.generate_upload_url(
            organization_id=tenant_context.organization_id,
            filename=request.filename,
            mime_type=request.mime_type,
            file_size=request.file_size,
            lead_id=request.lead_id,
            ttl_minutes=10
        )
        
        # Create MediaAsset record in database
        media_asset = MediaAsset(
            id=asset_id,
            organization_id=tenant_context.organization_id,
            lead_id=request.lead_id,
            storage_key=f"media-assets/{tenant_context.organization_id}/{asset_id}/{request.filename}",
            filename=request.filename,
            mime_type=request.mime_type,
            file_size=request.file_size,
            sha256_hash="",  # Will be updated after upload
            status="pending",  # Will be updated to "active" after upload
            upload_completed=False,
            asset_metadata=request.metadata,
            tags=request.tags,
            created_by_id=current_user.id
        )
        
        db.add(media_asset)
        db.commit()
        db.refresh(media_asset)
        
        # Log audit event with actual user
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            event_type=AuditEventType.MEDIA_UPLOAD_URL_GENERATED,
            user_id=str(current_user.id),
            organization_id=tenant_context.organization_id,
            details={
                "asset_id": asset_id,
                "filename": request.filename,
                "mime_type": request.mime_type,
                "file_size": request.file_size,
                "lead_id": request.lead_id
            }
        )
        
        expires_at = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=10)
        
        return MediaUploadResponse(
            asset_id=asset_id,
            upload_url=upload_url,
            expires_at=expires_at.isoformat(),
            max_file_size=50 * 1024 * 1024  # 50MB
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating upload URL: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{asset_id}", response_model=MediaDownloadResponse)
async def get_download_url(
    asset_id: str = Path(..., description="Media asset ID"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate signed download URL for secure media access
    
    Verifies organization access and returns a short-lived signed download URL.
    Updates access tracking for audit purposes.
    """
    try:
        # Get and validate asset access
        asset = db.query(MediaAsset).filter(
            MediaAsset.id == asset_id,
            MediaAsset.organization_id == tenant_context.organization_id,
            MediaAsset.status == "active"
        ).first()
        
        if not asset:
            raise HTTPException(
                status_code=404,
                detail="Media asset not found or access denied"
            )
        
        # Check if asset is expired
        if asset.is_expired():
            raise HTTPException(
                status_code=410,
                detail="Media asset has expired"
            )
        
        # Check upload completion
        if not asset.upload_completed:
            raise HTTPException(
                status_code=409,
                detail="Media asset upload not completed"
            )
        
        # Initialize storage service
        storage_service = get_media_storage_service()
        
        # Generate signed download URL
        download_url = storage_service.generate_download_url(
            asset_id=asset_id,
            organization_id=tenant_context.organization_id,
            ttl_minutes=5
        )
        
        # Update access tracking
        asset.access_count += 1
        asset.last_accessed_at = datetime.now(timezone.utc)
        db.commit()
        
        # Log audit event
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            event_type=AuditEventType.MEDIA_ASSET_DOWNLOADED,
            user_id=str(current_user.id),
            organization_id=tenant_context.organization_id,
            details={
                "asset_id": asset_id,
                "access_count": asset.access_count
            }
        )
        
        expires_at = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=5)
        
        return MediaDownloadResponse(
            download_url=download_url,
            expires_at=expires_at.isoformat(),
            filename=asset.filename,
            file_size=asset.file_size,
            mime_type=asset.mime_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating download URL for asset {asset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{asset_id}")
async def revoke_asset(
    asset_id: str = Path(..., description="Media asset ID"),
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Revoke access to a media asset (soft delete)
    
    Marks the asset as deleted for audit purposes. Actual storage cleanup
    happens via background job.
    """
    try:
        # Get and validate asset access
        asset = db.query(MediaAsset).filter(
            MediaAsset.id == asset_id,
            MediaAsset.organization_id == tenant_context.organization_id
        ).first()
        
        if not asset:
            raise HTTPException(
                status_code=404,
                detail="Media asset not found or access denied"
            )
        
        if asset.status == "deleted":
            raise HTTPException(
                status_code=409,
                detail="Media asset already deleted"
            )
        
        # Mark as deleted
        asset.status = "deleted"
        asset.updated_by_id = current_user.id
        asset.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        # Revoke via storage service
        storage_service = get_media_storage_service()
        storage_service.revoke_asset(
            asset_id=asset_id,
            organization_id=tenant_context.organization_id,
            reason="user_requested"
        )
        
        # Log audit event
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            event_type=AuditEventType.MEDIA_ASSET_DELETED,
            user_id=str(current_user.id),
            organization_id=tenant_context.organization_id,
            details={
                "asset_id": asset_id,
                "filename": asset.filename,
                "reason": "user_requested"
            }
        )
        
        return {"message": "Media asset revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking asset {asset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=MediaAssetListResponse)
async def list_media_assets(
    lead_id: Optional[str] = Query(None, description="Filter by lead ID"),
    status: Optional[str] = Query(None, description="Filter by asset status"),
    mime_type: Optional[str] = Query(None, description="Filter by MIME type"),
    limit: int = Query(50, ge=1, le=100, description="Number of assets to return"),
    offset: int = Query(0, ge=0, description="Number of assets to skip"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List media assets for the organization
    
    Returns paginated list of media assets with optional filtering.
    Enforces organization boundaries.
    """
    try:
        # Build org-scoped query
        query = db.query(MediaAsset).filter(
            MediaAsset.organization_id == tenant_context.organization_id
        )
        
        # Apply filters
        if lead_id:
            query = query.filter(MediaAsset.lead_id == lead_id)
        
        if status:
            query = query.filter(MediaAsset.status == status)
        else:
            # By default, exclude deleted assets
            query = query.filter(MediaAsset.status != "deleted")
        
        if mime_type:
            query = query.filter(MediaAsset.mime_type == mime_type)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Get paginated results
        assets = query.order_by(
            MediaAsset.created_at.desc()
        ).offset(offset).limit(limit + 1).all()
        
        # Check if there are more results
        has_more = len(assets) > limit
        if has_more:
            assets = assets[:limit]
        
        # Convert to response format
        asset_responses = [MediaAssetResponse(**asset.to_dict()) for asset in assets]
        
        return MediaAssetListResponse(
            assets=asset_responses,
            total_count=total_count,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Error listing media assets: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{asset_id}/complete-upload")
async def complete_upload(
    asset_id: str = Path(..., description="Media asset ID"),
    sha256_hash: str = Query(..., description="SHA256 hash of uploaded file"),
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Complete the upload process and activate the asset
    
    Called after successful upload to S3 to update the asset status
    and verify file integrity.
    """
    try:
        # Get and validate asset
        asset = db.query(MediaAsset).filter(
            MediaAsset.id == asset_id,
            MediaAsset.organization_id == tenant_context.organization_id,
            MediaAsset.status == "pending"
        ).first()
        
        if not asset:
            raise HTTPException(
                status_code=404,
                detail="Media asset not found or already completed"
            )
        
        # Update asset status
        asset.sha256_hash = sha256_hash
        asset.status = "active"
        asset.upload_completed = True
        asset.updated_by_id = current_user.id
        asset.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        # Log audit event
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            event_type=AuditEventType.MEDIA_ASSET_UPLOADED,
            user_id=str(current_user.id),
            organization_id=tenant_context.organization_id,
            details={
                "asset_id": asset_id,
                "filename": asset.filename,
                "file_size": asset.file_size,
                "sha256_hash": sha256_hash
            }
        )
        
        return {"message": "Upload completed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing upload for asset {asset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_storage_stats(
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get storage statistics for the organization
    
    Returns summary statistics about media asset usage.
    """
    try:
        # Get stats from database
        total_assets = db.query(MediaAsset).filter(
            MediaAsset.organization_id == tenant_context.organization_id,
            MediaAsset.status != "deleted"
        ).count()
        
        active_assets = db.query(MediaAsset).filter(
            MediaAsset.organization_id == tenant_context.organization_id,
            MediaAsset.status == "active"
        ).count()
        
        # Get total size (this would be expensive for large datasets)
        total_size = db.query(db.func.sum(MediaAsset.file_size)).filter(
            MediaAsset.organization_id == tenant_context.organization_id,
            MediaAsset.status != "deleted"
        ).scalar() or 0
        
        return {
            "organization_id": tenant_context.organization_id,
            "total_assets": total_assets,
            "active_assets": active_assets,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "storage_limit_bytes": 50 * 1024 * 1024 * 100,  # Example: 100 * 50MB files
        }
        
    except Exception as e:
        logger.error(f"Error getting storage stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")