"""
Authentication Management API Endpoints
Provides token management, user session control, and auth system monitoring
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
import logging

from backend.auth.middleware import jwt_middleware, validate_jwt_token
from backend.auth.dependencies import get_current_active_user, get_admin_user
from backend.db.models import User
from backend.core.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["authentication-management"])
logger = logging.getLogger(__name__)
settings = get_settings()

# Pydantic models
class TokenValidationResponse(BaseModel):
    is_valid: bool
    user_id: str
    auth_method: str
    expires_at: float
    claims: Dict[str, Any]

class BlacklistTokenRequest(BaseModel):
    token: str
    reason: str = "User requested logout"

class UserSessionInfo(BaseModel):
    user_id: str
    email: str
    auth_method: str
    active_sessions: int
    last_activity: datetime
    permissions: List[str]

class MiddlewareStatsResponse(BaseModel):
    cached_tokens: int
    blacklisted_tokens: int
    active_users: int
    total_cache_size: int
    uptime_seconds: float

@router.post("/validate-token", response_model=TokenValidationResponse)
async def validate_token_endpoint(request: Request):
    """
    Validate JWT token and return detailed information
    Useful for frontend token validation and user session management
    """
    try:
        # Use the middleware's validation logic
        payload = await validate_jwt_token(request)
        
        return TokenValidationResponse(
            is_valid=True,
            user_id=payload.get("sub"),
            auth_method="auth0" if "@" in payload.get("sub", "") else "local",
            expires_at=payload.get("exp", 0),
            claims=payload
        )
        
    except HTTPException as e:
        logger.warning(f"Token validation failed: {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {e.detail}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token validation service error"
        )

@router.post("/blacklist-token")
async def blacklist_token(
    request: BlacklistTokenRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Blacklist a JWT token (logout functionality)
    Adds token to blacklist to prevent further use
    """
    try:
        # Add token to middleware blacklist
        jwt_middleware.blacklist_token(request.token)
        
        logger.info(f"Token blacklisted for user {current_user.id}: {request.reason}")
        
        return {
            "message": "Token successfully blacklisted",
            "user_id": current_user.id,
            "reason": request.reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to blacklist token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to blacklist token"
        )

@router.post("/logout")
async def logout_user(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout user by blacklisting their current token
    """
    try:
        # Extract token from request
        token = jwt_middleware._extract_token_from_request(request)
        
        if token:
            # Blacklist the token
            jwt_middleware.blacklist_token(token)
            
            # Clear user's cached tokens
            jwt_middleware.clear_user_cache(str(current_user.id))
            
            logger.info(f"User {current_user.id} logged out successfully")
            
            return {
                "message": "Successfully logged out",
                "user_id": current_user.id,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No token found in request"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/session-info", response_model=UserSessionInfo)
async def get_session_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user session information
    """
    try:
        # Get user permissions based on tier
        permissions = []
        if current_user.tier == "pro":
            permissions = ["read", "write", "analytics", "export"]
        elif current_user.tier == "enterprise":
            permissions = ["read", "write", "analytics", "export", "admin", "bulk_operations"]
        else:  # base tier
            permissions = ["read", "write"]
        
        return UserSessionInfo(
            user_id=str(current_user.id),
            email=current_user.email,
            auth_method="local",  # Local JWT authentication
            active_sessions=1,  # This could be enhanced to track multiple sessions
            last_activity=datetime.utcnow(),
            permissions=permissions
        )
        
    except Exception as e:
        logger.error(f"Failed to get session info for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session information"
        )

@router.get("/middleware-stats", response_model=MiddlewareStatsResponse)
async def get_middleware_stats(
    admin_user: User = Depends(get_admin_user)
):
    """
    Get JWT middleware performance statistics (Admin only)
    """
    try:
        stats = jwt_middleware.get_middleware_stats()
        
        return MiddlewareStatsResponse(
            cached_tokens=stats["cached_tokens"],
            blacklisted_tokens=stats["blacklisted_tokens"],
            active_users=stats["active_users"],
            total_cache_size=stats["total_cache_size"],
            uptime_seconds=0.0  # Could be enhanced to track actual uptime
        )
        
    except Exception as e:
        logger.error(f"Failed to get middleware stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve middleware statistics"
        )

@router.post("/clear-user-cache")
async def clear_user_cache(
    user_email: str,
    admin_user: User = Depends(get_admin_user)
):
    """
    Clear cached tokens for a specific user (Admin only)
    Useful for forcing re-authentication
    """
    try:
        # This is a simplified approach - in production you'd want better user identification
        jwt_middleware.clear_user_cache(user_email)
        
        logger.info(f"Admin {admin_user.id} cleared cache for user: {user_email}")
        
        return {
            "message": f"Cache cleared for user: {user_email}",
            "admin_user": admin_user.email,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to clear user cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear user cache"
        )

@router.get("/health")
async def auth_health_check():
    """
    Detailed authentication system health check
    """
    from backend.auth.middleware import get_jwt_cache_status
    
    try:
        # Check local JWT configuration
        local_jwt_healthy = bool(settings.secret_key and settings.secret_key != "your-secret-key-change-this")
        
        # Get JWT cache status
        jwt_cache_status = get_jwt_cache_status()
        
        # Get middleware stats  
        middleware_stats = await jwt_middleware.get_middleware_stats()
        
        overall_status = "healthy" if local_jwt_healthy else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "local_jwt": {
                    "configured": local_jwt_healthy,
                    "status": "healthy" if local_jwt_healthy else "misconfigured"
                },
                "jwt_cache": jwt_cache_status,
                "middleware": {
                    "status": "healthy",
                    "stats": middleware_stats
                }
            },
            "recommendations": [
                "Set strong secret key for local JWT" if not local_jwt_healthy else "",
                "Redis connection required for distributed caching" if not middleware_stats.get("redis_connected", False) else ""
            ]
        }
        
    except Exception as e:
        logger.error(f"Auth health check failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@router.get("/config")
async def get_auth_config(
    admin_user: User = Depends(get_admin_user)
):
    """
    Get authentication configuration (Admin only, sensitive data masked)
    """
    try:
        return {
            "auth0": {
                "domain": settings.auth0_domain,
                "audience": settings.auth0_audience,
                "client_id": settings.auth0_client_id,
                "client_secret": "***masked***" if settings.auth0_client_secret else None
            },
            "local_jwt": {
                "algorithm": settings.algorithm,
                "access_token_expire_minutes": settings.access_token_expire_minutes,
                "secret_key": "***masked***" if settings.secret_key else None
            },
            "environment": settings.environment,
            "debug": settings.debug
        }
        
    except Exception as e:
        logger.error(f"Failed to get auth config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve auth configuration"
        )