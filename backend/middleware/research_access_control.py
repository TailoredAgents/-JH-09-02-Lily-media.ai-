"""
Research Access Control Middleware

Comprehensive access control for research features combining:
1. Feature flags (ENABLE_DEEP_RESEARCH)
2. Plan-based subscription enforcement
3. Usage quota validation
4. Rate limiting for research operations

Provides tiered access to different research capabilities based on subscription plans.
"""

import logging
import time
from typing import Optional, Dict, Any
from functools import wraps
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.auth.dependencies import get_current_user, AuthUser
from backend.core.feature_flags import ff
from backend.services.plan_service import PlanService
from backend.services.usage_tracking_service import get_usage_tracking_service
from backend.core.observability import get_observability_manager

logger = logging.getLogger(__name__)
observability = get_observability_manager()

class ResearchAccessLevel:
    """Research access levels based on subscription plans"""
    
    # Basic research capabilities (Free/Starter)
    BASIC = {
        'knowledge_base_queries': 5,  # per day
        'content_opportunities': True,
        'recent_intelligence': True,
        'research_status': True,
        'research_analytics': False,
        'immediate_research': False,
        'setup_industry_research': False,
        'deep_research': False
    }
    
    # Standard research capabilities (Professional)
    STANDARD = {
        'knowledge_base_queries': 25,  # per day
        'content_opportunities': True,
        'recent_intelligence': True,
        'research_status': True,
        'research_analytics': True,
        'immediate_research': 3,  # per day
        'setup_industry_research': 2,  # max industries
        'deep_research': False
    }
    
    # Premium research capabilities (Enterprise)
    PREMIUM = {
        'knowledge_base_queries': 100,  # per day
        'content_opportunities': True,
        'recent_intelligence': True,
        'research_status': True,
        'research_analytics': True,
        'immediate_research': 10,  # per day
        'setup_industry_research': 10,  # max industries
        'deep_research': True
    }
    
    # Enterprise research capabilities (Enterprise+)
    ENTERPRISE = {
        'knowledge_base_queries': -1,  # unlimited
        'content_opportunities': True,
        'recent_intelligence': True,
        'research_status': True,
        'research_analytics': True,
        'immediate_research': -1,  # unlimited
        'setup_industry_research': -1,  # unlimited
        'deep_research': True
    }

class ResearchAccessError(HTTPException):
    """Exception raised when research access is denied"""
    
    def __init__(self, reason: str, upgrade_suggestion: str = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "research_access_denied",
                "reason": reason,
                "upgrade_suggestion": upgrade_suggestion or "Upgrade your plan to access advanced research features",
                "help_center": "https://help.lilymedia.ai/research-features",
                "upgrade_url": "https://app.lilymedia.ai/billing/upgrade"
            }
        )

class ResearchAccessController:
    """Controller for research access validation and enforcement"""
    
    def __init__(self, db: Session, user: AuthUser):
        self.db = db
        self.user = user
        self.plan_service = PlanService(db, int(user.user_id))
        self.usage_tracker = get_usage_tracking_service()
        
        # Determine access level based on plan
        self.access_level = self._determine_access_level()
    
    def _determine_access_level(self) -> Dict[str, Any]:
        """Determine research access level based on user's plan"""
        try:
            capabilities = self.plan_service.get_user_capabilities()
            
            if capabilities.has_autopilot_research():
                # Enterprise+ plans get full research access
                if capabilities.get_plan_name().lower() in ['enterprise', 'enterprise+']:
                    return ResearchAccessLevel.ENTERPRISE
                else:
                    return ResearchAccessLevel.PREMIUM
            else:
                # Professional plans get standard research
                if capabilities.get_plan_name().lower() in ['professional', 'pro']:
                    return ResearchAccessLevel.STANDARD
                else:
                    # Free/Starter plans get basic research
                    return ResearchAccessLevel.BASIC
                    
        except Exception as e:
            logger.error(f"Failed to determine research access level: {e}")
            # Default to basic access on error
            return ResearchAccessLevel.BASIC
    
    async def validate_feature_access(self, feature: str, 
                                    operation_cost: int = 1) -> bool:
        """
        Validate access to a specific research feature
        
        Args:
            feature: Research feature name (e.g., 'knowledge_base_queries')
            operation_cost: Cost/count for quota tracking
            
        Returns:
            True if access allowed, raises ResearchAccessError if denied
        """
        # 1. Check feature flag first
        if not ff("ENABLE_DEEP_RESEARCH"):
            raise ResearchAccessError(
                reason="Research features are currently disabled",
                upgrade_suggestion="Research features are temporarily unavailable"
            )
        
        # 2. Check if feature is available in access level
        if feature not in self.access_level:
            raise ResearchAccessError(
                reason=f"Research feature '{feature}' not available on your plan",
                upgrade_suggestion=f"Upgrade to Professional or Enterprise to access {feature}"
            )
        
        feature_limit = self.access_level[feature]
        
        # 3. Check boolean features
        if isinstance(feature_limit, bool):
            if not feature_limit:
                plan_name = self.plan_service.get_user_capabilities().get_plan_name()
                raise ResearchAccessError(
                    reason=f"Feature '{feature}' not available on {plan_name} plan",
                    upgrade_suggestion=f"Upgrade to access advanced research features"
                )
            return True
        
        # 4. Check quota-based features
        if isinstance(feature_limit, int):
            if feature_limit == -1:  # Unlimited
                return True
            
            if feature_limit == 0:  # Not allowed
                raise ResearchAccessError(
                    reason=f"Feature '{feature}' not available on your plan",
                    upgrade_suggestion="Upgrade to access research features"
                )
            
            # Check current usage
            today_usage = await self._get_daily_usage(feature)
            
            if today_usage + operation_cost > feature_limit:
                raise ResearchAccessError(
                    reason=f"Daily limit exceeded for '{feature}' ({today_usage}/{feature_limit})",
                    upgrade_suggestion=f"Upgrade your plan for higher research limits"
                )
            
            # Track the usage
            await self._track_usage(feature, operation_cost)
            
            return True
        
        # Default: allow access
        return True
    
    async def _get_daily_usage(self, feature: str) -> int:
        """Get today's usage count for a feature"""
        try:
            from datetime import date
            today = date.today().isoformat()
            
            usage_key = f"research_{feature}_{self.user.user_id}_{today}"
            usage = await self.usage_tracker.get_usage_count(usage_key)
            return usage or 0
            
        except Exception as e:
            logger.error(f"Failed to get daily usage for {feature}: {e}")
            return 0
    
    async def _track_usage(self, feature: str, count: int = 1):
        """Track feature usage for quota enforcement"""
        try:
            from datetime import date
            today = date.today().isoformat()
            
            usage_key = f"research_{feature}_{self.user.user_id}_{today}"
            await self.usage_tracker.increment_usage(usage_key, count, expire_seconds=86400)  # 24 hours
            
            # Log for observability
            if observability:
                observability.add_sentry_breadcrumb(
                    f"Research feature used: {feature}",
                    category="research_access",
                    data={
                        "feature": feature,
                        "user_id": self.user.user_id,
                        "count": count,
                        "date": today
                    }
                )
            
        except Exception as e:
            logger.error(f"Failed to track usage for {feature}: {e}")
    
    def get_access_summary(self) -> Dict[str, Any]:
        """Get summary of research access capabilities"""
        capabilities = self.plan_service.get_user_capabilities()
        
        return {
            "plan": capabilities.get_plan_name(),
            "research_enabled": ff("ENABLE_DEEP_RESEARCH"),
            "autopilot_research": capabilities.has_autopilot_research(),
            "access_level": self.access_level,
            "limits": {
                feature: limit for feature, limit in self.access_level.items()
                if isinstance(limit, int) and limit != -1
            }
        }

# FastAPI Dependencies
def get_research_access_controller(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
) -> ResearchAccessController:
    """Dependency to get research access controller"""
    return ResearchAccessController(db, current_user)

def require_research_feature(feature: str, operation_cost: int = 1):
    """
    FastAPI dependency factory to require specific research feature access
    
    Usage:
        @router.post("/research-endpoint")
        async def research_endpoint(
            _: None = Depends(require_research_feature("immediate_research"))
        ):
            ...
    """
    async def dependency(
        access_controller: ResearchAccessController = Depends(get_research_access_controller)
    ):
        await access_controller.validate_feature_access(feature, operation_cost)
        return None
    
    return dependency

def require_basic_research():
    """Dependency for basic research access (knowledge base queries)"""
    return require_research_feature("knowledge_base_queries")

def require_advanced_research():
    """Dependency for advanced research access (immediate research)"""
    return require_research_feature("immediate_research")

def require_deep_research():
    """Dependency for deep research access (industry setup)"""
    return require_research_feature("deep_research")

def require_research_analytics():
    """Dependency for research analytics access"""
    return require_research_feature("research_analytics")

# Middleware for request-level research access logging
async def log_research_access(request: Request, call_next):
    """Middleware to log research API access attempts"""
    
    # Only log for research endpoints
    if "/deep-research" not in str(request.url):
        return await call_next(request)
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Log successful access
        duration = time.time() - start_time
        logger.info(f"Research API access: {request.method} {request.url.path} - {response.status_code} ({duration:.2f}s)")
        
        return response
        
    except Exception as e:
        # Log failed access
        duration = time.time() - start_time
        logger.warning(f"Research API access failed: {request.method} {request.url.path} - {type(e).__name__}: {str(e)} ({duration:.2f}s)")
        raise