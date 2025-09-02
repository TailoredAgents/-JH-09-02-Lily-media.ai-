"""
Content management API endpoints
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator, ConfigDict
from datetime import datetime, date, timezone, timedelta
import uuid
import json

from backend.db.database import get_db
from backend.db.models import ContentLog, ContentItem, User, SocialConnection, ContentDraft
from backend.auth.dependencies import get_current_active_user
from backend.services.cache_decorators import cached, cache_invalidate
from backend.agents.tools import openai_tool
from backend.services.image_generation_service import image_generation_service
from backend.services.file_upload_service import file_upload_service
from backend.utils.db_checks import ensure_table_exists, safe_table_query
from backend.services.content_scheduler_service import get_content_scheduler_service
from backend.api.partner_oauth import is_partner_oauth_enabled

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/content", tags=["content"])

# Pydantic models
class CreateContentRequest(BaseModel):
    platform: str = Field(..., pattern="^(twitter|linkedin|instagram|facebook|tiktok)$")
    content: str = Field(..., min_length=1, max_length=10000)
    content_type: str = Field(..., pattern="^(text|image|video|carousel)$")
    scheduled_for: Optional[datetime] = None
    engagement_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('scheduled_for')
    def scheduled_for_must_be_future(cls, v):
        if v and v <= datetime.now(timezone.utc):
            raise ValueError('Scheduled time must be in the future')
        return v

class UpdateContentRequest(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    scheduled_for: Optional[datetime] = None
    engagement_data: Optional[Dict[str, Any]] = None
    
    @validator('scheduled_for')
    def scheduled_for_must_be_future(cls, v):
        if v and v <= datetime.now(timezone.utc):
            raise ValueError('Scheduled time must be in the future')
        return v

class PublishContentRequest(BaseModel):
    platform_post_id: Optional[str] = None
    engagement_data: Optional[Dict[str, Any]] = Field(default_factory=dict)

class GenerateContentRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    content_type: str = Field(..., pattern="^(text|image|video|carousel)$")
    platform: Optional[str] = Field(None, pattern="^(twitter|linkedin|instagram|facebook|tiktok)$")
    tone: Optional[str] = Field("professional", pattern="^(professional|casual|humorous|inspiring|educational)$")

class GenerateImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    content_context: Optional[str] = Field(None, max_length=2000)
    platform: str = Field(..., pattern="^(twitter|linkedin|instagram|facebook|tiktok)$")
    industry_context: Optional[str] = Field(None, max_length=1000)
    quality_preset: str = Field("standard", pattern="^(draft|standard|premium|story|banner)$")
    tone: str = Field("professional", pattern="^(professional|casual|humorous|inspiring|educational)$")

class EditImageRequest(BaseModel):
    edit_prompt: str = Field(..., min_length=1, max_length=300)
    previous_response_id: Optional[str] = None
    previous_image_id: Optional[str] = None
    platform: str = Field(..., pattern="^(twitter|linkedin|instagram|facebook|tiktok)$")
    quality_preset: str = Field("standard", pattern="^(draft|standard|premium|story|banner)$")

class GenerateContentImagesRequest(BaseModel):
    content_text: str = Field(..., min_length=1, max_length=2000)
    platforms: List[str] = Field(..., min_length=1)
    image_count: int = Field(1, ge=1, le=3)
    industry_context: Optional[str] = Field(None, max_length=1000)

class ContentResponse(BaseModel):
    id: int
    platform: str
    content: str
    content_type: str
    status: str
    engagement_data: Dict[str, Any]
    scheduled_for: Optional[datetime]
    published_at: Optional[datetime]
    platform_post_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class ContentAnalytics(BaseModel):
    total_posts: int
    posts_by_platform: Dict[str, int]
    posts_by_status: Dict[str, int]


# Phase 7: New models for connection-based publishing
class TestDraftRequest(BaseModel):
    """Request model for creating test drafts"""
    content: str = Field(..., min_length=1, max_length=10000)
    media_urls: Optional[List[str]] = Field(default=[], description="List of media URLs")
    connection_id: str = Field(..., description="UUID of the social connection")


class ScheduleConnectionRequest(BaseModel):
    """Request model for scheduling content with connection IDs (new flow)"""
    content: str = Field(..., min_length=1, max_length=10000)
    media_urls: Optional[List[str]] = Field(default=[], description="List of media URLs")
    connection_ids: List[str] = Field(..., min_length=1, description="List of connection UUIDs")
    scheduled_time: Optional[datetime] = Field(None, description="When to publish (null for immediate)")
    
    @validator('scheduled_time')
    def scheduled_time_must_be_future(cls, v):
        if v and v <= datetime.now(timezone.utc):
            raise ValueError('Scheduled time must be in the future')
        return v


class ScheduleLegacyRequest(BaseModel):
    """Request model for scheduling content with platforms (legacy flow)"""
    content: str = Field(..., min_length=1, max_length=10000)
    platforms: List[str] = Field(..., min_length=1, description="List of platform names")
    scheduled_time: Optional[datetime] = Field(None, description="When to publish (null for immediate)")
    
    @validator('scheduled_time')
    def scheduled_time_must_be_future(cls, v):
        if v and v <= datetime.now(timezone.utc):
            raise ValueError('Scheduled time must be in the future')
        return v
    
    @validator('platforms')
    def validate_platforms(cls, v):
        valid_platforms = {"twitter", "linkedin", "instagram", "facebook", "tiktok"}
        invalid_platforms = set(v) - valid_platforms
        if invalid_platforms:
            raise ValueError(f"Invalid platforms: {list(invalid_platforms)}")
        return v


class TestDraftResponse(BaseModel):
    """Response model for test draft creation"""
    success: bool
    draft_id: Optional[str] = None
    message: str
    connection_id: str
    platform: str


class ScheduleResponse(BaseModel):
    """Response model for content scheduling"""
    success: bool
    scheduled_count: int
    failed_count: int
    results: List[Dict[str, Any]]
    errors: List[str]

class RegenerateImageRequest(BaseModel):
    content_id: int
    custom_prompt: str = Field(..., min_length=1, max_length=500)
    platform: str = Field(..., pattern="^(twitter|linkedin|instagram|facebook|tiktok)$")
    quality_preset: str = Field("standard", pattern="^(draft|standard|premium|story|banner)$")
    keep_original_context: bool = True


# Phase 7: New endpoints for connection-based publishing
@router.post("/test-draft", response_model=TestDraftResponse)
async def create_test_draft(
    request: TestDraftRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a test draft for connection verification (Phase 7)
    This endpoint creates a draft artifact without external posting
    and marks the connection as verified for posting after first success
    """
    # Check if partner OAuth is enabled
    if not is_partner_oauth_enabled():
        raise HTTPException(
            status_code=404, 
            detail="Partner OAuth feature not enabled"
        )
    
    try:
        # Get user's organization ID
        organization_id = getattr(current_user, 'organization_id', None)
        if not organization_id:
            raise HTTPException(
                status_code=400,
                detail="User not associated with an organization"
            )
        
        # Get scheduler service
        scheduler = get_content_scheduler_service()
        
        # Create draft
        success, draft_id, error = await scheduler.create_draft(
            organization_id=str(organization_id),
            connection_id=request.connection_id,
            content=request.content,
            media_urls=request.media_urls or [],
            db=db
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=error)
        
        # Get connection info for response
        connection = db.query(SocialConnection).filter(
            SocialConnection.id == request.connection_id,
            SocialConnection.organization_id == organization_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        return TestDraftResponse(
            success=True,
            draft_id=draft_id,
            message="Draft created successfully - connection verified for posting",
            connection_id=request.connection_id,
            platform=connection.platform
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating test draft: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/schedule", response_model=ScheduleResponse)
async def schedule_content(
    request: Union[ScheduleConnectionRequest, ScheduleLegacyRequest],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Schedule content for publishing (Phase 7)
    Supports both new connection-based flow and legacy platform-based flow
    """
    try:
        # Determine if this is new flow (connection_ids) or legacy (platforms)
        if hasattr(request, 'connection_ids'):
            # New flow with connection IDs
            if not is_partner_oauth_enabled():
                raise HTTPException(
                    status_code=404,
                    detail="Partner OAuth feature not enabled"
                )
            
            # Get user's organization ID
            organization_id = getattr(current_user, 'organization_id', None)
            if not organization_id:
                raise HTTPException(
                    status_code=400,
                    detail="User not associated with an organization"
                )
            
            # Get scheduler service
            scheduler = get_content_scheduler_service()
            
            # Schedule content
            results = await scheduler.schedule_content(
                organization_id=str(organization_id),
                connection_ids=request.connection_ids,
                content=request.content,
                media_urls=getattr(request, 'media_urls', []) or [],
                scheduled_time=request.scheduled_time,
                db=db
            )
            
            return ScheduleResponse(**results, success=results['failed_count'] == 0)
        
        else:
            # Legacy flow with platforms
            logger.info("Using legacy content scheduling flow")
            
            # TODO: Implement legacy flow using existing ContentLog approach
            # For now, return a placeholder response
            return ScheduleResponse(
                success=False,
                scheduled_count=0,
                failed_count=len(request.platforms),
                results=[],
                errors=["Legacy flow not implemented in Phase 7"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling content: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@cache_invalidate("content", "user_content_list")  # Invalidate user content list cache
@router.post("/", response_model=ContentResponse)
async def create_content(
    request: CreateContentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create new content"""
    
    content = ContentLog(
        user_id=current_user.id,
        platform=request.platform,
        content=request.content,
        content_type=request.content_type,
        status="draft",
        engagement_data=request.engagement_data or {},
        scheduled_for=request.scheduled_for
    )
    
    # Auto-schedule if scheduled_for is provided
    if request.scheduled_for:
        content.status = "scheduled"
    
    db.add(content)
    db.commit()
    db.refresh(content)
    
    return content

@cached("content", "user_content_list", ttl=300)  # 5 minute cache
@router.get("/", response_model=List[ContentResponse])
async def get_user_content(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    platform: Optional[str] = Query(None, pattern="^(twitter|linkedin|instagram|facebook|tiktok)$"),
    status: Optional[str] = Query(None, pattern="^(draft|scheduled|published|failed)$"),
    content_type: Optional[str] = Query(None, pattern="^(text|image|video|carousel)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get user's content with filtering and pagination"""
    
    # Ensure the content_logs table exists before querying
    ensure_table_exists(db, "content_logs", "get_user_content")
    
    def query_user_content(db_session):
        query = db_session.query(ContentLog).filter(ContentLog.user_id == current_user.id)
        
        if platform:
            query = query.filter(ContentLog.platform == platform)
        if status:
            query = query.filter(ContentLog.status == status)
        if content_type:
            query = query.filter(ContentLog.content_type == content_type)
        
        return query.order_by(ContentLog.created_at.desc()).offset(offset).limit(limit).all()
    
    # Use safe query with fallback
    return safe_table_query(
        db=db,
        table_name="content_logs",
        query_func=query_user_content,
        fallback_value=[],
        endpoint_name="get_user_content"
    )


@router.get("/items", response_model=List[dict])
async def get_content_items(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get user's content items (including uploaded images) with filtering and pagination"""
    
    query = db.query(ContentItem).filter(ContentItem.user_id == current_user.id)
    
    if platform:
        query = query.filter(ContentItem.platform == platform)
    if status:
        query = query.filter(ContentItem.status == status)
    if content_type:
        query = query.filter(ContentItem.content_type == content_type)
    
    content_items = query.order_by(ContentItem.created_at.desc()).offset(offset).limit(limit).all()
    
    # Convert to dict format for frontend compatibility
    items = []
    for item in content_items:
        item_dict = {
            "id": item.id,
            "content": item.content,
            "platform": item.platform,
            "content_type": item.content_type,
            "status": item.status,
            "title": getattr(item, 'title', ''),
            "created_at": item.created_at,
            "updated_at": getattr(item, 'updated_at', None),
            "platform_metadata": item.platform_metadata or {},
            "is_uploaded": item.platform == "upload"
        }
        items.append(item_dict)
    
    return items


@cached("content", "single_content", ttl=600)  # 10 minute cache
@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(
    content_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific content by ID"""
    
    content = db.query(ContentLog).filter(
        ContentLog.id == content_id,
        ContentLog.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return content

@router.put("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: int,
    request: UpdateContentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update content"""
    
    content = db.query(ContentLog).filter(
        ContentLog.id == content_id,
        ContentLog.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if content.status == "published":
        raise HTTPException(status_code=400, detail="Cannot update published content")
    
    # Update fields
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(content, field, value)
    
    # Update status if scheduling
    if request.scheduled_for and content.status == "draft":
        content.status = "scheduled"
    elif not request.scheduled_for and content.status == "scheduled":
        content.status = "draft"
    
    content.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(content)
    
    return content

@router.post("/{content_id}/publish", response_model=ContentResponse)
async def publish_content(
    content_id: int,
    request: PublishContentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark content as published"""
    
    content = db.query(ContentLog).filter(
        ContentLog.id == content_id,
        ContentLog.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if content.status == "published":
        raise HTTPException(status_code=400, detail="Content already published")
    
    # Update content status
    content.status = "published"
    content.published_at = datetime.now(timezone.utc)
    content.platform_post_id = request.platform_post_id
    
    # Update engagement data
    if request.engagement_data:
        content.engagement_data.update(request.engagement_data)
    
    content.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(content)
    
    return content

@router.post("/{content_id}/schedule")
async def schedule_content(
    content_id: int,
    scheduled_for: datetime,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Schedule content for publishing"""
    
    if scheduled_for <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future")
    
    content = db.query(ContentLog).filter(
        ContentLog.id == content_id,
        ContentLog.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if content.status == "published":
        raise HTTPException(status_code=400, detail="Cannot schedule published content")
    
    content.scheduled_for = scheduled_for
    content.status = "scheduled"
    content.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {"message": "Content scheduled successfully", "scheduled_for": scheduled_for}

@router.delete("/{content_id}")
async def delete_content(
    content_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete content"""
    
    content = db.query(ContentLog).filter(
        ContentLog.id == content_id,
        ContentLog.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if content.status == "published":
        raise HTTPException(status_code=400, detail="Cannot delete published content")
    
    db.delete(content)
    db.commit()
    
    return {"message": "Content deleted successfully"}

@router.get("/scheduled/upcoming")
async def get_upcoming_content(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=30)
):
    """Get upcoming scheduled content"""
    
    
    # Ensure the content_logs table exists before querying
    ensure_table_exists(db, "content_logs", "get_upcoming_content")
    
    def query_upcoming_content(db_session):
        end_date = datetime.now(timezone.utc) + timedelta(days=days)
        
        # Add pagination to prevent over-fetch
        page_size = min(100, 50)  # Cap at 100 items for calendar view
        content_items = db_session.query(ContentLog).filter(
            ContentLog.user_id == current_user.id,
            ContentLog.status == "scheduled",
            ContentLog.scheduled_for.between(datetime.now(timezone.utc), end_date)
        ).order_by(ContentLog.scheduled_for).limit(page_size).all()
        
        return [
            {
                "id": content.id,
                "platform": content.platform,
                "content": content.content[:100] + "..." if len(content.content) > 100 else content.content,
                "content_type": content.content_type,
                "scheduled_for": content.scheduled_for,
                "days_until": (content.scheduled_for - datetime.now(timezone.utc)).days
            }
            for content in content_items
        ]
    
    # Use safe query with fallback
    return safe_table_query(
        db=db,
        table_name="content_logs",
        query_func=query_upcoming_content,
        fallback_value=[],
        endpoint_name="get_upcoming_content"
    )

@router.get("/analytics/summary", response_model=ContentAnalytics)
async def get_content_analytics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get content analytics summary"""
    
    # Ensure the content_logs table exists before querying
    ensure_table_exists(db, "content_logs", "get_content_analytics")
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    def query_content_analytics(db_session: Session):
        # Add pagination to prevent over-fetch for analytics
        page_size = 500  # Reasonable limit for analytics data
        return db_session.query(ContentLog).filter(
            ContentLog.user_id == current_user.id,
            ContentLog.created_at >= start_date
        ).order_by(ContentLog.created_at.desc()).limit(page_size).all()
    
    # Use safe query wrapper
    content_items = safe_table_query(
        db=db,
        table_name="content_logs", 
        query_func=query_content_analytics,
        fallback_value=[],
        endpoint_name="get_content_analytics"
    )
    
    # Calculate statistics
    total_posts = len(content_items)
    
    posts_by_platform = {}
    posts_by_status = {}
    engagement_scores = []
    
    for content in content_items:
        # Platform stats
        platform = content.platform
        posts_by_platform[platform] = posts_by_platform.get(platform, 0) + 1
        
        # Status stats
        status = content.status
        posts_by_status[status] = posts_by_status.get(status, 0) + 1
        
        # Engagement stats - safely access engagement_data column
        try:
            engagement_data = getattr(content, 'engagement_data', None) or {}
        except AttributeError:
            # Column doesn't exist in schema, use empty dict
            engagement_data = {}
        
        likes = engagement_data.get('likes', 0)
        comments = engagement_data.get('comments', 0)
        shares = engagement_data.get('shares', 0)
        engagement_score = likes + comments * 2 + shares * 3  # Weighted engagement
        engagement_scores.append(engagement_score)
    
    avg_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0
    
    # Top performing posts - safely calculate engagement scores
    content_with_engagement = []
    for content in content_items:
        if content.status == "published":
            # Safely access engagement_data column
            try:
                engagement_data = getattr(content, 'engagement_data', None) or {}
            except AttributeError:
                engagement_data = {}
            
            score = (engagement_data.get('likes', 0) + 
                    engagement_data.get('comments', 0) * 2 + 
                    engagement_data.get('shares', 0) * 3)
            content_with_engagement.append((content, score))
    
    top_performing = sorted(content_with_engagement, key=lambda x: x[1], reverse=True)[:5]
    
    top_performing_posts = [
        {
            "id": content.id,
            "platform": content.platform,
            "content": content.content[:100] + "..." if len(content.content) > 100 else content.content,
            "engagement_score": score,
            "published_at": content.published_at
        }
        for content, score in top_performing
    ]
    
    return ContentAnalytics(
        total_posts=total_posts,
        posts_by_platform=posts_by_platform,
        posts_by_status=posts_by_status,
        avg_engagement=round(avg_engagement, 2),
        top_performing_posts=top_performing_posts
    )

@router.post("/generate")
async def generate_content(
    request: GenerateContentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate AI content based on prompt"""
    
    try:
        # Use OpenAI tool to generate content
        result = openai_tool.generate_content(
            prompt=request.prompt,
            content_type=request.content_type,
            platform=request.platform,
            tone=request.tone
        )
        
        if result.get("status") == "success":
            return {
                "status": "success",
                "content": result.get("content"),
                "title": result.get("title"),
                "hashtags": result.get("hashtags", []),
                "platform": request.platform,
                "content_type": request.content_type,
                "tone": request.tone,
                "generated_at": datetime.now(timezone.utc)
            }
        else:
            return {
                "status": "error",
                "error": result.get("error", "Content generation failed"),
                "generated_at": datetime.now(timezone.utc)
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": f"Content generation failed: {str(e)}",
            "generated_at": datetime.now(timezone.utc)
        }

@router.post("/generate-ideas")
async def generate_content_ideas(
    platform: str = Query(..., pattern="^(twitter|linkedin|instagram|facebook|tiktok)$"),
    topic: Optional[str] = Query(None),
    tone: str = Query("professional", pattern="^(professional|casual|humorous|inspiring|educational)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate AI-powered content ideas using GPT-5 mini with web search"""
    
    try:
        from openai import AsyncOpenAI
        from backend.core.config import get_settings
        
        settings = get_settings()
        
        if not hasattr(settings, 'openai_api_key') or not settings.openai_api_key:
            raise HTTPException(
                status_code=503,
                detail="OpenAI API key not configured. Content idea generation unavailable."
            )
        
        # Initialize OpenAI client
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Build context-aware prompt
        topic_context = f" about {topic}" if topic else ""
        
        prompt = f"""
        Generate 5 creative and engaging content ideas for {platform}{topic_context}.
        
        Requirements:
        - Tone: {tone}
        - Platform: {platform} (consider platform-specific best practices)
        - Make ideas specific and actionable
        - Include current trends and timely topics where relevant
        - Ensure ideas will drive engagement
        
        For each idea, provide:
        1. A clear, specific content idea
        2. Brief explanation of why it would work well
        3. Suggested content format (text, image, video, etc.)
        
        Return as a JSON array of objects with keys: "idea", "reason", "format"
        """
        
        # Use GPT-5 mini with web search for current trends via Responses API
        response = await client.responses.create(
            model="gpt-5-mini",
            input=f"You are an expert social media strategist. Use web search to find current trends and generate content ideas. {prompt}",
            tools=[
                {
                    "type": "web_search"
                }
            ],
            text={"verbosity": "medium"}
        )
        
        content = response.output_text if hasattr(response, 'output_text') else str(response)
        
        # Try to parse JSON response
        try:
            import json
            suggestions = json.loads(content)
            if not isinstance(suggestions, list):
                suggestions = suggestions.get("ideas", [])
        except (json.JSONDecodeError, TypeError):
            # Fallback: extract ideas from text
            lines = content.split('\n')
            suggestions = []
            for line in lines:
                if line.strip() and any(keyword in line.lower() for keyword in ['idea', 'suggestion', 'content']):
                    suggestions.append({
                        "idea": line.strip(),
                        "reason": "AI-generated suggestion",
                        "format": "text"
                    })
            if len(suggestions) > 5:
                suggestions = suggestions[:5]
        
        # Ensure we have at least some suggestions
        if not suggestions:
            suggestions = [
                {
                    "idea": f"Create {tone} content about {topic or 'your expertise'} for {platform}",
                    "reason": "Leverages your knowledge and matches requested tone",
                    "format": "text"
                }
            ]
        
        return {
            "platform": platform,
            "topic": topic,
            "tone": tone,
            "suggestions": suggestions[:5],  # Return top 5
            "generated_at": datetime.now(timezone.utc),
            "ai_generated": True,
            "model_used": "gpt-5-mini"
        }
        
    except Exception as e:
        logger.error(f"AI content idea generation failed: {e}")
        
        # Fallback to basic suggestions
        platform_fallbacks = {
            "twitter": [
                {"idea": "Share a quick industry tip", "reason": "Tips perform well on Twitter", "format": "text"},
                {"idea": "Ask an engaging question", "reason": "Questions drive replies and engagement", "format": "text"},
                {"idea": "Comment on current industry news", "reason": "Timely content gets more visibility", "format": "text"}
            ],
            "linkedin": [
                {"idea": "Write about lessons learned", "reason": "Professional insights resonate on LinkedIn", "format": "article"},
                {"idea": "Share industry analysis", "reason": "Thought leadership content performs well", "format": "text"},
                {"idea": "Highlight team achievements", "reason": "Human stories build connections", "format": "text"}
            ],
            "instagram": [
                {"idea": "Post behind-the-scenes content", "reason": "Authenticity drives Instagram engagement", "format": "image"},
                {"idea": "Create an educational carousel", "reason": "Educational content gets high saves", "format": "carousel"},
                {"idea": "Share customer success stories", "reason": "Social proof builds trust", "format": "image"}
            ]
        }
        
        suggestions = platform_fallbacks.get(platform, platform_fallbacks["twitter"])
        
        return {
            "platform": platform,
            "topic": topic,
            "tone": tone,
            "suggestions": suggestions,
            "generated_at": datetime.now(timezone.utc),
            "ai_generated": False,
            "fallback_used": True,
            "error": "AI generation unavailable"
        }

@router.post("/generate-image")
async def generate_image(
    request: GenerateImageRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Generate an image using xAI Grok 2 Vision model"""
    
    result = await image_generation_service.generate_image(
        prompt=request.prompt,
        platform=request.platform,
        quality_preset=request.quality_preset,
        content_context=request.content_context,
        industry_context=request.industry_context,
        tone=request.tone
    )
    
    return result

@router.post("/edit-image")
async def edit_image(
    request: EditImageRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Edit an existing image using multi-turn capabilities"""
    
    if not request.previous_response_id and not request.previous_image_id:
        return {
            "status": "error",
            "error": "Either previous_response_id or previous_image_id must be provided"
        }
    
    result = await image_generation_service.edit_image(
        edit_prompt=request.edit_prompt,
        previous_response_id=request.previous_response_id,
        previous_image_id=request.previous_image_id,
        platform=request.platform,
        quality_preset=request.quality_preset
    )
    
    return result

@router.post("/regenerate-image")
async def regenerate_image(
    request: RegenerateImageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Regenerate image for existing content with custom user prompt.
    Keeps the original post text but allows user to customize image description.
    """
    try:
        # Get the original content
        content_log = db.query(ContentLog).filter(
            ContentLog.id == request.content_id,
            ContentLog.user_id == current_user.id
        ).first()
        
        if not content_log:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Get user settings for industry presets and brand parameters
        from backend.db.models import UserSetting
        user_settings = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
        user_settings_dict = None
        
        if user_settings:
            user_settings_dict = {
                "industry_type": user_settings.industry_type,
                "visual_style": user_settings.visual_style,
                "primary_color": user_settings.primary_color,
                "secondary_color": getattr(user_settings, 'secondary_color', '#10b981'),
                "image_mood": getattr(user_settings, 'image_mood', ["professional", "clean"]),
                "brand_keywords": getattr(user_settings, 'brand_keywords', []),
                "avoid_list": getattr(user_settings, 'avoid_list', []),
                "preferred_image_style": getattr(user_settings, 'preferred_image_style', {}),
                "image_quality": getattr(user_settings, 'image_quality', "high")
            }
        
        # Build enhanced prompt with user settings
        enhanced_prompt = request.custom_prompt
        if user_settings_dict:
            enhanced_prompt = image_generation_service.build_prompt_with_user_settings(
                base_prompt=request.custom_prompt,
                user_settings=user_settings_dict,
                platform=request.platform
            )
        
        # Prepare context if keeping original context
        content_context = None
        if request.keep_original_context:
            content_context = content_log.content[:200]  # First 200 chars of original post
        
        # Generate new image with custom prompt
        result = await image_generation_service.generate_image(
            prompt=enhanced_prompt,
            platform=request.platform,
            quality_preset=request.quality_preset,
            content_context=content_context,
            industry_context=user_settings_dict.get('industry_type', '') if user_settings_dict else '',
            tone="professional"
        )
        
        # Store the regeneration attempt (for analytics)
        try:
            engagement_data = content_log.engagement_data or {}
            image_history = engagement_data.get("image_history", [])
            
            # Add this regeneration to history
            image_history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "custom_prompt": request.custom_prompt,
                "enhanced_prompt": enhanced_prompt,
                "platform": request.platform,
                "quality_preset": request.quality_preset,
                "user_requested": True
            })
            
            # Keep only last 5 attempts
            if len(image_history) > 5:
                image_history = image_history[-5:]
            
            engagement_data["image_history"] = image_history
            content_log.engagement_data = engagement_data
            content_log.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            logger.info(f"Stored image regeneration history for content {request.content_id}")
            
        except Exception as history_error:
            logger.warning(f"Failed to store image history: {history_error}")
            # Don't fail the request if history storage fails
        
        # Add metadata about the regeneration
        result.update({
            "regenerated": True,
            "content_id": request.content_id,
            "custom_prompt_used": request.custom_prompt,
            "original_context_kept": request.keep_original_context,
            "user_settings_applied": user_settings_dict is not None
        })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image regeneration error: {e}")
        raise HTTPException(status_code=500, detail=f"Image regeneration failed: {str(e)}")

@router.post("/generate-content-images")
async def generate_content_images(
    request: GenerateContentImagesRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Generate multiple images optimized for different platforms based on content"""
    
    # Validate platforms
    valid_platforms = {"twitter", "linkedin", "instagram", "facebook", "tiktok"}
    invalid_platforms = set(request.platforms) - valid_platforms
    if invalid_platforms:
        return {
            "status": "error",
            "error": f"Invalid platforms: {list(invalid_platforms)}"
        }
    
    result = await image_generation_service.generate_content_images(
        content_text=request.content_text,
        platforms=request.platforms,
        image_count=request.image_count,
        industry_context=request.industry_context
    )
    
    return {
        "status": "success",
        "content_text": request.content_text,
        "platforms": request.platforms,
        "images": result,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    description: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload an image file for use in posts.
    
    - **file**: Image file (JPG, PNG, GIF, WebP)
    - **description**: Optional description of the image
    
    Returns file information and URL for use in posts.
    """
    
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided"
        )
    
    try:
        result = await file_upload_service.upload_image(
            file=file,
            user_id=current_user.id,
            description=description
        )
        
        return {
            "status": "success",
            "message": "Image uploaded successfully",
            "file": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to upload image"
        )

@router.delete("/upload-image/{filename}")
async def delete_uploaded_image(
    filename: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an uploaded image file.
    
    - **filename**: Name of the file to delete
    """
    
    success = file_upload_service.delete_image(filename, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Image not found or could not be deleted"
        )
    
    return {
        "status": "success",
        "message": "Image deleted successfully"
    }

@router.get("/upload-stats")
async def get_upload_stats(
    current_user: User = Depends(get_current_active_user)
):
    """Get file upload statistics (admin endpoint)"""
    
    # In production, you might want to restrict this to admin users
    stats = file_upload_service.get_upload_stats()
    
    return {
        "status": "success",
        "stats": stats
    }