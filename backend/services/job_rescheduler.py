"""
PW-WEATHER-ADD-001: Job rescheduler service

Handles automatic job rescheduling based on weather conditions.
Scans upcoming jobs, evaluates weather forecasts, and reschedules jobs
that exceed weather thresholds to next safe time slots.
"""

import asyncio
from datetime import datetime, timedelta, timezone, time
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.db.models import Job
from backend.services.weather_service import WeatherService, get_weather_service
from backend.services.settings_resolver import WeatherSettings, get_weather_settings
from backend.services.job_service import JobService, JobUpdateRequest
from backend.core.audit_logger import get_audit_logger, AuditEventType


@dataclass
class RescheduleResult:
    """Result of a job rescheduling operation"""
    job_id: str
    original_date: datetime
    new_date: Optional[datetime]
    reschedule_reason: str
    success: bool
    error_message: Optional[str] = None


@dataclass  
class BusinessHours:
    """Business hours for a specific day"""
    start_time: Optional[time]
    end_time: Optional[time]
    is_closed: bool = False
    
    @classmethod
    def from_string(cls, start_str: str, end_str: str) -> 'BusinessHours':
        """Create BusinessHours from time strings"""
        if start_str.lower() == "closed" or end_str.lower() == "closed":
            return cls(start_time=None, end_time=None, is_closed=True)
            
        try:
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
            return cls(start_time=start_time, end_time=end_time)
        except ValueError:
            # Default to 8 AM - 5 PM if parsing fails
            return cls(
                start_time=time(8, 0),
                end_time=time(17, 0)
            )


class JobRescheduler:
    """
    PW-WEATHER-ADD-001: Automatic job rescheduling based on weather
    
    Scans upcoming jobs and automatically reschedules them when weather
    conditions exceed configured thresholds.
    """
    
    def __init__(
        self,
        weather_service: Optional[WeatherService] = None,
        job_service: Optional[JobService] = None
    ):
        self.weather_service = weather_service or get_weather_service()
        self.job_service = job_service or JobService()
        self.audit_logger = get_audit_logger()
    
    async def run_rescheduling_check(
        self,
        organization_id: str,
        db: Session,
        user_id: Optional[int] = None
    ) -> List[RescheduleResult]:
        """
        Run weather-based rescheduling check for an organization
        
        Args:
            organization_id: Organization to check jobs for
            db: Database session
            user_id: User ID for audit logging
            
        Returns:
            List of rescheduling results
        """
        # Get organization weather settings
        weather_settings = get_weather_settings(
            db=db,
            org_id=organization_id
        )
        
        if not isinstance(weather_settings, WeatherSettings):
            # No weather settings configured, skip rescheduling
            return []
            
        if not weather_settings.auto_reschedule:
            # Auto-rescheduling disabled
            return []
        
        # Get upcoming jobs within lookahead window
        upcoming_jobs = self._get_upcoming_jobs(
            organization_id=organization_id,
            lookahead_days=weather_settings.lookahead_days,
            db=db
        )
        
        if not upcoming_jobs:
            return []
        
        results = []
        
        for job in upcoming_jobs:
            try:
                result = await self._evaluate_and_reschedule_job(
                    job=job,
                    weather_settings=weather_settings,
                    db=db,
                    user_id=user_id
                )
                
                if result:
                    results.append(result)
                    
            except Exception as e:
                # Log error and continue with other jobs
                error_result = RescheduleResult(
                    job_id=job.id,
                    original_date=job.scheduled_for,
                    new_date=None,
                    reschedule_reason=f"Error during rescheduling: {str(e)}",
                    success=False,
                    error_message=str(e)
                )
                results.append(error_result)
        
        return results
    
    def _get_upcoming_jobs(
        self,
        organization_id: str,
        lookahead_days: int,
        db: Session
    ) -> List[Job]:
        """Get upcoming scheduled jobs within lookahead window"""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(days=lookahead_days)
        
        return db.query(Job).filter(
            and_(
                Job.organization_id == organization_id,
                Job.status == "scheduled",
                Job.scheduled_for >= start_time,
                Job.scheduled_for <= end_time,
                Job.scheduled_for.isnot(None)
            )
        ).order_by(Job.scheduled_for).all()
    
    async def _evaluate_and_reschedule_job(
        self,
        job: Job,
        weather_settings: WeatherSettings,
        db: Session,
        user_id: Optional[int]
    ) -> Optional[RescheduleResult]:
        """Evaluate weather for a job and reschedule if necessary"""
        if not job.scheduled_for:
            return None
            
        # Get weather forecast for job date
        # For now, using fixed coordinates - in production, would geocode address
        latitude, longitude = self._geocode_address(job.address)
        
        forecasts = await self.weather_service.get_forecast(
            latitude=latitude,
            longitude=longitude,
            date_range=weather_settings.lookahead_days
        )
        
        if not forecasts:
            return None
            
        # Find forecast for job date
        job_date = job.scheduled_for.date()
        job_forecast = None
        
        for forecast in forecasts:
            if forecast.date.date() == job_date:
                job_forecast = forecast
                break
        
        if not job_forecast:
            return None
            
        # Check if weather exceeds thresholds
        if not job_forecast.is_bad_weather(weather_settings.bad_weather_threshold):
            # Weather is fine, no rescheduling needed
            return None
            
        # Weather is bad, find next safe slot
        next_safe_date = self._find_next_safe_slot(
            forecasts=forecasts,
            weather_settings=weather_settings,
            current_job_duration=job.duration_minutes or 120
        )
        
        if not next_safe_date:
            # No safe slot found within forecast window
            return RescheduleResult(
                job_id=job.id,
                original_date=job.scheduled_for,
                new_date=None,
                reschedule_reason="No safe weather window found within forecast period",
                success=False
            )
        
        # Reschedule the job
        reschedule_reason = self._generate_reschedule_reason(
            job_forecast, weather_settings.bad_weather_threshold
        )
        
        try:
            rescheduled_job = self.job_service.reschedule_job(
                job=job,
                new_scheduled_time=next_safe_date,
                reason=reschedule_reason,
                db=db,
                user_id=user_id or 0  # System user for automated rescheduling
            )
            
            # Log audit event
            await self.audit_logger.log_event(
                event_type=AuditEventType.JOB_RESCHEDULED,
                entity_id=job.id,
                entity_type="job",
                organization_id=job.organization_id,
                user_id=user_id,
                details={
                    "original_date": job.scheduled_for.isoformat(),
                    "new_date": next_safe_date.isoformat(),
                    "reason": reschedule_reason,
                    "automated": True,
                    "weather_data": {
                        "rain_probability": job_forecast.rain_probability,
                        "wind_speed": job_forecast.wind_speed_mph,
                        "temperature": job_forecast.temperature_low_f,
                        "condition": job_forecast.condition
                    }
                }
            )
            
            return RescheduleResult(
                job_id=job.id,
                original_date=job.scheduled_for,
                new_date=next_safe_date,
                reschedule_reason=reschedule_reason,
                success=True
            )
            
        except Exception as e:
            return RescheduleResult(
                job_id=job.id,
                original_date=job.scheduled_for,
                new_date=None,
                reschedule_reason=reschedule_reason,
                success=False,
                error_message=str(e)
            )
    
    def _geocode_address(self, address: str) -> Tuple[float, float]:
        """
        Geocode address to latitude/longitude
        
        For now, returns fixed coordinates for Atlanta, GA.
        In production, would use actual geocoding service.
        """
        # Default to Atlanta, GA coordinates
        return 33.7490, -84.3880
    
    def _find_next_safe_slot(
        self,
        forecasts: List,
        weather_settings: WeatherSettings,
        current_job_duration: int
    ) -> Optional[datetime]:
        """Find next safe weather window that respects business hours"""
        for forecast in forecasts:
            # Skip if weather is still bad
            if forecast.is_bad_weather(weather_settings.bad_weather_threshold):
                continue
            
            # Find available slot within business hours
            safe_slot = self._find_business_hour_slot(
                date=forecast.date,
                duration_minutes=current_job_duration,
                weather_settings=weather_settings
            )
            
            if safe_slot:
                return safe_slot
        
        return None
    
    def _find_business_hour_slot(
        self,
        date: datetime,
        duration_minutes: int,
        weather_settings: WeatherSettings
    ) -> Optional[datetime]:
        """Find available slot within business hours for given date"""
        weekday = date.strftime("%A").lower()
        
        if weekday not in weather_settings.business_hours:
            return None
            
        day_hours_config = weather_settings.business_hours[weekday]
        business_hours = BusinessHours.from_string(
            day_hours_config["start"],
            day_hours_config["end"]
        )
        
        if business_hours.is_closed:
            return None
        
        # Start at business open time
        start_time = datetime.combine(
            date.date(),
            business_hours.start_time,
            timezone.utc
        )
        
        # End at business close time minus job duration
        end_time = datetime.combine(
            date.date(),
            business_hours.end_time,
            timezone.utc
        ) - timedelta(minutes=duration_minutes)
        
        # Apply buffer time
        start_time += timedelta(minutes=weather_settings.buffer_minutes)
        
        if start_time <= end_time:
            return start_time
            
        return None
    
    def _generate_reschedule_reason(self, forecast, threshold) -> str:
        """Generate human-readable reschedule reason"""
        reasons = []
        
        if forecast.rain_probability >= threshold.rain_probability:
            reasons.append(f"{forecast.rain_probability}% chance of rain")
            
        if forecast.wind_speed_mph >= threshold.wind_speed_mph:
            reasons.append(f"{forecast.wind_speed_mph} mph winds")
            
        if forecast.temperature_low_f <= threshold.temp_low_f:
            reasons.append(f"Low temperature ({forecast.temperature_low_f}°F)")
        
        reason_text = ", ".join(reasons)
        return f"Automatically rescheduled due to weather: {reason_text}"
    
    async def check_single_job(
        self,
        job_id: str,
        db: Session,
        user_id: Optional[int] = None
    ) -> Optional[RescheduleResult]:
        """
        Check weather for a single job and reschedule if necessary
        
        Args:
            job_id: Job ID to check
            db: Database session
            user_id: User ID for audit logging
            
        Returns:
            Rescheduling result if action taken, None if no action needed
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.status != "scheduled":
            return None
            
        # Get organization weather settings
        weather_settings = get_weather_settings(
            db=db,
            org_id=job.organization_id
        )
        
        if not isinstance(weather_settings, WeatherSettings):
            return None
            
        return await self._evaluate_and_reschedule_job(
            job=job,
            weather_settings=weather_settings,
            db=db,
            user_id=user_id
        )


# Global service instance
_job_rescheduler_instance: Optional[JobRescheduler] = None


def get_job_rescheduler() -> JobRescheduler:
    """Get global job rescheduler instance"""
    global _job_rescheduler_instance
    if _job_rescheduler_instance is None:
        _job_rescheduler_instance = JobRescheduler()
    return _job_rescheduler_instance


def set_job_rescheduler(rescheduler: JobRescheduler) -> None:
    """Set global job rescheduler instance (mainly for testing)"""
    global _job_rescheduler_instance
    _job_rescheduler_instance = rescheduler