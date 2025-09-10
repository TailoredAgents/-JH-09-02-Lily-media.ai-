"""
Encryption Key Rotation Service

Comprehensive service for managing encryption key rotation, including automated
key generation, secure key storage, gradual migration, and compliance monitoring.
"""
import os
import json
import base64
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, func

from backend.db.models import User, SocialConnection, RefreshTokenBlacklist
from backend.db.user_credentials import UserCredentials
from backend.core.config import get_settings
from backend.core.encryption import VersionedEncryption, EncryptionError
from backend.core.audit_logger import AuditLogger

logger = logging.getLogger(__name__)
settings = get_settings()

class KeyRotationStatus(Enum):
    """Status of key rotation operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class KeyType(Enum):
    """Types of encryption keys"""
    TOKEN_ENCRYPTION = "token_encryption"
    DATABASE_ENCRYPTION = "database_encryption"
    FILE_ENCRYPTION = "file_encryption"
    SESSION_ENCRYPTION = "session_encryption"
    API_SIGNATURE = "api_signature"

@dataclass
class EncryptionKey:
    """Encryption key metadata"""
    key_id: str
    key_type: KeyType
    created_at: datetime
    expires_at: datetime
    status: str  # active, deprecated, retired
    algorithm: str
    key_length: int
    usage_count: int = 0
    last_used: Optional[datetime] = None

@dataclass
class KeyRotationEvent:
    """Key rotation event record"""
    event_id: str
    key_type: KeyType
    old_key_id: Optional[str]
    new_key_id: str
    status: KeyRotationStatus
    started_at: datetime
    completed_at: Optional[datetime]
    records_migrated: int = 0
    total_records: int = 0
    error_message: Optional[str] = None

class KeyRotationService:
    """Service for managing encryption key rotation and lifecycle"""
    
    def __init__(self):
        self.audit_logger = AuditLogger()
        self.encryption_service = VersionedEncryption()
        
        # Key rotation schedules (in days)
        self.rotation_schedules = {
            KeyType.TOKEN_ENCRYPTION: 90,      # 3 months
            KeyType.DATABASE_ENCRYPTION: 180,  # 6 months
            KeyType.FILE_ENCRYPTION: 365,      # 1 year
            KeyType.SESSION_ENCRYPTION: 30,    # 1 month
            KeyType.API_SIGNATURE: 90,         # 3 months
        }
        
        # Grace periods before key retirement (in days)
        self.grace_periods = {
            KeyType.TOKEN_ENCRYPTION: 30,      # 1 month
            KeyType.DATABASE_ENCRYPTION: 90,   # 3 months
            KeyType.FILE_ENCRYPTION: 180,      # 6 months
            KeyType.SESSION_ENCRYPTION: 7,     # 1 week
            KeyType.API_SIGNATURE: 30,         # 1 month
        }
        
        # In-memory key store (in production, use secure key management service)
        self.key_store = self._initialize_key_store()
        
    def _initialize_key_store(self) -> Dict[str, Dict[str, Any]]:
        """Initialize key store with existing keys"""
        key_store = {}
        
        # Load existing keys from environment/config
        current_token_key = getattr(settings, 'token_encryption_key', None)
        if current_token_key:
            key_id = "default"
            key_store[key_id] = {
                "key": current_token_key,
                "key_type": KeyType.TOKEN_ENCRYPTION,
                "created_at": datetime.now(timezone.utc) - timedelta(days=30),  # Assume existing
                "status": "active",
                "algorithm": "Fernet",
                "key_length": 256,
                "usage_count": 0
            }
        
        return key_store
    
    def generate_new_key(self, key_type: KeyType, algorithm: str = "Fernet") -> Tuple[str, str]:
        """
        Generate a new encryption key
        
        Args:
            key_type: Type of key to generate
            algorithm: Encryption algorithm (default: Fernet)
            
        Returns:
            Tuple of (key_id, key_material)
        """
        # Generate unique key ID
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        random_suffix = secrets.token_hex(4)
        key_id = f"{key_type.value}_{timestamp}_{random_suffix}"
        
        if algorithm == "Fernet":
            # Generate Fernet key (256-bit AES with HMAC)
            key_material = Fernet.generate_key().decode('utf-8')
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        # Store key metadata
        self.key_store[key_id] = {
            "key": key_material,
            "key_type": key_type,
            "created_at": datetime.now(timezone.utc),
            "status": "active",
            "algorithm": algorithm,
            "key_length": 256,
            "usage_count": 0
        }
        
        logger.info(f"Generated new {algorithm} key: {key_id}")
        
        # Audit log
        from backend.core.audit_logger import AuditEventType
        self.audit_logger.log_event(
            event_type=AuditEventType.SECURITY_VIOLATION,  # Closest available type
            user_id=None,
            resource=f"encryption_key_{key_type.value}",
            action="key_generation",
            outcome="success",
            details={
                "key_id": key_id,
                "key_type": key_type.value,
                "algorithm": algorithm,
                "key_length": 256
            }
        )
        
        return key_id, key_material
    
    def schedule_key_rotation(self, key_type: KeyType, force: bool = False) -> Dict[str, Any]:
        """
        Schedule key rotation for a specific key type
        
        Args:
            key_type: Type of key to rotate
            force: Force rotation even if not due
            
        Returns:
            Rotation schedule information
        """
        current_keys = self.get_active_keys(key_type)
        
        if not current_keys and not force:
            # No existing keys, create initial key
            key_id, key_material = self.generate_new_key(key_type)
            return {
                "action": "initial_key_created",
                "key_id": key_id,
                "key_type": key_type.value,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        
        # Check if rotation is due
        needs_rotation = False
        oldest_key_age = None
        
        if current_keys:
            oldest_key = min(current_keys, key=lambda k: k["created_at"])
            oldest_key_age = (datetime.now(timezone.utc) - oldest_key["created_at"]).days
            rotation_interval = self.rotation_schedules.get(key_type, 90)
            needs_rotation = oldest_key_age >= rotation_interval
        
        if not needs_rotation and not force:
            return {
                "action": "rotation_not_due",
                "key_type": key_type.value,
                "oldest_key_age_days": oldest_key_age,
                "rotation_due_in_days": self.rotation_schedules.get(key_type, 90) - (oldest_key_age or 0)
            }
        
        # Generate new key
        new_key_id, new_key_material = self.generate_new_key(key_type)
        
        # Create rotation event
        event_id = f"rotation_{key_type.value}_{secrets.token_hex(4)}"
        rotation_event = KeyRotationEvent(
            event_id=event_id,
            key_type=key_type,
            old_key_id=current_keys[0]["key_id"] if current_keys else None,
            new_key_id=new_key_id,
            status=KeyRotationStatus.PENDING,
            started_at=datetime.now(timezone.utc)
        )
        
        # Store rotation event (in production, use database)
        self._store_rotation_event(rotation_event)
        
        logger.info(f"Scheduled key rotation for {key_type.value}: {event_id}")
        
        return {
            "action": "rotation_scheduled",
            "event_id": event_id,
            "key_type": key_type.value,
            "new_key_id": new_key_id,
            "old_key_id": rotation_event.old_key_id,
            "scheduled_at": rotation_event.started_at.isoformat()
        }
    
    def execute_key_rotation(self, db: Session, event_id: str, 
                           batch_size: int = 1000) -> Dict[str, Any]:
        """
        Execute key rotation by migrating encrypted data
        
        Args:
            db: Database session
            event_id: Rotation event ID
            batch_size: Number of records to process per batch
            
        Returns:
            Rotation execution results
        """
        # Get rotation event
        rotation_event = self._get_rotation_event(event_id)
        if not rotation_event:
            raise ValueError(f"Rotation event {event_id} not found")
        
        if rotation_event.status != KeyRotationStatus.PENDING:
            raise ValueError(f"Rotation event {event_id} is not pending")
        
        try:
            # Mark as in progress
            rotation_event.status = KeyRotationStatus.IN_PROGRESS
            self._update_rotation_event(rotation_event)
            
            # Execute migration based on key type
            migration_results = self._migrate_encrypted_data(
                db, rotation_event, batch_size
            )
            
            # Update event with results
            rotation_event.status = KeyRotationStatus.COMPLETED
            rotation_event.completed_at = datetime.now(timezone.utc)
            rotation_event.records_migrated = migration_results["migrated_count"]
            rotation_event.total_records = migration_results["total_count"]
            
            self._update_rotation_event(rotation_event)
            
            # Mark old key as deprecated
            if rotation_event.old_key_id and rotation_event.old_key_id in self.key_store:
                self.key_store[rotation_event.old_key_id]["status"] = "deprecated"
            
            logger.info(f"Key rotation completed: {event_id}")
            
            # Audit log
            from backend.core.audit_logger import AuditEventType
            self.audit_logger.log_event(
                event_type=AuditEventType.CONFIG_CHANGED,
                user_id=None,
                resource=f"encryption_key_{rotation_event.key_type.value}",
                action="key_rotation_completed",
                outcome="success",
                details={
                    "event_id": event_id,
                    "key_type": rotation_event.key_type.value,
                    "records_migrated": migration_results["migrated_count"],
                    "duration_seconds": migration_results.get("duration_seconds", 0)
                }
            )
            
            return {
                "status": "completed",
                "event_id": event_id,
                "records_migrated": migration_results["migrated_count"],
                "total_records": migration_results["total_count"],
                "duration_seconds": migration_results.get("duration_seconds", 0),
                "errors": migration_results.get("errors", [])
            }
            
        except Exception as e:
            # Mark as failed
            rotation_event.status = KeyRotationStatus.FAILED
            rotation_event.error_message = str(e)
            rotation_event.completed_at = datetime.now(timezone.utc)
            self._update_rotation_event(rotation_event)
            
            logger.error(f"Key rotation failed: {event_id} - {e}")
            
            # Audit log
            from backend.core.audit_logger import AuditEventType
            self.audit_logger.log_event(
                event_type=AuditEventType.SECURITY_VIOLATION,
                user_id=None,
                resource=f"encryption_key_{rotation_event.key_type.value}",
                action="key_rotation_failed",
                outcome="failure",
                details={
                    "event_id": event_id,
                    "key_type": rotation_event.key_type.value,
                    "error": str(e)
                }
            )
            
            raise
    
    def _migrate_encrypted_data(self, db: Session, rotation_event: KeyRotationEvent,
                              batch_size: int) -> Dict[str, Any]:
        """Migrate encrypted data to new key"""
        start_time = datetime.now(timezone.utc)
        migrated_count = 0
        total_count = 0
        errors = []
        
        old_key_id = rotation_event.old_key_id
        new_key_id = rotation_event.new_key_id
        
        # Get old and new encryption keys
        old_key = self.key_store.get(old_key_id, {}).get("key") if old_key_id else None
        new_key = self.key_store.get(new_key_id, {}).get("key")
        
        if not new_key:
            raise ValueError(f"New key {new_key_id} not found")
        
        # Create encryption services
        old_encryption = VersionedEncryption(old_key) if old_key else None
        new_encryption = VersionedEncryption(new_key)
        
        if rotation_event.key_type == KeyType.TOKEN_ENCRYPTION:
            # Migrate OAuth tokens in user credentials
            credentials = db.query(UserCredentials).all()
            total_count = len(credentials)
            
            for credential in credentials:
                try:
                    # Decrypt with old key (if exists)
                    if old_encryption and credential.encrypted_token:
                        try:
                            decrypted_token = old_encryption.decrypt(credential.encrypted_token)
                            # Re-encrypt with new key
                            credential.encrypted_token = new_encryption.encrypt(decrypted_token)
                            migrated_count += 1
                        except Exception as e:
                            errors.append(f"Failed to migrate credential {credential.id}: {e}")
                    
                    # Migrate refresh token if exists
                    if old_encryption and credential.encrypted_refresh_token:
                        try:
                            decrypted_refresh = old_encryption.decrypt(credential.encrypted_refresh_token)
                            credential.encrypted_refresh_token = new_encryption.encrypt(decrypted_refresh)
                        except Exception as e:
                            errors.append(f"Failed to migrate refresh token {credential.id}: {e}")
                
                except Exception as e:
                    errors.append(f"Error processing credential {credential.id}: {e}")
            
            # Commit migrations
            db.commit()
        
        elif rotation_event.key_type == KeyType.SESSION_ENCRYPTION:
            # Migrate session data (example - adapt based on session storage)
            # For now, we'll just invalidate old sessions by updating blacklist
            db.query(RefreshTokenBlacklist).filter(
                RefreshTokenBlacklist.blacklisted_at < datetime.now(timezone.utc) - timedelta(days=1)
            ).delete(synchronize_session=False)
            db.commit()
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return {
            "migrated_count": migrated_count,
            "total_count": total_count,
            "duration_seconds": duration,
            "errors": errors
        }
    
    def get_active_keys(self, key_type: KeyType) -> List[Dict[str, Any]]:
        """Get all active keys for a specific type"""
        active_keys = []
        
        for key_id, key_data in self.key_store.items():
            if (key_data.get("key_type") == key_type and 
                key_data.get("status") == "active"):
                active_keys.append({
                    "key_id": key_id,
                    "created_at": key_data["created_at"],
                    "algorithm": key_data["algorithm"],
                    "usage_count": key_data.get("usage_count", 0)
                })
        
        return sorted(active_keys, key=lambda k: k["created_at"])
    
    def get_key_rotation_schedule(self) -> Dict[str, Any]:
        """Get complete key rotation schedule and status"""
        schedule = {
            "current_time": datetime.now(timezone.utc).isoformat(),
            "key_types": {},
            "overall_status": "healthy"
        }
        
        overdue_count = 0
        
        for key_type in KeyType:
            active_keys = self.get_active_keys(key_type)
            rotation_interval = self.rotation_schedules.get(key_type, 90)
            
            if active_keys:
                oldest_key = min(active_keys, key=lambda k: k["created_at"])
                age_days = (datetime.now(timezone.utc) - oldest_key["created_at"]).days
                
                is_overdue = age_days > rotation_interval
                if is_overdue:
                    overdue_count += 1
                
                schedule["key_types"][key_type.value] = {
                    "active_keys": len(active_keys),
                    "oldest_key_age_days": age_days,
                    "rotation_interval_days": rotation_interval,
                    "days_until_rotation": max(0, rotation_interval - age_days),
                    "is_overdue": is_overdue,
                    "status": "overdue" if is_overdue else "healthy"
                }
            else:
                schedule["key_types"][key_type.value] = {
                    "active_keys": 0,
                    "status": "no_keys",
                    "needs_initial_key": True
                }
                overdue_count += 1
        
        if overdue_count > 0:
            schedule["overall_status"] = "needs_attention"
        
        schedule["overdue_key_types"] = overdue_count
        
        return schedule
    
    def cleanup_expired_keys(self) -> Dict[str, Any]:
        """Clean up expired and deprecated keys"""
        cleaned_keys = []
        
        for key_id, key_data in list(self.key_store.items()):
            if key_data.get("status") == "deprecated":
                key_type = key_data.get("key_type")
                created_at = key_data.get("created_at")
                
                # Check if grace period has passed
                grace_period = self.grace_periods.get(key_type, 30)
                age_days = (datetime.now(timezone.utc) - created_at).days
                
                if age_days > (self.rotation_schedules.get(key_type, 90) + grace_period):
                    # Mark as retired and remove from active store
                    key_data["status"] = "retired"
                    key_data["retired_at"] = datetime.now(timezone.utc)
                    
                    # In production, move to cold storage instead of deleting
                    cleaned_keys.append({
                        "key_id": key_id,
                        "key_type": key_type.value if key_type else "unknown",
                        "age_days": age_days
                    })
                    
                    logger.info(f"Retired expired key: {key_id}")
        
        return {
            "cleaned_keys": len(cleaned_keys),
            "keys": cleaned_keys,
            "cleanup_date": datetime.now(timezone.utc).isoformat()
        }
    
    def _store_rotation_event(self, event: KeyRotationEvent):
        """Store rotation event (in production, use database)"""
        # For now, store in memory - replace with database storage
        if not hasattr(self, 'rotation_events'):
            self.rotation_events = {}
        self.rotation_events[event.event_id] = event
    
    def _get_rotation_event(self, event_id: str) -> Optional[KeyRotationEvent]:
        """Get rotation event by ID"""
        return getattr(self, 'rotation_events', {}).get(event_id)
    
    def _update_rotation_event(self, event: KeyRotationEvent):
        """Update rotation event"""
        if hasattr(self, 'rotation_events'):
            self.rotation_events[event.event_id] = event
    
    def generate_key_rotation_report(self) -> Dict[str, Any]:
        """Generate comprehensive key rotation report"""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {},
            "key_details": {},
            "rotation_history": [],
            "recommendations": []
        }
        
        # Get current schedule
        schedule = self.get_key_rotation_schedule()
        report["summary"] = {
            "overall_status": schedule["overall_status"],
            "overdue_key_types": schedule["overdue_key_types"],
            "total_key_types": len(KeyType)
        }
        
        # Key details
        for key_type in KeyType:
            active_keys = self.get_active_keys(key_type)
            report["key_details"][key_type.value] = {
                "active_count": len(active_keys),
                "rotation_schedule_days": self.rotation_schedules.get(key_type, 90),
                "grace_period_days": self.grace_periods.get(key_type, 30),
                "keys": active_keys
            }
        
        # Rotation history (from in-memory events)
        if hasattr(self, 'rotation_events'):
            for event_id, event in self.rotation_events.items():
                report["rotation_history"].append({
                    "event_id": event_id,
                    "key_type": event.key_type.value,
                    "status": event.status.value,
                    "started_at": event.started_at.isoformat(),
                    "completed_at": event.completed_at.isoformat() if event.completed_at else None,
                    "records_migrated": event.records_migrated
                })
        
        # Generate recommendations
        if schedule["overdue_key_types"] > 0:
            report["recommendations"].append(
                f"🚨 {schedule['overdue_key_types']} key types require immediate rotation"
            )
        
        for key_type_str, details in schedule["key_types"].items():
            if details.get("is_overdue"):
                report["recommendations"].append(
                    f"⚠️  {key_type_str} keys are {details['oldest_key_age_days']} days old (rotate every {details['rotation_interval_days']} days)"
                )
        
        if not report["recommendations"]:
            report["recommendations"].append("✅ All encryption keys are within rotation schedule")
        
        return report
    
    def generate_procedure_documentation(self) -> Dict[str, Any]:
        """P1-2c: Generate current key rotation procedure documentation"""
        current_config = self.get_key_rotation_schedule()
        
        documentation = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version": "2.0",
            "title": "Key Rotation Procedures - Auto-Generated",
            "system_status": {
                "overall_status": current_config["overall_status"],
                "total_key_types": len(KeyType),
                "overdue_count": current_config["overdue_key_types"],
                "active_keys_count": sum(
                    len(self.get_active_keys(key_type)) for key_type in KeyType
                )
            },
            "rotation_schedules": {
                key_type.value: {
                    "rotation_interval_days": self.rotation_schedules.get(key_type, 90),
                    "grace_period_days": self.grace_periods.get(key_type, 30),
                    "priority": "Critical" if key_type == KeyType.TOKEN_ENCRYPTION else
                              "High" if key_type in [KeyType.DATABASE_ENCRYPTION, KeyType.SESSION_ENCRYPTION, KeyType.API_SIGNATURE] else
                              "Medium"
                }
                for key_type in KeyType
            },
            "current_key_status": {
                key_type.value: {
                    "active_keys": len(self.get_active_keys(key_type)),
                    "status": current_config["key_types"].get(key_type.value, {}).get("status", "unknown"),
                    "oldest_key_age_days": current_config["key_types"].get(key_type.value, {}).get("oldest_key_age_days", 0),
                    "is_overdue": current_config["key_types"].get(key_type.value, {}).get("is_overdue", False)
                }
                for key_type in KeyType
            },
            "api_endpoints": {
                "status": "/api/v1/key-rotation/status",
                "schedule": "/api/v1/key-rotation/schedule",
                "execute": "/api/v1/key-rotation/execute",
                "report": "/api/v1/key-rotation/report",
                "events": "/api/v1/key-rotation/events",
                "rollback": "/api/v1/key-rotation/rollback"
            },
            "emergency_procedures": {
                "immediate_rotation_required": [
                    "1. Assess impact: GET /api/v1/key-rotation/impact/{key_type}",
                    "2. Force rotation: POST /api/v1/key-rotation/schedule with force=true",
                    "3. Monitor progress: GET /api/v1/key-rotation/events/{event_id}",
                    "4. Verify completion: GET /api/v1/key-rotation/report"
                ],
                "rollback_procedure": [
                    "1. Identify failed event ID",
                    "2. Execute rollback: POST /api/v1/key-rotation/rollback/{event_id}",
                    "3. Verify rollback: GET /api/v1/key-rotation/events/{event_id}",
                    "4. Investigate root cause"
                ]
            },
            "compliance_requirements": {
                "sox": "Quarterly key rotation documentation required",
                "pci_dss": "Key rotation for payment-related data",
                "gdpr": "Key rotation for EU user data",
                "audit_logging": "All operations logged to audit trail"
            },
            "monitoring_metrics": {
                "key_age_threshold": "Rotation schedule + grace period",
                "rotation_success_rate": "Target: >99%",
                "migration_performance": "Target: >1000 records/second",
                "error_rate_threshold": "Alert: >1%"
            }
        }
        
        # Add recommendations based on current status
        documentation["current_recommendations"] = []
        
        if current_config["overdue_key_types"] > 0:
            documentation["current_recommendations"].append({
                "priority": "CRITICAL",
                "message": f"{current_config['overdue_key_types']} key types require immediate rotation",
                "action": "Execute emergency key rotation procedure"
            })
        
        for key_type_str, details in current_config["key_types"].items():
            if details.get("is_overdue"):
                documentation["current_recommendations"].append({
                    "priority": "HIGH",
                    "message": f"{key_type_str} keys are {details['oldest_key_age_days']} days old",
                    "action": f"Schedule rotation (target: every {details['rotation_interval_days']} days)"
                })
        
        if not documentation["current_recommendations"]:
            documentation["current_recommendations"].append({
                "priority": "INFO",
                "message": "All encryption keys are within rotation schedule",
                "action": "Continue monitoring key age"
            })
        
        return documentation

# Global service instance
key_rotation_service = KeyRotationService()

def get_key_rotation_service() -> KeyRotationService:
    """Get the global key rotation service instance"""
    return key_rotation_service