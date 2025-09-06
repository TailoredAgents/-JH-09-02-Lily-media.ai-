"""
Plan-Aware Image Generation Service
Adds plan-based feature gating and usage tracking to the image generation service
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from backend.services.image_generation_service import ImageGenerationService
from backend.services.plan_service import PlanService
from backend.db.models import User
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PlanAwareImageService:
    """
    Image generation service with plan-based feature gating and usage tracking
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.image_service = ImageGenerationService()
        self.plan_service = PlanService(db)
        
        # Plan-based quality mapping
        self.plan_quality_mapping = {
            "free": "draft",
            "starter": "standard",
            "pro": "premium",
            "enterprise": "premium"
        }
        
        # Plan-based model access
        self.plan_model_access = {
            "free": ["grok2_basic"],
            "starter": ["grok2_basic"],
            "pro": ["grok2_basic", "grok2_premium"],
            "enterprise": ["grok2_basic", "grok2_premium", "gpt_image_1"]
        }
    
    async def generate_image_with_plan_gating(
        self,
        user_id: int,
        prompt: str,
        platform: str = "instagram",
        quality_preset: Optional[str] = None,
        model: str = "auto",
        content_context: Optional[str] = None,
        industry_context: Optional[str] = None,
        tone: str = "professional",
        custom_options: Optional[Dict[str, Any]] = None,
        enable_post_processing: bool = True,
        generate_alt_text: bool = True,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Generate image with plan-based feature gating and usage tracking
        
        Args:
            user_id: User requesting the image generation
            prompt: Base image description
            platform: Target social media platform
            quality_preset: Quality/size preset (overrides plan default if allowed)
            model: AI model to use (auto, grok2, gpt_image_1)
            content_context: Additional context about the content
            industry_context: Industry-specific context
            tone: Desired tone for the image
            custom_options: Custom tool options
            enable_post_processing: Apply platform-specific post-processing
            generate_alt_text: Generate accessibility alt-text
            max_retries: Maximum retry attempts
            
        Returns:
            Dict containing image data, usage info, and plan constraints
        """
        try:
            # Step 1: Content moderation - validate prompt before generation
            try:
                from backend.services.content_moderation_service import moderate_content, ContentType, ModerationResult
                
                moderation_result = await moderate_content(
                    content=prompt,
                    content_type=ContentType.TEXT,
                    user_id=user_id,
                    organization_id=None,  # TODO: Get organization_id from user
                    context={
                        'type': 'image_generation_prompt',
                        'platform': platform,
                        'model': model,
                        'quality': quality_preset
                    }
                )
                
                # Block generation if content is rejected
                if moderation_result['result'] == ModerationResult.REJECTED.value:
                    return {
                        "status": "moderation_rejected",
                        "error": f"Content rejected by moderation: {moderation_result['message']}",
                        "moderation": {
                            "result": moderation_result['result'],
                            "confidence": moderation_result['confidence'],
                            "categories": moderation_result['categories'],
                            "processing_time_ms": moderation_result['processing_time_ms']
                        }
                    }
                
                # Log flagged content but allow generation with warning
                if moderation_result['result'] == ModerationResult.FLAGGED.value:
                    logger.warning(
                        f"Flagged content approved for generation: user={user_id}, "
                        f"confidence={moderation_result['confidence']:.2f}, "
                        f"categories={moderation_result['categories']}"
                    )
                
            except ImportError:
                logger.warning("Content moderation service not available - proceeding without moderation")
            except Exception as e:
                logger.error(f"Content moderation error: {e} - proceeding with generation")
            
            # Get user plan capabilities
            capabilities = self.plan_service.get_user_capabilities(user_id)
            plan_name = capabilities.get_plan_name()
            
            # Check monthly usage limit
            current_usage = await self._get_monthly_image_usage(user_id)
            if not capabilities.can_generate_images(current_usage):
                limit = capabilities.plan.image_generation_limit if capabilities.plan else 5
                return {
                    "status": "limit_exceeded",
                    "error": f"Monthly image generation limit reached ({current_usage}/{limit})",
                    "plan": plan_name,
                    "usage": {
                        "current": current_usage,
                        "limit": limit,
                        "remaining": max(0, limit - current_usage)
                    },
                    "upgrade_required": True,
                    "suggested_plans": self._get_upgrade_suggestions(plan_name)
                }
            
            # Apply plan-based quality restrictions
            effective_quality = self._get_effective_quality(quality_preset, plan_name)
            
            # Apply plan-based model restrictions
            effective_model = self._get_effective_model(model, plan_name)
            if not effective_model:
                return {
                    "status": "model_restricted",
                    "error": f"Model '{model}' not available on {plan_name} plan",
                    "plan": plan_name,
                    "available_models": self.plan_model_access.get(plan_name, ["grok2_basic"]),
                    "upgrade_required": True,
                    "suggested_plans": self._get_upgrade_suggestions(plan_name)
                }
            
            # Apply plan-based feature restrictions
            features_result = self._check_feature_access(capabilities, 
                                                       enable_post_processing,
                                                       generate_alt_text,
                                                       custom_options)
            
            if features_result["restricted"]:
                return {
                    "status": "feature_restricted",
                    "error": "Some requested features are not available on your plan",
                    "plan": plan_name,
                    "restricted_features": features_result["restricted_features"],
                    "upgrade_required": True,
                    "suggested_plans": self._get_upgrade_suggestions(plan_name),
                    # Still allow generation with available features
                    "fallback_options": features_result["available_options"]
                }
            
            # Update custom options based on plan restrictions
            if features_result.get("modified_options"):
                custom_options = features_result["modified_options"]
                enable_post_processing = features_result.get("enable_post_processing", enable_post_processing)
                generate_alt_text = features_result.get("generate_alt_text", generate_alt_text)
            
            # Generate the image with plan-appropriate settings
            generation_result = await self.image_service.generate_image(
                prompt=prompt,
                platform=platform,
                quality_preset=effective_quality,
                model=effective_model,
                content_context=content_context,
                industry_context=industry_context,
                tone=tone,
                custom_options=custom_options,
                enable_post_processing=enable_post_processing,
                generate_alt_text=generate_alt_text,
                max_retries=max_retries
            )
            
            # Track usage if generation was successful
            if generation_result.get("status") == "success":
                await self._track_image_usage(user_id, effective_model, effective_quality)
                
                # Add plan context to result
                generation_result["plan_info"] = {
                    "plan": plan_name,
                    "model_used": effective_model,
                    "quality_used": effective_quality,
                    "usage": {
                        "current": current_usage + 1,
                        "limit": capabilities.plan.image_generation_limit if capabilities.plan else 5,
                        "remaining": max(0, (capabilities.plan.image_generation_limit if capabilities.plan else 5) - current_usage - 1)
                    }
                }
            
            return generation_result
            
        except Exception as e:
            logger.error(f"Plan-aware image generation failed for user {user_id}: {e}")
            return {
                "status": "error",
                "error": f"Image generation failed: {str(e)}",
                "plan": capabilities.get_plan_name() if 'capabilities' in locals() else "unknown"
            }
    
    async def get_user_image_capabilities(self, user_id: int) -> Dict[str, Any]:
        """Get user's image generation capabilities and current usage"""
        try:
            capabilities = self.plan_service.get_user_capabilities(user_id)
            plan_name = capabilities.get_plan_name()
            current_usage = await self._get_monthly_image_usage(user_id)
            
            return {
                "plan": plan_name,
                "monthly_limit": capabilities.plan.image_generation_limit if capabilities.plan else 5,
                "current_usage": current_usage,
                "remaining": max(0, (capabilities.plan.image_generation_limit if capabilities.plan else 5) - current_usage),
                "can_generate": capabilities.can_generate_images(current_usage),
                "available_models": self.plan_model_access.get(plan_name, ["grok2_basic"]),
                "max_quality": self.plan_quality_mapping.get(plan_name, "draft"),
                "features": {
                    "post_processing": capabilities.has_premium_ai_models() or plan_name != "free",
                    "alt_text": True,  # Available to all plans
                    "custom_sizes": capabilities.has_premium_ai_models(),
                    "batch_generation": plan_name in ["pro", "enterprise"],
                    "streaming": plan_name in ["pro", "enterprise"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting image capabilities for user {user_id}: {e}")
            return {
                "plan": "unknown",
                "error": str(e)
            }
    
    def _get_effective_quality(self, requested_quality: Optional[str], plan_name: str) -> str:
        """Determine the effective quality based on plan restrictions"""
        plan_max_quality = self.plan_quality_mapping.get(plan_name, "draft")
        
        if not requested_quality:
            return plan_max_quality
        
        # Quality hierarchy: draft < standard < premium
        quality_levels = {"draft": 1, "standard": 2, "premium": 3, "story": 3, "banner": 3}
        
        requested_level = quality_levels.get(requested_quality, 1)
        max_level = quality_levels.get(plan_max_quality, 1)
        
        if requested_level <= max_level:
            return requested_quality
        else:
            logger.info(f"Quality downgraded from {requested_quality} to {plan_max_quality} for plan {plan_name}")
            return plan_max_quality
    
    def _validate_model_policy(self, model: str) -> None:
        """Validate model against content policy - prevent DALL-E usage"""
        prohibited_models = ["dalle", "dall-e", "dalle3", "dall_e", "dalle_3"]
        if any(prohibited in model.lower() for prohibited in prohibited_models):
            raise ValueError(f"Model '{model}' violates content policy. DALL-E models are prohibited.")
    
    def _get_effective_model(self, requested_model: str, plan_name: str) -> Optional[str]:
        """Determine the effective model based on plan restrictions"""
        # First validate against content policy
        self._validate_model_policy(requested_model)
        
        available_models = self.plan_model_access.get(plan_name, ["grok2_basic"])
        
        if requested_model == "auto":
            # Return best available model for the plan
            if "gpt_image_1" in available_models:
                return "gpt_image_1"
            elif "grok2_premium" in available_models:
                return "grok2_premium"
            else:
                return "grok2_basic"
        
        if requested_model in available_models:
            return requested_model
        
        # Model not available for this plan
        return None
    
    def _check_feature_access(self, capabilities, enable_post_processing: bool, 
                            generate_alt_text: bool, custom_options: Optional[Dict]) -> Dict[str, Any]:
        """Check which features are accessible based on plan"""
        plan_name = capabilities.get_plan_name()
        restricted_features = []
        available_options = {}
        modified_options = custom_options.copy() if custom_options else {}
        
        # Post-processing restrictions
        if enable_post_processing and not capabilities.has_premium_ai_models() and plan_name == "free":
            restricted_features.append("advanced_post_processing")
            enable_post_processing = False
        
        # Custom options restrictions
        if custom_options:
            if not capabilities.has_premium_ai_models():
                # Remove premium-only options
                restricted_features.extend([k for k in custom_options.keys() 
                                         if k in ["custom_size", "advanced_quality", "style_transfer"]])
                for key in ["custom_size", "advanced_quality", "style_transfer"]:
                    modified_options.pop(key, None)
        
        return {
            "restricted": len(restricted_features) > 0,
            "restricted_features": restricted_features,
            "available_options": available_options,
            "modified_options": modified_options if custom_options else None,
            "enable_post_processing": enable_post_processing,
            "generate_alt_text": generate_alt_text
        }
    
    async def _get_monthly_image_usage(self, user_id: int) -> int:
        """Get current month's image generation usage for user"""
        try:
            # Calculate current month start
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Query usage from a hypothetical usage tracking table
            # For now, return mock data - this would need to be implemented with actual usage tracking
            # TODO: Implement actual usage tracking table
            return 0
            
        except Exception as e:
            logger.error(f"Error getting monthly usage for user {user_id}: {e}")
            return 0
    
    async def _track_image_usage(self, user_id: int, model: str, quality: str) -> None:
        """Track image generation usage for billing and limits"""
        try:
            # TODO: Implement usage tracking to database
            logger.info(f"Image generated - User: {user_id}, Model: {model}, Quality: {quality}")
            pass
            
        except Exception as e:
            logger.error(f"Error tracking image usage for user {user_id}: {e}")
    
    def _get_upgrade_suggestions(self, current_plan: str) -> List[str]:
        """Get suggested plan upgrades based on current plan"""
        upgrade_map = {
            "free": ["starter", "pro"],
            "starter": ["pro", "enterprise"],
            "pro": ["enterprise"],
            "enterprise": []
        }
        return upgrade_map.get(current_plan, ["starter", "pro"])


# Singleton instance
_plan_aware_image_service = None


def get_plan_aware_image_service(db: Session) -> PlanAwareImageService:
    """Get or create plan-aware image service instance"""
    return PlanAwareImageService(db)