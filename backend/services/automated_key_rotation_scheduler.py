"""
Automated Key Rotation Scheduler

Provides automated scheduling and execution of encryption key rotation
based on configured intervals and compliance requirements.
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from backend.services.key_rotation_service import (
    KeyRotationService, KeyType, KeyRotationStatus, get_key_rotation_service
)
from backend.db.database import get_db
from backend.core.config import get_settings
from backend.core.audit_logger import AuditLogger, AuditEventType

logger = logging.getLogger(__name__)
settings = get_settings()

class SchedulerStatus(Enum):
    """Scheduler operational status"""
    ACTIVE = "active"
    PAUSED = "paused" 
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class ScheduledRotation:
    """Scheduled key rotation event"""
    key_type: KeyType
    scheduled_time: datetime
    priority: str  # high, normal, low
    retry_count: int = 0
    max_retries: int = 3
    last_attempt: Optional[datetime] = None
    error_message: Optional[str] = None

@dataclass 
class SchedulerConfig:
    """Configuration for the automated scheduler"""
    enabled: bool = True
    check_interval_minutes: int = 60  # Check every hour
    max_concurrent_rotations: int = 2
    maintenance_window_start: int = 2  # 2 AM UTC
    maintenance_window_duration: int = 4  # 4 hours
    notification_emails: List[str] = None
    emergency_contact: str = "security@lilymedia.ai"

class AutomatedKeyRotationScheduler:
    """
    Automated scheduler for encryption key rotation
    
    Monitors key ages, schedules rotations, and executes them during
    maintenance windows to ensure continuous security compliance.
    """
    
    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()
        self.key_service = get_key_rotation_service()
        self.audit_logger = AuditLogger()
        
        self.status = SchedulerStatus.ACTIVE if self.config.enabled else SchedulerStatus.PAUSED
        self.scheduled_rotations: Dict[str, ScheduledRotation] = {}
        self.active_rotations: Set[str] = set()
        self.last_check_time: Optional[datetime] = None
        self.error_count = 0
        
        # Statistics
        self.stats = {
            "total_rotations_scheduled": 0,
            "total_rotations_completed": 0,
            "total_rotations_failed": 0,
            "average_rotation_duration": 0.0,
            "last_successful_rotation": None,
            "uptime_start": datetime.now(timezone.utc)
        }
        
        logger.info("Automated key rotation scheduler initialized")
    
    async def start_scheduler(self):
        """Start the automated scheduler"""
        if not self.config.enabled:
            logger.warning("Scheduler is disabled in configuration")
            return
            
        logger.info("Starting automated key rotation scheduler")
        self.status = SchedulerStatus.ACTIVE
        
        # Log scheduler startup
        self.audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_EVENT,
            user_id=None,
            resource="key_rotation_scheduler",
            action="scheduler_start",
            outcome="success",
            details={
                "config": {
                    "check_interval_minutes": self.config.check_interval_minutes,
                    "max_concurrent_rotations": self.config.max_concurrent_rotations,
                    "maintenance_window": {
                        "start": self.config.maintenance_window_start,
                        "duration": self.config.maintenance_window_duration
                    }
                }
            }
        )
        
        # Main scheduler loop
        while self.status == SchedulerStatus.ACTIVE:
            try:
                await self._scheduler_cycle()
                
                # Wait for next check interval
                await asyncio.sleep(self.config.check_interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Scheduler cycle error: {e}")
                self.error_count += 1
                
                if self.error_count >= 3:
                    self.status = SchedulerStatus.ERROR
                    await self._send_error_notification(
                        f"Scheduler stopped due to repeated errors: {e}"
                    )
                    break
                
                # Short backoff on error
                await asyncio.sleep(300)  # 5 minutes
    
    async def _scheduler_cycle(self):
        """Execute one scheduler cycle"""
        self.last_check_time = datetime.now(timezone.utc)
        logger.debug("Starting scheduler cycle")
        
        try:
            # 1. Check for overdue keys and schedule rotations
            await self._check_and_schedule_rotations()
            
            # 2. Execute scheduled rotations if in maintenance window
            await self._execute_scheduled_rotations()
            
            # 3. Clean up completed/failed rotations
            await self._cleanup_completed_rotations()
            
            # 4. Update statistics
            self._update_statistics()
            
            # Reset error count on successful cycle
            self.error_count = 0
            
        except Exception as e:
            logger.error(f"Error in scheduler cycle: {e}")
            raise
    
    async def _check_and_schedule_rotations(self):
        """Check key ages and schedule necessary rotations"""
        try:
            schedule = self.key_service.get_key_rotation_schedule()
            
            for key_type_str, key_info in schedule["key_types"].items():
                key_type = KeyType(key_type_str)
                
                # Skip if already scheduled or in progress
                if key_type_str in self.scheduled_rotations:
                    continue
                if key_type_str in self.active_rotations:
                    continue
                
                # Check if rotation is needed
                needs_rotation = False
                priority = "normal"
                
                if key_info.get("status") == "no_keys":
                    needs_rotation = True
                    priority = "high"
                elif key_info.get("is_overdue"):
                    needs_rotation = True
                    # Check how overdue
                    age_days = key_info.get("oldest_key_age_days", 0)
                    rotation_interval = key_info.get("rotation_interval_days", 90)
                    
                    if age_days > (rotation_interval * 1.5):
                        priority = "high"  # Severely overdue
                    elif age_days > (rotation_interval * 1.2):
                        priority = "normal"  # Moderately overdue
                
                if needs_rotation:
                    await self._schedule_rotation(key_type, priority)
            
        except Exception as e:
            logger.error(f"Error checking rotation schedule: {e}")
            raise
    
    async def _schedule_rotation(self, key_type: KeyType, priority: str = "normal"):
        """Schedule a key rotation"""
        try:
            # Calculate optimal schedule time
            now = datetime.now(timezone.utc)
            
            if priority == "high":
                # Schedule immediately for high priority
                scheduled_time = now + timedelta(minutes=5)
            else:
                # Schedule for next maintenance window
                scheduled_time = self._next_maintenance_window(now)
            
            rotation = ScheduledRotation(
                key_type=key_type,
                scheduled_time=scheduled_time,
                priority=priority
            )
            
            self.scheduled_rotations[key_type.value] = rotation
            self.stats["total_rotations_scheduled"] += 1
            
            logger.info(f"Scheduled {priority} priority rotation for {key_type.value} at {scheduled_time}")
            
            # Audit log
            self.audit_logger.log_event(
                event_type=AuditEventType.SECURITY_VIOLATION,  # Closest available
                user_id=None,
                resource=f"key_rotation_{key_type.value}",
                action="rotation_scheduled",
                outcome="success",
                details={
                    "key_type": key_type.value,
                    "priority": priority,
                    "scheduled_time": scheduled_time.isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error scheduling rotation for {key_type.value}: {e}")
            raise
    
    async def _execute_scheduled_rotations(self):
        """Execute rotations that are due"""
        now = datetime.now(timezone.utc)
        
        # Check if we're in maintenance window or have high priority rotations
        in_maintenance = self._is_maintenance_window(now)
        
        for key_type_str, rotation in list(self.scheduled_rotations.items()):
            # Execute if:
            # 1. High priority (immediate)
            # 2. Scheduled time has passed and we're in maintenance window
            # 3. Severely overdue (emergency)
            should_execute = (
                rotation.priority == "high" or
                (rotation.scheduled_time <= now and in_maintenance) or
                (rotation.last_attempt and 
                 (now - rotation.last_attempt).total_seconds() > 86400)  # 24h emergency
            )
            
            if should_execute and len(self.active_rotations) < self.config.max_concurrent_rotations:
                await self._execute_rotation(rotation)
    
    async def _execute_rotation(self, rotation: ScheduledRotation):
        """Execute a single key rotation"""
        key_type_str = rotation.key_type.value
        
        try:
            logger.info(f"Executing rotation for {key_type_str} (attempt {rotation.retry_count + 1})")
            
            self.active_rotations.add(key_type_str)
            rotation.last_attempt = datetime.now(timezone.utc)
            rotation.retry_count += 1
            
            start_time = datetime.now(timezone.utc)
            
            # Step 1: Schedule the rotation (generate new key)
            schedule_result = self.key_service.schedule_key_rotation(rotation.key_type, force=True)
            
            if schedule_result["action"] != "rotation_scheduled":
                logger.warning(f"Rotation not scheduled for {key_type_str}: {schedule_result['action']}")
                return
            
            event_id = schedule_result["event_id"]
            
            # Step 2: Execute the rotation (migrate data)
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                execute_result = self.key_service.execute_key_rotation(
                    db=db,
                    event_id=event_id,
                    batch_size=1000
                )
                
                if execute_result["status"] == "completed":
                    # Success
                    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                    
                    logger.info(f"Successfully completed rotation for {key_type_str} in {duration:.2f}s")
                    
                    self.stats["total_rotations_completed"] += 1
                    self.stats["last_successful_rotation"] = datetime.now(timezone.utc)
                    
                    # Update average duration
                    total_completed = self.stats["total_rotations_completed"]
                    current_avg = self.stats["average_rotation_duration"]
                    self.stats["average_rotation_duration"] = ((current_avg * (total_completed - 1)) + duration) / total_completed
                    
                    # Remove from scheduled
                    if key_type_str in self.scheduled_rotations:
                        del self.scheduled_rotations[key_type_str]
                    
                    # Audit log
                    self.audit_logger.log_event(
                        event_type=AuditEventType.SECURITY_VIOLATION,
                        user_id=None,
                        resource=f"key_rotation_{key_type_str}",
                        action="rotation_completed",
                        outcome="success",
                        details={
                            "event_id": event_id,
                            "duration_seconds": duration,
                            "records_migrated": execute_result.get("records_migrated", 0)
                        }
                    )
                    
                else:
                    raise Exception(f"Rotation failed with status: {execute_result['status']}")
                    
            finally:
                db.close()
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Rotation failed for {key_type_str}: {error_msg}")
            
            rotation.error_message = error_msg
            self.stats["total_rotations_failed"] += 1
            
            # Retry logic
            if rotation.retry_count < rotation.max_retries:
                # Exponential backoff
                backoff_minutes = (2 ** rotation.retry_count) * 30  # 30min, 1h, 2h
                retry_time = datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)
                rotation.scheduled_time = retry_time
                
                logger.info(f"Will retry rotation for {key_type_str} at {retry_time}")
            else:
                # Max retries exceeded - send alert
                logger.error(f"Max retries exceeded for {key_type_str} rotation")
                await self._send_error_notification(
                    f"Key rotation failed for {key_type_str} after {rotation.max_retries} attempts: {error_msg}"
                )
                
                # Remove from schedule to prevent infinite retries
                if key_type_str in self.scheduled_rotations:
                    del self.scheduled_rotations[key_type_str]
            
            # Audit log failure
            self.audit_logger.log_event(
                event_type=AuditEventType.SECURITY_VIOLATION,
                user_id=None,
                resource=f"key_rotation_{key_type_str}",
                action="rotation_failed",
                outcome="failure",
                details={
                    "error": error_msg,
                    "retry_count": rotation.retry_count,
                    "max_retries": rotation.max_retries
                }
            )
            
        finally:
            self.active_rotations.discard(key_type_str)
    
    async def _cleanup_completed_rotations(self):
        """Clean up old completed rotation records"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        completed_rotations = []
        for key_type_str, rotation in list(self.scheduled_rotations.items()):
            if (rotation.retry_count >= rotation.max_retries and 
                rotation.last_attempt and 
                rotation.last_attempt < cutoff_time):
                completed_rotations.append(key_type_str)
        
        for key_type_str in completed_rotations:
            del self.scheduled_rotations[key_type_str]
            logger.debug(f"Cleaned up completed rotation record for {key_type_str}")
    
    def _next_maintenance_window(self, from_time: datetime) -> datetime:
        """Calculate next maintenance window start time"""
        # Get next occurrence of maintenance window start hour
        start_hour = self.config.maintenance_window_start
        
        next_window = from_time.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        
        # If we've passed today's window, schedule for tomorrow
        if next_window <= from_time:
            next_window += timedelta(days=1)
        
        return next_window
    
    def _is_maintenance_window(self, check_time: datetime) -> bool:
        """Check if current time is within maintenance window"""
        hour = check_time.hour
        start_hour = self.config.maintenance_window_start
        end_hour = (start_hour + self.config.maintenance_window_duration) % 24
        
        if start_hour <= end_hour:
            # Window doesn't cross midnight
            return start_hour <= hour < end_hour
        else:
            # Window crosses midnight
            return hour >= start_hour or hour < end_hour
    
    def _update_statistics(self):
        """Update internal statistics"""
        self.stats["uptime_hours"] = (
            datetime.now(timezone.utc) - self.stats["uptime_start"]
        ).total_seconds() / 3600
        
        self.stats["scheduled_rotations_count"] = len(self.scheduled_rotations)
        self.stats["active_rotations_count"] = len(self.active_rotations)
        self.stats["error_count"] = self.error_count
    
    async def _send_error_notification(self, message: str):
        """Send error notification to administrators"""
        try:
            logger.critical(f"KEY ROTATION ALERT: {message}")
            
            # In production, implement actual notification system
            # For now, just log the alert
            self.audit_logger.log_event(
                event_type=AuditEventType.SECURITY_VIOLATION,
                user_id=None,
                resource="key_rotation_scheduler",
                action="error_notification",
                outcome="success",
                details={
                    "message": message,
                    "emergency_contact": self.config.emergency_contact
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status and statistics"""
        return {
            "status": self.status.value,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "scheduled_rotations": len(self.scheduled_rotations),
            "active_rotations": len(self.active_rotations),
            "config": {
                "enabled": self.config.enabled,
                "check_interval_minutes": self.config.check_interval_minutes,
                "max_concurrent_rotations": self.config.max_concurrent_rotations,
                "maintenance_window": {
                    "start": self.config.maintenance_window_start,
                    "duration": self.config.maintenance_window_duration
                }
            },
            "statistics": self.stats,
            "upcoming_rotations": [
                {
                    "key_type": r.key_type.value,
                    "scheduled_time": r.scheduled_time.isoformat(),
                    "priority": r.priority,
                    "retry_count": r.retry_count
                }
                for r in self.scheduled_rotations.values()
            ]
        }
    
    async def pause_scheduler(self):
        """Pause the scheduler"""
        logger.info("Pausing key rotation scheduler")
        self.status = SchedulerStatus.PAUSED
        
        self.audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_EVENT,
            user_id=None,
            resource="key_rotation_scheduler",
            action="scheduler_paused",
            outcome="success",
            details={}
        )
    
    async def resume_scheduler(self):
        """Resume the scheduler"""
        logger.info("Resuming key rotation scheduler")
        self.status = SchedulerStatus.ACTIVE
        
        self.audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_EVENT,
            user_id=None,
            resource="key_rotation_scheduler",
            action="scheduler_resumed",
            outcome="success",
            details={}
        )

# Global scheduler instance
_scheduler_instance: Optional[AutomatedKeyRotationScheduler] = None

def get_key_rotation_scheduler(config: Optional[SchedulerConfig] = None) -> AutomatedKeyRotationScheduler:
    """Get the global key rotation scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = AutomatedKeyRotationScheduler(config)
    return _scheduler_instance

async def start_automated_key_rotation():
    """Start the automated key rotation scheduler"""
    scheduler = get_key_rotation_scheduler()
    await scheduler.start_scheduler()