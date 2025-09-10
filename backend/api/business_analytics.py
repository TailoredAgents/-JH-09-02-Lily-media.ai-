"""
PW-ANALYTICS-ADD-001: Business KPIs analytics API

Provides org-scoped business outcome metrics API endpoints for pressure washing companies.
Replaces vanity metrics with actionable business KPIs: leads, quotes, jobs, revenue, conversion rates.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from backend.db.database import get_db
from backend.auth.dependencies import get_current_active_user
from backend.db.models import User
from backend.middleware.tenant_context import get_tenant_context, require_role, TenantContext
from backend.services.business_analytics_service import (
    get_business_analytics_service,
    BusinessAnalyticsService, 
    BusinessAnalyticsRequest,
    BusinessAnalyticsResponse
)

router = APIRouter(prefix="/api/analytics", tags=["business-analytics"])
logger = logging.getLogger(__name__)


class BusinessAnalyticsQueryParams(BaseModel):
    """Query parameters for business analytics"""
    from_date: Optional[date] = Field(None, description="Start date (default: 30 days ago)")
    to_date: Optional[date] = Field(None, description="End date (default: today)")
    group_by: str = Field("day", description="Time grouping: day, week, month")
    platform: Optional[str] = Field(None, description="Filter by platform: facebook, instagram, twitter")
    service_type: Optional[str] = Field(None, description="Filter by service type")

    def to_request(self) -> BusinessAnalyticsRequest:
        """Convert to service request object with defaults"""
        # Default to last 30 days if dates not provided
        end_date = self.to_date or date.today()
        start_date = self.from_date or (end_date - timedelta(days=30))
        
        return BusinessAnalyticsRequest(
            from_date=start_date,
            to_date=end_date,
            group_by=self.group_by,
            platform=self.platform,
            service_type=self.service_type
        )


@router.get("/business", response_model=BusinessAnalyticsResponse)
async def get_business_analytics(
    params: BusinessAnalyticsQueryParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
) -> BusinessAnalyticsResponse:
    """
    Get comprehensive business outcome analytics for the organization
    
    Returns business KPIs including:
    - Lead volume and conversion rates
    - Quote acceptance and revenue metrics  
    - Job completion and service performance
    - Time-based trends with configurable grouping
    - Platform and service type breakdowns
    
    **Permissions Required:** analytics.read
    
    **Time Range:** Defaults to last 30 days if not specified
    
    **Grouping Options:**
    - `day`: Daily aggregation
    - `week`: Weekly aggregation (Monday start)
    - `month`: Monthly aggregation
    
    **Filters:**
    - `platform`: Filter by social media platform (facebook, instagram, twitter)
    - `service_type`: Filter by service type (pressure_washing, roof_cleaning, etc.)
    """
    
    # Require analytics read permission
    require_role(tenant_context, "analytics.read")
    
    # Validate query parameters
    if params.group_by not in ["day", "week", "month"]:
        raise HTTPException(status_code=400, detail="Invalid group_by value. Must be 'day', 'week', or 'month'")
    
    # Validate date range
    request = params.to_request()
    if request.from_date > request.to_date:
        raise HTTPException(status_code=400, detail="from_date must be <= to_date")
    
    # Limit date range to prevent excessive queries
    max_days = 365 * 2  # 2 years
    date_diff = (request.to_date - request.from_date).days
    if date_diff > max_days:
        raise HTTPException(
            status_code=400, 
            detail=f"Date range too large. Maximum {max_days} days allowed."
        )
    
    try:
        # Get analytics service
        analytics_service = get_business_analytics_service()
        
        # Compute business analytics for the organization
        result = analytics_service.get_business_analytics(
            db=db,
            organization_id=tenant_context.organization_id,
            request=request
        )
        
        logger.info(
            f"Business analytics computed for org {tenant_context.organization_id}: "
            f"{result.totals.leads} leads, {result.totals.jobs_completed} jobs completed, "
            f"${result.totals.revenue:.2f} revenue"
        )
        
        return result
        
    except ValueError as e:
        logger.warning(f"Invalid analytics request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error computing business analytics for org {tenant_context.organization_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute business analytics")


@router.get("/business/summary", response_model=dict)
async def get_business_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
) -> dict:
    """
    Get high-level business summary for dashboard display
    
    Returns key metrics for the last 30 days compared to previous period:
    - Total leads, quotes, jobs, revenue
    - Period-over-period growth rates
    - Key conversion rates
    
    **Permissions Required:** analytics.read
    """
    
    # Require analytics read permission
    require_role(tenant_context, "analytics.read")
    
    try:
        analytics_service = get_business_analytics_service()
        
        # Get current period (last 30 days)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        current_request = BusinessAnalyticsRequest(
            from_date=start_date,
            to_date=end_date,
            group_by="day"
        )
        
        current_analytics = analytics_service.get_business_analytics(
            db=db,
            organization_id=tenant_context.organization_id,
            request=current_request
        )
        
        # Get previous period (31-60 days ago) 
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=30)
        
        prev_request = BusinessAnalyticsRequest(
            from_date=prev_start_date,
            to_date=prev_end_date,
            group_by="day"
        )
        
        prev_analytics = analytics_service.get_business_analytics(
            db=db,
            organization_id=tenant_context.organization_id,
            request=prev_request
        )
        
        # Calculate growth rates
        def calculate_growth(current: float, previous: float) -> float:
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return ((current - previous) / previous) * 100.0
        
        summary = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": 30
            },
            "current": {
                "leads": current_analytics.totals.leads,
                "quotes": current_analytics.totals.quotes,
                "quotes_accepted": current_analytics.totals.quotes_accepted,
                "jobs_completed": current_analytics.totals.jobs_completed,
                "revenue": current_analytics.totals.revenue,
                "avg_ticket": current_analytics.totals.avg_ticket,
                "acceptance_rate": current_analytics.totals.acceptance_rate,
                "completion_rate": current_analytics.totals.completion_rate
            },
            "previous": {
                "leads": prev_analytics.totals.leads,
                "quotes": prev_analytics.totals.quotes,
                "quotes_accepted": prev_analytics.totals.quotes_accepted,
                "jobs_completed": prev_analytics.totals.jobs_completed,
                "revenue": prev_analytics.totals.revenue,
                "avg_ticket": prev_analytics.totals.avg_ticket
            },
            "growth": {
                "leads": calculate_growth(current_analytics.totals.leads, prev_analytics.totals.leads),
                "quotes": calculate_growth(current_analytics.totals.quotes, prev_analytics.totals.quotes),
                "quotes_accepted": calculate_growth(current_analytics.totals.quotes_accepted, prev_analytics.totals.quotes_accepted),
                "jobs_completed": calculate_growth(current_analytics.totals.jobs_completed, prev_analytics.totals.jobs_completed),
                "revenue": calculate_growth(current_analytics.totals.revenue, prev_analytics.totals.revenue),
                "avg_ticket": calculate_growth(current_analytics.totals.avg_ticket, prev_analytics.totals.avg_ticket)
            }
        }
        
        logger.info(f"Business summary computed for org {tenant_context.organization_id}")
        return summary
        
    except Exception as e:
        logger.error(f"Error computing business summary for org {tenant_context.organization_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute business summary")


# Health check endpoint for monitoring
@router.get("/health")
async def analytics_health_check():
    """Health check for analytics API"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}