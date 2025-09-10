"""
PW-DM-ADD-001: Jobs API

API endpoints for managing pressure washing jobs: creation from accepted quotes,
scheduling, status updates, and job lifecycle management.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict, validator

from backend.db.database import get_db
from backend.auth.dependencies import get_current_active_user
from backend.db.models import User, Job, Quote, Lead
from backend.middleware.tenant_context import get_tenant_context, TenantContext, require_role
from backend.services.job_service import get_job_service, JobCreationRequest, JobUpdateRequest
from backend.core.audit_logger import get_audit_logger, AuditEventType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])


# Request/Response Models

class JobCreateRequest(BaseModel):
    """Request to create a new job"""
    model_config = ConfigDict(from_attributes=True)
    
    service_type: str = Field(..., description="Primary service type for the job")
    address: str = Field(..., description="Service location address")
    estimated_cost: float = Field(..., gt=0, description="Estimated job cost")
    
    # Optional relationships
    quote_id: Optional[str] = Field(None, description="Quote ID if created from quote")
    lead_id: Optional[str] = Field(None, description="Lead ID if created from lead")
    
    # Customer information (required if not from quote/lead)
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_email: Optional[str] = Field(None, description="Customer email")
    customer_phone: Optional[str] = Field(None, description="Customer phone")
    
    # Scheduling
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled start time")
    duration_minutes: Optional[int] = Field(None, gt=0, description="Estimated duration in minutes")
    
    # Job details
    service_details: Dict[str, Any] = Field(default_factory=dict, description="Detailed service breakdown")
    crew: Dict[str, Any] = Field(default_factory=dict, description="Crew assignment")
    crew_notes: Optional[str] = Field(None, description="Special crew instructions")
    internal_notes: Optional[str] = Field(None, description="Internal notes")
    priority: str = Field("normal", pattern="^(normal|high|urgent)$", description="Job priority")
    currency: str = Field("USD", description="Currency code")


class JobCreateFromQuoteRequest(BaseModel):
    """Request to create a job from an accepted quote"""
    model_config = ConfigDict(from_attributes=True)
    
    quote_id: str = Field(..., description="ID of the accepted quote")
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled start time")
    duration_minutes: Optional[int] = Field(None, gt=0, description="Estimated duration in minutes")
    crew: Dict[str, Any] = Field(default_factory=dict, description="Crew assignment")
    crew_notes: Optional[str] = Field(None, description="Special crew instructions")
    internal_notes: Optional[str] = Field(None, description="Internal notes")


class JobUpdateRequest(BaseModel):
    """Request to update a job"""
    model_config = ConfigDict(from_attributes=True)
    
    scheduled_for: Optional[datetime] = Field(None, description="New scheduled time")
    duration_minutes: Optional[int] = Field(None, gt=0, description="New duration")
    crew: Optional[Dict[str, Any]] = Field(None, description="Updated crew assignment")
    crew_notes: Optional[str] = Field(None, description="Updated crew notes")
    status: Optional[str] = Field(None, pattern="^(scheduled|rescheduled|in_progress|completed|canceled)$", description="New status")
    completion_notes: Optional[str] = Field(None, description="Completion notes")
    completion_photos: Optional[List[str]] = Field(None, description="Media asset IDs for completion photos")
    customer_satisfaction: Optional[int] = Field(None, ge=1, le=5, description="Customer satisfaction rating (1-5)")
    actual_cost: Optional[float] = Field(None, gt=0, description="Actual job cost")
    internal_notes: Optional[str] = Field(None, description="Updated internal notes")
    priority: Optional[str] = Field(None, pattern="^(normal|high|urgent)$", description="Updated priority")


class JobRescheduleRequest(BaseModel):
    """Request to reschedule a job"""
    model_config = ConfigDict(from_attributes=True)
    
    new_scheduled_time: datetime = Field(..., description="New scheduled time")
    reason: Optional[str] = Field(None, description="Reason for rescheduling")


class JobResponse(BaseModel):
    """Job details response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    organization_id: str
    lead_id: Optional[str]
    quote_id: Optional[str]
    job_number: str
    service_type: str
    service_details: Dict[str, Any]
    address: str
    scheduled_for: Optional[str]
    duration_minutes: Optional[int]
    crew: Dict[str, Any]
    crew_notes: Optional[str]
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    canceled_at: Optional[str]
    completion_notes: Optional[str]
    completion_photos: List[str]
    customer_satisfaction: Optional[int]
    estimated_cost: float
    actual_cost: Optional[float]
    currency: str
    internal_notes: Optional[str]
    priority: str
    customer_name: Optional[str]
    customer_phone: Optional[str]
    customer_email: Optional[str]
    created_by_id: int
    updated_by_id: Optional[int]
    created_at: str
    updated_at: Optional[str]


class JobListResponse(BaseModel):
    """Paginated job list response"""
    model_config = ConfigDict(from_attributes=True)
    
    jobs: List[JobResponse]
    total_count: int
    has_more: bool


# API Endpoints

@router.post("", response_model=JobResponse)
async def create_job(
    request: JobCreateRequest,
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new job (direct creation or from quote/lead)
    
    Creates a job directly with provided details or converts an accepted quote into a scheduled job.
    Enforces organization boundaries and validates quote acceptance status.
    """
    try:
        job_service = get_job_service()
        
        # If creating from quote, validate quote ownership and status
        if request.quote_id:
            quote = db.query(Quote).filter(
                Quote.id == request.quote_id,
                Quote.organization_id == tenant_context.organization_id
            ).first()
            
            if not quote:
                raise HTTPException(
                    status_code=404,
                    detail="Quote not found or access denied"
                )
            
            if quote.status != "accepted":
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot create job from quote with status '{quote.status}'. Quote must be accepted."
                )
            
            # Create job from accepted quote
            job = job_service.create_job_from_quote(
                quote=quote,
                scheduled_for=request.scheduled_for,
                duration_minutes=request.duration_minutes,
                db=db,
                user_id=current_user.id,
                crew=request.crew,
                crew_notes=request.crew_notes,
                internal_notes=request.internal_notes
            )
        else:
            # Create job directly
            job_request = JobCreationRequest(
                organization_id=tenant_context.organization_id,
                service_type=request.service_type,
                address=request.address,
                estimated_cost=request.estimated_cost,
                customer_name=request.customer_name,
                customer_email=request.customer_email,
                customer_phone=request.customer_phone,
                quote_id=request.quote_id,
                lead_id=request.lead_id,
                scheduled_for=request.scheduled_for,
                duration_minutes=request.duration_minutes,
                service_details=request.service_details,
                crew=request.crew,
                crew_notes=request.crew_notes,
                internal_notes=request.internal_notes,
                priority=request.priority,
                currency=request.currency
            )
            
            job = job_service.create_job_direct(job_request, db, current_user.id)
        
        return JobResponse(**job.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/from-quote", response_model=JobResponse)
async def create_job_from_quote(
    request: JobCreateFromQuoteRequest,
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a job from an accepted quote
    
    Specialized endpoint for converting accepted quotes into scheduled jobs.
    Validates quote ownership and acceptance status before job creation.
    """
    try:
        # Get and validate quote
        quote = db.query(Quote).filter(
            Quote.id == request.quote_id,
            Quote.organization_id == tenant_context.organization_id
        ).first()
        
        if not quote:
            raise HTTPException(
                status_code=404,
                detail="Quote not found or access denied"
            )
        
        if quote.status != "accepted":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot create job from quote with status '{quote.status}'. Quote must be accepted."
            )
        
        # Create job from quote
        job_service = get_job_service()
        job = job_service.create_job_from_quote(
            quote=quote,
            scheduled_for=request.scheduled_for,
            duration_minutes=request.duration_minutes,
            db=db,
            user_id=current_user.id,
            crew=request.crew,
            crew_notes=request.crew_notes,
            internal_notes=request.internal_notes
        )
        
        return JobResponse(**job.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating job from quote: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str = Path(..., description="Job ID"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get job details by ID (org-scoped)
    """
    try:
        # Get job with org-scoping
        job = db.query(Job).filter(
            Job.id == job_id,
            Job.organization_id == tenant_context.organization_id
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail="Job not found or access denied"
            )
        
        return JobResponse(**job.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    request: JobUpdateRequest,
    job_id: str = Path(..., description="Job ID"),
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update job details (reschedule, status updates, crew assignment)
    
    Supports partial updates with validation for status transitions and job lifecycle management.
    """
    try:
        # Get job with org-scoping
        job = db.query(Job).filter(
            Job.id == job_id,
            Job.organization_id == tenant_context.organization_id
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail="Job not found or access denied"
            )
        
        # Update job
        job_service = get_job_service()
        update_request = JobUpdateRequest(
            scheduled_for=request.scheduled_for,
            duration_minutes=request.duration_minutes,
            crew=request.crew,
            crew_notes=request.crew_notes,
            status=request.status,
            completion_notes=request.completion_notes,
            completion_photos=request.completion_photos,
            customer_satisfaction=request.customer_satisfaction,
            actual_cost=request.actual_cost,
            internal_notes=request.internal_notes,
            priority=request.priority
        )
        
        updated_job = job_service.update_job(job, update_request, db, current_user.id)
        
        return JobResponse(**updated_job.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{job_id}/reschedule", response_model=JobResponse)
async def reschedule_job(
    request: JobRescheduleRequest,
    job_id: str = Path(..., description="Job ID"),
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Reschedule a job to a new time
    
    Updates the job's scheduled time with optional reason tracking.
    Only allows rescheduling of jobs in appropriate status states.
    """
    try:
        # Get job with org-scoping
        job = db.query(Job).filter(
            Job.id == job_id,
            Job.organization_id == tenant_context.organization_id
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail="Job not found or access denied"
            )
        
        # Reschedule job
        job_service = get_job_service()
        rescheduled_job = job_service.reschedule_job(
            job=job,
            new_scheduled_time=request.new_scheduled_time,
            reason=request.reason,
            db=db,
            user_id=current_user.id
        )
        
        return JobResponse(**rescheduled_job.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error rescheduling job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    scheduled_date: Optional[str] = Query(None, description="Filter by scheduled date (YYYY-MM-DD)"),
    customer_email: Optional[str] = Query(None, description="Filter by customer email"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    overdue_only: bool = Query(False, description="Show only overdue jobs"),
    limit: int = Query(50, ge=1, le=100, description="Number of jobs to return"),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List jobs for the organization with optional filtering
    
    Returns paginated list of jobs with support for filtering by status, date, customer, and priority.
    """
    try:
        # Build org-scoped query
        query = db.query(Job).filter(
            Job.organization_id == tenant_context.organization_id
        )
        
        # Apply filters
        if status:
            query = query.filter(Job.status == status)
        
        if scheduled_date:
            try:
                from datetime import date as date_type
                filter_date = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
                query = query.filter(
                    db.func.date(Job.scheduled_for) == filter_date
                )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD."
                )
        
        if customer_email:
            query = query.filter(Job.customer_email == customer_email)
        
        if priority:
            query = query.filter(Job.priority == priority)
        
        if overdue_only:
            current_time = datetime.now(timezone.utc)
            query = query.filter(
                Job.scheduled_for < current_time,
                Job.status.in_(["scheduled", "rescheduled", "in_progress"])
            )
        
        # Get total count before pagination
        total_count = query.count()
        
        # Get paginated results
        jobs = query.order_by(
            Job.scheduled_for.asc().nullslast(),
            Job.created_at.desc()
        ).offset(offset).limit(limit + 1).all()
        
        # Check if there are more results
        has_more = len(jobs) > limit
        if has_more:
            jobs = jobs[:limit]
        
        # Convert to response format
        job_responses = [JobResponse(**job.to_dict()) for job in jobs]
        
        return JobListResponse(
            jobs=job_responses,
            total_count=total_count,
            has_more=has_more
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats/dashboard")
async def get_job_stats(
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get job statistics for dashboard display
    
    Returns summary statistics about jobs for the organization.
    """
    try:
        # Get stats from database
        total_jobs = db.query(Job).filter(
            Job.organization_id == tenant_context.organization_id
        ).count()
        
        scheduled_jobs = db.query(Job).filter(
            Job.organization_id == tenant_context.organization_id,
            Job.status.in_(["scheduled", "rescheduled"])
        ).count()
        
        in_progress_jobs = db.query(Job).filter(
            Job.organization_id == tenant_context.organization_id,
            Job.status == "in_progress"
        ).count()
        
        completed_jobs = db.query(Job).filter(
            Job.organization_id == tenant_context.organization_id,
            Job.status == "completed"
        ).count()
        
        # Get overdue jobs
        current_time = datetime.now(timezone.utc)
        overdue_jobs = db.query(Job).filter(
            Job.organization_id == tenant_context.organization_id,
            Job.scheduled_for < current_time,
            Job.status.in_(["scheduled", "rescheduled", "in_progress"])
        ).count()
        
        # Get revenue stats
        total_estimated = db.query(db.func.sum(Job.estimated_cost)).filter(
            Job.organization_id == tenant_context.organization_id
        ).scalar() or 0
        
        total_actual = db.query(db.func.sum(Job.actual_cost)).filter(
            Job.organization_id == tenant_context.organization_id,
            Job.status == "completed"
        ).scalar() or 0
        
        return {
            "organization_id": tenant_context.organization_id,
            "total_jobs": total_jobs,
            "scheduled_jobs": scheduled_jobs,
            "in_progress_jobs": in_progress_jobs,
            "completed_jobs": completed_jobs,
            "overdue_jobs": overdue_jobs,
            "total_estimated_revenue": float(total_estimated),
            "total_actual_revenue": float(total_actual),
            "completion_rate": round((completed_jobs / total_jobs * 100) if total_jobs > 0 else 0, 1)
        }
        
    except Exception as e:
        logger.error(f"Error getting job stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")