"""
Encryption Key Rotation Management API

Provides secure endpoints for managing encryption key rotation, monitoring
key lifecycles, and ensuring compliance with security policies.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.db.database import get_db
from backend.db.models import User
from backend.auth.dependencies import get_admin_user
from backend.services.key_rotation_service import (
    KeyRotationService, KeyType, KeyRotationStatus,
    get_key_rotation_service
)
from backend.core.api_version import create_versioned_router

logger = logging.getLogger(__name__)

router = create_versioned_router(prefix="/key-rotation", tags=["key-rotation"])

class KeyRotationScheduleRequest(BaseModel):
    """Request model for scheduling key rotation"""
    key_type: str
    force: bool = False

class KeyRotationExecuteRequest(BaseModel):
    """Request model for executing key rotation"""
    event_id: str
    batch_size: int = Field(default=1000, ge=100, le=10000)

class KeyRotationScheduleResponse(BaseModel):
    """Response model for key rotation scheduling"""
    action: str
    event_id: Optional[str] = None
    key_id: Optional[str] = None
    key_type: str
    message: str
    scheduled_at: Optional[str] = None

class KeyRotationExecuteResponse(BaseModel):
    """Response model for key rotation execution"""
    status: str
    event_id: str
    records_migrated: int
    total_records: int
    duration_seconds: float
    errors: List[str]

class KeyScheduleResponse(BaseModel):
    """Response model for key schedule information"""
    current_time: str
    key_types: Dict[str, Dict[str, Any]]
    overall_status: str
    overdue_key_types: int

class KeyRotationReportResponse(BaseModel):
    """Response model for key rotation reports"""
    generated_at: str
    summary: Dict[str, Any]
    key_details: Dict[str, Dict[str, Any]]
    rotation_history: List[Dict[str, Any]]
    recommendations: List[str]

@router.post("/schedule", response_model=KeyRotationScheduleResponse)
async def schedule_key_rotation(
    request: KeyRotationScheduleRequest,
    current_user: User = Depends(get_admin_user),
    key_service: KeyRotationService = Depends(get_key_rotation_service)
) -> KeyRotationScheduleResponse:
    """
    Schedule key rotation for a specific key type
    
    Initiates key rotation process by generating new keys and preparing
    for data migration. Use force=true to rotate keys before their
    scheduled rotation period.
    """
    try:
        # Validate key type
        try:
            key_type = KeyType(request.key_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid key type '{request.key_type}'. Valid types: {[k.value for k in KeyType]}"
            )
        
        # Schedule rotation
        result = key_service.schedule_key_rotation(key_type, request.force)
        
        # Create response message
        if result["action"] == "rotation_not_due":
            message = f"Key rotation not due. Next rotation in {result['rotation_due_in_days']} days."
        elif result["action"] == "initial_key_created":
            message = f"Initial {key_type.value} key created successfully."
        elif result["action"] == "rotation_scheduled":
            message = f"Key rotation scheduled for {key_type.value}. Ready for execution."
        else:
            message = f"Key rotation action: {result['action']}"
        
        logger.info(f"Key rotation scheduled by admin {current_user.id}: {key_type.value}")
        
        return KeyRotationScheduleResponse(
            action=result["action"],
            event_id=result.get("event_id"),
            key_id=result.get("key_id") or result.get("new_key_id"),
            key_type=key_type.value,
            message=message,
            scheduled_at=result.get("scheduled_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule key rotation for {request.key_type}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to schedule key rotation: {str(e)}"
        )

@router.post("/execute", response_model=KeyRotationExecuteResponse)
async def execute_key_rotation(
    request: KeyRotationExecuteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    key_service: KeyRotationService = Depends(get_key_rotation_service)
) -> KeyRotationExecuteResponse:
    """
    Execute scheduled key rotation
    
    WARNING: This operation migrates encrypted data to use new keys.
    Ensure you have database backups before proceeding. The operation
    cannot be easily reversed once completed.
    """
    try:
        # Execute rotation
        result = key_service.execute_key_rotation(
            db=db,
            event_id=request.event_id,
            batch_size=request.batch_size
        )
        
        logger.info(f"Key rotation executed by admin {current_user.id}: {request.event_id}")
        
        return KeyRotationExecuteResponse(
            status=result["status"],
            event_id=result["event_id"],
            records_migrated=result["records_migrated"],
            total_records=result["total_records"],
            duration_seconds=result["duration_seconds"],
            errors=result.get("errors", [])
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Key rotation execution failed for {request.event_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Key rotation execution failed: {str(e)}"
        )

@router.get("/schedule", response_model=KeyScheduleResponse)
async def get_key_rotation_schedule(
    current_user: User = Depends(get_admin_user),
    key_service: KeyRotationService = Depends(get_key_rotation_service)
) -> KeyScheduleResponse:
    """
    Get current key rotation schedule and status
    
    Returns information about all key types, their rotation schedules,
    current age, and whether any keys are overdue for rotation.
    """
    try:
        schedule = key_service.get_key_rotation_schedule()
        
        return KeyScheduleResponse(
            current_time=schedule["current_time"],
            key_types=schedule["key_types"],
            overall_status=schedule["overall_status"],
            overdue_key_types=schedule["overdue_key_types"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get key rotation schedule: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve key rotation schedule"
        )

@router.get("/keys/{key_type}")
async def get_active_keys(
    key_type: str,
    current_user: User = Depends(get_admin_user),
    key_service: KeyRotationService = Depends(get_key_rotation_service)
) -> Dict[str, Any]:
    """
    Get active keys for a specific key type
    
    Returns metadata about currently active keys including creation dates,
    algorithms, and usage statistics (without exposing key material).
    """
    try:
        # Validate key type
        try:
            key_type_enum = KeyType(key_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid key type '{key_type}'"
            )
        
        active_keys = key_service.get_active_keys(key_type_enum)
        
        return {
            "key_type": key_type,
            "active_keys_count": len(active_keys),
            "keys": active_keys,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get active keys for {key_type}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve active keys"
        )

@router.post("/cleanup")
async def cleanup_expired_keys(
    current_user: User = Depends(get_admin_user),
    key_service: KeyRotationService = Depends(get_key_rotation_service)
) -> JSONResponse:
    """
    Clean up expired and deprecated keys
    
    Removes old keys that have passed their grace period after rotation.
    This operation helps maintain security hygiene by ensuring old keys
    cannot be used maliciously.
    """
    try:
        result = key_service.cleanup_expired_keys()
        
        logger.info(f"Key cleanup executed by admin {current_user.id}: {result['cleaned_keys']} keys cleaned")
        
        return JSONResponse(content={
            "message": f"Cleaned up {result['cleaned_keys']} expired keys",
            "cleaned_keys": result["keys"],
            "cleanup_date": result["cleanup_date"]
        })
        
    except Exception as e:
        logger.error(f"Key cleanup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Key cleanup failed: {str(e)}"
        )

@router.get("/report", response_model=KeyRotationReportResponse)
async def get_key_rotation_report(
    current_user: User = Depends(get_admin_user),
    key_service: KeyRotationService = Depends(get_key_rotation_service)
) -> KeyRotationReportResponse:
    """
    Generate comprehensive key rotation compliance report
    
    Provides detailed overview of key rotation status, history,
    and recommendations for maintaining security compliance.
    """
    try:
        report = key_service.generate_key_rotation_report()
        
        logger.info(f"Key rotation report generated for admin {current_user.id}")
        
        return KeyRotationReportResponse(
            generated_at=report["generated_at"],
            summary=report["summary"],
            key_details=report["key_details"],
            rotation_history=report["rotation_history"],
            recommendations=report["recommendations"]
        )
        
    except Exception as e:
        logger.error(f"Failed to generate key rotation report: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate key rotation report"
        )

@router.get("/health")
async def key_rotation_health_check(
    current_user: User = Depends(get_admin_user),
    key_service: KeyRotationService = Depends(get_key_rotation_service)
) -> Dict[str, Any]:
    """
    Health check for key rotation system
    
    Provides basic health information about the key rotation system
    including service status and critical alerts.
    """
    try:
        schedule = key_service.get_key_rotation_schedule()
        
        # Check for critical issues
        critical_issues = []
        warnings = []
        
        for key_type_str, details in schedule["key_types"].items():
            if details.get("status") == "no_keys":
                critical_issues.append(f"No active keys for {key_type_str}")
            elif details.get("is_overdue"):
                if details["oldest_key_age_days"] > (details["rotation_interval_days"] * 1.5):
                    critical_issues.append(f"{key_type_str} keys severely overdue ({details['oldest_key_age_days']} days)")
                else:
                    warnings.append(f"{key_type_str} keys overdue for rotation")
        
        health_status = "healthy"
        if critical_issues:
            health_status = "critical"
        elif warnings:
            health_status = "warning"
        
        return {
            "status": health_status,
            "overall_status": schedule["overall_status"],
            "overdue_key_types": schedule["overdue_key_types"],
            "total_key_types": len(schedule["key_types"]),
            "critical_issues": critical_issues,
            "warnings": warnings,
            "service_operational": True,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Key rotation health check failed: {e}")
        return {
            "status": "unhealthy",
            "service_operational": False,
            "error": str(e),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }

@router.get("/key-types")
async def get_supported_key_types(
    current_user: User = Depends(get_admin_user)
) -> Dict[str, List[str]]:
    """
    Get all supported key types for rotation
    
    Returns list of all key types that can be managed through
    the key rotation system.
    """
    try:
        key_types = {
            "key_types": [key_type.value for key_type in KeyType],
            "descriptions": {
                KeyType.TOKEN_ENCRYPTION.value: "OAuth and API token encryption",
                KeyType.DATABASE_ENCRYPTION.value: "Database field encryption",
                KeyType.FILE_ENCRYPTION.value: "File and document encryption",
                KeyType.SESSION_ENCRYPTION.value: "User session encryption",
                KeyType.API_SIGNATURE.value: "API request signing keys"
            }
        }
        
        return key_types
        
    except Exception as e:
        logger.error(f"Failed to retrieve key types: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve supported key types"
        )

@router.post("/emergency-rotation")
async def emergency_key_rotation(
    key_type: str,
    reason: str = "emergency_security_incident",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    key_service: KeyRotationService = Depends(get_key_rotation_service)
) -> JSONResponse:
    """
    Emergency key rotation for security incidents
    
    Immediately rotates keys for a specific type, bypassing normal
    scheduling checks. Use only during security incidents or when
    key compromise is suspected.
    """
    try:
        # Validate key type
        try:
            key_type_enum = KeyType(key_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid key type '{key_type}'"
            )
        
        # Schedule emergency rotation
        schedule_result = key_service.schedule_key_rotation(key_type_enum, force=True)
        
        if schedule_result["action"] != "rotation_scheduled":
            return JSONResponse(content={
                "message": f"Emergency rotation not needed: {schedule_result['action']}",
                "action": schedule_result["action"],
                "key_type": key_type
            })
        
        # Execute rotation immediately in background
        event_id = schedule_result["event_id"]
        background_tasks.add_task(
            _emergency_rotation_task,
            event_id=event_id,
            key_type=key_type,
            reason=reason,
            admin_user_id=current_user.id
        )
        
        logger.warning(f"Emergency key rotation initiated by admin {current_user.id}: {key_type} - {reason}")
        
        return JSONResponse(content={
            "message": f"Emergency key rotation initiated for {key_type}",
            "event_id": event_id,
            "reason": reason,
            "initiated_at": datetime.now(timezone.utc).isoformat(),
            "status": "processing_in_background"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Emergency key rotation failed for {key_type}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Emergency key rotation failed: {str(e)}"
        )

async def _emergency_rotation_task(event_id: str, key_type: str, reason: str, admin_user_id: int):
    """Background task for emergency key rotation"""
    try:
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            key_service = get_key_rotation_service()
            result = key_service.execute_key_rotation(db, event_id, batch_size=500)
            
            logger.info(f"Emergency key rotation completed: {key_type} - {result}")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Emergency key rotation task failed: {key_type} - {e}")

@router.post("/schedule-all")
async def schedule_all_overdue_rotations(
    force_all: bool = False,
    current_user: User = Depends(get_admin_user),
    key_service: KeyRotationService = Depends(get_key_rotation_service)
) -> JSONResponse:
    """
    Schedule rotation for all overdue keys
    
    Convenience endpoint to schedule rotation for all key types that
    are past their rotation interval. Use force_all=true to rotate
    all keys regardless of schedule.
    """
    try:
        results = {}
        scheduled_count = 0
        
        for key_type in KeyType:
            try:
                result = key_service.schedule_key_rotation(key_type, force=force_all)
                results[key_type.value] = result
                
                if result["action"] == "rotation_scheduled":
                    scheduled_count += 1
                    
            except Exception as e:
                results[key_type.value] = {
                    "action": "error",
                    "error": str(e)
                }
        
        logger.info(f"Bulk key rotation scheduling by admin {current_user.id}: {scheduled_count} scheduled")
        
        return JSONResponse(content={
            "message": f"Scheduled rotation for {scheduled_count} key types",
            "scheduled_count": scheduled_count,
            "total_key_types": len(KeyType),
            "results": results,
            "scheduled_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Bulk key rotation scheduling failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Bulk scheduling failed: {str(e)}"
        )