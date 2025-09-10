"""
Template Validation API

Provides endpoints for validating AI model template coverage, compliance,
and functionality across the platform. Part of Agent 1 (Compliance & Data Protection)
responsibilities for ensuring proper model template implementation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging

from backend.db.database import get_db
from backend.auth.dependencies import get_admin_user
from backend.db.models import User
from backend.services.template_validation_service import (
    TemplateValidationService,
    ValidationIssue,
    ValidationLevel,
    ValidationCategory
)
from backend.core.audit_logger import audit_logger
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/template-validation", tags=["template-validation"])

class ValidationResponse(BaseModel):
    """Response model for validation operations"""
    success: bool
    issues: List[Dict[str, Any]]
    summary: Dict[str, Any]
    metadata: Dict[str, Any]

class ValidationRequest(BaseModel):
    """Request model for validation operations"""
    models: Optional[List[str]] = None
    include_coverage: bool = True
    include_compliance: bool = True
    include_functionality: bool = True
    include_integration: bool = True

@router.get("/status", response_model=Dict[str, Any])
async def get_validation_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
) -> Dict[str, Any]:
    """Get current template validation status overview"""
    try:
        service = TemplateValidationService()
        
        # Get all validation results
        issues = service.validate_template_coverage()
        
        # Categorize issues
        critical_issues = [issue for issue in issues if issue.level == ValidationLevel.CRITICAL]
        warning_issues = [issue for issue in issues if issue.level == ValidationLevel.WARNING]
        info_issues = [issue for issue in issues if issue.level == ValidationLevel.INFO]
        
        # Calculate coverage
        total_models = len(service.expected_models)
        available_models = len([model for model in service.expected_models if service.is_model_available(model)])
        coverage_percentage = (available_models / total_models) * 100 if total_models > 0 else 0
        
        status = {
            "overall_status": "healthy" if len(critical_issues) == 0 else "critical" if len(critical_issues) > 3 else "warning",
            "coverage": {
                "percentage": round(coverage_percentage, 2),
                "available_models": available_models,
                "total_models": total_models,
                "missing_models": [model for model in service.expected_models if not service.is_model_available(model)]
            },
            "issues_summary": {
                "critical": len(critical_issues),
                "warning": len(warning_issues),
                "info": len(info_issues),
                "total": len(issues)
            },
            "last_validation": service.get_validation_metadata()["timestamp"]
        }
        
        # Log admin access
        audit_logger.log_event(
            event_type="template_validation_status_accessed",
            user_id=current_user.id,
            details={
                "coverage_percentage": coverage_percentage,
                "critical_issues": len(critical_issues)
            }
        )
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get validation status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve validation status"
        )

@router.post("/validate", response_model=ValidationResponse)
async def validate_templates(
    request: ValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
) -> ValidationResponse:
    """Run comprehensive template validation"""
    try:
        service = TemplateValidationService()
        
        # Run validation based on request parameters
        all_issues = []
        
        if request.include_coverage:
            coverage_issues = service.validate_template_coverage()
            all_issues.extend(coverage_issues)
        
        if request.include_compliance:
            compliance_issues = service.validate_template_compliance()
            all_issues.extend(compliance_issues)
        
        if request.include_functionality:
            functionality_issues = service.validate_template_functionality()
            all_issues.extend(functionality_issues)
        
        if request.include_integration:
            integration_issues = service.validate_template_integration()
            all_issues.extend(integration_issues)
        
        # Filter by requested models if specified
        if request.models:
            all_issues = [
                issue for issue in all_issues 
                if any(model in issue.details.get("model", "") for model in request.models)
            ]
        
        # Convert issues to dict format
        issues_dict = [
            {
                "category": issue.category.value,
                "level": issue.level.value,
                "message": issue.message,
                "details": issue.details,
                "recommendations": issue.recommendations
            }
            for issue in all_issues
        ]
        
        # Create summary
        summary = {
            "total_issues": len(all_issues),
            "by_level": {
                "critical": len([i for i in all_issues if i.level == ValidationLevel.CRITICAL]),
                "warning": len([i for i in all_issues if i.level == ValidationLevel.WARNING]),
                "info": len([i for i in all_issues if i.level == ValidationLevel.INFO])
            },
            "by_category": {
                "coverage": len([i for i in all_issues if i.category == ValidationCategory.COVERAGE]),
                "compliance": len([i for i in all_issues if i.category == ValidationCategory.COMPLIANCE]),
                "functionality": len([i for i in all_issues if i.category == ValidationCategory.FUNCTIONALITY]),
                "integration": len([i for i in all_issues if i.category == ValidationCategory.INTEGRATION])
            }
        }
        
        # Log validation execution
        audit_logger.log_event(
            event_type="template_validation_executed",
            user_id=current_user.id,
            details={
                "validation_scope": {
                    "include_coverage": request.include_coverage,
                    "include_compliance": request.include_compliance,
                    "include_functionality": request.include_functionality,
                    "include_integration": request.include_integration
                },
                "models_filter": request.models,
                "total_issues": len(all_issues),
                "critical_issues": summary["by_level"]["critical"]
            }
        )
        
        return ValidationResponse(
            success=len([i for i in all_issues if i.level == ValidationLevel.CRITICAL]) == 0,
            issues=issues_dict,
            summary=summary,
            metadata=service.get_validation_metadata()
        )
        
    except Exception as e:
        logger.error(f"Template validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Template validation failed"
        )

@router.get("/models/{model_name}/validate", response_model=Dict[str, Any])
async def validate_specific_model(
    model_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
) -> Dict[str, Any]:
    """Validate a specific model template"""
    try:
        service = TemplateValidationService()
        
        # Check if model exists
        if model_name not in service.expected_models:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_name}' not found in expected models"
            )
        
        # Run model-specific validation
        model_issues = []
        
        # Coverage validation
        if not service.is_model_available(model_name):
            model_issues.append({
                "category": "coverage",
                "level": "critical",
                "message": f"Model {model_name} template not available",
                "details": {"model": model_name},
                "recommendations": [f"Implement {model_name} template class and integration"]
            })
        
        # Get model-specific template info
        template_info = service.get_template_info(model_name)
        
        result = {
            "model": model_name,
            "available": service.is_model_available(model_name),
            "template_info": template_info,
            "issues": model_issues,
            "validation_passed": len([i for i in model_issues if i["level"] == "critical"]) == 0
        }
        
        # Log model validation
        audit_logger.log_event(
            event_type="model_template_validated",
            user_id=current_user.id,
            details={
                "model": model_name,
                "available": result["available"],
                "issues_count": len(model_issues)
            }
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate model {model_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate model {model_name}"
        )

@router.get("/coverage/report", response_model=Dict[str, Any])
async def get_coverage_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
) -> Dict[str, Any]:
    """Get detailed template coverage report"""
    try:
        service = TemplateValidationService()
        
        # Generate comprehensive coverage report
        coverage_data = {}
        
        for model in service.expected_models:
            model_info = service.get_template_info(model)
            coverage_data[model] = {
                "available": service.is_model_available(model),
                "template_class": model_info.get("template_class"),
                "capabilities": model_info.get("capabilities", {}),
                "configuration": model_info.get("configuration", {}),
                "last_tested": model_info.get("last_tested"),
                "issues": []
            }
            
            # Add model-specific issues
            model_issues = [
                issue for issue in service.validate_template_coverage()
                if model in issue.details.get("model", "")
            ]
            coverage_data[model]["issues"] = [
                {
                    "level": issue.level.value,
                    "message": issue.message,
                    "recommendations": issue.recommendations
                }
                for issue in model_issues
            ]
        
        # Calculate overall metrics
        total_models = len(service.expected_models)
        available_models = len([m for m in service.expected_models if service.is_model_available(m)])
        
        report = {
            "coverage_summary": {
                "total_models": total_models,
                "available_models": available_models,
                "coverage_percentage": (available_models / total_models) * 100 if total_models > 0 else 0,
                "missing_models": [m for m in service.expected_models if not service.is_model_available(m)]
            },
            "model_details": coverage_data,
            "generated_at": service.get_validation_metadata()["timestamp"],
            "validation_version": service.get_validation_metadata()["version"]
        }
        
        # Log coverage report access
        audit_logger.log_event(
            event_type="template_coverage_report_accessed",
            user_id=current_user.id,
            details={
                "coverage_percentage": report["coverage_summary"]["coverage_percentage"],
                "available_models": available_models,
                "total_models": total_models
            }
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate coverage report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate coverage report"
        )

@router.post("/fix/auto", response_model=Dict[str, Any])
async def auto_fix_issues(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
) -> Dict[str, Any]:
    """Automatically fix common template validation issues"""
    try:
        service = TemplateValidationService()
        
        # Get current issues
        issues = service.validate_template_coverage()
        fixable_issues = [issue for issue in issues if issue.level != ValidationLevel.CRITICAL]
        
        fixes_applied = []
        fixes_failed = []
        
        for issue in fixable_issues:
            try:
                # Apply automatic fixes based on issue type
                if "configuration" in issue.message.lower():
                    # Configuration fixes
                    fix_result = service.auto_fix_configuration_issue(issue)
                    if fix_result.get("success"):
                        fixes_applied.append({
                            "issue": issue.message,
                            "fix": fix_result.get("description"),
                            "category": issue.category.value
                        })
                elif "integration" in issue.message.lower():
                    # Integration fixes
                    fix_result = service.auto_fix_integration_issue(issue)
                    if fix_result.get("success"):
                        fixes_applied.append({
                            "issue": issue.message,
                            "fix": fix_result.get("description"),
                            "category": issue.category.value
                        })
            except Exception as fix_error:
                fixes_failed.append({
                    "issue": issue.message,
                    "error": str(fix_error),
                    "category": issue.category.value
                })
        
        result = {
            "fixes_attempted": len(fixable_issues),
            "fixes_applied": len(fixes_applied),
            "fixes_failed": len(fixes_failed),
            "applied_fixes": fixes_applied,
            "failed_fixes": fixes_failed,
            "critical_issues_remaining": len([i for i in issues if i.level == ValidationLevel.CRITICAL])
        }
        
        # Log auto-fix execution
        audit_logger.log_event(
            event_type="template_validation_auto_fix",
            user_id=current_user.id,
            details=result
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Auto-fix failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auto-fix operation failed"
        )