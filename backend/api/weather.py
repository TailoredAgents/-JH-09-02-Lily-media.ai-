"""
PW-WEATHER-ADD-001: Weather API endpoints

Provides weather checking and rescheduling endpoints for job management.
Includes manual weather checks and admin-triggered rescheduling operations.
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.auth.dependencies import get_current_active_user
from backend.db.database import get_db
from backend.db.models import User, Job
from backend.middleware.tenant_context import get_tenant_context, TenantContext, require_role
from backend.services.weather_service import get_weather_service, WeatherForecast
from backend.services.job_rescheduler import get_job_rescheduler, RescheduleResult
from backend.services.settings_resolver import get_weather_settings, WeatherSettings
from backend.core.audit_logger import get_audit_logger, AuditEventType


router = APIRouter(prefix="/api/v1/weather", tags=["weather"])


# Request/Response Models

class WeatherCheckRequest(BaseModel):
    """Request for manual weather check"""
    job_id: str = Field(..., description="Job ID to check weather for")
    

class WeatherCheckResponse(BaseModel):
    """Response for weather check"""
    job_id: str
    job_scheduled_for: Optional[datetime]
    job_address: str
    weather_forecast: List[Dict[str, Any]]
    weather_risk_assessment: Dict[str, Any]
    reschedule_recommended: bool
    next_safe_date: Optional[datetime] = None


class RescheduleRunRequest(BaseModel):
    """Request to run rescheduling for organization"""
    organization_id: Optional[str] = Field(None, description="Organization ID (admin only)")
    force: bool = Field(False, description="Force rescheduling even if disabled")


class RescheduleRunResponse(BaseModel):
    """Response from rescheduling run"""
    organization_id: str
    total_jobs_checked: int
    jobs_rescheduled: int
    jobs_failed: int
    reschedule_results: List[Dict[str, Any]]


# Weather Check Endpoints

@router.get("/check", response_model=WeatherCheckResponse)
async def check_job_weather(
    job_id: str = Query(..., description="Job ID to check weather for"),
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    PW-WEATHER-ADD-001: Manual weather check for a specific job
    
    Checks weather forecast for a job's scheduled date and location,
    evaluates weather risk against configured thresholds, and provides
    rescheduling recommendations.
    """
    # Get the job with organization validation
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.organization_id == tenant_context.organization_id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or not accessible"
        )
    
    if not job.scheduled_for:
        raise HTTPException(
            status_code=400,
            detail="Job does not have a scheduled date"
        )
    
    # Get organization weather settings
    weather_settings = get_weather_settings(
        db=db,
        org_id=tenant_context.organization_id
    )
    
    if not isinstance(weather_settings, WeatherSettings):
        raise HTTPException(
            status_code=500,
            detail="Weather settings not configured for organization"
        )
    
    # Get weather service and fetch forecast
    weather_service = get_weather_service()
    
    # Geocode job address (using mock coordinates for now)
    latitude, longitude = 33.7490, -84.3880  # Atlanta, GA
    
    try:
        forecasts = await weather_service.get_forecast(
            latitude=latitude,
            longitude=longitude,
            date_range=weather_settings.lookahead_days
        )
        
        # Evaluate weather risk
        risk_assessment = weather_service.evaluate_weather_risk(
            forecasts=forecasts,
            threshold=weather_settings.bad_weather_threshold
        )
        
        # Convert forecasts to dict format for JSON response
        forecast_data = []
        for forecast in forecasts:
            forecast_data.append({
                "date": forecast.date.isoformat(),
                "temperature_high_f": forecast.temperature_high_f,
                "temperature_low_f": forecast.temperature_low_f,
                "rain_probability": forecast.rain_probability,
                "wind_speed_mph": forecast.wind_speed_mph,
                "condition": forecast.condition,
                "is_bad_weather": forecast.is_bad_weather(weather_settings.bad_weather_threshold)
            })
        
        # Log audit event for manual weather check
        audit_logger = get_audit_logger()
        await audit_logger.log_event(
            event_type=AuditEventType.JOB_UPDATED,  # Using existing event type
            entity_id=job.id,
            entity_type="job",
            organization_id=tenant_context.organization_id,
            user_id=current_user.id,
            details={
                "action": "manual_weather_check",
                "weather_risk": risk_assessment["overall_risk"],
                "next_safe_day": risk_assessment.get("next_safe_day")
            }
        )
        
        return WeatherCheckResponse(
            job_id=job.id,
            job_scheduled_for=job.scheduled_for,
            job_address=job.address,
            weather_forecast=forecast_data,
            weather_risk_assessment=risk_assessment,
            reschedule_recommended=risk_assessment["overall_risk"],
            next_safe_date=risk_assessment.get("next_safe_day")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check weather: {str(e)}"
        )


# Rescheduling Endpoints

@router.post("/run", response_model=RescheduleRunResponse)
async def run_weather_rescheduling(
    request: RescheduleRunRequest,
    background_tasks: BackgroundTasks,
    tenant_context: TenantContext = Depends(require_role("admin")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    PW-WEATHER-ADD-001: Admin trigger for weather-based rescheduling
    
    Manually triggers the weather rescheduling process for an organization.
    Admin users can force rescheduling even if auto-reschedule is disabled.
    """
    # Determine organization ID
    target_org_id = request.organization_id or tenant_context.organization_id
    
    # Validate organization access (admin can access any org)
    if target_org_id != tenant_context.organization_id and not tenant_context.is_super_admin:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to reschedule jobs for this organization"
        )
    
    # Get weather settings
    weather_settings = get_weather_settings(
        db=db,
        org_id=target_org_id
    )
    
    if not isinstance(weather_settings, WeatherSettings):
        raise HTTPException(
            status_code=400,
            detail="Weather settings not configured for organization"
        )
    
    # Check if rescheduling is enabled (unless forced)
    if not request.force and not weather_settings.auto_reschedule:
        raise HTTPException(
            status_code=400,
            detail="Automatic rescheduling is disabled. Use 'force=true' to override."
        )
    
    try:
        # Run rescheduling
        job_rescheduler = get_job_rescheduler()
        reschedule_results = await job_rescheduler.run_rescheduling_check(
            organization_id=target_org_id,
            db=db,
            user_id=current_user.id
        )
        
        # Process results
        total_checked = len(reschedule_results)
        successful_reschedules = sum(1 for r in reschedule_results if r.success)
        failed_reschedules = total_checked - successful_reschedules
        
        # Convert results to dict format
        result_data = []
        for result in reschedule_results:
            result_data.append({
                "job_id": result.job_id,
                "original_date": result.original_date.isoformat() if result.original_date else None,
                "new_date": result.new_date.isoformat() if result.new_date else None,
                "reschedule_reason": result.reschedule_reason,
                "success": result.success,
                "error_message": result.error_message
            })
        
        # Log audit event for admin-triggered rescheduling
        audit_logger = get_audit_logger()
        await audit_logger.log_event(
            event_type=AuditEventType.JOB_RESCHEDULED,
            entity_id=target_org_id,
            entity_type="organization",
            organization_id=target_org_id,
            user_id=current_user.id,
            details={
                "action": "admin_triggered_weather_rescheduling",
                "total_jobs_checked": total_checked,
                "jobs_rescheduled": successful_reschedules,
                "jobs_failed": failed_reschedules,
                "forced": request.force
            }
        )
        
        return RescheduleRunResponse(
            organization_id=target_org_id,
            total_jobs_checked=total_checked,
            jobs_rescheduled=successful_reschedules,
            jobs_failed=failed_reschedules,
            reschedule_results=result_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run rescheduling: {str(e)}"
        )


@router.post("/reschedule/job/{job_id}")
async def reschedule_single_job(
    job_id: str,
    tenant_context: TenantContext = Depends(require_role("member")),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    PW-WEATHER-ADD-001: Reschedule a single job based on weather
    
    Checks weather for a specific job and reschedules it if weather
    conditions exceed configured thresholds.
    """
    # Validate job exists and user has access
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.organization_id == tenant_context.organization_id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or not accessible"
        )
    
    if job.status != "scheduled":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not in scheduled status (current: {job.status})"
        )
    
    try:
        # Run single job rescheduling check
        job_rescheduler = get_job_rescheduler()
        result = await job_rescheduler.check_single_job(
            job_id=job_id,
            db=db,
            user_id=current_user.id
        )
        
        if not result:
            return {
                "job_id": job_id,
                "action_taken": "none",
                "reason": "No rescheduling needed - weather conditions are acceptable"
            }
        
        return {
            "job_id": result.job_id,
            "action_taken": "rescheduled" if result.success else "failed",
            "original_date": result.original_date.isoformat() if result.original_date else None,
            "new_date": result.new_date.isoformat() if result.new_date else None,
            "reschedule_reason": result.reschedule_reason,
            "success": result.success,
            "error_message": result.error_message
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reschedule job: {str(e)}"
        )


# Background task for scheduled rescheduling (would be called by cron/scheduler)
async def scheduled_weather_rescheduling_task(organization_id: str, db: Session):
    """
    Background task for scheduled weather rescheduling
    
    This would be called by a cron job or task scheduler to run
    automatic rescheduling at regular intervals.
    """
    try:
        job_rescheduler = get_job_rescheduler()
        results = await job_rescheduler.run_rescheduling_check(
            organization_id=organization_id,
            db=db,
            user_id=None  # System user for automated tasks
        )
        
        # Log results for monitoring
        successful_reschedules = sum(1 for r in results if r.success)
        
        if successful_reschedules > 0:
            audit_logger = get_audit_logger()
            await audit_logger.log_event(
                event_type=AuditEventType.JOB_RESCHEDULED,
                entity_id=organization_id,
                entity_type="organization",
                organization_id=organization_id,
                user_id=None,
                details={
                    "action": "scheduled_weather_rescheduling",
                    "total_jobs_checked": len(results),
                    "jobs_rescheduled": successful_reschedules,
                    "automated": True
                }
            )
        
    except Exception as e:
        # Log error but don't raise to avoid breaking the scheduler
        print(f"Scheduled weather rescheduling failed for org {organization_id}: {e}")


# Status/Info Endpoints

@router.get("/status")
async def get_weather_service_status(
    tenant_context: TenantContext = Depends(require_role("member"))
):
    """Get weather service status and configuration"""
    weather_service = get_weather_service()
    
    return {
        "weather_provider": type(weather_service.provider).__name__,
        "provider_configured": weather_service.provider.validate_config(),
        "service_available": True
    }