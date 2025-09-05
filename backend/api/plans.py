"""
Plans API endpoints - Plan management and feature access
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from backend.db.database import get_db
from backend.auth.dependencies import get_current_user
from backend.db.models import User
from backend.services.plan_service import PlanService
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plans", tags=["plans"])


# Pydantic models for request/response
class PlanAssignmentRequest(BaseModel):
    plan_name: str


class TrialStartRequest(BaseModel):
    plan_name: str


class PlanFeatureResponse(BaseModel):
    plan_name: str
    display_name: str = None
    max_social_profiles: int
    max_posts_per_day: int
    max_posts_per_week: int
    image_generation_limit: int = None
    full_ai: bool = False
    premium_ai_models: bool = False
    enhanced_autopilot: bool = False
    ai_inbox: bool = False
    crm_integration: bool = False
    advanced_analytics: bool = False
    predictive_analytics: bool = False
    white_label: bool = False
    autopilot_posts_per_day: int = 0
    autopilot_research_enabled: bool = False
    autopilot_ad_campaigns: bool = False
    max_users: int = 1
    max_workspaces: int = 1
    features: Dict[str, Any] = {}


@router.get("/available", response_model=List[Dict[str, Any]])
def get_available_plans(db: Session = Depends(get_db)):
    """Get all available subscription plans"""
    try:
        plan_service = PlanService(db)
        plans = plan_service.get_plan_comparison()
        return plans
        
    except Exception as e:
        logger.error(f"Error fetching available plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch available plans"
        )


@router.get("/my-plan", response_model=PlanFeatureResponse)
def get_my_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's plan and capabilities"""
    try:
        plan_service = PlanService(db)
        capabilities = plan_service.get_user_capabilities(current_user.id)
        features = capabilities.get_feature_list()
        
        return PlanFeatureResponse(**features)
        
    except Exception as e:
        logger.error(f"Error fetching user plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user plan"
        )


@router.post("/assign")
def assign_plan(
    request: PlanAssignmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign a plan to current user (admin/testing endpoint)"""
    try:
        plan_service = PlanService(db)
        success = plan_service.assign_plan_to_user(current_user.id, request.plan_name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to assign plan '{request.plan_name}'"
            )
        
        return {"message": f"Successfully assigned plan '{request.plan_name}'"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign plan"
        )


@router.post("/upgrade")
def upgrade_plan(
    request: PlanAssignmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upgrade user to a higher tier plan"""
    try:
        plan_service = PlanService(db)
        success = plan_service.upgrade_user_plan(current_user.id, request.plan_name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to upgrade to plan '{request.plan_name}' - not a valid upgrade"
            )
        
        return {"message": f"Successfully upgraded to plan '{request.plan_name}'"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error upgrading plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upgrade plan"
        )


@router.post("/start-trial")
def start_trial(
    request: TrialStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a trial for the specified plan"""
    try:
        plan_service = PlanService(db)
        
        # Check trial eligibility
        if not plan_service.check_trial_eligibility(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not eligible for trial"
            )
        
        success = plan_service.start_trial(current_user.id, request.plan_name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to start trial for plan '{request.plan_name}'"
            )
        
        return {"message": f"Successfully started trial for '{request.plan_name}'"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting trial: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start trial"
        )


@router.get("/capabilities/{capability_name}")
def check_capability(
    capability_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has a specific capability"""
    try:
        plan_service = PlanService(db)
        capabilities = plan_service.get_user_capabilities(current_user.id)
        
        # Map capability names to methods
        capability_map = {
            "full_ai": capabilities.has_full_ai_access,
            "premium_ai": capabilities.has_premium_ai_models,
            "enhanced_autopilot": capabilities.has_enhanced_autopilot,
            "ai_inbox": capabilities.can_use_ai_inbox,
            "crm_integration": capabilities.has_crm_integration,
            "advanced_analytics": capabilities.has_advanced_analytics,
            "predictive_analytics": capabilities.has_predictive_analytics,
            "white_label": capabilities.has_white_label,
            "autopilot_research": capabilities.has_autopilot_research,
            "autopilot_ads": capabilities.has_autopilot_ad_campaigns,
        }
        
        if capability_name not in capability_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown capability: {capability_name}"
            )
        
        has_capability = capability_map[capability_name]()
        
        return {
            "capability": capability_name,
            "has_access": has_capability,
            "plan": capabilities.get_plan_name()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking capability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check capability"
        )


@router.get("/limits")
def get_usage_limits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage limits for current user's plan"""
    try:
        plan_service = PlanService(db)
        capabilities = plan_service.get_user_capabilities(current_user.id)
        
        limits = {
            "plan": capabilities.get_plan_name(),
            "social_profiles": {
                "max": capabilities.plan.max_social_profiles if capabilities.plan else 1,
                "can_add_more": True  # TODO: Get current count and check
            },
            "posts": {
                "daily_limit": capabilities.plan.max_posts_per_day if capabilities.plan else 3,
                "weekly_limit": capabilities.plan.max_posts_per_week if capabilities.plan else 10,
                "can_post_today": True,  # TODO: Get today's count and check
                "can_post_this_week": True  # TODO: Get week's count and check
            },
            "images": {
                "monthly_limit": capabilities.plan.image_generation_limit if capabilities.plan else 5,
                "can_generate": True  # TODO: Get month's count and check
            },
            "autopilot": {
                "daily_posts": capabilities.get_autopilot_posts_per_day(),
                "research_enabled": capabilities.has_autopilot_research(),
                "ad_campaigns": capabilities.has_autopilot_ad_campaigns()
            },
            "team": {
                "max_users": capabilities.get_max_users(),
                "max_workspaces": capabilities.get_max_workspaces()
            }
        }
        
        return limits
        
    except Exception as e:
        logger.error(f"Error fetching usage limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch usage limits"
        )