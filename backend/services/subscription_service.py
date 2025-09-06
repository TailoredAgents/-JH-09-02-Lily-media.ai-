"""
Subscription tier enforcement service for multi-tenant SaaS
Handles plan-based feature gating and Stripe integration
"""
import logging
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.db.database import get_db
from backend.db.models import User
from backend.db.multi_tenant_models import Organization
from backend.core.config import get_settings

logger = logging.getLogger(__name__)

class SubscriptionTier(str, Enum):
    """Standardized subscription tiers"""
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class SubscriptionError(Exception):
    """Base exception for subscription operations"""
    pass

class InsufficientTierError(SubscriptionError):
    """User's tier is insufficient for requested feature"""
    pass

# Feature sets for each tier
TIER_FEATURES = {
    SubscriptionTier.BASIC: {
        "basic_posting", 
        "basic_scheduling", 
        "basic_analytics", 
        "basic_image_generation",  # Grok-2 only
        "social_accounts_limit_3",
        "posts_per_day_10",
        "research_basic"
    },
    SubscriptionTier.PREMIUM: {
        "basic_posting", 
        "basic_scheduling", 
        "basic_analytics",
        "advanced_scheduling",
        "premium_analytics",
        "premium_image_generation",  # Image1 model
        "basic_image_generation",   # Also has basic
        "autonomous_posting",
        "industry_research",
        "social_accounts_limit_10",
        "posts_per_day_50",
        "research_advanced"
    },
    SubscriptionTier.ENTERPRISE: {
        "basic_posting", 
        "basic_scheduling", 
        "basic_analytics",
        "advanced_scheduling",
        "premium_analytics",
        "enterprise_analytics",
        "premium_image_generation",  # Image1 model
        "basic_image_generation",   # Also has basic
        "enterprise_image_generation",  # Advanced image generation
        "autonomous_posting",
        "industry_research",
        "advanced_automation",
        "custom_branding",
        "priority_support",
        "social_accounts_unlimited",
        "posts_per_day_unlimited",
        "research_comprehensive",
        "team_collaboration",
        "advanced_rbac"
    }
}

# Tier limits for various features
TIER_LIMITS = {
    SubscriptionTier.BASIC: {
        "max_social_accounts": 3,
        "max_posts_per_day": 10,
        "max_teams": 1,
        "max_users": 1,
        "max_ai_requests_per_day": 20,
        "max_image_generations_per_day": 5,
        "research_queries_per_week": 5
    },
    SubscriptionTier.PREMIUM: {
        "max_social_accounts": 10,
        "max_posts_per_day": 50,
        "max_teams": 5,
        "max_users": 10,
        "max_ai_requests_per_day": 200,
        "max_image_generations_per_day": 50,
        "research_queries_per_week": 25
    },
    SubscriptionTier.ENTERPRISE: {
        "max_social_accounts": -1,  # unlimited
        "max_posts_per_day": -1,   # unlimited
        "max_teams": -1,           # unlimited
        "max_users": -1,           # unlimited
        "max_ai_requests_per_day": -1,
        "max_image_generations_per_day": -1,
        "research_queries_per_week": -1
    }
}

# Tier hierarchy for upgrades
TIER_HIERARCHY = {
    SubscriptionTier.BASIC: 1,
    SubscriptionTier.PREMIUM: 2,
    SubscriptionTier.ENTERPRISE: 3
}

class SubscriptionService:
    """
    Centralized subscription management and tier enforcement
    
    Features:
    - Standardized tier checking across user and organization models
    - Feature-based access control with granular permissions
    - Usage limit enforcement per tier
    - Stripe integration preparation
    - Multi-tenant tier resolution
    """
    
    def __init__(self, db: Session = None):
        """
        Initialize subscription service
        
        Args:
            db: Database session (optional, will create if not provided)
        """
        self.db = db or next(get_db())
        self.settings = get_settings()
    
    def normalize_tier(self, tier_value: str) -> SubscriptionTier:
        """
        Normalize various tier naming conventions to standard enum
        
        Args:
            tier_value: Tier string from User.tier or Organization.plan_type
            
        Returns:
            Standardized SubscriptionTier enum
        """
        if not tier_value:
            return SubscriptionTier.BASIC
            
        # Normalize the input
        tier_lower = tier_value.lower().strip()
        
        # Map legacy and inconsistent naming
        tier_mapping = {
            # User.tier variants
            "base": SubscriptionTier.BASIC,
            "basic": SubscriptionTier.BASIC,
            "pro": SubscriptionTier.PREMIUM,
            "premium": SubscriptionTier.PREMIUM,
            "enterprise": SubscriptionTier.ENTERPRISE,
            
            # Organization.plan_type variants
            "starter": SubscriptionTier.BASIC,
            "professional": SubscriptionTier.PREMIUM,
            
            # Legacy variants
            "free": SubscriptionTier.BASIC,
            "paid": SubscriptionTier.PREMIUM
        }
        
        return tier_mapping.get(tier_lower, SubscriptionTier.BASIC)
    
    def get_user_tier(self, user_id: int) -> SubscriptionTier:
        """
        Get effective tier for a user (considering both user and organization)
        
        Args:
            user_id: User ID
            
        Returns:
            Effective subscription tier (highest available)
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return SubscriptionTier.BASIC
            
            # Get user's individual tier
            user_tier = self.normalize_tier(user.tier)
            
            # Get organization tier (if user belongs to one)
            org_tier = SubscriptionTier.BASIC
            if user.default_organization_id:
                org = self.db.query(Organization).filter(
                    Organization.id == user.default_organization_id
                ).first()
                if org:
                    org_tier = self.normalize_tier(org.plan_type)
            
            # Return the highest tier available
            user_level = TIER_HIERARCHY[user_tier]
            org_level = TIER_HIERARCHY[org_tier]
            
            if user_level >= org_level:
                return user_tier
            else:
                return org_tier
                
        except Exception as e:
            logger.error(f"Failed to get user tier: {e}")
            return SubscriptionTier.BASIC
    
    def get_organization_tier(self, organization_id: str) -> SubscriptionTier:
        """
        Get organization's subscription tier
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Organization's subscription tier
        """
        try:
            org = self.db.query(Organization).filter(
                Organization.id == organization_id
            ).first()
            
            if not org:
                return SubscriptionTier.BASIC
                
            return self.normalize_tier(org.plan_type)
            
        except Exception as e:
            logger.error(f"Failed to get organization tier: {e}")
            return SubscriptionTier.BASIC
    
    def has_feature(self, user_id: int, feature: str, organization_id: str = None) -> bool:
        """
        Check if user has access to a specific feature
        
        Args:
            user_id: User ID
            feature: Feature identifier (e.g., "premium_image_generation")
            organization_id: Optional organization context
            
        Returns:
            True if user has access to the feature
        """
        try:
            if organization_id:
                tier = self.get_organization_tier(organization_id)
            else:
                tier = self.get_user_tier(user_id)
            
            return feature in TIER_FEATURES.get(tier, set())
            
        except Exception as e:
            logger.error(f"Feature check failed: {e}")
            return False
    
    def check_usage_limit(
        self, 
        user_id: int, 
        limit_type: str, 
        current_usage: int,
        organization_id: str = None
    ) -> bool:
        """
        Check if user is within usage limits for their tier
        
        Args:
            user_id: User ID
            limit_type: Type of limit (e.g., "max_posts_per_day")
            current_usage: Current usage count
            organization_id: Optional organization context
            
        Returns:
            True if within limits, False if exceeded
        """
        try:
            if organization_id:
                tier = self.get_organization_tier(organization_id)
            else:
                tier = self.get_user_tier(user_id)
            
            tier_limits = TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.BASIC])
            limit = tier_limits.get(limit_type, 0)
            
            # -1 means unlimited
            if limit == -1:
                return True
                
            return current_usage < limit
            
        except Exception as e:
            logger.error(f"Usage limit check failed: {e}")
            return False
    
    def get_tier_limits(self, user_id: int, organization_id: str = None) -> Dict[str, int]:
        """
        Get all usage limits for user's tier
        
        Args:
            user_id: User ID
            organization_id: Optional organization context
            
        Returns:
            Dictionary of limits for the user's tier
        """
        try:
            if organization_id:
                tier = self.get_organization_tier(organization_id)
            else:
                tier = self.get_user_tier(user_id)
            
            return TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.BASIC])
            
        except Exception as e:
            logger.error(f"Failed to get tier limits: {e}")
            return TIER_LIMITS[SubscriptionTier.BASIC]
    
    def get_tier_features(self, user_id: int, organization_id: str = None) -> Set[str]:
        """
        Get all available features for user's tier
        
        Args:
            user_id: User ID
            organization_id: Optional organization context
            
        Returns:
            Set of available features
        """
        try:
            if organization_id:
                tier = self.get_organization_tier(organization_id)
            else:
                tier = self.get_user_tier(user_id)
            
            return TIER_FEATURES.get(tier, TIER_FEATURES[SubscriptionTier.BASIC])
            
        except Exception as e:
            logger.error(f"Failed to get tier features: {e}")
            return TIER_FEATURES[SubscriptionTier.BASIC]
    
    def upgrade_user_tier(self, user_id: int, new_tier: SubscriptionTier) -> bool:
        """
        Upgrade user to a new subscription tier
        
        Args:
            user_id: User ID
            new_tier: Target subscription tier
            
        Returns:
            True if upgrade successful
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Update user tier
            user.tier = new_tier.value
            user.subscription_status = "active"
            user.updated_at = datetime.now(timezone.utc)
            
            # Update organization if user owns one
            if user.default_organization_id:
                org = self.db.query(Organization).filter(
                    Organization.id == user.default_organization_id,
                    Organization.owner_id == user_id
                ).first()
                
                if org:
                    # Map tiers to organization plan types
                    org_plan_mapping = {
                        SubscriptionTier.BASIC: "starter",
                        SubscriptionTier.PREMIUM: "professional", 
                        SubscriptionTier.ENTERPRISE: "enterprise"
                    }
                    
                    org.plan_type = org_plan_mapping[new_tier]
                    org.updated_at = datetime.now(timezone.utc)
                    
                    # Update organization limits
                    limits = TIER_LIMITS[new_tier]
                    org.max_users = limits["max_users"] if limits["max_users"] != -1 else 999999
                    org.max_teams = limits["max_teams"] if limits["max_teams"] != -1 else 999999
                    org.max_social_accounts = limits["max_social_accounts"] if limits["max_social_accounts"] != -1 else 999999
                    
                    # Update enabled features
                    org.features_enabled = list(TIER_FEATURES[new_tier])
            
            self.db.commit()
            logger.info(f"Upgraded user {user_id} to tier {new_tier.value}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to upgrade user tier: {e}")
            return False
    
    def require_feature(self, feature: str):
        """
        Decorator to require specific feature access
        
        Usage:
            @subscription_service.require_feature("premium_image_generation")
            async def generate_premium_image(...):
                ...
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # This will be implemented with FastAPI dependencies
                # For now, return the function as-is
                return func(*args, **kwargs)
            return wrapper
        return decorator


# Singleton service instance
_subscription_service = None

def get_subscription_service(db: Session = None) -> SubscriptionService:
    """Get singleton subscription service instance"""
    global _subscription_service
    if _subscription_service is None or db is not None:
        _subscription_service = SubscriptionService(db)
    return _subscription_service