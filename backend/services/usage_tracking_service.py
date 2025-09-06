"""
Usage Tracking Service for Subscription Enforcement
Tracks API usage, image generation, posts, and other billable activities
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from backend.db.models import UsageRecord, User
from backend.services.redis_cache import redis_cache

logger = logging.getLogger(__name__)


class UsageTrackingService:
    """
    Service to track and enforce usage limits based on subscription tiers
    """
    
    def __init__(self, db: Session):
        self.db = db
        
        # Usage type mapping for different activities
        self.usage_types = {
            "image_generation": "image_generation",
            "post_creation": "post_creation",
            "api_call": "api_call",
            "ai_content_generation": "ai_content_generation",
            "scheduling": "scheduling",
            "analytics": "analytics"
        }
    
    async def track_usage(
        self,
        user_id: int,
        organization_id: int,
        usage_type: str,
        resource: Optional[str] = None,
        quantity: int = 1,
        cost_credits: float = 0.0,
        cost_usd: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track a usage event
        
        Args:
            user_id: User ID
            organization_id: Organization ID
            usage_type: Type of usage (image_generation, post_creation, etc.)
            resource: Specific resource used (grok2, gpt_image_1, etc.)
            quantity: Amount used (default 1)
            cost_credits: Cost in internal credits
            cost_usd: Cost in USD
            metadata: Additional context
            
        Returns:
            Success status
        """
        try:
            # Get current billing period (YYYY-MM)
            current_period = datetime.now(timezone.utc).strftime("%Y-%m")
            
            # Create usage record
            usage_record = UsageRecord(
                user_id=user_id,
                organization_id=organization_id,
                usage_type=usage_type,
                resource=resource,
                quantity=quantity,
                cost_credits=cost_credits,
                cost_usd=cost_usd,
                usage_metadata=metadata or {},
                billing_period=current_period
            )
            
            self.db.add(usage_record)
            self.db.commit()
            
            # Invalidate cache for this user's usage
            await self._invalidate_usage_cache(user_id, current_period, usage_type)
            
            logger.info(f"Usage tracked: user={user_id}, type={usage_type}, quantity={quantity}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to track usage: {e}")
            self.db.rollback()
            return False
    
    async def get_monthly_usage(
        self,
        user_id: int,
        usage_type: str,
        period: Optional[str] = None
    ) -> int:
        """
        Get monthly usage for a specific user and usage type
        
        Args:
            user_id: User ID
            usage_type: Type of usage to check
            period: Billing period (YYYY-MM), defaults to current month
            
        Returns:
            Total usage quantity for the period
        """
        if period is None:
            period = datetime.now(timezone.utc).strftime("%Y-%m")
        
        # Try cache first
        cache_key = f"usage:{user_id}:{usage_type}:{period}"
        try:
            cached_usage = await redis_cache.get("usage_tracking", "monthly_usage", resource_id=cache_key)
            if cached_usage is not None:
                return cached_usage
        except Exception as e:
            logger.warning(f"Cache read failed for usage: {e}")
        
        try:
            # Query database
            result = self.db.query(func.sum(UsageRecord.quantity)).filter(
                and_(
                    UsageRecord.user_id == user_id,
                    UsageRecord.usage_type == usage_type,
                    UsageRecord.billing_period == period
                )
            ).scalar()
            
            usage_count = result or 0
            
            # Cache the result for 5 minutes
            try:
                await redis_cache.set("usage_tracking", "monthly_usage", usage_count, resource_id=cache_key, ttl=300)
            except Exception as e:
                logger.warning(f"Cache write failed for usage: {e}")
            
            return usage_count
            
        except Exception as e:
            logger.error(f"Failed to get monthly usage: {e}")
            return 0
    
    async def get_organization_usage(
        self,
        organization_id: int,
        usage_type: str,
        period: Optional[str] = None
    ) -> int:
        """
        Get monthly usage for an entire organization
        
        Args:
            organization_id: Organization ID
            usage_type: Type of usage to check
            period: Billing period (YYYY-MM), defaults to current month
            
        Returns:
            Total usage quantity for the organization in the period
        """
        if period is None:
            period = datetime.now(timezone.utc).strftime("%Y-%m")
        
        try:
            result = self.db.query(func.sum(UsageRecord.quantity)).filter(
                and_(
                    UsageRecord.organization_id == organization_id,
                    UsageRecord.usage_type == usage_type,
                    UsageRecord.billing_period == period
                )
            ).scalar()
            
            return result or 0
            
        except Exception as e:
            logger.error(f"Failed to get organization usage: {e}")
            return 0
    
    async def check_usage_limit(
        self,
        user_id: int,
        usage_type: str,
        limit: int,
        period: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if user has exceeded usage limit
        
        Args:
            user_id: User ID
            usage_type: Type of usage to check
            limit: Usage limit to check against
            period: Billing period (YYYY-MM), defaults to current month
            
        Returns:
            Dict with usage info and limit status
        """
        current_usage = await self.get_monthly_usage(user_id, usage_type, period)
        
        return {
            "current_usage": current_usage,
            "limit": limit,
            "remaining": max(0, limit - current_usage),
            "exceeded": current_usage >= limit,
            "percentage_used": (current_usage / limit * 100) if limit > 0 else 0
        }
    
    async def get_usage_summary(
        self,
        user_id: int,
        period: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive usage summary for a user
        
        Args:
            user_id: User ID
            period: Billing period (YYYY-MM), defaults to current month
            
        Returns:
            Dict with usage summary for all types
        """
        if period is None:
            period = datetime.now(timezone.utc).strftime("%Y-%m")
        
        try:
            # Query all usage types for the user in the period
            results = self.db.query(
                UsageRecord.usage_type,
                func.sum(UsageRecord.quantity),
                func.sum(UsageRecord.cost_credits),
                func.sum(UsageRecord.cost_usd)
            ).filter(
                and_(
                    UsageRecord.user_id == user_id,
                    UsageRecord.billing_period == period
                )
            ).group_by(UsageRecord.usage_type).all()
            
            summary = {}
            total_credits = 0.0
            total_usd = 0.0
            
            for usage_type, quantity, credits, usd in results:
                summary[usage_type] = {
                    "quantity": quantity or 0,
                    "cost_credits": float(credits or 0),
                    "cost_usd": float(usd or 0)
                }
                total_credits += float(credits or 0)
                total_usd += float(usd or 0)
            
            return {
                "period": period,
                "usage_by_type": summary,
                "totals": {
                    "cost_credits": total_credits,
                    "cost_usd": total_usd
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage summary: {e}")
            return {
                "period": period,
                "usage_by_type": {},
                "totals": {"cost_credits": 0.0, "cost_usd": 0.0}
            }
    
    async def _invalidate_usage_cache(self, user_id: int, period: str, usage_type: str):
        """Invalidate usage cache for a user/period/type combination"""
        try:
            cache_key = f"usage:{user_id}:{usage_type}:{period}"
            await redis_cache.delete("usage_tracking", "monthly_usage", resource_id=cache_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate usage cache: {e}")


# Factory function
def get_usage_tracking_service(db: Session) -> UsageTrackingService:
    """Get usage tracking service instance"""
    return UsageTrackingService(db)