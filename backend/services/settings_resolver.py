"""
PW-SETTINGS-REPLACE-001: Central typed settings resolver for pressure washing platform

Provides tenant-configurable settings with typed validation and merge hierarchy:
plan -> organization -> team -> integration -> user (last writer wins)

Supports namespaces: pricing.*, weather.*, dm.*, scheduling.*
"""

import json
import hashlib
from typing import Dict, Any, Optional, Union, List, TypeVar, Generic
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field, validator, ConfigDict
from sqlalchemy.orm import Session
try:
    import redis
    REDIS_AVAILABLE = True
    # Create a simple Redis client for settings caching
    redis_client = redis.from_url(
        "redis://localhost:6379/0", 
        encoding='utf-8', 
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
except ImportError:
    REDIS_AVAILABLE = False
    redis_client = None
try:
    from backend.db.models import Plan, Organization, Team, UserSetting, User
    from backend.db.multi_tenant_models import Organization, Team
except ImportError:
    # Fallback for testing
    from db.models import Plan, UserSetting, User
    from db.multi_tenant_models import Organization, Team
import logging

logger = logging.getLogger(__name__)

# Type definitions
T = TypeVar('T', bound=BaseModel)

class SettingsNamespace(str, Enum):
    """Supported settings namespaces"""
    PRICING = "pricing"
    WEATHER = "weather"
    DM = "dm"
    SCHEDULING = "scheduling"

class SurfaceType(str, Enum):
    """Supported surface types for pricing"""
    CONCRETE = "concrete"
    BRICK = "brick"
    VINYL_SIDING = "vinyl_siding"
    WOOD_DECK = "wood_deck"
    ROOF = "roof"
    DRIVEWAY = "driveway"
    PATIO = "patio"
    FENCE = "fence"

class WeatherSeverity(str, Enum):
    """Weather severity levels"""
    LIGHT = "light"
    MODERATE = "moderate"
    SEVERE = "severe"

class BookingStatus(str, Enum):
    """DM booking workflow statuses"""
    INQUIRY = "inquiry"
    QUALIFIED = "qualified"
    QUOTED = "quoted"
    BOOKED = "booked"
    CANCELLED = "cancelled"

# Pydantic Settings Models

class PricingSettings(BaseModel):
    """Pricing configuration for pressure washing services"""
    model_config = ConfigDict(extra="forbid")
    
    # Base pricing per square foot by surface type
    base_rates: Dict[SurfaceType, float] = Field(
        default={
            SurfaceType.CONCRETE: 0.15,
            SurfaceType.BRICK: 0.18,
            SurfaceType.VINYL_SIDING: 0.20,
            SurfaceType.WOOD_DECK: 0.25,
            SurfaceType.ROOF: 0.30,
            SurfaceType.DRIVEWAY: 0.12,
            SurfaceType.PATIO: 0.15,
            SurfaceType.FENCE: 0.22
        },
        description="Base pricing per square foot by surface type"
    )
    
    # Minimum job pricing
    minimum_job_price: float = Field(
        default=150.0,
        ge=50.0,
        le=1000.0,
        description="Minimum price for any job"
    )
    
    # Additional services pricing
    soft_wash_multiplier: float = Field(
        default=1.3,
        ge=1.0,
        le=3.0,
        description="Multiplier for soft wash services"
    )
    
    gutter_cleaning_rate: float = Field(
        default=1.50,
        ge=0.50,
        le=5.0,
        description="Price per linear foot for gutter cleaning"
    )
    
    # Seasonal pricing modifiers
    seasonal_multipliers: Dict[str, float] = Field(
        default={
            "spring": 1.2,  # High demand
            "summer": 1.0,  # Normal pricing
            "fall": 1.1,    # Moderate demand
            "winter": 0.8   # Lower demand
        },
        description="Seasonal pricing multipliers by season"
    )
    
    # Bundle discounts
    multi_service_discount: float = Field(
        default=0.10,
        ge=0.0,
        le=0.5,
        description="Discount for multiple services (10% default)"
    )
    
    # Travel charges
    travel_rate_per_mile: float = Field(
        default=2.0,
        ge=0.0,
        le=10.0,
        description="Travel charge per mile beyond free radius"
    )
    
    free_travel_radius_miles: float = Field(
        default=15.0,
        ge=0.0,
        le=100.0,
        description="Free travel radius in miles"
    )
    
    @validator('base_rates')
    def validate_base_rates(cls, v):
        """Ensure all surface types have positive rates"""
        for surface, rate in v.items():
            if rate <= 0:
                raise ValueError(f"Base rate for {surface} must be positive")
        return v

    @validator('seasonal_multipliers')
    def validate_seasonal_multipliers(cls, v):
        """Ensure all seasonal multipliers are positive"""
        required_seasons = {"spring", "summer", "fall", "winter"}
        if set(v.keys()) != required_seasons:
            raise ValueError(f"Must include all seasons: {required_seasons}")
        for season, multiplier in v.items():
            if multiplier <= 0:
                raise ValueError(f"Seasonal multiplier for {season} must be positive")
        return v


class WeatherSettings(BaseModel):
    """Weather-aware scheduling configuration"""
    model_config = ConfigDict(extra="forbid")
    
    # Rain delay thresholds
    rain_delay_threshold_inches: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Rain threshold in inches to trigger delay"
    )
    
    # Wind speed limits by service type
    max_wind_speed_roof: float = Field(
        default=15.0,
        ge=5.0,
        le=50.0,
        description="Maximum wind speed for roof work (mph)"
    )
    
    max_wind_speed_general: float = Field(
        default=25.0,
        ge=10.0,
        le=60.0,
        description="Maximum wind speed for general work (mph)"
    )
    
    # Temperature limits
    min_temperature_f: float = Field(
        default=35.0,
        ge=-10.0,
        le=80.0,
        description="Minimum temperature for pressure washing"
    )
    
    max_temperature_f: float = Field(
        default=95.0,
        ge=60.0,
        le=120.0,
        description="Maximum temperature for safe work"
    )
    
    # Automatic rescheduling
    auto_reschedule_enabled: bool = Field(
        default=True,
        description="Automatically reschedule jobs due to weather"
    )
    
    advance_notice_hours: int = Field(
        default=24,
        ge=4,
        le=168,
        description="Hours in advance to check weather and notify"
    )
    
    # Weather severity handling
    weather_severity_actions: Dict[WeatherSeverity, str] = Field(
        default={
            WeatherSeverity.LIGHT: "proceed",
            WeatherSeverity.MODERATE: "reschedule",
            WeatherSeverity.SEVERE: "cancel_day"
        },
        description="Actions to take based on weather severity"
    )
    
    @validator('min_temperature_f', 'max_temperature_f')
    def validate_temperatures(cls, v, values):
        """Ensure temperature range is logical"""
        if 'min_temperature_f' in values and v <= values['min_temperature_f']:
            raise ValueError("Max temperature must be greater than min temperature")
        return v


class DMSettings(BaseModel):
    """DM booking flow configuration"""
    model_config = ConfigDict(extra="forbid")
    
    # Auto-response settings
    auto_response_enabled: bool = Field(
        default=True,
        description="Enable automatic responses to pricing inquiries"
    )
    
    response_delay_minutes: int = Field(
        default=2,
        ge=0,
        le=60,
        description="Delay before auto-responding (minutes)"
    )
    
    # Photo collection
    require_photos_for_quote: bool = Field(
        default=True,
        description="Require photos before providing quotes"
    )
    
    max_photos_per_inquiry: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum photos per inquiry"
    )
    
    # Quote generation
    provide_ballpark_estimates: bool = Field(
        default=True,
        description="Provide ballpark estimates before site visit"
    )
    
    ballpark_accuracy_margin: float = Field(
        default=0.25,
        ge=0.1,
        le=1.0,
        description="Ballpark estimate accuracy margin (±25%)"
    )
    
    # Lead qualification
    qualification_questions: List[str] = Field(
        default=[
            "What type of surface needs cleaning?",
            "Approximate square footage?",
            "When would you like the work completed?",
            "What's your preferred contact method?"
        ],
        description="Questions to qualify leads"
    )
    
    auto_qualify_threshold: float = Field(
        default=0.8,
        ge=0.5,
        le=1.0,
        description="AI confidence threshold for auto-qualification"
    )
    
    # Booking conversion
    booking_link_in_response: bool = Field(
        default=True,
        description="Include booking link in responses"
    )
    
    follow_up_after_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Hours to wait before follow-up"
    )


class SchedulingSettings(BaseModel):
    """Scheduling and calendar management configuration"""
    model_config = ConfigDict(extra="forbid")
    
    # Working hours
    business_hours_start: str = Field(
        default="08:00",
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="Business hours start time (HH:MM format)"
    )
    
    business_hours_end: str = Field(
        default="17:00",
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="Business hours end time (HH:MM format)"
    )
    
    working_days: List[str] = Field(
        default=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
        description="Working days of the week"
    )
    
    # Job scheduling
    default_job_duration_hours: float = Field(
        default=3.0,
        ge=0.5,
        le=12.0,
        description="Default job duration in hours"
    )
    
    buffer_time_minutes: int = Field(
        default=30,
        ge=0,
        le=120,
        description="Buffer time between jobs in minutes"
    )
    
    # Advance booking
    min_advance_booking_hours: int = Field(
        default=24,
        ge=2,
        le=720,
        description="Minimum hours in advance for booking"
    )
    
    max_advance_booking_days: int = Field(
        default=90,
        ge=7,
        le=365,
        description="Maximum days in advance for booking"
    )
    
    # Emergency/rush jobs
    allow_rush_jobs: bool = Field(
        default=True,
        description="Allow emergency/rush job booking"
    )
    
    rush_job_multiplier: float = Field(
        default=1.5,
        ge=1.0,
        le=3.0,
        description="Price multiplier for rush jobs"
    )
    
    # Capacity management
    max_jobs_per_day: int = Field(
        default=6,
        ge=1,
        le=20,
        description="Maximum jobs per day"
    )
    
    @validator('working_days')
    def validate_working_days(cls, v):
        """Ensure working days are valid"""
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in v:
            if day.lower() not in valid_days:
                raise ValueError(f"Invalid working day: {day}")
        return [day.lower() for day in v]


# Composite Settings Model
class PWSettings(BaseModel):
    """Complete pressure washing settings configuration"""
    model_config = ConfigDict(extra="forbid")
    
    pricing: PricingSettings = Field(default_factory=PricingSettings)
    weather: WeatherSettings = Field(default_factory=WeatherSettings)
    dm: DMSettings = Field(default_factory=DMSettings)
    scheduling: SchedulingSettings = Field(default_factory=SchedulingSettings)


class SettingsResolver:
    """
    Central settings resolver with hierarchical merging and caching
    
    Merge order: plan -> organization -> team -> integration -> user (last writer wins)
    """
    
    def __init__(self, db: Session, cache_ttl_seconds: int = 300):
        self.db = db
        self.cache_ttl = cache_ttl_seconds
        
    def _get_cache_key(self, org_id: str, user_id: Optional[int] = None, 
                       team_id: Optional[str] = None, integration_id: Optional[str] = None) -> str:
        """Generate cache key for settings"""
        key_parts = [f"pw_settings:org:{org_id}"]
        if team_id:
            key_parts.append(f"team:{team_id}")
        if integration_id:
            key_parts.append(f"integration:{integration_id}")
        if user_id:
            key_parts.append(f"user:{user_id}")
        return ":".join(key_parts)
    
    def _get_cache_version_key(self, org_id: str) -> str:
        """Get cache version key for invalidation"""
        return f"pw_settings_version:org:{org_id}"
    
    def _get_settings_from_entity(self, entity: Any, namespace: SettingsNamespace) -> Dict[str, Any]:
        """Extract settings for a namespace from an entity"""
        if not entity:
            return {}
            
        # Get settings from different entity types
        if hasattr(entity, 'settings') and entity.settings:
            settings = entity.settings or {}
        elif hasattr(entity, 'features') and entity.features:
            settings = entity.features or {}
        else:
            return {}
            
        # Return namespace-specific settings
        namespace_settings = settings.get(namespace.value, {})
        return namespace_settings if isinstance(namespace_settings, dict) else {}
    
    def _merge_settings_dicts(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two settings dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_settings_dicts(result[key], value)
            else:
                result[key] = value
                
        return result
    
    def _validate_settings(self, settings_dict: Dict[str, Any]) -> PWSettings:
        """Validate and parse settings dictionary into typed model"""
        try:
            return PWSettings(**settings_dict)
        except Exception as e:
            logger.error(f"Settings validation failed: {e}")
            logger.error(f"Invalid settings: {settings_dict}")
            # Return default settings on validation failure
            return PWSettings()
    
    def get_settings(self, 
                    org_id: str,
                    user_id: Optional[int] = None,
                    team_id: Optional[str] = None,
                    integration_id: Optional[str] = None,
                    bypass_cache: bool = False) -> PWSettings:
        """
        Get resolved settings with hierarchical merging
        
        Args:
            org_id: Organization ID (required)
            user_id: User ID (optional)
            team_id: Team ID (optional) 
            integration_id: Integration ID (optional)
            bypass_cache: Skip cache lookup
            
        Returns:
            PWSettings: Fully resolved and validated settings
        """
        cache_key = self._get_cache_key(org_id, user_id, team_id, integration_id)
        
        # Try cache first (unless bypassed)
        if not bypass_cache and REDIS_AVAILABLE and redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    settings_dict = json.loads(cached)
                    return PWSettings(**settings_dict)
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")
        
        try:
            # Start with empty settings
            merged_settings = {
                "pricing": {},
                "weather": {},
                "dm": {},
                "scheduling": {}
            }
            
            # 1. Get plan-level settings
            if user_id:
                user = self.db.query(User).filter(User.id == user_id).first()
                if user and user.plan:
                    for namespace in SettingsNamespace:
                        plan_settings = self._get_settings_from_entity(user.plan, namespace)
                        if plan_settings:
                            merged_settings[namespace.value] = self._merge_settings_dicts(
                                merged_settings[namespace.value], plan_settings
                            )
            
            # 2. Get organization-level settings
            org = self.db.query(Organization).filter(Organization.id == org_id).first()
            if org:
                for namespace in SettingsNamespace:
                    org_settings = self._get_settings_from_entity(org, namespace)
                    if org_settings:
                        merged_settings[namespace.value] = self._merge_settings_dicts(
                            merged_settings[namespace.value], org_settings
                        )
            
            # 3. Get team-level settings
            if team_id:
                team = self.db.query(Team).filter(Team.id == team_id).first()
                if team:
                    for namespace in SettingsNamespace:
                        team_settings = self._get_settings_from_entity(team, namespace)
                        if team_settings:
                            merged_settings[namespace.value] = self._merge_settings_dicts(
                                merged_settings[namespace.value], team_settings
                            )
            
            # 4. Get integration-level settings (placeholder for future integration model)
            # TODO: Implement integration settings when integration model is added
            
            # 5. Get user-level settings
            if user_id:
                user_settings = self.db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
                if user_settings:
                    for namespace in SettingsNamespace:
                        # Convert UserSetting attributes to namespace dict
                        user_ns_settings = self._extract_user_namespace_settings(user_settings, namespace)
                        if user_ns_settings:
                            merged_settings[namespace.value] = self._merge_settings_dicts(
                                merged_settings[namespace.value], user_ns_settings
                            )
            
            # Validate and create typed settings
            validated_settings = self._validate_settings(merged_settings)
            
            # Cache the result
            if REDIS_AVAILABLE and redis_client:
                try:
                    cache_data = validated_settings.model_dump()
                    redis_client.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(cache_data, default=str)
                    )
                except Exception as e:
                    logger.warning(f"Cache write failed: {e}")
            
            return validated_settings
            
        except Exception as e:
            logger.error(f"Settings resolution failed: {e}")
            # Return default settings on any failure
            return PWSettings()
    
    def _extract_user_namespace_settings(self, user_settings: UserSetting, 
                                       namespace: SettingsNamespace) -> Dict[str, Any]:
        """Extract namespace-specific settings from UserSetting model"""
        
        # Map UserSetting fields to namespace settings
        if namespace == SettingsNamespace.PRICING:
            # No direct pricing settings in UserSetting yet - could be added
            return {}
            
        elif namespace == SettingsNamespace.WEATHER:
            # Extract weather-related preferences from user settings
            return {}
            
        elif namespace == SettingsNamespace.DM:
            # Extract DM/auto-response settings
            return {
                "auto_response_enabled": getattr(user_settings, 'auto_response_enabled', False),
                "response_delay_minutes": getattr(user_settings, 'auto_response_delay_minutes', 2),
            }
            
        elif namespace == SettingsNamespace.SCHEDULING:
            # Extract scheduling preferences
            return {
                "business_hours_start": getattr(user_settings, 'business_hours_start', "08:00"),
                "business_hours_end": getattr(user_settings, 'business_hours_end', "17:00"),
                "working_days": getattr(user_settings, 'business_days', 
                                      ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]),
            }
            
        return {}
    
    def invalidate_cache(self, org_id: str) -> None:
        """Invalidate cached settings for an organization"""
        if not REDIS_AVAILABLE or not redis_client:
            logger.warning("Redis not available, cannot invalidate cache")
            return
            
        try:
            # Increment version number to invalidate all related caches
            version_key = self._get_cache_version_key(org_id)
            redis_client.incr(version_key)
            
            # Also try to delete specific cache keys (best effort)
            pattern = f"pw_settings:org:{org_id}*"
            for key in redis_client.scan_iter(match=pattern):
                redis_client.delete(key)
                
            logger.info(f"Invalidated settings cache for organization {org_id}")
            
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
    
    def get_namespace_settings(self, 
                             org_id: str,
                             namespace: SettingsNamespace,
                             user_id: Optional[int] = None,
                             team_id: Optional[str] = None,
                             integration_id: Optional[str] = None) -> Union[PricingSettings, WeatherSettings, DMSettings, SchedulingSettings]:
        """Get settings for a specific namespace only"""
        
        full_settings = self.get_settings(org_id, user_id, team_id, integration_id)
        
        if namespace == SettingsNamespace.PRICING:
            return full_settings.pricing
        elif namespace == SettingsNamespace.WEATHER:
            return full_settings.weather
        elif namespace == SettingsNamespace.DM:
            return full_settings.dm
        elif namespace == SettingsNamespace.SCHEDULING:
            return full_settings.scheduling
        else:
            raise ValueError(f"Unknown namespace: {namespace}")


def create_settings_resolver(db: Session) -> SettingsResolver:
    """Factory function to create settings resolver"""
    return SettingsResolver(db)


# Convenience functions for specific namespace access
def get_pricing_settings(db: Session, org_id: str, user_id: Optional[int] = None) -> PricingSettings:
    """Get pricing settings for an organization/user"""
    resolver = SettingsResolver(db)
    return resolver.get_namespace_settings(org_id, SettingsNamespace.PRICING, user_id)


def get_weather_settings(db: Session, org_id: str, user_id: Optional[int] = None) -> WeatherSettings:
    """Get weather settings for an organization/user"""
    resolver = SettingsResolver(db)
    return resolver.get_namespace_settings(org_id, SettingsNamespace.WEATHER, user_id)


def get_dm_settings(db: Session, org_id: str, user_id: Optional[int] = None) -> DMSettings:
    """Get DM settings for an organization/user"""
    resolver = SettingsResolver(db)
    return resolver.get_namespace_settings(org_id, SettingsNamespace.DM, user_id)


def get_scheduling_settings(db: Session, org_id: str, user_id: Optional[int] = None) -> SchedulingSettings:
    """Get scheduling settings for an organization/user"""
    resolver = SettingsResolver(db)
    return resolver.get_namespace_settings(org_id, SettingsNamespace.SCHEDULING, user_id)