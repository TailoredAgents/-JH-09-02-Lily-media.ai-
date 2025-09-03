"""
X (Twitter) connection service for partner OAuth flows
Handles X API user verification and connection data
"""
import logging
from typing import Dict, Any, Optional
import httpx

from backend.core.service_factory import register_service, get_service

logger = logging.getLogger(__name__)


class XConnectionService:
    """Service for X API user operations"""
    
    def __init__(self):
        self.base_url = "https://api.twitter.com/2"
    
    async def get_me(self, tokens: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get authenticated user's profile information from X API
        
        Args:
            tokens: Dictionary containing access_token and other OAuth tokens
            
        Returns:
            Dictionary with user ID, username, and name
            
        Raises:
            ValueError: If API call fails or tokens are invalid
            httpx.HTTPStatusError: If X API returns error
        """
        access_token = tokens.get("access_token")
        if not access_token:
            raise ValueError("Access token is required")
        
        url = f"{self.base_url}/users/me"
        params = {
            "user.fields": "id,username,name,public_metrics,verified,created_at"
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "AI-Social-Media-Agent/1.0"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                user_data = data.get("data", {})
                
                if not user_data:
                    raise ValueError("No user data returned from X API")
                
                user_id = user_data.get("id")
                username = user_data.get("username")
                name = user_data.get("name")
                
                if not user_id or not username:
                    raise ValueError("Invalid user data: missing ID or username")
                
                result = {
                    "id": user_id,
                    "username": username,
                    "name": name or username,
                    "verified": user_data.get("verified", False),
                    "created_at": user_data.get("created_at"),
                    "public_metrics": user_data.get("public_metrics", {})
                }
                
                logger.info(f"Retrieved X user profile: @{username} (ID: {user_id})")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"X API error getting user profile: {e.response.status_code} - {e.response.text}")
            
            if e.response.status_code == 401:
                raise ValueError("Invalid or expired X access token")
            elif e.response.status_code == 403:
                raise ValueError("Insufficient permissions to access user profile")
            elif e.response.status_code == 429:
                raise ValueError("X API rate limit exceeded - please try again later")
            else:
                error_data = {}
                try:
                    error_data = e.response.json()
                except:
                    pass
                
                error_detail = error_data.get("detail", f"X API error: {e.response.status_code}")
                raise ValueError(f"X API error: {error_detail}")
                
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to get X user profile: {e}")
            raise ValueError(f"Failed to retrieve user profile: {str(e)}")
    
    async def validate_tokens(self, tokens: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate X access tokens and return token info
        
        Args:
            tokens: Dictionary containing access tokens
            
        Returns:
            Dictionary with validation results and token metadata
        """
        try:
            user_data = await self.get_me(tokens)
            
            return {
                "valid": True,
                "user_id": user_data["id"],
                "username": user_data["username"],
                "name": user_data["name"],
                "scopes": self._extract_scopes(tokens),
                "expires_at": tokens.get("expires_at")
            }
            
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    def _extract_scopes(self, tokens: Dict[str, Any]) -> list:
        """
        Extract granted scopes from token response
        
        Args:
            tokens: OAuth token response
            
        Returns:
            List of granted scopes
        """
        scope_string = tokens.get("scope", "")
        if isinstance(scope_string, str) and scope_string:
            return scope_string.split()
        elif isinstance(scope_string, list):
            return scope_string
        else:
            # Fallback to expected scopes if not provided
            return ["tweet.read", "tweet.write", "users.read", "offline.access"]
    
    async def get_user_context(self, tokens: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get additional context for user connection
        
        Args:
            tokens: OAuth tokens
            
        Returns:
            Dictionary with user context and metadata
        """
        try:
            user_data = await self.get_me(tokens)
            
            # Prepare metadata for storage
            metadata = {
                "since_id": None,  # For timeline tracking
                "verified": user_data.get("verified", False),
                "created_at": user_data.get("created_at"),
                "followers_count": user_data.get("public_metrics", {}).get("followers_count", 0),
                "following_count": user_data.get("public_metrics", {}).get("following_count", 0),
                "tweet_count": user_data.get("public_metrics", {}).get("tweet_count", 0),
                "last_connected": None  # Will be set when connection is created
            }
            
            return {
                "user_id": user_data["id"],
                "username": user_data["username"],
                "display_name": user_data["name"],
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to get user context: {e}")
            raise ValueError(f"Failed to get user context: {str(e)}")


# Register service with factory
register_service('x_connection_service', XConnectionService, scope='singleton')

def get_x_connection_service() -> XConnectionService:
    """Get X connection service instance from service factory"""
    return get_service('x_connection_service')