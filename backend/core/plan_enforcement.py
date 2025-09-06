"""
Plan and quota enforcement middleware for subscription-based feature gating
"""
import os
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import redis
from sqlalchemy import text

logger = logging.getLogger(__name__)

class PlanTier(Enum):
    """Subscription plan tiers with feature access levels"""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class QuotaType(Enum):
    """Types of usage quotas to enforce"""
    API_REQUESTS = "api_requests"
    CONTENT_GENERATIONS = "content_generations"
    IMAGE_GENERATIONS = "image_generations"
    AI_SUGGESTIONS = "ai_suggestions"
    OAUTH_CONNECTIONS = "oauth_connections"
    SOCIAL_POSTS = "social_posts"
    WEBHOOK_EVENTS = "webhook_events"
    STORAGE_MB = "storage_mb"

class PlanLimits:
    """Plan-specific limits and quotas"""
    
    PLAN_LIMITS = {
        PlanTier.FREE: {
            QuotaType.API_REQUESTS: 1000,  # per day
            QuotaType.CONTENT_GENERATIONS: 10,  # per day
            QuotaType.IMAGE_GENERATIONS: 5,  # per day
            QuotaType.AI_SUGGESTIONS: 50,  # per day
            QuotaType.OAUTH_CONNECTIONS: 2,  # total
            QuotaType.SOCIAL_POSTS: 10,  # per day
            QuotaType.WEBHOOK_EVENTS: 100,  # per day
            QuotaType.STORAGE_MB: 100,  # total
        },
        PlanTier.BASIC: {
            QuotaType.API_REQUESTS: 10000,  # per day
            QuotaType.CONTENT_GENERATIONS: 100,  # per day
            QuotaType.IMAGE_GENERATIONS: 50,  # per day
            QuotaType.AI_SUGGESTIONS: 500,  # per day
            QuotaType.OAUTH_CONNECTIONS: 10,  # total
            QuotaType.SOCIAL_POSTS: 100,  # per day
            QuotaType.WEBHOOK_EVENTS: 1000,  # per day
            QuotaType.STORAGE_MB: 1000,  # total
        },
        PlanTier.PROFESSIONAL: {
            QuotaType.API_REQUESTS: 100000,  # per day
            QuotaType.CONTENT_GENERATIONS: 1000,  # per day
            QuotaType.IMAGE_GENERATIONS: 500,  # per day
            QuotaType.AI_SUGGESTIONS: 5000,  # per day
            QuotaType.OAUTH_CONNECTIONS: 50,  # total
            QuotaType.SOCIAL_POSTS: 1000,  # per day
            QuotaType.WEBHOOK_EVENTS: 10000,  # per day
            QuotaType.STORAGE_MB: 10000,  # total
        },
        PlanTier.ENTERPRISE: {
            QuotaType.API_REQUESTS: -1,  # unlimited
            QuotaType.CONTENT_GENERATIONS: -1,  # unlimited
            QuotaType.IMAGE_GENERATIONS: -1,  # unlimited
            QuotaType.AI_SUGGESTIONS: -1,  # unlimited
            QuotaType.OAUTH_CONNECTIONS: -1,  # unlimited
            QuotaType.SOCIAL_POSTS: -1,  # unlimited
            QuotaType.WEBHOOK_EVENTS: -1,  # unlimited
            QuotaType.STORAGE_MB: -1,  # unlimited
        }
    }
    
    PLAN_FEATURES = {
        PlanTier.FREE: {
            "ai_content_generation": True,
            "basic_scheduling": True,
            "single_platform_posting": True,
            "basic_analytics": True,
            "community_support": True,
            "multi_platform_posting": False,
            "advanced_analytics": False,
            "custom_workflows": False,
            "api_access": False,
            "priority_support": False,
            "white_label": False,
            "sso": False,
            "advanced_ai_features": False,
            "bulk_operations": False,
        },
        PlanTier.BASIC: {
            "ai_content_generation": True,
            "basic_scheduling": True,
            "single_platform_posting": True,
            "basic_analytics": True,
            "community_support": True,
            "multi_platform_posting": True,
            "advanced_analytics": False,
            "custom_workflows": False,
            "api_access": True,
            "priority_support": False,
            "white_label": False,
            "sso": False,
            "advanced_ai_features": False,
            "bulk_operations": False,
        },
        PlanTier.PROFESSIONAL: {
            "ai_content_generation": True,
            "basic_scheduling": True,
            "single_platform_posting": True,
            "basic_analytics": True,
            "community_support": True,
            "multi_platform_posting": True,
            "advanced_analytics": True,
            "custom_workflows": True,
            "api_access": True,
            "priority_support": True,
            "white_label": False,
            "sso": False,
            "advanced_ai_features": True,
            "bulk_operations": True,
        },
        PlanTier.ENTERPRISE: {
            "ai_content_generation": True,
            "basic_scheduling": True,
            "single_platform_posting": True,
            "basic_analytics": True,
            "community_support": True,
            "multi_platform_posting": True,
            "advanced_analytics": True,
            "custom_workflows": True,
            "api_access": True,
            "priority_support": True,
            "white_label": True,
            "sso": True,
            "advanced_ai_features": True,
            "bulk_operations": True,
        }
    }
    
    @classmethod
    def get_limit(cls, plan: PlanTier, quota_type: QuotaType) -> int:
        """Get the limit for a specific plan and quota type"""
        return cls.PLAN_LIMITS.get(plan, {}).get(quota_type, 0)
    
    @classmethod
    def has_feature(cls, plan: PlanTier, feature: str) -> bool:
        """Check if a plan has access to a specific feature"""
        return cls.PLAN_FEATURES.get(plan, {}).get(feature, False)

class QuotaManager:
    """Redis-based quota tracking and enforcement"""
    
    def __init__(self):
        self.redis_client = self._get_redis_client()
        self.enabled = self.redis_client is not None
        
    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client for quota tracking"""
        try:
            redis_url = os.getenv('REDIS_URL')
            if not redis_url:
                logger.warning("REDIS_URL not configured - quota enforcement disabled")
                return None
                
            client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            client.ping()
            return client
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis for quota tracking: {e}")
            return None
    
    def get_quota_key(self, user_id: str, quota_type: QuotaType, period: str = "daily") -> str:
        """Generate Redis key for quota tracking"""
        date_suffix = ""
        if period == "daily":
            date_suffix = datetime.utcnow().strftime("%Y-%m-%d")
        elif period == "monthly":
            date_suffix = datetime.utcnow().strftime("%Y-%m")
        elif period == "total":
            date_suffix = "total"
            
        return f"quota:{user_id}:{quota_type.value}:{date_suffix}"
    
    def get_usage(self, user_id: str, quota_type: QuotaType, period: str = "daily") -> int:
        """Get current usage for a quota type"""
        if not self.enabled:
            return 0
            
        try:
            key = self.get_quota_key(user_id, quota_type, period)
            usage = self.redis_client.get(key)
            return int(usage) if usage else 0
            
        except Exception as e:
            logger.error(f"Failed to get quota usage: {e}")
            return 0
    
    def increment_usage(self, user_id: str, quota_type: QuotaType, amount: int = 1, period: str = "daily") -> int:
        """Increment usage counter and return new total"""
        if not self.enabled:
            return 0
            
        try:
            key = self.get_quota_key(user_id, quota_type, period)
            
            # Use pipeline for atomic operations
            pipeline = self.redis_client.pipeline()
            pipeline.incr(key, amount)
            
            # Set expiration for daily quotas
            if period == "daily":
                # Expire at end of day
                tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                expire_seconds = int((tomorrow - datetime.utcnow()).total_seconds())
                pipeline.expire(key, expire_seconds)
            elif period == "monthly":
                # Expire at end of month
                next_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if next_month.month == 12:
                    next_month = next_month.replace(year=next_month.year + 1, month=1)
                else:
                    next_month = next_month.replace(month=next_month.month + 1)
                expire_seconds = int((next_month - datetime.utcnow()).total_seconds())
                pipeline.expire(key, expire_seconds)
                
            results = pipeline.execute()
            return results[0]
            
        except Exception as e:
            logger.error(f"Failed to increment quota usage: {e}")
            return 0
    
    def check_quota(self, user_id: str, plan: PlanTier, quota_type: QuotaType, amount: int = 1) -> Tuple[bool, int, int]:
        """
        Check if quota allows for additional usage
        
        Returns:
            (allowed, current_usage, limit)
        """
        limit = PlanLimits.get_limit(plan, quota_type)
        
        # Unlimited quota
        if limit == -1:
            return True, 0, -1
            
        current_usage = self.get_usage(user_id, quota_type)
        allowed = (current_usage + amount) <= limit
        
        return allowed, current_usage, limit

class PlanEnforcementMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce plan limits and feature access"""
    
    def __init__(self, app):
        super().__init__(app)
        self.quota_manager = QuotaManager()
        self.enabled = os.getenv('PLAN_ENFORCEMENT_ENABLED', 'true').lower() == 'true'
        
        # Endpoint-specific quota mappings
        self.endpoint_quotas = {
            '/api/content/generate': QuotaType.CONTENT_GENERATIONS,
            '/api/content/generate-image': QuotaType.IMAGE_GENERATIONS,
            '/api/ai/suggestions': QuotaType.AI_SUGGESTIONS,
            '/api/social-platforms/post': QuotaType.SOCIAL_POSTS,
            '/api/webhooks': QuotaType.WEBHOOK_EVENTS,
        }
        
        # Feature-protected endpoints
        self.feature_endpoints = {
            '/api/analytics/advanced': 'advanced_analytics',
            '/api/workflows/custom': 'custom_workflows',
            '/api/bulk': 'bulk_operations',
            '/api/ai/advanced': 'advanced_ai_features',
            '/api/sso': 'sso',
        }
        
    async def dispatch(self, request: Request, call_next):
        """Process request with plan enforcement"""
        if not self.enabled:
            return await call_next(request)
            
        # Skip enforcement for health checks and auth endpoints
        if self._should_skip_enforcement(request):
            return await call_next(request)
            
        # Get user and plan information
        user_info = await self._get_user_info(request)
        if not user_info:
            # No user context - allow request to proceed (auth will handle)
            return await call_next(request)
            
        user_id, plan = user_info
        
        # Check feature access
        feature_check = self._check_feature_access(request, plan)
        if not feature_check[0]:
            return self._create_feature_blocked_response(feature_check[1])
            
        # Check quota limits
        quota_check = await self._check_quota_limits(request, user_id, plan)
        if not quota_check[0]:
            return self._create_quota_exceeded_response(quota_check[1])
            
        # Process request and track usage
        response = await call_next(request)
        
        # Track successful usage
        if response.status_code < 400:
            await self._track_usage(request, user_id)
            
        return response
    
    def _should_skip_enforcement(self, request: Request) -> bool:
        """Check if request should skip plan enforcement"""
        skip_paths = [
            '/health', '/docs', '/redoc', '/openapi.json',
            '/api/auth', '/api/register', '/api/login',
            '/api/observability', '/api/prometheus',
        ]
        
        path = request.url.path
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    async def _get_user_info(self, request: Request) -> Optional[Tuple[str, PlanTier]]:
        """Extract user and plan information from request"""
        try:
            # Get user from request state (set by auth middleware)
            user = getattr(request.state, 'current_user', None)
            if not user:
                return None
                
            user_id = str(user.id)
            
            # Get plan from user or organization
            plan_name = "free"  # Default
            if hasattr(user, 'subscription_plan'):
                plan_name = user.subscription_plan
            elif hasattr(user, 'organization') and user.organization:
                plan_name = getattr(user.organization, 'subscription_plan', 'free')
                
            # Convert to PlanTier enum
            try:
                plan = PlanTier(plan_name.lower())
            except ValueError:
                logger.warning(f"Unknown plan: {plan_name}, defaulting to FREE")
                plan = PlanTier.FREE
                
            return user_id, plan
            
        except Exception as e:
            logger.error(f"Error extracting user info: {e}")
            return None
    
    def _check_feature_access(self, request: Request, plan: PlanTier) -> Tuple[bool, Optional[str]]:
        """Check if user's plan has access to the requested feature"""
        path = request.url.path
        
        # Check if path requires specific feature
        for endpoint_pattern, feature in self.feature_endpoints.items():
            if path.startswith(endpoint_pattern):
                if not PlanLimits.has_feature(plan, feature):
                    return False, feature
                    
        return True, None
    
    async def _check_quota_limits(self, request: Request, user_id: str, plan: PlanTier) -> Tuple[bool, Optional[Dict]]:
        """Check if request would exceed quota limits"""
        path = request.url.path
        method = request.method
        
        # Check if endpoint has quota limits
        quota_type = None
        for endpoint_pattern, qt in self.endpoint_quotas.items():
            if path.startswith(endpoint_pattern):
                quota_type = qt
                break
                
        if not quota_type:
            # No quota limit for this endpoint
            return True, None
            
        # Check quota
        allowed, current_usage, limit = self.quota_manager.check_quota(user_id, plan, quota_type)
        
        if not allowed:
            return False, {
                'quota_type': quota_type.value,
                'current_usage': current_usage,
                'limit': limit,
                'plan': plan.value
            }
            
        return True, None
    
    async def _track_usage(self, request: Request, user_id: str):
        """Track successful API usage"""
        path = request.url.path
        
        # Always track API requests
        self.quota_manager.increment_usage(user_id, QuotaType.API_REQUESTS)
        
        # Track specific endpoint usage
        for endpoint_pattern, quota_type in self.endpoint_quotas.items():
            if path.startswith(endpoint_pattern):
                self.quota_manager.increment_usage(user_id, quota_type)
                break
    
    def _create_feature_blocked_response(self, feature: str) -> Response:
        """Create response for blocked feature access"""
        import json
        return Response(
            content=json.dumps({
                "error": "feature_not_available",
                "message": f"Feature '{feature}' is not available in your current plan",
                "code": "PLAN_FEATURE_BLOCKED"
            }),
            status_code=status.HTTP_403_FORBIDDEN,
            media_type="application/json"
        )
    
    def _create_quota_exceeded_response(self, quota_info: Dict) -> Response:
        """Create response for quota exceeded"""
        import json
        return Response(
            content=json.dumps({
                "error": "quota_exceeded",
                "message": f"Usage quota exceeded for {quota_info['quota_type']}",
                "details": quota_info,
                "code": "PLAN_QUOTA_EXCEEDED"
            }),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            media_type="application/json"
        )

class PlanManager:
    """Utility class for plan management operations"""
    
    def __init__(self):
        self.quota_manager = QuotaManager()
        
    def get_user_plan_info(self, user) -> Dict[str, Any]:
        """Get comprehensive plan information for a user"""
        plan_name = "free"
        if hasattr(user, 'subscription_plan'):
            plan_name = user.subscription_plan
        elif hasattr(user, 'organization') and user.organization:
            plan_name = getattr(user.organization, 'subscription_plan', 'free')
            
        try:
            plan = PlanTier(plan_name.lower())
        except ValueError:
            plan = PlanTier.FREE
            
        return {
            'plan': plan.value,
            'limits': PlanLimits.PLAN_LIMITS[plan],
            'features': PlanLimits.PLAN_FEATURES[plan],
        }
    
    def get_user_usage_summary(self, user_id: str, plan: PlanTier) -> Dict[str, Any]:
        """Get usage summary for a user"""
        usage_summary = {}
        
        for quota_type in QuotaType:
            current_usage = self.quota_manager.get_usage(user_id, quota_type)
            limit = PlanLimits.get_limit(plan, quota_type)
            
            usage_summary[quota_type.value] = {
                'current': current_usage,
                'limit': limit,
                'percentage': (current_usage / limit * 100) if limit > 0 else 0,
                'unlimited': limit == -1
            }
            
        return usage_summary
    
    def reset_user_quotas(self, user_id: str, quota_types: List[QuotaType] = None):
        """Reset quotas for a user (admin function)"""
        if not self.quota_manager.enabled:
            return
            
        if quota_types is None:
            quota_types = list(QuotaType)
            
        try:
            for quota_type in quota_types:
                daily_key = self.quota_manager.get_quota_key(user_id, quota_type, "daily")
                monthly_key = self.quota_manager.get_quota_key(user_id, quota_type, "monthly")
                total_key = self.quota_manager.get_quota_key(user_id, quota_type, "total")
                
                self.quota_manager.redis_client.delete(daily_key, monthly_key, total_key)
                
            logger.info(f"Reset quotas for user {user_id}: {[qt.value for qt in quota_types]}")
            
        except Exception as e:
            logger.error(f"Failed to reset quotas for user {user_id}: {e}")

def setup_plan_enforcement_middleware(app):
    """Setup plan enforcement middleware for the FastAPI app"""
    try:
        app.add_middleware(PlanEnforcementMiddleware)
        logger.info("Plan enforcement middleware configured successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup plan enforcement middleware: {e}")
        return False

# Global instances
plan_manager = PlanManager()

def get_plan_manager():
    """Get the global plan manager instance"""
    return plan_manager