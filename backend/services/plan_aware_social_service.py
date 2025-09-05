"""
Plan-Aware Social Connection Service
Enforces plan-based limits on social media account connections
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from backend.services.plan_service import PlanService
from backend.db.models import User, SocialPlatformConnection
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PlanAwareSocialService:
    """
    Social connection service with plan-based limits and feature gating
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.plan_service = PlanService(db)
        
        # Plan-based platform access
        self.plan_platform_access = {
            "free": ["twitter", "instagram"],  # Limited to basic platforms
            "starter": ["twitter", "instagram", "facebook", "linkedin"],
            "pro": ["twitter", "instagram", "facebook", "linkedin", "tiktok", "youtube"],
            "enterprise": ["twitter", "instagram", "facebook", "linkedin", "tiktok", "youtube", "pinterest"]
        }
        
        # Plan-based advanced features
        self.plan_features = {
            "free": {
                "auto_posting": False,
                "bulk_operations": False,
                "analytics_depth": "basic",
                "scheduling_horizon_days": 7
            },
            "starter": {
                "auto_posting": True,
                "bulk_operations": False,
                "analytics_depth": "standard",
                "scheduling_horizon_days": 30
            },
            "pro": {
                "auto_posting": True,
                "bulk_operations": True,
                "analytics_depth": "advanced",
                "scheduling_horizon_days": 90
            },
            "enterprise": {
                "auto_posting": True,
                "bulk_operations": True,
                "analytics_depth": "premium",
                "scheduling_horizon_days": 365
            }
        }
    
    async def check_connection_limit(self, user_id: int) -> Dict[str, Any]:
        """
        Check if user can connect more social accounts
        
        Returns:
            Dict with limit check results and usage information
        """
        try:
            # Get user plan capabilities
            capabilities = self.plan_service.get_user_capabilities(user_id)
            plan_name = capabilities.get_plan_name()
            
            # Get current connection count
            current_count = await self._get_active_connections_count(user_id)
            
            # Check against plan limit
            max_connections = capabilities.plan.max_social_profiles if capabilities.plan else 1
            can_connect_more = capabilities.can_connect_social_accounts(current_count)
            
            return {
                "can_connect": can_connect_more,
                "plan": plan_name,
                "current_connections": current_count,
                "max_connections": max_connections,
                "remaining": max(0, max_connections - current_count),
                "usage_percentage": (current_count / max_connections * 100) if max_connections > 0 else 100,
                "upgrade_needed": not can_connect_more
            }
            
        except Exception as e:
            logger.error(f"Error checking connection limit for user {user_id}: {e}")
            return {
                "can_connect": False,
                "error": str(e)
            }
    
    async def validate_platform_access(self, user_id: int, platform: str) -> Dict[str, Any]:
        """
        Validate if user can access specific platform based on their plan
        
        Args:
            user_id: User ID
            platform: Platform name (twitter, instagram, etc.)
            
        Returns:
            Dict with validation results
        """
        try:
            capabilities = self.plan_service.get_user_capabilities(user_id)
            plan_name = capabilities.get_plan_name()
            
            available_platforms = self.plan_platform_access.get(plan_name, ["twitter"])
            has_access = platform in available_platforms
            
            return {
                "has_access": has_access,
                "platform": platform,
                "plan": plan_name,
                "available_platforms": available_platforms,
                "restricted": not has_access,
                "upgrade_required": not has_access and plan_name in ["free", "starter"]
            }
            
        except Exception as e:
            logger.error(f"Error validating platform access for user {user_id}, platform {platform}: {e}")
            return {
                "has_access": False,
                "error": str(e)
            }
    
    async def get_connection_capabilities(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive social connection capabilities for user
        
        Returns:
            Dict with detailed capabilities information
        """
        try:
            capabilities = self.plan_service.get_user_capabilities(user_id)
            plan_name = capabilities.get_plan_name()
            
            # Get current connections
            current_count = await self._get_active_connections_count(user_id)
            connections_by_platform = await self._get_connections_by_platform(user_id)
            
            # Plan limits
            max_connections = capabilities.plan.max_social_profiles if capabilities.plan else 1
            
            return {
                "plan": plan_name,
                "limits": {
                    "max_connections": max_connections,
                    "current_connections": current_count,
                    "remaining": max(0, max_connections - current_count),
                    "can_connect_more": current_count < max_connections
                },
                "platforms": {
                    "available": self.plan_platform_access.get(plan_name, ["twitter"]),
                    "connected": list(connections_by_platform.keys()),
                    "remaining_slots": max(0, max_connections - current_count)
                },
                "features": self.plan_features.get(plan_name, self.plan_features["free"]),
                "connections_detail": connections_by_platform,
                "upgrade_benefits": self._get_upgrade_benefits(plan_name)
            }
            
        except Exception as e:
            logger.error(f"Error getting connection capabilities for user {user_id}: {e}")
            return {
                "plan": "unknown",
                "error": str(e)
            }
    
    async def enforce_connection_limit(self, user_id: int, platform: str) -> Dict[str, Any]:
        """
        Enforce connection limits before allowing new connection
        
        Args:
            user_id: User attempting to connect
            platform: Platform they want to connect
            
        Returns:
            Dict with enforcement decision and details
        """
        try:
            # Check overall connection limit
            limit_check = await self.check_connection_limit(user_id)
            if not limit_check["can_connect"]:
                return {
                    "allowed": False,
                    "reason": "connection_limit_exceeded",
                    "message": f"Maximum connections limit reached ({limit_check['current_connections']}/{limit_check['max_connections']})",
                    "plan": limit_check["plan"],
                    "current_usage": limit_check,
                    "suggested_plans": self._get_upgrade_suggestions(limit_check["plan"])
                }
            
            # Check platform access
            platform_check = await self.validate_platform_access(user_id, platform)
            if not platform_check["has_access"]:
                return {
                    "allowed": False,
                    "reason": "platform_restricted",
                    "message": f"Platform '{platform}' not available on {platform_check['plan']} plan",
                    "plan": platform_check["plan"],
                    "available_platforms": platform_check["available_platforms"],
                    "suggested_plans": self._get_upgrade_suggestions(platform_check["plan"])
                }
            
            # Check for duplicate connections
            existing_connection = await self._get_platform_connection(user_id, platform)
            if existing_connection:
                return {
                    "allowed": False,
                    "reason": "platform_already_connected",
                    "message": f"Platform '{platform}' is already connected",
                    "existing_connection": {
                        "id": existing_connection.id,
                        "username": existing_connection.platform_username,
                        "connected_at": existing_connection.connected_at.isoformat()
                    }
                }
            
            # All checks passed
            return {
                "allowed": True,
                "platform": platform,
                "remaining_connections": limit_check["remaining"] - 1,
                "message": f"Connection to {platform} allowed"
            }
            
        except Exception as e:
            logger.error(f"Error enforcing connection limit for user {user_id}, platform {platform}: {e}")
            return {
                "allowed": False,
                "reason": "system_error",
                "message": f"System error: {str(e)}"
            }
    
    async def track_connection_usage(self, user_id: int, platform: str, action: str, 
                                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Track connection usage for analytics and billing
        
        Args:
            user_id: User ID
            platform: Platform name
            action: Action performed (connect, disconnect, post, etc.)
            metadata: Additional metadata
        """
        try:
            # TODO: Implement usage tracking to database/analytics
            logger.info(f"Connection usage - User: {user_id}, Platform: {platform}, Action: {action}")
            if metadata:
                logger.info(f"Connection metadata: {metadata}")
            
        except Exception as e:
            logger.error(f"Error tracking connection usage: {e}")
    
    async def _get_active_connections_count(self, user_id: int) -> int:
        """Get count of active social platform connections for user"""
        try:
            result = self.db.execute(
                select(func.count(SocialPlatformConnection.id))
                .where(
                    and_(
                        SocialPlatformConnection.user_id == user_id,
                        SocialPlatformConnection.is_active == True
                    )
                )
            )
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error getting active connections count for user {user_id}: {e}")
            return 0
    
    async def _get_connections_by_platform(self, user_id: int) -> Dict[str, Any]:
        """Get active connections grouped by platform"""
        try:
            result = self.db.execute(
                select(SocialPlatformConnection)
                .where(
                    and_(
                        SocialPlatformConnection.user_id == user_id,
                        SocialPlatformConnection.is_active == True
                    )
                )
            )
            connections = result.scalars().all()
            
            by_platform = {}
            for conn in connections:
                by_platform[conn.platform] = {
                    "id": conn.id,
                    "username": conn.platform_username,
                    "display_name": conn.platform_display_name,
                    "connected_at": conn.connected_at.isoformat(),
                    "last_used": conn.last_used_at.isoformat() if conn.last_used_at else None,
                    "status": conn.connection_status
                }
            
            return by_platform
            
        except Exception as e:
            logger.error(f"Error getting connections by platform for user {user_id}: {e}")
            return {}
    
    async def _get_platform_connection(self, user_id: int, platform: str) -> Optional[SocialPlatformConnection]:
        """Get existing connection for user and platform"""
        try:
            result = self.db.execute(
                select(SocialPlatformConnection)
                .where(
                    and_(
                        SocialPlatformConnection.user_id == user_id,
                        SocialPlatformConnection.platform == platform,
                        SocialPlatformConnection.is_active == True
                    )
                )
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting platform connection for user {user_id}, platform {platform}: {e}")
            return None
    
    def _get_upgrade_suggestions(self, current_plan: str) -> List[Dict[str, Any]]:
        """Get suggested plan upgrades with benefits"""
        upgrade_map = {
            "free": [
                {"plan": "starter", "connections": 5, "platforms": 4},
                {"plan": "pro", "connections": 25, "platforms": 6}
            ],
            "starter": [
                {"plan": "pro", "connections": 25, "platforms": 6},
                {"plan": "enterprise", "connections": 100, "platforms": 7}
            ],
            "pro": [
                {"plan": "enterprise", "connections": 100, "platforms": 7}
            ],
            "enterprise": []
        }
        return upgrade_map.get(current_plan, [])
    
    def _get_upgrade_benefits(self, current_plan: str) -> Dict[str, Any]:
        """Get benefits of upgrading from current plan"""
        benefits = {
            "free": {
                "starter": ["5 social profiles", "4 platforms", "Auto-posting", "30-day scheduling"],
                "pro": ["25 social profiles", "6 platforms", "Bulk operations", "Advanced analytics"]
            },
            "starter": {
                "pro": ["25 social profiles", "TikTok & YouTube", "Bulk operations", "Advanced analytics"],
                "enterprise": ["100 social profiles", "All platforms", "Premium analytics", "1-year scheduling"]
            },
            "pro": {
                "enterprise": ["100 social profiles", "Pinterest access", "Premium analytics", "Priority support"]
            }
        }
        return benefits.get(current_plan, {})


def get_plan_aware_social_service(db: Session) -> PlanAwareSocialService:
    """Get plan-aware social service instance"""
    return PlanAwareSocialService(db)