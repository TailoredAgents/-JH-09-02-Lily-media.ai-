"""
Social Media OAuth API Endpoints
Integration Specialist Component - API endpoints for social media authentication
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging

from backend.db.database import get_db
from backend.auth.dependencies import get_current_active_user
from backend.auth.social_oauth import oauth_manager
from backend.db.models import User, UserSetting
from backend.core.config import get_settings
from backend.services.plan_aware_social_service import get_plan_aware_social_service

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/social-auth",
    tags=["social-authentication"]
)

# Request/Response Models
class ConnectPlatformRequest(BaseModel):
    platform: str = Field(..., description="Social media platform to connect")
    redirect_uri: str = Field(..., description="OAuth callback URL")

class ConnectPlatformResponse(BaseModel):
    status: str
    auth_url: str
    platform: str
    state: str
    expires_in: int

class OAuthCallbackRequest(BaseModel):
    platform: str = Field(..., description="Social media platform")
    code: str = Field(..., description="OAuth authorization code")
    state: str = Field(..., description="OAuth state parameter")
    redirect_uri: str = Field(..., description="OAuth callback URL")

class ConnectedAccountResponse(BaseModel):
    platform: str
    username: str
    display_name: str
    profile_image: Optional[str]
    follower_count: int
    verified: bool
    connected_at: str
    status: str

class PlatformStatusResponse(BaseModel):
    platform: str
    connected: bool
    account_info: Optional[Dict[str, Any]]
    last_activity: Optional[str]
    connection_health: str

@router.post("/connect", response_model=ConnectPlatformResponse)
async def initiate_platform_connection(
    request: ConnectPlatformRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ConnectPlatformResponse:
    """
    Initiate OAuth connection to a social media platform
    SECURITY: Now includes plan-aware validation to prevent subscription bypass
    """
    try:
        # Validate platform
        supported_platforms = ["twitter", "instagram", "facebook", "tiktok"]
        if request.platform not in supported_platforms:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported platform. Must be one of: {', '.join(supported_platforms)}"
            )
        
        # SECURITY FIX: Add plan-aware validation to prevent bypass
        plan_service = get_plan_aware_social_service(db)
        enforcement_result = await plan_service.enforce_connection_limit(
            user_id=current_user.id,
            platform=request.platform
        )
        
        if not enforcement_result["allowed"]:
            # Log the bypass attempt for security monitoring
            logger.warning(
                f"Connection attempt blocked for user {current_user.id} on {request.platform}: "
                f"{enforcement_result['reason']} - {enforcement_result['message']}"
            )
            
            # Return plan enforcement error with upgrade suggestions
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "connection_not_allowed",
                    "reason": enforcement_result["reason"],
                    "message": enforcement_result["message"],
                    "current_plan": enforcement_result.get("plan"),
                    "suggested_plans": enforcement_result.get("suggested_plans", []),
                    "current_usage": enforcement_result.get("current_usage"),
                    "upgrade_required": True
                }
            )
        
        # Generate OAuth authorization URL
        auth_data = oauth_manager.build_authorization_url(
            platform=request.platform,
            user_id=current_user.id,
            redirect_uri=request.redirect_uri
        )
        
        logger.info(f"Initiated OAuth connection for {request.platform} (user: {current_user.id})")
        
        return ConnectPlatformResponse(
            status="success",
            auth_url=auth_data["auth_url"],
            platform=request.platform,
            state=auth_data["state"],
            expires_in=600  # State expires in 10 minutes
        )
        
    except Exception as e:
        logger.error(f"Error initiating platform connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate connection: {str(e)}")

@router.post("/callback")
async def handle_oauth_callback(
    request: OAuthCallbackRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Handle OAuth callback and complete platform connection
    """
    try:
        # Exchange authorization code for tokens
        token_data = await oauth_manager.exchange_code_for_tokens(
            platform=request.platform,
            authorization_code=request.code,
            redirect_uri=request.redirect_uri,
            state=request.state
        )
        
        # SECURITY FIX: Validate plan limits before completing connection
        plan_service = get_plan_aware_social_service(db)
        enforcement_result = await plan_service.enforce_connection_limit(
            user_id=token_data["user_id"],
            platform=request.platform
        )
        
        if not enforcement_result["allowed"]:
            # Log the callback bypass attempt
            logger.warning(
                f"OAuth callback blocked for user {token_data['user_id']} on {request.platform}: "
                f"{enforcement_result['reason']} - {enforcement_result['message']}"
            )
            
            # Return plan enforcement error
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "connection_not_allowed",
                    "reason": enforcement_result["reason"], 
                    "message": enforcement_result["message"],
                    "current_plan": enforcement_result.get("plan"),
                    "suggested_plans": enforcement_result.get("suggested_plans", []),
                    "upgrade_required": True
                }
            )
        
        # Get user profile from platform
        profile_data = await oauth_manager.get_user_profile(
            platform=request.platform,
            access_token=token_data["access_token"]
        )
        
        # Store tokens and profile data
        success = await oauth_manager.store_user_tokens(
            user_id=token_data["user_id"],
            platform=request.platform,
            token_data=token_data,
            profile_data=profile_data,
            db=db
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store connection data")
        
        logger.info(f"Successfully connected {request.platform} for user {token_data['user_id']}")
        
        return {
            "status": "success",
            "platform": request.platform,
            "account_info": {
                "username": profile_data.get("username"),
                "display_name": profile_data.get("display_name"),
                "profile_image": profile_data.get("profile_image"),
                "follower_count": profile_data.get("follower_count", 0),
                "verified": profile_data.get("verified", False)
            },
            "message": f"Successfully connected {request.platform} account"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")

@router.get("/callback/{platform}")
async def oauth_callback_redirect(
    platform: str,
    code: str = Query(..., description="OAuth authorization code"),
    state: str = Query(..., description="OAuth state parameter"),
    error: Optional[str] = Query(None, description="OAuth error"),
    error_description: Optional[str] = Query(None, description="OAuth error description"),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback redirect from social media platforms
    This endpoint is called directly by the OAuth provider
    """
    try:
        # Check for OAuth errors
        if error:
            logger.error(f"OAuth error for {platform}: {error} - {error_description}")
            raise HTTPException(
                status_code=400,
                detail=f"OAuth error: {error_description or error}"
            )
        
        # Build redirect URI (this should match the one used in authorization)
        redirect_uri = f"{settings.backend_url}/api/social-auth/callback/{platform}"
        
        # Process the callback
        callback_request = OAuthCallbackRequest(
            platform=platform,
            code=code,
            state=state,
            redirect_uri=redirect_uri
        )
        
        result = await handle_oauth_callback(callback_request, db)
        
        # Redirect to frontend success page
        success_url = f"{settings.frontend_url}/settings/social-accounts?status=connected&platform={platform}"
        return RedirectResponse(url=success_url)
        
    except HTTPException as e:
        # Redirect to frontend error page
        error_url = f"{settings.frontend_url}/settings/social-accounts?status=error&platform={platform}&error={e.detail}"
        return RedirectResponse(url=error_url)
    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {e}")
        error_url = f"{settings.frontend_url}/settings/social-accounts?status=error&platform={platform}&error=connection_failed"
        return RedirectResponse(url=error_url)

@router.get("/connected", response_model=List[ConnectedAccountResponse])
async def get_connected_accounts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[ConnectedAccountResponse]:
    """
    Get list of connected social media accounts
    """
    try:
        user_settings = db.query(UserSetting).filter(
            UserSetting.user_id == current_user.id
        ).first()
        
        connected_accounts = []
        
        if user_settings and user_settings.connected_accounts:
            for platform, account_data in user_settings.connected_accounts.items():
                # Determine connection status
                status = "active"
                if account_data.get("expires_at"):
                    from datetime import datetime
                    expires_at = datetime.fromisoformat(account_data["expires_at"])
                    if expires_at < datetime.utcnow():
                        status = "expired"
                
                connected_accounts.append(ConnectedAccountResponse(
                    platform=platform,
                    username=account_data.get("username", ""),
                    display_name=account_data.get("display_name", ""),
                    profile_image=account_data.get("profile_image"),
                    follower_count=account_data.get("follower_count", 0),
                    verified=account_data.get("verified", False),
                    connected_at=account_data.get("connected_at", ""),
                    status=status
                ))
        
        return connected_accounts
        
    except Exception as e:
        logger.error(f"Error getting connected accounts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve connected accounts")

@router.get("/status/{platform}", response_model=PlatformStatusResponse)
async def get_platform_status(
    platform: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> PlatformStatusResponse:
    """
    Get connection status for a specific platform
    """
    try:
        user_settings = db.query(UserSetting).filter(
            UserSetting.user_id == current_user.id
        ).first()
        
        connected = False
        account_info = None
        last_activity = None
        connection_health = "disconnected"
        
        if user_settings and user_settings.connected_accounts:
            account_data = user_settings.connected_accounts.get(platform)
            
            if account_data:
                connected = True
                connection_health = "healthy"
                
                # Check token expiration
                if account_data.get("expires_at"):
                    from datetime import datetime
                    expires_at = datetime.fromisoformat(account_data["expires_at"])
                    if expires_at < datetime.utcnow():
                        connection_health = "expired"
                
                account_info = {
                    "username": account_data.get("username"),
                    "display_name": account_data.get("display_name"),
                    "follower_count": account_data.get("follower_count", 0),
                    "verified": account_data.get("verified", False)
                }
                
                last_activity = account_data.get("last_refreshed") or account_data.get("connected_at")
        
        return PlatformStatusResponse(
            platform=platform,
            connected=connected,
            account_info=account_info,
            last_activity=last_activity,
            connection_health=connection_health
        )
        
    except Exception as e:
        logger.error(f"Error getting platform status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get platform status")

@router.post("/disconnect/{platform}")
async def disconnect_platform(
    platform: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Disconnect from a social media platform
    """
    try:
        success = oauth_manager.disconnect_platform(
            user_id=current_user.id,
            platform=platform,
            db=db
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Platform {platform} not connected")
        
        logger.info(f"Disconnected {platform} for user {current_user.id}")
        
        return {
            "status": "success",
            "platform": platform,
            "message": f"Successfully disconnected {platform} account"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting platform: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to disconnect {platform}")

@router.post("/refresh/{platform}")
async def refresh_platform_token(
    platform: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually refresh access token for a platform
    """
    try:
        # Get current valid token (this will automatically refresh if needed)
        token = await oauth_manager.get_valid_token(
            user_id=current_user.id,
            platform=platform,
            db=db
        )
        
        if not token:
            raise HTTPException(
                status_code=404,
                detail=f"No valid connection found for {platform}"
            )
        
        logger.info(f"Refreshed token for {platform} (user: {current_user.id})")
        
        return {
            "status": "success",
            "platform": platform,
            "message": f"Successfully refreshed {platform} token",
            "token_refreshed": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing platform token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh {platform} token")

@router.get("/test/{platform}")
async def test_platform_connection(
    platform: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Test connection to a social media platform
    """
    try:
        # Get valid token
        token = await oauth_manager.get_valid_token(
            user_id=current_user.id,
            platform=platform,
            db=db
        )
        
        if not token:
            raise HTTPException(
                status_code=404,
                detail=f"No connection found for {platform}"
            )
        
        # Test the connection by fetching user profile
        profile_data = await oauth_manager.get_user_profile(platform, token)
        
        return {
            "status": "success",
            "platform": platform,
            "connection_test": "passed",
            "account_info": {
                "username": profile_data.get("username"),
                "display_name": profile_data.get("display_name"),
                "follower_count": profile_data.get("follower_count", 0)
            },
            "message": f"Connection to {platform} is working correctly"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing platform connection: {e}")
        raise HTTPException(status_code=500, detail=f"Connection test failed for {platform}")

@router.get("/platforms")
async def get_supported_platforms() -> Dict[str, Any]:
    """
    Get list of supported social media platforms and their capabilities
    """
    platforms = {
        "twitter": {
            "name": "Twitter",
            "capabilities": ["post", "thread", "analytics", "engagement"],
            "content_types": ["text", "image", "video"],
            "max_characters": 280,
            "supports_scheduling": True,
            "oauth_version": "2.0"
        },
        "instagram": {
            "name": "Instagram",
            "capabilities": ["post", "story", "analytics", "engagement"],
            "content_types": ["image", "video", "carousel"],
            "max_characters": 2200,
            "supports_scheduling": True,
            "oauth_version": "2.0"
        },
        "facebook": {
            "name": "Facebook",
            "capabilities": ["post", "page_management", "analytics", "engagement"],
            "content_types": ["text", "image", "video", "link"],
            "max_characters": 63206,
            "supports_scheduling": True,
            "oauth_version": "2.0"
        },
        "tiktok": {
            "name": "TikTok",
            "capabilities": ["video_upload", "analytics"],
            "content_types": ["video"],
            "max_characters": 150,
            "supports_scheduling": False,
            "oauth_version": "2.0"
        }
    }
    
    return {
        "status": "success",
        "supported_platforms": platforms,
        "total_platforms": len(platforms)
    }