"""
Multi-tenant API endpoints for organization, team, and role management
Provides RESTful API for managing multi-tenancy features
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.auth.dependencies import get_current_user, AuthUser
from backend.services.multi_tenant_service import get_multi_tenant_service, MultiTenantError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organizations", tags=["Multi-Tenancy"])

# Request/Response models
class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-z0-9\-]+$')
    description: Optional[str] = Field(None, max_length=500)
    plan_type: str = Field("starter", pattern=r'^(starter|professional|enterprise)$')

    @field_validator('slug')
    @classmethod
    def slug_must_be_lowercase(cls, v):
        if v != v.lower():
            raise ValueError('Slug must be lowercase')
        return v

class OrganizationResponse(BaseModel):
    id: int
    public_id: str
    name: str
    slug: str
    description: Optional[str]
    plan_type: str
    user_role: Optional[str]
    joined_at: Optional[str]
    created_at: str

class OrganizationMemberResponse(BaseModel):
    id: int
    public_id: str
    email: str
    username: str
    full_name: Optional[str]
    role: str
    joined_at: Optional[str]
    is_active: bool

class AssignRoleRequest(BaseModel):
    user_id: int
    role_name: str = Field(..., pattern=r'^(super_admin|org_owner|admin|manager|member|viewer)$')

class SystemRoleResponse(BaseModel):
    name: str
    description: Optional[str]
    permissions: List[str]

class SystemPermissionResponse(BaseModel):
    name: str
    description: Optional[str]
    resource: str
    action: str

class SystemInitResponse(BaseModel):
    roles_created: int
    permissions_created: int
    message: str

# Dependency to get multi-tenant service
def get_mt_service(db: Session = Depends(get_db)):
    return get_multi_tenant_service(db)

@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    request: CreateOrganizationRequest,
    current_user: AuthUser = Depends(get_current_user),
    mt_service = Depends(get_mt_service)
):
    """Create a new organization"""
    try:
        org_data = mt_service.create_organization(
            name=request.name,
            slug=request.slug,
            owner_id=int(current_user.user_id),
            description=request.description,
            plan_type=request.plan_type
        )
        
        return OrganizationResponse(
            id=org_data["id"],
            public_id=org_data["public_id"],
            name=org_data["name"],
            slug=org_data["slug"],
            description=request.description,
            plan_type=request.plan_type,
            user_role="org_owner",
            joined_at=org_data["created_at"],
            created_at=org_data["created_at"]
        )
        
    except MultiTenantError as e:
        logger.error(f"Organization creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/", response_model=List[OrganizationResponse])
async def list_user_organizations(
    current_user: AuthUser = Depends(get_current_user),
    mt_service = Depends(get_mt_service)
):
    """List all organizations the current user belongs to"""
    try:
        organizations = mt_service.get_user_organizations(int(current_user.user_id))
        
        return [
            OrganizationResponse(
                id=org["id"],
                public_id=org["public_id"],
                name=org["name"],
                slug=org["slug"],
                description=org["description"],
                plan_type=org["plan_type"],
                user_role=org["user_role"],
                joined_at=org["joined_at"],
                created_at=org["created_at"]
            )
            for org in organizations
        ]
        
    except Exception as e:
        logger.error(f"Failed to list user organizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organizations"
        )

@router.get("/{organization_id}/members", response_model=List[OrganizationMemberResponse])
async def list_organization_members(
    organization_id: int,
    current_user: AuthUser = Depends(get_current_user),
    mt_service = Depends(get_mt_service)
):
    """List all members of an organization"""
    try:
        # Check if user has permission to view members
        has_permission = mt_service.check_user_permission(
            int(current_user.user_id), organization_id, "users.read"
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view organization members"
            )
        
        members = mt_service.get_organization_members(organization_id)
        
        return [
            OrganizationMemberResponse(
                id=member["id"],
                public_id=member["public_id"],
                email=member["email"],
                username=member["username"],
                full_name=member["full_name"],
                role=member["role"],
                joined_at=member["joined_at"],
                is_active=member["is_active"]
            )
            for member in members
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list organization members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization members"
        )

@router.post("/{organization_id}/members/assign-role", status_code=status.HTTP_200_OK)
async def assign_user_role(
    organization_id: int,
    request: AssignRoleRequest,
    current_user: AuthUser = Depends(get_current_user),
    mt_service = Depends(get_mt_service)
):
    """Assign a role to a user in the organization"""
    try:
        # Check if user has permission to manage users
        has_permission = mt_service.check_user_permission(
            int(current_user.user_id), organization_id, "users.update"
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to assign roles"
            )
        
        success = mt_service.assign_user_role(
            user_id=request.user_id,
            organization_id=organization_id,
            role_name=request.role_name,
            assigned_by_id=int(current_user.user_id)
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to assign role"
            )
        
        return {"message": f"Role '{request.role_name}' assigned successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign role"
        )

@router.get("/{organization_id}/permissions/{permission}")
async def check_permission(
    organization_id: int,
    permission: str,
    current_user: AuthUser = Depends(get_current_user),
    mt_service = Depends(get_mt_service)
):
    """Check if current user has a specific permission in the organization"""
    try:
        has_permission = mt_service.check_user_permission(
            int(current_user.user_id), organization_id, permission
        )
        
        return {
            "user_id": int(current_user.user_id),
            "organization_id": organization_id,
            "permission": permission,
            "has_permission": has_permission
        }
        
    except Exception as e:
        logger.error(f"Permission check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check permission"
        )

# System management endpoints (admin only)
@router.get("/system/roles", response_model=List[SystemRoleResponse])
async def list_system_roles(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all system roles (admin only)"""
    try:
        # Check if user is superuser
        if not getattr(current_user, 'is_superuser', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view system roles"
            )
        
        from sqlalchemy import text
        
        query = text("""
            SELECT name, description, permissions
            FROM roles 
            WHERE is_system_role = true 
            ORDER BY name
        """)
        
        results = db.execute(query).fetchall()
        
        return [
            SystemRoleResponse(
                name=row[0],
                description=row[1],
                permissions=row[2] or []
            )
            for row in results
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list system roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system roles"
        )

@router.get("/system/permissions", response_model=List[SystemPermissionResponse])
async def list_system_permissions(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all system permissions (admin only)"""
    try:
        # Check if user is superuser
        if not getattr(current_user, 'is_superuser', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view system permissions"
            )
        
        from sqlalchemy import text
        
        query = text("""
            SELECT name, description, resource, action
            FROM permissions 
            ORDER BY resource, action
        """)
        
        results = db.execute(query).fetchall()
        
        return [
            SystemPermissionResponse(
                name=row[0],
                description=row[1],
                resource=row[2],
                action=row[3]
            )
            for row in results
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list system permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system permissions"
        )

@router.post("/system/initialize", response_model=SystemInitResponse)
async def initialize_system_data(
    current_user: AuthUser = Depends(get_current_user),
    mt_service = Depends(get_mt_service)
):
    """Initialize system roles and permissions (admin only)"""
    try:
        # Check if user is superuser
        if not getattr(current_user, 'is_superuser', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can initialize system data"
            )
        
        result = mt_service.initialize_system_data()
        
        return SystemInitResponse(
            roles_created=result["roles"],
            permissions_created=result["permissions"],
            message="System initialization completed successfully"
        )
        
    except HTTPException:
        raise
    except MultiTenantError as e:
        logger.error(f"System initialization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"System initialization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize system data"
        )