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
from prometheus_client import Counter, Histogram, CollectorRegistry, REGISTRY

logger = logging.getLogger(__name__)

# Plan limit metrics for observability - Check if already registered
try:
    PLAN_LIMIT_VIOLATIONS = Counter(
        'plan_enforcement_violations_total',  # Changed name to avoid collision
        'Total plan enforcement violations by type and plan',
        ['violation_type', 'plan_tier', 'quota_type']
    )
except ValueError:
    # Metric already exists, get it from registry
    for collector in REGISTRY._collector_to_names:
        if hasattr(collector, '_name') and 'plan_enforcement_violations_total' in collector._name:
            PLAN_LIMIT_VIOLATIONS = collector
            break

try:
    PLAN_UPGRADE_SUGGESTIONS = Counter(
        'plan_enforcement_upgrade_suggestions_total',  # Changed name to avoid collision
        'Total plan upgrade suggestions shown to users', 
        ['current_plan', 'suggested_plan', 'trigger_reason']
    )
except ValueError:
    # Metric already exists, get it from registry
    for collector in REGISTRY._collector_to_names:
        if hasattr(collector, '_name') and 'plan_enforcement_upgrade_suggestions_total' in collector._name:
            PLAN_UPGRADE_SUGGESTIONS = collector
            break

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


class UpgradeSuggestionEngine:
    """Generates intelligent upgrade suggestions when users hit plan limits"""
    
    PLAN_UPGRADE_PATHS = {
        PlanTier.FREE: [PlanTier.BASIC, PlanTier.PROFESSIONAL],
        PlanTier.BASIC: [PlanTier.PROFESSIONAL, PlanTier.ENTERPRISE],
        PlanTier.PROFESSIONAL: [PlanTier.ENTERPRISE],
        PlanTier.ENTERPRISE: []  # No upgrade path
    }
    
    PLAN_PRICING = {
        PlanTier.FREE: {"monthly": 0, "annual": 0},
        PlanTier.BASIC: {"monthly": 19, "annual": 190},
        PlanTier.PROFESSIONAL: {"monthly": 49, "annual": 490},
        PlanTier.ENTERPRISE: {"monthly": 199, "annual": 1990}
    }
    
    QUOTA_UPGRADE_BENEFITS = {
        QuotaType.CONTENT_GENERATIONS: {
            "title": "AI Content Generation",
            "description": "Create more AI-powered social media content",
            "icon": "✍️"
        },
        QuotaType.IMAGE_GENERATIONS: {
            "title": "AI Image Generation", 
            "description": "Generate more stunning visual content",
            "icon": "🎨"
        },
        QuotaType.OAUTH_CONNECTIONS: {
            "title": "Social Platform Connections",
            "description": "Connect more social media accounts",
            "icon": "🔗"
        },
        QuotaType.SOCIAL_POSTS: {
            "title": "Social Media Posts",
            "description": "Publish more content across platforms",
            "icon": "📱"
        },
        QuotaType.AI_SUGGESTIONS: {
            "title": "AI-Powered Suggestions",
            "description": "Get more intelligent content recommendations",
            "icon": "💡"
        }
    }
    
    @classmethod
    def generate_quota_upgrade_suggestion(cls, current_plan: PlanTier, quota_type: QuotaType, current_usage: int, limit: int) -> Dict[str, Any]:
        """Generate upgrade suggestion for quota exceeded scenario"""
        
        # Get upgrade paths
        upgrade_options = cls.PLAN_UPGRADE_PATHS.get(current_plan, [])
        if not upgrade_options:
            return cls._create_enterprise_contact_suggestion(current_plan, quota_type)
        
        # Find the best upgrade option (smallest plan that meets needs)
        recommended_plan = None
        for plan_option in upgrade_options:
            new_limit = PlanLimits.get_limit(plan_option, quota_type)
            if new_limit == -1 or new_limit > current_usage * 2:  # 2x buffer
                recommended_plan = plan_option
                break
        
        if not recommended_plan:
            recommended_plan = upgrade_options[-1]  # Highest available plan
            
        # Get quota benefits info
        quota_info = cls.QUOTA_UPGRADE_BENEFITS.get(quota_type, {
            "title": quota_type.value.replace('_', ' ').title(),
            "description": f"Increase your {quota_type.value.replace('_', ' ')} limits",
            "icon": "📈"
        })
        
        # Calculate usage patterns
        usage_percentage = (current_usage / limit * 100) if limit > 0 else 100
        new_limit = PlanLimits.get_limit(recommended_plan, quota_type)
        
        suggestion = {
            "trigger_reason": "quota_exceeded",
            "current_plan": current_plan.value,
            "recommended_plan": recommended_plan.value,
            "quota_exceeded": {
                "type": quota_type.value,
                "current_usage": current_usage,
                "current_limit": limit,
                "usage_percentage": round(usage_percentage, 1),
                "quota_info": quota_info
            },
            "upgrade_benefits": {
                "new_limit": new_limit,
                "limit_increase": "Unlimited" if new_limit == -1 else f"{new_limit - limit:,} more",
                "additional_features": cls._get_additional_features(current_plan, recommended_plan)
            },
            "pricing": cls.PLAN_PRICING[recommended_plan],
            "urgency": "high" if usage_percentage > 95 else "medium",
            "message": cls._generate_upgrade_message(current_plan, recommended_plan, quota_info, usage_percentage),
            "cta": {
                "primary": f"Upgrade to {recommended_plan.value.title()}",
                "secondary": "View All Plans"
            }
        }
        
        # Track the suggestion
        PLAN_UPGRADE_SUGGESTIONS.labels(
            current_plan=current_plan.value,
            suggested_plan=recommended_plan.value,
            trigger_reason="quota_exceeded"
        ).inc()
        
        return suggestion
    
    @classmethod
    def generate_feature_upgrade_suggestion(cls, current_plan: PlanTier, blocked_feature: str) -> Dict[str, Any]:
        """Generate upgrade suggestion for blocked feature access"""
        
        # Find the minimum plan that has this feature
        recommended_plan = None
        for plan in [PlanTier.BASIC, PlanTier.PROFESSIONAL, PlanTier.ENTERPRISE]:
            if PlanLimits.has_feature(plan, blocked_feature):
                recommended_plan = plan
                break
        
        if not recommended_plan:
            return cls._create_enterprise_contact_suggestion(current_plan, None, blocked_feature)
        
        feature_info = {
            "advanced_analytics": {"title": "Advanced Analytics", "icon": "📊", "description": "Deep insights into your content performance"},
            "custom_workflows": {"title": "Custom Workflows", "icon": "⚙️", "description": "Build automated content creation workflows"},
            "bulk_operations": {"title": "Bulk Operations", "icon": "⚡", "description": "Manage multiple posts and campaigns at once"},
            "advanced_ai_features": {"title": "Advanced AI Features", "icon": "🧠", "description": "Access cutting-edge AI content generation"},
            "white_label": {"title": "White Label", "icon": "🏷️", "description": "Brand the platform as your own"},
            "sso": {"title": "Single Sign-On", "icon": "🔐", "description": "Enterprise-grade authentication"}
        }.get(blocked_feature, {"title": blocked_feature.replace('_', ' ').title(), "icon": "🔒", "description": f"Access to {blocked_feature.replace('_', ' ')}"})
        
        suggestion = {
            "trigger_reason": "feature_blocked",
            "current_plan": current_plan.value,
            "recommended_plan": recommended_plan.value,
            "blocked_feature": {
                "name": blocked_feature,
                "info": feature_info
            },
            "upgrade_benefits": {
                "primary_feature": feature_info,
                "additional_features": cls._get_additional_features(current_plan, recommended_plan)
            },
            "pricing": cls.PLAN_PRICING[recommended_plan],
            "urgency": "medium",
            "message": cls._generate_feature_upgrade_message(current_plan, recommended_plan, feature_info),
            "cta": {
                "primary": f"Upgrade to {recommended_plan.value.title()}",
                "secondary": "Compare Plans"
            }
        }
        
        # Track the suggestion
        PLAN_UPGRADE_SUGGESTIONS.labels(
            current_plan=current_plan.value,
            suggested_plan=recommended_plan.value,
            trigger_reason="feature_blocked"
        ).inc()
        
        return suggestion
    
    @classmethod
    def _get_additional_features(cls, current_plan: PlanTier, target_plan: PlanTier) -> List[Dict[str, str]]:
        """Get additional features gained by upgrading"""
        current_features = set(
            feature for feature, enabled in PlanLimits.PLAN_FEATURES[current_plan].items() if enabled
        )
        target_features = set(
            feature for feature, enabled in PlanLimits.PLAN_FEATURES[target_plan].items() if enabled
        )
        
        new_features = target_features - current_features
        
        feature_descriptions = {
            "multi_platform_posting": "Post to multiple social platforms",
            "advanced_analytics": "Advanced performance insights",
            "custom_workflows": "Custom automation workflows", 
            "api_access": "Full API access",
            "priority_support": "Priority customer support",
            "white_label": "White-label platform branding",
            "sso": "Single sign-on authentication",
            "advanced_ai_features": "Advanced AI content generation",
            "bulk_operations": "Bulk content operations"
        }
        
        return [
            {
                "name": feature,
                "title": feature_descriptions.get(feature, feature.replace('_', ' ').title()),
                "icon": "✨"
            }
            for feature in sorted(new_features) if feature in feature_descriptions
        ][:5]  # Limit to top 5 features
    
    @classmethod
    def _generate_upgrade_message(cls, current_plan: PlanTier, recommended_plan: PlanTier, quota_info: Dict, usage_percentage: float) -> str:
        """Generate personalized upgrade message for quota scenarios"""
        quota_title = quota_info.get("title", "Usage")
        
        if usage_percentage >= 100:
            return f"You've reached your {quota_title.lower()} limit on the {current_plan.value.title()} plan. Upgrade to {recommended_plan.value.title()} to continue growing your social media presence!"
        elif usage_percentage >= 90:
            return f"You're using {usage_percentage:.0f}% of your {quota_title.lower()} quota. Upgrade to {recommended_plan.value.title()} to avoid hitting limits."
        else:
            return f"Unlock more {quota_title.lower()} with {recommended_plan.value.title()} plan - perfect for scaling your content strategy!"
    
    @classmethod
    def _generate_feature_upgrade_message(cls, current_plan: PlanTier, recommended_plan: PlanTier, feature_info: Dict) -> str:
        """Generate personalized upgrade message for feature scenarios"""
        feature_title = feature_info.get("title", "Feature")
        return f"{feature_title} is available starting with the {recommended_plan.value.title()} plan. Upgrade now to unlock advanced capabilities!"
    
    @classmethod
    def _create_enterprise_contact_suggestion(cls, current_plan: PlanTier, quota_type: Optional[QuotaType] = None, feature: Optional[str] = None) -> Dict[str, Any]:
        """Create enterprise contact suggestion for edge cases"""
        return {
            "trigger_reason": "enterprise_needed",
            "current_plan": current_plan.value,
            "recommended_plan": "enterprise",
            "message": "For higher limits or custom requirements, let's discuss an Enterprise solution tailored to your needs.",
            "cta": {
                "primary": "Contact Sales",
                "secondary": "View Enterprise Features"
            },
            "contact_info": {
                "email": "enterprise@lilymedia.ai",
                "calendar_link": "https://calendly.com/lilymedia-enterprise",
                "phone": "+1-800-LILY-AI"
            }
        }

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
            return self._create_feature_blocked_response(feature_check[1], user_id, plan, request)
            
        # Check quota limits
        quota_check = await self._check_quota_limits(request, user_id, plan)
        if not quota_check[0]:
            return self._create_quota_exceeded_response(quota_check[1], user_id, plan, request)
            
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
    
    def _create_feature_blocked_response(self, feature: str, user_id: str, plan: PlanTier, request: Request) -> Response:
        """Create response for blocked feature access with logging and upgrade suggestions"""
        import json
        
        # Generate upgrade suggestion
        upgrade_suggestion = UpgradeSuggestionEngine.generate_feature_upgrade_suggestion(plan, feature)
        
        # Log the plan violation with structured logging
        logger.warning(
            "Plan feature access blocked",
            extra={
                "user_id": user_id,
                "current_plan": plan.value,
                "blocked_feature": feature,
                "endpoint": request.url.path,
                "method": request.method,
                "suggested_plan": upgrade_suggestion.get("recommended_plan"),
                "event_type": "plan_feature_blocked",
                "correlation_id": getattr(request.state, "correlation_id", None)
            }
        )
        
        # Track metrics
        PLAN_LIMIT_VIOLATIONS.labels(
            violation_type="feature_blocked",
            plan_tier=plan.value,
            quota_type="feature_access"
        ).inc()
        
        response_data = {
            "error": "feature_not_available",
            "message": f"Feature '{feature}' is not available in your current plan",
            "code": "PLAN_FEATURE_BLOCKED",
            "current_plan": plan.value,
            "blocked_feature": feature,
            "upgrade_suggestion": upgrade_suggestion,
            "support": {
                "help_center": "https://help.lilymedia.ai/plan-features",
                "contact_support": "support@lilymedia.ai"
            }
        }
        
        return Response(
            content=json.dumps(response_data),
            status_code=status.HTTP_403_FORBIDDEN,
            media_type="application/json"
        )
    
    def _create_quota_exceeded_response(self, quota_info: Dict, user_id: str, plan: PlanTier, request: Request) -> Response:
        """Create response for quota exceeded with logging and upgrade suggestions"""
        import json
        
        # Generate upgrade suggestion
        quota_type = QuotaType(quota_info['quota_type'])
        upgrade_suggestion = UpgradeSuggestionEngine.generate_quota_upgrade_suggestion(
            plan, quota_type, quota_info['current_usage'], quota_info['limit']
        )
        
        # Log the quota violation with structured logging
        logger.warning(
            "Plan quota exceeded",
            extra={
                "user_id": user_id,
                "current_plan": plan.value,
                "quota_type": quota_info['quota_type'],
                "current_usage": quota_info['current_usage'],
                "limit": quota_info['limit'],
                "usage_percentage": round((quota_info['current_usage'] / quota_info['limit']) * 100, 1) if quota_info['limit'] > 0 else 100,
                "endpoint": request.url.path,
                "method": request.method,
                "suggested_plan": upgrade_suggestion.get("recommended_plan"),
                "event_type": "plan_quota_exceeded",
                "correlation_id": getattr(request.state, "correlation_id", None)
            }
        )
        
        # Track metrics
        PLAN_LIMIT_VIOLATIONS.labels(
            violation_type="quota_exceeded",
            plan_tier=plan.value,
            quota_type=quota_info['quota_type']
        ).inc()
        
        response_data = {
            "error": "quota_exceeded",
            "message": f"Usage quota exceeded for {quota_info['quota_type']}",
            "code": "PLAN_QUOTA_EXCEEDED",
            "current_plan": plan.value,
            "quota_details": quota_info,
            "upgrade_suggestion": upgrade_suggestion,
            "retry_after": 3600,  # Reset in 1 hour for daily quotas
            "support": {
                "help_center": "https://help.lilymedia.ai/plan-limits",
                "billing_portal": "https://app.lilymedia.ai/billing",
                "contact_support": "support@lilymedia.ai"
            }
        }
        
        return Response(
            content=json.dumps(response_data),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            media_type="application/json",
            headers={"Retry-After": "3600"}
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
    
    def get_proactive_upgrade_suggestions(self, user_id: str, plan: PlanTier, usage_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """
        Get proactive upgrade suggestions when users approach limits
        
        Args:
            user_id: User ID to check
            plan: Current user plan 
            usage_threshold: Threshold (0.0-1.0) to trigger suggestions
            
        Returns:
            List of upgrade suggestions for quotas near limits
        """
        suggestions = []
        
        if plan == PlanTier.ENTERPRISE:
            return suggestions  # No upgrades available
        
        try:
            for quota_type in QuotaType:
                current_usage = self.quota_manager.get_usage(user_id, quota_type)
                limit = PlanLimits.get_limit(plan, quota_type)
                
                # Skip unlimited quotas
                if limit == -1 or limit == 0:
                    continue
                
                usage_percentage = current_usage / limit
                
                # Generate suggestion if approaching limit
                if usage_percentage >= usage_threshold:
                    suggestion = UpgradeSuggestionEngine.generate_quota_upgrade_suggestion(
                        plan, quota_type, current_usage, limit
                    )
                    suggestion["trigger_reason"] = "approaching_limit"
                    suggestion["usage_percentage"] = round(usage_percentage * 100, 1)
                    
                    suggestions.append(suggestion)
                    
                    # Log proactive suggestion
                    logger.info(
                        "Generated proactive upgrade suggestion",
                        extra={
                            "user_id": user_id,
                            "current_plan": plan.value,
                            "quota_type": quota_type.value,
                            "usage_percentage": round(usage_percentage * 100, 1),
                            "suggested_plan": suggestion.get("recommended_plan"),
                            "event_type": "proactive_upgrade_suggestion"
                        }
                    )
        
        except Exception as e:
            logger.error(f"Failed to generate proactive upgrade suggestions for user {user_id}: {e}")
        
        return suggestions
    
    def log_plan_usage_warning(self, user_id: str, plan: PlanTier, quota_type: QuotaType, usage_percentage: float):
        """Log structured warning when users approach plan limits"""
        logger.warning(
            "User approaching plan limit",
            extra={
                "user_id": user_id,
                "current_plan": plan.value,
                "quota_type": quota_type.value,
                "usage_percentage": round(usage_percentage, 1),
                "event_type": "approaching_plan_limit",
                "threshold_warning": True
            }
        )
        
        # Track in metrics
        PLAN_LIMIT_VIOLATIONS.labels(
            violation_type="approaching_limit",
            plan_tier=plan.value,
            quota_type=quota_type.value
        ).inc()

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