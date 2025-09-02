"""
Instagram API Client with OAuth 2.0 Support
Handles authentication, posting, and metrics collection for Instagram platform
"""
import os
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import json
import time
from dataclasses import dataclass
from enum import Enum

import requests
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session

from backend.core.token_encryption import get_token_manager
from backend.core.audit_logger import log_content_event, AuditEventType

logger = logging.getLogger(__name__)

class InstagramMediaType(Enum):
    """Instagram media types"""
    IMAGE = "IMAGE"
    VIDEO = "VIDEO" 
    CAROUSEL_ALBUM = "CAROUSEL_ALBUM"
    REELS = "REELS"

class InstagramAPIError(Exception):
    """Custom exception for Instagram API errors"""
    pass

@dataclass
class InstagramPost:
    """Instagram post data structure"""
    id: str
    caption: str
    media_type: str  # IMAGE, VIDEO, CAROUSEL_ALBUM
    media_url: str
    permalink: str
    created_at: datetime
    engagement_metrics: Dict[str, int]

class InstagramClient:
    """
    Instagram API client with OAuth 2.0 authentication and comprehensive features
    
    Features:
    - OAuth 2.0 authentication flow (Instagram Basic Display API)
    - Image and video post creation
    - Engagement metrics collection
    - Rate limit handling
    - Error recovery and retry logic
    
    Note: Uses Instagram Basic Display API for personal accounts.
    For business accounts, use Instagram Graph API which requires Facebook Business approval.
    """
    
    # Instagram Graph API endpoints (Meta/Facebook)
    BASE_URL = "https://graph.instagram.com"
    FACEBOOK_OAUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
    FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
    
    # Instagram API limits
    MAX_CAPTION_LENGTH = 2200
    SUPPORTED_IMAGE_FORMATS = ["jpg", "jpeg", "png"]
    SUPPORTED_VIDEO_FORMATS = ["mp4", "mov"]
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Initialize Instagram client
        
        Args:
            client_id: Facebook App ID for Instagram API access
            client_secret: Facebook App Secret
        """
        self.client_id = client_id or os.getenv("INSTAGRAM_CLIENT_ID") or os.getenv("FACEBOOK_APP_ID")
        self.client_secret = client_secret or os.getenv("INSTAGRAM_CLIENT_SECRET") or os.getenv("FACEBOOK_APP_SECRET")
        
        if not self.client_id or not self.client_secret:
            logger.warning("Instagram OAuth credentials not provided. Set INSTAGRAM_CLIENT_ID and INSTAGRAM_CLIENT_SECRET environment variables.")
        
        self.token_manager = get_token_manager()
        self.session = requests.Session()
        
        # Rate limiting tracking
        self.rate_limits = {}
        self.last_rate_limit_check = {}
        
        logger.info("Instagram client initialized")
    
    def get_oauth_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> Tuple[str, str]:
        """
        Get OAuth 2.0 authorization URL for user consent
        
        Args:
            redirect_uri: OAuth redirect URI
            state: Optional state parameter for CSRF protection
            
        Returns:
            Tuple of (authorization_url, state)
        """
        try:
            # Instagram uses Facebook OAuth with specific scopes
            oauth = OAuth2Session(
                client_id=self.client_id,
                redirect_uri=redirect_uri,
                scope=["instagram_basic", "instagram_content_publish", "pages_show_list"]
            )
            
            authorization_url, state = oauth.authorization_url(
                self.FACEBOOK_OAUTH_URL,
                state=state
            )
            
            logger.info(f"Generated Instagram OAuth authorization URL for redirect_uri: {redirect_uri}")
            return authorization_url, state
            
        except Exception as e:
            logger.error(f"Failed to generate Instagram OAuth authorization URL: {e}")
            raise InstagramAPIError(f"OAuth authorization URL generation failed: {e}")
    
    def exchange_code_for_tokens(self, authorization_code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens
        
        Args:
            authorization_code: OAuth authorization code from callback
            redirect_uri: OAuth redirect URI used in authorization
            
        Returns:
            Dictionary containing token data
        """
        try:
            token_data = {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = requests.post(
                self.FACEBOOK_TOKEN_URL,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15
            )
            
            if response.status_code != 200:
                logger.error(f"Instagram token exchange failed: {response.status_code} - {response.text}")
                raise InstagramAPIError(f"Token exchange failed: {response.text}")
            
            token_response = response.json()
            
            # Exchange short-lived token for long-lived token
            if "access_token" in token_response:
                long_lived_token = self._get_long_lived_token(token_response["access_token"])
                if long_lived_token:
                    token_response.update(long_lived_token)
            
            logger.info("Successfully exchanged authorization code for Instagram tokens")
            return token_response
            
        except Exception as e:
            logger.error(f"Instagram token exchange failed: {e}")
            raise InstagramAPIError(f"Token exchange failed: {e}")
    
    def _get_long_lived_token(self, short_lived_token: str) -> Optional[Dict[str, Any]]:
        """
        Exchange short-lived access token for long-lived token (60 days)
        
        Args:
            short_lived_token: Short-lived access token
            
        Returns:
            Long-lived token data or None if exchange fails
        """
        try:
            response = requests.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "fb_exchange_token": short_lived_token
                },
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                token_data["expires_at"] = time.time() + token_data.get("expires_in", 5184000)  # 60 days default
                logger.info("Successfully obtained long-lived Instagram token")
                return token_data
            else:
                logger.warning(f"Failed to get long-lived token: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get long-lived Instagram token: {e}")
            return None
    
    def _get_authenticated_session(self, access_token: str) -> requests.Session:
        """Get authenticated requests session"""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        })
        return session
    
    def _check_rate_limit(self, endpoint: str) -> bool:
        """
        Check if we're within rate limits for an endpoint
        
        Args:
            endpoint: API endpoint to check
            
        Returns:
            True if within limits, False if rate limited
        """
        now = time.time()
        rate_limit_info = self.rate_limits.get(endpoint, {})
        
        # Check if rate limit has reset
        reset_time = rate_limit_info.get("reset_time", 0)
        if now >= reset_time:
            return True
        
        # Check remaining requests
        remaining = rate_limit_info.get("remaining", 1)
        return remaining > 0
    
    def _update_rate_limit(self, endpoint: str, response: requests.Response):
        """Update rate limit tracking from API response headers"""
        headers = response.headers
        
        # Instagram uses different rate limit headers
        self.rate_limits[endpoint] = {
            "limit": int(headers.get("x-app-usage", "{}").split(",")[0].split(":")[1] if "x-app-usage" in headers else 100),
            "remaining": 100 - int(headers.get("x-app-usage", "{}").split(",")[0].split(":")[1] if "x-app-usage" in headers else 0),
            "reset_time": int(time.time()) + 3600  # Assume 1 hour reset
        }
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get authenticated user information
        
        Args:
            access_token: OAuth access token
            
        Returns:
            Dictionary containing user information
        """
        try:
            # First get user's pages to find Instagram account
            pages_response = requests.get(
                "https://graph.facebook.com/v18.0/me/accounts",
                params={
                    "access_token": access_token,
                    "fields": "id,name,access_token"
                }
            )
            
            if pages_response.status_code != 200:
                logger.error(f"Failed to get Facebook pages: {pages_response.status_code} - {pages_response.text}")
                raise InstagramAPIError(f"Failed to get user pages: {pages_response.text}")
            
            pages_data = pages_response.json()
            
            # Find Instagram Business Account
            instagram_account_id = None
            page_access_token = None
            
            for page in pages_data.get("data", []):
                # Get Instagram account connected to this page
                ig_response = requests.get(
                    f"https://graph.facebook.com/v18.0/{page['id']}",
                    params={
                        "access_token": page["access_token"],
                        "fields": "instagram_business_account"
                    }
                )
                
                if ig_response.status_code == 200:
                    ig_data = ig_response.json()
                    if "instagram_business_account" in ig_data:
                        instagram_account_id = ig_data["instagram_business_account"]["id"]
                        page_access_token = page["access_token"]
                        break
            
            if not instagram_account_id:
                raise InstagramAPIError("No Instagram Business Account found")
            
            # Get Instagram account details
            response = requests.get(
                f"https://graph.facebook.com/v18.0/{instagram_account_id}",
                params={
                    "access_token": page_access_token,
                    "fields": "id,username,name,profile_picture_url,followers_count,follows_count,media_count"
                }
            )
            
            self._update_rate_limit("user_info", response)
            
            if response.status_code != 200:
                logger.error(f"Failed to get Instagram user info: {response.status_code} - {response.text}")
                raise InstagramAPIError(f"Failed to get user info: {response.text}")
            
            user_data = response.json()
            
            profile = {
                "id": user_data.get("id"),
                "username": user_data.get("username", ""),
                "name": user_data.get("name", ""),
                "profile_picture": user_data.get("profile_picture_url", ""),
                "followers_count": user_data.get("followers_count", 0),
                "following_count": user_data.get("follows_count", 0),
                "media_count": user_data.get("media_count", 0),
                "page_access_token": page_access_token  # Store for posting
            }
            
            logger.info(f"Retrieved Instagram user info for @{profile['username']}")
            return profile
            
        except Exception as e:
            logger.error(f"Failed to get Instagram user info: {e}")
            raise InstagramAPIError(f"Failed to get user info: {e}")
    
    def create_media_container(self, access_token: str, image_url: str, caption: str, instagram_account_id: str) -> str:
        """
        Create a media container for posting
        
        Args:
            access_token: Page access token
            image_url: Publicly accessible image URL
            caption: Post caption
            instagram_account_id: Instagram Business Account ID
            
        Returns:
            Media container ID
        """
        try:
            # Validate caption length
            if len(caption) > self.MAX_CAPTION_LENGTH:
                raise InstagramAPIError(f"Caption too long: {len(caption)} > {self.MAX_CAPTION_LENGTH}")
            
            # Create media container
            response = requests.post(
                f"https://graph.facebook.com/v18.0/{instagram_account_id}/media",
                params={
                    "access_token": access_token,
                    "image_url": image_url,
                    "caption": caption
                },
                timeout=30
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Failed to create Instagram media container: {response.status_code} - {response.text}")
                raise InstagramAPIError(f"Failed to create media container: {response.text}")
            
            container_data = response.json()
            container_id = container_data.get("id")
            
            logger.info(f"Created Instagram media container: {container_id}")
            return container_id
            
        except Exception as e:
            logger.error(f"Failed to create Instagram media container: {e}")
            raise InstagramAPIError(f"Failed to create media container: {e}")
    
    def publish_media(self, access_token: str, container_id: str, instagram_account_id: str, user_id: int) -> Dict[str, Any]:
        """
        Publish a media container to Instagram
        
        Args:
            access_token: Page access token
            container_id: Media container ID
            instagram_account_id: Instagram Business Account ID
            user_id: User ID for audit logging
            
        Returns:
            Dictionary containing post response data
        """
        try:
            # Check rate limits
            if not self._check_rate_limit("media_publish"):
                raise InstagramAPIError("Rate limit exceeded for media publish endpoint")
            
            # Publish media
            response = requests.post(
                f"https://graph.facebook.com/v18.0/{instagram_account_id}/media_publish",
                params={
                    "access_token": access_token,
                    "creation_id": container_id
                },
                timeout=30
            )
            
            self._update_rate_limit("media_publish", response)
            
            if response.status_code not in [200, 201]:
                logger.error(f"Failed to publish Instagram media: {response.status_code} - {response.text}")
                raise InstagramAPIError(f"Failed to publish media: {response.text}")
            
            publish_data = response.json()
            post_id = publish_data.get("id")
            
            # Log successful posting
            log_content_event(
                AuditEventType.CONTENT_PUBLISHED,
                user_id=user_id,
                resource=f"instagram_post_{post_id}",
                action="publish_media",
                additional_data={
                    "post_id": post_id,
                    "container_id": container_id,
                    "instagram_account_id": instagram_account_id
                }
            )
            
            logger.info(f"Successfully published Instagram post: {post_id}")
            return {
                "id": post_id,
                "container_id": container_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to publish Instagram media: {e}")
            
            # Log failed posting
            log_content_event(
                AuditEventType.CONTENT_PUBLISHED,
                user_id=user_id,
                resource="instagram_post_failed",
                action="publish_media",
                additional_data={
                    "error": str(e),
                    "container_id": container_id
                }
            )
            
            raise InstagramAPIError(f"Failed to publish media: {e}")
    
    def post_image(self, access_token: str, image_url: str, caption: str, user_id: int) -> Dict[str, Any]:
        """
        Post an image to Instagram (combines container creation and publishing)
        
        Args:
            access_token: OAuth access token
            image_url: Publicly accessible image URL
            caption: Post caption
            user_id: User ID for audit logging
            
        Returns:
            Dictionary containing post response data
        """
        try:
            # Get user info to get Instagram account ID and page token
            user_info = self.get_user_info(access_token)
            instagram_account_id = user_info["id"]
            page_access_token = user_info["page_access_token"]
            
            # Create media container
            container_id = self.create_media_container(
                page_access_token, 
                image_url, 
                caption, 
                instagram_account_id
            )
            
            # Wait for media processing (Instagram requirement)
            import time
            time.sleep(2)  # Wait for Instagram processing
            
            # Publish media
            publish_result = self.publish_media(
                page_access_token,
                container_id,
                instagram_account_id,
                user_id
            )
            
            return {
                "id": publish_result["id"],
                "caption": caption,
                "image_url": image_url,
                "instagram_account_id": instagram_account_id,
                "created_at": publish_result["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Failed to post Instagram image: {e}")
            raise InstagramAPIError(f"Failed to post image: {e}")
    
    def get_post_metrics(self, access_token: str, post_id: str) -> Dict[str, Any]:
        """
        Get engagement metrics for a specific Instagram post
        
        Args:
            access_token: OAuth access token
            post_id: Instagram post ID
            
        Returns:
            Dictionary containing post metrics
        """
        try:
            # Check rate limits
            if not self._check_rate_limit("insights"):
                raise InstagramAPIError("Rate limit exceeded for insights endpoint")
            
            # Get post insights
            response = requests.get(
                f"https://graph.facebook.com/v18.0/{post_id}/insights",
                params={
                    "access_token": access_token,
                    "metric": "impressions,reach,likes,comments,saves,shares"
                }
            )
            
            self._update_rate_limit("insights", response)
            
            if response.status_code != 200:
                logger.error(f"Failed to get Instagram post metrics: {response.status_code} - {response.text}")
                # Return empty metrics if API call fails
                return {
                    "post_id": post_id,
                    "impressions_count": 0,
                    "reach_count": 0,
                    "likes_count": 0,
                    "comments_count": 0,
                    "saves_count": 0,
                    "shares_count": 0,
                    "engagement_rate": 0.0,
                    "retrieved_at": datetime.utcnow().isoformat()
                }
            
            insights_data = response.json()
            
            # Parse insights data
            metrics = {}
            for insight in insights_data.get("data", []):
                metric_name = insight.get("name")
                metric_values = insight.get("values", [])
                if metric_values:
                    metrics[metric_name] = metric_values[0].get("value", 0)
            
            # Calculate engagement rate
            impressions = metrics.get("impressions", 0)
            likes = metrics.get("likes", 0)
            comments = metrics.get("comments", 0)
            saves = metrics.get("saves", 0)
            shares = metrics.get("shares", 0)
            
            engagement_count = likes + comments + saves + shares
            engagement_rate = (engagement_count / impressions * 100) if impressions > 0 else 0
            
            processed_metrics = {
                "post_id": post_id,
                "impressions_count": impressions,
                "reach_count": metrics.get("reach", 0),
                "likes_count": likes,
                "comments_count": comments,
                "saves_count": saves,
                "shares_count": shares,
                "engagement_rate": round(engagement_rate, 2),
                "total_engagement": engagement_count,
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Retrieved Instagram metrics for post {post_id}: {engagement_count} engagements, {engagement_rate:.2f}% rate")
            return processed_metrics
            
        except Exception as e:
            logger.error(f"Failed to get Instagram post metrics: {e}")
            # Return empty metrics on error
            return {
                "post_id": post_id,
                "impressions_count": 0,
                "reach_count": 0,
                "likes_count": 0,
                "comments_count": 0,
                "saves_count": 0,
                "shares_count": 0,
                "engagement_rate": 0.0,
                "retrieved_at": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def validate_connection(self, access_token: str) -> Dict[str, Any]:
        """
        Validate Instagram connection by making a test API call
        
        Args:
            access_token: OAuth access token
            
        Returns:
            Dictionary containing validation results
        """
        try:
            # Test connection by getting user info
            user_info = self.get_user_info(access_token)
            
            return {
                "is_valid": True,
                "user_id": user_info["id"],
                "username": user_info["username"],
                "display_name": user_info["name"],
                "followers_count": user_info.get("followers_count", 0),
                "following_count": user_info.get("following_count", 0),
                "media_count": user_info.get("media_count", 0),
                "validated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Instagram connection validation failed: {e}")
            return {
                "is_valid": False,
                "error": str(e),
                "validated_at": datetime.utcnow().isoformat()
            }
    
    def validate_post_content(self, caption: str, image_url: str) -> Tuple[bool, str]:
        """
        Validate Instagram post content
        
        Args:
            caption: Post caption to validate
            image_url: Image URL to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not image_url or not image_url.strip():
            return False, "Image URL is required for Instagram posts"
        
        if caption and len(caption) > self.MAX_CAPTION_LENGTH:
            return False, f"Caption too long ({len(caption)}/{self.MAX_CAPTION_LENGTH} characters)"
        
        # Validate image URL format
        if not image_url.lower().startswith(('http://', 'https://')):
            return False, "Image URL must be a valid HTTP/HTTPS URL"
        
        return True, ""
    
    def extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from Instagram caption text"""
        import re
        hashtags = re.findall(r'#\w+', text)
        return [tag.lower() for tag in hashtags]
    
    def extract_mentions(self, text: str) -> List[str]:
        """Extract mentions from Instagram caption text"""
        import re
        mentions = re.findall(r'@\w+', text)
        return [mention.lower() for mention in mentions]
    
    def optimize_for_instagram(self, text: str) -> str:
        """
        Optimize content for Instagram's visual-first platform
        
        Args:
            text: Original content
            
        Returns:
            Instagram-optimized content
        """
        # Instagram allows up to 30 hashtags, but 5-10 is optimal
        hashtags = self.extract_hashtags(text)
        if len(hashtags) > 10:
            # Keep first 10 hashtags
            for hashtag in hashtags[10:]:
                text = text.replace(hashtag, '')
        
        # Add line breaks for better readability
        if len(text) > 300:
            # Split into shorter paragraphs
            sentences = text.split('. ')
            formatted_sentences = []
            current_paragraph = ""
            
            for sentence in sentences:
                if len(current_paragraph + sentence) > 150:
                    if current_paragraph:
                        formatted_sentences.append(current_paragraph.strip() + '.')
                        current_paragraph = sentence
                    else:
                        formatted_sentences.append(sentence + '.')
                else:
                    current_paragraph += sentence + '. ' if not sentence.endswith('.') else sentence + ' '
            
            if current_paragraph:
                formatted_sentences.append(current_paragraph.strip())
            
            text = '\n\n'.join(formatted_sentences)
        
        return text.strip()


# Helper functions for common operations

def create_instagram_client() -> InstagramClient:
    """Create and return an InstagramClient instance"""
    return InstagramClient()

def validate_image_url(url: str) -> bool:
    """
    Validate that an image URL is accessible and valid for Instagram
    
    Args:
        url: Image URL to validate
        
    Returns:
        True if URL is valid and accessible
    """
    try:
        response = requests.head(url, timeout=10)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            return content_type.startswith('image/')
        return False
    except Exception:
        return False

# Global Instagram client instance
instagram_client = InstagramClient()