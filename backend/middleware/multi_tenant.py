"""
Multi-tenant middleware for request context isolation
Provides organization context and permission checking for requests
"""
import logging
from typing import Optional, Dict, Any
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.services.multi_tenant_service import get_multi_tenant_service
from backend.auth.jwt_handler import decode_jwt_token

logger = logging.getLogger(__name__)

class MultiTenantContext:
    """Thread-local context for multi-tenant information"""
    
    def __init__(self):
        self.user_id: Optional[int] = None
        self.organization_id: Optional[int] = None
        self.user_role: Optional[str] = None
        self.permissions: set = set()
        self.is_superuser: bool = False
        
    def clear(self):
        """Clear all context data"""
        self.user_id = None
        self.organization_id = None
        self.user_role = None
        self.permissions.clear()
        self.is_superuser = False
        
    def has_permission(self, permission: str) -> bool:
        """Check if current user has specific permission"""
        if self.is_superuser:
            return True
            
        # Check exact permission
        if permission in self.permissions:
            return True
            
        # Check wildcard permissions
        resource = permission.split('.')[0] if '.' in permission else permission
        resource_wildcard = f"{resource}.*"
        
        return resource_wildcard in self.permissions or '*' in self.permissions

# Global context instance
tenant_context = MultiTenantContext()

class MultiTenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle multi-tenant request context
    
    Features:
    - Extracts organization context from requests
    - Sets up permission context for authenticated users
    - Provides request isolation for multi-tenant operations
    """
    
    def __init__(self, app, exclude_paths: set = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or {
            "/docs", "/redoc", "/openapi.json", "/health", "/metrics",
            "/api/auth/login", "/api/auth/register", "/api/auth/refresh"
        }
        
    async def dispatch(self, request: Request, call_next):
        """Process request with multi-tenant context"""
        
        # Skip middleware for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Clear previous context
        tenant_context.clear()
        
        try:
            # Extract user and organization context
            await self._setup_tenant_context(request)
            
            # Process request with context
            response = await call_next(request)
            
            # Add tenant headers to response
            if tenant_context.organization_id:
                response.headers["X-Organization-ID"] = str(tenant_context.organization_id)
            
            return response
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except Exception as e:
            logger.error(f"Multi-tenant middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
        finally:
            # Clean up context after request
            tenant_context.clear()
    
    async def _setup_tenant_context(self, request: Request):
        """Setup multi-tenant context for the request"""
        
        # Extract JWT token
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return  # No authentication - context remains empty
        
        token = authorization[7:]  # Remove "Bearer " prefix
        
        try:
            # Decode JWT to get user information
            payload = decode_jwt_token(token)
            if not payload:
                return
                
            user_id = payload.get("user_id")
            if not user_id:
                return
            
            tenant_context.user_id = user_id
            tenant_context.is_superuser = payload.get("is_superuser", False)
            
            # Get organization context
            org_id = self._extract_organization_id(request)
            if org_id:
                await self._setup_organization_context(user_id, org_id)
            
        except Exception as e:
            logger.debug(f"Failed to setup tenant context: {e}")
            # Continue without tenant context - some endpoints don't require it
    
    def _extract_organization_id(self, request: Request) -> Optional[int]:
        """Extract organization ID from request"""
        
        # Try URL path parameters first (e.g., /api/organizations/{org_id}/...)
        path_parts = request.url.path.split('/')
        if len(path_parts) > 3 and path_parts[2] == "organizations":
            try:
                return int(path_parts[3])
            except (ValueError, IndexError):
                pass
        
        # Try query parameters
        org_id = request.query_params.get("organization_id")
        if org_id:
            try:
                return int(org_id)
            except ValueError:
                pass
        
        # Try headers
        org_id = request.headers.get("X-Organization-ID")
        if org_id:
            try:
                return int(org_id)
            except ValueError:
                pass
        
        return None
    
    async def _setup_organization_context(self, user_id: int, org_id: int):
        """Setup organization-specific context"""
        
        try:
            # Get database session
            db = next(get_db())
            mt_service = get_multi_tenant_service(db)
            
            # Get user's role and permissions in the organization
            from sqlalchemy import text
            
            query = text("""
                SELECT r.name, r.permissions
                FROM user_organization_roles uro
                JOIN roles r ON uro.role_id = r.id
                WHERE uro.user_id = :user_id 
                AND uro.organization_id = :org_id
                AND uro.is_active = true
            """)
            
            result = db.execute(query, {
                "user_id": user_id,
                "org_id": org_id
            }).first()
            
            if result:
                tenant_context.organization_id = org_id
                tenant_context.user_role = result[0]
                tenant_context.permissions = set(result[1] or [])
            
            db.close()
            
        except Exception as e:
            logger.error(f"Failed to setup organization context: {e}")

def require_permission(permission: str):
    """
    Decorator to require specific permission for endpoint
    
    Usage:
        @require_permission("content.create")
        async def create_content(...):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not tenant_context.has_permission(permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission '{permission}' required"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_organization():
    """
    Decorator to require organization context for endpoint
    
    Usage:
        @require_organization()
        async def get_org_data(...):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not tenant_context.organization_id:
                raise HTTPException(
                    status_code=400,
                    detail="Organization context required"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Utility functions for accessing context
def get_current_organization_id() -> Optional[int]:
    """Get current organization ID from context"""
    return tenant_context.organization_id

def get_current_user_role() -> Optional[str]:
    """Get current user's role in organization"""
    return tenant_context.user_role

def has_permission(permission: str) -> bool:
    """Check if current user has permission"""
    return tenant_context.has_permission(permission)

def is_superuser() -> bool:
    """Check if current user is superuser"""
    return tenant_context.is_superuser