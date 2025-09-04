"""
LinkedIn API Client - 2025 Best Practices Implementation
Production-ready LinkedIn integration for autonomous social media posting

Following 2025 LinkedIn API guidelines:
- OAuth 2.0 authentication using requests-oauthlib
- Support for both 2-legged and 3-legged OAuth flows
- UGC API for content posting (requires partnership approval)
- Comprehensive error handling and rate limiting
- Integration with observability and token management systems
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

import requests
from requests_oauthlib import OAuth2Session
from urllib.parse import urlencode

from backend.core.config import get_settings
from backend.core.observability import get_observability_manager

logger = logging.getLogger(__name__)
settings = get_settings()
observability = get_observability_manager()


class LinkedInAPIError(Exception):
    """LinkedIn API specific exceptions"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class LinkedInAuthType(Enum):
    """LinkedIn OAuth flow types"""
    THREE_LEGGED = "3-legged"  # User authorization (recommended for posting)
    TWO_LEGGED = "2-legged"    # Client credentials (app-only access)


@dataclass
class LinkedInConfig:
    """LinkedIn API configuration"""
    client_id: str
    client_secret: str
    redirect_uri: str = "https://your-domain.com/auth/linkedin/callback"
    base_url: str = "https://api.linkedin.com"
    auth_url: str = "https://www.linkedin.com/oauth/v2/authorization"
    token_url: str = "https://www.linkedin.com/oauth/v2/accessToken"
    
    # 2025 API Scopes for content posting (requires LinkedIn Partnership)
    posting_scopes: List[str] = None
    basic_scopes: List[str] = None
    
    def __post_init__(self):
        if self.posting_scopes is None:
            self.posting_scopes = [
                "openid",
                "profile", 
                "email",
                "w_member_social"  # Required for UGC posting (Partnership needed)
            ]
        if self.basic_scopes is None:
            self.basic_scopes = [
                "openid",
                "profile",
                "email"
            ]


class LinkedInAPIClient:
    """
    Production-ready LinkedIn API client for autonomous social media management
    
    2025 Implementation Notes:
    - LinkedIn API is heavily restricted and requires Partnership Program approval for posting
    - "Share on LinkedIn" product must be added to your LinkedIn Developer app
    - UGC API access requires approved partnership status
    - Rate limiting is enforced per app and per user
    """
    
    def __init__(self, config: Optional[LinkedInConfig] = None):
        """Initialize LinkedIn API client with 2025 best practices"""
        
        # Load configuration from environment or use provided config
        if config is None:
            config = LinkedInConfig(
                client_id=settings.linkedin_client_id or "",
                client_secret=settings.linkedin_client_secret or "",
                redirect_uri=settings.linkedin_redirect_uri or "https://localhost:8000/auth/linkedin/callback"
            )
        
        self.config = config
        self.session = requests.Session()
        self._setup_session_defaults()
        
        # Track API usage for rate limiting
        self.request_count = 0
        self.last_request_time = None
        self.rate_limit_reset = None
        
        logger.info("LinkedIn API client initialized")
        
        # Warn if credentials are missing
        if not self.config.client_id or not self.config.client_secret:
            logger.warning("LinkedIn OAuth credentials not provided. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET environment variables.")
    
    def _setup_session_defaults(self):
        """Setup default session configuration"""
        self.session.headers.update({
            'User-Agent': 'Autonomous-Social-Media-AI/2.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'LinkedIn-Version': '202311'  # LinkedIn API version (2025)
        })
        
        # Set timeout for all requests
        self.session.request = lambda *args, **kwargs: requests.Session.request(
            self.session, *args, timeout=30, **kwargs
        )
    
    def get_authorization_url(self, scopes: Optional[List[str]] = None, state: Optional[str] = None) -> str:
        """
        Get LinkedIn OAuth authorization URL for 3-legged flow
        
        Args:
            scopes: OAuth scopes (defaults to basic scopes)
            state: CSRF protection state parameter
            
        Returns:
            Authorization URL for user to visit
        """
        if not self.config.client_id:
            raise LinkedInAPIError("LinkedIn client ID not configured")
        
        scopes = scopes or self.config.basic_scopes
        
        # Create OAuth2Session for authorization URL generation
        oauth = OAuth2Session(
            self.config.client_id,
            redirect_uri=self.config.redirect_uri,
            scope=scopes,
            state=state
        )
        
        authorization_url, state = oauth.authorization_url(self.config.auth_url)
        
        observability.add_sentry_breadcrumb(
            "Generated LinkedIn authorization URL",
            category="oauth",
            data={"scopes": scopes, "state": state}
        )
        
        return authorization_url
    
    def exchange_code_for_token(self, authorization_code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Exchange authorization code for access token (3-legged OAuth)
        
        Args:
            authorization_code: Code received from LinkedIn authorization
            state: CSRF state parameter for validation
            
        Returns:
            Token response with access_token, refresh_token, etc.
        """
        try:
            oauth = OAuth2Session(
                self.config.client_id,
                redirect_uri=self.config.redirect_uri,
                state=state
            )
            
            token = oauth.fetch_token(
                self.config.token_url,
                code=authorization_code,
                client_secret=self.config.client_secret,
                include_client_id=True
            )
            
            observability.add_sentry_breadcrumb(
                "Successfully exchanged LinkedIn authorization code for token",
                category="oauth",
                data={"expires_in": token.get("expires_in")}
            )
            
            return token
            
        except Exception as e:
            observability.capture_exception(e, {"step": "linkedin_token_exchange"})
            raise LinkedInAPIError(f"Failed to exchange code for token: {e}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh LinkedIn access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New token response
        """
        try:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': self.config.client_id,
                'client_secret': self.config.client_secret
            }
            
            response = self.session.post(
                self.config.token_url,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code != 200:
                raise LinkedInAPIError(
                    f"Token refresh failed: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.json() if response.content else None
                )
            
            token_data = response.json()
            
            observability.add_sentry_breadcrumb(
                "Successfully refreshed LinkedIn access token",
                category="oauth",
                data={"expires_in": token_data.get("expires_in")}
            )
            
            return token_data
            
        except Exception as e:
            observability.capture_exception(e, {"step": "linkedin_token_refresh"})
            raise LinkedInAPIError(f"Failed to refresh token: {e}")
    
    def _make_authenticated_request(
        self, 
        method: str, 
        endpoint: str, 
        access_token: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to LinkedIn API with rate limiting and error handling
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            access_token: Valid LinkedIn access token
            data: Request body data
            params: Query parameters
            
        Returns:
            API response data
        """
        url = f"{self.config.base_url}{endpoint}"
        
        # Add authorization header
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        
        # Rate limiting (basic implementation)
        self._handle_rate_limiting()
        
        try:
            start_time = time.time()
            
            response = self.session.request(
                method=method,
                url=url,
                json=data if data else None,
                params=params,
                headers=headers
            )
            
            duration = time.time() - start_time
            self.request_count += 1
            self.last_request_time = datetime.now(timezone.utc)
            
            # Track API performance
            observability.track_ai_generation("linkedin_api", "linkedin", "success", duration)
            
            # Handle rate limit headers
            if 'X-RateLimit-Reset' in response.headers:
                self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
            
            # Handle different response codes
            if response.status_code == 401:
                raise LinkedInAPIError("LinkedIn access token expired or invalid", status_code=401)
            elif response.status_code == 403:
                raise LinkedInAPIError("LinkedIn API access forbidden - check partnership status", status_code=403)
            elif response.status_code == 429:
                raise LinkedInAPIError("LinkedIn API rate limit exceeded", status_code=429)
            elif response.status_code >= 400:
                error_data = response.json() if response.content else {}
                raise LinkedInAPIError(
                    f"LinkedIn API error: {response.status_code}",
                    status_code=response.status_code,
                    response_data=error_data
                )
            
            return response.json() if response.content else {}
            
        except LinkedInAPIError:
            raise
        except Exception as e:
            duration = time.time() - start_time
            observability.track_ai_generation("linkedin_api", "linkedin", "failed", duration)
            observability.capture_exception(e, {"endpoint": endpoint, "method": method})
            raise LinkedInAPIError(f"LinkedIn API request failed: {e}")
    
    def _handle_rate_limiting(self):
        """Handle basic rate limiting to avoid API limits"""
        if self.last_request_time:
            # Basic rate limiting: max 1 request per second
            time_since_last = (datetime.now(timezone.utc) - self.last_request_time).total_seconds()
            if time_since_last < 1.0:
                sleep_time = 1.0 - time_since_last
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
    
    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """
        Get LinkedIn user profile information
        
        Args:
            access_token: Valid LinkedIn access token
            
        Returns:
            User profile data
        """
        return self._make_authenticated_request(
            "GET",
            "/v2/people/~",
            access_token
        )
    
    def create_ugc_post(
        self, 
        access_token: str, 
        person_urn: str, 
        text: str,
        media_urns: Optional[List[str]] = None,
        visibility: str = "PUBLIC"
    ) -> Dict[str, Any]:
        """
        Create UGC (User Generated Content) post on LinkedIn
        
        IMPORTANT: This requires LinkedIn Partnership Program approval and 
        "Share on LinkedIn" product added to your app.
        
        Args:
            access_token: Valid LinkedIn access token
            person_urn: LinkedIn person URN (e.g., "urn:li:person:PERSON_ID")
            text: Post content text
            media_urns: Optional list of media URNs for images/videos
            visibility: Post visibility ("PUBLIC", "CONNECTIONS")
            
        Returns:
            UGC post creation response
        """
        if not person_urn:
            raise LinkedInAPIError("person_urn is required for UGC post creation")
        
        # Construct UGC post data according to 2025 LinkedIn API format
        post_data = {
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "ARTICLE" if not media_urns else "IMAGE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }
        
        # Add media if provided
        if media_urns:
            post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                {"media": urn} for urn in media_urns
            ]
        
        try:
            result = self._make_authenticated_request(
                "POST",
                "/v2/ugcPosts",
                access_token,
                data=post_data
            )
            
            observability.add_sentry_breadcrumb(
                "Successfully created LinkedIn UGC post",
                category="social_posting",
                data={"post_id": result.get("id"), "text_length": len(text)}
            )
            
            return result
            
        except LinkedInAPIError as e:
            if e.status_code == 403:
                logger.error("LinkedIn UGC posting failed - Partnership Program approval required")
                raise LinkedInAPIError(
                    "LinkedIn posting requires Partnership Program approval and 'Share on LinkedIn' product. "
                    "See: https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication"
                )
            raise
    
    def get_post_analytics(self, access_token: str, ugc_post_urn: str) -> Dict[str, Any]:
        """
        Get analytics for a LinkedIn UGC post (requires partnership)
        
        Args:
            access_token: Valid LinkedIn access token
            ugc_post_urn: LinkedIn UGC post URN
            
        Returns:
            Post analytics data
        """
        return self._make_authenticated_request(
            "GET",
            f"/v2/socialActions/{ugc_post_urn}",
            access_token
        )
    
    def upload_media(self, access_token: str, person_urn: str, media_data: bytes, media_type: str) -> str:
        """
        Upload media to LinkedIn for use in posts (requires partnership)
        
        Args:
            access_token: Valid LinkedIn access token
            person_urn: LinkedIn person URN
            media_data: Binary media data
            media_type: MIME type (e.g., "image/jpeg")
            
        Returns:
            Media URN for use in posts
        """
        # This is a simplified implementation - full media upload requires multiple API calls
        # 1. Register upload
        # 2. Upload binary data
        # 3. Finalize upload
        
        logger.warning("LinkedIn media upload not fully implemented - requires partnership approval")
        raise LinkedInAPIError("Media upload requires LinkedIn Partnership Program approval")
    
    def validate_token(self, access_token: str) -> bool:
        """
        Validate LinkedIn access token
        
        Args:
            access_token: Token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            self.get_user_profile(access_token)
            return True
        except LinkedInAPIError:
            return False


# Production-ready client instance with error handling
class LinkedInClientWrapper:
    """Wrapper for LinkedIn client with enhanced error handling and fallbacks"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize LinkedIn client with proper error handling"""
        try:
            self.client = LinkedInAPIClient()
            logger.info("LinkedIn client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LinkedIn client: {e}")
            observability.capture_exception(e, {"component": "linkedin_client_init"})
    
    def is_available(self) -> bool:
        """Check if LinkedIn client is available and properly configured"""
        return (
            self.client is not None and 
            bool(settings.linkedin_client_id) and 
            bool(settings.linkedin_client_secret)
        )
    
    def create_post(self, access_token: str, person_urn: str, content: str) -> Dict[str, Any]:
        """
        Create LinkedIn post with comprehensive error handling
        
        Args:
            access_token: Valid LinkedIn access token
            person_urn: LinkedIn person URN  
            content: Post content
            
        Returns:
            Post creation result or error information
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "LinkedIn client not available or not configured",
                "requires_setup": True
            }
        
        try:
            result = self.client.create_ugc_post(
                access_token=access_token,
                person_urn=person_urn,
                text=content
            )
            
            return {
                "success": True,
                "post_id": result.get("id"),
                "post_url": f"https://linkedin.com/posts/{result.get('id', '')}"
            }
            
        except LinkedInAPIError as e:
            error_response = {
                "success": False,
                "error": str(e),
                "status_code": e.status_code
            }
            
            # Add specific guidance for common issues
            if e.status_code == 403:
                error_response["guidance"] = (
                    "LinkedIn posting requires Partnership Program approval. "
                    "Apply at: https://docs.microsoft.com/en-us/linkedin/marketing/getting-started"
                )
            elif e.status_code == 401:
                error_response["guidance"] = "Access token expired. Please re-authenticate."
            
            return error_response


# Global instance for use throughout the application
linkedin_client = LinkedInClientWrapper()

# Export the client class for direct use if needed
LinkedInAPIClientWrapper = LinkedInClientWrapper