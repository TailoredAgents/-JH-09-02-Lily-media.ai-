"""
Token refresh service for partner OAuth connections
Handles automatic token refresh for Meta and X connections to maintain health
"""
import logging
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple

from backend.core.config import get_settings
from backend.core.encryption import encrypt_token, decrypt_token
from backend.core.http_client import get_http_client
from backend.db.models import SocialConnection, SocialAudit
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TokenRefreshService:
    """Service for refreshing OAuth tokens to maintain connection health"""
    
    def __init__(self, settings=None):
        """
        Initialize token refresh service
        
        Args:
            settings: Application settings (will get from config if not provided)
        """
        self.settings = settings or get_settings()
        self.meta_graph_version = getattr(self.settings, 'meta_graph_version', 'v18.0')
        self.meta_app_id = getattr(self.settings, 'meta_app_id', '')
        self.meta_app_secret = getattr(self.settings, 'meta_app_secret', '')
        self.x_client_id = getattr(self.settings, 'x_client_id', '')
        self.x_client_secret = getattr(self.settings, 'x_client_secret', '')
        
        self.meta_base_url = f"https://graph.facebook.com/{self.meta_graph_version}"
        self.x_base_url = "https://api.twitter.com/2"
    
    async def refresh_meta_connection(
        self, 
        connection: SocialConnection, 
        db: Session
    ) -> Tuple[bool, Optional[datetime], str]:
        """
        Refresh Meta (Facebook/Instagram) connection tokens
        
        Args:
            connection: SocialConnection instance
            db: Database session
            
        Returns:
            Tuple of (success, new_expiry, status_message)
        """
        try:
            logger.info(f"Starting Meta token refresh for connection {connection.id}")
            
            if not self.meta_app_id or not self.meta_app_secret:
                return False, None, "Meta app credentials not configured"
            
            # Get current user token
            encrypted_user_token = connection.access_tokens.get("access_token")
            if not encrypted_user_token:
                return False, None, "No user access token found"
            
            user_access_token = decrypt_token(encrypted_user_token)
            
            # Step 1: Exchange for long-lived user token if needed
            new_user_token = user_access_token
            new_expires_at = None
            
            # Always attempt to exchange for long-lived token
            try:
                new_user_token, new_expires_at = await self._exchange_for_long_lived_token(user_access_token)
                logger.info(f"Successfully exchanged for long-lived token for connection {connection.id}")
            except Exception as e:
                logger.warning(f"Failed to exchange for long-lived token: {e}, using existing token")
                # Continue with existing token - might still be valid
            
            # Step 2: Validate token via debug endpoint
            is_valid = await self._validate_meta_token(new_user_token)
            if not is_valid:
                return False, None, "User token validation failed"
            
            # Step 3: Re-derive page access token
            page_id = connection.platform_account_id
            try:
                new_page_token = await self._get_page_access_token(page_id, new_user_token)
            except Exception as e:
                logger.error(f"Failed to re-derive page token: {e}")
                return False, None, f"Page token derivation failed: {str(e)}"
            
            # Step 4: Update connection with new tokens
            updates = {
                "access_tokens": {
                    **connection.access_tokens,
                    "access_token": encrypt_token(new_user_token),
                    "page_token": encrypt_token(new_page_token)
                },
                "last_checked_at": self._now_utc(),
                "token_expires_at": new_expires_at
            }
            
            self._update_connection(db, connection, updates)
            
            # Create success audit log
            await self._create_refresh_audit(
                db, connection, "refresh", "success", 
                {
                    "platform": "meta",
                    "old_expiry": connection.token_expires_at.isoformat() if connection.token_expires_at else None,
                    "new_expiry": new_expires_at.isoformat() if new_expires_at else None,
                    "page_id": page_id
                }
            )
            
            success_msg = f"Meta token refresh successful, expires: {new_expires_at}"
            logger.info(f"Meta token refresh completed for connection {connection.id}: {success_msg}")
            return True, new_expires_at, success_msg
            
        except Exception as e:
            error_msg = f"Meta token refresh failed: {str(e)}"
            logger.error(f"Meta token refresh error for connection {connection.id}: {error_msg}")
            
            # Create failure audit log
            try:
                await self._create_refresh_audit(
                    db, connection, "refresh", "failure",
                    {"platform": "meta", "error": str(e)}
                )
            except Exception as audit_error:
                logger.error(f"Failed to create audit log: {audit_error}")
            
            return False, None, error_msg
    
    async def refresh_x_connection(
        self,
        connection: SocialConnection,
        db: Session
    ) -> Tuple[bool, Optional[datetime], str]:
        """
        Refresh X (Twitter) connection tokens using OAuth2 refresh token
        
        Args:
            connection: SocialConnection instance
            db: Database session
            
        Returns:
            Tuple of (success, new_expiry, status_message)
        """
        try:
            logger.info(f"Starting X token refresh for connection {connection.id}")
            
            if not self.x_client_id or not self.x_client_secret:
                return False, None, "X client credentials not configured"
            
            # Get current refresh token
            encrypted_refresh_token = connection.access_tokens.get("refresh_token")
            if not encrypted_refresh_token:
                return False, None, "No refresh token found"
            
            refresh_token = decrypt_token(encrypted_refresh_token)
            
            # Refresh the tokens via X OAuth2
            try:
                new_tokens = await self._refresh_x_oauth_tokens(refresh_token)
            except Exception as e:
                logger.error(f"X OAuth2 token refresh failed: {e}")
                return False, None, f"Token refresh API call failed: {str(e)}"
            
            # Calculate new expiry
            expires_in = new_tokens.get("expires_in", 7200)  # Default 2 hours
            new_expires_at = self._now_utc() + timedelta(seconds=expires_in)
            
            # Update connection with new tokens
            updates = {
                "access_tokens": {
                    **connection.access_tokens,
                    "access_token": encrypt_token(new_tokens["access_token"]),
                    "refresh_token": encrypt_token(new_tokens["refresh_token"])
                },
                "last_checked_at": self._now_utc(),
                "token_expires_at": new_expires_at
            }
            
            self._update_connection(db, connection, updates)
            
            # Create success audit log
            await self._create_refresh_audit(
                db, connection, "refresh", "success",
                {
                    "platform": "x",
                    "old_expiry": connection.token_expires_at.isoformat() if connection.token_expires_at else None,
                    "new_expiry": new_expires_at.isoformat(),
                    "expires_in_seconds": expires_in
                }
            )
            
            success_msg = f"X token refresh successful, expires: {new_expires_at}"
            logger.info(f"X token refresh completed for connection {connection.id}: {success_msg}")
            return True, new_expires_at, success_msg
            
        except Exception as e:
            error_msg = f"X token refresh failed: {str(e)}"
            logger.error(f"X token refresh error for connection {connection.id}: {error_msg}")
            
            # Create failure audit log
            try:
                await self._create_refresh_audit(
                    db, connection, "refresh", "failure",
                    {"platform": "x", "error": str(e)}
                )
            except Exception as audit_error:
                logger.error(f"Failed to create audit log: {audit_error}")
            
            return False, None, error_msg
    
    async def _exchange_for_long_lived_token(self, short_token: str) -> Tuple[str, Optional[datetime]]:
        """Exchange short-lived token for long-lived token"""
        url = f"{self.meta_base_url}/oauth/access_token"
        
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.meta_app_id,
            "client_secret": self.meta_app_secret,
            "fb_exchange_token": short_token
        }
        
        client = await get_http_client()
        response = await client.get(url, params=params)
        response.raise_for_status()
            
            data = response.json()
            
            long_lived_token = data.get("access_token")
            if not long_lived_token:
                raise ValueError("No access_token in response")
            
            # Calculate expiry if provided
            expires_in = data.get("expires_in")
            expires_at = None
            if expires_in:
                expires_at = self._now_utc() + timedelta(seconds=int(expires_in))
            
            return long_lived_token, expires_at
    
    async def _validate_meta_token(self, token: str) -> bool:
        """Validate Meta token via debug endpoint"""
        try:
            url = f"{self.meta_base_url}/debug_token"
            params = {
                "input_token": token,
                "access_token": f"{self.meta_app_id}|{self.meta_app_secret}"
            }
            
            client = await get_http_client()
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            token_data = data.get("data", {})
                
                return token_data.get("is_valid", False)
                
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False
    
    async def _get_page_access_token(self, page_id: str, user_token: str) -> str:
        """Get page access token using user token"""
        url = f"{self.meta_base_url}/{page_id}"
        
        params = {
            "fields": "access_token",
            "access_token": user_token
        }
        
        client = await get_http_client()
        response = await client.get(url, params=params)
        response.raise_for_status()
            
            data = response.json()
            page_token = data.get("access_token")
            
            if not page_token:
                raise ValueError("No page access_token in response")
            
            return page_token
    
    async def _refresh_x_oauth_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh X OAuth2 tokens"""
        url = f"{self.x_base_url}/oauth2/token"
        
        # Create Basic auth header
        auth_string = f"{self.x_client_id}:{self.x_client_secret}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        client = await get_http_client()
        response = await client.post(url, headers=headers, data=data)
        response.raise_for_status()
            
            token_data = response.json()
            
            required_fields = ["access_token", "refresh_token"]
            for field in required_fields:
                if field not in token_data:
                    raise ValueError(f"Missing {field} in token response")
            
            return token_data
    
    def _now_utc(self) -> datetime:
        """Get current UTC datetime"""
        return datetime.now(timezone.utc)
    
    def _update_connection(self, db: Session, connection: SocialConnection, updates: Dict[str, Any]) -> None:
        """Update connection with new data"""
        for field, value in updates.items():
            setattr(connection, field, value)
        
        db.commit()
        db.refresh(connection)
    
    async def _create_refresh_audit(
        self,
        db: Session,
        connection: SocialConnection,
        action: str,
        status: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Create audit log for token refresh operation"""
        try:
            audit = SocialAudit(
                organization_id=connection.organization_id,
                connection_id=connection.id,
                action=action,
                platform=connection.platform,
                user_id=None,  # System operation
                status=status,
                audit_metadata=metadata
            )
            db.add(audit)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to create refresh audit log: {e}")
            # Don't raise - audit logging shouldn't break the main operation


# Singleton instance
_token_refresh_service = None


def get_token_refresh_service(settings=None) -> TokenRefreshService:
    """
    Get token refresh service instance
    
    Args:
        settings: Application settings (optional)
        
    Returns:
        TokenRefreshService instance
    """
    global _token_refresh_service
    
    if _token_refresh_service is None:
        _token_refresh_service = TokenRefreshService(settings)
    
    return _token_refresh_service