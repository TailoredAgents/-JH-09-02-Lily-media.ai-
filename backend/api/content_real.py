"""
Real Content API with AI-powered functionality

IMPORTANT: This file contains ONLY real AI-powered functionality.
NO MOCK DATA OR FALLBACKS ARE ALLOWED IN THIS FILE.
All responses must be genuine AI-generated content or proper error handling with Lily messages.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging
from datetime import datetime
import uuid

from backend.services.image_generation_service import ImageGenerationService
from backend.services.ai_insights_service import ai_insights_service
from backend.services.twitter_service import twitter_service
from backend.auth.dependencies import get_current_active_user
from backend.db.database import get_db
from backend.db.models import User, ContentLog

router = APIRouter(prefix="/api/content", tags=["content"])
logger = logging.getLogger(__name__)

# Initialize services
image_service = ImageGenerationService()

# Import database service for content persistence
from backend.services.content_persistence_service import ContentPersistenceService
from backend.db.database import get_db
from backend.auth.fastapi_users_config import current_active_user, UserTable
from sqlalchemy.orm import Session
from fastapi import Depends

class ImageGenerationRequest(BaseModel):
    prompt: str
    platform: str = "instagram"
    quality_preset: str = "standard"
    content_context: Optional[str] = None
    industry_context: Optional[str] = None
    tone: str = "professional"

class RegenerateImageRequest(BaseModel):
    content_id: int
    custom_prompt: str
    platform: str = "instagram"
    quality_preset: str = "standard"
    keep_original_context: bool = True  # Whether to use original content context

class ContentGenerationRequest(BaseModel):
    topic: str
    content_type: str = "text"  # text, image, video, etc.
    platform: str = "twitter"
    tone: str = "professional"
    include_hashtags: bool = True
    specific_instructions: Optional[str] = None
    company_research_data: Optional[dict] = None

class ContentUpdateRequest(BaseModel):
    title: str = None
    content: str = None
    platform: str = None
    status: str = None
    scheduled_at: str = None
    scheduled_date: str = None

class ContentCreateRequest(BaseModel):
    title: str
    content: str
    platform: str = "twitter"
    content_type: str = "text"
    status: str = "draft"
    scheduled_at: Optional[str] = None
    tags: List[str] = []

@router.get("/")
async def get_content(
    page: int = 1, 
    limit: int = 20,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    current_user: UserTable = Depends(current_active_user),
    db: Session = Depends(get_db)
):
    """Get recent generated content for the authenticated user"""
    try:
        content_service = ContentPersistenceService(db)
        return content_service.get_content_list(
            user_id=current_user.id,
            page=page,
            limit=limit,
            platform=platform,
            status=status
        )
    except Exception as e:
        logger.error(f"Error getting content: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve content")

@router.post("/")
async def create_content(
    request: ContentCreateRequest,
    current_user: UserTable = Depends(current_active_user),
    db: Session = Depends(get_db)
):
    """Create new content for the authenticated user"""
    try:
        content_service = ContentPersistenceService(db)
        
        # Parse scheduled_at if provided
        scheduled_datetime = None
        if request.scheduled_at:
            try:
                scheduled_datetime = datetime.fromisoformat(request.scheduled_at.replace('Z', '+00:00'))
            except ValueError:
                pass  # Invalid date format, will be None
        
        # Create content in database
        content_log = content_service.create_content(
            user_id=current_user.id,
            title=request.title,
            content=request.content,
            platform=request.platform,
            content_type=request.content_type,
            status=request.status,
            scheduled_at=scheduled_datetime,
            tags=request.tags
        )
        
        # Format response to match expected structure
        engagement_data = content_log.engagement_data or {}
        content_obj = {
            "id": content_log.id,
            "title": engagement_data.get("title", request.title),
            "content": content_log.content,
            "platform": content_log.platform,
            "content_type": content_log.content_type,
            "status": content_log.status,
            "scheduled_at": content_log.scheduled_for.isoformat() + "Z" if content_log.scheduled_for else None,
            "tags": engagement_data.get("tags", request.tags),
            "created_at": content_log.created_at.isoformat() + "Z",
            "updated_at": content_log.updated_at.isoformat() + "Z" if content_log.updated_at else None,
            "generated_by_ai": request.dict().get('generated_by_ai', False),
            "industry_context": request.dict().get('industry_context', ''),
            "image_url": request.dict().get('image_url', None),
            "image_prompt": request.dict().get('image_prompt', None),
            "performance": {
                "views": 0,
                "likes": 0,
                "shares": 0,
                "engagement_rate": 0
            }
        }
        
        return {
            "success": True,
            "content_id": content_log.id,
            "message": "Content created successfully",
            "content": content_obj
        }
    except Exception as e:
        logger.error(f"Content creation error: {e}")
        raise HTTPException(status_code=500, detail=f"Content creation failed: {str(e)}")

@router.get("/scheduled/upcoming")
async def get_upcoming_scheduled(
    current_user: UserTable = Depends(current_active_user),
    db: Session = Depends(get_db)
):
    """Get upcoming scheduled content for the authenticated user"""
    try:
        from datetime import timedelta
        content_service = ContentPersistenceService(db)
        scheduled_content = content_service.get_scheduled_content(
            user_id=current_user.id,
            before=datetime.utcnow() + timedelta(days=30)  # Next 30 days
        )
        
        # Format content for response
        formatted_content = []
        for content_log in scheduled_content:
            engagement_data = content_log.engagement_data or {}
            formatted_content.append({
                "id": content_log.id,
                "title": engagement_data.get("title", ""),
                "content": content_log.content,
                "platform": content_log.platform,
                "status": content_log.status,
                "scheduled_at": content_log.scheduled_for.isoformat() + "Z" if content_log.scheduled_for else None,
                "created_at": content_log.created_at.isoformat() + "Z"
            })
        
        return {
            "scheduled_content": formatted_content,
            "total": len(formatted_content)
        }
    except Exception as e:
        logger.error(f"Error getting scheduled content: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scheduled content")

@router.post("/generate")
async def generate_content(request: ContentGenerationRequest):
    """Generate AI-powered social media content with industry insights and research data"""
    try:
        # Platform character limits with 50-char buffer for safety (LinkedIn and TikTok removed)
        platform_limits = {
            "twitter": 280 - 50,
            "instagram": 2200 - 50,
            "facebook": 63206 - 50
        }
        
        max_chars = platform_limits.get(request.platform, 250)
        
        # Get AI insights for context
        insights = await ai_insights_service.generate_weekly_insights()
        
        # Build enhanced context
        context_parts = []
        
        # Add industry insights
        if insights.get("status") == "success":
            context_parts.append(f"Industry insights: {insights['insights']['full_analysis'][:300]}")
        
        # Add company research data if provided
        if request.company_research_data:
            research_insights = []
            company_insights = request.company_research_data.get('insights', {})
            
            # Extract key insights from research
            for category in ['content_themes', 'recent_news', 'market_position', 'competitive_advantages']:
                category_data = company_insights.get(category, [])
                for item in category_data[:2]:  # Limit to 2 items per category
                    if isinstance(item, dict) and 'insight' in item:
                        research_insights.append(item['insight'])
            
            if research_insights:
                context_parts.append(f"Company research: {'. '.join(research_insights[:3])}")
        
        enhanced_context = '. '.join(context_parts)
        
        # Generate content based on insights and topic
        from openai import AsyncOpenAI
        from backend.core.config import get_settings
        
        settings = get_settings()
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        instructions = request.specific_instructions or f"Create content about {request.topic}"
        
        prompt = f"""
        You are Lily, an expert social media content creator. Create engaging {request.platform} content with these MANDATORY specifications:
        
        Instructions: {instructions}
        Context: {enhanced_context}
        
        🚨 CRITICAL CHARACTER LIMIT: {max_chars - 10} characters maximum
        - COUNT EVERY CHARACTER including spaces, punctuation, hashtags
        - YOUR RESPONSE MUST BE UNDER {max_chars - 10} CHARACTERS (strict limit)
        - This is for {request.platform} - exceeding the limit will break the post
        - AIM for {max_chars - 20} characters to be safe
        
        Requirements:
        - Platform: {request.platform}
        - Tone: {request.tone}
        - Include hashtags: {request.include_hashtags}
        - Use the context to make content specific and valuable
        - Focus on actionable insights and benefits
        - Make it engaging and authentic
        
        IMPORTANT: Count characters as you write. Write concisely. Quality over quantity.
        Return ONLY the final content text under {max_chars - 10} characters. No explanations or extra text.
        """
        
        # Use web search for research-heavy platforms like Twitter
        if request.platform in ['twitter']:
            response = await client.responses.create(
                model="gpt-4.1-mini",
                input=f"Generate social media content with current trends and information. {prompt}",
                tools=[
                    {
                        "type": "web_search"
                    }
                ],
                text={"verbosity": "low"}
            )
            generated_content = response.output_text if hasattr(response, 'output_text') else str(response)
        else:
            # Use regular Chat Completions for other platforms
            response = await client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=400
            )
            generated_content = response.choices[0].message.content.strip()
        
        # Check character limit compliance
        if len(generated_content) > max_chars:
            logger.warning(f"⚠️ GPT-5 exceeded character limit: {len(generated_content)} > {max_chars} for {request.platform}")
            logger.warning(f"Generated content that exceeded limit: {generated_content[:100]}...")
            
            # Instead of truncating, try one more time with an even stricter prompt
            stricter_prompt = f"""
            EMERGENCY: Create {request.platform} content UNDER {max_chars - 30} characters.
            
            Topic: {instructions}
            Context: {enhanced_context[:150]}
            
            🚨 ABSOLUTE LIMIT: {max_chars - 30} characters (strict safety buffer)
            Write SHORT, impactful content. No fluff. Be extremely concise.
            Include hashtags only if plenty of room left.
            
            Return ONLY the content, nothing else.
            """
            
            retry_response = await client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": stricter_prompt}],
                # temperature=0.5,  # Temperature not supported for GPT-5 models
                max_completion_tokens=200  # GPT-5 uses max_completion_tokens
            )
            
            generated_content = retry_response.choices[0].message.content.strip()
            logger.info(f"Retry generated content length: {len(generated_content)}")
            
            # Final fallback: truncate if still too long
            if len(generated_content) > max_chars:
                logger.error(f"❌ Even retry exceeded limit. Truncating as last resort.")
                # Truncate preserving hashtags
                hashtag_match = generated_content[-100:].find('#')
                if hashtag_match > 0:
                    hashtags = generated_content[len(generated_content) - 100 + hashtag_match:]
                    content_without_hashtags = generated_content[:len(generated_content) - 100 + hashtag_match].strip()
                    if len(content_without_hashtags) + len(hashtags) + 1 > max_chars:
                        truncated_length = max_chars - len(hashtags) - 4  # -4 for "... "
                        generated_content = content_without_hashtags[:truncated_length].strip() + "... " + hashtags
                else:
                    generated_content = generated_content[:max_chars - 3] + "..."
        
        result = {
            "success": True,
            "content": generated_content,
            "platform": request.platform,
            "topic": request.topic,
            "tone": request.tone,
            "content_type": request.content_type,
            "character_count": len(generated_content),
            "max_characters": max_chars + 30,  # Show actual platform limit
            "generated_at": datetime.utcnow().isoformat(),
            "used_research": bool(request.company_research_data)
        }
        
        # If content type is "image", also generate an image
        if request.content_type == "image":
            try:
                # Create image prompt based on the generated content and context
                image_prompt = f"""
                Create a professional social media image for {request.platform} that complements this content:
                
                Content: {generated_content[:200]}
                Topic: {request.topic}
                Industry context: {enhanced_context[:300] if enhanced_context else 'Professional business context'}
                
                The image should be visually appealing, professional, and enhance the message of the text content.
                Include relevant visual elements that support the topic and industry context.
                """
                
                # Generate the image using the image service
                image_result = await image_service.generate_image(
                    prompt=image_prompt,
                    platform=request.platform,
                    content_context=generated_content,
                    industry_context=enhanced_context,
                    quality_preset="standard"
                )
                
                if image_result and image_result.get("status") == "success":
                    result["image"] = {
                        "image_url": image_result.get("image_data_url"),
                        "image_data_url": image_result.get("image_data_url"),  # For backward compatibility
                        "prompt": image_result.get("prompt", {}).get("enhanced", image_prompt),
                        "generated_at": datetime.utcnow().isoformat(),
                        "status": "success"
                    }
                else:
                    result["image"] = {
                        "status": "failed",
                        "error": image_result.get("error", "Image generation failed") if image_result else "Image service unavailable"
                    }
                    
            except Exception as img_error:
                logger.error(f"Image generation failed for content: {img_error}")
                result["image"] = {
                    "status": "failed", 
                    "error": f"Image generation failed: {str(img_error)}"
                }
        
        return result
        
    except Exception as e:
        logger.error(f"Content generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")

# Image generation endpoint moved to content.py to avoid duplication
from backend.api.content import generate_image

@router.post("/regenerate-image")
async def regenerate_image(
    request: RegenerateImageRequest,
    current_user: UserTable = Depends(current_active_user),
    db: Session = Depends(get_db)
):
    """
    Regenerate image for existing content with custom user prompt.
    Keeps the original post text but allows user to customize image description.
    """
    try:
        # Get the original content
        content_service = ContentPersistenceService(db)
        content_log = content_service.get_content_by_id(current_user.id, request.content_id)
        
        if not content_log:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Get user settings for industry presets and brand parameters
        from backend.db.models import UserSetting
        user_settings = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
        from backend.api.content_utils import build_user_settings_dict
        user_settings_dict = build_user_settings_dict(user_settings)
        
        # Build enhanced prompt with user settings
        enhanced_prompt = request.custom_prompt
        if user_settings_dict:
            enhanced_prompt = image_service.build_prompt_with_user_settings(
                base_prompt=request.custom_prompt,
                user_settings=user_settings_dict,
                platform=request.platform
            )
        
        # Prepare context if keeping original context
        content_context = None
        if request.keep_original_context:
            content_context = content_log.content[:200]  # First 200 chars of original post
        
        # Generate new image with custom prompt
        result = await image_service.generate_image(
            prompt=enhanced_prompt,
            platform=request.platform,
            quality_preset=request.quality_preset,
            content_context=content_context,
            tone="professional"
        )
        
        # Store the regeneration attempt (for analytics)
        try:
            engagement_data = content_log.engagement_data or {}
            image_history = engagement_data.get("image_history", [])
            
            # Add this regeneration to history
            image_history.append({
                "timestamp": datetime.now().isoformat(),
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

@router.get("/ai-insights")
async def get_ai_insights():
    """Get real AI industry insights"""
    try:
        insights = await ai_insights_service.generate_weekly_insights()
        return insights
    except Exception as e:
        logger.error(f"AI insights error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")

@router.get("/social-connections")
async def get_social_connections():
    """Get status of social media API connections"""
    connections = {
        "twitter": twitter_service.get_connection_status(),
        "instagram": {
            "connected": False,
            "error": "Instagram API credentials not configured", 
            "credentials_needed": ["app_id", "app_secret", "access_token", "business_id"]
        },
        "facebook": {
            "connected": False,
            "error": "Facebook API credentials not configured",
            "credentials_needed": ["app_id", "app_secret", "access_token", "page_id"]
        }
    }
    
    return {
        "status": "success",
        "connections": connections,
        "connected_count": sum(1 for conn in connections.values() if conn.get("connected", False)),
        "total_platforms": len(connections)
    }

@router.get("/{content_id}")
async def get_content_by_id(
    content_id: int,
    current_user: UserTable = Depends(current_active_user),
    db: Session = Depends(get_db)
):
    """Get content by ID"""
    try:
        content_service = ContentPersistenceService(db)
        content_log = content_service.get_content_by_id(current_user.id, content_id)
        
        if not content_log:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Format response to match expected structure
        engagement_data = content_log.engagement_data or {}
        content_obj = {
            "id": content_log.id,
            "title": engagement_data.get("title", ""),
            "content": content_log.content,
            "platform": content_log.platform,
            "content_type": content_log.content_type,
            "status": content_log.status,
            "scheduled_at": content_log.scheduled_for.isoformat() + "Z" if content_log.scheduled_for else None,
            "published_at": content_log.published_at.isoformat() + "Z" if content_log.published_at else None,
            "tags": engagement_data.get("tags", []),
            "created_at": content_log.created_at.isoformat() + "Z",
            "updated_at": content_log.updated_at.isoformat() + "Z" if content_log.updated_at else None,
            "generated_by_ai": engagement_data.get('generated_by_ai', False),
            "industry_context": engagement_data.get('industry_context', ''),
            "image_url": engagement_data.get('image_url', None),
            "image_prompt": engagement_data.get('image_prompt', None),
            "performance": {
                "views": engagement_data.get('views', 0),
                "likes": engagement_data.get('likes', 0),
                "shares": engagement_data.get('shares', 0),
                "comments": engagement_data.get('comments', 0),
                "engagement_rate": engagement_data.get('engagement_rate', 0)
            }
        }
        
        return {
            "success": True,
            "content": content_obj
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get content by ID error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get content: {str(e)}")

@router.put("/{content_id}")
async def update_content(
    content_id: int,
    request: ContentUpdateRequest,
    current_user: UserTable = Depends(current_active_user),
    db: Session = Depends(get_db)
):
    """Update existing content for the authenticated user"""
    try:
        content_service = ContentPersistenceService(db)
        
        # Prepare updates dict
        updates = {}
        for field, value in request.dict().items():
            if value is not None:
                if field == "scheduled_at" and value:
                    # Parse datetime
                    try:
                        updates["scheduled_for"] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except ValueError:
                        pass  # Skip invalid dates
                elif field in ["title", "content", "platform", "status", "tags"]:
                    updates[field] = value
        
        # Update content in database
        updated_content = content_service.update_content(
            user_id=current_user.id,
            content_id=content_id,
            updates=updates
        )
        
        if not updated_content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Format response
        engagement_data = updated_content.engagement_data or {}
        content_obj = {
            "id": updated_content.id,
            "title": engagement_data.get("title", ""),
            "content": updated_content.content,
            "platform": updated_content.platform,
            "content_type": updated_content.content_type,
            "status": updated_content.status,
            "scheduled_at": updated_content.scheduled_for.isoformat() + "Z" if updated_content.scheduled_for else None,
            "published_at": updated_content.published_at.isoformat() + "Z" if updated_content.published_at else None,
            "tags": engagement_data.get("tags", []),
            "created_at": updated_content.created_at.isoformat() + "Z",
            "updated_at": updated_content.updated_at.isoformat() + "Z" if updated_content.updated_at else None
        }
        
        return {
            "success": True,
            "content_id": updated_content.id,
            "message": "Content updated successfully",
            "updated_fields": list(updates.keys()),
            "content": content_obj
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content update error: {e}")
        raise HTTPException(status_code=500, detail=f"Content update failed: {str(e)}")

@router.delete("/{content_id}")
async def delete_content(
    content_id: int,
    current_user: UserTable = Depends(current_active_user),
    db: Session = Depends(get_db)
):
    """Delete content for the authenticated user"""
    try:
        content_service = ContentPersistenceService(db)
        success = content_service.delete_content(current_user.id, content_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Content not found")
        
        return {
            "success": True,
            "content_id": content_id,
            "message": "Content deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content deletion error: {e}")
        raise HTTPException(status_code=500, detail=f"Content deletion failed: {str(e)}")

@router.get("/analytics/summary")
async def get_content_analytics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get content analytics summary with real database data"""
    try:
        from datetime import timedelta
        from sqlalchemy import func, and_
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all content for the user within date range
        content_query = db.query(ContentLog).filter(
            ContentLog.user_id == current_user.id,
            ContentLog.created_at >= start_date
        )
        
        total_content = content_query.count()
        
        # Count by status
        published_count = content_query.filter(ContentLog.status == "published").count()
        scheduled_count = content_query.filter(ContentLog.status == "scheduled").count()
        draft_count = content_query.filter(ContentLog.status == "draft").count()
        
        # Platform breakdown
        platform_stats = db.query(
            ContentLog.platform,
            func.count(ContentLog.id).label('count')
        ).filter(
            ContentLog.user_id == current_user.id,
            ContentLog.created_at >= start_date
        ).group_by(ContentLog.platform).all()
        
        top_platforms = [
            {"platform": platform, "count": count}
            for platform, count in platform_stats
        ]
        
        # Engagement metrics from all published content
        published_content = content_query.filter(ContentLog.status == "published").all()
        
        total_views = 0
        total_likes = 0
        total_shares = 0
        total_comments = 0
        
        performance_data = []
        
        for content in published_content:
            engagement_data = content.engagement_data or {}
            
            views = engagement_data.get('views', 0)
            likes = engagement_data.get('likes', 0)
            shares = engagement_data.get('shares', 0)
            comments = engagement_data.get('comments', 0)
            
            total_views += views
            total_likes += likes
            total_shares += shares
            total_comments += comments
            
            # Add to performance trends
            performance_data.append({
                "date": content.created_at.strftime('%Y-%m-%d'),
                "engagement_score": likes + comments * 2 + shares * 3,
                "platform": content.platform
            })
        
        # Generate performance trends (group by date)
        from collections import defaultdict
        daily_performance = defaultdict(int)
        daily_counts = defaultdict(int)
        
        for item in performance_data:
            daily_performance[item["date"]] += item["engagement_score"]
            daily_counts[item["date"]] += 1
        
        performance_trends = [
            {
                "date": date,
                "average_engagement": daily_performance[date] / daily_counts[date] if daily_counts[date] > 0 else 0,
                "post_count": daily_counts[date]
            }
            for date in sorted(daily_performance.keys())
        ]
        
        return {
            "total_content": total_content,
            "published_content": published_count,
            "scheduled_content": scheduled_count,
            "draft_content": draft_count,
            "top_platforms": sorted(top_platforms, key=lambda x: x["count"], reverse=True),
            "engagement_metrics": {
                "total_views": total_views,
                "total_likes": total_likes,
                "total_shares": total_shares,
                "total_comments": total_comments
            },
            "performance_trends": performance_trends[-30:],  # Last 30 days
            "date_range": {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": datetime.utcnow().strftime('%Y-%m-%d'),
                "days": days
            },
            "message": f"Analytics for last {days} days"
        }
        
    except Exception as e:
        logger.error(f"Content analytics error: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")