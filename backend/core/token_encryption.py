"""
Secure Token Encryption Service
Handles encryption/decryption of OAuth tokens and sensitive data at rest
"""
import os
import base64
import logging
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import json

logger = logging.getLogger(__name__)

class TokenEncryptionService:
    """
    Secure token encryption service using Fernet (AES 128 with HMAC authentication)
    
    Features:
    - Symmetric encryption of OAuth tokens
    - Key derivation from master secret
    - Safe token serialization/deserialization
    - Audit logging of encryption operations
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service
        
        Args:
            master_key: Master encryption key. If None, reads from environment.
        """
        self._master_key = master_key or os.getenv("ENCRYPTION_KEY") or os.getenv("SECRET_KEY")
        
        if not self._master_key:
            raise ValueError("No encryption key provided. Set ENCRYPTION_KEY or SECRET_KEY environment variable.")
        
        # Derive encryption key from master key
        self._fernet = self._create_fernet_key(self._master_key)
        
        logger.info("Token encryption service initialized")
    
    def _create_fernet_key(self, master_key: str) -> Fernet:
        """Create Fernet encryption key from master key"""
        try:
            # SECURITY: Use environment-specific salt to prevent cross-deployment attacks
            salt_env = os.getenv("TOKEN_ENCRYPTION_SALT")
            if salt_env:
                salt = salt_env.encode('utf-8')
            else:
                # Fallback: generate salt from master key to ensure uniqueness per deployment
                import hashlib
                salt = hashlib.sha256(f"token_salt_{self._master_key[:16]}".encode()).digest()[:16]
                logger.warning("TOKEN_ENCRYPTION_SALT not set, using derived salt. Set TOKEN_ENCRYPTION_SALT for better security.")
            
            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,  # OWASP recommended minimum
                backend=default_backend()
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
            return Fernet(key)
            
        except Exception as e:
            logger.error(f"Failed to create encryption key: {e}")
            raise
    
    def encrypt_token(self, token: str) -> str:
        """
        Encrypt an OAuth token for database storage
        
        Args:
            token: Plain text token to encrypt
            
        Returns:
            Base64-encoded encrypted token
            
        Raises:
            ValueError: If token is invalid
            Exception: If encryption fails
        """
        if not token or not isinstance(token, str):
            raise ValueError("Token must be a non-empty string")
        
        try:
            # Encrypt the token
            encrypted_bytes = self._fernet.encrypt(token.encode('utf-8'))
            
            # Return base64 encoded string for database storage
            encrypted_token = base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
            
            logger.debug(f"Successfully encrypted token (length: {len(token)})")
            return encrypted_token
            
        except Exception as e:
            logger.error(f"Token encryption failed: {e}")
            raise
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt an OAuth token from database storage
        
        Args:
            encrypted_token: Base64-encoded encrypted token
            
        Returns:
            Plain text token
            
        Raises:
            ValueError: If encrypted token is invalid
            Exception: If decryption fails
        """
        if not encrypted_token or not isinstance(encrypted_token, str):
            raise ValueError("Encrypted token must be a non-empty string")
        
        try:
            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode('utf-8'))
            
            # Decrypt the token
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            token = decrypted_bytes.decode('utf-8')
            
            logger.debug("Successfully decrypted token")
            return token
            
        except Exception as e:
            logger.error(f"Token decryption failed: {e}")
            raise
    
    def encrypt_token_data(self, token_data: Dict[str, Any]) -> str:
        """
        Encrypt complete OAuth token data structure
        
        Args:
            token_data: Dictionary containing token data
            
        Returns:
            Base64-encoded encrypted JSON string
        """
        if not token_data or not isinstance(token_data, dict):
            raise ValueError("Token data must be a non-empty dictionary")
        
        try:
            # Serialize to JSON
            json_data = json.dumps(token_data, sort_keys=True)
            
            # Encrypt the JSON string
            encrypted_bytes = self._fernet.encrypt(json_data.encode('utf-8'))
            
            # Return base64 encoded string
            encrypted_data = base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
            
            logger.debug(f"Successfully encrypted token data with {len(token_data)} fields")
            return encrypted_data
            
        except Exception as e:
            logger.error(f"Token data encryption failed: {e}")
            raise
    
    def decrypt_token_data(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt complete OAuth token data structure
        
        Args:
            encrypted_data: Base64-encoded encrypted JSON string
            
        Returns:
            Dictionary containing token data
        """
        if not encrypted_data or not isinstance(encrypted_data, str):
            raise ValueError("Encrypted data must be a non-empty string")
        
        try:
            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            
            # Decrypt the data
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            json_data = decrypted_bytes.decode('utf-8')
            
            # Parse JSON
            token_data = json.loads(json_data)
            
            logger.debug(f"Successfully decrypted token data with {len(token_data)} fields")
            return token_data
            
        except Exception as e:
            logger.error(f"Token data decryption failed: {e}")
            raise
    
    def is_token_valid(self, encrypted_token: str) -> bool:
        """
        Check if an encrypted token can be successfully decrypted
        
        Args:
            encrypted_token: Base64-encoded encrypted token
            
        Returns:
            True if token can be decrypted, False otherwise
        """
        try:
            self.decrypt_token(encrypted_token)
            return True
        except Exception:
            return False
    
    def rotate_encryption_key(self, new_master_key: str, old_tokens: list) -> list:
        """
        Rotate encryption key and re-encrypt existing tokens
        
        Args:
            new_master_key: New master key for encryption
            old_tokens: List of encrypted tokens to re-encrypt
            
        Returns:
            List of tokens encrypted with new key
            
        Note: This is an advanced operation for key rotation scenarios
        """
        if not new_master_key:
            raise ValueError("New master key is required")
        
        try:
            # Store current Fernet instance
            old_fernet = self._fernet
            
            # Create new Fernet instance with new key
            new_fernet = self._create_fernet_key(new_master_key)
            
            # Re-encrypt all tokens
            re_encrypted_tokens = []
            
            for encrypted_token in old_tokens:
                try:
                    # Decrypt with old key
                    encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode('utf-8'))
                    decrypted_bytes = old_fernet.decrypt(encrypted_bytes)
                    
                    # Re-encrypt with new key
                    new_encrypted_bytes = new_fernet.encrypt(decrypted_bytes)
                    new_encrypted_token = base64.urlsafe_b64encode(new_encrypted_bytes).decode('utf-8')
                    
                    re_encrypted_tokens.append(new_encrypted_token)
                    
                except Exception as e:
                    logger.error(f"Failed to rotate token: {e}")
                    # Could not re-encrypt this token, mark it as invalid
                    re_encrypted_tokens.append(None)
            
            # Update to new Fernet instance
            self._fernet = new_fernet
            self._master_key = new_master_key
            
            logger.info(f"Successfully rotated encryption key for {len(re_encrypted_tokens)} tokens")
            return re_encrypted_tokens
            
        except Exception as e:
            logger.error(f"Encryption key rotation failed: {e}")
            raise


class SocialTokenManager:
    """
    High-level manager for social media platform tokens
    
    Provides convenient methods for storing and retrieving platform tokens
    with proper encryption and validation.
    """
    
    def __init__(self, encryption_service: Optional[TokenEncryptionService] = None):
        """
        Initialize token manager
        
        Args:
            encryption_service: Optional custom encryption service
        """
        self.encryption_service = encryption_service or TokenEncryptionService()
        logger.info("Social token manager initialized")
    
    def store_oauth_tokens(self, platform: str, token_data: Dict[str, Any]) -> str:
        """
        Store OAuth tokens for a social media platform
        
        Args:
            platform: Platform name (twitter, linkedin, instagram)
            token_data: OAuth token response data
            
        Returns:
            Encrypted token data string for database storage
        """
        if not platform or not token_data:
            raise ValueError("Platform and token data are required")
        
        # Add metadata to token data
        enhanced_token_data = {
            "platform": platform,
            "stored_at": str(int(time.time())),
            **token_data
        }
        
        # Remove sensitive data from logs
        safe_data = {k: v for k, v in enhanced_token_data.items() 
                    if k not in ['access_token', 'refresh_token', 'client_secret']}
        logger.info(f"Storing OAuth tokens for {platform}: {safe_data}")
        
        return self.encryption_service.encrypt_token_data(enhanced_token_data)
    
    def retrieve_oauth_tokens(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Retrieve and decrypt OAuth tokens
        
        Args:
            encrypted_data: Encrypted token data from database
            
        Returns:
            Decrypted token data dictionary
        """
        if not encrypted_data:
            raise ValueError("Encrypted data is required")
        
        token_data = self.encryption_service.decrypt_token_data(encrypted_data)
        
        platform = token_data.get("platform", "unknown")
        logger.debug(f"Retrieved OAuth tokens for {platform}")
        
        return token_data
    
    def is_token_expired(self, token_data: Dict[str, Any]) -> bool:
        """
        Check if OAuth token is expired
        
        Args:
            token_data: Decrypted token data
            
        Returns:
            True if token is expired, False otherwise
        """
        import time
        
        expires_at = token_data.get("expires_at")
        if not expires_at:
            # No expiration info, assume valid
            return False
        
        try:
            expires_timestamp = float(expires_at)
            return time.time() >= expires_timestamp
        except (ValueError, TypeError):
            # Invalid expiration data, assume expired for safety
            return True
    
    def get_access_token(self, encrypted_data: str) -> Optional[str]:
        """
        Get the access token from encrypted OAuth data
        
        Args:
            encrypted_data: Encrypted token data from database
            
        Returns:
            Access token string or None if invalid/expired
        """
        try:
            token_data = self.retrieve_oauth_tokens(encrypted_data)
            
            if self.is_token_expired(token_data):
                logger.warning(f"Access token expired for platform {token_data.get('platform')}")
                return None
            
            return token_data.get("access_token")
            
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return None


# Global token manager instance
_token_manager: Optional[SocialTokenManager] = None

def get_token_manager() -> SocialTokenManager:
    """Get or create global token manager instance"""
    global _token_manager
    
    if _token_manager is None:
        _token_manager = SocialTokenManager()
    
    return _token_manager

# For backwards compatibility
import time