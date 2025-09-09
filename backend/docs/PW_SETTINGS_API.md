# Pressure Washing Settings API Documentation

## Overview

The Pressure Washing Settings API provides tenant-configurable endpoints for managing pricing, weather, DM (direct message), and scheduling settings. This API enables pressure washing companies to customize their operational parameters without code changes.

## Base URL

```
/api/pw-settings
```

## Authentication & Authorization

All endpoints require:
- **JWT Authentication**: Valid Bearer token in `Authorization` header
- **Organization Context**: `X-Organization-ID` header containing the organization UUID
- **Active User**: User must be active and have appropriate permissions within the organization

## Content Type

All requests and responses use `application/json` unless otherwise specified.

## Settings Namespaces

The API supports four configuration namespaces:

### 1. Pricing Settings (`/pricing`)
Configure surface-specific rates, seasonal pricing, and service modifiers.

### 2. Weather Settings (`/weather`)
Configure weather thresholds, automatic rescheduling, and severe weather handling.

### 3. DM Settings (`/dm`)
Configure auto-response behavior, lead qualification, and booking conversion.

### 4. Scheduling Settings (`/scheduling`)
Configure business hours, job capacity, and advance booking rules.

## Endpoints

### Get All Settings

**GET** `/api/pw-settings/`

Retrieve all pressure washing settings for the organization.

**Headers:**
```
Authorization: Bearer <jwt_token>
X-Organization-ID: <organization_uuid>
```

**Response:**
```json
{
  "organization_id": "org_123",
  "pricing": {
    "base_rates": {
      "concrete": 0.15,
      "brick": 0.18,
      "vinyl_siding": 0.20,
      "wood_deck": 0.25,
      "roof": 0.30,
      "driveway": 0.12,
      "patio": 0.15,
      "fence": 0.22
    },
    "minimum_job_price": 150.0,
    "soft_wash_multiplier": 1.3,
    "gutter_cleaning_rate": 1.50,
    "seasonal_multipliers": {
      "spring": 1.2,
      "summer": 1.0,
      "fall": 1.1,
      "winter": 0.8
    },
    "multi_service_discount": 0.10,
    "travel_rate_per_mile": 2.0,
    "free_travel_radius_miles": 15.0
  },
  "weather": {
    "rain_delay_threshold_inches": 0.1,
    "max_wind_speed_roof": 15.0,
    "max_wind_speed_general": 25.0,
    "min_temperature_f": 35.0,
    "max_temperature_f": 95.0,
    "auto_reschedule_enabled": true,
    "advance_notice_hours": 24,
    "weather_severity_actions": {
      "light": "proceed",
      "moderate": "reschedule",
      "severe": "cancel_day"
    }
  },
  "dm": {
    "auto_response_enabled": true,
    "response_delay_minutes": 2,
    "require_photos_for_quote": true,
    "max_photos_per_inquiry": 5,
    "provide_ballpark_estimates": true,
    "ballpark_accuracy_margin": 0.25,
    "qualification_questions": [
      "What type of surface needs cleaning?",
      "Approximate square footage?",
      "When would you like the work completed?",
      "What's your preferred contact method?"
    ],
    "auto_qualify_threshold": 0.8,
    "booking_link_in_response": true,
    "follow_up_after_hours": 24
  },
  "scheduling": {
    "business_hours_start": "08:00",
    "business_hours_end": "17:00",
    "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
    "default_job_duration_hours": 3.0,
    "buffer_time_minutes": 30,
    "min_advance_booking_hours": 24,
    "max_advance_booking_days": 90,
    "allow_rush_jobs": true,
    "rush_job_multiplier": 1.5,
    "max_jobs_per_day": 6
  },
  "last_updated": "2024-12-08T15:30:00Z"
}
```

### Get Namespace-Specific Settings

**GET** `/api/pw-settings/{namespace}`

Retrieve settings for a specific namespace.

**Path Parameters:**
- `namespace`: One of `pricing`, `weather`, `dm`, `scheduling`

**Example: GET** `/api/pw-settings/pricing`

**Response:**
```json
{
  "namespace": "pricing",
  "organization_id": "org_123",
  "settings": {
    "base_rates": {
      "concrete": 0.15,
      "brick": 0.18,
      "vinyl_siding": 0.20,
      "wood_deck": 0.25,
      "roof": 0.30,
      "driveway": 0.12,
      "patio": 0.15,
      "fence": 0.22
    },
    "minimum_job_price": 150.0,
    "soft_wash_multiplier": 1.3,
    "gutter_cleaning_rate": 1.50,
    "seasonal_multipliers": {
      "spring": 1.2,
      "summer": 1.0,
      "fall": 1.1,
      "winter": 0.8
    },
    "multi_service_discount": 0.10,
    "travel_rate_per_mile": 2.0,
    "free_travel_radius_miles": 15.0
  },
  "last_updated": "2024-12-08T15:30:00Z"
}
```

### Update Settings

**PUT** `/api/pw-settings/{namespace}`

Update settings for a specific namespace. Only provided fields will be updated.

**Example: PUT** `/api/pw-settings/pricing`

**Request Body:**
```json
{
  "minimum_job_price": 175.0,
  "base_rates": {
    "concrete": 0.18,
    "brick": 0.20
  },
  "seasonal_multipliers": {
    "spring": 1.3,
    "summer": 1.0,
    "fall": 1.2,
    "winter": 0.9
  }
}
```

**Response:**
```json
{
  "success": true,
  "namespace": "pricing",
  "organization_id": "org_123",
  "changes_applied": {
    "minimum_job_price": 175.0,
    "base_rates": {
      "concrete": 0.18,
      "brick": 0.20
    },
    "seasonal_multipliers": {
      "spring": 1.3,
      "summer": 1.0,
      "fall": 1.2,
      "winter": 0.9
    }
  },
  "validation_errors": [],
  "cache_invalidated": true,
  "audit_logged": true
}
```

### Get Default Settings

**GET** `/api/pw-settings/defaults`

Retrieve default settings for all namespaces (useful for new organizations or reference).

**Response:**
```json
{
  "pricing": { /* default pricing settings */ },
  "weather": { /* default weather settings */ },
  "dm": { /* default DM settings */ },
  "scheduling": { /* default scheduling settings */ }
}
```

### Get Settings Schema

**GET** `/api/pw-settings/schema/{namespace}`

Retrieve JSON schema for a specific namespace to understand validation rules.

**Example: GET** `/api/pw-settings/schema/pricing`

**Response:**
```json
{
  "namespace": "pricing",
  "schema": {
    "type": "object",
    "properties": {
      "base_rates": {
        "type": "object",
        "description": "Pricing per square foot by surface type",
        "additionalProperties": {
          "type": "number",
          "minimum": 0
        }
      },
      "minimum_job_price": {
        "type": "number",
        "minimum": 50.0,
        "maximum": 1000.0,
        "description": "Minimum price for any job ($50-$1000)"
      },
      // ... additional properties
    }
  }
}
```

### Cache Management

**POST** `/api/pw-settings/cache/invalidate`

Manually invalidate cached settings for the organization.

**Response:**
```json
{
  "success": true,
  "message": "Settings cache invalidated for organization org_123"
}
```

## Pricing Settings Schema

### Base Rates
Configure pricing per square foot by surface type:

| Surface Type | Description | Default Rate |
|-------------|-------------|-------------|
| `concrete` | Concrete surfaces | $0.15/sq ft |
| `brick` | Brick surfaces | $0.18/sq ft |
| `vinyl_siding` | Vinyl siding | $0.20/sq ft |
| `wood_deck` | Wood decking | $0.25/sq ft |
| `roof` | Roof cleaning | $0.30/sq ft |
| `driveway` | Driveways | $0.12/sq ft |
| `patio` | Patios | $0.15/sq ft |
| `fence` | Fencing | $0.22/sq ft |

### Pricing Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `base_rates` | object | positive numbers | Surface-specific rates per sq ft |
| `minimum_job_price` | number | $50-$1000 | Minimum charge for any job |
| `soft_wash_multiplier` | number | 1.0-3.0 | Price multiplier for soft washing |
| `gutter_cleaning_rate` | number | $0.50-$5.00 | Price per linear foot for gutters |
| `seasonal_multipliers` | object | positive numbers | Seasonal pricing modifiers |
| `multi_service_discount` | number | 0-0.5 | Discount for multiple services |
| `travel_rate_per_mile` | number | $0-$10 | Travel charge beyond free radius |
| `free_travel_radius_miles` | number | 0-100 | Free travel radius in miles |

### Seasonal Multipliers
Required seasons with pricing multipliers:
- `spring`: Spring pricing (default: 1.2x)
- `summer`: Summer pricing (default: 1.0x)
- `fall`: Fall pricing (default: 1.1x)
- `winter`: Winter pricing (default: 0.8x)

## Weather Settings Schema

### Weather Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `rain_delay_threshold_inches` | number | 0-2.0 | Rain threshold to trigger delays |
| `max_wind_speed_roof` | number | 5-50 | Max wind speed for roof work (mph) |
| `max_wind_speed_general` | number | 10-60 | Max wind speed for general work (mph) |
| `min_temperature_f` | number | -10-80 | Minimum working temperature |
| `max_temperature_f` | number | 60-120 | Maximum working temperature |
| `auto_reschedule_enabled` | boolean | - | Enable automatic rescheduling |
| `advance_notice_hours` | integer | 4-168 | Hours advance notice for weather checks |
| `weather_severity_actions` | object | - | Actions by weather severity |

### Weather Severity Actions
Actions to take based on weather conditions:
- `light`: "proceed", "reschedule", "cancel_day"
- `moderate`: "proceed", "reschedule", "cancel_day"  
- `severe`: "proceed", "reschedule", "cancel_day"

## DM Settings Schema

### DM Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `auto_response_enabled` | boolean | - | Enable automatic responses |
| `response_delay_minutes` | integer | 0-60 | Delay before auto-responding |
| `require_photos_for_quote` | boolean | - | Require photos for quotes |
| `max_photos_per_inquiry` | integer | 1-20 | Max photos per inquiry |
| `provide_ballpark_estimates` | boolean | - | Provide ballpark estimates |
| `ballpark_accuracy_margin` | number | 0.1-1.0 | Estimate accuracy margin |
| `qualification_questions` | array | max 10 items | Lead qualification questions |
| `auto_qualify_threshold` | number | 0.5-1.0 | AI confidence threshold |
| `booking_link_in_response` | boolean | - | Include booking links |
| `follow_up_after_hours` | integer | 1-168 | Hours before follow-up |
| `quiet_hours` | object | - | Hours to avoid auto-responses |

### Qualification Questions
Array of strings with constraints:
- Maximum 10 questions
- Each question max 200 characters
- Cannot be empty strings

### Quiet Hours
Object with start/end times in HH:MM format:
```json
{
  "start": "22:00",
  "end": "08:00"
}
```

## Scheduling Settings Schema

### Scheduling Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `business_hours_start` | string | HH:MM | Business start time |
| `business_hours_end` | string | HH:MM | Business end time |
| `working_days` | array | max 7 days | Working days of week |
| `default_job_duration_hours` | number | 0.5-12.0 | Default job duration |
| `buffer_time_minutes` | integer | 0-120 | Buffer between jobs |
| `min_advance_booking_hours` | integer | 2-720 | Minimum advance booking |
| `max_advance_booking_days` | integer | 7-365 | Maximum advance booking |
| `allow_rush_jobs` | boolean | - | Allow emergency jobs |
| `rush_job_multiplier` | number | 1.0-3.0 | Rush job price multiplier |
| `max_jobs_per_day` | integer | 1-20 | Maximum daily jobs |

### Working Days
Array of day names (case-insensitive):
- `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday`

### Time Format
All time fields use 24-hour HH:MM format:
- `08:00` (8:00 AM)
- `17:30` (5:30 PM)
- `22:00` (10:00 PM)

## Error Responses

### 400 Bad Request
Missing or invalid organization context:
```json
{
  "detail": "Missing X-Organization-ID header. Multi-tenant requests require organization context."
}
```

### 401 Unauthorized
Invalid or missing authentication:
```json
{
  "detail": "Invalid authentication credentials"
}
```

### 404 Not Found
Organization not found:
```json
{
  "detail": "Organization not found"
}
```

### 422 Validation Error
Invalid request data:
```json
{
  "detail": [
    {
      "loc": ["body", "minimum_job_price"],
      "msg": "ensure this value is greater than or equal to 50",
      "type": "value_error.number.not_ge",
      "ctx": {"limit_value": 50}
    }
  ]
}
```

### 500 Internal Server Error
Server-side errors:
```json
{
  "detail": "Failed to update pricing settings"
}
```

## Usage Examples

### Update Pricing for Summer Season

```bash
curl -X PUT "https://api.yourapp.com/api/pw-settings/pricing" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "X-Organization-ID: org_123" \
  -H "Content-Type: application/json" \
  -d '{
    "seasonal_multipliers": {
      "spring": 1.3,
      "summer": 1.1,
      "fall": 1.2,
      "winter": 0.9
    }
  }'
```

### Configure Weather Sensitivity

```bash
curl -X PUT "https://api.yourapp.com/api/pw-settings/weather" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "X-Organization-ID: org_123" \
  -H "Content-Type: application/json" \
  -d '{
    "rain_delay_threshold_inches": 0.05,
    "max_wind_speed_roof": 12.0,
    "auto_reschedule_enabled": true,
    "advance_notice_hours": 48
  }'
```

### Setup Auto-Response for DMs

```bash
curl -X PUT "https://api.yourapp.com/api/pw-settings/dm" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "X-Organization-ID: org_123" \
  -H "Content-Type: application/json" \
  -d '{
    "auto_response_enabled": true,
    "response_delay_minutes": 5,
    "qualification_questions": [
      "What type of surface needs cleaning?",
      "What is the approximate square footage?",
      "When would you like the work completed?",
      "Do you have any specific areas of concern?"
    ],
    "quiet_hours": {
      "start": "21:00",
      "end": "08:00"
    }
  }'
```

### Adjust Business Hours

```bash
curl -X PUT "https://api.yourapp.com/api/pw-settings/scheduling" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "X-Organization-ID: org_123" \
  -H "Content-Type: application/json" \
  -d '{
    "business_hours_start": "07:00",
    "business_hours_end": "18:00",
    "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
    "max_jobs_per_day": 8,
    "allow_rush_jobs": true,
    "rush_job_multiplier": 2.0
  }'
```

## Cache Behavior

### Automatic Cache Invalidation
Cache is automatically invalidated when:
- Any settings are updated via PUT endpoints
- Organization settings are modified
- Manual cache invalidation is triggered

### Cache TTL
- Default cache time-to-live: 5 minutes
- Cache key format: `pw_settings:org:{org_id}[:user:{user_id}]`
- Distributed caching via Redis

### Manual Cache Control
Use the cache invalidation endpoint when:
- Settings are modified outside the API
- Cache appears stale
- Troubleshooting configuration issues

## Audit Logging

All settings changes are automatically logged with:
- User ID and organization ID
- Timestamp of change
- Namespace and specific changes
- User role and IP address
- Success/failure status

Audit logs are available for compliance and troubleshooting purposes.

## Rate Limiting

API endpoints are subject to standard rate limiting:
- 60 requests per minute per organization
- 1000 requests per hour per organization
- Burst allowance of 10 requests

## Security Considerations

### Multi-Tenant Isolation
- All operations are scoped to the authenticated user's organization
- Settings cannot be accessed across organization boundaries
- Organization ID validation is enforced on every request

### Input Validation
- All inputs are validated using Pydantic schemas
- Business rules are enforced (e.g., positive rates, valid time ranges)
- SQL injection protection via parameterized queries

### Audit Trail
- Complete audit trail of all settings changes
- Immutable audit logs for compliance
- Integration with security monitoring systems

## Support

For API support or questions:
- Review this documentation
- Check the JSON schema endpoints for validation rules
- Contact support with audit log references for troubleshooting