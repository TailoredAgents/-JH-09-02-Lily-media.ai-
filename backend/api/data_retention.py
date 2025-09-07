"""
Data Retention Management API

Provides endpoints for managing data retention policies, monitoring expired data,
and executing cleanup operations in compliance with GDPR/CCPA requirements.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.db.database import get_db
from backend.db.models import User
from backend.auth.dependencies import get_current_user, get_admin_user
from backend.services.data_retention_service import (
    DataRetentionService, DataCategory, RetentionPolicy,
    get_data_retention_service
)
from backend.core.api_version import create_versioned_router

logger = logging.getLogger(__name__)

router = create_versioned_router(prefix="/data-retention", tags=["data-retention"])

class RetentionPolicyResponse(BaseModel):
    """Response model for retention policy"""
    category: str
    retention_days: int
    description: str
    automatic_cleanup: bool
    legal_hold_exempt: bool
    gdpr_category: Optional[str]
    ccpa_category: Optional[str]

class DataCleanupRequest(BaseModel):
    """Request model for data cleanup operations"""
    category: str
    dry_run: bool = True
    force_cleanup: bool = False

class DataCleanupResponse(BaseModel):
    """Response model for cleanup operations"""
    category: str
    dry_run: bool
    deleted_counts: Dict[str, int]
    total_deleted: int
    errors: List[str]
    cleanup_date: str
    expired_counts: Optional[Dict[str, int]] = None

class RetentionReportResponse(BaseModel):
    """Response model for retention reports"""
    generated_at: str
    policies: Dict[str, Dict[str, Any]]
    expired_data_summary: Dict[str, Dict[str, int]]
    total_expired_records: int
    recommendations: List[str]

@router.get("/policies", response_model=Dict[str, RetentionPolicyResponse])
async def get_retention_policies(
    current_user: User = Depends(get_admin_user),
    retention_service: DataRetentionService = Depends(get_data_retention_service)
) -> Dict[str, RetentionPolicyResponse]:
    """
    Get all data retention policies
    
    Returns comprehensive information about retention policies for all data categories,
    including GDPR and CCPA compliance information.
    """
    try:
        policies = retention_service.get_all_retention_policies()
        
        response = {}
        for category, policy in policies.items():
            response[category.value] = RetentionPolicyResponse(
                category=category.value,
                retention_days=policy.retention_days,
                description=policy.description,
                automatic_cleanup=policy.automatic_cleanup,
                legal_hold_exempt=policy.legal_hold_exempt,
                gdpr_category=policy.gdpr_category,
                ccpa_category=policy.ccpa_category
            )
        
        logger.info(f"Retrieved {len(policies)} retention policies for admin user {current_user.id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to retrieve retention policies: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve retention policies"
        )

@router.get("/policies/{category}", response_model=RetentionPolicyResponse)
async def get_retention_policy(
    category: str,
    current_user: User = Depends(get_admin_user),
    retention_service: DataRetentionService = Depends(get_data_retention_service)
) -> RetentionPolicyResponse:
    """
    Get retention policy for a specific data category
    """
    try:
        # Validate category
        try:
            data_category = DataCategory(category)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category '{category}'. Valid categories: {[c.value for c in DataCategory]}"
            )
        
        policy = retention_service.get_retention_policy(data_category)
        if not policy:
            raise HTTPException(
                status_code=404,
                detail=f"No retention policy found for category '{category}'"
            )
        
        return RetentionPolicyResponse(
            category=policy.category.value,
            retention_days=policy.retention_days,
            description=policy.description,
            automatic_cleanup=policy.automatic_cleanup,
            legal_hold_exempt=policy.legal_hold_exempt,
            gdpr_category=policy.gdpr_category,
            ccpa_category=policy.ccpa_category
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve retention policy for {category}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve retention policy"
        )

@router.get("/expired-data", response_model=Dict[str, Dict[str, int]])
async def get_expired_data_summary(
    category: Optional[str] = Query(None, description="Filter by specific data category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    retention_service: DataRetentionService = Depends(get_data_retention_service)
) -> Dict[str, Dict[str, int]]:
    """
    Get summary of expired data across all or specific categories
    
    Returns counts of expired records that are eligible for cleanup based on
    retention policies. Use this to monitor data retention compliance.
    """
    try:
        expired_summary = {}
        
        if category:
            # Get expired data for specific category
            try:
                data_category = DataCategory(category)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category '{category}'"
                )
            
            expired_counts = retention_service.get_expired_data_count(db, data_category)
            if any(expired_counts.values()):
                expired_summary[category] = expired_counts
        else:
            # Get expired data for all categories
            for data_category in DataCategory:
                expired_counts = retention_service.get_expired_data_count(db, data_category)
                if any(expired_counts.values()):
                    expired_summary[data_category.value] = expired_counts
        
        total_expired = sum(
            sum(counts.values()) 
            for counts in expired_summary.values()
        )
        
        logger.info(f"Retrieved expired data summary: {total_expired} total expired records")
        return expired_summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve expired data summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve expired data summary"
        )

@router.post("/cleanup", response_model=DataCleanupResponse)
async def cleanup_expired_data(
    request: DataCleanupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    retention_service: DataRetentionService = Depends(get_data_retention_service)
) -> DataCleanupResponse:
    """
    Execute data cleanup for expired records
    
    Performs cleanup of expired data according to retention policies. Use dry_run=true
    to preview what would be deleted before executing actual cleanup.
    
    WARNING: This operation is irreversible when dry_run=false.
    """
    try:
        # Validate category
        try:
            data_category = DataCategory(request.category)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category '{request.category}'"
            )
        
        # Get retention policy
        policy = retention_service.get_retention_policy(data_category)
        if not policy:
            raise HTTPException(
                status_code=404,
                detail=f"No retention policy found for category '{request.category}'"
            )
        
        # Check if automatic cleanup is enabled or force is requested
        if not policy.automatic_cleanup and not request.force_cleanup:
            raise HTTPException(
                status_code=400,
                detail=f"Automatic cleanup disabled for {request.category}. Use force_cleanup=true to override."
            )
        
        # Perform cleanup
        cleanup_results = retention_service.cleanup_expired_data(
            db=db,
            category=data_category,
            dry_run=request.dry_run
        )
        
        # Log the operation
        operation_type = "DRY RUN" if request.dry_run else "CLEANUP"
        total_deleted = cleanup_results.get("total_deleted", 0)
        logger.info(f"Data {operation_type} for {request.category} by admin {current_user.id}: {total_deleted} records")
        
        # Convert to response model
        response = DataCleanupResponse(
            category=cleanup_results["category"],
            dry_run=cleanup_results["dry_run"],
            deleted_counts=cleanup_results.get("deleted_counts", {}),
            total_deleted=cleanup_results["total_deleted"],
            errors=cleanup_results.get("errors", []),
            cleanup_date=cleanup_results["cleanup_date"],
            expired_counts=cleanup_results.get("expired_counts")
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data cleanup failed for {request.category}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Data cleanup operation failed: {str(e)}"
        )

@router.get("/report", response_model=RetentionReportResponse)
async def generate_retention_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    retention_service: DataRetentionService = Depends(get_data_retention_service)
) -> RetentionReportResponse:
    """
    Generate comprehensive data retention compliance report
    
    Provides detailed overview of retention policies, expired data counts,
    and recommendations for maintaining compliance.
    """
    try:
        report = retention_service.generate_retention_report(db)
        
        logger.info(f"Generated retention report for admin {current_user.id}: {report['total_expired_records']} expired records")
        
        return RetentionReportResponse(
            generated_at=report["generated_at"],
            policies=report["policies"],
            expired_data_summary=report["expired_data_summary"],
            total_expired_records=report["total_expired_records"],
            recommendations=report["recommendations"]
        )
        
    except Exception as e:
        logger.error(f"Failed to generate retention report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate retention report"
        )

@router.get("/categories")
async def get_data_categories(
    current_user: User = Depends(get_admin_user)
) -> Dict[str, List[str]]:
    """
    Get all available data categories
    
    Returns list of all data categories that can be managed through
    the retention policy system.
    """
    try:
        categories = {
            "categories": [category.value for category in DataCategory],
            "descriptions": {
                category.value: {
                    "name": category.value.replace("_", " ").title(),
                    "enum_value": category.value
                }
                for category in DataCategory
            }
        }
        
        return categories
        
    except Exception as e:
        logger.error(f"Failed to retrieve data categories: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve data categories"
        )

@router.post("/schedule-cleanup")
async def schedule_automated_cleanup(
    categories: Optional[List[str]] = None,
    dry_run: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    retention_service: DataRetentionService = Depends(get_data_retention_service)
) -> JSONResponse:
    """
    Schedule automated cleanup for multiple categories
    
    Schedules background cleanup tasks for specified categories or all categories
    with automatic_cleanup enabled.
    """
    try:
        if not categories:
            # Get all categories with automatic cleanup enabled
            all_policies = retention_service.get_all_retention_policies()
            categories = [
                category.value 
                for category, policy in all_policies.items()
                if policy.automatic_cleanup
            ]
        
        # Validate all categories
        valid_categories = []
        for category_str in categories:
            try:
                data_category = DataCategory(category_str)
                valid_categories.append(data_category)
            except ValueError:
                logger.warning(f"Skipping invalid category: {category_str}")
        
        if not valid_categories:
            raise HTTPException(
                status_code=400,
                detail="No valid categories specified for cleanup"
            )
        
        # Schedule cleanup tasks
        scheduled_tasks = []
        for category in valid_categories:
            # In a production environment, this would use Celery or similar
            # For now, we'll add to FastAPI background tasks
            background_tasks.add_task(
                _background_cleanup_task,
                category=category,
                dry_run=dry_run,
                admin_user_id=current_user.id
            )
            scheduled_tasks.append(category.value)
        
        logger.info(f"Scheduled cleanup tasks for {len(scheduled_tasks)} categories by admin {current_user.id}")
        
        return JSONResponse(content={
            "message": f"Scheduled cleanup for {len(scheduled_tasks)} categories",
            "scheduled_categories": scheduled_tasks,
            "dry_run": dry_run,
            "scheduled_at": datetime.now(timezone.utc).isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule automated cleanup: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to schedule automated cleanup"
        )

async def _background_cleanup_task(category: DataCategory, dry_run: bool, admin_user_id: int):
    """Background task for data cleanup"""
    try:
        # Get database session using the FastAPI dependency pattern
        db_gen = get_db()
        db = next(db_gen)
        try:
            retention_service = get_data_retention_service()
            result = retention_service.cleanup_expired_data(db, category, dry_run)
            
            operation_type = "DRY RUN" if dry_run else "CLEANUP"
            logger.info(f"Background {operation_type} completed for {category.value}: {result}")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Background cleanup task failed for {category.value}: {e}")

@router.get("/health")
async def retention_health_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    retention_service: DataRetentionService = Depends(get_data_retention_service)
) -> Dict[str, Any]:
    """
    Health check for data retention system
    
    Provides basic health information about the retention system without
    requiring admin privileges.
    """
    try:
        # Get basic stats
        total_policies = len(retention_service.get_all_retention_policies())
        
        # Quick check for any expired data (limited to avoid performance impact)
        has_expired_data = False
        try:
            # Just check one category quickly
            expired_counts = retention_service.get_expired_data_count(db, DataCategory.NOTIFICATIONS)
            has_expired_data = any(expired_counts.values())
        except:
            pass  # Don't fail health check on this
        
        return {
            "status": "healthy",
            "total_retention_policies": total_policies,
            "has_expired_data": has_expired_data,
            "service_operational": True,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Retention health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "service_operational": False,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }