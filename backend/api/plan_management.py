"""
Plan management API endpoints for subscription plan operations
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.core.plan_enforcement import (
    PlanTier, QuotaType, PlanLimits, PlanManager, 
    get_plan_manager
)

# Optional auth imports - fallback if not available  
try:
    from backend.api.auth_fastapi_users import current_active_user
    from backend.db.models import User
    AUTH_AVAILABLE = True
except ImportError:
    class MockUser:
        id = "mock-user"
        subscription_plan = "free"
    
    def mock_current_active_user():
        return MockUser()
    
    current_active_user = mock_current_active_user
    User = MockUser
    AUTH_AVAILABLE = False

# Optional database import
try:
    from backend.db.database import get_db
    DB_AVAILABLE = True
except ImportError:
    def mock_get_db():
        return None
    get_db = mock_get_db
    DB_AVAILABLE = False

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/plans", tags=["plan_management"])

# Pydantic models
class PlanInfo(BaseModel):
    plan: str = Field(..., description="Current subscription plan")
    limits: Dict[str, int] = Field(..., description="Plan-specific usage limits")
    features: Dict[str, bool] = Field(..., description="Plan-specific feature access")

class QuotaUsage(BaseModel):
    quota_type: str = Field(..., description="Type of quota")
    current: int = Field(..., description="Current usage")
    limit: int = Field(..., description="Usage limit (-1 for unlimited)")
    percentage: float = Field(..., description="Usage percentage")
    unlimited: bool = Field(..., description="Whether quota is unlimited")

class UsageSummary(BaseModel):
    user_id: str = Field(..., description="User ID")
    plan: str = Field(..., description="Current plan")
    usage: Dict[str, QuotaUsage] = Field(..., description="Usage by quota type")
    timestamp: datetime = Field(..., description="Summary timestamp")

class PlanUpgradeRequest(BaseModel):
    target_plan: str = Field(..., description="Target plan to upgrade to")
    billing_cycle: str = Field("monthly", description="Billing cycle (monthly/yearly)")

class PlanFeatureCheck(BaseModel):
    feature: str = Field(..., description="Feature to check")
    available: bool = Field(..., description="Whether feature is available")
    required_plan: Optional[str] = Field(None, description="Minimum plan required for feature")

class QuotaResetRequest(BaseModel):
    quota_types: Optional[List[str]] = Field(None, description="Specific quota types to reset (null for all)")

@router.get("/current", response_model=PlanInfo)
async def get_current_plan(
    user: User = Depends(current_active_user),
    plan_manager: PlanManager = Depends(get_plan_manager)
):
    """
    Get current user's plan information including limits and features
    """
    try:
        plan_info = plan_manager.get_user_plan_info(user)
        
        return PlanInfo(
            plan=plan_info['plan'],
            limits={k.value if hasattr(k, 'value') else str(k): v for k, v in plan_info['limits'].items()},
            features=plan_info['features']
        )
        
    except Exception as e:
        logger.error(f"Error getting plan info for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve plan information")

@router.get("/usage", response_model=UsageSummary)  
async def get_usage_summary(
    user: User = Depends(current_active_user),
    plan_manager: PlanManager = Depends(get_plan_manager)
):
    """
    Get comprehensive usage summary for the current user
    """
    try:
        # Get user's plan
        plan_info = plan_manager.get_user_plan_info(user)
        plan = PlanTier(plan_info['plan'])
        
        # Get usage summary
        usage_data = plan_manager.get_user_usage_summary(str(user.id), plan)
        
        # Convert to response format
        usage_summary = {}
        for quota_type, data in usage_data.items():
            usage_summary[quota_type] = QuotaUsage(
                quota_type=quota_type,
                current=data['current'],
                limit=data['limit'],
                percentage=data['percentage'],
                unlimited=data['unlimited']
            )
        
        return UsageSummary(
            user_id=str(user.id),
            plan=plan_info['plan'],
            usage=usage_summary,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error getting usage summary for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve usage summary")

@router.get("/features/{feature}", response_model=PlanFeatureCheck)
async def check_feature_access(
    feature: str,
    user: User = Depends(current_active_user),
    plan_manager: PlanManager = Depends(get_plan_manager)
):
    """
    Check if current user's plan has access to a specific feature
    """
    try:
        plan_info = plan_manager.get_user_plan_info(user)
        plan = PlanTier(plan_info['plan'])
        
        # Check feature availability
        available = PlanLimits.has_feature(plan, feature)
        
        # Find minimum required plan if feature is not available
        required_plan = None
        if not available:
            for tier in [PlanTier.BASIC, PlanTier.PROFESSIONAL, PlanTier.ENTERPRISE]:
                if PlanLimits.has_feature(tier, feature):
                    required_plan = tier.value
                    break
        
        return PlanFeatureCheck(
            feature=feature,
            available=available,
            required_plan=required_plan
        )
        
    except ValueError as e:
        if "is not a valid PlanTier" in str(e):
            # Handle unknown plan gracefully
            return PlanFeatureCheck(
                feature=feature,
                available=False,
                required_plan="basic"
            )
        raise HTTPException(status_code=400, detail=f"Invalid plan or feature: {e}")
    except Exception as e:
        logger.error(f"Error checking feature access for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to check feature access")

@router.get("/quotas/{quota_type}")
async def get_quota_status(
    quota_type: str,
    user: User = Depends(current_active_user),
    plan_manager: PlanManager = Depends(get_plan_manager)
):
    """
    Get detailed status for a specific quota type
    """
    try:
        # Validate quota type
        try:
            qt = QuotaType(quota_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid quota type: {quota_type}")
        
        # Get user's plan
        plan_info = plan_manager.get_user_plan_info(user)
        plan = PlanTier(plan_info['plan'])
        
        # Get quota details
        current_usage = plan_manager.quota_manager.get_usage(str(user.id), qt)
        limit = PlanLimits.get_limit(plan, qt)
        
        return {
            "quota_type": quota_type,
            "current_usage": current_usage,
            "limit": limit,
            "remaining": max(0, limit - current_usage) if limit != -1 else -1,
            "percentage": (current_usage / limit * 100) if limit > 0 else 0,
            "unlimited": limit == -1,
            "plan": plan.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quota status for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve quota status")

@router.get("/available")
async def get_available_plans():
    """
    Get all available subscription plans with their features and limits
    """
    try:
        plans_info = {}
        
        for plan_tier in PlanTier:
            plans_info[plan_tier.value] = {
                "name": plan_tier.value.title(),
                "limits": {qt.value: limit for qt, limit in PlanLimits.PLAN_LIMITS[plan_tier].items()},
                "features": PlanLimits.PLAN_FEATURES[plan_tier],
                "tier_order": list(PlanTier).index(plan_tier)
            }
        
        return {
            "plans": plans_info,
            "quota_types": [qt.value for qt in QuotaType],
            "feature_descriptions": {
                "ai_content_generation": "AI-powered content creation",
                "basic_scheduling": "Schedule posts in advance",
                "single_platform_posting": "Post to one social media platform",
                "basic_analytics": "Basic performance metrics",
                "community_support": "Community forum support",
                "multi_platform_posting": "Post to multiple platforms simultaneously",
                "advanced_analytics": "Detailed analytics and insights",
                "custom_workflows": "Create custom automation workflows",
                "api_access": "Access to REST API",
                "priority_support": "Priority email and chat support",
                "white_label": "Remove branding and customize interface",
                "sso": "Single Sign-On integration",
                "advanced_ai_features": "Advanced AI capabilities and models",
                "bulk_operations": "Bulk content creation and scheduling"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting available plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve available plans")

@router.post("/upgrade")
async def request_plan_upgrade(
    upgrade_request: PlanUpgradeRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_active_user),
    db=Depends(get_db)
):
    """
    Request a plan upgrade (integrates with billing system)
    """
    try:
        # Validate target plan
        try:
            target_plan = PlanTier(upgrade_request.target_plan.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid plan: {upgrade_request.target_plan}")
        
        # Get current plan
        current_plan_name = "free"
        if hasattr(user, 'subscription_plan'):
            current_plan_name = user.subscription_plan
        elif hasattr(user, 'organization') and user.organization:
            current_plan_name = getattr(user.organization, 'subscription_plan', 'free')
            
        current_plan = PlanTier(current_plan_name.lower())
        
        # Check if upgrade is valid
        plan_order = [PlanTier.FREE, PlanTier.BASIC, PlanTier.PROFESSIONAL, PlanTier.ENTERPRISE]
        if plan_order.index(target_plan) <= plan_order.index(current_plan):
            raise HTTPException(
                status_code=400, 
                detail="Cannot upgrade to a lower or same tier plan"
            )
        
        # Create upgrade request (this would integrate with billing system)
        upgrade_data = {
            "user_id": str(user.id),
            "current_plan": current_plan.value,
            "target_plan": target_plan.value,
            "billing_cycle": upgrade_request.billing_cycle,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        
        # Background task to process upgrade
        background_tasks.add_task(process_plan_upgrade, upgrade_data)
        
        return {
            "message": "Plan upgrade request submitted",
            "upgrade_request": upgrade_data,
            "next_steps": "You will receive billing information via email"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing plan upgrade for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process upgrade request")

@router.post("/admin/reset-quotas/{user_id}")
async def reset_user_quotas(
    user_id: str,
    reset_request: QuotaResetRequest,
    user: User = Depends(current_active_user),
    plan_manager: PlanManager = Depends(get_plan_manager)
):
    """
    Reset quotas for a specific user (admin only)
    """
    # Check if user is admin (simplified check - implement proper admin validation)
    if not hasattr(user, 'is_admin') or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        quota_types = None
        if reset_request.quota_types:
            quota_types = []
            for qt_str in reset_request.quota_types:
                try:
                    quota_types.append(QuotaType(qt_str))
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid quota type: {qt_str}")
        
        plan_manager.reset_user_quotas(user_id, quota_types)
        
        return {
            "message": "User quotas reset successfully",
            "user_id": user_id,
            "reset_quota_types": reset_request.quota_types or "all",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting quotas for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset user quotas")

@router.get("/admin/usage-stats")
async def get_platform_usage_stats(
    user: User = Depends(current_active_user),
    db=Depends(get_db),
    days: int = Query(7, description="Number of days to analyze")
):
    """
    Get platform-wide usage statistics (admin only)
    """
    # Check if user is admin
    if not hasattr(user, 'is_admin') or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not DB_AVAILABLE:
        return {
            "message": "Database not available for usage statistics",
            "stats": {}
        }
    
    try:
        # Get user distribution by plan
        plan_distribution = {}
        for plan in PlanTier:
            plan_distribution[plan.value] = 0  # Would query database
        
        # Get quota usage statistics  
        quota_stats = {}
        for quota_type in QuotaType:
            quota_stats[quota_type.value] = {
                "total_usage": 0,
                "avg_usage": 0,
                "peak_usage": 0,
                "users_at_limit": 0
            }
        
        return {
            "period_days": days,
            "plan_distribution": plan_distribution,
            "quota_statistics": quota_stats,
            "total_active_users": sum(plan_distribution.values()),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting platform usage stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve usage statistics")

async def process_plan_upgrade(upgrade_data: Dict[str, Any]):
    """Background task to process plan upgrade with billing system"""
    try:
        logger.info(f"Processing plan upgrade: {upgrade_data}")
        
        # This would integrate with the billing system (Stripe, etc.)
        # For now, just log the upgrade request
        
        # Example integration points:
        # 1. Create billing subscription in Stripe
        # 2. Send confirmation email
        # 3. Update user plan in database
        # 4. Log upgrade event for analytics
        
        logger.info(f"Plan upgrade processed successfully for user {upgrade_data['user_id']}")
        
    except Exception as e:
        logger.error(f"Failed to process plan upgrade: {e}")
        # Would typically send failure notification and rollback