"""
OAuth Token Service - Centralized secure token management
Provides production-ready token storage, rotation, and lifecycle management
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.db.models import OAuthToken, User, Organization
from backend.core.encryption import get_encryption, EncryptionError
from backend.db.database import get_db

logger = logging.getLogger(__name__)


class OAuthTokenError(Exception):
    """Base exception for OAuth token operations"""
    pass


class TokenExpiredError(OAuthTokenError):
    """Token has expired and needs refresh"""
    pass


class TokenNotFoundError(OAuthTokenError):
    """Token not found in storage"""
    pass


class OAuthTokenService:
    """
    Centralized OAuth token management service with enhanced security
    
    Features:
    - Versioned Fernet encryption with key rotation support
    - Automatic token expiration handling
    - Comprehensive audit logging
    - Multi-platform token support
    - Token lifecycle management
    """
    
    def __init__(self, db: Session = None):
        """
        Initialize OAuth token service
        
        Args:
            db: Database session (optional, will create if not provided)
        """
        self.db = db or next(get_db())
        self.encryption = get_encryption()
    
    def store_token(
        self,
        organization_id: int,
        platform: str,
        platform_account_id: str,
        token_type: str,
        token_value: str,
        user_id: int,
        token_name: str = None,
        expires_at: datetime = None,
        scopes: List[str] = None,
        token_metadata: Dict[str, Any] = None,
        connection_reference: str = None
    ) -> OAuthToken:
        """
        Store a new OAuth token with encryption
        
        Args:
            organization_id: Organization ID
            platform: Platform identifier (meta, x, tiktok, linkedin)
            platform_account_id: External platform account ID
            token_type: Type of token (access_token, refresh_token, page_token)
            token_value: Raw token value to encrypt
            user_id: ID of user creating the token
            token_name: Human-readable token name
            expires_at: Token expiration timestamp
            scopes: Granted OAuth scopes
            token_metadata: Platform-specific metadata
            connection_reference: Reference to SocialConnection if applicable
            
        Returns:
            Created OAuthToken instance
            
        Raises:
            OAuthTokenError: If token storage fails
        """
        try:
            # Generate token name if not provided
            if not token_name:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                token_name = f"{platform}_{token_type}_{timestamp}"
            
            # Check for existing token and revoke if necessary
            existing = self.get_token(
                organization_id=organization_id,
                platform=platform,
                platform_account_id=platform_account_id,
                token_type=token_type,
                include_expired=True
            )
            
            if existing and existing.is_valid:
                logger.info(f"Revoking existing {token_type} for {platform}:{platform_account_id}")
                self.revoke_token(existing.id, reason="replaced_by_new_token")
            
            # Encrypt the token
            encrypted_token = self.encryption.encrypt(token_value)
            
            # Create new token record
            oauth_token = OAuthToken(
                organization_id=organization_id,
                token_name=token_name,
                token_type=token_type,
                platform=platform,
                platform_account_id=platform_account_id,
                connection_reference=connection_reference,
                encrypted_token=encrypted_token,
                encryption_version=self.encryption.current_version,
                encryption_key_id=self.encryption.default_kid,
                issued_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                is_valid=True,
                scopes=scopes or [],
                token_metadata=token_metadata or {},
                created_by_user_id=user_id,
                rotation_count=0
            )
            
            self.db.add(oauth_token)
            self.db.commit()
            self.db.refresh(oauth_token)
            
            logger.info(f"Stored new {token_type} for {platform}:{platform_account_id} (ID: {oauth_token.id})")
            return oauth_token
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to store OAuth token: {e}")
            raise OAuthTokenError(f"Token storage failed: {e}")
    
    def get_token(
        self,
        organization_id: int,
        platform: str,
        platform_account_id: str,
        token_type: str,
        include_expired: bool = False
    ) -> Optional[OAuthToken]:
        """
        Retrieve an OAuth token by identifiers
        
        Args:
            organization_id: Organization ID
            platform: Platform identifier
            platform_account_id: External platform account ID
            token_type: Type of token to retrieve
            include_expired: Whether to include expired tokens
            
        Returns:
            OAuthToken instance or None if not found
        """
        try:
            query = self.db.query(OAuthToken).filter(
                and_(
                    OAuthToken.organization_id == organization_id,
                    OAuthToken.platform == platform,
                    OAuthToken.platform_account_id == platform_account_id,
                    OAuthToken.token_type == token_type,
                    OAuthToken.is_valid == True
                )
            )
            
            if not include_expired:
                # Only include non-expired tokens
                now = datetime.now(timezone.utc)
                query = query.filter(
                    or_(
                        OAuthToken.expires_at.is_(None),
                        OAuthToken.expires_at > now
                    )
                )
            
            return query.first()
            
        except Exception as e:
            logger.error(f"Failed to get OAuth token: {e}")
            return None
    
    def get_decrypted_token(
        self,
        organization_id: int,
        platform: str,
        platform_account_id: str,
        token_type: str
    ) -> Optional[str]:
        """
        Retrieve and decrypt an OAuth token
        
        Args:
            organization_id: Organization ID
            platform: Platform identifier
            platform_account_id: External platform account ID
            token_type: Type of token to retrieve
            
        Returns:
            Decrypted token string or None if not found/expired
            
        Raises:
            TokenExpiredError: If token exists but is expired
            OAuthTokenError: If decryption fails
        """
        try:
            token_record = self.get_token(
                organization_id=organization_id,
                platform=platform,
                platform_account_id=platform_account_id,
                token_type=token_type,
                include_expired=True
            )
            
            if not token_record:
                return None
            
            # Check expiration
            if token_record.expires_at and token_record.expires_at <= datetime.now(timezone.utc):
                raise TokenExpiredError(f"Token {token_record.id} has expired")
            
            # Decrypt token
            decrypted = self.encryption.decrypt(token_record.encrypted_token)
            
            # Update last validated timestamp
            token_record.last_validated_at = datetime.now(timezone.utc)
            self.db.commit()
            
            return decrypted
            
        except TokenExpiredError:
            raise
        except EncryptionError as e:
            logger.error(f"Token decryption failed: {e}")
            raise OAuthTokenError(f"Token decryption failed: {e}")
        except Exception as e:
            logger.error(f"Failed to get decrypted token: {e}")
            raise OAuthTokenError(f"Token retrieval failed: {e}")
    
    def rotate_token(
        self,
        token_id: str,
        new_token_value: str,
        new_expires_at: datetime = None,
        rotation_reason: str = "periodic_rotation"
    ) -> OAuthToken:
        """
        Rotate an existing token with a new value
        
        Args:
            token_id: UUID of token to rotate
            new_token_value: New token value
            new_expires_at: New expiration timestamp
            rotation_reason: Reason for rotation (for audit)
            
        Returns:
            Updated OAuthToken instance
            
        Raises:
            TokenNotFoundError: If token doesn't exist
            OAuthTokenError: If rotation fails
        """
        try:
            token_record = self.db.query(OAuthToken).filter(
                OAuthToken.id == token_id
            ).first()
            
            if not token_record:
                raise TokenNotFoundError(f"Token {token_id} not found")
            
            # Encrypt new token value
            encrypted_new_token = self.encryption.encrypt(new_token_value)
            
            # Update token record
            token_record.encrypted_token = encrypted_new_token
            token_record.expires_at = new_expires_at
            token_record.last_rotation_at = datetime.now(timezone.utc)
            token_record.rotation_count += 1
            token_record.updated_at = datetime.now(timezone.utc)
            
            # Update encryption metadata if key rotated
            token_record.encryption_version = self.encryption.current_version
            token_record.encryption_key_id = self.encryption.default_kid
            
            self.db.commit()
            self.db.refresh(token_record)
            
            logger.info(f"Rotated token {token_id} (rotation #{token_record.rotation_count}, reason: {rotation_reason})")
            return token_record
            
        except TokenNotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Token rotation failed: {e}")
            raise OAuthTokenError(f"Token rotation failed: {e}")
    
    def revoke_token(
        self,
        token_id: str,
        reason: str = "manual_revocation"
    ) -> bool:
        """
        Revoke an OAuth token
        
        Args:
            token_id: UUID of token to revoke
            reason: Reason for revocation
            
        Returns:
            True if token was revoked, False if not found
            
        Raises:
            OAuthTokenError: If revocation fails
        """
        try:
            token_record = self.db.query(OAuthToken).filter(
                OAuthToken.id == token_id
            ).first()
            
            if not token_record:
                return False
            
            # Mark as revoked
            token_record.is_valid = False
            token_record.revoked_at = datetime.now(timezone.utc)
            token_record.revoked_reason = reason
            token_record.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            
            logger.info(f"Revoked token {token_id} (reason: {reason})")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Token revocation failed: {e}")
            raise OAuthTokenError(f"Token revocation failed: {e}")
    
    def list_tokens_for_organization(
        self,
        organization_id: int,
        platform: str = None,
        include_expired: bool = False,
        include_revoked: bool = False
    ) -> List[OAuthToken]:
        """
        List OAuth tokens for an organization
        
        Args:
            organization_id: Organization ID
            platform: Filter by platform (optional)
            include_expired: Include expired tokens
            include_revoked: Include revoked tokens
            
        Returns:
            List of OAuthToken instances
        """
        try:
            query = self.db.query(OAuthToken).filter(
                OAuthToken.organization_id == organization_id
            )
            
            if platform:
                query = query.filter(OAuthToken.platform == platform)
            
            if not include_revoked:
                query = query.filter(OAuthToken.is_valid == True)
            
            if not include_expired:
                now = datetime.now(timezone.utc)
                query = query.filter(
                    or_(
                        OAuthToken.expires_at.is_(None),
                        OAuthToken.expires_at > now
                    )
                )
            
            return query.order_by(OAuthToken.created_at.desc()).all()
            
        except Exception as e:
            logger.error(f"Failed to list tokens: {e}")
            return []
    
    def cleanup_expired_tokens(self, older_than_days: int = 30) -> int:
        """
        Clean up expired and revoked tokens older than specified days
        
        Args:
            older_than_days: Remove tokens older than this many days
            
        Returns:
            Number of tokens cleaned up
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            
            # Find expired/revoked tokens older than cutoff
            tokens_to_delete = self.db.query(OAuthToken).filter(
                and_(
                    or_(
                        OAuthToken.is_valid == False,
                        OAuthToken.expires_at < datetime.now(timezone.utc)
                    ),
                    OAuthToken.created_at < cutoff_date
                )
            )
            
            count = tokens_to_delete.count()
            tokens_to_delete.delete()
            self.db.commit()
            
            logger.info(f"Cleaned up {count} expired/revoked OAuth tokens older than {older_than_days} days")
            return count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Token cleanup failed: {e}")
            return 0
    
    def get_token_metadata(self, token_id: str) -> Dict[str, Any]:
        """
        Get token metadata without decrypting the token
        
        Args:
            token_id: UUID of token
            
        Returns:
            Dictionary with token metadata
        """
        try:
            token_record = self.db.query(OAuthToken).filter(
                OAuthToken.id == token_id
            ).first()
            
            if not token_record:
                return {}
            
            # Get encryption envelope info without decrypting
            envelope_info = self.encryption.get_envelope_info(token_record.encrypted_token)
            
            return {
                "id": str(token_record.id),
                "token_name": token_record.token_name,
                "token_type": token_record.token_type,
                "platform": token_record.platform,
                "platform_account_id": token_record.platform_account_id,
                "is_valid": token_record.is_valid,
                "issued_at": token_record.issued_at.isoformat() if token_record.issued_at else None,
                "expires_at": token_record.expires_at.isoformat() if token_record.expires_at else None,
                "last_validated_at": token_record.last_validated_at.isoformat() if token_record.last_validated_at else None,
                "last_rotation_at": token_record.last_rotation_at.isoformat() if token_record.last_rotation_at else None,
                "rotation_count": token_record.rotation_count,
                "encryption_version": token_record.encryption_version,
                "encryption_key_id": token_record.encryption_key_id,
                "envelope_info": envelope_info,
                "scopes": token_record.scopes,
                "created_at": token_record.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get token metadata: {e}")
            return {}


# Singleton service instance
_oauth_token_service = None


def get_oauth_token_service(db: Session = None) -> OAuthTokenService:
    """Get singleton OAuth token service instance"""
    global _oauth_token_service
    if _oauth_token_service is None or db is not None:
        _oauth_token_service = OAuthTokenService(db)
    return _oauth_token_service