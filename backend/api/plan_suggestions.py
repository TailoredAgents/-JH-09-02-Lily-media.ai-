"""
Plan upgrade suggestion API endpoints
Provides intelligent upgrade recommendations based on usage patterns
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.core.auth import get_current_user
from backend.core.plan_enforcement import (
    PlanManager, UpgradeSuggestionEngine, PlanTier, QuotaType, plan_manager
)
from backend.db.models import User

router = APIRouter(prefix="/api/plan-suggestions", tags=["Plan Management"])


@router.get("/proactive", response_model=List[Dict[str, Any]])
async def get_proactive_upgrade_suggestions(
    threshold: float = 0.8,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get proactive upgrade suggestions when approaching plan limits
    
    Args:
        threshold: Usage threshold (0.0-1.0) to trigger suggestions
    """
    try:
        # Get user's current plan
        plan_info = plan_manager.get_user_plan_info(current_user)
        current_plan = PlanTier(plan_info["plan"])
        
        # Get proactive suggestions
        suggestions = plan_manager.get_proactive_upgrade_suggestions(
            user_id=str(current_user.id),
            plan=current_plan,
            usage_threshold=threshold
        )
        
        return suggestions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get upgrade suggestions: {str(e)}"
        )


@router.get("/usage-summary", response_model=Dict[str, Any])
async def get_usage_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive usage summary with upgrade recommendations"""
    try:
        # Get user's current plan and usage
        plan_info = plan_manager.get_user_plan_info(current_user)
        current_plan = PlanTier(plan_info["plan"])
        
        usage_summary = plan_manager.get_user_usage_summary(
            user_id=str(current_user.id),
            plan=current_plan
        )
        
        # Add upgrade suggestions for high usage quotas
        upgrade_suggestions = []
        for quota_type_str, quota_info in usage_summary.items():
            if quota_info["percentage"] >= 75 and not quota_info["unlimited"]:
                try:
                    quota_type = QuotaType(quota_type_str)
                    suggestion = UpgradeSuggestionEngine.generate_quota_upgrade_suggestion(
                        current_plan, quota_type, quota_info["current"], quota_info["limit"]
                    )
                    upgrade_suggestions.append(suggestion)
                except ValueError:
                    continue  # Skip invalid quota types
        
        return {
            "current_plan": plan_info["plan"],
            "usage": usage_summary,
            "upgrade_suggestions": upgrade_suggestions,
            "features": plan_info["features"],
            "limits": plan_info["limits"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage summary: {str(e)}"
        )


@router.post("/feature-suggestion", response_model=Dict[str, Any])
async def get_feature_upgrade_suggestion(
    feature_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get upgrade suggestion for a specific blocked feature"""
    try:
        # Get user's current plan
        plan_info = plan_manager.get_user_plan_info(current_user)
        current_plan = PlanTier(plan_info["plan"])
        
        # Generate feature upgrade suggestion
        suggestion = UpgradeSuggestionEngine.generate_feature_upgrade_suggestion(
            current_plan, feature_name
        )
        
        return suggestion
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feature upgrade suggestion: {str(e)}"
        )


@router.get("/quota-warning/{quota_type}", response_model=Dict[str, Any])
async def check_quota_warning(
    quota_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user should see quota warning for specific quota type"""
    try:
        # Get user's current plan
        plan_info = plan_manager.get_user_plan_info(current_user)
        current_plan = PlanTier(plan_info["plan"])
        
        # Get usage for specific quota
        quota_enum = QuotaType(quota_type)
        current_usage = plan_manager.quota_manager.get_usage(str(current_user.id), quota_enum)
        limit = plan_info["limits"][quota_type]
        
        if limit <= 0 or limit == -1:  # Unlimited or no limit
            return {"show_warning": False}
            
        usage_percentage = (current_usage / limit) * 100
        
        # Show warning if over 80% usage
        show_warning = usage_percentage >= 80
        
        result = {
            "show_warning": show_warning,
            "usage_percentage": round(usage_percentage, 1),
            "current_usage": current_usage,
            "limit": limit,
            "quota_type": quota_type
        }
        
        # Add upgrade suggestion if warning
        if show_warning:
            suggestion = UpgradeSuggestionEngine.generate_quota_upgrade_suggestion(
                current_plan, quota_enum, current_usage, limit
            )
            result["upgrade_suggestion"] = suggestion
            
            # Log the warning
            plan_manager.log_plan_usage_warning(
                str(current_user.id), current_plan, quota_enum, usage_percentage
            )
        
        return result
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid quota type: {quota_type}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check quota warning: {str(e)}"
        )


@router.get("/all-plans", response_model=List[Dict[str, Any]])
async def get_all_plan_options():
    """Get all available plan options with features and pricing"""
    
    plans = []
    
    for plan_tier in PlanTier:
        plan_data = {
            "name": plan_tier.value,
            "display_name": plan_tier.value.title(),
            "pricing": UpgradeSuggestionEngine.PLAN_PRICING.get(plan_tier, {"monthly": 0, "annual": 0}),
            "features": {
                feature: enabled 
                for feature, enabled in plan_manager.get_user_plan_info(
                    type("MockUser", (), {"subscription_plan": plan_tier.value})()
                )["features"].items()
            },
            "limits": {
                quota.value: limit
                for quota, limit in plan_manager.get_user_plan_info(
                    type("MockUser", (), {"subscription_plan": plan_tier.value})()
                )["limits"].items()
            }
        }
        
        plans.append(plan_data)
    
    return plans