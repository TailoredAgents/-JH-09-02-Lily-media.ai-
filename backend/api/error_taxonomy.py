"""
Error Taxonomy API

Provides endpoints for error taxonomy management, classification, and reporting.
Part of Agent 1 (P0-8d) comprehensive error taxonomy mapping implementation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timezone

from backend.core.dependencies import get_db, get_current_admin_user
from backend.db.models import User
from backend.services.error_taxonomy_service import (
    get_error_taxonomy_service,
    ErrorCategory,
    ErrorSeverity,
    ErrorTaxonomyService
)
from backend.core.audit_logger import audit_logger
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/error-taxonomy", tags=["error-taxonomy"])

class ErrorClassificationRequest(BaseModel):
    """Request model for error classification"""
    error_code: str
    context: Optional[Dict[str, Any]] = None

class ErrorStatisticsRequest(BaseModel):
    """Request model for error statistics"""
    time_window_hours: int = 24
    category_filter: Optional[str] = None

@router.get("/status", response_model=Dict[str, Any])
async def get_taxonomy_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get error taxonomy system status"""
    try:
        service = get_error_taxonomy_service()
        
        # Get validation results
        validation_results = service.validate_taxonomy_completeness()
        
        # Get basic statistics
        stats = service.get_error_statistics(time_window_hours=24)
        
        # Get compliance overview
        compliance_report = service.get_compliance_report()
        
        status = {
            "system_status": "healthy" if validation_results["validation_passed"] else "incomplete",
            "taxonomy_coverage": {
                "total_error_codes": validation_results["total_defined_codes"],
                "mapped_codes": validation_results["total_mapped_codes"],
                "coverage_percentage": validation_results["coverage_percentage"],
                "missing_entries": len(validation_results["missing_taxonomy_entries"])
            },
            "error_activity_24h": {
                "total_errors": stats["total_errors"],
                "error_rate_per_hour": stats["error_rate_per_hour"],
                "critical_errors": len(stats["critical_errors"]),
                "customer_visible_errors": stats["customer_visible_errors"]
            },
            "compliance_overview": {
                "compliance_impacting": compliance_report["compliance_impacting_errors"],
                "gdpr_relevant": compliance_report["gdpr_relevant_errors"],
                "audit_required": compliance_report["audit_required_errors"],
                "security_errors": compliance_report["security_errors"]
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        # Log admin access
        audit_logger.log_event(
            event_type="error_taxonomy_status_accessed",
            user_id=current_user.id,
            details={
                "coverage_percentage": validation_results["coverage_percentage"],
                "total_errors_24h": stats["total_errors"]
            }
        )
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get taxonomy status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve taxonomy status"
        )

@router.post("/classify", response_model=Dict[str, Any])
async def classify_error(
    request: ErrorClassificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Classify an error code and get comprehensive handling information"""
    try:
        service = get_error_taxonomy_service()
        
        # Get taxonomy entry
        taxonomy = service.get_error_taxonomy(request.error_code)
        if not taxonomy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Error code '{request.error_code}' not found in taxonomy"
            )
        
        # Record occurrence if context provided
        if request.context:
            service.record_error_occurrence(request.error_code, request.context)
        
        # Get user-friendly information
        user_friendly = service.get_user_friendly_error(request.error_code, request.context)
        
        # Get troubleshooting guide
        troubleshooting = service.get_troubleshooting_guide(request.error_code)
        
        result = {
            "error_code": request.error_code,
            "classification": {
                "name": taxonomy.name,
                "description": taxonomy.description,
                "category": taxonomy.category.value,
                "subcategory": taxonomy.subcategory.value,
                "severity": taxonomy.severity.value,
                "impact": taxonomy.impact.value
            },
            "user_facing": {
                "message": user_friendly["message"],
                "action": user_friendly["action"],
                "can_retry": user_friendly["can_retry"],
                "has_fallback": user_friendly["has_fallback"],
                "contact_support": user_friendly["contact_support"]
            },
            "operational": {
                "should_alert": taxonomy.should_alert,
                "alert_channels": taxonomy.alert_channels,
                "escalation_required": taxonomy.escalation_required,
                "auto_recoverable": taxonomy.auto_recoverable,
                "recovery_actions": taxonomy.recovery_actions
            },
            "compliance": {
                "compliance_impact": taxonomy.compliance_impact,
                "audit_required": taxonomy.audit_required,
                "gdpr_relevant": taxonomy.gdpr_relevant
            },
            "troubleshooting": troubleshooting
        }
        
        # Log classification request
        audit_logger.log_event(
            event_type="error_classification_performed",
            user_id=current_user.id,
            details={
                "error_code": request.error_code,
                "severity": taxonomy.severity.value,
                "category": taxonomy.category.value
            }
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to classify error {request.error_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error classification failed"
        )

@router.post("/statistics", response_model=Dict[str, Any])
async def get_error_statistics(
    request: ErrorStatisticsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get comprehensive error statistics for monitoring and reporting"""
    try:
        service = get_error_taxonomy_service()
        
        # Parse category filter
        category_filter = None
        if request.category_filter:
            try:
                category_filter = ErrorCategory(request.category_filter.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category filter: {request.category_filter}"
                )
        
        # Get statistics
        stats = service.get_error_statistics(
            time_window_hours=request.time_window_hours,
            category_filter=category_filter
        )
        
        # Add additional analysis
        result = {
            **stats,
            "analysis": {
                "error_trend": "stable" if stats["error_rate_per_hour"] < 5 else "elevated" if stats["error_rate_per_hour"] < 20 else "critical",
                "critical_alert_needed": len(stats["critical_errors"]) > 0,
                "customer_impact_score": min(100, (stats["customer_visible_errors"] / max(stats["total_errors"], 1)) * 100),
                "system_health": "healthy" if len(stats["critical_errors"]) == 0 and stats["error_rate_per_hour"] < 10 else "degraded"
            },
            "recommendations": []
        }
        
        # Add recommendations based on statistics
        if len(stats["critical_errors"]) > 0:
            result["recommendations"].append("Immediate investigation required for critical errors")
        
        if stats["error_rate_per_hour"] > 20:
            result["recommendations"].append("Error rate is elevated - consider scaling or performance investigation")
        
        if stats["customer_visible_errors"] > stats["total_errors"] * 0.3:
            result["recommendations"].append("High customer-visible error rate - review user experience impact")
        
        # Log statistics request
        audit_logger.log_event(
            event_type="error_statistics_accessed",
            user_id=current_user.id,
            details={
                "time_window_hours": request.time_window_hours,
                "category_filter": request.category_filter,
                "total_errors": stats["total_errors"],
                "error_rate": stats["error_rate_per_hour"]
            }
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get error statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve error statistics"
        )

@router.get("/categories", response_model=Dict[str, List[str]])
async def get_taxonomy_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, List[str]]:
    """Get available taxonomy categories and subcategories"""
    try:
        from backend.services.error_taxonomy_service import ErrorCategory, ErrorSubcategory, ErrorSeverity, ErrorImpact
        
        categories = {
            "categories": [category.value for category in ErrorCategory],
            "subcategories": [subcategory.value for subcategory in ErrorSubcategory],
            "severities": [severity.value for severity in ErrorSeverity],
            "impacts": [impact.value for impact in ErrorImpact]
        }
        
        # Log categories access
        audit_logger.log_event(
            event_type="error_taxonomy_categories_accessed",
            user_id=current_user.id,
            details={"categories_count": len(categories["categories"])}
        )
        
        return categories
        
    except Exception as e:
        logger.error(f"Failed to get taxonomy categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve taxonomy categories"
        )

@router.get("/compliance/report", response_model=Dict[str, Any])
async def get_compliance_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Generate comprehensive compliance-focused error report"""
    try:
        service = get_error_taxonomy_service()
        
        # Get compliance report
        report = service.get_compliance_report()
        
        # Get recent statistics for compliance-relevant errors
        recent_stats = service.get_error_statistics(time_window_hours=168)  # 7 days
        
        # Enhanced compliance analysis
        compliance_analysis = {
            **report,
            "recent_activity": {
                "total_errors_7d": recent_stats["total_errors"],
                "compliance_errors_7d": len([
                    code for code in recent_stats["top_errors"].keys()
                    if service.get_error_taxonomy(code) and service.get_error_taxonomy(code).compliance_impact
                ]),
                "security_incidents_7d": len([
                    code for code in recent_stats["top_errors"].keys()
                    if service.get_error_taxonomy(code) and service.get_error_taxonomy(code).category.value == "security"
                ])
            },
            "risk_assessment": {
                "compliance_risk": "high" if report["compliance_impacting_errors"] > 10 else "medium" if report["compliance_impacting_errors"] > 5 else "low",
                "gdpr_risk": "high" if report["gdpr_relevant_errors"] > 5 else "medium" if report["gdpr_relevant_errors"] > 2 else "low",
                "audit_readiness": "ready" if report["audit_required_errors"] == 0 else "needs_attention"
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_period": "last_7_days"
        }
        
        # Log compliance report access
        audit_logger.log_event(
            event_type="compliance_report_generated",
            user_id=current_user.id,
            details={
                "compliance_errors": report["compliance_impacting_errors"],
                "gdpr_errors": report["gdpr_relevant_errors"],
                "security_errors": report["security_errors"]
            }
        )
        
        return compliance_analysis
        
    except Exception as e:
        logger.error(f"Failed to generate compliance report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate compliance report"
        )

@router.get("/export/taxonomy", response_model=Dict[str, Any])
async def export_taxonomy_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Export complete error taxonomy configuration"""
    try:
        service = get_error_taxonomy_service()
        
        # Export taxonomy configuration
        config = service.export_taxonomy_config()
        
        # Log export
        audit_logger.log_event(
            event_type="error_taxonomy_exported",
            user_id=current_user.id,
            details={
                "total_entries": config["total_entries"],
                "export_timestamp": config["generated_at"]
            }
        )
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to export taxonomy config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export taxonomy configuration"
        )

@router.get("/validation/completeness", response_model=Dict[str, Any])
async def validate_taxonomy_completeness(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Validate taxonomy completeness and coverage"""
    try:
        service = get_error_taxonomy_service()
        
        # Get validation results
        validation_results = service.validate_taxonomy_completeness()
        
        # Add recommendations
        recommendations = []
        if validation_results["missing_taxonomy_entries"]:
            recommendations.append(f"Add taxonomy entries for {len(validation_results['missing_taxonomy_entries'])} missing error codes")
        
        if validation_results["unmapped_codes"]:
            recommendations.append(f"Review {len(validation_results['unmapped_codes'])} unmapped taxonomy entries")
        
        if validation_results["coverage_percentage"] < 100:
            recommendations.append("Achieve 100% taxonomy coverage for comprehensive error handling")
        
        result = {
            **validation_results,
            "recommendations": recommendations,
            "validation_status": "complete" if validation_results["validation_passed"] else "incomplete",
            "validated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Log validation
        audit_logger.log_event(
            event_type="taxonomy_validation_performed",
            user_id=current_user.id,
            details={
                "coverage_percentage": validation_results["coverage_percentage"],
                "missing_entries": len(validation_results["missing_taxonomy_entries"]),
                "validation_passed": validation_results["validation_passed"]
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to validate taxonomy completeness: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate taxonomy completeness"
        )

@router.get("/troubleshooting/{error_code}", response_model=Dict[str, Any])
async def get_troubleshooting_guide(
    error_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get detailed troubleshooting guide for an error code"""
    try:
        service = get_error_taxonomy_service()
        
        # Get troubleshooting guide
        guide = service.get_troubleshooting_guide(error_code)
        
        if "error" in guide:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Error code '{error_code}' not found in taxonomy"
            )
        
        # Log troubleshooting access
        audit_logger.log_event(
            event_type="troubleshooting_guide_accessed",
            user_id=current_user.id,
            details={
                "error_code": error_code,
                "severity": guide["severity"]
            }
        )
        
        return guide
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get troubleshooting guide for {error_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve troubleshooting guide"
        )