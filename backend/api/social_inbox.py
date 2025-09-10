"""
Social Media Inbox API

API endpoints for managing social media interactions, responses, and webhooks
for Facebook, Instagram, and X/Twitter integration.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from backend.db.database import get_db
from backend.db.models import (
    SocialInteraction, InteractionResponse, ResponseTemplate, 
    CompanyKnowledge, User, SocialPlatformConnection
)
from backend.auth.dependencies import get_current_active_user
from backend.middleware.tenant_context import get_tenant_context, TenantContext, require_role
from backend.services.social_webhook_service import get_webhook_service
from backend.services.personality_response_engine import get_personality_engine
from backend.services.websocket_manager import websocket_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/inbox", tags=["social-inbox"])

# Pydantic models for API requests/responses

class InteractionResponse(BaseModel):
    id: str
    platform: str
    interaction_type: str
    author_username: str
    author_display_name: Optional[str]
    content: str
    sentiment: Optional[str]
    intent: Optional[str]
    priority_score: float
    status: str
    response_strategy: str
    platform_created_at: datetime
    received_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class InteractionListResponse(BaseModel):
    interactions: List[InteractionResponse]
    total_count: int
    unread_count: int
    high_priority_count: int

class CreateResponseRequest(BaseModel):
    interaction_id: str
    response_text: str
    response_type: str = Field(default="manual", pattern="^(manual|auto|template)$")
    template_id: Optional[str] = None

class ResponseTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str = Field(..., pattern="^(intent|keyword|platform|sentiment)$")
    trigger_conditions: Dict[str, Any] = Field(default_factory=dict)
    keywords: List[str] = Field(default_factory=list)
    platforms: List[str] = Field(default_factory=list)
    response_text: str
    personality_style: str = Field(default="professional", pattern="^(professional|friendly|casual|technical)$")
    tone: str = Field(default="helpful")
    auto_approve: bool = False

class CompanyKnowledgeRequest(BaseModel):
    title: str
    topic: str
    content: str
    summary: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    context_type: str = Field(default="general")
    platforms: List[str] = Field(default=["facebook", "instagram", "twitter"])

class GenerateResponseRequest(BaseModel):
    interaction_id: str
    personality_style: str = Field(default="professional", pattern="^(professional|friendly|casual|technical)$")

# Inbox Management Endpoints

@router.get("/interactions", response_model=InteractionListResponse)
async def get_interactions(
    platform: Optional[str] = Query(None, pattern="^(facebook|instagram|twitter)$"),
    status: Optional[str] = Query(None, pattern="^(unread|read|responded|archived|escalated)$"),
    intent: Optional[str] = Query(None, pattern="^(question|complaint|praise|lead|spam|general)$"),
    user_id: Optional[int] = Query(None, description="Filter by specific user (optional within org)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get filtered list of social media interactions - org-scoped with RBAC
    
    Inbox is org-scoped; user filters are optional.
    """
    try:
        # Build org-scoped query via SocialPlatformConnection
        query = db.query(SocialInteraction).join(
            SocialPlatformConnection,
            SocialInteraction.connection_id == SocialPlatformConnection.id
        ).filter(
            SocialPlatformConnection.organization_id == tenant_context.organization_id
        )
        
        # Optional user filtering within organization
        if user_id is not None:
            query = query.filter(SocialInteraction.user_id == user_id)
        
        if platform:
            query = query.filter(SocialInteraction.platform == platform)
        
        if status:
            query = query.filter(SocialInteraction.status == status)
        
        if intent:
            query = query.filter(SocialInteraction.intent == intent)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Get paginated results
        interactions = query.order_by(
            SocialInteraction.priority_score.desc(),
            SocialInteraction.received_at.desc()
        ).offset(offset).limit(limit).all()
        
        # Get summary counts (org-scoped)
        base_org_query = db.query(SocialInteraction).join(
            SocialPlatformConnection,
            SocialInteraction.connection_id == SocialPlatformConnection.id
        ).filter(
            SocialPlatformConnection.organization_id == tenant_context.organization_id
        )
        
        unread_count = base_org_query.filter(
            SocialInteraction.status == 'unread'
        ).count()
        
        high_priority_count = base_org_query.filter(
            SocialInteraction.priority_score >= 70,
            SocialInteraction.status.in_(['unread', 'read'])
        ).count()
        
        return InteractionListResponse(
            interactions=interactions,
            total_count=total_count,
            unread_count=unread_count,
            high_priority_count=high_priority_count
        )
        
    except Exception as e:
        logger.error(f"Failed to get interactions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve interactions")

@router.put("/interactions/{interaction_id}")
async def update_interaction(
    interaction_id: str,
    status: Optional[str] = None,
    priority_score: Optional[float] = None,
    response_strategy: Optional[str] = None,
    assigned_to: Optional[int] = None,
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update interaction status, priority, or assignment - requires member role"""
    try:
        # Org-scoped query with RBAC
        interaction = db.query(SocialInteraction).join(
            SocialPlatformConnection,
            SocialInteraction.connection_id == SocialPlatformConnection.id
        ).filter(
            SocialInteraction.id == interaction_id,
            SocialPlatformConnection.organization_id == tenant_context.organization_id
        ).first()
        
        if not interaction:
            raise HTTPException(status_code=404, detail="Interaction not found")
        
        # Update fields if provided
        if status:
            interaction.status = status
        
        if priority_score is not None:
            interaction.priority_score = max(0, min(100, priority_score))
        
        if response_strategy:
            interaction.response_strategy = response_strategy
        
        if assigned_to is not None:
            interaction.assigned_to = assigned_to
        
        interaction.last_updated_at = datetime.now(timezone.utc)
        
        db.commit()
        
        return {"message": "Interaction updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update interaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to update interaction")

@router.delete("/interactions/{interaction_id}")
async def archive_interaction(
    interaction_id: str,
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Archive (soft delete) an interaction - requires member role"""
    try:
        # Org-scoped query with RBAC
        interaction = db.query(SocialInteraction).join(
            SocialPlatformConnection,
            SocialInteraction.connection_id == SocialPlatformConnection.id
        ).filter(
            SocialInteraction.id == interaction_id,
            SocialPlatformConnection.organization_id == tenant_context.organization_id
        ).first()
        
        if not interaction:
            raise HTTPException(status_code=404, detail="Interaction not found")
        
        interaction.status = 'archived'
        interaction.last_updated_at = datetime.now(timezone.utc)
        
        db.commit()
        
        return {"message": "Interaction archived successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to archive interaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to archive interaction")

# Response Management Endpoints

@router.post("/interactions/respond")
async def send_response(
    request: CreateResponseRequest,
    background_tasks: BackgroundTasks,
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a response to a social media interaction - requires member role"""
    try:
        # Get the interaction (org-scoped with RBAC)
        interaction = db.query(SocialInteraction).join(
            SocialPlatformConnection,
            SocialInteraction.connection_id == SocialPlatformConnection.id
        ).filter(
            SocialInteraction.id == request.interaction_id,
            SocialPlatformConnection.organization_id == tenant_context.organization_id
        ).first()
        
        if not interaction:
            raise HTTPException(status_code=404, detail="Interaction not found")
        
        # Create response record
        response = InteractionResponse(
            interaction_id=request.interaction_id,
            user_id=current_user.id,
            response_text=request.response_text,
            response_type=request.response_type,
            template_id=request.template_id,
            platform=interaction.platform
        )
        
        db.add(response)
        
        # Update interaction status
        interaction.status = 'responded'
        interaction.last_updated_at = datetime.now(timezone.utc)
        
        db.commit()
        
        # Schedule background task to actually send the response
        background_tasks.add_task(
            _send_platform_response,
            response.id,
            interaction.platform,
            interaction.external_id,
            request.response_text
        )
        
        # Send WebSocket notification about response being sent
        await websocket_service.notify_interaction_responded(
            current_user.id,
            request.interaction_id,
            response.id
        )
        
        return {
            "message": "Response queued successfully",
            "response_id": response.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send response: {e}")
        raise HTTPException(status_code=500, detail="Failed to send response")

@router.post("/interactions/generate-response")
async def generate_ai_response(
    request: GenerateResponseRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate AI-powered response suggestion"""
    try:
        personality_engine = get_personality_engine(db)
        
        response_data = await personality_engine.process_interaction(
            request.interaction_id,
            current_user.id,
            request.personality_style
        )
        
        if not response_data:
            raise HTTPException(status_code=400, detail="Failed to generate response")
        
        result = {
            "suggested_response": response_data["response_text"],
            "confidence_score": response_data["confidence_score"],
            "personality_style": response_data["personality_style"],
            "reasoning": response_data["response_reasoning"]
        }
        
        # Send WebSocket notification about generated response
        await websocket_service.notify_response_generated(
            current_user.id,
            request.interaction_id,
            result
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate AI response: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response")

# Response Template Management

@router.get("/templates")
async def get_response_templates(
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get organization's response templates"""
    # Note: ResponseTemplate needs organization_id field to be fully org-scoped
    # For now, we'll filter by users within the organization
    # TODO: Add organization_id to ResponseTemplate model
    templates = db.query(ResponseTemplate).filter(
        ResponseTemplate.user_id == current_user.id,
        ResponseTemplate.is_active == True
    ).order_by(ResponseTemplate.priority.desc()).all()
    
    return {"templates": templates}

@router.post("/templates")
async def create_response_template(
    request: ResponseTemplateRequest,
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new response template"""
    try:
        template = ResponseTemplate(
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            trigger_type=request.trigger_type,
            trigger_conditions=request.trigger_conditions,
            keywords=request.keywords,
            platforms=request.platforms,
            response_text=request.response_text,
            personality_style=request.personality_style,
            tone=request.tone,
            auto_approve=request.auto_approve
        )
        
        db.add(template)
        db.commit()
        
        return {
            "message": "Template created successfully",
            "template_id": template.id
        }
        
    except Exception as e:
        logger.error(f"Failed to create template: {e}")
        raise HTTPException(status_code=500, detail="Failed to create template")

# Company Knowledge Base Management

@router.get("/knowledge-base")
async def get_company_knowledge(
    topic: Optional[str] = Query(None),
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get organization's knowledge base entries"""
    # Note: CompanyKnowledge needs organization_id field to be fully org-scoped
    # For now, we'll filter by users within the organization
    # TODO: Add organization_id to CompanyKnowledge model
    query = db.query(CompanyKnowledge).filter(
        CompanyKnowledge.user_id == current_user.id,
        CompanyKnowledge.is_active == True
    )
    
    if topic:
        query = query.filter(CompanyKnowledge.topic == topic)
    
    knowledge_entries = query.order_by(
        CompanyKnowledge.usage_count.desc()
    ).all()
    
    return {"knowledge_entries": knowledge_entries or []}

@router.get("/knowledge-base/status")
async def get_knowledge_base_status(
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get organization's knowledge base status and setup info"""
    # Note: CompanyKnowledge needs organization_id field to be fully org-scoped
    # For now, we'll filter by users within the organization
    # TODO: Add organization_id to CompanyKnowledge model
    total_entries = db.query(CompanyKnowledge).filter(
        CompanyKnowledge.user_id == current_user.id,
        CompanyKnowledge.is_active == True
    ).count()
    
    return {
        "has_knowledge": total_entries > 0,
        "entry_count": total_entries,
        "needs_setup": total_entries == 0,
        "suggested_topics": [
            "company_info",
            "faq", 
            "product_info",
            "contact_info",
            "policies"
        ],
        "setup_message": "Add company knowledge entries to help AI generate better responses."
    }

@router.post("/knowledge-base")
async def create_knowledge_entry(
    request: CompanyKnowledgeRequest,
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new knowledge base entry"""
    try:
        knowledge = CompanyKnowledge(
            user_id=current_user.id,
            title=request.title,
            topic=request.topic,
            content=request.content,
            summary=request.summary,
            keywords=request.keywords,
            tags=request.tags,
            context_type=request.context_type,
            platforms=request.platforms
        )
        
        db.add(knowledge)
        db.commit()
        
        return {
            "message": "Knowledge entry created successfully",
            "knowledge_id": knowledge.id
        }
        
    except Exception as e:
        logger.error(f"Failed to create knowledge entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to create knowledge entry")

# Webhook Endpoints

@router.post("/webhooks/facebook")
async def handle_facebook_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle Facebook webhook events"""
    try:
        # Verify webhook signature
        payload = await request.body()
        signature = request.headers.get('X-Hub-Signature-256', '')
        
        webhook_service = get_webhook_service(db)
        
        # In production, you'd get the app secret from environment
        # For now, we'll skip verification in development
        # is_valid = webhook_service.verify_facebook_webhook(payload.decode(), signature, app_secret)
        # if not is_valid:
        #     raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse webhook data
        webhook_data = await request.json()
        
        # Process webhook in background
        background_tasks.add_task(
            _process_facebook_webhook_background,
            webhook_data
        )
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Facebook webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.post("/webhooks/instagram")
async def handle_instagram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle Instagram webhook events"""
    try:
        payload = await request.body()
        signature = request.headers.get('X-Hub-Signature-256', '')
        
        webhook_data = await request.json()
        
        # Process webhook in background
        background_tasks.add_task(
            _process_instagram_webhook_background,
            webhook_data
        )
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Instagram webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.post("/webhooks/twitter")
async def handle_twitter_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle Twitter/X webhook events"""
    try:
        payload = await request.body()
        signature = request.headers.get('X-Twitter-Webhooks-Signature', '')
        
        webhook_data = await request.json()
        
        # Process webhook in background
        background_tasks.add_task(
            _process_twitter_webhook_background,
            webhook_data
        )
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Twitter webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

# Background task functions

async def _process_facebook_webhook_background(webhook_data: Dict[str, Any]):
    """Background task to process Facebook webhook"""
    db = next(get_db())
    try:
        webhook_service = get_webhook_service(db)
        created_interactions = webhook_service.process_facebook_webhook(webhook_data)
        logger.info(f"Processed Facebook webhook, created {len(created_interactions)} interactions")
    except Exception as e:
        logger.error(f"Background Facebook webhook processing failed: {e}")
    finally:
        db.close()

async def _process_instagram_webhook_background(webhook_data: Dict[str, Any]):
    """Background task to process Instagram webhook"""
    db = next(get_db())
    try:
        webhook_service = get_webhook_service(db)
        created_interactions = webhook_service.process_instagram_webhook(webhook_data)
        logger.info(f"Processed Instagram webhook, created {len(created_interactions)} interactions")
    except Exception as e:
        logger.error(f"Background Instagram webhook processing failed: {e}")
    finally:
        db.close()

async def _process_twitter_webhook_background(webhook_data: Dict[str, Any]):
    """Background task to process Twitter webhook"""
    db = next(get_db())
    try:
        webhook_service = get_webhook_service(db)
        created_interactions = webhook_service.process_twitter_webhook(webhook_data)
        logger.info(f"Processed Twitter webhook, created {len(created_interactions)} interactions")
    except Exception as e:
        logger.error(f"Background Twitter webhook processing failed: {e}")
    finally:
        db.close()

async def _send_platform_response(
    response_id: str,
    platform: str,
    external_id: str,
    response_text: str
):
    """Background task to send response to social media platform"""
    db = next(get_db())
    try:
        # This would integrate with platform APIs to actually send the response
        # For now, we'll just update the response status
        response = db.query(InteractionResponse).filter(
            InteractionResponse.id == response_id
        ).first()
        
        if response:
            response.status = 'sent'
            response.sent_at = datetime.now(timezone.utc)
            # In production, set platform_response_id from API response
            db.commit()
        
        logger.info(f"Sent {platform} response for interaction {external_id}")
        
    except Exception as e:
        logger.error(f"Failed to send platform response: {e}")
        # Update response status to failed
        response = db.query(InteractionResponse).filter(
            InteractionResponse.id == response_id
        ).first()
        if response:
            response.status = 'failed'
            response.failure_reason = str(e)
            db.commit()
    finally:
        db.close()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    WebSocket endpoint for real-time social inbox updates
    
    Handles real-time communication for:
    - New interactions
    - Status updates  
    - Response generation
    - Error notifications
    """
    try:
        await websocket_service.handle_websocket(websocket, user_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")


@router.get("/ws/stats")
async def get_websocket_stats(
    current_user: User = Depends(get_current_active_user)
):
    """Get WebSocket connection statistics"""
    return websocket_service.get_connection_stats()