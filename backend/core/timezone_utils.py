"""
Timezone utilities for Lily AI - Ensures consistent EST/EDT timezone handling
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    pytz = None

from backend.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# EST timezone object - fallback to UTC offset if pytz not available
if PYTZ_AVAILABLE:
    EST = pytz.timezone(settings.timezone)
else:
    # Use fixed UTC-5 offset for EST (without DST support)
    # In production, should use pytz or zoneinfo for proper DST handling
    EST = timezone(timedelta(hours=-5), "EST")

def get_lily_timezone():
    """Get Lily's configured timezone (EST/EDT)"""
    return EST

def now_in_est() -> datetime:
    """Get current time in Lily's timezone (EST/EDT)"""
    return datetime.now(EST)

def utc_to_est(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to EST"""
    if utc_dt.tzinfo is None:
        # Assume UTC if no timezone info
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(EST)

def est_to_utc(est_dt: datetime) -> datetime:
    """Convert EST datetime to UTC"""
    if est_dt.tzinfo is None:
        # Assume EST if no timezone info
        est_dt = EST.localize(est_dt)
    return est_dt.astimezone(timezone.utc)

def format_lily_timestamp(dt: Optional[datetime] = None) -> str:
    """Format timestamp in Lily's preferred format (EST)"""
    if dt is None:
        dt = now_in_est()
    elif dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        # Convert UTC to EST if no timezone or UTC
        dt = utc_to_est(dt.replace(tzinfo=timezone.utc))
    else:
        # Convert to EST
        dt = dt.astimezone(EST)
    
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")

def get_lily_business_hours():
    """Get Lily's business hours in EST"""
    return {
        "start_hour": 9,  # 9 AM EST
        "end_hour": 17,   # 5 PM EST
        "timezone": "EST/EDT",
        "timezone_obj": EST
    }

def is_lily_business_hours(dt: Optional[datetime] = None) -> bool:
    """Check if current time (or provided time) is within Lily's business hours"""
    if dt is None:
        dt = now_in_est()
    elif dt.tzinfo != EST:
        dt = dt.astimezone(EST)
    
    business_hours = get_lily_business_hours()
    hour = dt.hour
    
    # Check if it's a weekday (Monday=0, Sunday=6)
    is_weekday = dt.weekday() < 5
    
    # Check if within business hours
    is_business_time = business_hours["start_hour"] <= hour < business_hours["end_hour"]
    
    return is_weekday and is_business_time

def get_next_business_hour() -> datetime:
    """Get the next business hour in EST"""
    current = now_in_est()
    business_hours = get_lily_business_hours()
    
    # If it's weekend, go to next Monday 9 AM
    if current.weekday() >= 5:  # Saturday or Sunday
        days_until_monday = 7 - current.weekday()
        next_business = current.replace(
            hour=business_hours["start_hour"], 
            minute=0, 
            second=0, 
            microsecond=0
        )
        next_business += timedelta(days=days_until_monday)
        return next_business
    
    # If it's before business hours, start at 9 AM today
    if current.hour < business_hours["start_hour"]:
        return current.replace(
            hour=business_hours["start_hour"], 
            minute=0, 
            second=0, 
            microsecond=0
        )
    
    # If it's after business hours, start at 9 AM tomorrow
    if current.hour >= business_hours["end_hour"]:
        from datetime import timedelta
        next_day = current + timedelta(days=1)
        # Check if tomorrow is weekend
        if next_day.weekday() >= 5:
            return get_next_business_hour()  # Recursive call for weekend
        
        return next_day.replace(
            hour=business_hours["start_hour"], 
            minute=0, 
            second=0, 
            microsecond=0
        )
    
    # Currently in business hours
    return current

# Logging with EST timestamps
class ESTFormatter(logging.Formatter):
    """Custom log formatter that shows EST timestamps"""
    
    def formatTime(self, record, datefmt=None):
        # Convert to EST
        est_time = utc_to_est(datetime.fromtimestamp(record.created, tz=timezone.utc))
        
        if datefmt:
            return est_time.strftime(datefmt)
        else:
            return est_time.strftime("%Y-%m-%d %H:%M:%S EST")

def setup_lily_logging():
    """Setup logging with EST timestamps for Lily"""
    # Get root logger
    root_logger = logging.getLogger()
    
    # Create EST formatter
    formatter = ESTFormatter(
        fmt='%(asctime)s EST - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Update existing handlers
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
    
    logger.info(f"Lily timezone set to: {settings.timezone}")
    logger.info(f"Current time: {format_lily_timestamp()}")
    logger.info(f"Business hours: 9 AM - 5 PM EST/EDT, Monday-Friday")

if __name__ == "__main__":
    # Test timezone functionality
    print(f"Lily's timezone: {settings.timezone}")
    print(f"Current time in EST: {format_lily_timestamp()}")
    print(f"Is business hours: {is_lily_business_hours()}")
    print(f"Next business hour: {format_lily_timestamp(get_next_business_hour())}")