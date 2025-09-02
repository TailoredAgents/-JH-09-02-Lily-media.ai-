"""
Partner OAuth API endpoints for tenant-scoped social media connections
Gated by FEATURE_PARTNER_OAUTH flag
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
import logging
import urllib.parse
import httpx

from backend.core.config import get_settings
from backend.auth.dependencies import get_current_active_user
from backend.db.models import User, SocialConnection, SocialAudit
from backend.db.database import get_db
from backend.services.pkce_state_store import get_state_store
from backend.services.meta_page_token_service import get_meta_page_service
from backend.services.x_connection_service import get_x_connection_service

# Import Meta webhook service for subscription management
try:
    from backend.services.meta_webhook_service import get_meta_webhook_service
except ImportError:
    get_meta_webhook_service = None
from backend.core.encryption import encrypt_token
from backend.auth.social_oauth import SocialOAuthManager
from backend.integrations.connection_health import compute_connection_health
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Feature flag check
def is_partner_oauth_enabled():
    """Check if partner OAuth feature is enabled"""
    settings = get_settings()
    return getattr(settings, 'feature_partner_oauth', False)

def require_partner_oauth_enabled():
    """Dependency to ensure feature is enabled"""
    if not is_partner_oauth_enabled():
        raise HTTPException(
            status_code=404,
            detail={
                "error": "feature_disabled",
                "message": "Partner OAuth feature is not enabled",
                "feature_flag": "FEATURE_PARTNER_OAUTH"
            }
        )

# Router setup
router = APIRouter(
    prefix="/api/oauth",
    tags=["partner-oauth"],
    dependencies=[Depends(require_partner_oauth_enabled)]
)

# Request/Response Models
class OAuthStartResponse(BaseModel):
    auth_url: str
    state: str
    platform: str
    expires_in: int = 600  # 10 minutes

class OAuthCallbackResponse(BaseModel):
    status: str
    platform: str
    state: str
    next_step: str  # "asset_selection" | "connection_confirm"
    expires_in: int = 600

class DisabledFeatureResponse(BaseModel):
    error: str = "feature_disabled"
    message: str = "Partner OAuth feature is not enabled"
    feature_flag: str = "FEATURE_PARTNER_OAUTH"

# Phase 3 Models
class FacebookPage(BaseModel):
    id: str
    name: str
    has_instagram: bool
    token_available: bool
    instagram_business_account: Optional[Dict[str, Any]] = None

class MetaAssetsResponse(BaseModel):
    pages: List[FacebookPage]

class MetaConnectRequest(BaseModel):
    state: str
    page_id: str
    instagram_id: Optional[str] = None

class MetaConnectResponse(BaseModel):
    connection_id: str
    facebook_page: Dict[str, str]  # {id, name}
    instagram_account: Optional[Dict[str, str]] = None  # {id, username}

class XConnectRequest(BaseModel):
    state: str

class XConnectResponse(BaseModel):
    connection_id: str
    username: str
    user_id: str

# Phase 4 Models
class ConnectionListItem(BaseModel):
    id: str
    platform: str
    platform_account_id: str
    platform_username: str
    connection_name: str
    scopes: List[str]
    webhook_subscribed: bool
    expires_at: Optional[str] = None  # ISO string or null
    expires_in_hours: Optional[int] = None  # null if no expiry
    last_checked_at: Optional[str] = None  # ISO string or null
    needs_reconnect: bool = False  # true if expires within 72 hours
    created_at: str  # ISO string

class ConnectionListResponse(BaseModel):
    connections: List[ConnectionListItem]

class DisconnectRequest(BaseModel):
    confirmation: bool = True

class DisconnectResponse(BaseModel):
    status: str = "revoked"
    connection_id: str
    revoked_at: str  # ISO string

# OAuth Configuration
PLATFORM_CONFIGS = {
    "meta": {
        "name": "Meta (Facebook & Instagram)",
        "auth_base": "https://www.facebook.com/{version}/dialog/oauth",
        "scopes": [
            "pages_show_list",
            "pages_manage_posts", 
            "pages_read_engagement",
            "instagram_basic",
            "instagram_content_publish",
            "instagram_manage_insights"
        ],
        "requires_pkce": False,
        "next_step": "asset_selection"
    },
    "x": {
        "name": "X (Twitter)",
        "auth_base": "https://twitter.com/i/oauth2/authorize",
        "scopes": [
            "tweet.read",
            "tweet.write",
            "users.read", 
            "offline.access"
        ],
        "requires_pkce": True,
        "next_step": "connection_confirm"
    }
}

def get_user_organization_id(user: User) -> str:
    """
    Get user's organization ID for tenant-aware OAuth
    For now, use user ID as organization ID (single-user orgs)
    TODO: Update when proper organization selection is implemented
    """
    # Check if user has a default organization
    if hasattr(user, 'default_organization_id') and user.default_organization_id:
        return str(user.default_organization_id)
    
    # Fallback to user ID (single-user organization)
    return str(user.id)

@router.get("/{platform}/start", response_model=OAuthStartResponse)
async def start_oauth_flow(
    platform: str,
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> OAuthStartResponse:
    """
    Initiate partner OAuth flow for a platform
    
    Args:
        platform: OAuth platform (meta, x)
        current_user: Authenticated user from JWT
        
    Returns:
        OAuth authorization URL and state
        
    Raises:
        HTTPException: If platform unsupported or configuration missing
    """
    try:
        # Validate platform
        if platform not in PLATFORM_CONFIGS:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_platform",
                    "message": f"Platform '{platform}' is not supported",
                    "supported_platforms": list(PLATFORM_CONFIGS.keys())
                }
            )
        
        platform_config = PLATFORM_CONFIGS[platform]
        settings = get_settings()
        
        # Get user's organization ID
        organization_id = get_user_organization_id(current_user)
        
        # Create PKCE state (stores code_verifier server-side)
        state_store = get_state_store()
        pkce_data = state_store.create(organization_id, platform)
        
        # Build OAuth parameters
        oauth_params = {
            "client_id": _get_client_id(platform, settings),
            "redirect_uri": _get_redirect_uri(platform, settings),
            "scope": " ".join(platform_config["scopes"]),
            "response_type": "code",
            "state": pkce_data["state"]
        }
        
        # Add PKCE parameters for X
        if platform_config["requires_pkce"]:
            oauth_params.update({
                "code_challenge": pkce_data["code_challenge"],
                "code_challenge_method": pkce_data["code_challenge_method"]
            })
        
        # Build authorization URL
        if platform == "meta":
            auth_base = platform_config["auth_base"].format(version=settings.meta_graph_version)
        else:
            auth_base = platform_config["auth_base"]
        
        auth_url = f"{auth_base}?{urllib.parse.urlencode(oauth_params)}"
        
        logger.info(
            f"Started OAuth flow for user {current_user.id}, org {organization_id}, platform {platform}",
            extra={"no_log_params": True}  # Prevent logging of auth URLs
        )
        
        return OAuthStartResponse(
            auth_url=auth_url,
            state=pkce_data["state"],
            platform=platform,
            expires_in=600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth start failed for platform {platform}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "oauth_start_failed",
                "message": "Failed to initiate OAuth flow",
                "platform": platform
            }
        )

@router.get("/{platform}/callback", response_model=OAuthCallbackResponse)
async def handle_oauth_callback(
    platform: str,
    code: str = Query(..., description="OAuth authorization code"),
    state: str = Query(..., description="OAuth state parameter"),
    error: Optional[str] = Query(None, description="OAuth error"),
    error_description: Optional[str] = Query(None, description="OAuth error description")
) -> OAuthCallbackResponse:
    """
    Handle OAuth callback from platform
    
    Args:
        platform: OAuth platform
        code: Authorization code from provider
        state: State parameter for validation
        error: OAuth error (if any)
        error_description: Error description (if any)
        
    Returns:
        OAuth callback result with next step
        
    Raises:
        HTTPException: If callback processing fails
    """
    try:
        # Check for OAuth errors from provider
        if error:
            logger.warning(f"OAuth error from {platform}: {error} - {error_description}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "oauth_provider_error",
                    "message": error_description or error,
                    "platform": platform,
                    "provider_error": error
                }
            )
        
        # Validate platform
        if platform not in PLATFORM_CONFIGS:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_platform",
                    "message": f"Platform '{platform}' is not supported"
                }
            )
        
        platform_config = PLATFORM_CONFIGS[platform]
        
        # Consume and validate state
        state_store = get_state_store()
        try:
            state_data = state_store.consume(state)
        except ValueError as e:
            logger.warning(f"Invalid state in OAuth callback: {e}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_state",
                    "message": "Invalid or expired state parameter",
                    "platform": platform
                }
            )
        
        # Verify platform matches
        if state_data["platform"] != platform:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "platform_mismatch",
                    "message": f"State platform {state_data['platform']} does not match callback platform {platform}"
                }
            )
        
        # Exchange code for tokens using existing orchestrator
        try:
            oauth_manager = SocialOAuthManager()
            
            # Build redirect URI
            settings = get_settings()
            redirect_uri = _get_redirect_uri(platform, settings)
            
            # Get code_verifier for PKCE (X only)
            code_verifier = state_data.get("code_verifier") if platform_config["requires_pkce"] else None
            
            # Exchange authorization code for tokens
            token_data = await _exchange_code_for_tokens(
                oauth_manager=oauth_manager,
                platform=platform,
                code=code,
                redirect_uri=redirect_uri,
                code_verifier=code_verifier,
                settings=settings
            )
            
            # Cache tokens temporarily for next phase
            state_store.cache_tokens(
                state=state,
                tokens=token_data,
                scopes=platform_config["scopes"]
            )
            
            logger.info(
                f"OAuth callback successful for org {state_data['organization_id']}, platform {platform}",
                extra={"no_log_tokens": True}
            )
            
            return OAuthCallbackResponse(
                status="success",
                platform=platform,
                state=state,
                next_step=platform_config["next_step"],
                expires_in=600
            )
            
        except Exception as e:
            logger.error(f"Token exchange failed for platform {platform}: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "token_exchange_failed",
                    "message": "Failed to exchange authorization code for tokens",
                    "platform": platform
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed for platform {platform}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "oauth_callback_failed",
                "message": "Failed to process OAuth callback",
                "platform": platform
            }
        )

# Helper Functions

def _get_client_id(platform: str, settings) -> str:
    """Get client ID for platform"""
    if platform == "meta":
        client_id = getattr(settings, 'meta_app_id', None)
        if not client_id:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "missing_config",
                    "message": "META_APP_ID not configured",
                    "platform": platform
                }
            )
        return client_id
    elif platform == "x":
        client_id = getattr(settings, 'x_client_id', None)
        if not client_id:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "missing_config", 
                    "message": "X_CLIENT_ID not configured",
                    "platform": platform
                }
            )
        return client_id
    else:
        raise ValueError(f"Unsupported platform: {platform}")

def _get_redirect_uri(platform: str, settings) -> str:
    """Get redirect URI for platform"""
    base_url = getattr(settings, 'backend_url', 'http://localhost:8000')
    return f"{base_url}/api/oauth/{platform}/callback"

async def _exchange_code_for_tokens(
    oauth_manager: SocialOAuthManager,
    platform: str,
    code: str,
    redirect_uri: str,
    code_verifier: Optional[str],
    settings
) -> Dict[str, Any]:
    """
    Exchange authorization code for tokens using the existing orchestrator
    
    This integrates with backend/auth/social_oauth.py without duplicating logic
    """
    import httpx
    import json
    
    if platform == "meta":
        # Meta token exchange
        token_url = f"https://graph.facebook.com/{settings.meta_graph_version}/oauth/access_token"
        
        token_data = {
            "client_id": _get_client_id(platform, settings),
            "client_secret": getattr(settings, 'meta_app_secret', ''),
            "redirect_uri": redirect_uri,
            "code": code
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=token_data)
            
            if response.status_code != 200:
                raise Exception(f"Meta token exchange failed: {response.text}")
            
            tokens = response.json()
            
            # Return standardized format
            return {
                "access_token": tokens["access_token"],
                "token_type": tokens.get("token_type", "bearer"),
                "expires_in": tokens.get("expires_in"),
                "platform": platform
            }
    
    elif platform == "x":
        # X token exchange with PKCE
        token_url = "https://api.twitter.com/2/oauth2/token"
        
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "client_id": _get_client_id(platform, settings)
        }
        
        # X uses basic auth
        auth = (
            _get_client_id(platform, settings),
            getattr(settings, 'x_client_secret', '')
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=token_data,
                auth=auth,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                raise Exception(f"X token exchange failed: {response.text}")
            
            tokens = response.json()
            
            return {
                "access_token": tokens["access_token"],
                "token_type": tokens.get("token_type", "bearer"),
                "expires_in": tokens.get("expires_in"),
                "refresh_token": tokens.get("refresh_token"),
                "scope": tokens.get("scope"),
                "platform": platform
            }
    
    else:
        raise ValueError(f"Unsupported platform: {platform}")

# Phase 4 Helper Functions

def _compute_connection_health(connection: SocialConnection) -> Dict[str, Any]:
    """
    Compute connection health metrics (delegates to a small, testable helper).
    """
    return compute_connection_health(connection)

async def _revoke_provider_access(connection: SocialConnection, settings) -> bool:
    """
    Revoke access at the provider level
    
    Args:
        connection: SocialConnection to revoke
        settings: Application settings
        
    Returns:
        True if revocation succeeded, False otherwise
    """
    try:
        from backend.core.encryption import decrypt_token
        
        if connection.platform == "meta":
            # Meta: DELETE /{page-id}/subscribed_apps
            if connection.page_access_token:
                try:
                    page_token = decrypt_token(connection.page_access_token)
                    page_id = connection.platform_metadata.get("page_id")
                    
                    if page_id and page_token:
                        # Unsubscribe page apps
                        url = f"https://graph.facebook.com/{settings.meta_graph_version}/{page_id}/subscribed_apps"
                        async with httpx.AsyncClient() as client:
                            response = await client.delete(url, params={"access_token": page_token})
                            if response.status_code not in [200, 400]:  # 400 is OK if already unsubscribed
                                logger.warning(f"Failed to unsubscribe Meta page {page_id}: {response.status_code}")
                        
                        # Unsubscribe Instagram if present
                        ig_id = connection.platform_metadata.get("ig_id")
                        if ig_id:
                            ig_url = f"https://graph.facebook.com/{settings.meta_graph_version}/{ig_id}/subscribed_apps"
                            async with httpx.AsyncClient() as client:
                                ig_response = await client.delete(ig_url, params={"access_token": page_token})
                                if ig_response.status_code not in [200, 400]:
                                    logger.warning(f"Failed to unsubscribe Instagram {ig_id}: {ig_response.status_code}")
                    
                except Exception as e:
                    logger.warning(f"Meta unsubscribe error: {e}")
            return True
            
        elif connection.platform == "x":
            # X: POST /2/oauth2/revoke
            try:
                access_token = decrypt_token(connection.access_token)
                
                revoke_url = "https://api.twitter.com/2/oauth2/revoke"
                revoke_data = {
                    "token": access_token,
                    "token_type_hint": "access_token"
                }
                
                # X uses client credentials for revocation
                auth = (
                    _get_client_id("x", settings),
                    getattr(settings, 'x_client_secret', '')
                )
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        revoke_url,
                        data=revoke_data,
                        auth=auth,
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
                    
                    if response.status_code not in [200, 400]:  # 400 might mean already revoked
                        logger.warning(f"X token revocation failed: {response.status_code} - {response.text}")
                        return False
                
            except Exception as e:
                logger.warning(f"X revoke error: {e}")
                return False
                
            return True
        
        else:
            logger.warning(f"Unknown platform for revocation: {connection.platform}")
            return False
            
    except Exception as e:
        logger.error(f"Provider revocation failed for {connection.platform}: {e}")
        return False

# Phase 3 Endpoints

@router.get("/meta/assets", response_model=MetaAssetsResponse)
async def get_meta_assets(
    state: str = Query(..., description="OAuth state from callback"),
    current_user: User = Depends(get_current_active_user)
) -> MetaAssetsResponse:
    """
    Get Facebook Pages and Instagram Business accounts for asset selection
    
    Args:
        state: OAuth state parameter from callback
        current_user: Authenticated user
        
    Returns:
        List of Facebook Pages with Instagram linking info
    """
    try:
        # Read cached user tokens
        state_store = get_state_store()
        cached_tokens = state_store.read_tokens(state)
        
        if not cached_tokens:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_state",
                    "message": "State not found or expired - please restart OAuth flow"
                }
            )
        
        user_token = cached_tokens["tokens"]["access_token"]
        
        # Get pages with Instagram info
        meta_service = get_meta_page_service()
        pages_data = await meta_service.list_pages_with_instagram(user_token)
        
        # Transform to response model
        pages = []
        for page_data in pages_data:
            page = FacebookPage(
                id=page_data["id"],
                name=page_data["name"],
                has_instagram=page_data["has_instagram"],
                token_available=page_data["token_available"],
                instagram_business_account=page_data.get("instagram_business_account")
            )
            pages.append(page)
        
        logger.info(f"Retrieved {len(pages)} Facebook Pages for user {current_user.id}")
        
        return MetaAssetsResponse(pages=pages)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Meta assets: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "assets_fetch_failed",
                "message": "Failed to retrieve Facebook Pages",
                "details": str(e)
            }
        )

@router.post("/meta/connect", response_model=MetaConnectResponse)
async def connect_meta_account(
    request: MetaConnectRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> MetaConnectResponse:
    """
    Connect a Facebook Page (and optional Instagram) to the organization
    
    Args:
        request: Connection request with state and page_id
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Connection details with encrypted tokens persisted
    """
    try:
        # Read cached user tokens
        state_store = get_state_store()
        cached_tokens = state_store.read_tokens(request.state)
        
        if not cached_tokens:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_state",
                    "message": "State not found or expired - please restart OAuth flow"
                }
            )
        
        user_token = cached_tokens["tokens"]["access_token"]
        organization_id = get_user_organization_id(current_user)
        
        # Exchange for page token
        meta_service = get_meta_page_service()
        page_token_data = await meta_service.exchange_for_page_token(user_token, request.page_id)
        
        page_access_token = page_token_data["page_access_token"]
        page_name = page_token_data["page_name"]
        
        # Get Instagram info if requested
        instagram_account = None
        instagram_id = None
        instagram_username = None
        
        if request.instagram_id:
            instagram_id = request.instagram_id
            instagram_username = await meta_service.get_instagram_username(instagram_id, page_access_token)
            if not instagram_username:
                instagram_username = f"ig_{request.instagram_id}"  # Fallback if username fetch fails
            instagram_account = {"id": instagram_id, "username": instagram_username}
        
        # Prepare connection data
        platform_account_id = request.instagram_id if request.instagram_id else request.page_id
        platform_username = instagram_username if instagram_username else page_name
        
        # Encrypt tokens
        encrypted_user_token = encrypt_token(user_token)
        encrypted_page_token = encrypt_token(page_access_token)
        
        # Create metadata
        platform_metadata = {
            "page_id": request.page_id,
            "page_name": page_name
        }
        
        if instagram_id:
            platform_metadata.update({
                "ig_id": instagram_id,
                "ig_username": instagram_username
            })
        
        # Calculate token expiration
        token_expires_at = None
        if cached_tokens["tokens"].get("expires_in"):
            expires_in = cached_tokens["tokens"]["expires_in"]
            token_expires_at = datetime.now(timezone.utc).timestamp() + expires_in
            token_expires_at = datetime.fromtimestamp(token_expires_at, tz=timezone.utc)
        
        # Create social connection
        connection = SocialConnection(
            organization_id=organization_id,
            platform="meta",
            platform_account_id=platform_account_id,
            platform_username=platform_username,
            connection_name=f"{page_name}" + (f" + @{instagram_username}" if instagram_username else ""),
            access_token=encrypted_user_token,
            page_access_token=encrypted_page_token,
            token_expires_at=token_expires_at,
            scopes=cached_tokens.get("scopes", PLATFORM_CONFIGS["meta"]["scopes"]),
            platform_metadata=platform_metadata,
            webhook_subscribed=False,
            is_active=True,
            revoked_at=None
        )
        
        db.add(connection)
        db.commit()
        db.refresh(connection)
        
        # Subscribe to webhooks
        webhook_subscription_success = False
        if get_meta_webhook_service:
            try:
                webhook_service = get_meta_webhook_service()
                
                # Subscribe Facebook Page to webhooks
                page_webhook_success = await webhook_service.subscribe_page_webhooks(
                    request.page_id, 
                    page_access_token
                )
                
                # Subscribe Instagram if present
                instagram_webhook_success = True  # Default to success if no Instagram
                if instagram_id:
                    instagram_webhook_success = await webhook_service.subscribe_instagram_webhooks(
                        instagram_id,
                        page_access_token
                    )
                
                # Overall webhook subscription success
                webhook_subscription_success = page_webhook_success and instagram_webhook_success
                
                # Update connection webhook status
                if webhook_subscription_success:
                    connection.webhook_subscribed = True
                    db.commit()
                    db.refresh(connection)
                    logger.info(f"Successfully subscribed Page {request.page_id} to webhooks")
                else:
                    logger.warning(f"Failed to fully subscribe Page {request.page_id} to webhooks")
                    
            except Exception as e:
                logger.error(f"Error subscribing Page {request.page_id} to webhooks: {e}")
                # Don't fail the connection, just log the error
        
        # Create audit log
        audit = SocialAudit(
            organization_id=organization_id,
            connection_id=connection.id,
            action="connect",
            platform="meta",
            user_id=current_user.id,
            status="success",
            audit_metadata={
                "page_id": request.page_id,
                "page_name": page_name,
                "instagram_id": instagram_id,
                "connection_type": "page_with_instagram" if instagram_id else "page_only",
                "webhook_subscription": webhook_subscription_success
            }
        )
        db.add(audit)
        db.commit()
        
        logger.info(f"Created Meta connection {connection.id} for org {organization_id}")
        
        return MetaConnectResponse(
            connection_id=str(connection.id),
            facebook_page={"id": request.page_id, "name": page_name},
            instagram_account=instagram_account
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        # Create failed audit log
        try:
            organization_id = get_user_organization_id(current_user)
            audit = SocialAudit(
                organization_id=organization_id,
                action="connect",
                platform="meta",
                user_id=current_user.id,
                status="failure",
                error_message=str(e),
                audit_metadata={"page_id": request.page_id, "error": str(e)}
            )
            db.add(audit)
            db.commit()
        except:
            pass
        
        raise HTTPException(
            status_code=400,
            detail={
                "error": "connection_failed",
                "message": str(e),
                "page_id": request.page_id
            }
        )
    except Exception as e:
        logger.error(f"Failed to connect Meta account: {e}")
        
        # Create failed audit log
        try:
            organization_id = get_user_organization_id(current_user)
            audit = SocialAudit(
                organization_id=organization_id,
                action="connect",
                platform="meta",
                user_id=current_user.id,
                status="failure",
                error_message=str(e),
                audit_metadata={"page_id": request.page_id, "error": str(e)}
            )
            db.add(audit)
            db.commit()
        except:
            pass
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "connection_failed",
                "message": "Failed to create connection",
                "details": str(e)
            }
        )

@router.post("/x/connect", response_model=XConnectResponse)
async def connect_x_account(
    request: XConnectRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> XConnectResponse:
    """
    Connect an X (Twitter) account to the organization
    
    Args:
        request: Connection request with state
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Connection details with encrypted tokens persisted
    """
    try:
        # Read cached tokens
        state_store = get_state_store()
        cached_tokens = state_store.read_tokens(request.state)
        
        if not cached_tokens:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_state",
                    "message": "State not found or expired - please restart OAuth flow"
                }
            )
        
        tokens = cached_tokens["tokens"]
        organization_id = get_user_organization_id(current_user)
        
        # Get user profile
        x_service = get_x_connection_service()
        user_context = await x_service.get_user_context(tokens)
        
        user_id = user_context["user_id"]
        username = user_context["username"]
        display_name = user_context["display_name"]
        metadata = user_context["metadata"]
        
        # Set connection timestamp
        metadata["last_connected"] = datetime.now(timezone.utc).isoformat()
        
        # Encrypt tokens
        encrypted_access_token = encrypt_token(tokens["access_token"])
        encrypted_refresh_token = None
        if tokens.get("refresh_token"):
            encrypted_refresh_token = encrypt_token(tokens["refresh_token"])
        
        # Calculate token expiration
        token_expires_at = None
        if tokens.get("expires_in"):
            expires_in = tokens["expires_in"]
            token_expires_at = datetime.now(timezone.utc).timestamp() + expires_in
            token_expires_at = datetime.fromtimestamp(token_expires_at, tz=timezone.utc)
        
        # Extract scopes
        scopes = x_service._extract_scopes(tokens)
        
        # Create social connection
        connection = SocialConnection(
            organization_id=organization_id,
            platform="x",
            platform_account_id=user_id,
            platform_username=username,
            connection_name=f"@{username} ({display_name})",
            access_token=encrypted_access_token,
            refresh_token=encrypted_refresh_token,
            token_expires_at=token_expires_at,
            scopes=scopes,
            platform_metadata=metadata,
            webhook_subscribed=False,
            is_active=True,
            revoked_at=None
        )
        
        db.add(connection)
        db.commit()
        db.refresh(connection)
        
        # Create audit log
        audit = SocialAudit(
            organization_id=organization_id,
            connection_id=connection.id,
            action="connect",
            platform="x",
            user_id=current_user.id,
            status="success",
            audit_metadata={
                "user_id": user_id,
                "username": username,
                "display_name": display_name,
                "verified": metadata.get("verified", False)
            }
        )
        db.add(audit)
        db.commit()
        
        logger.info(f"Created X connection {connection.id} for org {organization_id}")
        
        return XConnectResponse(
            connection_id=str(connection.id),
            username=username,
            user_id=user_id
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        # Create failed audit log
        try:
            organization_id = get_user_organization_id(current_user)
            audit = SocialAudit(
                organization_id=organization_id,
                action="connect",
                platform="x",
                user_id=current_user.id,
                status="failure",
                error_message=str(e),
                audit_metadata={"error": str(e)}
            )
            db.add(audit)
            db.commit()
        except:
            pass
        
        raise HTTPException(
            status_code=400,
            detail={
                "error": "connection_failed",
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Failed to connect X account: {e}")
        
        # Create failed audit log
        try:
            organization_id = get_user_organization_id(current_user)
            audit = SocialAudit(
                organization_id=organization_id,
                action="connect",
                platform="x",
                user_id=current_user.id,
                status="failure",
                error_message=str(e),
                audit_metadata={"error": str(e)}
            )
            db.add(audit)
            db.commit()
        except:
            pass
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "connection_failed",
                "message": "Failed to create connection",
                "details": str(e)
            }
        )

# Phase 4 Endpoints

@router.get("/connections", response_model=ConnectionListResponse)
async def list_connections(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ConnectionListResponse:
    """
    List all active social connections for the user's organization
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of connections with health status (no tokens)
    """
    try:
        organization_id = get_user_organization_id(current_user)
        
        # Query active connections for this organization
        connections = db.query(SocialConnection).filter(
            SocialConnection.organization_id == organization_id,
            SocialConnection.is_active == True,
            SocialConnection.revoked_at.is_(None)
        ).order_by(SocialConnection.created_at.desc()).all()
        
        # Transform to response models
        connection_items = []
        for connection in connections:
            health_data = _compute_connection_health(connection)
            
            item = ConnectionListItem(
                id=str(connection.id),
                platform=connection.platform,
                platform_account_id=connection.platform_account_id,
                platform_username=connection.platform_username,
                connection_name=connection.connection_name,
                scopes=connection.scopes or [],
                webhook_subscribed=connection.webhook_subscribed,
                expires_at=health_data["expires_at"],
                expires_in_hours=health_data["expires_in_hours"],
                last_checked_at=health_data["last_checked_at"],
                needs_reconnect=health_data["needs_reconnect"],
                created_at=health_data["created_at"]
            )
            connection_items.append(item)
        
        logger.info(f"Listed {len(connection_items)} connections for org {organization_id}")
        
        return ConnectionListResponse(connections=connection_items)
        
    except Exception as e:
        logger.error(f"Failed to list connections: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "connections_list_failed",
                "message": "Failed to retrieve connections"
            }
        )

@router.delete("/{connection_id}", response_model=DisconnectResponse)
async def disconnect_connection(
    connection_id: str,
    request: DisconnectRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> DisconnectResponse:
    """
    Disconnect and revoke a social connection
    
    Args:
        connection_id: UUID of connection to disconnect
        request: Disconnect confirmation
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Disconnection confirmation with timestamp
    """
    try:
        organization_id = get_user_organization_id(current_user)
        
        # Find the connection and verify ownership
        connection = db.query(SocialConnection).filter(
            SocialConnection.id == connection_id,
            SocialConnection.organization_id == organization_id,
            SocialConnection.is_active == True,
            SocialConnection.revoked_at.is_(None)
        ).first()
        
        if not connection:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "connection_not_found",
                    "message": "Connection not found or already disconnected",
                    "connection_id": connection_id
                }
            )
        
        # Unsubscribe from webhooks before revoking access
        webhook_unsubscription_success = False
        try:
            if connection.platform == "meta" and connection.webhook_subscribed:
                # Import webhook service
                try:
                    from backend.services.meta_webhook_service import get_meta_webhook_service
                    
                    webhook_service = get_meta_webhook_service()
                    
                    # Get encrypted page token for unsubscription
                    encrypted_page_token = connection.access_tokens.get("page_token")
                    if encrypted_page_token:
                        page_access_token = decrypt_token(encrypted_page_token)
                        page_id = connection.platform_account_id
                        
                        # Unsubscribe Page webhooks
                        page_webhook_success = await webhook_service.unsubscribe_page_webhooks(
                            page_id, 
                            page_access_token
                        )
                        
                        # Unsubscribe Instagram webhooks if available
                        instagram_webhook_success = True
                        instagram_id = connection.connection_metadata.get("instagram_account_id")
                        if instagram_id:
                            instagram_webhook_success = await webhook_service.unsubscribe_instagram_webhooks(
                                instagram_id,
                                page_access_token
                            )
                        
                        webhook_unsubscription_success = page_webhook_success and instagram_webhook_success
                        
                        logger.info(
                            f"Meta webhook unsubscription for connection {connection_id}: "
                            f"page_success={page_webhook_success}, "
                            f"instagram_success={instagram_webhook_success}"
                        )
                    else:
                        logger.warning(f"No page token found for Meta connection {connection_id} webhook unsubscription")
                        
                except ImportError:
                    logger.warning("Meta webhook service not available for unsubscription")
                except Exception as webhook_error:
                    logger.error(f"Error during webhook unsubscription for connection {connection_id}: {webhook_error}")
                    
        except Exception as e:
            logger.error(f"Unexpected error during webhook unsubscription for connection {connection_id}: {e}")

        # Revoke access at provider level
        settings = get_settings()
        revocation_success = await _revoke_provider_access(connection, settings)
        
        # Mark as revoked locally regardless of provider response
        revoked_at = datetime.now(timezone.utc)
        connection.is_active = False
        connection.revoked_at = revoked_at
        connection.webhook_subscribed = False
        
        db.commit()
        db.refresh(connection)
        
        # Create audit log
        audit_status = "success" if revocation_success else "partial_success"
        audit_metadata = {
            "connection_id": connection_id,
            "platform_account_id": connection.platform_account_id,
            "platform_username": connection.platform_username,
            "provider_revocation": revocation_success,
            "revoked_at": revoked_at.isoformat()
        }
        
        # Add webhook unsubscription results to audit metadata
        if connection.platform == "meta":
            audit_metadata["webhook_unsubscription"] = webhook_unsubscription_success
            audit_metadata["had_webhook_subscription"] = connection.webhook_subscribed
        
        audit = SocialAudit(
            organization_id=organization_id,
            connection_id=connection.id,
            action="disconnect",
            platform=connection.platform,
            user_id=current_user.id,
            status=audit_status,
            audit_metadata=audit_metadata
        )
        db.add(audit)
        db.commit()
        
        logger.info(
            f"Disconnected connection {connection_id} for org {organization_id}, "
            f"provider_revocation={revocation_success}"
        )
        
        return DisconnectResponse(
            status="revoked",
            connection_id=connection_id,
            revoked_at=revoked_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect connection {connection_id}: {e}")
        
        # Create failed audit log
        try:
            organization_id = get_user_organization_id(current_user)
            audit = SocialAudit(
                organization_id=organization_id,
                connection_id=connection_id if 'connection_id' in locals() else None,
                action="disconnect",
                platform="unknown",
                user_id=current_user.id,
                status="failure",
                error_message=str(e),
                audit_metadata={"connection_id": connection_id, "error": str(e)}
            )
            db.add(audit)
            db.commit()
        except:
            pass
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "disconnect_failed",
                "message": "Failed to disconnect connection",
                "connection_id": connection_id
            }
        )


@router.post("/{connection_id}/refresh")
async def refresh_connection_tokens(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: dict = Depends(require_partner_oauth_enabled)
) -> Dict[str, Any]:
    """
    Manually refresh tokens for a specific connection
    
    Args:
        connection_id: UUID of connection to refresh
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Task information for the refresh operation
    """
    try:
        organization_id = get_user_organization_id(current_user)
        
        # Verify connection exists and belongs to user's organization
        connection = db.query(SocialConnection).filter(
            SocialConnection.id == connection_id,
            SocialConnection.organization_id == organization_id,
            SocialConnection.is_active == True
        ).first()
        
        if not connection:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "connection_not_found",
                    "message": "Connection not found or not accessible",
                    "connection_id": connection_id
                }
            )
        
        # Check if platform supports token refresh
        if connection.platform not in ["meta", "x"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "platform_not_supported",
                    "message": f"Token refresh not supported for platform: {connection.platform}",
                    "connection_id": connection_id
                }
            )
        
        # Enqueue refresh task
        try:
            from backend.tasks.token_health_tasks import refresh_connection
            
            task = refresh_connection.delay(connection_id)
            task_id = task.id
            
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "service_unavailable", 
                    "message": "Token refresh service not available"
                }
            )
        except Exception as e:
            logger.error(f"Failed to enqueue refresh task for connection {connection_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "enqueue_failed",
                    "message": "Failed to enqueue refresh task"
                }
            )
        
        # Create audit log for manual refresh request
        audit = SocialAudit(
            organization_id=organization_id,
            connection_id=connection.id,
            action="manual_refresh_requested",
            platform=connection.platform,
            user_id=current_user.id,
            status="success",
            audit_metadata={
                "connection_id": connection_id,
                "task_id": task_id,
                "requested_by": current_user.email,
                "requested_at": datetime.now(timezone.utc).isoformat()
            }
        )
        db.add(audit)
        db.commit()
        
        logger.info(f"Manual refresh requested for connection {connection_id} by user {current_user.id}")
        
        return {
            "queued": True,
            "task_id": task_id,
            "connection_id": connection_id,
            "platform": connection.platform,
            "message": "Token refresh has been queued for processing",
            "requested_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual refresh request failed for connection {connection_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "refresh_request_failed",
                "message": "Failed to process refresh request",
                "connection_id": connection_id
            }
        )


# Disabled feature handler (when flag is off)
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def handle_disabled_feature(path: str):
    """
    Handle all requests when feature is disabled
    This should never be reached due to the dependency, but included for safety
    """
    return JSONResponse(
        status_code=404,
        content=DisabledFeatureResponse().dict()
    )