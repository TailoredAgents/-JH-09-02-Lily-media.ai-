"""
Meta page token service for partner OAuth flows
Handles Facebook Page discovery and page access token exchange
"""
import logging
from typing import Dict, List, Any, Optional
import httpx

from backend.core.config import get_settings
from backend.core.service_factory import register_service, get_service

logger = logging.getLogger(__name__)


class MetaPageTokenService:
    """Service for Meta Graph API page token operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.graph_version = self.settings.meta_graph_version
        self.base_url = f"https://graph.facebook.com/{self.graph_version}"
    
    async def list_pages_with_instagram(self, user_access_token: str) -> List[Dict[str, Any]]:
        """
        List Facebook Pages with Instagram Business account linking
        
        Args:
            user_access_token: User's access token from OAuth flow
            
        Returns:
            List of page dictionaries with computed flags
            
        Raises:
            ValueError: If API call fails or user has no pages
            httpx.HTTPStatusError: If Graph API returns error
        """
        if not user_access_token:
            raise ValueError("User access token is required")
        
        url = f"{self.base_url}/me/accounts"
        params = {
            "fields": "id,name,instagram_business_account,access_token",
            "access_token": user_access_token
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                pages_data = data.get("data", [])
                
                if not pages_data:
                    logger.warning("User has no Facebook Pages")
                    return []
                
                # Transform pages data with computed flags
                pages = []
                for page_data in pages_data:
                    page = {
                        "id": page_data["id"],
                        "name": page_data["name"],
                        "has_instagram": bool(page_data.get("instagram_business_account")),
                        "token_available": bool(page_data.get("access_token")),
                        "instagram_business_account": None
                    }
                    
                    # Include Instagram Business account details if available
                    ig_account = page_data.get("instagram_business_account")
                    if ig_account:
                        # Get Instagram username if available
                        ig_username = await self._get_instagram_username(
                            ig_account["id"], 
                            page_data.get("access_token")
                        )
                        
                        page["instagram_business_account"] = {
                            "id": ig_account["id"],
                            "username": ig_username
                        }
                    
                    pages.append(page)
                
                logger.info(f"Retrieved {len(pages)} Facebook Pages for user")
                return pages
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Graph API error listing pages: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 403:
                raise ValueError("Insufficient permissions to access Facebook Pages")
            elif e.response.status_code == 401:
                raise ValueError("Invalid or expired access token")
            else:
                raise ValueError(f"Facebook API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Failed to list Facebook Pages: {e}")
            raise ValueError(f"Failed to retrieve Facebook Pages: {str(e)}")
    
    async def _get_instagram_username(self, instagram_id: str, page_token: str) -> Optional[str]:
        """
        Get Instagram username for a Business account
        
        Args:
            instagram_id: Instagram Business account ID
            page_token: Page access token
            
        Returns:
            Instagram username or None if not available
        """
        if not page_token:
            return None
            
        try:
            url = f"{self.base_url}/{instagram_id}"
            params = {
                "fields": "username",
                "access_token": page_token
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                return data.get("username")
                
        except Exception as e:
            logger.warning(f"Failed to get Instagram username for {instagram_id}: {e}")
            return None
    
    async def exchange_for_page_token(self, user_access_token: str, page_id: str) -> Dict[str, Any]:
        """
        Exchange user token for page-specific access token
        
        Args:
            user_access_token: User's access token from OAuth flow
            page_id: Facebook Page ID to get token for
            
        Returns:
            Dictionary with page token and metadata
            
        Raises:
            ValueError: If exchange fails or user lacks permissions
        """
        if not user_access_token:
            raise ValueError("User access token is required")
        if not page_id:
            raise ValueError("Page ID is required")
        
        url = f"{self.base_url}/{page_id}"
        params = {
            "fields": "access_token,name",
            "access_token": user_access_token
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                page_token = data.get("access_token")
                page_name = data.get("name")
                
                if not page_token:
                    raise ValueError("Unable to obtain page access token - you may not be a Page admin")
                
                logger.info(f"Successfully exchanged for page token: {page_id}")
                
                return {
                    "page_access_token": page_token,
                    "page_name": page_name,
                    "page_id": page_id
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Graph API error getting page token: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 403:
                raise ValueError("You don't have admin access to this Facebook Page")
            elif e.response.status_code == 404:
                raise ValueError("Facebook Page not found or not accessible")
            elif e.response.status_code == 401:
                raise ValueError("Invalid or expired access token")
            else:
                raise ValueError(f"Facebook API error: {e.response.status_code}")
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to exchange for page token: {e}")
            raise ValueError(f"Failed to get page access token: {str(e)}")
    
    async def get_instagram_username(self, instagram_id: str, page_access_token: str) -> Optional[str]:
        """
        Get Instagram username for a Business account using page token
        
        Args:
            instagram_id: Instagram Business account ID
            page_access_token: Page access token
            
        Returns:
            Instagram username or None if not available
        """
        if not page_access_token or not instagram_id:
            return None
            
        try:
            url = f"{self.base_url}/{instagram_id}"
            params = {
                "fields": "username",
                "access_token": page_access_token
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                return data.get("username")
                
        except Exception as e:
            logger.warning(f"Failed to get Instagram username for {instagram_id}: {e}")
            return None
    
    async def validate_page_permissions(self, page_token: str, page_id: str) -> Dict[str, Any]:
        """
        Validate page token and get page permissions/info
        
        Args:
            page_token: Page access token to validate
            page_id: Facebook Page ID
            
        Returns:
            Dictionary with page info and permissions
        """
        url = f"{self.base_url}/{page_id}"
        params = {
            "fields": "id,name,permissions",
            "access_token": page_token
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                return {
                    "page_id": data.get("id"),
                    "page_name": data.get("name"),
                    "permissions": data.get("permissions", {}),
                    "valid": True
                }
                
        except Exception as e:
            logger.error(f"Failed to validate page token: {e}")
            return {
                "valid": False,
                "error": str(e)
            }


# Register service with factory
register_service('meta_page_token_service', MetaPageTokenService, scope='singleton')

def get_meta_page_service() -> MetaPageTokenService:
    """Get Meta page token service instance from service factory"""
    return get_service('meta_page_token_service')