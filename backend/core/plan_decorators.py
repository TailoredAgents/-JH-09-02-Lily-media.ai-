"""
Decorators and utilities for plan-based access control
"""
import functools
import logging
from typing import Optional, List

from fastapi import HTTPException, status

from backend.core.plan_enforcement import PlanTier, QuotaType, PlanLimits, get_plan_manager

logger = logging.getLogger(__name__)

def require_plan(min_plan: PlanTier):
    """
    Decorator to require a minimum plan tier for endpoint access
    
    Args:
        min_plan: Minimum plan tier required
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (should be injected by FastAPI dependency)
            user = kwargs.get('user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Get user's plan
            plan_manager = get_plan_manager()
            plan_info = plan_manager.get_user_plan_info(user)
            user_plan = PlanTier(plan_info['plan'])
            
            # Check plan hierarchy
            plan_order = [PlanTier.FREE, PlanTier.BASIC, PlanTier.PROFESSIONAL, PlanTier.ENTERPRISE]
            if plan_order.index(user_plan) < plan_order.index(min_plan):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature requires {min_plan.value} plan or higher. Current plan: {user_plan.value}",
                    headers={"X-Required-Plan": min_plan.value}
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_feature(feature_name: str):
    """
    Decorator to require a specific feature for endpoint access
    
    Args:
        feature_name: Name of the required feature
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs
            user = kwargs.get('user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Get user's plan and check feature
            plan_manager = get_plan_manager()
            plan_info = plan_manager.get_user_plan_info(user)
            user_plan = PlanTier(plan_info['plan'])
            
            if not PlanLimits.has_feature(user_plan, feature_name):
                # Find minimum required plan
                required_plan = None
                for tier in [PlanTier.BASIC, PlanTier.PROFESSIONAL, PlanTier.ENTERPRISE]:
                    if PlanLimits.has_feature(tier, feature_name):
                        required_plan = tier.value
                        break
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Feature '{feature_name}' is not available in your {user_plan.value} plan",
                    headers={
                        "X-Required-Feature": feature_name,
                        "X-Required-Plan": required_plan or "enterprise"
                    }
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def enforce_quota(quota_type: QuotaType, amount: int = 1):
    """
    Decorator to enforce quota limits before allowing endpoint access
    
    Args:
        quota_type: Type of quota to enforce
        amount: Amount of quota to consume (default: 1)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs
            user = kwargs.get('user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check quota
            plan_manager = get_plan_manager()
            plan_info = plan_manager.get_user_plan_info(user)
            user_plan = PlanTier(plan_info['plan'])
            
            allowed, current_usage, limit = plan_manager.quota_manager.check_quota(
                str(user.id), user_plan, quota_type, amount
            )
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Quota exceeded for {quota_type.value}. Current: {current_usage}/{limit}",
                    headers={
                        "X-Quota-Type": quota_type.value,
                        "X-Quota-Limit": str(limit),
                        "X-Quota-Used": str(current_usage),
                        "X-Quota-Remaining": str(max(0, limit - current_usage)) if limit != -1 else "-1"
                    }
                )
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Track successful usage
            plan_manager.quota_manager.increment_usage(str(user.id), quota_type, amount)
            
            return result
        return wrapper
    return decorator

def track_usage(quota_type: QuotaType, amount: int = 1):
    """
    Decorator to track usage without enforcing limits (for analytics)
    
    Args:
        quota_type: Type of usage to track
        amount: Amount to track (default: 1)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function first
            result = await func(*args, **kwargs)
            
            # Track usage after successful execution
            try:
                user = kwargs.get('user')
                if user:
                    plan_manager = get_plan_manager()
                    plan_manager.quota_manager.increment_usage(str(user.id), quota_type, amount)
            except Exception as e:
                logger.warning(f"Failed to track usage for {quota_type.value}: {e}")
            
            return result
        return wrapper
    return decorator

class PlanGate:
    """Context manager for conditional plan-based execution"""
    
    def __init__(self, user, required_plan: Optional[PlanTier] = None, required_feature: Optional[str] = None):
        self.user = user
        self.required_plan = required_plan
        self.required_feature = required_feature
        self.allowed = False
        
    def __enter__(self):
        if not self.user:
            return self
            
        try:
            plan_manager = get_plan_manager()
            plan_info = plan_manager.get_user_plan_info(self.user)
            user_plan = PlanTier(plan_info['plan'])
            
            # Check plan requirement
            if self.required_plan:
                plan_order = [PlanTier.FREE, PlanTier.BASIC, PlanTier.PROFESSIONAL, PlanTier.ENTERPRISE]
                self.allowed = plan_order.index(user_plan) >= plan_order.index(self.required_plan)
                
            # Check feature requirement
            elif self.required_feature:
                self.allowed = PlanLimits.has_feature(user_plan, self.required_feature)
            else:
                self.allowed = True
                
        except Exception as e:
            logger.error(f"Error checking plan access: {e}")
            self.allowed = False
            
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def __bool__(self):
        return self.allowed

def get_plan_context(user) -> dict:
    """
    Get comprehensive plan context for a user
    
    Returns:
        Dictionary with plan information, limits, and current usage
    """
    if not user:
        return {
            'plan': 'free',
            'limits': {},
            'features': {},
            'usage': {},
            'authenticated': False
        }
    
    try:
        plan_manager = get_plan_manager()
        plan_info = plan_manager.get_user_plan_info(user)
        user_plan = PlanTier(plan_info['plan'])
        usage_summary = plan_manager.get_user_usage_summary(str(user.id), user_plan)
        
        return {
            'plan': plan_info['plan'],
            'limits': {k.value if hasattr(k, 'value') else str(k): v for k, v in plan_info['limits'].items()},
            'features': plan_info['features'],
            'usage': usage_summary,
            'authenticated': True
        }
        
    except Exception as e:
        logger.error(f"Error getting plan context: {e}")
        return {
            'plan': 'free',
            'limits': {},
            'features': {},
            'usage': {},
            'authenticated': True,
            'error': str(e)
        }

# Convenience decorators for common plan requirements
require_basic_plan = require_plan(PlanTier.BASIC)
require_professional_plan = require_plan(PlanTier.PROFESSIONAL)
require_enterprise_plan = require_plan(PlanTier.ENTERPRISE)

# Convenience decorators for common features
require_multi_platform = require_feature("multi_platform_posting")
require_advanced_analytics = require_feature("advanced_analytics")
require_api_access = require_feature("api_access")
require_custom_workflows = require_feature("custom_workflows")
require_bulk_operations = require_feature("bulk_operations")

# Convenience decorators for common quotas
enforce_content_generation_quota = enforce_quota(QuotaType.CONTENT_GENERATIONS)
enforce_image_generation_quota = enforce_quota(QuotaType.IMAGE_GENERATIONS)
enforce_ai_suggestions_quota = enforce_quota(QuotaType.AI_SUGGESTIONS)
enforce_social_posts_quota = enforce_quota(QuotaType.SOCIAL_POSTS)