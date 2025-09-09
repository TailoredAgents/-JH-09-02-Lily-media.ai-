"""
Comprehensive audit logging system for AI Social Media Content Agent.
Ensures compliance with data protection regulations and security standards.
"""

import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Union
from contextlib import contextmanager
from functools import wraps

import structlog
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

Base = declarative_base()

class AuditEventType(Enum):
    """Enumeration of audit event types for compliance tracking."""
    
    # Authentication & Authorization
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_FAILED_LOGIN = "user_failed_login"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    
    # Data Access & Modification
    DATA_READ = "data_read"
    DATA_CREATED = "data_created"
    DATA_UPDATED = "data_updated"
    DATA_DELETED = "data_deleted"
    DATA_EXPORTED = "data_exported"
    DATA_IMPORTED = "data_imported"
    
    # AI & Content Generation
    AI_REQUEST = "ai_request"
    CONTENT_GENERATED = "content_generated"
    CONTENT_PUBLISHED = "content_published"
    CONTENT_MODERATED = "content_moderated"
    
    # System & Security
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIG_CHANGED = "config_changed"
    SECURITY_VIOLATION = "security_violation"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"
    
    # API & External Integrations
    API_CALL = "api_call"
    EXTERNAL_SERVICE_CALL = "external_service_call"
    WEBHOOK_RECEIVED = "webhook_received"
    
    # Compliance & Privacy
    GDPR_REQUEST = "gdpr_request"
    DATA_RETENTION_ACTION = "data_retention_action"
    PRIVACY_SETTINGS_CHANGED = "privacy_settings_changed"
    
    # Settings Management
    SETTINGS_UPDATED = "settings_updated"
    SETTINGS_ACCESSED = "settings_accessed"
    
    # Quote Management
    QUOTE_CREATED = "quote_created"
    QUOTE_UPDATED = "quote_updated"
    QUOTE_DELETED = "quote_deleted"
    QUOTE_SENT = "quote_sent"
    QUOTE_ACCEPTED = "quote_accepted"
    QUOTE_DECLINED = "quote_declined"
    QUOTE_EXPIRED = "quote_expired"
    
    # Lead Management (PW-DM-REPLACE-001, PW-DM-ADD-002)
    LEAD_CREATED = "lead_created"
    LEAD_UPDATED = "lead_updated"
    LEAD_STATUS_CHANGED = "lead_status_changed"
    LEAD_CONVERTED_TO_QUOTE = "lead_converted_to_quote"
    LEAD_PHOTO_UPLOAD_SENT = "lead_photo_upload_sent"
    LEAD_MEDIA_ATTACHED = "lead_media_attached"
    LEAD_MEDIA_NOTIFICATION_SENT = "lead_media_notification_sent"
    
    # Media Storage (PW-SEC-ADD-001)
    MEDIA_UPLOAD_URL_GENERATED = "media_upload_url_generated"
    MEDIA_DOWNLOAD_URL_GENERATED = "media_download_url_generated"
    MEDIA_ASSET_UPLOADED = "media_asset_uploaded"
    MEDIA_ASSET_DOWNLOADED = "media_asset_downloaded"
    MEDIA_ASSET_DELETED = "media_asset_deleted"
    MEDIA_ASSET_REVOKED = "media_asset_revoked"
    MEDIA_INTEGRITY_CHECK = "media_integrity_check"


class AuditLog(Base):
    """Database model for storing audit log entries."""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), index=True)
    session_id = Column(String(100), index=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    resource = Column(String(200))
    action = Column(String(100))
    outcome = Column(String(50))  # success, failure, error
    details = Column(JSON)
    compliance_flags = Column(JSON)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log entry to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource": self.resource,
            "action": self.action,
            "outcome": self.outcome,
            "details": self.details,
            "compliance_flags": self.compliance_flags
        }


class AuditLogger:
    """
    Comprehensive audit logging system with compliance features.
    
    Features:
    - Structured logging with JSON output
    - Database persistence for audit trails
    - GDPR/CCPA compliance tracking
    - Security event monitoring
    - Performance metrics
    - Automated compliance reporting
    """
    
    def __init__(self, db_url: str = None):
        self.logger = structlog.get_logger("audit")
        
        if db_url:
            self.engine = create_engine(db_url)
            Base.metadata.create_all(bind=self.engine)
            Session = sessionmaker(bind=self.engine)
            self.db_session = Session()
        else:
            self.db_session = None
    
    def log_event(
        self,
        event_type: Union[AuditEventType, str],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None,
        compliance_flags: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an audit event with comprehensive metadata.
        
        Args:
            event_type: Type of event being logged
            user_id: ID of the user performing the action
            session_id: Session identifier
            ip_address: Client IP address
            user_agent: Client user agent string
            resource: Resource being accessed/modified
            action: Specific action being performed
            outcome: Result of the action (success/failure/error)
            details: Additional event-specific details
            compliance_flags: Compliance-related metadata
        """
        
        if isinstance(event_type, AuditEventType):
            event_type = event_type.value
        
        # Prepare audit log entry
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "session_id": session_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "resource": resource,
            "action": action,
            "outcome": outcome,
            "details": details or {},
            "compliance_flags": compliance_flags or {}
        }
        
        # Add compliance metadata
        audit_entry["compliance_flags"].update({
            "retention_required": self._requires_retention(event_type),
            "pii_involved": self._contains_pii(details),
            "security_relevant": self._is_security_relevant(event_type),
            "gdpr_relevant": self._is_gdpr_relevant(event_type, details)
        })
        
        # Log to structured logger
        self.logger.info("audit_event", **audit_entry)
        
        # Persist to database if available
        if self.db_session:
            try:
                db_audit = AuditLog(
                    timestamp=datetime.utcnow(),
                    event_type=event_type,
                    user_id=user_id,
                    session_id=session_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    resource=resource,
                    action=action,
                    outcome=outcome,
                    details=details,
                    compliance_flags=audit_entry["compliance_flags"]
                )
                self.db_session.add(db_audit)
                self.db_session.commit()
            except Exception as e:
                self.logger.error("Failed to persist audit log", error=str(e))
                self.db_session.rollback()
    
    def _requires_retention(self, event_type: str) -> bool:
        """Determine if event requires long-term retention."""
        retention_events = {
            "user_login", "user_logout", "user_failed_login",
            "data_deleted", "permission_granted", "permission_revoked",
            "security_violation", "gdpr_request", "data_retention_action"
        }
        return event_type in retention_events
    
    def _contains_pii(self, details: Optional[Dict[str, Any]]) -> bool:
        """Check if event details contain personally identifiable information."""
        if not details:
            return False
        
        pii_fields = {
            "email", "phone", "address", "name", "ssn", "credit_card",
            "personal_data", "user_profile", "contact_info"
        }
        
        return any(field in str(details).lower() for field in pii_fields)
    
    def _is_security_relevant(self, event_type: str) -> bool:
        """Determine if event is security-relevant."""
        security_events = {
            "user_failed_login", "permission_granted", "permission_revoked",
            "security_violation", "config_changed", "system_start", "system_stop"
        }
        return event_type in security_events
    
    def _is_gdpr_relevant(self, event_type: str, details: Optional[Dict[str, Any]]) -> bool:
        """Determine if event is relevant for GDPR compliance."""
        gdpr_events = {
            "user_created", "user_updated", "user_deleted", "data_exported",
            "gdpr_request", "privacy_settings_changed", "data_retention_action"
        }
        return event_type in gdpr_events or self._contains_pii(details)


# Global audit logger instance
audit_logger = AuditLogger()


def audit_action(
    event_type: Union[AuditEventType, str],
    resource: Optional[str] = None,
    include_request_data: bool = False
):
    """
    Decorator for automatically auditing function calls.
    
    Args:
        event_type: Type of audit event
        resource: Resource being accessed
        include_request_data: Whether to include request data in audit log
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            outcome = "success"
            error_details = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                outcome = "error"
                error_details = {"error": str(e), "error_type": type(e).__name__}
                raise
            finally:
                execution_time = time.time() - start_time
                
                details = {
                    "function": func.__name__,
                    "execution_time": execution_time,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()) if kwargs else []
                }
                
                if include_request_data:
                    details["request_data"] = {
                        "args": args,
                        "kwargs": kwargs
                    }
                
                if error_details:
                    details.update(error_details)
                
                audit_logger.log_event(
                    event_type=event_type,
                    resource=resource or func.__name__,
                    action="function_call",
                    outcome=outcome,
                    details=details
                )
        
        return wrapper
    return decorator


@contextmanager
def audit_context(
    event_type: Union[AuditEventType, str],
    user_id: Optional[str] = None,
    resource: Optional[str] = None,
    **kwargs
):
    """
    Context manager for auditing code blocks.
    
    Args:
        event_type: Type of audit event
        user_id: User performing the action
        resource: Resource being accessed
        **kwargs: Additional audit metadata
    """
    start_time = time.time()
    outcome = "success"
    error_details = None
    
    try:
        yield
    except Exception as e:
        outcome = "error"
        error_details = {"error": str(e), "error_type": type(e).__name__}
        raise
    finally:
        execution_time = time.time() - start_time
        
        details = kwargs.get("details", {})
        details.update({
            "execution_time": execution_time
        })
        
        if error_details:
            details.update(error_details)
        
        audit_logger.log_event(
            event_type=event_type,
            user_id=user_id,
            resource=resource,
            outcome=outcome,
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


class ComplianceReporter:
    """Generate compliance reports from audit logs."""
    
    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger
    
    def generate_gdpr_report(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate GDPR compliance report."""
        
        if not self.audit_logger.db_session:
            raise ValueError("Database session required for compliance reporting")
        
        query = self.audit_logger.db_session.query(AuditLog).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date,
            AuditLog.compliance_flags.op('->>')('gdpr_relevant').astext == 'true'
        )
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        events = query.all()
        
        return {
            "report_type": "gdpr_compliance",
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "user_id": user_id,
            "total_events": len(events),
            "events_by_type": self._group_events_by_type(events),
            "pii_access_events": [
                event.to_dict() for event in events
                if event.compliance_flags.get("pii_involved", False)
            ],
            "data_subject_rights": self._analyze_data_subject_rights(events)
        }
    
    def generate_security_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate security audit report."""
        
        if not self.audit_logger.db_session:
            raise ValueError("Database session required for security reporting")
        
        query = self.audit_logger.db_session.query(AuditLog).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date,
            AuditLog.compliance_flags.op('->>')('security_relevant').astext == 'true'
        )
        
        events = query.all()
        failed_events = [e for e in events if e.outcome == "failure"]
        
        return {
            "report_type": "security_audit",
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_security_events": len(events),
            "failed_events": len(failed_events),
            "events_by_type": self._group_events_by_type(events),
            "failed_login_attempts": len([
                e for e in events if e.event_type == "user_failed_login"
            ]),
            "security_violations": [
                e.to_dict() for e in events if e.event_type == "security_violation"
            ]
        }
    
    def _group_events_by_type(self, events) -> Dict[str, int]:
        """Group events by type and count occurrences."""
        event_counts = {}
        for event in events:
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
        return event_counts
    
    def _analyze_data_subject_rights(self, events) -> Dict[str, Any]:
        """Analyze data subject rights exercises."""
        gdpr_requests = [e for e in events if e.event_type == "gdpr_request"]
        
        return {
            "total_requests": len(gdpr_requests),
            "request_types": self._group_events_by_type(gdpr_requests),
            "completed_requests": len([
                e for e in gdpr_requests if e.outcome == "success"
            ])
        }


class AuditTrackingMiddleware:
    """FastAPI middleware for automatic audit logging of requests."""
    
    def __init__(self, app, audit_logger: AuditLogger):
        self.app = app
        self.audit_logger = audit_logger
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request_time = time.time()
        
        # Extract request information
        method = scope.get("method", "")
        path = scope.get("path", "")
        client_ip = scope.get("client", ["unknown", None])[0] if scope.get("client") else "unknown"
        
        # Get headers
        headers = dict(scope.get("headers", []))
        user_agent = headers.get(b"user-agent", b"").decode("utf-8", errors="ignore")
        
        response_status = 200
        
        async def send_wrapper(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message.get("status", 200)
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
            outcome = "success" if response_status < 400 else "failure"
        except Exception as e:
            outcome = "error"
            response_status = 500
        
        # Log the request
        execution_time = time.time() - request_time
        
        self.audit_logger.log_event(
            event_type=AuditEventType.API_CALL,
            ip_address=client_ip,
            user_agent=user_agent,
            resource=path,
            action=method,
            outcome=outcome,
            details={
                "status_code": response_status,
                "execution_time": execution_time,
                "path": path,
                "method": method
            }
        )


# Example usage
if __name__ == "__main__":
    # Initialize audit logger
    audit_logger = AuditLogger("sqlite:///audit.db")
    
    # Log various events
    audit_logger.log_event(
        AuditEventType.USER_LOGIN,
        user_id="user123",
        ip_address="192.168.1.100",
        details={"login_method": "oauth", "provider": "google"}
    )
    
    # Use decorator for automatic auditing
    @audit_action(AuditEventType.DATA_CREATED, resource="social_posts")
    def create_post(content: str, user_id: str):
        # Function implementation
        return {"id": "post123", "content": content}
    
    # Use context manager for auditing code blocks
    with audit_context(
        AuditEventType.AI_REQUEST,
        user_id="user123",
        resource="content_generation",
        details={"model": "gpt-5", "tokens": 150}
    ):
        # AI content generation code
        pass

# Convenience functions for common audit events
_default_audit_logger = None

def get_audit_logger():
    """Get or create default audit logger instance"""
    global _default_audit_logger
    if _default_audit_logger is None:
        _default_audit_logger = AuditLogger()
    return _default_audit_logger

def log_content_event(event_type: AuditEventType, user_id: str = None, 
                     resource: str = None, details: Dict[str, Any] = None):
    """Convenience function for logging content-related events"""
    logger = get_audit_logger()
    return logger.log_event(
        event_type=event_type,
        user_id=user_id,
        resource=resource,
        details=details
    )

async def log_settings_event(event_type: AuditEventType, user_id: int, 
                            organization_id: str, details: Dict[str, Any] = None,
                            db: Any = None):
    """Convenience function for logging settings-related events"""
    logger = get_audit_logger()
    
    # Set database session for persistence if provided
    if db and not logger.db_session:
        logger.db_session = db
    
    return logger.log_event(
        event_type=event_type,
        user_id=str(user_id),
        resource=f"organization/{organization_id}/settings",
        action="update",
        outcome="success",
        details={
            "organization_id": organization_id,
            **(details or {})
        }
    )