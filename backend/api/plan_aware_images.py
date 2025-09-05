"""
Plan-Aware Image Generation API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import logging

from backend.db.database import get_db
from backend.auth.dependencies import get_current_user
from backend.db.models import User
from backend.services.plan_aware_image_service import get_plan_aware_image_service
from backend.middleware.feature_flag_enforcement import require_flag
from backend.middleware.subscription_enforcement import require_feature, check_usage_limit
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["plan-aware-images"])


# Pydantic models
class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000, description="Image description prompt")
    platform: str = Field(default="instagram", description="Target platform")
    quality_preset: Optional[str] = Field(default=None, description="Quality preset (draft, standard, premium)")
    model: str = Field(default="auto", description="AI model (auto, grok2, dalle3, gpt_image_1)")
    content_context: Optional[str] = Field(default=None, max_length=500, description="Content context")
    industry_context: Optional[str] = Field(default=None, max_length=200, description="Industry context")
    tone: str = Field(default="professional", description="Tone (professional, casual, creative)")
    enable_post_processing: bool = Field(default=True, description="Enable post-processing")
    generate_alt_text: bool = Field(default=True, description="Generate alt text")
    custom_options: Optional[Dict[str, Any]] = Field(default=None, description="Custom options")


class ImageCapabilitiesResponse(BaseModel):
    plan: str
    monthly_limit: int
    current_usage: int
    remaining: int
    can_generate: bool
    available_models: List[str]
    max_quality: str
    features: Dict[str, bool]


@router.post("/generate")
async def generate_image_with_plan_gating(
    request: ImageGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("image_generation")),
    _usage_check: None = Depends(check_usage_limit("image_generation", "max_image_generations_per_month"))
):
    """Generate an image with plan-based feature gating and usage tracking"""
    try:
        image_service = get_plan_aware_image_service(db)
        
        result = await image_service.generate_image_with_plan_gating(
            user_id=current_user.id,
            prompt=request.prompt,
            platform=request.platform,
            quality_preset=request.quality_preset,
            model=request.model,
            content_context=request.content_context,
            industry_context=request.industry_context,
            tone=request.tone,
            custom_options=request.custom_options,
            enable_post_processing=request.enable_post_processing,
            generate_alt_text=request.generate_alt_text
        )
        
        # Handle different result statuses
        if result["status"] == "limit_exceeded":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": result["error"],
                    "plan": result["plan"],
                    "usage": result["usage"],
                    "upgrade_required": True,
                    "suggested_plans": result["suggested_plans"]
                }
            )
        
        elif result["status"] == "model_restricted":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": result["error"],
                    "plan": result["plan"],
                    "available_models": result["available_models"],
                    "upgrade_required": True,
                    "suggested_plans": result["suggested_plans"]
                }
            )
        
        elif result["status"] == "feature_restricted":
            # Return warning but allow generation with fallback options
            return {
                "status": "partial_success",
                "message": result["error"],
                "plan": result["plan"],
                "restricted_features": result["restricted_features"],
                "fallback_options": result["fallback_options"],
                "upgrade_suggested": True,
                "suggested_plans": result["suggested_plans"]
            }
        
        elif result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image generation API error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate image"
        )


@router.get("/capabilities", response_model=ImageCapabilitiesResponse)
async def get_image_capabilities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("image_generation"))
):
    """Get user's image generation capabilities and current usage"""
    try:
        image_service = get_plan_aware_image_service(db)
        capabilities = await image_service.get_user_image_capabilities(current_user.id)
        
        if "error" in capabilities:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=capabilities["error"]
            )
        
        return ImageCapabilitiesResponse(**capabilities)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching image capabilities for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch image capabilities"
        )


@router.get("/usage")
async def get_image_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("image_generation"))
):
    """Get detailed usage information for current user"""
    try:
        image_service = get_plan_aware_image_service(db)
        capabilities = await image_service.get_user_image_capabilities(current_user.id)
        
        if "error" in capabilities:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=capabilities["error"]
            )
        
        return {
            "plan": capabilities["plan"],
            "usage": {
                "current_month": capabilities["current_usage"],
                "limit": capabilities["monthly_limit"],
                "remaining": capabilities["remaining"],
                "percentage_used": (capabilities["current_usage"] / capabilities["monthly_limit"] * 100) if capabilities["monthly_limit"] > 0 else 0
            },
            "capabilities": {
                "models": capabilities["available_models"],
                "max_quality": capabilities["max_quality"],
                "features": capabilities["features"]
            },
            "recommendations": {
                "upgrade_needed": capabilities["remaining"] <= 5,
                "suggested_plans": ["pro", "enterprise"] if capabilities["plan"] in ["free", "starter"] else []
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching image usage for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch image usage"
        )


@router.get("/models")
async def get_available_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("image_generation"))
):
    """Get available AI models for user's plan"""
    try:
        image_service = get_plan_aware_image_service(db)
        capabilities = await image_service.get_user_image_capabilities(current_user.id)
        
        if "error" in capabilities:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=capabilities["error"]
            )
        
        model_details = {
            "grok2_basic": {
                "name": "Grok 2 Basic",
                "description": "Fast, efficient image generation",
                "quality": "standard",
                "speed": "fast"
            },
            "grok2_premium": {
                "name": "Grok 2 Premium", 
                "description": "Enhanced quality and detail",
                "quality": "high",
                "speed": "medium"
            },
            "dalle3": {
                "name": "DALL-E 3",
                "description": "OpenAI's advanced image model",
                "quality": "premium",
                "speed": "medium"
            },
            "gpt_image_1": {
                "name": "GPT Image 1",
                "description": "Next-generation image synthesis",
                "quality": "premium",
                "speed": "slow"
            }
        }
        
        available_models = []
        for model_key in capabilities["available_models"]:
            if model_key in model_details:
                model_info = model_details[model_key].copy()
                model_info["key"] = model_key
                available_models.append(model_info)
        
        return {
            "plan": capabilities["plan"],
            "available_models": available_models,
            "recommended": available_models[-1]["key"] if available_models else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching available models for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch available models"
        )