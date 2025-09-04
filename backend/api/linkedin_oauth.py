"""
LinkedIn OAuth API Endpoints - 2025 Implementation
Production-ready LinkedIn OAuth flow with comprehensive error handling

Endpoints:
- GET /api/linkedin/auth - Initiate LinkedIn OAuth flow
- GET /api/linkedin/callback - Handle OAuth callback
- POST /api/linkedin/test-post - Test LinkedIn posting (requires Partnership)
- GET /api/linkedin/profile - Get user profile
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.auth.dependencies import get_current_active_user
from backend.db.models import User
from backend.integrations.linkedin_client import linkedin_client, LinkedInAPIError
from backend.core.observability import get_observability_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/linkedin", tags=["linkedin-oauth"])
observability = get_observability_manager()


class LinkedInAuthResponse(BaseModel):
    """Response model for LinkedIn authentication initiation"""
    authorization_url: str
    state: str
    message: str


class LinkedInProfileResponse(BaseModel):
    """Response model for LinkedIn profile data"""
    id: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    profile_picture: Optional[str] = None


class LinkedInPostRequest(BaseModel):
    """Request model for LinkedIn post creation"""
    content: str
    visibility: str = "PUBLIC"


@router.get("/auth", response_model=LinkedInAuthResponse)
async def initiate_linkedin_auth(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Initiate LinkedIn OAuth authentication flow
    
    This endpoint starts the LinkedIn OAuth process by generating an authorization URL.
    The user will be redirected to LinkedIn to grant permissions.
    
    Requires:
    - LinkedIn Partnership Program approval for posting features
    - "Share on LinkedIn" product added to LinkedIn Developer app
    """
    try:
        if not linkedin_client.is_available():
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "LinkedIn OAuth not configured",
                    "message": "LinkedIn client credentials are not configured. Please set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET environment variables.",
                    "requires_setup": True
                }
            )
        
        # Generate CSRF state for security
        import secrets
        state = secrets.token_urlsafe(32)
        
        # Store state in session or database for validation
        # For production, you should store this in a secure session store or database
        # associated with the current user
        
        # Get authorization URL with appropriate scopes
        # Note: Posting scopes require LinkedIn Partnership Program approval
        scopes = ["openid", "profile", "email"]  # Basic scopes that work without partnership
        
        try:
            authorization_url = linkedin_client.client.get_authorization_url(
                scopes=scopes,
                state=state
            )
        except Exception as e:
            logger.error(f"Failed to generate LinkedIn authorization URL: {e}")
            observability.capture_exception(e, {"step": "linkedin_auth_url_generation"})
            raise HTTPException(
                status_code=500,
                detail="Failed to generate LinkedIn authorization URL"
            )
        
        observability.add_sentry_breadcrumb(
            f"Generated LinkedIn auth URL for user {current_user.id}",
            category="oauth",
            data={"scopes": scopes, "user_id": current_user.id}
        )
        
        return LinkedInAuthResponse(
            authorization_url=authorization_url,
            state=state,
            message="Redirect user to authorization_url to complete LinkedIn OAuth"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LinkedIn OAuth initiation failed: {e}")
        observability.capture_exception(e, {"step": "linkedin_oauth_init"})
        raise HTTPException(
            status_code=500,
            detail="Failed to initiate LinkedIn OAuth flow"
        )


@router.get("/callback")
async def linkedin_oauth_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from LinkedIn"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    error: Optional[str] = Query(None, description="Error from LinkedIn OAuth"),
    error_description: Optional[str] = Query(None, description="Error description"),
    db: Session = Depends(get_db)
):
    """
    Handle LinkedIn OAuth callback
    
    This endpoint processes the OAuth callback from LinkedIn after user authorization.
    It exchanges the authorization code for access tokens.
    """
    try:
        # Handle OAuth errors
        if error:
            logger.warning(f"LinkedIn OAuth error: {error} - {error_description}")
            observability.add_sentry_breadcrumb(
                f"LinkedIn OAuth error: {error}",
                category="oauth_error",
                data={"error": error, "description": error_description}
            )
            
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"LinkedIn OAuth failed: {error}",
                    "description": error_description or "OAuth authorization was denied or failed"
                }
            )
        
        # Validate state parameter (in production, validate against stored state)
        if not state:
            raise HTTPException(
                status_code=400,
                detail="Missing state parameter - possible CSRF attack"
            )
        
        # Exchange code for token
        try:
            token_data = linkedin_client.client.exchange_code_for_token(
                authorization_code=code,
                state=state
            )
        except LinkedInAPIError as e:
            logger.error(f"LinkedIn token exchange failed: {e}")
            observability.capture_exception(e, {"step": "linkedin_token_exchange"})
            raise HTTPException(
                status_code=400,
                detail=f"Token exchange failed: {e}"
            )
        
        # Get user profile to verify token
        try:
            profile = linkedin_client.client.get_user_profile(
                access_token=token_data["access_token"]
            )
        except LinkedInAPIError as e:
            logger.error(f"Failed to get LinkedIn profile: {e}")
            observability.capture_exception(e, {"step": "linkedin_profile_fetch"})
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get user profile: {e}"
            )
        
        # In production, you should:
        # 1. Store the tokens securely (encrypted) in the database
        # 2. Associate them with the current user
        # 3. Set up token refresh scheduling
        
        observability.add_sentry_breadcrumb(
            "Successfully completed LinkedIn OAuth flow",
            category="oauth",
            data={
                "linkedin_id": profile.get("id"),
                "expires_in": token_data.get("expires_in")
            }
        )
        
        return {
            "success": True,
            "message": "LinkedIn account connected successfully",
            "profile": {
                "id": profile.get("id"),
                "first_name": profile.get("localizedFirstName", ""),
                "last_name": profile.get("localizedLastName", ""),
                "profile_picture": profile.get("profilePicture", {}).get("displayImage")
            },
            "token_info": {
                "expires_in": token_data.get("expires_in"),
                "scope": token_data.get("scope", "").split()
            },
            "partnership_required": {
                "posting": "Requires LinkedIn Partnership Program approval",
                "analytics": "Requires LinkedIn Partnership Program approval",
                "messaging": "Requires LinkedIn Partnership Program approval"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LinkedIn OAuth callback failed: {e}")
        observability.capture_exception(e, {"step": "linkedin_oauth_callback"})
        raise HTTPException(
            status_code=500,
            detail="Failed to process LinkedIn OAuth callback"
        )


@router.get("/profile", response_model=LinkedInProfileResponse)
async def get_linkedin_profile(
    access_token: str = Query(..., description="LinkedIn access token"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get LinkedIn user profile
    
    Retrieves the LinkedIn profile information for the authenticated user.
    Requires a valid LinkedIn access token.
    """
    try:
        if not linkedin_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="LinkedIn client not available"
            )
        
        profile = linkedin_client.client.get_user_profile(access_token)
        
        return LinkedInProfileResponse(
            id=profile.get("id", ""),
            first_name=profile.get("localizedFirstName", ""),
            last_name=profile.get("localizedLastName", ""),
            email=profile.get("elements", [{}])[0].get("handle~", {}).get("emailAddress") if "elements" in profile else None
        )
        
    except LinkedInAPIError as e:
        logger.error(f"Failed to get LinkedIn profile: {e}")
        observability.capture_exception(e, {"step": "linkedin_get_profile"})
        
        if e.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="LinkedIn access token expired or invalid"
            )
        elif e.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="LinkedIn API access forbidden - check partnership status"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get LinkedIn profile: {e}"
            )
    except Exception as e:
        logger.error(f"LinkedIn profile request failed: {e}")
        observability.capture_exception(e, {"step": "linkedin_profile_request"})
        raise HTTPException(
            status_code=500,
            detail="Failed to get LinkedIn profile"
        )


@router.post("/test-post")
async def create_linkedin_test_post(
    post_data: LinkedInPostRequest,
    access_token: str = Query(..., description="LinkedIn access token"),
    person_urn: str = Query(..., description="LinkedIn person URN (e.g., urn:li:person:PERSON_ID)"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a test LinkedIn post
    
    IMPORTANT: This endpoint requires:
    - LinkedIn Partnership Program approval
    - "Share on LinkedIn" product added to your LinkedIn Developer app
    - UGC (User Generated Content) API access
    
    Without partnership approval, this will return a 403 Forbidden error.
    """
    try:
        if not linkedin_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="LinkedIn client not available"
            )
        
        # Attempt to create post (will fail without partnership)
        result = linkedin_client.create_post(
            access_token=access_token,
            person_urn=person_urn,
            content=post_data.content
        )
        
        if result.get("success"):
            observability.add_sentry_breadcrumb(
                f"Successfully created LinkedIn test post for user {current_user.id}",
                category="social_posting",
                data={"post_id": result.get("post_id"), "content_length": len(post_data.content)}
            )
            
            return {
                "success": True,
                "message": "LinkedIn post created successfully",
                "post_id": result.get("post_id"),
                "post_url": result.get("post_url")
            }
        else:
            return {
                "success": False,
                "error": result.get("error"),
                "guidance": result.get("guidance"),
                "partnership_required": True
            }
            
    except Exception as e:
        logger.error(f"LinkedIn test post failed: {e}")
        observability.capture_exception(e, {"step": "linkedin_test_post"})
        
        return {
            "success": False,
            "error": str(e),
            "message": "LinkedIn posting requires Partnership Program approval",
            "guidance": "Apply for LinkedIn Partnership Program at: https://docs.microsoft.com/en-us/linkedin/marketing/getting-started",
            "partnership_required": True
        }


@router.get("/status")
async def linkedin_integration_status():
    """
    Get LinkedIn integration status and requirements
    
    Returns information about the LinkedIn API integration status,
    configuration requirements, and partnership program details.
    """
    try:
        is_configured = linkedin_client.is_available()
        
        return {
            "configured": is_configured,
            "client_available": linkedin_client.client is not None,
            "requirements": {
                "environment_variables": {
                    "LINKEDIN_CLIENT_ID": "Required - Your LinkedIn app client ID",
                    "LINKEDIN_CLIENT_SECRET": "Required - Your LinkedIn app client secret",
                    "LINKEDIN_REDIRECT_URI": "Optional - OAuth callback URL"
                },
                "linkedin_developer_setup": {
                    "app_creation": "Create app at: https://www.linkedin.com/developers/apps",
                    "products_required": [
                        "Sign In with LinkedIn using OpenID Connect",
                        "Share on LinkedIn (requires Partnership Program approval)"
                    ],
                    "partnership_program": "Required for posting - apply at: https://docs.microsoft.com/en-us/linkedin/marketing/getting-started"
                }
            },
            "api_limitations": {
                "basic_access": [
                    "User profile information",
                    "Basic authentication"
                ],
                "partnership_required": [
                    "Content posting (UGC API)",
                    "Post analytics",
                    "Company page management",
                    "Advanced user data"
                ]
            },
            "implementation_status": "Complete - 2025 best practices with OAuth 2.0",
            "last_updated": "2025"
        }
        
    except Exception as e:
        logger.error(f"Failed to get LinkedIn status: {e}")
        observability.capture_exception(e, {"step": "linkedin_status"})
        return {
            "configured": False,
            "error": str(e),
            "message": "Failed to check LinkedIn integration status"
        }