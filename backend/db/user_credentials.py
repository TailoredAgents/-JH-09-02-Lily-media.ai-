"""
User Social Media Credentials Model
Secure storage for per-user social media platform credentials
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.db.database import Base
from cryptography.fernet import Fernet
import os
import base64
import json
from typing import Dict, Optional, Any


class UserCredentials(Base):
    """
    Encrypted storage for user's social media platform credentials
    Each user can store multiple platform credentials securely
    """
    __tablename__ = "user_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Platform identification
    platform = Column(String, nullable=False, index=True)  # twitter, linkedin, instagram, facebook
    platform_user_id = Column(String, nullable=True)  # Platform-specific user ID
    platform_username = Column(String, nullable=True)  # Platform username/handle
    
    # Encrypted credentials (JSON format, encrypted)
    encrypted_credentials = Column(Text, nullable=False)
    
    # Credential metadata (non-sensitive)
    credential_type = Column(String, nullable=False)  # api_key, oauth_token, app_credentials
    is_active = Column(Boolean, default=True)
    last_verified = Column(DateTime, nullable=True)
    verification_error = Column(Text, nullable=True)
    
    # Connection metadata
    scopes = Column(JSON, nullable=True)  # OAuth scopes or permissions
    expires_at = Column(DateTime, nullable=True)  # For OAuth tokens
    
    # Audit fields
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_used = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="credentials")
    
    # Class-level encryption key (derived from environment)
    _encryption_key = None
    
    @classmethod
    def get_encryption_key(cls) -> bytes:
        """Get or generate encryption key for credentials"""
        if cls._encryption_key is None:
            # SECURITY: Use environment-specific salt for user credential encryption
            secret_key = os.getenv("SECRET_KEY", "development-key-change-in-production")
            
            # Get salt from environment or derive from secret key for uniqueness
            salt_env = os.getenv("USER_CREDENTIALS_SALT")
            if salt_env:
                salt = salt_env.encode('utf-8')
            else:
                # Fallback: derive salt from secret key to ensure per-deployment uniqueness
                import hashlib
                salt = hashlib.sha256(f"creds_salt_{secret_key[:16]}".encode()).digest()[:16]
            
            # Create a deterministic key from the secret
            import hashlib
            key_material = hashlib.pbkdf2_hmac('sha256', secret_key.encode(), salt, 100000)
            cls._encryption_key = base64.urlsafe_b64encode(key_material[:32])
        
        return cls._encryption_key
    
    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """Encrypt credentials dictionary to store in database"""
        fernet = Fernet(self.get_encryption_key())
        credentials_json = json.dumps(credentials)
        encrypted_data = fernet.encrypt(credentials_json.encode())
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt_credentials(self) -> Dict[str, Any]:
        """Decrypt and return credentials dictionary"""
        if not self.encrypted_credentials:
            return {}
        
        try:
            fernet = Fernet(self.get_encryption_key())
            encrypted_data = base64.b64decode(self.encrypted_credentials.encode())
            decrypted_json = fernet.decrypt(encrypted_data).decode()
            return json.loads(decrypted_json)
        except Exception as e:
            # Log error but don't expose credentials in logs
            print(f"Failed to decrypt credentials for user {self.user_id}, platform {self.platform}: {type(e).__name__}")
            return {}
    
    def set_credentials(self, credentials: Dict[str, Any]) -> None:
        """Set and encrypt credentials"""
        self.encrypted_credentials = self.encrypt_credentials(credentials)
        self.updated_at = func.now()
    
    def get_credentials(self) -> Dict[str, Any]:
        """Get decrypted credentials"""
        return self.decrypt_credentials()
    
    def verify_credentials(self) -> bool:
        """Verify credentials are valid (placeholder for platform-specific verification)"""
        # This would be implemented per platform to verify the credentials work
        # For now, just check if credentials exist and can be decrypted
        try:
            creds = self.decrypt_credentials()
            return bool(creds)
        except:
            return False
    
    def __repr__(self):
        return f"<UserCredentials(user_id={self.user_id}, platform={self.platform}, active={self.is_active})>"


class SocialMediaPlatformConfig(Base):
    """
    Configuration for supported social media platforms
    Defines what credentials are needed for each platform
    """
    __tablename__ = "platform_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    platform_name = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    
    # Platform configuration
    is_active = Column(Boolean, default=True)
    requires_oauth = Column(Boolean, default=False)
    requires_app_credentials = Column(Boolean, default=False)
    
    # Required credential fields (JSON schema)
    required_fields = Column(JSON, nullable=False)
    optional_fields = Column(JSON, default={})
    
    # OAuth configuration (if applicable)
    oauth_config = Column(JSON, nullable=True)
    
    # API configuration
    api_base_url = Column(String, nullable=True)
    api_version = Column(String, nullable=True)
    rate_limits = Column(JSON, nullable=True)
    
    # Documentation and help
    setup_instructions = Column(Text, nullable=True)
    help_url = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SocialMediaPlatformConfig(platform={self.platform_name}, active={self.is_active})>"


# Update the User model relationship (this would go in models.py)
# Add this to the User class relationships:
# credentials = relationship("UserCredentials", back_populates="user", cascade="all, delete-orphan")


# Default platform configurations
DEFAULT_PLATFORM_CONFIGS = [
    {
        "platform_name": "twitter",
        "display_name": "Twitter/X",
        "requires_oauth": False,
        "requires_app_credentials": True,
        "required_fields": {
            "api_key": {"type": "string", "description": "Twitter API Key"},
            "api_secret": {"type": "string", "description": "Twitter API Secret"},
            "access_token": {"type": "string", "description": "Access Token"},
            "access_token_secret": {"type": "string", "description": "Access Token Secret"},
            "bearer_token": {"type": "string", "description": "Bearer Token"}
        },
        "optional_fields": {},
        "api_base_url": "https://api.twitter.com/2",
        "setup_instructions": "Get your API keys from https://developer.twitter.com",
        "help_url": "https://developer.twitter.com/en/docs/authentication"
    },
    {
        "platform_name": "linkedin",
        "display_name": "LinkedIn",
        "requires_oauth": True,
        "requires_app_credentials": True,
        "required_fields": {
            "client_id": {"type": "string", "description": "LinkedIn Client ID"},
            "client_secret": {"type": "string", "description": "LinkedIn Client Secret"},
            "access_token": {"type": "string", "description": "Access Token"}
        },
        "optional_fields": {
            "refresh_token": {"type": "string", "description": "Refresh Token"}
        },
        "oauth_config": {
            "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
            "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
            "scopes": ["r_liteprofile", "r_emailaddress", "w_member_social"]
        },
        "api_base_url": "https://api.linkedin.com/v2",
        "setup_instructions": "Create an app at https://www.linkedin.com/developers/",
        "help_url": "https://docs.microsoft.com/en-us/linkedin/"
    },
    {
        "platform_name": "instagram",
        "display_name": "Instagram Business",
        "requires_oauth": True,
        "requires_app_credentials": True,
        "required_fields": {
            "app_id": {"type": "string", "description": "Instagram App ID"},
            "app_secret": {"type": "string", "description": "Instagram App Secret"},
            "access_token": {"type": "string", "description": "Access Token"},
            "business_account_id": {"type": "string", "description": "Instagram Business Account ID"}
        },
        "optional_fields": {},
        "api_base_url": "https://graph.facebook.com",
        "setup_instructions": "Set up Instagram Business API through Facebook Developers",
        "help_url": "https://developers.facebook.com/docs/instagram-api/"
    },
    {
        "platform_name": "facebook",
        "display_name": "Facebook Pages",
        "requires_oauth": True,
        "requires_app_credentials": True,
        "required_fields": {
            "app_id": {"type": "string", "description": "Facebook App ID"},
            "app_secret": {"type": "string", "description": "Facebook App Secret"},
            "access_token": {"type": "string", "description": "Page Access Token"},
            "page_id": {"type": "string", "description": "Facebook Page ID"}
        },
        "optional_fields": {},
        "api_base_url": "https://graph.facebook.com",
        "setup_instructions": "Create an app at https://developers.facebook.com",
        "help_url": "https://developers.facebook.com/docs/pages-api/"
    }
]