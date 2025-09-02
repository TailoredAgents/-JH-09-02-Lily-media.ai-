"""
Integration Services API Endpoints
Exposes Instagram, Facebook, research automation, and content generation services
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date

from backend.db.database import get_db
from backend.db.models import User, ContentItem, ResearchData
from backend.auth.dependencies import get_current_active_user
from backend.integrations.instagram_client import instagram_client, InstagramMediaType
from backend.integrations.facebook_client import facebook_client
from backend.services.research_automation import research_service, ResearchQuery, ResearchSource
from backend.services.content_automation import content_automation_service
from backend.services.workflow_orchestration import workflow_orchestrator

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

# Pydantic Models for API Requests/Responses

class InstagramPostRequest(BaseModel):
    caption: str = Field(..., max_length=2200)
    media_urls: List[str] = Field(..., min_length=1, max_length=10)
    media_type: str = Field(..., pattern="^(IMAGE|VIDEO|CAROUSEL_ALBUM|REELS)$")
    location_id: Optional[str] = None
    hashtags: Optional[List[str]] = Field(default_factory=list)
    schedule_for: Optional[datetime] = None

class FacebookPostRequest(BaseModel):
    message: str = Field(..., max_length=63206)
    media_urls: Optional[List[str]] = Field(default_factory=list)
    link: Optional[str] = None
    scheduled_publish_time: Optional[datetime] = None
    targeting: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ResearchQueryRequest(BaseModel):
    keywords: List[str] = Field(..., min_length=1, max_length=10)
    platforms: List[str] = Field(..., min_length=1)
    time_range: str = Field("24h", pattern="^(1h|24h|7d|30d)$")
    location: Optional[str] = None
    max_results: int = Field(50, ge=10, le=500)
    include_sentiment: bool = True
    include_engagement: bool = True

class ContentGenerationRequest(BaseModel):
    topic: str = Field(..., min_length=5, max_length=200)
    platform: str = Field(..., pattern="^(twitter|instagram|facebook|linkedin)$")
    content_type: str = Field(..., pattern="^(post|story|reel|thread|article)$")
    tone: str = Field("professional", pattern="^(professional|casual|humorous|inspirational|educational)$")
    target_audience: Optional[str] = None
    include_hashtags: bool = True
    include_cta: bool = True

class WorkflowTriggerRequest(BaseModel):
    workflow_type: str = Field(..., pattern="^(daily_content|research_analysis|engagement_optimization|trend_monitoring)$")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    schedule_for: Optional[datetime] = None

# Instagram API Endpoints

@router.post("/instagram/post")
def create_instagram_post(
    request: InstagramPostRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create Instagram post with media"""
    try:
        # Get user's Instagram access token (sync operation)
        instagram_token = instagram_client.get_user_token(current_user.id)
        if not instagram_token:
            raise HTTPException(status_code=401, detail="Instagram account not connected")
        
        # Create Instagram post using existing sync method
        result = instagram_client.post_image(
            access_token=instagram_token,
            image_url=request.media_urls[0],
            caption=request.caption,
            user_id=current_user.id
        )
        
        # Store in database
        content_item = ContentItem(
            user_id=current_user.id,
            content=request.caption,
            platform="instagram",
            content_type=request.media_type.lower(),
            platform_post_id=result["id"],
            platform_url=result.get("permalink"),
            status="published",
            published_at=datetime.utcnow()
        )
        db.add(content_item)
        db.commit()
        
        return {
            "success": True,
            "instagram_post_id": result["id"],
            "permalink": result.get("permalink"),
            "content_id": content_item.id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Instagram post: {str(e)}")

@router.get("/instagram/insights/{post_id}")
async def get_instagram_insights(
    post_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get Instagram post insights"""
    try:
        instagram_token = await instagram_client.get_user_token(current_user.id)
        if not instagram_token:
            raise HTTPException(status_code=401, detail="Instagram account not connected")
        
        insights = await instagram_client.get_media_insights(instagram_token, post_id)
        return {"insights": insights}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Instagram insights: {str(e)}")

# Facebook API Endpoints

@router.post("/facebook/post")
async def create_facebook_post(
    request: FacebookPostRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create Facebook post"""
    try:
        facebook_token = await facebook_client.get_user_token(current_user.id)
        if not facebook_token:
            raise HTTPException(status_code=401, detail="Facebook account not connected")
        
        result = await facebook_client.create_post(
            access_token=facebook_token,
            message=request.message,
            media_urls=request.media_urls,
            link=request.link,
            scheduled_publish_time=request.scheduled_publish_time
        )
        
        # Store in database
        content_item = ContentItem(
            user_id=current_user.id,
            content=request.message,
            platform="facebook",
            content_type="post",
            platform_post_id=result["id"],
            status="published" if not request.scheduled_publish_time else "scheduled",
            published_at=datetime.utcnow() if not request.scheduled_publish_time else None,
            scheduled_for=request.scheduled_publish_time
        )
        db.add(content_item)
        db.commit()
        
        return {
            "success": True,
            "facebook_post_id": result["id"],
            "content_id": content_item.id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Facebook post: {str(e)}")

@router.get("/facebook/insights/{post_id}")
async def get_facebook_insights(
    post_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get Facebook post insights"""
    try:
        facebook_token = await facebook_client.get_user_token(current_user.id)
        if not facebook_token:
            raise HTTPException(status_code=401, detail="Facebook account not connected")
        
        insights = await facebook_client.get_post_insights(facebook_token, post_id)
        return {"insights": insights}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Facebook insights: {str(e)}")

# Research Automation Endpoints

@router.post("/research/execute")
def execute_research(
    request: ResearchQueryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Execute automated research query"""
    try:
        # Convert request to ResearchQuery object
        research_query = ResearchQuery(
            keywords=request.keywords,
            platforms=[ResearchSource(platform) for platform in request.platforms],
            content_types=["text", "image", "video"],
            time_range=request.time_range,
            location=request.location,
            max_results=request.max_results,
            include_sentiment=request.include_sentiment,
            include_engagement=request.include_engagement
        )
        
        # Execute research in background
        background_tasks.add_task(
            research_service.execute_research_pipeline,
            query=research_query,
            user_id=current_user.id,
            db=db
        )
        
        return {
            "success": True,
            "message": "Research pipeline started",
            "query": {
                "keywords": request.keywords,
                "platforms": request.platforms,
                "time_range": request.time_range,
                "max_results": request.max_results
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute research: {str(e)}")

@router.get("/research/results")
async def get_research_results(
    keywords: List[str] = Query(...),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get recent research results"""
    try:
        # Query research data
        results = db.query(ResearchData).filter(
            ResearchData.user_id == current_user.id,
            ResearchData.keywords.contains(keywords)
        ).order_by(ResearchData.created_at.desc()).limit(limit).all()
        
        return {
            "results": [
                {
                    "id": result.id,
                    "source": result.source,
                    "content": result.content,
                    "keywords": result.keywords,
                    "sentiment": result.sentiment_score,
                    "engagement": result.engagement_metrics,
                    "created_at": result.created_at
                }
                for result in results
            ],
            "total": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get research results: {str(e)}")

# Content Generation Endpoints

@router.post("/content/generate")
async def generate_content(
    request: ContentGenerationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate AI-powered content"""
    try:
        # Generate content using automation service
        generated_content = await content_automation_service.generate_content(
            topic=request.topic,
            platform=request.platform,
            content_type=request.content_type,
            tone=request.tone,
            target_audience=request.target_audience,
            include_hashtags=request.include_hashtags,
            include_cta=request.include_cta,
            user_id=current_user.id
        )
        
        # Store generated content
        content_item = ContentItem(
            user_id=current_user.id,
            content=generated_content["content"],
            platform=request.platform,
            content_type=request.content_type,
            status="draft",
            ai_model=generated_content.get("model", "openai-gpt"),
            prompt_used=generated_content.get("prompt"),
            generation_params={
                "topic": request.topic,
                "tone": request.tone,
                "target_audience": request.target_audience
            }
        )
        db.add(content_item)
        db.commit()
        
        return {
            "success": True,
            "content": generated_content["content"],
            "hashtags": generated_content.get("hashtags", []),
            "engagement_prediction": generated_content.get("engagement_score"),
            "content_id": content_item.id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate content: {str(e)}")

# Workflow Orchestration Endpoints

@router.post("/workflow/trigger")
async def trigger_workflow(
    request: WorkflowTriggerRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """Trigger automated workflow"""
    try:
        # Trigger workflow in background
        background_tasks.add_task(
            workflow_orchestrator.execute_workflow,
            workflow_type=request.workflow_type,
            user_id=current_user.id,
            parameters=request.parameters,
            scheduled_time=request.schedule_for
        )
        
        return {
            "success": True,
            "message": f"Workflow '{request.workflow_type}' triggered",
            "workflow_type": request.workflow_type,
            "parameters": request.parameters,
            "scheduled_for": request.schedule_for
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger workflow: {str(e)}")

@router.get("/workflow/status/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get workflow execution status"""
    try:
        status = await workflow_orchestrator.get_workflow_status(workflow_id, current_user.id)
        return {"status": status}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")

@router.get("/metrics/collection")
async def get_metrics_collection_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get metrics collection status across all platforms"""
    try:
        from backend.services.metrics_collection import metrics_collector
        
        status = await metrics_collector.get_collection_status(current_user.id)
        return {
            "collection_status": status,
            "last_collection": status.get("last_update"),
            "platforms": status.get("platforms", {}),
            "metrics_count": status.get("total_metrics", 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics status: {str(e)}")

