"""
Social Platform Management API
Handles OAuth connections, posting, and metrics for social media platforms
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User, SocialPlatformConnection, SocialPost
from backend.auth.dependencies import get_current_active_user
from backend.core.token_encryption import get_token_manager
from backend.core.audit_logger import log_content_event, AuditEventType
from backend.integrations.twitter_client import twitter_client, TwitterAPIError
from backend.integrations.instagram_client import instagram_client, InstagramAPIError
from backend.services.notification_service import (
    trigger_post_published_notification,
    trigger_post_failed_notification,
    trigger_platform_connected_notification,
    trigger_oauth_expired_notification
)
from backend.core.pagination import (
    PaginationService, 
    get_pagination_params, 
    get_cursor_pagination_params,
    PaginationParams,
    CursorPaginationParams,
    PaginatedResponse,
    CursorPaginatedResponse
)
from backend.core.performance import performance_monitor, cached

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/social", tags=["social-platforms"])

# Pydantic models for API requests/responses

class SocialPlatformConnectionResponse(BaseModel):
    id: int
    platform: str
    platform_user_id: str
    platform_username: str
    platform_display_name: Optional[str]
    profile_image_url: Optional[str]
    is_active: bool
    connection_status: str
    connected_at: datetime
    last_used_at: Optional[datetime]
    platform_metadata: Dict[str, Any] = {}
    
    model_config = ConfigDict(from_attributes=True)

class PostContentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=3000)
    platforms: List[str] = Field(..., min_length=1)
    media_urls: Optional[List[str]] = None
    schedule_for: Optional[datetime] = None

class PostResponse(BaseModel):
    success: bool
    posts: List[Dict[str, Any]]
    errors: List[Dict[str, str]] = []

class ConnectionMetricsResponse(BaseModel):
    platform: str
    followers_count: int
    following_count: int
    posts_count: int
    engagement_rate: float
    last_updated: datetime

# OAuth connection endpoints

@router.get("/connect/{platform}")
async def initiate_oauth_connection(
    platform: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Initiate OAuth connection for a social platform
    
    Args:
        platform: Social platform name (twitter, linkedin, instagram)
        current_user: Authenticated user
        db: Database session
        
    Returns:
        OAuth authorization URL for user to complete connection
    """
    if platform not in ["twitter", "instagram"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}"
        )
    
    try:
        # Generate OAuth authorization URL based on platform
        # Use configured backend URL instead of hardcoded localhost
        from backend.core.config import get_settings
        settings = get_settings()
        base_url = settings.backend_url or "http://localhost:8000"  # Fallback for development
        redirect_uri = f"{base_url}/api/social/callback/{platform}"
        state = f"{current_user.id}:{platform}"
        
        if platform == "twitter":
            auth_url, oauth_state = twitter_client.get_oauth_authorization_url(redirect_uri, state)
        elif platform == "instagram":
            auth_url, oauth_state = instagram_client.get_oauth_authorization_url(redirect_uri, state)
        
        # Log OAuth initiation
        log_content_event(
            AuditEventType.AUTHENTICATION_SUCCESS,
            user_id=current_user.id,
            resource=f"{platform}_oauth_init",
            action="initiate_connection",
            additional_data={"platform": platform}
        )
        
        return {
            "authorization_url": auth_url,
            "state": oauth_state,
            "platform": platform
        }
        
    except Exception as e:
        logger.error(f"Failed to initiate {platform} OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate {platform} connection"
        )

@router.get("/callback/{platform}")
async def oauth_callback(
    platform: str,
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from social platform
    
    Args:
        platform: Social platform name
        code: Authorization code from OAuth provider
        state: State parameter for security
        db: Database session
        
    Returns:
        Success response or error
    """
    try:
        # Parse state to get user ID
        user_id_str, platform_from_state = state.split(":")
        user_id = int(user_id_str)
        
        if platform != platform_from_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter"
            )
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Exchange code for tokens based on platform
        redirect_uri = f"http://localhost:8000/api/social/callback/{platform}"
        
        if platform == "twitter":
            # Note: Twitter OAuth 2.0 with PKCE requires code_verifier
            # In production, this should be stored in session/cache
            code_verifier = "dummy_verifier"  # Should be retrieved from session
            token_data = twitter_client.exchange_code_for_tokens(code, redirect_uri, code_verifier)
            
            # Get user info to store connection details
            user_info = twitter_client.get_user_info(token_data["access_token"])
            
        elif platform == "instagram":
            token_data = instagram_client.exchange_code_for_tokens(code, redirect_uri)
            user_info = instagram_client.get_user_info(token_data["access_token"])
        
        # Encrypt and store tokens
        token_manager = get_token_manager()
        encrypted_token_data = token_manager.store_oauth_tokens(platform, token_data)
        
        # Check if connection already exists
        existing_connection = db.query(SocialPlatformConnection).filter(
            SocialPlatformConnection.user_id == user_id,
            SocialPlatformConnection.platform == platform
        ).first()
        
        if existing_connection:
            # Update existing connection
            existing_connection.access_token = encrypted_token_data
            existing_connection.platform_user_id = user_info.get("id", user_info.get("user_id", ""))
            existing_connection.platform_username = user_info.get("username", user_info.get("display_name", ""))
            existing_connection.platform_display_name = user_info.get("name", user_info.get("display_name", ""))
            existing_connection.profile_image_url = user_info.get("profile_image_url", user_info.get("profile_picture", ""))
            existing_connection.is_active = True
            existing_connection.connection_status = "connected"
            existing_connection.last_refreshed_at = datetime.utcnow()
            existing_connection.platform_metadata = user_info
            
        else:
            # Create new connection
            new_connection = SocialPlatformConnection(
                user_id=user_id,
                platform=platform,
                platform_user_id=user_info.get("id", user_info.get("user_id", "")),
                platform_username=user_info.get("username", user_info.get("display_name", "")),
                platform_display_name=user_info.get("name", user_info.get("display_name", "")),
                profile_image_url=user_info.get("profile_image_url", user_info.get("profile_picture", "")),
                access_token=encrypted_token_data,
                token_type="Bearer",
                is_active=True,
                connection_status="connected",
                platform_metadata=user_info
            )
            db.add(new_connection)
        
        db.commit()
        
        # Log successful connection
        log_content_event(
            AuditEventType.AUTHENTICATION_SUCCESS,
            user_id=user_id,
            resource=f"{platform}_connection",
            action="complete_oauth",
            additional_data={
                "platform": platform,
                "platform_user_id": user_info.get("id", ""),
                "platform_username": user_info.get("username", "")
            }
        )
        
        logger.info(f"Successfully connected {platform} account for user {user_id}")
        
        # Trigger platform connected notification
        try:
            username = user_info.get("username", user_info.get("display_name", ""))
            await trigger_platform_connected_notification(user_id, platform, username)
        except Exception as e:
            logger.warning(f"Failed to send platform connected notification: {e}")
        
        # Redirect to frontend with success message
        return RedirectResponse(
            url=f"http://localhost:3000/dashboard/connections?success=true&platform={platform}",
            status_code=status.HTTP_302_FOUND
        )
        
    except Exception as e:
        logger.error(f"OAuth callback failed for {platform}: {e}")
        
        # Log failed connection
        if 'user_id' in locals():
            log_content_event(
                AuditEventType.AUTHENTICATION_FAILURE,
                user_id=user_id,
                resource=f"{platform}_connection",
                action="oauth_callback_failed",
                additional_data={"error": str(e), "platform": platform}
            )
        
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"http://localhost:3000/dashboard/connections?error=true&platform={platform}",
            status_code=status.HTTP_302_FOUND
        )

# Connection management endpoints

@router.get("/connections")
@performance_monitor("get_user_connections")
@cached("user_connections_{args[0].id}", ttl=300)
async def get_user_connections(
    current_user: User = Depends(get_current_active_user),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db)
) -> PaginatedResponse[SocialPlatformConnection]:
    """
    Get paginated social platform connections for the current user
    
    Args:
        current_user: Authenticated user
        pagination: Pagination parameters
        db: Database session
        
    Returns:
        Paginated list of user's social platform connections
    """
    try:
        # Build base query
        base_query = db.query(SocialPlatformConnection).filter(
            SocialPlatformConnection.user_id == current_user.id,
            SocialPlatformConnection.is_active == True
        )
        
        # Apply default sorting by connected_at desc if no sort specified
        if not pagination.sort_by:
            base_query = base_query.order_by(SocialPlatformConnection.connected_at.desc())
        
        # Use pagination service
        pagination_service = PaginationService(db)
        result = pagination_service.paginate_query(base_query, pagination)
        
        logger.info(f"Found {result.pagination['total_items']} social connections for user {current_user.id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving social connections for user {current_user.id}: {e}")
        logger.error(f"Error type: {type(e)}")
        
        # Return empty paginated result on error
        return PaginatedResponse(
            items=[],
            pagination={
                "current_page": pagination.page,
                "page_size": pagination.page_size,
                "total_items": 0,
                "total_pages": 0,
                "has_next": False,
                "has_previous": False,
                "next_page": None,
                "previous_page": None
            }
        )

@router.get("/connections/status")
async def get_connection_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get social platform connection status for the current user
    Returns summary info about connected platforms
    """
    connections = db.query(SocialPlatformConnection).filter(
        SocialPlatformConnection.user_id == current_user.id,
        SocialPlatformConnection.is_active == True
    ).all()
    
    connected_platforms = [conn.platform for conn in connections]
    
    return {
        "has_connections": len(connections) > 0,
        "connection_count": len(connections),
        "connected_platforms": connected_platforms,
        "available_platforms": ["twitter", "instagram", "facebook", "linkedin", "tiktok"],
        "needs_setup": len(connections) == 0
    }

@router.delete("/connections/{connection_id}")
async def disconnect_platform(
    connection_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect a social platform connection
    
    Args:
        connection_id: Connection ID to disconnect
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Success response
    """
    connection = db.query(SocialPlatformConnection).filter(
        SocialPlatformConnection.id == connection_id,
        SocialPlatformConnection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Deactivate connection instead of deleting to preserve audit trail
    connection.is_active = False
    connection.connection_status = "disconnected"
    db.commit()
    
    # Log disconnection
    log_content_event(
        AuditEventType.AUTHENTICATION_SUCCESS,
        user_id=current_user.id,
        resource=f"{connection.platform}_connection",
        action="disconnect",
        additional_data={
            "connection_id": connection_id,
            "platform": connection.platform
        }
    )
    
    return {"success": True, "message": f"{connection.platform} connection disconnected"}

@router.post("/validate/{platform}")
async def validate_platform_connection(
    platform: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Validate a social platform connection by making a test API call
    
    Args:
        platform: Platform to validate
        current_user: Authenticated user  
        db: Database session
        
    Returns:
        Connection validation results
    """
    connection = db.query(SocialPlatformConnection).filter(
        SocialPlatformConnection.user_id == current_user.id,
        SocialPlatformConnection.platform == platform,
        SocialPlatformConnection.is_active == True
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active {platform} connection found"
        )
    
    try:
        # Decrypt tokens
        token_manager = get_token_manager()
        access_token = token_manager.get_access_token(connection.access_token)
        
        if not access_token:
            # Trigger OAuth expired notification
            try:
                await trigger_oauth_expired_notification(current_user.id, platform)
            except Exception as e:
                logger.warning(f"Failed to trigger OAuth expired notification: {e}")
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token"
            )
        
        # Validate connection based on platform
        if platform == "twitter":
            validation_result = twitter_client.validate_connection(access_token)
        elif platform == "instagram":
            validation_result = instagram_client.validate_connection(access_token)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform: {platform}"
            )
        
        # Update connection status
        if validation_result["is_valid"]:
            connection.connection_status = "connected"
            connection.last_used_at = datetime.utcnow()
            connection.error_count = 0
            connection.last_error = None
        else:
            connection.connection_status = "error"
            connection.error_count = (connection.error_count or 0) + 1
            connection.last_error = validation_result.get("error", "Validation failed")
            connection.last_error_at = datetime.utcnow()
        
        db.commit()
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Failed to validate {platform} connection: {e}")
        
        # Update connection with error
        connection.connection_status = "error"
        connection.error_count = (connection.error_count or 0) + 1
        connection.last_error = str(e)
        connection.last_error_at = datetime.utcnow()
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate {platform} connection: {str(e)}"
        )

# Content posting endpoints

@router.post("/post", response_model=PostResponse)
async def post_to_platforms(
    post_request: PostContentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Post content to specified social media platforms
    
    Args:
        post_request: Post content and platform details
        background_tasks: Background task handler
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Post results for each platform
    """
    results = []
    errors = []
    
    for platform in post_request.platforms:
        try:
            # Get platform connection
            connection = db.query(SocialPlatformConnection).filter(
                SocialPlatformConnection.user_id == current_user.id,
                SocialPlatformConnection.platform == platform,
                SocialPlatformConnection.is_active == True
            ).first()
            
            if not connection:
                errors.append({
                    "platform": platform,
                    "error": f"No active {platform} connection found"
                })
                continue
            
            # Get access token
            token_manager = get_token_manager()
            access_token = token_manager.get_access_token(connection.access_token)
            
            if not access_token:
                errors.append({
                    "platform": platform,
                    "error": f"Invalid or expired {platform} access token"
                })
                continue
            
            # Post to platform
            if platform == "twitter":
                post_result = twitter_client.post_tweet(
                    access_token, 
                    post_request.content, 
                    current_user.id,
                    post_request.media_urls
                )
            elif platform == "instagram":
                if not post_request.media_urls or len(post_request.media_urls) == 0:
                    errors.append({
                        "platform": platform,
                        "error": "Instagram requires at least one image URL"
                    })
                    continue
                    
                post_result = instagram_client.post_image(
                    access_token,
                    post_request.media_urls[0],
                    post_request.content,
                    current_user.id
                )
            
            # Create database record
            social_post = SocialPost(
                user_id=current_user.id,
                connection_id=connection.id,
                platform=platform,
                platform_post_id=post_result["id"],
                content_text=post_request.content,
                media_urls=post_request.media_urls or [],
                status="posted",
                posted_at=datetime.utcnow()
            )
            db.add(social_post)
            
            # Update connection last used
            connection.last_used_at = datetime.utcnow()
            
            results.append({
                "platform": platform,
                "post_id": post_result["id"],
                "success": True,
                "posted_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Successfully posted to {platform} for user {current_user.id}")
            
            # Trigger post published notification
            try:
                background_tasks.add_task(
                    trigger_post_published_notification,
                    current_user.id,
                    platform,
                    post_result["id"],
                    post_request.content
                )
            except Exception as e:
                logger.warning(f"Failed to trigger post published notification: {e}")
            
        except (TwitterAPIError, LinkedInAPIError, InstagramAPIError) as e:
            logger.error(f"Failed to post to {platform}: {e}")
            error_msg = str(e)
            errors.append({
                "platform": platform,
                "error": error_msg
            })
            
            # Trigger post failed notification
            try:
                background_tasks.add_task(
                    trigger_post_failed_notification,
                    current_user.id,
                    platform,
                    post_request.content,
                    error_msg
                )
            except Exception as notification_error:
                logger.warning(f"Failed to trigger post failed notification: {notification_error}")
                
        except Exception as e:
            logger.error(f"Unexpected error posting to {platform}: {e}")
            error_msg = f"Unexpected error: {str(e)}"
            errors.append({
                "platform": platform,
                "error": error_msg
            })
            
            # Trigger post failed notification for unexpected errors
            try:
                background_tasks.add_task(
                    trigger_post_failed_notification,
                    current_user.id,
                    platform,
                    post_request.content,
                    error_msg
                )
            except Exception as notification_error:
                logger.warning(f"Failed to trigger post failed notification: {notification_error}")
    
    db.commit()
    
    return PostResponse(
        success=len(results) > 0,
        posts=results,
        errors=errors
    )

@router.get("/posts")
async def get_user_posts(
    platform: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get user's social media posts
    
    Args:
        platform: Optional platform filter
        limit: Maximum number of posts to return
        offset: Number of posts to skip
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of user's posts
    """
    query = db.query(SocialPost).filter(
        SocialPost.user_id == current_user.id
    )
    
    if platform:
        query = query.filter(SocialPost.platform == platform)
    
    posts = query.order_by(
        SocialPost.posted_at.desc()
    ).offset(offset).limit(limit).all()
    
    return posts

# Metrics endpoints

@router.get("/metrics/{platform}")
async def get_platform_metrics(
    platform: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get metrics for a specific platform connection
    
    Args:
        platform: Platform to get metrics for
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Platform metrics and engagement data
    """
    connection = db.query(SocialPlatformConnection).filter(
        SocialPlatformConnection.user_id == current_user.id,
        SocialPlatformConnection.platform == platform,
        SocialPlatformConnection.is_active == True
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active {platform} connection found"
        )
    
    # Get platform metadata for basic metrics
    platform_metadata = connection.platform_metadata or {}
    
    return ConnectionMetricsResponse(
        platform=platform,
        followers_count=platform_metadata.get("followers_count", 0),
        following_count=platform_metadata.get("following_count", 0),
        posts_count=platform_metadata.get("media_count", 0),
        engagement_rate=0.0,  # Calculate from posts
        last_updated=connection.updated_at or connection.connected_at
    )

@router.get("/analytics/overview")
async def get_analytics_overview(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get analytics overview across all connected platforms
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Analytics overview data
    """
    # Get all active connections
    connections = db.query(SocialPlatformConnection).filter(
        SocialPlatformConnection.user_id == current_user.id,
        SocialPlatformConnection.is_active == True
    ).all()
    
    # Get recent posts
    recent_posts = db.query(SocialPost).filter(
        SocialPost.user_id == current_user.id,
        SocialPost.status == "posted"
    ).order_by(SocialPost.posted_at.desc()).limit(10).all()
    
    platform_data = []
    for connection in connections:
        metadata = connection.platform_metadata or {}
        platform_data.append({
            "platform": connection.platform,
            "username": connection.platform_username,
            "followers": metadata.get("followers_count", 0),
            "connected_at": connection.connected_at.isoformat(),
            "status": connection.connection_status
        })
    
    return {
        "connected_platforms": len(connections),
        "total_posts": len(recent_posts),
        "platforms": platform_data,
        "recent_posts": [
            {
                "id": post.id,
                "platform": post.platform,
                "content": post.content_text[:100] + "..." if len(post.content_text) > 100 else post.content_text,
                "posted_at": post.posted_at.isoformat(),
                "status": post.status
            }
            for post in recent_posts
        ]
    }