# PW-SETTINGS-REPLACE-001: Central Typed Settings Resolver

## Overview

This document describes the implementation of the central typed settings resolver for the pressure washing platform. The resolver provides tenant-configurable settings with typed validation and hierarchical merging to support per-client variability in pricing, weather conditions, DM booking behavior, and scheduling.

## Architecture

### Hierarchical Merge Order
Settings are merged in the following order (last writer wins):
1. **Plan** → Organization plan settings
2. **Organization** → Organization-specific settings  
3. **Team** → Team-level overrides
4. **Integration** → Integration-specific settings (future)
5. **User** → User personal preferences

### Supported Namespaces
- `pricing.*` - Pricing configuration per surface type, bundles, seasonal modifiers
- `weather.*` - Weather-aware scheduling thresholds and automation
- `dm.*` - DM booking flow, auto-response, lead qualification
- `scheduling.*` - Business hours, job capacity, advance booking rules

## Settings Schema

### PricingSettings
```python
class PricingSettings(BaseModel):
    # Base pricing per square foot by surface type
    base_rates: Dict[SurfaceType, float]
    minimum_job_price: float = 150.0
    
    # Additional services
    soft_wash_multiplier: float = 1.3
    gutter_cleaning_rate: float = 1.50
    
    # Seasonal pricing modifiers
    seasonal_multipliers: Dict[str, float]
    
    # Bundle discounts
    multi_service_discount: float = 0.10
    
    # Travel charges
    travel_rate_per_mile: float = 2.0
    free_travel_radius_miles: float = 15.0
```

**Supported Surface Types:**
- `concrete` (0.15/sq ft default)
- `brick` (0.18/sq ft default) 
- `vinyl_siding` (0.20/sq ft default)
- `wood_deck` (0.25/sq ft default)
- `roof` (0.30/sq ft default)
- `driveway` (0.12/sq ft default)
- `patio` (0.15/sq ft default)
- `fence` (0.22/sq ft default)

### WeatherSettings
```python
class WeatherSettings(BaseModel):
    # Rain delay thresholds
    rain_delay_threshold_inches: float = 0.1
    
    # Wind speed limits by service type  
    max_wind_speed_roof: float = 15.0
    max_wind_speed_general: float = 25.0
    
    # Temperature limits
    min_temperature_f: float = 35.0
    max_temperature_f: float = 95.0
    
    # Automatic rescheduling
    auto_reschedule_enabled: bool = True
    advance_notice_hours: int = 24
    
    # Weather severity handling
    weather_severity_actions: Dict[WeatherSeverity, str]
```

**Weather Severity Actions:**
- `light` → "proceed"
- `moderate` → "reschedule" 
- `severe` → "cancel_day"

### DMSettings
```python
class DMSettings(BaseModel):
    # Auto-response settings
    auto_response_enabled: bool = True
    response_delay_minutes: int = 2
    
    # Photo collection
    require_photos_for_quote: bool = True
    max_photos_per_inquiry: int = 5
    
    # Quote generation
    provide_ballpark_estimates: bool = True
    ballpark_accuracy_margin: float = 0.25
    
    # Lead qualification
    qualification_questions: List[str]
    auto_qualify_threshold: float = 0.8
    
    # Booking conversion
    booking_link_in_response: bool = True
    follow_up_after_hours: int = 24
```

### SchedulingSettings
```python
class SchedulingSettings(BaseModel):
    # Working hours
    business_hours_start: str = "08:00"  # HH:MM format
    business_hours_end: str = "17:00"
    working_days: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    
    # Job scheduling
    default_job_duration_hours: float = 3.0
    buffer_time_minutes: int = 30
    
    # Advance booking
    min_advance_booking_hours: int = 24
    max_advance_booking_days: int = 90
    
    # Emergency/rush jobs
    allow_rush_jobs: bool = True
    rush_job_multiplier: float = 1.5
    
    # Capacity management
    max_jobs_per_day: int = 6
```

## Usage Examples

### Basic Usage
```python
from backend.services.settings_resolver import SettingsResolver, create_settings_resolver
from backend.db.database import get_db

# Create resolver
db = get_db()
resolver = create_settings_resolver(db)

# Get complete settings for an organization/user
settings = resolver.get_settings(
    org_id="org_123",
    user_id=456
)

# Access specific settings
min_price = settings.pricing.minimum_job_price
auto_reschedule = settings.weather.auto_reschedule_enabled
business_start = settings.scheduling.business_hours_start
```

### Namespace-Specific Access
```python
from backend.services.settings_resolver import (
    get_pricing_settings,
    get_weather_settings,
    get_dm_settings, 
    get_scheduling_settings
)

# Get only pricing settings
pricing = get_pricing_settings(db, org_id="org_123", user_id=456)
concrete_rate = pricing.base_rates[SurfaceType.CONCRETE]

# Get only weather settings  
weather = get_weather_settings(db, org_id="org_123")
if weather.auto_reschedule_enabled:
    # Handle automatic rescheduling
    pass
```

### Hierarchical Settings Override
```python
# Organization-level settings in database
organization.settings = {
    "pricing": {
        "minimum_job_price": 175.0,
        "base_rates": {
            "concrete": 0.18  # Override default 0.15
        }
    }
}

# User-level preferences  
user_settings.business_hours_start = "09:00"  # Override default 08:00

# Resolved settings will have:
# - minimum_job_price = 175.0 (from organization)
# - concrete rate = 0.18 (from organization)  
# - business_hours_start = "09:00" (from user)
# - All other settings = defaults
```

## Caching

### Cache Strategy
- **Cache Key Format:** `pw_settings:org:{org_id}[:team:{team_id}][:integration:{integration_id}][:user:{user_id}]`
- **Default TTL:** 5 minutes (300 seconds)
- **Storage:** Redis with fallback to in-memory when Redis unavailable
- **Invalidation:** Automatic on settings updates via `invalidate_cache(org_id)`

### Cache Invalidation
```python
# Invalidate all cached settings for an organization
resolver.invalidate_cache("org_123")

# This will:
# 1. Increment version number 
# 2. Delete all matching cache keys
# 3. Force fresh database lookup on next access
```

## Validation & Error Handling

### Pydantic Validation
All settings are validated using Pydantic models with:
- **Type checking** (int, float, bool, string, enums)
- **Range validation** (ge, le constraints)
- **Format validation** (regex for time formats)
- **Custom validators** (temperature ranges, seasonal completeness)

### Error Handling
- **Invalid settings** → Return validated defaults with error logging
- **Database errors** → Return defaults, log error
- **Cache errors** → Fall back to database, log warning
- **Missing entities** → Use defaults for missing hierarchy levels

### Example Validation Errors
```python
# These will raise ValidationError:
PricingSettings(minimum_job_price=-100)  # Negative price
WeatherSettings(min_temperature_f=80, max_temperature_f=60)  # Invalid range
SchedulingSettings(working_days=["invalid_day"])  # Invalid day
SchedulingSettings(business_hours_start="25:00")  # Invalid time format
```

## Database Integration

### Entity Settings Storage
Settings are stored as JSON in the following fields:
- `Plan.features` - Plan-level settings
- `Organization.settings` - Organization-specific settings  
- `Team.settings` - Team-level overrides
- `UserSetting.*` - User preferences mapped to namespaces

### Settings Extraction
The resolver automatically extracts namespace-specific settings from entity JSON fields:

```python
# Organization settings
{
  "pricing": {
    "minimum_job_price": 175.0,
    "base_rates": {"concrete": 0.18}
  },
  "weather": {
    "auto_reschedule_enabled": false
  }
}

# UserSetting model mapping
user_settings.auto_response_enabled → dm.auto_response_enabled
user_settings.business_hours_start → scheduling.business_hours_start
user_settings.business_days → scheduling.working_days
```

## Testing

### Test Coverage
The implementation includes comprehensive unit tests covering:

- **Default settings validation** - All namespaces use valid defaults
- **Field validation** - Pydantic constraints properly enforced  
- **Hierarchical merging** - Settings merge in correct order
- **Cache behavior** - Hit/miss scenarios, invalidation
- **Error handling** - Database errors, invalid data, missing entities
- **Edge cases** - Malformed data, connection failures

### Running Tests
```bash
# Run settings resolver tests
python -m pytest backend/tests/test_settings_resolver.py -v

# Run specific test class
python -m pytest backend/tests/test_settings_resolver.py::TestPricingSettings -v

# Run with coverage
python -m pytest backend/tests/test_settings_resolver.py --cov=backend.services.settings_resolver
```

## Performance Considerations

### Caching Strategy
- **5-minute TTL** balances freshness vs performance
- **Redis storage** enables distributed caching across instances
- **Batch invalidation** minimizes cache management overhead
- **Graceful fallback** maintains availability when Redis unavailable

### Database Queries
- **Minimal queries** - Only fetch required entities in hierarchy
- **Lazy loading** - Skip queries for missing hierarchy levels
- **Connection reuse** - Leverages SQLAlchemy session management

### Memory Usage
- **Lightweight models** - Pydantic models minimize memory footprint
- **JSON serialization** - Efficient Redis storage format
- **No global state** - Resolver instances are stateless

## Future Enhancements

### Integration-Level Settings
```python
# Future: Integration-specific settings for field service software
integration_settings = {
  "scheduling": {
    "sync_with_housecall_pro": True,
    "jobber_booking_webhook": "https://api.jobber.com/webhooks/booking"
  }
}
```

### Dynamic Settings Updates
```python
# Future: Real-time settings updates via WebSocket
await resolver.watch_settings("org_123", callback=handle_settings_change)
```

### Settings Analytics
```python
# Future: Track settings usage and effectiveness
analytics = resolver.get_settings_analytics("org_123")
# Returns: most_used_settings, effectiveness_scores, optimization_suggestions
```

## Migration Guide

### Existing Settings Integration
To migrate existing ad-hoc settings:

1. **Identify current settings** in database JSON fields
2. **Map to namespaces** using provided schema
3. **Update calling code** to use resolver instead of direct JSON access
4. **Add validation** using Pydantic models
5. **Implement caching** for performance optimization

### Example Migration
```python
# Before: Direct JSON access
org_settings = organization.settings or {}
min_price = org_settings.get('pricing', {}).get('minimum_job_price', 150.0)

# After: Using settings resolver  
settings = resolver.get_settings(org_id=organization.id)
min_price = settings.pricing.minimum_job_price
```

This provides type safety, validation, caching, and hierarchical merging automatically.