"""
FastAPI dependencies and middleware for subscription tier enforcement
Provides decorators and dependencies for protecting premium endpoints
"""
import logging
from typing import Optional, Set, Dict, Any
from functools import wraps
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.auth.dependencies import get_current_user, AuthUser
from backend.services.subscription_service import (
    get_subscription_service, 
    SubscriptionService, 
    SubscriptionTier,
    InsufficientTierError
)
from backend.services.usage_tracking_service import get_usage_tracking_service

logger = logging.getLogger(__name__)

class SubscriptionDependencies:
    """FastAPI dependencies for subscription enforcement"""
    
    @staticmethod 
    def get_subscription_service_dep(db: Session = Depends(get_db)) -> SubscriptionService:
        """Dependency to get subscription service"""
        return get_subscription_service(db)
    
    @staticmethod
    def require_feature(feature: str):
        """
        FastAPI dependency factory to require specific feature access
        
        Usage:
            @router.post("/premium-endpoint")
            async def premium_endpoint(
                user: AuthUser = Depends(get_current_user),
                _: None = Depends(require_feature("premium_image_generation"))
            ):
                ...
        """
        def dependency(
            current_user: AuthUser = Depends(get_current_user),
            subscription_service: SubscriptionService = Depends(SubscriptionDependencies.get_subscription_service_dep)
        ):
            user_id = int(current_user.user_id)
            
            if not subscription_service.has_feature(user_id, feature):
                user_tier = subscription_service.get_user_tier(user_id)
                
                # Provide helpful upgrade message
                if user_tier == SubscriptionTier.BASIC:
                    upgrade_to = "Premium or Enterprise"
                elif user_tier == SubscriptionTier.PREMIUM:
                    upgrade_to = "Enterprise"
                else:
                    upgrade_to = "higher tier"
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "insufficient_tier",
                        "message": f"This feature requires {upgrade_to} plan",
                        "feature": feature,
                        "current_tier": user_tier.value,
                        "upgrade_required": True
                    }
                )
            return None
        
        return dependency
    
    @staticmethod
    def require_tier(minimum_tier: SubscriptionTier):
        """
        FastAPI dependency factory to require minimum subscription tier
        
        Usage:
            @router.post("/enterprise-endpoint")
            async def enterprise_endpoint(
                user: AuthUser = Depends(get_current_user),
                _: None = Depends(require_tier(SubscriptionTier.ENTERPRISE))
            ):
                ...
        """
        def dependency(
            current_user: AuthUser = Depends(get_current_user),
            subscription_service: SubscriptionService = Depends(SubscriptionDependencies.get_subscription_service_dep)
        ):
            user_id = int(current_user.user_id)
            user_tier = subscription_service.get_user_tier(user_id)
            
            from backend.services.subscription_service import TIER_HIERARCHY
            
            if TIER_HIERARCHY[user_tier] < TIER_HIERARCHY[minimum_tier]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "insufficient_tier",
                        "message": f"This endpoint requires {minimum_tier.value.title()} plan or higher",
                        "current_tier": user_tier.value,
                        "required_tier": minimum_tier.value,
                        "upgrade_required": True
                    }
                )
            return None
        
        return dependency
    
    @staticmethod
    def check_usage_limit(usage_type: str, limit_key: str):
        """
        FastAPI dependency factory to check usage limits with actual tracking
        
        Usage:
            @router.post("/api/generate-image")
            async def generate_image(
                user: AuthUser = Depends(get_current_user),
                _: None = Depends(check_usage_limit("image_generation", "max_image_generations_per_month"))
            ):
                ...
        """
        async def dependency(
            current_user: AuthUser = Depends(get_current_user),
            subscription_service: SubscriptionService = Depends(SubscriptionDependencies.get_subscription_service_dep),
            db: Session = Depends(get_db)
        ):
            user_id = int(current_user.user_id)
            
            # Get user tier limits
            limits = subscription_service.get_tier_limits(user_id)
            limit_value = limits.get(limit_key, 0)
            
            if limit_value == 0:
                user_tier = subscription_service.get_user_tier(user_id)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "feature_not_available",
                        "message": f"This feature is not available in your {user_tier.value.title()} plan",
                        "current_tier": user_tier.value,
                        "upgrade_required": True
                    }
                )
            
            # Check actual usage
            usage_service = get_usage_tracking_service(db)
            usage_status = await usage_service.check_usage_limit(user_id, usage_type, limit_value)
            
            if usage_status["exceeded"]:
                user_tier = subscription_service.get_user_tier(user_id)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "usage_limit_exceeded",
                        "message": f"Monthly {usage_type.replace('_', ' ')} limit exceeded ({usage_status['current_usage']}/{usage_status['limit']})",
                        "current_tier": user_tier.value,
                        "usage": usage_status,
                        "upgrade_required": True
                    }
                )
            
            return None
        
        return dependency
    
    @staticmethod
    def get_user_context():
        """
        Dependency to get user subscription context
        
        Returns user tier, features, and limits for use in endpoints
        """
        def dependency(
            current_user: AuthUser = Depends(get_current_user),
            subscription_service: SubscriptionService = Depends(SubscriptionDependencies.get_subscription_service_dep)
        ) -> Dict[str, Any]:
            user_id = int(current_user.user_id)
            
            return {
                "user_id": user_id,
                "tier": subscription_service.get_user_tier(user_id),
                "features": subscription_service.get_tier_features(user_id),
                "limits": subscription_service.get_tier_limits(user_id)
            }
        
        return dependency
    
    @staticmethod 
    async def track_usage_after_operation(
        user_id: int,
        organization_id: int,
        usage_type: str,
        resource: Optional[str] = None,
        quantity: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> bool:
        """
        Helper function to track usage after an operation
        
        Args:
            user_id: User ID
            organization_id: Organization ID
            usage_type: Type of usage (image_generation, post_creation, etc.)
            resource: Specific resource used
            quantity: Amount used
            metadata: Additional context
            db: Database session
            
        Returns:
            Success status
        """
        if not db:
            logger.warning("Database session not provided for usage tracking")
            return False
            
        try:
            usage_service = get_usage_tracking_service(db)
            return await usage_service.track_usage(
                user_id=user_id,
                organization_id=organization_id,
                usage_type=usage_type,
                resource=resource,
                quantity=quantity,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Failed to track usage: {e}")
            return False

# Convenience instances
require_feature = SubscriptionDependencies.require_feature
require_tier = SubscriptionDependencies.require_tier  
check_usage_limit = SubscriptionDependencies.check_usage_limit
# Note: get_user_context is a factory method that returns a dependency function
# It should be called with () when used as a Depends()

# Specific tier requirements
require_premium = require_tier(SubscriptionTier.PREMIUM)
require_enterprise = require_tier(SubscriptionTier.ENTERPRISE)

# Common feature requirements
require_premium_images = require_feature("premium_image_generation")
require_enterprise_images = require_feature("enterprise_image_generation") 
require_autonomous_posting = require_feature("autonomous_posting")
require_industry_research = require_feature("industry_research")
require_advanced_automation = require_feature("advanced_automation")

def tier_protected(feature: Optional[str] = None, minimum_tier: Optional[SubscriptionTier] = None):
    """
    Function decorator for tier-based protection (for non-FastAPI functions)
    
    Args:
        feature: Feature name to require
        minimum_tier: Minimum tier to require
        
    Usage:
        @tier_protected(feature="premium_image_generation")
        def generate_premium_image(user_id: int, prompt: str):
            ...
            
        @tier_protected(minimum_tier=SubscriptionTier.ENTERPRISE)  
        def enterprise_feature(user_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user_id from function arguments
            user_id = None
            
            # Try to find user_id in various argument positions
            if args:
                if isinstance(args[0], int):
                    user_id = args[0]
                elif hasattr(args[0], 'id'):
                    user_id = args[0].id
            
            if 'user_id' in kwargs:
                user_id = kwargs['user_id']
            elif 'current_user' in kwargs:
                user = kwargs['current_user']
                user_id = int(user.user_id) if hasattr(user, 'user_id') else user.id
            
            if user_id is None:
                raise ValueError("Could not determine user_id for tier protection")
            
            # Get subscription service
            subscription_service = get_subscription_service()
            
            # Check feature requirement
            if feature and not subscription_service.has_feature(user_id, feature):
                user_tier = subscription_service.get_user_tier(user_id)
                raise InsufficientTierError(
                    f"Feature '{feature}' requires higher tier than {user_tier.value}"
                )
            
            # Check tier requirement  
            if minimum_tier:
                user_tier = subscription_service.get_user_tier(user_id)
                from backend.services.subscription_service import TIER_HIERARCHY
                
                if TIER_HIERARCHY[user_tier] < TIER_HIERARCHY[minimum_tier]:
                    raise InsufficientTierError(
                        f"Function requires {minimum_tier.value} tier, user has {user_tier.value}"
                    )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator