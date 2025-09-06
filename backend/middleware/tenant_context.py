"""
Tenant Context Middleware for Multi-Tenant Isolation
Implements comprehensive tenant isolation enforcement as required by the production audit.
"""
import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import UserOrganizationRole
from backend.auth.dependencies import get_current_user, AuthUser

logger = logging.getLogger(__name__)


class TenantContext:
    """
    Tenant context object that ensures proper isolation between organizations
    """
    def __init__(self, user: AuthUser, organization_id: int, role: str):
        self.user = user
        self.organization_id = organization_id
        self.role = role
        self.user_id = user.id


async def get_tenant_context(
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TenantContext:
    """
    Extract and validate tenant context from request headers.
    
    This dependency ensures:
    1. X-Organization-ID header is present
    2. User has valid membership in the organization
    3. Returns TenantContext with validated organization and role information
    
    Raises:
        HTTPException: If organization header is missing or user lacks access
    """
    # Extract organization ID from header
    org_id_header = request.headers.get("X-Organization-ID")
    
    if not org_id_header:
        logger.warning(f"Missing X-Organization-ID header for user {current_user.id}")
        raise HTTPException(
            status_code=400,
            detail="Missing X-Organization-ID header. Multi-tenant requests require organization context."
        )
    
    try:
        organization_id = int(org_id_header)
    except ValueError:
        logger.warning(f"Invalid X-Organization-ID header: {org_id_header}")
        raise HTTPException(
            status_code=400,
            detail="Invalid X-Organization-ID header. Must be a valid integer."
        )
    
    # Validate user membership in organization
    membership = db.query(UserOrganizationRole).filter(
        UserOrganizationRole.user_id == current_user.id,
        UserOrganizationRole.organization_id == organization_id
    ).first()
    
    if not membership:
        logger.warning(
            f"User {current_user.id} attempted to access organization {organization_id} without membership"
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied. User is not a member of the specified organization."
        )
    
    logger.debug(
        f"Validated tenant context: user={current_user.id}, org={organization_id}, role={membership.role}"
    )
    
    return TenantContext(
        user=current_user,
        organization_id=organization_id,
        role=membership.role
    )


def get_tenant_context_optional(
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Optional[TenantContext]:
    """
    Optional tenant context for endpoints that can work with or without organization context.
    
    Returns None if X-Organization-ID is not provided or invalid, but doesn't raise an error.
    Used for endpoints that can operate at user level or organization level.
    """
    org_id_header = request.headers.get("X-Organization-ID")
    
    if not org_id_header:
        return None
    
    try:
        organization_id = int(org_id_header)
    except ValueError:
        logger.warning(f"Invalid X-Organization-ID header: {org_id_header}")
        return None
    
    # Validate user membership
    membership = db.query(UserOrganizationRole).filter(
        UserOrganizationRole.user_id == current_user.id,
        UserOrganizationRole.organization_id == organization_id
    ).first()
    
    if not membership:
        logger.warning(
            f"User {current_user.id} attempted to access organization {organization_id} without membership"
        )
        return None
    
    return TenantContext(
        user=current_user,
        organization_id=organization_id,
        role=membership.role
    )


def require_role(required_role: str):
    """
    Dependency factory to enforce role-based access control within organizations.
    
    Args:
        required_role: Minimum role required (e.g., 'admin', 'member')
    
    Returns:
        Dependency that validates user has required role in organization
    """
    def role_dependency(tenant_context: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        # Role hierarchy: admin > member > viewer
        role_hierarchy = {"viewer": 0, "member": 1, "admin": 2}
        
        user_level = role_hierarchy.get(tenant_context.role, 0)
        required_level = role_hierarchy.get(required_role, 999)
        
        if user_level < required_level:
            logger.warning(
                f"User {tenant_context.user_id} with role {tenant_context.role} "
                f"attempted to access endpoint requiring {required_role}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: {required_role}, user role: {tenant_context.role}"
            )
        
        return tenant_context
    
    return role_dependency


def create_celery_context(tenant_context: TenantContext) -> Dict[str, Any]:
    """
    Create context dictionary to pass to Celery tasks.
    
    This ensures tenant context propagation to background tasks.
    
    Args:
        tenant_context: Validated tenant context from request
        
    Returns:
        Dictionary with tenant information for Celery tasks
    """
    return {
        "user_id": tenant_context.user_id,
        "organization_id": tenant_context.organization_id,
        "role": tenant_context.role
    }


def validate_celery_context(context: Dict[str, Any]) -> bool:
    """
    Validate that Celery task context contains required tenant information.
    
    Args:
        context: Context dictionary passed to Celery task
        
    Returns:
        True if context is valid, False otherwise
    """
    required_keys = ["user_id", "organization_id", "role"]
    return all(key in context and context[key] is not None for key in required_keys)