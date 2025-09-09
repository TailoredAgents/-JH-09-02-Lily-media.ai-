# PW-WEATHER-ADD-001: Weather API Documentation

## Overview

The Weather API provides automatic job rescheduling based on configurable weather thresholds. Jobs are automatically rescheduled when weather conditions exceed tenant-specific safety limits.

## Configuration

### Weather Thresholds

Configure weather thresholds via the settings API (`/api/v1/settings/weather`):

```json
{
  "bad_weather_threshold": {
    "rain_probability": 70.0,
    "wind_speed_mph": 25.0, 
    "temp_low_f": 35.0
  },
  "lookahead_days": 3,
  "auto_reschedule": true,
  "buffer_minutes": 60,
  "business_hours": {
    "monday": {"start": "08:00", "end": "17:00"},
    "tuesday": {"start": "08:00", "end": "17:00"},
    "wednesday": {"start": "08:00", "end": "17:00"},
    "thursday": {"start": "08:00", "end": "17:00"}, 
    "friday": {"start": "08:00", "end": "17:00"},
    "saturday": {"start": "08:00", "end": "16:00"},
    "sunday": {"start": "closed", "end": "closed"}
  }
}
```

### Environment Configuration

Set weather provider via environment variable:
- `WEATHER_PROVIDER=openweather` (requires `OPENWEATHER_API_KEY`)
- `WEATHER_PROVIDER=mock` (for development/testing)

## API Endpoints

### Manual Weather Check

**GET** `/api/v1/weather/check?job_id={job_id}`

Check weather forecast for a specific job and get rescheduling recommendations.

**Response:**
```json
{
  "job_id": "job-123",
  "job_scheduled_for": "2024-01-15T10:00:00Z",
  "job_address": "123 Main St, Atlanta, GA",
  "weather_forecast": [
    {
      "date": "2024-01-15T00:00:00Z",
      "temperature_high_f": 75.0,
      "temperature_low_f": 30.0,
      "rain_probability": 80.0,
      "wind_speed_mph": 15.0,
      "condition": "cloudy",
      "is_bad_weather": true
    }
  ],
  "weather_risk_assessment": {
    "overall_risk": true,
    "risky_days": [
      {
        "date": "2024-01-15T00:00:00Z",
        "reasons": ["High rain probability: 80%", "Low temperature: 30.0°F"]
      }
    ],
    "safe_days": ["2024-01-16T00:00:00Z"],
    "next_safe_day": "2024-01-16T00:00:00Z"
  },
  "reschedule_recommended": true,
  "next_safe_date": "2024-01-16T08:30:00Z"
}
```

### Admin Rescheduling Trigger

**POST** `/api/v1/weather/run`

Manually trigger weather-based rescheduling for organization (admin only).

**Request Body:**
```json
{
  "organization_id": "org-456", // Optional, defaults to current org
  "force": false // Override auto_reschedule=false setting
}
```

**Response:**
```json
{
  "organization_id": "org-456",
  "total_jobs_checked": 5,
  "jobs_rescheduled": 2,
  "jobs_failed": 0,
  "reschedule_results": [
    {
      "job_id": "job-123",
      "original_date": "2024-01-15T10:00:00Z",
      "new_date": "2024-01-16T08:30:00Z",
      "reschedule_reason": "Automatically rescheduled due to weather: 80% chance of rain, Low temperature (30.0°F)",
      "success": true,
      "error_message": null
    }
  ]
}
```

### Single Job Rescheduling

**POST** `/api/v1/weather/reschedule/job/{job_id}`

Check and reschedule a single job based on weather conditions.

**Response:**
```json
{
  "job_id": "job-123",
  "action_taken": "rescheduled", // or "none" or "failed"
  "original_date": "2024-01-15T10:00:00Z",
  "new_date": "2024-01-16T08:30:00Z", 
  "reschedule_reason": "Automatically rescheduled due to weather: 80% chance of rain",
  "success": true,
  "error_message": null
}
```

### Service Status

**GET** `/api/v1/weather/status`

Check weather service health and configuration.

**Response:**
```json
{
  "weather_provider": "OpenWeatherMapProvider",
  "provider_configured": true,
  "service_available": true
}
```

## Automated Rescheduling

### Trigger Conditions

Jobs are automatically rescheduled when:
- Rain probability ≥ configured threshold
- Wind speed ≥ configured threshold  
- Temperature ≤ configured minimum
- Severe weather conditions (thunderstorms, snow, sleet, heavy rain)

### Rescheduling Logic

1. **Weather Check**: Forecast is retrieved for job's scheduled date
2. **Risk Assessment**: Weather conditions compared against thresholds
3. **Safe Slot Finding**: Next available slot within business hours
4. **Buffer Time**: Configured buffer minutes applied between jobs
5. **Job Update**: Job rescheduled with audit logging and notifications

### Business Hours Constraints

- Jobs only rescheduled to business hours slots
- Closed days (e.g., Sunday) are skipped
- Buffer time prevents scheduling conflicts
- Duration requirements respected

## Error Handling

- **404**: Job not found or not accessible
- **400**: Invalid job status, no scheduled date, or disabled rescheduling
- **403**: Insufficient permissions for organization
- **500**: Weather service errors or rescheduling failures

All errors include descriptive messages for troubleshooting.

## Integration Notes

### Background Tasks

For production deployment, implement scheduled background tasks to run:
```python
from backend.api.weather import scheduled_weather_rescheduling_task
await scheduled_weather_rescheduling_task(organization_id, db)
```

### Audit Logging

All rescheduling actions are logged with:
- Event type: `job_rescheduled`
- Weather data and risk factors
- Original vs new scheduling times
- User ID (for manual) or system (for automated)

### Notifications

Rescheduling triggers notification events through the notification service for customer communication.