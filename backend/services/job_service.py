"""
PW-DM-ADD-001: Job Service

Service for managing pressure washing job lifecycle: creation from accepted quotes,
scheduling, status updates, and crew management.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from backend.db.models import Job, Quote, Lead, User, Organization
from backend.core.audit_logger import get_audit_logger, AuditEventType
from backend.services.notification_service import get_notification_service, NotificationType, NotificationPriority

logger = logging.getLogger(__name__)


class JobCreationRequest:
    """Request object for creating jobs"""
    
    def __init__(
        self,
        organization_id: str,
        service_type: str,
        address: str,
        estimated_cost: float,
        customer_name: Optional[str] = None,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
        quote_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        scheduled_for: Optional[datetime] = None,
        duration_minutes: Optional[int] = None,
        service_details: Optional[Dict[str, Any]] = None,
        crew: Optional[Dict[str, Any]] = None,
        crew_notes: Optional[str] = None,
        internal_notes: Optional[str] = None,
        priority: str = "normal",
        currency: str = "USD"
    ):
        self.organization_id = organization_id
        self.service_type = service_type
        self.address = address
        self.estimated_cost = estimated_cost
        self.customer_name = customer_name
        self.customer_email = customer_email
        self.customer_phone = customer_phone
        self.quote_id = quote_id
        self.lead_id = lead_id
        self.scheduled_for = scheduled_for
        self.duration_minutes = duration_minutes
        self.service_details = service_details or {}
        self.crew = crew or {}
        self.crew_notes = crew_notes
        self.internal_notes = internal_notes
        self.priority = priority
        self.currency = currency


class JobUpdateRequest:
    """Request object for updating jobs"""
    
    def __init__(
        self,
        scheduled_for: Optional[datetime] = None,
        duration_minutes: Optional[int] = None,
        crew: Optional[Dict[str, Any]] = None,
        crew_notes: Optional[str] = None,
        status: Optional[str] = None,
        completion_notes: Optional[str] = None,
        completion_photos: Optional[List[str]] = None,
        customer_satisfaction: Optional[int] = None,
        actual_cost: Optional[float] = None,
        internal_notes: Optional[str] = None,
        priority: Optional[str] = None
    ):
        self.scheduled_for = scheduled_for
        self.duration_minutes = duration_minutes
        self.crew = crew
        self.crew_notes = crew_notes
        self.status = status
        self.completion_notes = completion_notes
        self.completion_photos = completion_photos
        self.customer_satisfaction = customer_satisfaction
        self.actual_cost = actual_cost
        self.internal_notes = internal_notes
        self.priority = priority


class JobService:
    """Service for managing pressure washing job operations"""
    
    def __init__(self):
        self.audit_logger = get_audit_logger()
        self.notification_service = get_notification_service()
    
    def create_job_from_quote(
        self, 
        quote: Quote, 
        scheduled_for: Optional[datetime],
        duration_minutes: Optional[int],
        db: Session, 
        user_id: int,
        crew: Optional[Dict[str, Any]] = None,
        crew_notes: Optional[str] = None,
        internal_notes: Optional[str] = None
    ) -> Job:
        """
        Create a job from an accepted quote
        
        Args:
            quote: Accepted quote to convert to job
            scheduled_for: When the job is scheduled
            duration_minutes: Estimated job duration
            db: Database session
            user_id: User creating the job
            crew: Optional crew assignment
            crew_notes: Optional crew notes
            internal_notes: Optional internal notes
        
        Returns:
            Created job object
        
        Raises:
            ValueError: If quote is not in accepted state
            RuntimeError: If job creation fails
        """
        try:
            # Validate quote status
            if quote.status != "accepted":
                raise ValueError(f"Cannot create job from quote with status '{quote.status}'. Quote must be accepted.")
            
            # Generate job number
            job_number = self._generate_job_number(quote.organization_id, db)
            
            # Determine service type from quote line items
            service_type = self._extract_primary_service_type(quote.line_items)
            
            # Create job from quote data
            job = Job(
                organization_id=quote.organization_id,
                lead_id=quote.lead_id,
                quote_id=quote.id,
                job_number=job_number,
                service_type=service_type,
                service_details=self._extract_service_details(quote.line_items),
                address=quote.customer_address or "Address needed",
                scheduled_for=scheduled_for,
                duration_minutes=duration_minutes,
                crew=crew or {},
                crew_notes=crew_notes,
                status="scheduled",
                estimated_cost=quote.total,
                currency=quote.currency,
                customer_name=quote.customer_name,
                customer_phone=quote.customer_phone,
                customer_email=quote.customer_email,
                internal_notes=internal_notes,
                priority="normal",
                created_by_id=user_id
            )
            
            db.add(job)
            db.commit()
            db.refresh(job)
            
            # Log audit event
            self.audit_logger.log_event(
                event_type=AuditEventType.JOB_CREATED,
                user_id=str(user_id),
                organization_id=quote.organization_id,
                details={
                    "job_id": job.id,
                    "job_number": job_number,
                    "quote_id": quote.id,
                    "lead_id": quote.lead_id,
                    "service_type": service_type,
                    "estimated_cost": float(quote.total),
                    "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
                    "created_from": "quote_acceptance"
                }
            )
            
            logger.info(f"Created job {job.id} from accepted quote {quote.id}")
            return job
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating job from quote {quote.id}: {str(e)}")
            raise RuntimeError(f"Failed to create job from quote: {str(e)}")
    
    def create_job_direct(
        self, 
        request: JobCreationRequest, 
        db: Session, 
        user_id: int
    ) -> Job:
        """
        Create a job directly (not from quote)
        
        Args:
            request: Job creation request
            db: Database session
            user_id: User creating the job
        
        Returns:
            Created job object
        """
        try:
            # Generate job number
            job_number = self._generate_job_number(request.organization_id, db)
            
            job = Job(
                organization_id=request.organization_id,
                lead_id=request.lead_id,
                quote_id=request.quote_id,
                job_number=job_number,
                service_type=request.service_type,
                service_details=request.service_details,
                address=request.address,
                scheduled_for=request.scheduled_for,
                duration_minutes=request.duration_minutes,
                crew=request.crew,
                crew_notes=request.crew_notes,
                status="scheduled",
                estimated_cost=request.estimated_cost,
                currency=request.currency,
                customer_name=request.customer_name,
                customer_phone=request.customer_phone,
                customer_email=request.customer_email,
                internal_notes=request.internal_notes,
                priority=request.priority,
                created_by_id=user_id
            )
            
            db.add(job)
            db.commit()
            db.refresh(job)
            
            # Log audit event
            self.audit_logger.log_event(
                event_type=AuditEventType.JOB_CREATED,
                user_id=str(user_id),
                organization_id=request.organization_id,
                details={
                    "job_id": job.id,
                    "job_number": job_number,
                    "service_type": request.service_type,
                    "estimated_cost": request.estimated_cost,
                    "scheduled_for": request.scheduled_for.isoformat() if request.scheduled_for else None,
                    "created_from": "direct_creation"
                }
            )
            
            logger.info(f"Created job {job.id} directly")
            return job
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating job directly: {str(e)}")
            raise RuntimeError(f"Failed to create job: {str(e)}")
    
    def update_job(
        self, 
        job: Job, 
        request: JobUpdateRequest, 
        db: Session, 
        user_id: int
    ) -> Job:
        """
        Update a job with new information
        
        Args:
            job: Job to update
            request: Update request with new values
            db: Database session
            user_id: User making the update
        
        Returns:
            Updated job object
        
        Raises:
            ValueError: If status transition is invalid
            RuntimeError: If update fails
        """
        try:
            # Track what changed for audit
            changes = {}
            old_status = job.status
            
            # Update fields if provided
            if request.scheduled_for is not None:
                if job.scheduled_for != request.scheduled_for:
                    changes["scheduled_for"] = {
                        "from": job.scheduled_for.isoformat() if job.scheduled_for else None,
                        "to": request.scheduled_for.isoformat() if request.scheduled_for else None
                    }
                    job.scheduled_for = request.scheduled_for
            
            if request.duration_minutes is not None:
                if job.duration_minutes != request.duration_minutes:
                    changes["duration_minutes"] = {
                        "from": job.duration_minutes,
                        "to": request.duration_minutes
                    }
                    job.duration_minutes = request.duration_minutes
            
            if request.crew is not None:
                changes["crew"] = {"updated": True}
                job.crew = request.crew
            
            if request.crew_notes is not None:
                job.crew_notes = request.crew_notes
            
            if request.completion_notes is not None:
                job.completion_notes = request.completion_notes
            
            if request.completion_photos is not None:
                job.completion_photos = request.completion_photos
            
            if request.customer_satisfaction is not None:
                if not (1 <= request.customer_satisfaction <= 5):
                    raise ValueError("Customer satisfaction must be between 1 and 5")
                job.customer_satisfaction = request.customer_satisfaction
            
            if request.actual_cost is not None:
                if request.actual_cost != job.actual_cost:
                    changes["actual_cost"] = {
                        "from": float(job.actual_cost) if job.actual_cost else None,
                        "to": request.actual_cost
                    }
                    job.actual_cost = request.actual_cost
            
            if request.internal_notes is not None:
                job.internal_notes = request.internal_notes
            
            if request.priority is not None:
                if job.priority != request.priority:
                    changes["priority"] = {
                        "from": job.priority,
                        "to": request.priority
                    }
                    job.priority = request.priority
            
            # Handle status changes with validation
            if request.status is not None:
                if not job.can_transition_to(request.status):
                    raise ValueError(
                        f"Cannot transition job from '{job.status}' to '{request.status}'. "
                        f"Valid transitions: {self._get_valid_transitions(job.status)}"
                    )
                
                # Update status and timestamp
                job.status = request.status
                changes["status"] = {
                    "from": old_status,
                    "to": request.status
                }
                
                # Set status-specific timestamps
                current_time = datetime.now(timezone.utc)
                if request.status == "in_progress":
                    job.started_at = current_time
                elif request.status == "completed":
                    job.completed_at = current_time
                elif request.status == "canceled":
                    job.canceled_at = current_time
            
            # Update audit fields
            job.updated_by_id = user_id
            
            db.commit()
            db.refresh(job)
            
            # Log audit event
            self.audit_logger.log_event(
                event_type=AuditEventType.JOB_UPDATED,
                user_id=str(user_id),
                organization_id=job.organization_id,
                details={
                    "job_id": job.id,
                    "job_number": job.job_number,
                    "changes": changes
                }
            )
            
            # Send notifications for important status changes
            if request.status and request.status != old_status:
                asyncio.create_task(self._send_status_change_notification(
                    job, old_status, request.status, user_id
                ))
            
            logger.info(f"Updated job {job.id} with {len(changes)} changes")
            return job
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating job {job.id}: {str(e)}")
            raise RuntimeError(f"Failed to update job: {str(e)}")
    
    def reschedule_job(
        self, 
        job: Job, 
        new_scheduled_time: datetime, 
        reason: Optional[str], 
        db: Session, 
        user_id: int
    ) -> Job:
        """
        Reschedule a job to a new time
        
        Args:
            job: Job to reschedule
            new_scheduled_time: New scheduled time
            reason: Optional reason for rescheduling
            db: Database session
            user_id: User making the change
        
        Returns:
            Updated job object
        
        Raises:
            ValueError: If job cannot be rescheduled
        """
        try:
            if job.status not in ["scheduled", "rescheduled"]:
                raise ValueError(f"Cannot reschedule job with status '{job.status}'")
            
            old_time = job.scheduled_for
            
            # Update job
            job.scheduled_for = new_scheduled_time
            job.status = "rescheduled" if job.status == "scheduled" else job.status
            job.updated_by_id = user_id
            
            # Add rescheduling notes
            reschedule_note = f"Rescheduled from {old_time.isoformat() if old_time else 'unscheduled'} to {new_scheduled_time.isoformat()}"
            if reason:
                reschedule_note += f". Reason: {reason}"
            
            if job.internal_notes:
                job.internal_notes += f"\n{reschedule_note}"
            else:
                job.internal_notes = reschedule_note
            
            db.commit()
            db.refresh(job)
            
            # Log audit event
            self.audit_logger.log_event(
                event_type=AuditEventType.JOB_RESCHEDULED,
                user_id=str(user_id),
                organization_id=job.organization_id,
                details={
                    "job_id": job.id,
                    "job_number": job.job_number,
                    "old_scheduled_time": old_time.isoformat() if old_time else None,
                    "new_scheduled_time": new_scheduled_time.isoformat(),
                    "reason": reason
                }
            )
            
            logger.info(f"Rescheduled job {job.id} from {old_time} to {new_scheduled_time}")
            return job
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error rescheduling job {job.id}: {str(e)}")
            raise RuntimeError(f"Failed to reschedule job: {str(e)}")
    
    def _generate_job_number(self, organization_id: str, db: Session) -> str:
        """Generate a unique job number for the organization"""
        # Get count of jobs for this org to generate sequential number
        job_count = db.query(Job).filter(
            Job.organization_id == organization_id
        ).count()
        
        # Generate job number: JOB-{org_prefix}-{sequential}
        org_prefix = organization_id[:8].upper()
        return f"JOB-{org_prefix}-{job_count + 1:04d}"
    
    def _extract_primary_service_type(self, line_items: List[Dict[str, Any]]) -> str:
        """Extract the primary service type from quote line items"""
        if not line_items:
            return "pressure_washing"
        
        # Find the line item with the highest cost (primary service)
        primary_item = max(line_items, key=lambda x: x.get("total", 0))
        return primary_item.get("service", "pressure_washing")
    
    def _extract_service_details(self, line_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract detailed service information from quote line items"""
        return {
            "line_items": line_items,
            "total_line_items": len(line_items),
            "services_included": [item.get("service") for item in line_items if item.get("service")]
        }
    
    def _get_valid_transitions(self, current_status: str) -> List[str]:
        """Get valid status transitions for a job status"""
        valid_transitions = {
            "scheduled": ["in_progress", "canceled", "rescheduled"],
            "rescheduled": ["scheduled", "in_progress", "canceled"],
            "in_progress": ["completed", "canceled"],
            "completed": [],
            "canceled": []
        }
        return valid_transitions.get(current_status, [])
    
    async def _send_status_change_notification(
        self, 
        job: Job, 
        old_status: str, 
        new_status: str, 
        user_id: int
    ):
        """Send notification for job status changes"""
        try:
            # Notification messages for different status changes
            status_messages = {
                "in_progress": f"Job {job.job_number} has started at {job.address}",
                "completed": f"Job {job.job_number} has been completed at {job.address}",
                "canceled": f"Job {job.job_number} has been canceled",
                "rescheduled": f"Job {job.job_number} has been rescheduled"
            }
            
            if new_status in status_messages:
                await self.notification_service.create_notification(
                    user_id=user_id,
                    title=f"Job Status Update",
                    message=status_messages[new_status],
                    notification_type=NotificationType.JOB_STATUS_CHANGED,
                    priority=NotificationPriority.HIGH if new_status in ["completed", "canceled"] else NotificationPriority.MEDIUM,
                    metadata={
                        "job_id": job.id,
                        "job_number": job.job_number,
                        "old_status": old_status,
                        "new_status": new_status,
                        "customer_name": job.customer_name
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to send job status notification: {e}")


def get_job_service() -> JobService:
    """Factory function to get job service instance"""
    return JobService()


# Import asyncio for async task creation
import asyncio