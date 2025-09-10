"""
PW-ANALYTICS-ADD-001: Business KPIs analytics service

Provides business outcome analytics for pressure washing companies:
- Lead conversion funnel metrics
- Revenue and job completion analytics
- Time-based aggregations with org-scoped isolation
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, text
from sqlalchemy.dialects.postgresql import ARRAY
from pydantic import BaseModel

from backend.db.models import Lead, Quote, Job, Organization
from backend.middleware.tenant_context import get_tenant_context, require_role

logger = logging.getLogger(__name__)


class BusinessAnalyticsRequest(BaseModel):
    """Request model for business analytics"""
    from_date: date
    to_date: date
    group_by: str = "day"  # day, week, month
    platform: Optional[str] = None  # Filter by platform
    service_type: Optional[str] = None  # Filter by service type


class BusinessTotals(BaseModel):
    """Business totals for the time period"""
    leads: int
    quotes: int  
    quotes_accepted: int
    jobs_scheduled: int
    jobs_completed: int
    revenue: float
    avg_ticket: float
    acceptance_rate: float  # quotes_accepted / quotes_sent
    completion_rate: float  # jobs_completed / jobs_scheduled
    lead_to_quote_rate: float  # quotes / leads
    quote_to_job_rate: float  # jobs_scheduled / quotes_accepted


class TimeSeriesPoint(BaseModel):
    """Single time series data point"""
    period: str  # ISO date string
    leads: int = 0
    quotes: int = 0  
    quotes_accepted: int = 0
    jobs_scheduled: int = 0
    jobs_completed: int = 0
    revenue: float = 0.0


class PlatformBreakdown(BaseModel):
    """Platform-specific breakdown"""
    platform: str
    leads: int
    quotes: int
    quotes_accepted: int
    jobs_completed: int
    revenue: float


class ServiceTypeBreakdown(BaseModel):
    """Service type breakdown"""
    service_type: str
    jobs_scheduled: int
    jobs_completed: int
    revenue: float
    avg_ticket: float


class BusinessAnalyticsResponse(BaseModel):
    """Complete business analytics response"""
    totals: BusinessTotals
    time_series: List[TimeSeriesPoint]
    platform_breakdown: Optional[List[PlatformBreakdown]] = None
    service_type_breakdown: Optional[List[ServiceTypeBreakdown]] = None


class BusinessAnalyticsService:
    """
    Business analytics aggregation service for pressure washing companies
    
    Computes outcome-focused KPIs across the lead -> quote -> job -> revenue pipeline
    with org-scoped data isolation and flexible time groupings.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def get_business_analytics(
        self,
        db: Session,
        organization_id: str,
        request: BusinessAnalyticsRequest
    ) -> BusinessAnalyticsResponse:
        """
        Get comprehensive business analytics for an organization
        
        Args:
            db: Database session
            organization_id: Organization ID for multi-tenant scoping
            request: Analytics request parameters
            
        Returns:
            BusinessAnalyticsResponse with totals and time series data
        """
        self.logger.info(f"Computing business analytics for org {organization_id} from {request.from_date} to {request.to_date}")
        
        # Build base filters
        base_filters = self._build_base_filters(organization_id, request.from_date, request.to_date)
        platform_filter = request.platform
        service_type_filter = request.service_type
        
        # Compute totals
        totals = self._compute_totals(db, base_filters, platform_filter, service_type_filter)
        
        # Compute time series
        time_series = self._compute_time_series(
            db, base_filters, request.group_by, platform_filter, service_type_filter
        )
        
        # Compute breakdowns if requested (when no specific filters applied)
        platform_breakdown = None
        service_type_breakdown = None
        
        if not platform_filter:
            platform_breakdown = self._compute_platform_breakdown(db, base_filters)
            
        if not service_type_filter:
            service_type_breakdown = self._compute_service_type_breakdown(db, base_filters)
        
        return BusinessAnalyticsResponse(
            totals=totals,
            time_series=time_series,
            platform_breakdown=platform_breakdown,
            service_type_breakdown=service_type_breakdown
        )
    
    def _build_base_filters(self, organization_id: str, from_date: date, to_date: date) -> Dict[str, Any]:
        """Build base filters for org and date range"""
        # Convert to datetime for proper comparison
        start_datetime = datetime.combine(from_date, datetime.min.time())
        end_datetime = datetime.combine(to_date, datetime.max.time())
        
        return {
            'organization_id': organization_id,
            'start_datetime': start_datetime,
            'end_datetime': end_datetime
        }
    
    def _compute_totals(
        self,
        db: Session,
        base_filters: Dict[str, Any],
        platform_filter: Optional[str] = None,
        service_type_filter: Optional[str] = None
    ) -> BusinessTotals:
        """Compute aggregate totals across all models"""
        
        org_id = base_filters['organization_id']
        start_dt = base_filters['start_datetime']
        end_dt = base_filters['end_datetime']
        
        # Build platform condition
        platform_condition = True
        if platform_filter:
            platform_condition = Lead.source_platform == platform_filter
            
        # Build service type condition  
        service_type_condition = True
        if service_type_filter:
            service_type_condition = Job.service_type == service_type_filter
        
        # Lead metrics
        leads_count = db.query(func.count(Lead.id)).filter(
            and_(
                Lead.organization_id == org_id,
                Lead.created_at.between(start_dt, end_dt),
                platform_condition
            )
        ).scalar() or 0
        
        # Quote metrics
        quotes_query = db.query(Quote).filter(
            and_(
                Quote.organization_id == org_id,
                Quote.created_at.between(start_dt, end_dt)
            )
        )
        
        if platform_filter:
            # Join with leads to filter by platform
            quotes_query = quotes_query.join(Lead, Quote.lead_id == Lead.id).filter(
                Lead.source_platform == platform_filter
            )
        
        quotes_count = quotes_query.count()
        quotes_accepted_count = quotes_query.filter(Quote.status == 'accepted').count()
        
        # Job metrics  
        jobs_query = db.query(Job).filter(
            and_(
                Job.organization_id == org_id,
                Job.created_at.between(start_dt, end_dt),
                service_type_condition
            )
        )
        
        if platform_filter:
            # Join through quote to lead for platform filter
            jobs_query = jobs_query.join(Quote, Job.quote_id == Quote.id)\
                                   .join(Lead, Quote.lead_id == Lead.id)\
                                   .filter(Lead.source_platform == platform_filter)
        
        jobs_scheduled_count = jobs_query.count()
        jobs_completed_count = jobs_query.filter(Job.status == 'completed').count()
        
        # Revenue calculation (prefer actual_cost, fallback to estimated_cost)
        revenue_result = jobs_query.filter(Job.status == 'completed').with_entities(
            func.sum(
                case(
                    (Job.actual_cost.is_not(None), Job.actual_cost),
                    else_=Job.estimated_cost
                )
            )
        ).scalar()
        
        total_revenue = float(revenue_result or 0)
        
        # Compute derived metrics
        avg_ticket = total_revenue / jobs_completed_count if jobs_completed_count > 0 else 0.0
        acceptance_rate = quotes_accepted_count / quotes_count if quotes_count > 0 else 0.0
        completion_rate = jobs_completed_count / jobs_scheduled_count if jobs_scheduled_count > 0 else 0.0
        lead_to_quote_rate = quotes_count / leads_count if leads_count > 0 else 0.0
        quote_to_job_rate = jobs_scheduled_count / quotes_accepted_count if quotes_accepted_count > 0 else 0.0
        
        return BusinessTotals(
            leads=leads_count,
            quotes=quotes_count,
            quotes_accepted=quotes_accepted_count,
            jobs_scheduled=jobs_scheduled_count,
            jobs_completed=jobs_completed_count,
            revenue=total_revenue,
            avg_ticket=avg_ticket,
            acceptance_rate=acceptance_rate,
            completion_rate=completion_rate,
            lead_to_quote_rate=lead_to_quote_rate,
            quote_to_job_rate=quote_to_job_rate
        )
    
    def _compute_time_series(
        self,
        db: Session,
        base_filters: Dict[str, Any],
        group_by: str,
        platform_filter: Optional[str] = None,
        service_type_filter: Optional[str] = None
    ) -> List[TimeSeriesPoint]:
        """Compute time series data with specified grouping"""
        
        org_id = base_filters['organization_id']
        start_dt = base_filters['start_datetime']
        end_dt = base_filters['end_datetime']
        
        # Determine date truncation based on group_by
        if group_by == "day":
            date_trunc = func.date_trunc('day', Lead.created_at)
            date_format = 'YYYY-MM-DD'
        elif group_by == "week":
            date_trunc = func.date_trunc('week', Lead.created_at)  
            date_format = 'YYYY-MM-DD'
        elif group_by == "month":
            date_trunc = func.date_trunc('month', Lead.created_at)
            date_format = 'YYYY-MM-DD'
        else:
            raise ValueError(f"Invalid group_by value: {group_by}")
        
        # Build platform conditions
        lead_platform_condition = True
        quote_platform_condition = True
        job_platform_condition = True
        
        if platform_filter:
            lead_platform_condition = Lead.source_platform == platform_filter
            # For quotes and jobs, we'll need to join to leads
        
        # Build service type condition
        job_service_condition = True
        if service_type_filter:
            job_service_condition = Job.service_type == service_type_filter
        
        # Get leads time series
        leads_ts = db.query(
            date_trunc.label('period'),
            func.count(Lead.id).label('leads')
        ).filter(
            and_(
                Lead.organization_id == org_id,
                Lead.created_at.between(start_dt, end_dt),
                lead_platform_condition
            )
        ).group_by(date_trunc).all()
        
        # Get quotes time series
        quotes_subquery = db.query(Quote).filter(
            and_(
                Quote.organization_id == org_id,
                Quote.created_at.between(start_dt, end_dt)
            )
        )
        
        if platform_filter:
            quotes_subquery = quotes_subquery.join(Lead, Quote.lead_id == Lead.id).filter(
                Lead.source_platform == platform_filter
            )
        
        quotes_ts = quotes_subquery.with_entities(
            func.date_trunc(group_by, Quote.created_at).label('period'),
            func.count(Quote.id).label('quotes'),
            func.sum(case((Quote.status == 'accepted', 1), else_=0)).label('quotes_accepted')
        ).group_by(func.date_trunc(group_by, Quote.created_at)).all()
        
        # Get jobs time series
        jobs_subquery = db.query(Job).filter(
            and_(
                Job.organization_id == org_id,
                Job.created_at.between(start_dt, end_dt),
                job_service_condition
            )
        )
        
        if platform_filter:
            jobs_subquery = jobs_subquery.join(Quote, Job.quote_id == Quote.id)\
                                         .join(Lead, Quote.lead_id == Lead.id)\
                                         .filter(Lead.source_platform == platform_filter)
        
        jobs_ts = jobs_subquery.with_entities(
            func.date_trunc(group_by, Job.created_at).label('period'),
            func.count(Job.id).label('jobs_scheduled'),
            func.sum(case((Job.status == 'completed', 1), else_=0)).label('jobs_completed'),
            func.sum(
                case(
                    (Job.status == 'completed',
                     case(
                         (Job.actual_cost.is_not(None), Job.actual_cost),
                         else_=Job.estimated_cost
                     )
                    ),
                    else_=0
                )
            ).label('revenue')
        ).group_by(func.date_trunc(group_by, Job.created_at)).all()
        
        # Combine all time series data
        time_series_dict = {}
        
        # Add leads data
        for row in leads_ts:
            period_str = row.period.strftime('%Y-%m-%d')
            time_series_dict[period_str] = TimeSeriesPoint(
                period=period_str,
                leads=row.leads
            )
        
        # Add quotes data
        for row in quotes_ts:
            period_str = row.period.strftime('%Y-%m-%d')
            if period_str not in time_series_dict:
                time_series_dict[period_str] = TimeSeriesPoint(period=period_str)
            time_series_dict[period_str].quotes = row.quotes
            time_series_dict[period_str].quotes_accepted = row.quotes_accepted
        
        # Add jobs data
        for row in jobs_ts:
            period_str = row.period.strftime('%Y-%m-%d')
            if period_str not in time_series_dict:
                time_series_dict[period_str] = TimeSeriesPoint(period=period_str)
            time_series_dict[period_str].jobs_scheduled = row.jobs_scheduled
            time_series_dict[period_str].jobs_completed = row.jobs_completed
            time_series_dict[period_str].revenue = float(row.revenue or 0)
        
        # Return sorted time series
        return sorted(time_series_dict.values(), key=lambda x: x.period)
    
    def _compute_platform_breakdown(
        self, 
        db: Session, 
        base_filters: Dict[str, Any]
    ) -> List[PlatformBreakdown]:
        """Compute platform-specific breakdown"""
        
        org_id = base_filters['organization_id']
        start_dt = base_filters['start_datetime']
        end_dt = base_filters['end_datetime']
        
        # Get platform breakdown from leads joined to quotes and jobs
        platform_data = db.query(
            Lead.source_platform.label('platform'),
            func.count(func.distinct(Lead.id)).label('leads'),
            func.count(func.distinct(Quote.id)).label('quotes'),
            func.sum(case((Quote.status == 'accepted', 1), else_=0)).label('quotes_accepted'),
            func.sum(case((Job.status == 'completed', 1), else_=0)).label('jobs_completed'),
            func.sum(
                case(
                    (Job.status == 'completed',
                     case(
                         (Job.actual_cost.is_not(None), Job.actual_cost),
                         else_=Job.estimated_cost
                     )
                    ),
                    else_=0
                )
            ).label('revenue')
        ).outerjoin(Quote, Lead.id == Quote.lead_id)\
         .outerjoin(Job, Quote.id == Job.quote_id)\
         .filter(
            and_(
                Lead.organization_id == org_id,
                Lead.created_at.between(start_dt, end_dt)
            )
         ).group_by(Lead.source_platform).all()
        
        return [
            PlatformBreakdown(
                platform=row.platform,
                leads=row.leads or 0,
                quotes=row.quotes or 0,
                quotes_accepted=row.quotes_accepted or 0,
                jobs_completed=row.jobs_completed or 0,
                revenue=float(row.revenue or 0)
            )
            for row in platform_data
        ]
    
    def _compute_service_type_breakdown(
        self,
        db: Session,
        base_filters: Dict[str, Any]
    ) -> List[ServiceTypeBreakdown]:
        """Compute service type breakdown from jobs"""
        
        org_id = base_filters['organization_id']
        start_dt = base_filters['start_datetime']
        end_dt = base_filters['end_datetime']
        
        service_data = db.query(
            Job.service_type,
            func.count(Job.id).label('jobs_scheduled'),
            func.sum(case((Job.status == 'completed', 1), else_=0)).label('jobs_completed'),
            func.sum(
                case(
                    (Job.status == 'completed',
                     case(
                         (Job.actual_cost.is_not(None), Job.actual_cost),
                         else_=Job.estimated_cost
                     )
                    ),
                    else_=0
                )
            ).label('revenue')
        ).filter(
            and_(
                Job.organization_id == org_id,
                Job.created_at.between(start_dt, end_dt)
            )
        ).group_by(Job.service_type).all()
        
        return [
            ServiceTypeBreakdown(
                service_type=row.service_type,
                jobs_scheduled=row.jobs_scheduled,
                jobs_completed=row.jobs_completed or 0,
                revenue=float(row.revenue or 0),
                avg_ticket=float(row.revenue or 0) / max(row.jobs_completed or 1, 1)
            )
            for row in service_data
        ]


def get_business_analytics_service() -> BusinessAnalyticsService:
    """Factory function to get business analytics service instance"""
    return BusinessAnalyticsService()