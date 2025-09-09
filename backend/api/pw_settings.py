"""
PW-SETTINGS-ADD-001: Pressure Washing Settings API
Provides tenant-configurable settings endpoints for pricing, weather, DM, and scheduling namespaces
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator, ConfigDict
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User, Organization, Team, UserSetting
from backend.db.multi_tenant_models import Organization as MTOrganization, Team as MTTeam
from backend.auth.dependencies import get_current_active_user
from backend.middleware.tenant_context import get_tenant_context, TenantContext
from backend.services.settings_resolver import (
    SettingsResolver,
    SettingsNamespace,
    PricingSettings,
    WeatherSettings,
    DMSettings,
    SchedulingSettings,
    SurfaceType,
    WeatherSeverity,
    create_settings_resolver
)
from backend.core.audit_logger import log_settings_event, AuditEventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pw-settings", tags=["pressure-washing-settings"])

# Enhanced Request/Response Models for API

class PricingSettingsRequest(BaseModel):
    """API request model for pricing settings with enhanced validation"""
    
    # Base pricing per square foot by surface type
    base_rates: Optional[Dict[str, float]] = Field(
        None,
        description="Pricing per square foot by surface type",
        example={
            "concrete": 0.15,
            "brick": 0.18,
            "vinyl_siding": 0.20,
            "wood_deck": 0.25,
            "roof": 0.30,
            "driveway": 0.12,
            "patio": 0.15,
            "fence": 0.22
        }
    )
    
    minimum_job_price: Optional[float] = Field(
        None,
        ge=50.0,
        le=1000.0,
        description="Minimum price for any job ($50-$1000)"
    )
    
    # Additional services pricing
    soft_wash_multiplier: Optional[float] = Field(
        None,
        ge=1.0,
        le=3.0,
        description="Price multiplier for soft wash services (1.0-3.0x)"
    )
    
    gutter_cleaning_rate: Optional[float] = Field(
        None,
        ge=0.50,
        le=5.0,
        description="Price per linear foot for gutter cleaning ($0.50-$5.00)"
    )
    
    # Seasonal pricing modifiers
    seasonal_multipliers: Optional[Dict[str, float]] = Field(
        None,
        description="Seasonal pricing multipliers by season",
        example={
            "spring": 1.2,
            "summer": 1.0,
            "fall": 1.1,
            "winter": 0.8
        }
    )
    
    # Bundle discounts
    multi_service_discount: Optional[float] = Field(
        None,
        ge=0.0,
        le=0.5,
        description="Discount for multiple services (0-50%)"
    )
    
    # Travel charges
    travel_rate_per_mile: Optional[float] = Field(
        None,
        ge=0.0,
        le=10.0,
        description="Travel charge per mile beyond free radius ($0-$10)"
    )
    
    free_travel_radius_miles: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Free travel radius in miles (0-100)"
    )
    
    @validator('base_rates')
    def validate_base_rates(cls, v):
        if v is not None:
            # Validate surface types and positive rates
            valid_surfaces = {e.value for e in SurfaceType}
            for surface, rate in v.items():
                if surface not in valid_surfaces:
                    raise ValueError(f"Invalid surface type: {surface}. Valid types: {list(valid_surfaces)}")
                if rate <= 0:
                    raise ValueError(f"Base rate for {surface} must be positive")
        return v
    
    @validator('seasonal_multipliers')
    def validate_seasonal_multipliers(cls, v):
        if v is not None:
            required_seasons = {"spring", "summer", "fall", "winter"}
            provided_seasons = set(v.keys())
            if not required_seasons.issubset(provided_seasons):
                missing = required_seasons - provided_seasons
                raise ValueError(f"Missing required seasons: {list(missing)}")
            for season, multiplier in v.items():
                if multiplier <= 0:
                    raise ValueError(f"Seasonal multiplier for {season} must be positive")
        return v


class WeatherSettingsRequest(BaseModel):
    """API request model for weather settings with enhanced validation"""
    
    # Rain delay thresholds
    rain_delay_threshold_inches: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="Rain threshold in inches to trigger delay (0-2.0)"
    )
    
    # Wind speed limits by service type
    max_wind_speed_roof: Optional[float] = Field(
        None,
        ge=5.0,
        le=50.0,
        description="Maximum wind speed for roof work in mph (5-50)"
    )
    
    max_wind_speed_general: Optional[float] = Field(
        None,
        ge=10.0,
        le=60.0,
        description="Maximum wind speed for general work in mph (10-60)"
    )
    
    # Temperature limits
    min_temperature_f: Optional[float] = Field(
        None,
        ge=-10.0,
        le=80.0,
        description="Minimum temperature for pressure washing (-10°F to 80°F)"
    )
    
    max_temperature_f: Optional[float] = Field(
        None,
        ge=60.0,
        le=120.0,
        description="Maximum temperature for safe work (60°F to 120°F)"
    )
    
    # Automatic rescheduling
    auto_reschedule_enabled: Optional[bool] = Field(
        None,
        description="Automatically reschedule jobs due to weather"
    )
    
    advance_notice_hours: Optional[int] = Field(
        None,
        ge=4,
        le=168,
        description="Hours in advance to check weather and notify (4-168)"
    )
    
    # Weather severity handling
    weather_severity_actions: Optional[Dict[str, str]] = Field(
        None,
        description="Actions to take based on weather severity",
        example={
            "light": "proceed",
            "moderate": "reschedule", 
            "severe": "cancel_day"
        }
    )
    
    @validator('weather_severity_actions')
    def validate_severity_actions(cls, v):
        if v is not None:
            valid_severities = {e.value for e in WeatherSeverity}
            valid_actions = {"proceed", "reschedule", "cancel_day"}
            for severity, action in v.items():
                if severity not in valid_severities:
                    raise ValueError(f"Invalid weather severity: {severity}. Valid: {list(valid_severities)}")
                if action not in valid_actions:
                    raise ValueError(f"Invalid action: {action}. Valid: {list(valid_actions)}")
        return v


class DMSettingsRequest(BaseModel):
    """API request model for DM/booking settings with enhanced validation"""
    
    # Auto-response settings
    auto_response_enabled: Optional[bool] = Field(
        None,
        description="Enable automatic responses to pricing inquiries"
    )
    
    response_delay_minutes: Optional[int] = Field(
        None,
        ge=0,
        le=60,
        description="Delay before auto-responding in minutes (0-60)"
    )
    
    # Photo collection
    require_photos_for_quote: Optional[bool] = Field(
        None,
        description="Require photos before providing quotes"
    )
    
    max_photos_per_inquiry: Optional[int] = Field(
        None,
        ge=1,
        le=20,
        description="Maximum photos per inquiry (1-20)"
    )
    
    # Quote generation
    provide_ballpark_estimates: Optional[bool] = Field(
        None,
        description="Provide ballpark estimates before site visit"
    )
    
    ballpark_accuracy_margin: Optional[float] = Field(
        None,
        ge=0.1,
        le=1.0,
        description="Ballpark estimate accuracy margin (10%-100%)"
    )
    
    # Lead qualification
    qualification_questions: Optional[List[str]] = Field(
        None,
        max_items=10,
        description="Questions to qualify leads (max 10)",
        example=[
            "What type of surface needs cleaning?",
            "Approximate square footage?",
            "When would you like the work completed?",
            "What's your preferred contact method?"
        ]
    )
    
    auto_qualify_threshold: Optional[float] = Field(
        None,
        ge=0.5,
        le=1.0,
        description="AI confidence threshold for auto-qualification (50%-100%)"
    )
    
    # Booking conversion
    booking_link_in_response: Optional[bool] = Field(
        None,
        description="Include booking link in responses"
    )
    
    follow_up_after_hours: Optional[int] = Field(
        None,
        ge=1,
        le=168,
        description="Hours to wait before follow-up (1-168)"
    )
    
    # Quiet hours for auto-responses
    quiet_hours: Optional[Dict[str, str]] = Field(
        None,
        description="Hours to avoid auto-responses",
        example={
            "start": "22:00",
            "end": "08:00"
        }
    )
    
    @validator('qualification_questions')
    def validate_questions(cls, v):
        if v is not None:
            for question in v:
                if not question.strip():
                    raise ValueError("Qualification questions cannot be empty")
                if len(question) > 200:
                    raise ValueError("Qualification questions must be under 200 characters")
        return v
    
    @validator('quiet_hours')
    def validate_quiet_hours(cls, v):
        if v is not None:
            if 'start' not in v or 'end' not in v:
                raise ValueError("Quiet hours must include 'start' and 'end' times")
            # Validate time format (HH:MM)
            import re
            time_pattern = r'^([01]\d|2[0-3]):[0-5]\d$'
            for key, time_val in v.items():
                if not re.match(time_pattern, time_val):
                    raise ValueError(f"Invalid time format for {key}: {time_val}. Use HH:MM format")
        return v


class SchedulingSettingsRequest(BaseModel):
    """API request model for scheduling settings with enhanced validation"""
    
    # Working hours
    business_hours_start: Optional[str] = Field(
        None,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="Business hours start time (HH:MM format)"
    )
    
    business_hours_end: Optional[str] = Field(
        None,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="Business hours end time (HH:MM format)"
    )
    
    working_days: Optional[List[str]] = Field(
        None,
        max_items=7,
        description="Working days of the week",
        example=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    )
    
    # Job scheduling
    default_job_duration_hours: Optional[float] = Field(
        None,
        ge=0.5,
        le=12.0,
        description="Default job duration in hours (0.5-12.0)"
    )
    
    buffer_time_minutes: Optional[int] = Field(
        None,
        ge=0,
        le=120,
        description="Buffer time between jobs in minutes (0-120)"
    )
    
    # Advance booking
    min_advance_booking_hours: Optional[int] = Field(
        None,
        ge=2,
        le=720,
        description="Minimum hours in advance for booking (2-720)"
    )
    
    max_advance_booking_days: Optional[int] = Field(
        None,
        ge=7,
        le=365,
        description="Maximum days in advance for booking (7-365)"
    )
    
    # Emergency/rush jobs
    allow_rush_jobs: Optional[bool] = Field(
        None,
        description="Allow emergency/rush job booking"
    )
    
    rush_job_multiplier: Optional[float] = Field(
        None,
        ge=1.0,
        le=3.0,
        description="Price multiplier for rush jobs (1.0-3.0x)"
    )
    
    # Capacity management
    max_jobs_per_day: Optional[int] = Field(
        None,
        ge=1,
        le=20,
        description="Maximum jobs per day (1-20)"
    )
    
    @validator('working_days')
    def validate_working_days(cls, v):
        if v is not None:
            valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
            for day in v:
                if day.lower() not in valid_days:
                    raise ValueError(f"Invalid working day: {day}. Valid: {list(valid_days)}")
        return [day.lower() for day in v] if v else v


# Response Models

class SettingsResponseBase(BaseModel):
    """Base response model for settings"""
    namespace: str
    organization_id: str
    last_updated: datetime
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class PricingSettingsResponse(SettingsResponseBase):
    """Response model for pricing settings"""
    namespace: str = "pricing"
    settings: PricingSettings


class WeatherSettingsResponse(SettingsResponseBase):
    """Response model for weather settings"""
    namespace: str = "weather"
    settings: WeatherSettings


class DMSettingsResponse(SettingsResponseBase):
    """Response model for DM settings"""
    namespace: str = "dm"
    settings: DMSettings


class SchedulingSettingsResponse(SettingsResponseBase):
    """Response model for scheduling settings"""
    namespace: str = "scheduling"
    settings: SchedulingSettings


class AllSettingsResponse(BaseModel):
    """Response model for all namespaces"""
    organization_id: str
    pricing: PricingSettings
    weather: WeatherSettings
    dm: DMSettings
    scheduling: SchedulingSettings
    last_updated: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SettingsUpdateResponse(BaseModel):
    """Response model for settings updates"""
    success: bool
    namespace: str
    organization_id: str
    changes_applied: Dict[str, Any]
    validation_errors: List[str] = []
    cache_invalidated: bool = True
    audit_logged: bool = True


# Dependencies

def get_settings_resolver(db: Session = Depends(get_db)) -> SettingsResolver:
    """Get settings resolver instance"""
    return create_settings_resolver(db)


async def log_settings_audit(
    namespace: str,
    action: str,
    tenant_context: TenantContext,
    changes: Dict[str, Any],
    db: Session
):
    """Log settings changes for audit trail"""
    try:
        await log_settings_event(
            event_type=AuditEventType.SETTINGS_UPDATED,
            user_id=int(tenant_context.user.user_id),
            organization_id=tenant_context.organization_id,
            details={
                "namespace": namespace,
                "action": action,
                "changes": changes,
                "role": tenant_context.role
            },
            db=db
        )
    except Exception as e:
        logger.error(f"Failed to log settings audit: {e}")


# GET Endpoints - Retrieve Settings

@router.get("/", response_model=AllSettingsResponse)
async def get_all_settings(
    tenant_context: TenantContext = Depends(get_tenant_context),
    resolver: SettingsResolver = Depends(get_settings_resolver)
):
    """Get all pressure washing settings for the organization"""
    try:
        settings = resolver.get_settings(
            org_id=str(tenant_context.organization_id),
            user_id=int(tenant_context.user.user_id)
        )
        
        return AllSettingsResponse(
            organization_id=str(tenant_context.organization_id),
            pricing=settings.pricing,
            weather=settings.weather,
            dm=settings.dm,
            scheduling=settings.scheduling,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get all settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve settings"
        )


@router.get("/pricing", response_model=PricingSettingsResponse)
async def get_pricing_settings(
    tenant_context: TenantContext = Depends(get_tenant_context),
    resolver: SettingsResolver = Depends(get_settings_resolver)
):
    """Get pricing settings for the organization"""
    try:
        settings = resolver.get_namespace_settings(
            org_id=str(tenant_context.organization_id),
            namespace=SettingsNamespace.PRICING,
            user_id=int(tenant_context.user.user_id)
        )
        
        return PricingSettingsResponse(
            organization_id=str(tenant_context.organization_id),
            settings=settings,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get pricing settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pricing settings"
        )


@router.get("/weather", response_model=WeatherSettingsResponse)
async def get_weather_settings(
    tenant_context: TenantContext = Depends(get_tenant_context),
    resolver: SettingsResolver = Depends(get_settings_resolver)
):
    """Get weather settings for the organization"""
    try:
        settings = resolver.get_namespace_settings(
            org_id=str(tenant_context.organization_id),
            namespace=SettingsNamespace.WEATHER,
            user_id=int(tenant_context.user.user_id)
        )
        
        return WeatherSettingsResponse(
            organization_id=str(tenant_context.organization_id),
            settings=settings,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get weather settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve weather settings"
        )


@router.get("/dm", response_model=DMSettingsResponse)
async def get_dm_settings(
    tenant_context: TenantContext = Depends(get_tenant_context),
    resolver: SettingsResolver = Depends(get_settings_resolver)
):
    """Get DM/booking settings for the organization"""
    try:
        settings = resolver.get_namespace_settings(
            org_id=str(tenant_context.organization_id),
            namespace=SettingsNamespace.DM,
            user_id=int(tenant_context.user.user_id)
        )
        
        return DMSettingsResponse(
            organization_id=str(tenant_context.organization_id),
            settings=settings,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get DM settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve DM settings"
        )


@router.get("/scheduling", response_model=SchedulingSettingsResponse)
async def get_scheduling_settings(
    tenant_context: TenantContext = Depends(get_tenant_context),
    resolver: SettingsResolver = Depends(get_settings_resolver)
):
    """Get scheduling settings for the organization"""
    try:
        settings = resolver.get_namespace_settings(
            org_id=str(tenant_context.organization_id),
            namespace=SettingsNamespace.SCHEDULING,
            user_id=int(tenant_context.user.user_id)
        )
        
        return SchedulingSettingsResponse(
            organization_id=str(tenant_context.organization_id),
            settings=settings,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get scheduling settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scheduling settings"
        )


# PUT Endpoints - Update Settings

@router.put("/pricing", response_model=SettingsUpdateResponse)
async def update_pricing_settings(
    request: PricingSettingsRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    resolver: SettingsResolver = Depends(get_settings_resolver),
    db: Session = Depends(get_db)
):
    """Update pricing settings for the organization"""
    try:
        # Get current organization settings
        org = db.query(MTOrganization).filter(MTOrganization.id == str(tenant_context.organization_id)).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Prepare update data (only include non-None values)
        update_data = request.dict(exclude_unset=True, exclude_none=True)
        
        # Get current settings or initialize empty
        current_settings = org.settings or {}
        pricing_settings = current_settings.get("pricing", {})
        
        # Apply updates
        pricing_settings.update(update_data)
        current_settings["pricing"] = pricing_settings
        
        # Update organization settings
        org.settings = current_settings
        db.commit()
        
        # Invalidate cache
        resolver.invalidate_cache(str(tenant_context.organization_id))
        
        # Log audit trail
        await log_settings_audit(
            namespace="pricing",
            action="update",
            tenant_context=tenant_context,
            changes=update_data,
            db=db
        )
        
        return SettingsUpdateResponse(
            success=True,
            namespace="pricing",
            organization_id=str(tenant_context.organization_id),
            changes_applied=update_data,
            cache_invalidated=True,
            audit_logged=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update pricing settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update pricing settings"
        )


@router.put("/weather", response_model=SettingsUpdateResponse)
async def update_weather_settings(
    request: WeatherSettingsRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    resolver: SettingsResolver = Depends(get_settings_resolver),
    db: Session = Depends(get_db)
):
    """Update weather settings for the organization"""
    try:
        # Get current organization settings
        org = db.query(MTOrganization).filter(MTOrganization.id == str(tenant_context.organization_id)).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Prepare update data
        update_data = request.dict(exclude_unset=True, exclude_none=True)
        
        # Get current settings or initialize empty
        current_settings = org.settings or {}
        weather_settings = current_settings.get("weather", {})
        
        # Apply updates
        weather_settings.update(update_data)
        current_settings["weather"] = weather_settings
        
        # Update organization settings
        org.settings = current_settings
        db.commit()
        
        # Invalidate cache
        resolver.invalidate_cache(str(tenant_context.organization_id))
        
        # Log audit trail
        await log_settings_audit(
            namespace="weather",
            action="update",
            tenant_context=tenant_context,
            changes=update_data,
            db=db
        )
        
        return SettingsUpdateResponse(
            success=True,
            namespace="weather",
            organization_id=str(tenant_context.organization_id),
            changes_applied=update_data,
            cache_invalidated=True,
            audit_logged=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update weather settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update weather settings"
        )


@router.put("/dm", response_model=SettingsUpdateResponse)
async def update_dm_settings(
    request: DMSettingsRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    resolver: SettingsResolver = Depends(get_settings_resolver),
    db: Session = Depends(get_db)
):
    """Update DM/booking settings for the organization"""
    try:
        # Get current organization settings
        org = db.query(MTOrganization).filter(MTOrganization.id == str(tenant_context.organization_id)).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Prepare update data
        update_data = request.dict(exclude_unset=True, exclude_none=True)
        
        # Get current settings or initialize empty
        current_settings = org.settings or {}
        dm_settings = current_settings.get("dm", {})
        
        # Apply updates
        dm_settings.update(update_data)
        current_settings["dm"] = dm_settings
        
        # Update organization settings
        org.settings = current_settings
        db.commit()
        
        # Invalidate cache
        resolver.invalidate_cache(str(tenant_context.organization_id))
        
        # Log audit trail
        await log_settings_audit(
            namespace="dm",
            action="update",
            tenant_context=tenant_context,
            changes=update_data,
            db=db
        )
        
        return SettingsUpdateResponse(
            success=True,
            namespace="dm",
            organization_id=str(tenant_context.organization_id),
            changes_applied=update_data,
            cache_invalidated=True,
            audit_logged=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update DM settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update DM settings"
        )


@router.put("/scheduling", response_model=SettingsUpdateResponse)
async def update_scheduling_settings(
    request: SchedulingSettingsRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    resolver: SettingsResolver = Depends(get_settings_resolver),
    db: Session = Depends(get_db)
):
    """Update scheduling settings for the organization"""
    try:
        # Get current organization settings
        org = db.query(MTOrganization).filter(MTOrganization.id == str(tenant_context.organization_id)).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Prepare update data
        update_data = request.dict(exclude_unset=True, exclude_none=True)
        
        # Get current settings or initialize empty
        current_settings = org.settings or {}
        scheduling_settings = current_settings.get("scheduling", {})
        
        # Apply updates
        scheduling_settings.update(update_data)
        current_settings["scheduling"] = scheduling_settings
        
        # Update organization settings
        org.settings = current_settings
        db.commit()
        
        # Invalidate cache
        resolver.invalidate_cache(str(tenant_context.organization_id))
        
        # Log audit trail
        await log_settings_audit(
            namespace="scheduling",
            action="update",
            tenant_context=tenant_context,
            changes=update_data,
            db=db
        )
        
        return SettingsUpdateResponse(
            success=True,
            namespace="scheduling",
            organization_id=str(tenant_context.organization_id),
            changes_applied=update_data,
            cache_invalidated=True,
            audit_logged=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update scheduling settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update scheduling settings"
        )


# Utility Endpoints

@router.get("/defaults")
async def get_default_settings():
    """Get default settings for all namespaces (for reference/new organizations)"""
    try:
        from backend.services.settings_resolver import PWSettings
        defaults = PWSettings()
        
        return {
            "pricing": defaults.pricing.dict(),
            "weather": defaults.weather.dict(),
            "dm": defaults.dm.dict(),
            "scheduling": defaults.scheduling.dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to get default settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve default settings"
        )


@router.post("/cache/invalidate")
async def invalidate_settings_cache(
    tenant_context: TenantContext = Depends(get_tenant_context),
    resolver: SettingsResolver = Depends(get_settings_resolver)
):
    """Manually invalidate settings cache for the organization"""
    try:
        resolver.invalidate_cache(str(tenant_context.organization_id))
        
        return {
            "success": True,
            "message": f"Settings cache invalidated for organization {tenant_context.organization_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invalidate settings cache"
        )


@router.get("/schema/{namespace}")
async def get_settings_schema(namespace: str):
    """Get JSON schema for a specific settings namespace"""
    try:
        if namespace == "pricing":
            schema = PricingSettingsRequest.model_json_schema()
        elif namespace == "weather":
            schema = WeatherSettingsRequest.model_json_schema()
        elif namespace == "dm":
            schema = DMSettingsRequest.model_json_schema()
        elif namespace == "scheduling":
            schema = SchedulingSettingsRequest.model_json_schema()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown namespace: {namespace}"
            )
        
        return {
            "namespace": namespace,
            "schema": schema
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schema for {namespace}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve settings schema"
        )