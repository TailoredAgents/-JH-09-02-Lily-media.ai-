"""
Plan Service - Centralized business logic for subscription plans and feature gating
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select
import logging
from datetime import datetime, timezone, timedelta

from backend.db.models import Plan, User
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PlanCapability:
    """Plan capability checker with lazy loading"""
    
    def __init__(self, user_id: int, db: Session):
        self.user_id = user_id
        self.db = db
        self._user: Optional[User] = None
        self._plan: Optional[Plan] = None
        self._loaded = False
    
    def _load_user_plan(self) -> None:
        """Load user and plan data if not already loaded"""
        if not self._loaded:
            # Get user with plan relationship
            result = self.db.execute(
                select(User).where(User.id == self.user_id)
            )
            self._user = result.scalar_one_or_none()
            
            if self._user and self._user.plan_id:
                plan_result = self.db.execute(
                    select(Plan).where(Plan.id == self._user.plan_id)
                )
                self._plan = plan_result.scalar_one_or_none()
            
            self._loaded = True
    
    @property
    def user(self) -> Optional[User]:
        """Get user instance"""
        self._load_user_plan()
        return self._user
    
    @property 
    def plan(self) -> Optional[Plan]:
        """Get plan instance"""
        self._load_user_plan()
        return self._plan
    
    def has_plan(self) -> bool:
        """Check if user has an active plan"""
        return self.plan is not None and self.plan.is_active
    
    def get_plan_name(self) -> str:
        """Get plan name or 'free' if no plan"""
        return self.plan.name if self.plan else "free"
    
    def can_connect_social_accounts(self, current_count: int = 0) -> bool:
        """Check if user can connect more social accounts"""
        if not self.has_plan():
            return current_count < 1  # Free users get 1 connection
        return current_count < self.plan.max_social_profiles
    
    def can_create_posts_today(self, posts_today: int = 0) -> bool:
        """Check if user can create more posts today"""
        if not self.has_plan():
            return posts_today < 3  # Free users get 3 posts per day
        return posts_today < self.plan.max_posts_per_day
    
    def can_create_posts_this_week(self, posts_this_week: int = 0) -> bool:
        """Check if user can create more posts this week"""
        if not self.has_plan():
            return posts_this_week < 10  # Free users get 10 posts per week
        return posts_this_week < self.plan.max_posts_per_week
    
    def can_generate_images(self, images_this_month: int = 0) -> bool:
        """Check if user can generate more images this month"""
        if not self.has_plan():
            return images_this_month < 5  # Free users get 5 images per month
        limit = self.plan.image_generation_limit or 0
        return images_this_month < limit
    
    def has_full_ai_access(self) -> bool:
        """Check if user has full AI model access"""
        return self.plan.full_ai if self.plan else False
    
    def has_premium_ai_models(self) -> bool:
        """Check if user can access premium AI models"""
        return self.plan.premium_ai_models if self.plan else False
    
    def has_enhanced_autopilot(self) -> bool:
        """Check if user has enhanced autopilot features"""
        return self.plan.enhanced_autopilot if self.plan else False
    
    def can_use_ai_inbox(self) -> bool:
        """Check if user can use AI inbox features"""
        return self.plan.ai_inbox if self.plan else False
    
    def has_crm_integration(self) -> bool:
        """Check if user has CRM integration access"""
        return self.plan.crm_integration if self.plan else False
    
    def has_advanced_analytics(self) -> bool:
        """Check if user has advanced analytics"""
        return self.plan.advanced_analytics if self.plan else False
    
    def has_predictive_analytics(self) -> bool:
        """Check if user has predictive analytics"""
        return self.plan.predictive_analytics if self.plan else False
    
    def has_white_label(self) -> bool:
        """Check if user has white label features"""
        return self.plan.white_label if self.plan else False
    
    def get_autopilot_posts_per_day(self) -> int:
        """Get daily autopilot post limit"""
        if not self.has_plan():
            return 0  # Free users don't get autopilot
        return self.plan.autopilot_posts_per_day or 0
    
    def has_autopilot_research(self) -> bool:
        """Check if user has autopilot research enabled"""
        return self.plan.autopilot_research_enabled if self.plan else False
    
    def has_autopilot_ad_campaigns(self) -> bool:
        """Check if user has autopilot ad campaigns"""
        return self.plan.autopilot_ad_campaigns if self.plan else False
    
    def get_max_users(self) -> int:
        """Get maximum users allowed in organization"""
        if not self.has_plan():
            return 1  # Free users get 1 user
        return self.plan.max_users or 1
    
    def get_max_workspaces(self) -> int:
        """Get maximum workspaces allowed"""
        if not self.has_plan():
            return 1  # Free users get 1 workspace
        return self.plan.max_workspaces or 1
    
    def get_feature_list(self) -> Dict[str, Any]:
        """Get all plan features as dictionary"""
        if not self.has_plan():
            return {
                "plan_name": "free",
                "max_social_profiles": 1,
                "max_posts_per_day": 3,
                "max_posts_per_week": 10,
                "image_generation_limit": 5,
                "full_ai": False,
                "premium_ai_models": False,
                "enhanced_autopilot": False,
                "ai_inbox": False,
                "crm_integration": False,
                "advanced_analytics": False,
                "predictive_analytics": False,
                "white_label": False,
                "autopilot_posts_per_day": 0,
                "autopilot_research_enabled": False,
                "autopilot_ad_campaigns": False,
                "max_users": 1,
                "max_workspaces": 1
            }
        
        return {
            "plan_name": self.plan.name,
            "display_name": self.plan.display_name,
            "max_social_profiles": self.plan.max_social_profiles,
            "max_posts_per_day": self.plan.max_posts_per_day,
            "max_posts_per_week": self.plan.max_posts_per_week,
            "image_generation_limit": self.plan.image_generation_limit,
            "full_ai": self.plan.full_ai,
            "premium_ai_models": self.plan.premium_ai_models,
            "enhanced_autopilot": self.plan.enhanced_autopilot,
            "ai_inbox": self.plan.ai_inbox,
            "crm_integration": self.plan.crm_integration,
            "advanced_analytics": self.plan.advanced_analytics,
            "predictive_analytics": self.plan.predictive_analytics,
            "white_label": self.plan.white_label,
            "autopilot_posts_per_day": self.plan.autopilot_posts_per_day,
            "autopilot_research_enabled": self.plan.autopilot_research_enabled,
            "autopilot_ad_campaigns": self.plan.autopilot_ad_campaigns,
            "max_users": self.plan.max_users,
            "max_workspaces": self.plan.max_workspaces,
            "features": self.plan.features or {}
        }


class PlanService:
    """Service for plan management and business logic"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_capabilities(self, user_id: int) -> PlanCapability:
        """Get plan capabilities for a user"""
        return PlanCapability(user_id, self.db)
    
    def get_all_plans(self, active_only: bool = True) -> List[Plan]:
        """Get all available plans"""
        query = select(Plan)
        if active_only:
            query = query.where(Plan.is_active == True)
        query = query.order_by(Plan.sort_order)
        
        result = self.db.execute(query)
        return result.scalars().all()
    
    def get_plan_by_name(self, name: str) -> Optional[Plan]:
        """Get plan by name"""
        result = self.db.execute(
            select(Plan).where(Plan.name == name)
        )
        return result.scalar_one_or_none()
    
    def get_plan_by_id(self, plan_id: int) -> Optional[Plan]:
        """Get plan by ID"""
        result = self.db.execute(
            select(Plan).where(Plan.id == plan_id)
        )
        return result.scalar_one_or_none()
    
    def assign_plan_to_user(self, user_id: int, plan_name: str) -> bool:
        """Assign a plan to a user"""
        try:
            # Get user
            user_result = self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User {user_id} not found")
                return False
            
            # Get plan
            plan = self.get_plan_by_name(plan_name)
            if not plan:
                logger.error(f"Plan '{plan_name}' not found")
                return False
            
            # Assign plan
            user.plan_id = plan.id
            self.db.commit()
            
            logger.info(f"Assigned plan '{plan_name}' to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning plan to user: {e}")
            self.db.rollback()
            return False
    
    def upgrade_user_plan(self, user_id: int, new_plan_name: str) -> bool:
        """Upgrade user to a new plan"""
        capabilities = self.get_user_capabilities(user_id)
        current_plan = capabilities.get_plan_name()
        
        # Check if it's actually an upgrade
        plan_hierarchy = {"free": 0, "starter": 1, "pro": 2, "enterprise": 3}
        current_level = plan_hierarchy.get(current_plan, 0)
        new_level = plan_hierarchy.get(new_plan_name, 0)
        
        if new_level <= current_level:
            logger.warning(f"Not an upgrade: {current_plan} -> {new_plan_name}")
            return False
        
        return self.assign_plan_to_user(user_id, new_plan_name)
    
    def get_plan_comparison(self) -> List[Dict[str, Any]]:
        """Get plan comparison data for frontend"""
        plans = self.get_all_plans()
        comparison = []
        
        for plan in plans:
            comparison.append({
                "name": plan.name,
                "display_name": plan.display_name,
                "description": plan.description,
                "monthly_price": float(plan.monthly_price),
                "annual_price": float(plan.annual_price) if plan.annual_price else None,
                "trial_days": plan.trial_days,
                "is_popular": plan.is_popular,
                "features": {
                    "max_social_profiles": plan.max_social_profiles,
                    "max_posts_per_day": plan.max_posts_per_day,
                    "max_posts_per_week": plan.max_posts_per_week,
                    "max_users": plan.max_users,
                    "max_workspaces": plan.max_workspaces,
                    "image_generation_limit": plan.image_generation_limit,
                    "autopilot_posts_per_day": plan.autopilot_posts_per_day,
                    "full_ai": plan.full_ai,
                    "premium_ai_models": plan.premium_ai_models,
                    "enhanced_autopilot": plan.enhanced_autopilot,
                    "ai_inbox": plan.ai_inbox,
                    "crm_integration": plan.crm_integration,
                    "advanced_analytics": plan.advanced_analytics,
                    "predictive_analytics": plan.predictive_analytics,
                    "white_label": plan.white_label,
                    "autopilot_research_enabled": plan.autopilot_research_enabled,
                    "autopilot_ad_campaigns": plan.autopilot_ad_campaigns
                },
                "custom_features": plan.features or {}
            })
        
        return comparison
    
    def check_trial_eligibility(self, user_id: int) -> bool:
        """Check if user is eligible for trial"""
        capabilities = self.get_user_capabilities(user_id)
        user = capabilities.user
        
        if not user:
            return False
        
        # User is eligible if they don't have a plan or are on free
        current_plan = capabilities.get_plan_name()
        return current_plan == "free"
    
    def start_trial(self, user_id: int, plan_name: str) -> bool:
        """Start trial for user"""
        try:
            if not self.check_trial_eligibility(user_id):
                logger.warning(f"User {user_id} not eligible for trial")
                return False
            
            plan = self.get_plan_by_name(plan_name)
            if not plan or not plan.trial_days:
                logger.error(f"Plan '{plan_name}' doesn't offer trials")
                return False
            
            # Get user
            user_result = self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return False
            
            # Set trial
            user.plan_id = plan.id
            user.subscription_status = "trial"
            user.subscription_end_date = datetime.now(timezone.utc) + timedelta(days=plan.trial_days)
            
            self.db.commit()
            
            logger.info(f"Started {plan.trial_days}-day trial of '{plan_name}' for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting trial: {e}")
            self.db.rollback()
            return False