"""
GDPR/CCPA Data Export API

Provides comprehensive user data export functionality for privacy compliance.
Includes all user-related data across the platform with proper anonymization
and structured export formats.
"""
import asyncio
import json
import logging
import zipfile
import io
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import tempfile
import csv

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, text
from pydantic import BaseModel, EmailStr

from backend.db.database import get_db
from backend.db.models import (
    User, UserSetting, Metric, ContentLog, Goal, WorkflowExecution,
    Notification, Memory, Content, Organization, Team, UserOrganizationRole,
    OrganizationInvitation, SocialConnection, ContentSchedule, ContentDraft,
    Plan
)
from backend.db.user_credentials import UserCredentials
from backend.auth.dependencies import get_current_user
from backend.core.config import get_settings
from backend.core.api_version import create_versioned_router

logger = logging.getLogger(__name__)
settings = get_settings()

router = create_versioned_router(prefix="/data-export", tags=["data-export"])

class DataExportRequest(BaseModel):
    """Request model for data export"""
    format: str = "json"  # json, csv, xml
    include_content: bool = True
    include_metrics: bool = True
    include_connections: bool = True
    anonymize_sensitive: bool = False
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None

class DataExportStatus(BaseModel):
    """Response model for export status"""
    export_id: str
    status: str  # pending, processing, completed, failed
    created_at: datetime
    progress: int = 0
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None

class DataExportService:
    """Service for handling comprehensive data exports"""
    
    def __init__(self, db: Session):
        self.db = db
        self.export_cache = {}  # In production, use Redis
        
    def _anonymize_data(self, data: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
        """Anonymize sensitive fields in data"""
        anonymized = data.copy()
        for field in sensitive_fields:
            if field in anonymized:
                if isinstance(anonymized[field], str):
                    anonymized[field] = f"[ANONYMIZED_{field.upper()}]"
                elif isinstance(anonymized[field], dict):
                    anonymized[field] = {k: f"[ANONYMIZED_{k.upper()}]" for k in anonymized[field].keys()}
        return anonymized
    
    def _get_user_profile_data(self, user: User, anonymize: bool = False) -> Dict[str, Any]:
        """Extract user profile data"""
        profile_data = {
            "user_id": user.id,
            "public_id": str(user.public_id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "tier": user.tier,
            "auth_provider": user.auth_provider,
            "two_factor_enabled": user.two_factor_enabled,
            "email_verified": user.email_verified,
            "subscription_status": user.subscription_status,
            "subscription_end_date": user.subscription_end_date.isoformat() if user.subscription_end_date else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }
        
        if anonymize:
            sensitive_fields = ["email", "full_name", "stripe_customer_id"]
            profile_data = self._anonymize_data(profile_data, sensitive_fields)
            
        return profile_data
    
    def _get_user_settings_data(self, user: User, anonymize: bool = False) -> Optional[Dict[str, Any]]:
        """Extract user settings data"""
        if not user.user_settings:
            return None
            
        settings_data = {
            "brand_name": user.user_settings.brand_name,
            "brand_voice": user.user_settings.brand_voice,
            "primary_color": user.user_settings.primary_color,
            "secondary_color": user.user_settings.secondary_color,
            "logo_url": user.user_settings.logo_url,
            "industry_type": user.user_settings.industry_type,
            "visual_style": user.user_settings.visual_style,
            "image_mood": user.user_settings.image_mood,
            "brand_keywords": user.user_settings.brand_keywords,
            "avoid_list": user.user_settings.avoid_list,
            "timezone": user.user_settings.timezone,
            "content_preferences": user.user_settings.content_preferences,
            "ai_suggestions_enabled": user.user_settings.ai_suggestions_enabled,
            "auto_publish_enabled": user.user_settings.auto_publish_enabled,
            "created_at": user.user_settings.created_at.isoformat() if user.user_settings.created_at else None,
            "updated_at": user.user_settings.updated_at.isoformat() if user.user_settings.updated_at else None,
        }
        
        if anonymize:
            sensitive_fields = ["brand_name", "logo_url"]
            settings_data = self._anonymize_data(settings_data, sensitive_fields)
            
        return settings_data
    
    def _get_user_metrics_data(self, user: User, date_start: Optional[datetime] = None, 
                              date_end: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Extract user metrics data"""
        query = self.db.query(Metric).filter(Metric.user_id == user.id)
        
        if date_start:
            query = query.filter(Metric.date_recorded >= date_start)
        if date_end:
            query = query.filter(Metric.date_recorded <= date_end)
            
        metrics = query.all()
        
        return [{
            "metric_type": m.metric_type,
            "platform": m.platform,
            "value": m.value,
            "date_recorded": m.date_recorded.isoformat() if m.date_recorded else None,
            "metric_metadata": m.metric_metadata,
        } for m in metrics]
    
    def _get_user_content_data(self, user: User, date_start: Optional[datetime] = None,
                              date_end: Optional[datetime] = None, anonymize: bool = False) -> Dict[str, Any]:
        """Extract user content data"""
        # Content logs
        content_query = self.db.query(ContentLog).filter(ContentLog.user_id == user.id)
        if date_start:
            content_query = content_query.filter(ContentLog.created_at >= date_start)
        if date_end:
            content_query = content_query.filter(ContentLog.created_at <= date_end)
        content_logs = content_query.all()
        
        # Content (AI-generated content)
        ai_content_query = self.db.query(Content).filter(Content.user_id == user.id)
        if date_start:
            ai_content_query = ai_content_query.filter(Content.created_at >= date_start)
        if date_end:
            ai_content_query = ai_content_query.filter(Content.created_at <= date_end)
        ai_content = ai_content_query.all()
        
        # Memories (AI context)
        memories_query = self.db.query(Memory).filter(Memory.user_id == user.id)
        if date_start:
            memories_query = memories_query.filter(Memory.created_at >= date_start)
        if date_end:
            memories_query = memories_query.filter(Memory.created_at <= date_end)
        memories = memories_query.all()
        
        content_data = {
            "content_logs": [{
                "id": cl.id,
                "content_type": cl.content_type,
                "content": cl.content if not anonymize else "[CONTENT_ANONYMIZED]",
                "platform": cl.platform,
                "status": cl.status,
                "metadata": cl.metadata if not anonymize else {"anonymized": True},
                "created_at": cl.created_at.isoformat() if cl.created_at else None,
            } for cl in content_logs],
            
            "ai_generated_content": [{
                "id": c.id,
                "content": c.content if not anonymize else "[AI_CONTENT_ANONYMIZED]",
                "content_type": c.content_type,
                "platform": c.platform,
                "status": c.status,
                "ai_model_used": c.ai_model_used,
                "generation_metadata": c.generation_metadata if not anonymize else {"anonymized": True},
                "created_at": c.created_at.isoformat() if c.created_at else None,
            } for c in ai_content],
            
            "memories": [{
                "id": m.id,
                "content": m.content if not anonymize else "[MEMORY_ANONYMIZED]",
                "memory_type": m.memory_type,
                "importance_score": m.importance_score,
                "metadata": m.metadata if not anonymize else {"anonymized": True},
                "created_at": m.created_at.isoformat() if m.created_at else None,
            } for m in memories]
        }
        
        return content_data
    
    def _get_user_connections_data(self, user: User, anonymize: bool = False) -> List[Dict[str, Any]]:
        """Extract user social connections data"""
        # Get connections through organizations the user belongs to
        user_org_ids = [role.organization_id for role in user.organization_roles]
        
        connections = self.db.query(SocialConnection).filter(
            SocialConnection.organization_id.in_(user_org_ids)
        ).all()
        
        connections_data = []
        for conn in connections:
            conn_data = {
                "id": str(conn.id),
                "platform": conn.platform,
                "account_name": conn.account_name if not anonymize else "[ACCOUNT_ANONYMIZED]",
                "account_id": conn.account_id if not anonymize else "[ID_ANONYMIZED]",
                "status": conn.status,
                "is_active": conn.is_active,
                "permissions": conn.permissions,
                "created_at": conn.created_at.isoformat() if conn.created_at else None,
                "last_used_at": conn.last_used_at.isoformat() if conn.last_used_at else None,
            }
            connections_data.append(conn_data)
            
        return connections_data
    
    def _get_user_organizations_data(self, user: User, anonymize: bool = False) -> Dict[str, Any]:
        """Extract user organization and team data"""
        orgs_data = {
            "owned_organizations": [],
            "member_organizations": [],
            "teams": [],
            "invitations": []
        }
        
        # Owned organizations
        for org in user.owned_organizations:
            org_data = {
                "id": str(org.id),
                "name": org.name if not anonymize else "[ORG_NAME_ANONYMIZED]",
                "display_name": org.display_name if not anonymize else "[DISPLAY_NAME_ANONYMIZED]",
                "tier": org.tier,
                "status": org.status,
                "created_at": org.created_at.isoformat() if org.created_at else None,
            }
            orgs_data["owned_organizations"].append(org_data)
        
        # Member organizations and roles
        for role in user.organization_roles:
            org_data = {
                "organization_id": str(role.organization_id),
                "organization_name": role.organization.name if not anonymize else "[ORG_ANONYMIZED]",
                "role": role.role.name if role.role else None,
                "joined_at": role.created_at.isoformat() if role.created_at else None,
            }
            orgs_data["member_organizations"].append(org_data)
        
        # Teams
        for team in user.teams:
            team_data = {
                "id": str(team.id),
                "name": team.name if not anonymize else "[TEAM_ANONYMIZED]",
                "description": team.description if not anonymize else "[DESC_ANONYMIZED]",
                "organization_id": str(team.organization_id),
                "created_at": team.created_at.isoformat() if team.created_at else None,
            }
            orgs_data["teams"].append(team_data)
        
        # Invitations (sent and received)
        for invitation in user.sent_invitations + user.received_invitations:
            inv_data = {
                "id": str(invitation.id),
                "organization_id": str(invitation.organization_id),
                "invited_email": invitation.invited_email if not anonymize else "[EMAIL_ANONYMIZED]",
                "role_name": invitation.role.name if invitation.role else None,
                "status": invitation.status,
                "invited_by": "self" if invitation.invited_by_id == user.id else "other",
                "created_at": invitation.created_at.isoformat() if invitation.created_at else None,
            }
            orgs_data["invitations"].append(inv_data)
        
        return orgs_data
    
    def _get_user_workflow_data(self, user: User, date_start: Optional[datetime] = None,
                               date_end: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Extract user workflow execution data"""
        query = self.db.query(WorkflowExecution).filter(WorkflowExecution.user_id == user.id)
        
        if date_start:
            query = query.filter(WorkflowExecution.created_at >= date_start)
        if date_end:
            query = query.filter(WorkflowExecution.created_at <= date_end)
            
        executions = query.all()
        
        return [{
            "id": we.id,
            "workflow_type": we.workflow_type,
            "status": we.status,
            "input_data": we.input_data,
            "output_data": we.output_data,
            "error_message": we.error_message,
            "started_at": we.started_at.isoformat() if we.started_at else None,
            "completed_at": we.completed_at.isoformat() if we.completed_at else None,
            "created_at": we.created_at.isoformat() if we.created_at else None,
        } for we in executions]
    
    def export_user_data(self, user: User, request: DataExportRequest) -> Dict[str, Any]:
        """Generate comprehensive user data export"""
        logger.info(f"Starting data export for user {user.id}")
        
        export_data = {
            "export_metadata": {
                "user_id": user.id,
                "export_date": datetime.now(timezone.utc).isoformat(),
                "export_format": request.format,
                "anonymized": request.anonymize_sensitive,
                "date_range": {
                    "start": request.date_range_start.isoformat() if request.date_range_start else None,
                    "end": request.date_range_end.isoformat() if request.date_range_end else None,
                },
                "includes": {
                    "content": request.include_content,
                    "metrics": request.include_metrics,
                    "connections": request.include_connections,
                }
            }
        }
        
        # Core profile data
        export_data["profile"] = self._get_user_profile_data(user, request.anonymize_sensitive)
        
        # User settings
        if user.user_settings:
            export_data["settings"] = self._get_user_settings_data(user, request.anonymize_sensitive)
        
        # Plan information
        if user.plan:
            export_data["plan"] = {
                "name": user.plan.name,
                "display_name": user.plan.display_name,
                "monthly_price": str(user.plan.monthly_price),
                "limits": {
                    "monthly_content_generation": user.plan.monthly_content_generation,
                    "monthly_ai_images": user.plan.monthly_ai_images,
                    "max_social_connections": user.plan.max_social_connections,
                    "max_team_members": user.plan.max_team_members,
                }
            }
        
        # Metrics data
        if request.include_metrics:
            export_data["metrics"] = self._get_user_metrics_data(
                user, request.date_range_start, request.date_range_end
            )
        
        # Content data
        if request.include_content:
            export_data["content"] = self._get_user_content_data(
                user, request.date_range_start, request.date_range_end, request.anonymize_sensitive
            )
        
        # Social connections
        if request.include_connections:
            export_data["social_connections"] = self._get_user_connections_data(user, request.anonymize_sensitive)
        
        # Organization and team data
        export_data["organizations"] = self._get_user_organizations_data(user, request.anonymize_sensitive)
        
        # Workflow executions
        export_data["workflows"] = self._get_user_workflow_data(
            user, request.date_range_start, request.date_range_end
        )
        
        # Goals
        goals = self.db.query(Goal).filter(Goal.user_id == user.id).all()
        export_data["goals"] = [{
            "id": g.id,
            "title": g.title if not request.anonymize_sensitive else "[GOAL_TITLE_ANONYMIZED]",
            "description": g.description if not request.anonymize_sensitive else "[GOAL_DESC_ANONYMIZED]",
            "target_value": g.target_value,
            "current_value": g.current_value,
            "status": g.status,
            "target_date": g.target_date.isoformat() if g.target_date else None,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        } for g in goals]
        
        # Notifications
        notifications = self.db.query(Notification).filter(Notification.user_id == user.id).all()
        export_data["notifications"] = [{
            "id": n.id,
            "type": n.type,
            "title": n.title if not request.anonymize_sensitive else "[NOTIFICATION_ANONYMIZED]",
            "message": n.message if not request.anonymize_sensitive else "[MESSAGE_ANONYMIZED]",
            "is_read": n.is_read,
            "priority": n.priority,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        } for n in notifications]
        
        logger.info(f"Data export completed for user {user.id}")
        return export_data


@router.post("/request", response_model=DataExportStatus)
async def request_data_export(
    request: DataExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> DataExportStatus:
    """
    Request a comprehensive data export for GDPR/CCPA compliance
    
    This endpoint initiates a data export process that will gather all
    user-related data from across the platform and prepare it for download.
    """
    try:
        # Generate export ID
        export_id = f"export_{current_user.id}_{int(datetime.now().timestamp())}"
        
        # Validate format
        valid_formats = ["json", "csv", "xml"]
        if request.format not in valid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format '{request.format}'. Must be one of: {valid_formats}"
            )
        
        # Create export status
        status = DataExportStatus(
            export_id=export_id,
            status="pending",
            created_at=datetime.now(timezone.utc),
            progress=0,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)  # Download expires in 24h
        )
        
        # Store status (in production, use Redis)
        # For now, we'll process synchronously for small datasets
        export_service = DataExportService(db)
        
        try:
            # Generate the export data
            export_data = export_service.export_user_data(current_user, request)
            
            # Create download URL (in production, store in S3/similar)
            download_url = f"/api/v1/data-export/download/{export_id}"
            
            # Store the export data temporarily (in production, use persistent storage)
            export_service.export_cache[export_id] = {
                "data": export_data,
                "format": request.format,
                "created_at": datetime.now(timezone.utc),
                "user_id": current_user.id
            }
            
            status.status = "completed"
            status.progress = 100
            status.download_url = download_url
            
            logger.info(f"Data export completed for user {current_user.id}, export_id: {export_id}")
            
        except Exception as e:
            logger.error(f"Export failed for user {current_user.id}: {str(e)}")
            status.status = "failed"
            status.error_message = "Export processing failed. Please try again."
        
        return status
        
    except Exception as e:
        logger.error(f"Data export request failed for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process data export request"
        )


@router.get("/download/{export_id}")
async def download_data_export(
    export_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download a completed data export
    
    Returns the exported data in the requested format (JSON, CSV, or XML)
    as a downloadable file.
    """
    try:
        # Get export service
        export_service = DataExportService(db)
        
        # Check if export exists and belongs to user
        if export_id not in export_service.export_cache:
            raise HTTPException(status_code=404, detail="Export not found")
        
        export_info = export_service.export_cache[export_id]
        if export_info["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if export has expired
        if datetime.now(timezone.utc) - export_info["created_at"] > timedelta(hours=24):
            del export_service.export_cache[export_id]
            raise HTTPException(status_code=410, detail="Export has expired")
        
        export_format = export_info["format"]
        export_data = export_info["data"]
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"user_data_export_{current_user.id}_{timestamp}"
        
        if export_format == "json":
            # Return JSON format
            json_content = json.dumps(export_data, indent=2, default=str)
            return Response(
                content=json_content,
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}.json"
                }
            )
        
        elif export_format == "csv":
            # Convert to CSV format
            output = io.StringIO()
            
            # Write profile data
            if "profile" in export_data:
                output.write("=== USER PROFILE ===\\n")
                profile_writer = csv.writer(output)
                profile_writer.writerow(["Field", "Value"])
                for key, value in export_data["profile"].items():
                    profile_writer.writerow([key, str(value)])
                output.write("\\n")
            
            # Write other sections
            for section_name, section_data in export_data.items():
                if section_name in ["profile", "export_metadata"]:
                    continue
                
                output.write(f"=== {section_name.upper()} ===\\n")
                
                if isinstance(section_data, list) and section_data:
                    # Table format for lists
                    if isinstance(section_data[0], dict):
                        writer = csv.DictWriter(output, fieldnames=section_data[0].keys())
                        writer.writeheader()
                        writer.writerows(section_data)
                elif isinstance(section_data, dict):
                    # Key-value format for dicts
                    writer = csv.writer(output)
                    writer.writerow(["Field", "Value"])
                    for key, value in section_data.items():
                        writer.writerow([key, str(value)])
                
                output.write("\\n")
            
            csv_content = output.getvalue()
            output.close()
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}.csv"
                }
            )
        
        elif export_format == "xml":
            # Convert to XML format (basic implementation)
            def dict_to_xml(data, root_name="data"):
                xml_lines = [f"<{root_name}>"]
                
                for key, value in data.items():
                    if isinstance(value, dict):
                        xml_lines.append(f"  <{key}>")
                        for sub_key, sub_value in value.items():
                            xml_lines.append(f"    <{sub_key}>{str(sub_value)}</{sub_key}>")
                        xml_lines.append(f"  </{key}>")
                    elif isinstance(value, list):
                        xml_lines.append(f"  <{key}>")
                        for i, item in enumerate(value):
                            if isinstance(item, dict):
                                xml_lines.append(f"    <item_{i}>")
                                for sub_key, sub_value in item.items():
                                    xml_lines.append(f"      <{sub_key}>{str(sub_value)}</{sub_key}>")
                                xml_lines.append(f"    </item_{i}>")
                            else:
                                xml_lines.append(f"    <item_{i}>{str(item)}</item_{i}>")
                        xml_lines.append(f"  </{key}>")
                    else:
                        xml_lines.append(f"  <{key}>{str(value)}</{key}>")
                
                xml_lines.append(f"</{root_name}>")
                return "\\n".join(xml_lines)
            
            xml_content = f'<?xml version="1.0" encoding="UTF-8"?>\\n{dict_to_xml(export_data, "user_data_export")}'
            
            return Response(
                content=xml_content,
                media_type="application/xml",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}.xml"
                }
            )
        
        else:
            raise HTTPException(status_code=400, detail="Invalid export format")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed for export {export_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to download export"
        )


@router.get("/status/{export_id}", response_model=DataExportStatus)
async def get_export_status(
    export_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> DataExportStatus:
    """
    Get the status of a data export request
    
    Returns current status, progress, and download information if available.
    """
    try:
        export_service = DataExportService(db)
        
        if export_id not in export_service.export_cache:
            raise HTTPException(status_code=404, detail="Export not found")
        
        export_info = export_service.export_cache[export_id]
        if export_info["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if expired
        created_at = export_info["created_at"]
        expires_at = created_at + timedelta(hours=24)
        
        if datetime.now(timezone.utc) > expires_at:
            status = "expired"
            download_url = None
        else:
            status = "completed"
            download_url = f"/api/v1/data-export/download/{export_id}"
        
        return DataExportStatus(
            export_id=export_id,
            status=status,
            created_at=created_at,
            progress=100,
            download_url=download_url,
            expires_at=expires_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed for export {export_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get export status"
        )


@router.delete("/cleanup")
async def cleanup_expired_exports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Administrative endpoint to cleanup expired exports
    (In production, this would be a background job)
    """
    try:
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        export_service = DataExportService(db)
        expired_count = 0
        
        # Find and remove expired exports
        for export_id, export_info in list(export_service.export_cache.items()):
            if datetime.now(timezone.utc) - export_info["created_at"] > timedelta(hours=24):
                del export_service.export_cache[export_id]
                expired_count += 1
        
        logger.info(f"Cleaned up {expired_count} expired data exports")
        
        return {"message": f"Cleaned up {expired_count} expired exports"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to cleanup expired exports"
        )