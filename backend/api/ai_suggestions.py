"""
AI Contextual Suggestions API
Provides personalized, real-time AI suggestions based on user context
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import logging
from datetime import datetime, timedelta

from backend.db.database import get_db
from backend.db.models import User, UserSetting, Content, Goal, Memory
from backend.auth.dependencies import get_current_active_user
from openai import AsyncOpenAI
from backend.core.config import get_settings
from backend.core.constants import (
    DEFAULT_SUGGESTION_LIMIT, MAX_CONTENT_COUNT_DISPLAY, 
    DEFAULT_PLATFORMS, DEFAULT_BRAND_VOICE, DEFAULT_CREATIVITY_LEVEL
)
from sqlalchemy.exc import SQLAlchemyError
import json

settings = get_settings()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["ai-suggestions"])

# Request/Response Models
class SuggestionRequest(BaseModel):
    type: str = Field(..., pattern="^(content|goals|inbox|memory|scheduler)$")
    context: Dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=DEFAULT_SUGGESTION_LIMIT, ge=1, le=10)

class AISuggestion(BaseModel):
    id: str
    title: str
    description: str
    action: str
    color: str = "blue"
    ai_prompt: str
    estimated_time: str
    priority: int = Field(default=5, ge=1, le=10)  # 1 = highest priority
    personalization_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
class SuggestionsResponse(BaseModel):
    suggestions: List[AISuggestion]
    context_summary: str
    personalization_level: str  # "basic", "medium", "high"

async def analyze_user_context(user: User, db: Session, suggestion_type: str) -> Dict[str, Any]:
    """Analyze user's current context to personalize suggestions"""
    context = {
        "user_id": user.id,
        "type": suggestion_type,
        "account_age_days": (datetime.utcnow() - user.created_at).days if user.created_at else 0,
        "has_content": False,
        "content_count": 0,
        "has_goals": False,
        "goal_count": 0,
        "has_memories": False,
        "memory_count": 0,
        "recent_activity": False,
        "preferred_platforms": [],
        "brand_voice": "professional",
        "creativity_level": 0.7
    }
    
    try:
        # Get user settings for personalization (with fallback if table doesn't exist)
        try:
            user_settings = db.query(UserSetting).filter(UserSetting.user_id == user.id).first()
            if user_settings:
                context["preferred_platforms"] = user_settings.preferred_platforms or list(DEFAULT_PLATFORMS)
                context["brand_voice"] = user_settings.brand_voice or DEFAULT_BRAND_VOICE
                context["creativity_level"] = user_settings.creativity_level or DEFAULT_CREATIVITY_LEVEL
        except SQLAlchemyError as settings_error:
            # Handle case where user_settings table doesn't exist yet
            logger.warning(f"UserSettings table not accessible, using defaults: {settings_error}")
            context["preferred_platforms"] = list(DEFAULT_PLATFORMS)
            context["brand_voice"] = DEFAULT_BRAND_VOICE
            context["creativity_level"] = 0.7
        
        # Analyze content history (with limits for performance and error handling)
        try:
            content_count = db.query(Content).filter(Content.user_id == user.id).limit(1000).count()
            context["content_count"] = min(content_count, MAX_CONTENT_COUNT_DISPLAY)
            context["has_content"] = content_count > 0
        except SQLAlchemyError:
            context["content_count"] = 0
            context["has_content"] = False
        
        # Check for recent content (last 7 days, limited query)
        try:
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_content = db.query(Content).filter(
                Content.user_id == user.id,
                Content.created_at >= week_ago
            ).limit(100).count()
            context["recent_activity"] = recent_content > 0
        except SQLAlchemyError:
            context["recent_activity"] = False
        
        # Analyze goals (limited for performance)
        try:
            goal_count = db.query(Goal).filter(Goal.user_id == user.id).limit(50).count()
            context["goal_count"] = min(goal_count, 50)
            context["has_goals"] = goal_count > 0
        except SQLAlchemyError:
            context["goal_count"] = 0
            context["has_goals"] = False
        
        # Analyze memories/brand brain (limited for performance) 
        try:
            memory_count = db.query(Memory).filter(Memory.user_id == user.id).limit(100).count()
            context["memory_count"] = min(memory_count, 100)
            context["has_memories"] = memory_count > 0
        except SQLAlchemyError:
            context["memory_count"] = 0
            context["has_memories"] = False
        
    except Exception as e:
        logger.warning(f"Error analyzing user context: {e}")
    
    return context

async def generate_contextual_suggestions(user_context: Dict[str, Any], suggestion_type: str) -> List[Dict[str, Any]]:
    """Generate AI-powered contextual suggestions based on user context"""
    
    # Build AI prompt based on context
    context_info = f"""
    User Context:
    - Account age: {user_context['account_age_days']} days
    - Content created: {user_context['content_count']} posts
    - Goals set: {user_context['goal_count']} goals
    - Brand brain entries: {user_context['memory_count']} memories
    - Recent activity: {user_context['recent_activity']}
    - Preferred platforms: {', '.join(user_context['preferred_platforms'])}
    - Brand voice: {user_context['brand_voice']}
    - Creativity level: {user_context['creativity_level']}
    
    Generate 4 personalized AI suggestions for {suggestion_type} that would be most valuable for this user.
    Consider their experience level, activity patterns, and preferences.
    """
    
    try:
        # Generate contextual suggestions using OpenAI directly with timeout
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Use the utility function to get correct parameters for GPT-5
        from backend.core.openai_utils import get_openai_completion_params
        
        params = get_openai_completion_params(
            model="gpt-4.1-mini",
            max_tokens=1500,
            temperature=0.7,  # Will be ignored for GPT-5 models
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI social media assistant. Generate specific, actionable suggestions in JSON format."
                },
                {
                    "role": "user", 
                    "content": f"""Based on the user context below, generate 4 specific, actionable suggestions for {suggestion_type}.

{context_info}

Return suggestions as JSON array with this format:
[
  {{
    "id": "unique-id",
    "title": "Action title",
    "description": "Specific description based on user context",
    "action": "Button text",
    "color": "blue|purple|green|orange",
    "ai_prompt": "Specific AI prompt for this action",
    "estimated_time": "X minutes/seconds",
    "priority": 1-10,
    "personalization_score": 0.0-1.0
  }}
]

Make suggestions specific to their experience level and current situation. For new users, focus on getting started. For experienced users, focus on optimization and growth."""
                }
            ],
            timeout=10.0  # 10 second timeout to prevent long waits
        )
        
        response = await client.chat.completions.create(**params)
        
        ai_response = response.choices[0].message.content
        
        # Parse AI response with robust error handling
        import json
        import re
        
        if not ai_response or not ai_response.strip():
            logger.warning("Empty AI response received")
            return []
            
        try:
            # Clean the response - sometimes AI returns text before/after JSON
            cleaned_response = ai_response.strip()
            
            # Try to extract JSON array from the response
            json_match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                suggestions_data = json.loads(json_text)
                
                # Validate that it's a list
                if isinstance(suggestions_data, list):
                    return suggestions_data
                else:
                    logger.warning(f"AI returned non-list JSON: {type(suggestions_data)}")
                    return []
            else:
                logger.warning(f"No JSON array found in AI response: {cleaned_response[:200]}...")
                return []
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI suggestions JSON: {e}. Response: {ai_response[:200]}...")
            return []
        except Exception as e:  # final safeguard at boundary
            logger.warning(f"Unexpected error parsing AI response: {e}")
            return []
        
    except Exception as e:
        logger.error(f"Error generating AI suggestions (timeout or API issue): {e}")
        # Return empty to trigger fast fallback suggestions
        return []

def get_fallback_suggestions(suggestion_type: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Provide fallback suggestions if AI generation fails"""
    fallbacks = {
        "content": [
            {
                "id": "trending-content",
                "title": "Generate trending content ideas",
                "description": "AI will research current trends and create personalized post ideas",
                "action": "Generate Ideas",
                "color": "blue",
                "ai_prompt": "Generate trending social media post ideas based on current industry trends",
                "estimated_time": "30 seconds",
                "priority": 3,
                "personalization_score": 0.6
            },
            {
                "id": "content-calendar",
                "title": "Create content calendar",
                "description": "Plan and schedule your posts for optimal engagement",
                "action": "Plan Calendar",
                "color": "purple",
                "ai_prompt": "Create a weekly content calendar with strategic posting times",
                "estimated_time": "1 minute",
                "priority": 2,
                "personalization_score": 0.7
            }
        ],
        "goals": [
            {
                "id": "growth-goals",
                "title": "Set growth targets",
                "description": "AI-recommended goals based on your current performance",
                "action": "Create Goals",
                "color": "green",
                "ai_prompt": "Suggest realistic growth goals based on current metrics",
                "estimated_time": "30 seconds",
                "priority": 1,
                "personalization_score": 0.8
            },
            {
                "id": "engagement-goals",
                "title": "Boost engagement rates",
                "description": "Set targets to increase likes, comments, and shares",
                "action": "Set Targets",
                "color": "blue",
                "ai_prompt": "Create engagement improvement goals and strategies",
                "estimated_time": "1 minute",
                "priority": 2,
                "personalization_score": 0.7
            },
            {
                "id": "brand-voice",
                "title": "Optimize brand voice",
                "description": "Refine your content tone and messaging consistency",
                "action": "Optimize Voice",
                "color": "orange",
                "ai_prompt": "Analyze and optimize brand voice consistency across posts",
                "estimated_time": "1 minute",
                "priority": 4,
                "personalization_score": 0.5
            },
            {
                "id": "hashtag-research",
                "title": "Research trending hashtags",
                "description": "Find the best hashtags for your niche and audience",
                "action": "Research Tags",
                "color": "green",
                "ai_prompt": "Research and suggest trending hashtags for better reach",
                "estimated_time": "45 seconds",
                "priority": 5,
                "personalization_score": 0.4
            }
        ],
        "inbox": [
            {
                "id": "inbox-cleanup",
                "title": "Organize social inbox",
                "description": "Sort and prioritize your social media messages and mentions",
                "action": "Clean Inbox",
                "color": "purple",
                "ai_prompt": "Organize and prioritize social media inbox items",
                "estimated_time": "2 minutes",
                "priority": 3,
                "personalization_score": 0.6
            }
        ],
        "memory": [
            {
                "id": "brand-knowledge",
                "title": "Update brand knowledge",
                "description": "Add key brand information to your AI memory",
                "action": "Update Knowledge",
                "color": "blue",
                "ai_prompt": "Suggest important brand information to store in memory",
                "estimated_time": "1 minute",
                "priority": 2,
                "personalization_score": 0.8
            },
            {
                "id": "audience-insights",
                "title": "Store audience insights",
                "description": "Capture key learnings about your audience preferences",
                "action": "Save Insights",
                "color": "green",
                "ai_prompt": "Analyze and store audience behavior patterns",
                "estimated_time": "45 seconds",
                "priority": 3,
                "personalization_score": 0.7
            },
            {
                "id": "content-performance",
                "title": "Record content performance",
                "description": "Remember what types of content work best",
                "action": "Record Performance",
                "color": "orange",
                "ai_prompt": "Identify and store successful content patterns",
                "estimated_time": "30 seconds",
                "priority": 4,
                "personalization_score": 0.6
            }
        ],
        "scheduler": [
            {
                "id": "optimal-timing",
                "title": "Find optimal posting times",
                "description": "AI analysis of when your audience is most active",
                "action": "Analyze Timing",
                "color": "purple",
                "ai_prompt": "Analyze engagement data to suggest optimal posting times",
                "estimated_time": "1 minute",
                "priority": 1,
                "personalization_score": 0.9
            },
            {
                "id": "content-calendar",
                "title": "Create weekly schedule",
                "description": "Plan your content posting schedule for the week",
                "action": "Plan Schedule",
                "color": "blue",
                "ai_prompt": "Create a strategic weekly content posting calendar",
                "estimated_time": "2 minutes",
                "priority": 2,
                "personalization_score": 0.8
            },
            {
                "id": "automation-setup",
                "title": "Set up automated posting",
                "description": "Configure smart posting automation for consistent presence",
                "action": "Setup Automation",
                "color": "green",
                "ai_prompt": "Configure intelligent automated posting settings",
                "estimated_time": "3 minutes",
                "priority": 3,
                "personalization_score": 0.7
            }
        ]
    }
    
    # Return suggestions for the requested type, or default to content
    return fallbacks.get(suggestion_type, fallbacks["content"])[:4]  # Limit to 4 suggestions

@router.post("/suggestions", response_model=SuggestionsResponse)
async def get_contextual_suggestions(
    request: SuggestionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get personalized AI suggestions based on user context"""
    try:
        # Analyze user context
        user_context = await analyze_user_context(current_user, db, request.type)
        user_context.update(request.context)  # Merge with request context
        
        # Generate AI suggestions
        ai_suggestions = await generate_contextual_suggestions(user_context, request.type)
        
        # Fallback to fast static suggestions if AI fails or is slow
        if not ai_suggestions:
            ai_suggestions = get_fallback_suggestions(request.type, user_context)
            logger.info(f"Using fast fallback suggestions for user {current_user.id} (type: {request.type})")
        
        # Limit results
        ai_suggestions = ai_suggestions[:request.limit]
        
        # Convert to response models with validation error handling
        suggestions = []
        for suggestion in ai_suggestions:
            try:
                suggestions.append(AISuggestion(**suggestion))
            except Exception as validation_error:
                logger.warning(f"Invalid AI suggestion format: {validation_error}. Suggestion: {suggestion}")
                # Skip malformed suggestions, continue with others
                continue
        
        # If all AI suggestions were malformed, fall back to static suggestions
        if not suggestions:
            logger.warning("All AI suggestions were malformed, falling back to static suggestions")
            fallback_suggestions = get_fallback_suggestions(request.type, user_context)[:request.limit]
            for suggestion in fallback_suggestions:
                try:
                    suggestions.append(AISuggestion(**suggestion))
                except Exception as fallback_error:
                    logger.error(f"Even fallback suggestion is malformed: {fallback_error}. Suggestion: {suggestion}")
                    continue
        
        # Determine personalization level
        avg_score = sum(s.personalization_score for s in suggestions) / len(suggestions) if suggestions else 0
        if avg_score >= 0.8:
            personalization_level = "high"
        elif avg_score >= 0.6:
            personalization_level = "medium"  
        else:
            personalization_level = "basic"
        
        # Create context summary
        context_summary = f"Based on your {user_context['account_age_days']}-day journey with {user_context['content_count']} posts created"
        
        return SuggestionsResponse(
            suggestions=suggestions,
            context_summary=context_summary,
            personalization_level=personalization_level
        )
        
    except Exception as e:
        logger.error(f"Error getting contextual suggestions for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate suggestions"
        )

@router.get("/suggestion-types")
async def get_available_suggestion_types():
    """Get list of available suggestion types"""
    return {
        "types": ["content", "goals", "inbox", "memory", "scheduler"],
        "descriptions": {
            "content": "Content creation and posting suggestions",
            "goals": "Goal setting and achievement suggestions", 
            "inbox": "Social inbox management suggestions",
            "memory": "Brand brain and knowledge suggestions",
            "scheduler": "Content scheduling and timing suggestions"
        }
    }