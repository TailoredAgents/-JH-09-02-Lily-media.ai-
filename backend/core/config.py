from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from functools import lru_cache
from typing import List
import os
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

def get_utc_now() -> datetime:
    """Get current UTC time with timezone awareness"""
    return datetime.now(timezone.utc)

# Load environment variables from both backend/.env and project root .env (root wins)
_backend_env = Path(__file__).resolve().parents[1] / ".env"
_root_env = Path(__file__).resolve().parents[2] / ".env"
for _env in (_backend_env, _root_env):
    if _env.exists():
        load_dotenv(_env, override=False)

def _detect_environment() -> str:
    """Detect environment with proper logic and clear fallbacks"""
    # 1. Check explicit ENVIRONMENT variable first
    explicit_env = os.getenv("ENVIRONMENT", "").lower().strip()
    if explicit_env in ["production", "staging", "development"]:
        return explicit_env
    
    # 2. Check for Render deployment (production indicator)
    if os.getenv("RENDER"):
        return "production"
    
    # 3. Check for other production indicators
    if any(os.getenv(var) for var in ["RAILWAY_ENVIRONMENT", "HEROKU_APP_NAME", "FLY_APP_NAME"]):
        return "production"
    
    # 4. Default to development for local/unknown environments
    return "development"

class Settings(BaseSettings):
    # Environment - Proper detection with clear fallbacks
    environment: str = Field(default_factory=lambda: _detect_environment())
    debug: bool = Field(default_factory=lambda: _detect_environment() != "production")
    
    # API Keys
    openai_api_key: str = ""
    xai_api_key: str = ""
    serper_api_key: str = ""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "")  # PostgreSQL from environment
    postgres_url: str = os.getenv("DATABASE_URL", "")  # PostgreSQL for production (same as database_url)
    
    def get_database_url(self) -> str:
        """Get database URL - POSTGRESQL ONLY, NO SQLITE"""
        # Check for DATABASE_URL environment variable
        db_url = self.database_url or os.getenv("DATABASE_URL")
        
        # CRITICAL: No database URL configured
        if not db_url:
            error_msg = "CRITICAL: DATABASE_URL environment variable is not set. Application cannot start without database configuration."
            logger.error(error_msg)
            if self.environment == "production":
                raise ValueError(error_msg)
            # Only allow local PostgreSQL in development
            return "postgresql://postgres:postgres@localhost:5432/socialmedia_dev"
        
        # Reject SQLite URLs completely
        if db_url.startswith("sqlite"):
            error_msg = "SQLite is not supported! Please configure PostgreSQL database."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Add SSL mode for PostgreSQL if not already present
        if db_url.startswith("postgresql://") and "sslmode" not in db_url:
            db_url += "?sslmode=require"
        
        return db_url
    
    def validate_production_config(self) -> List[str]:
        """Validate production configuration and return missing required fields"""
        missing_fields = []
        
        if self.environment == "production":
            # Critical security fields
            if not self.SECRET_KEY or self.SECRET_KEY == "your-secret-key-change-this-in-production":
                missing_fields.append("SECRET_KEY")
            
            if not self.encryption_key or self.encryption_key == "your-32-byte-encryption-key-change-this":
                missing_fields.append("ENCRYPTION_KEY")
            
            # Database
            if not self.get_database_url():
                missing_fields.append("DATABASE_URL")
            
            # Redis
            if not self.redis_url or self.redis_url == "redis://localhost:6379/0":
                missing_fields.append("REDIS_URL")
            
            # OpenAI API key (required for most features)
            if not self.openai_api_key:
                missing_fields.append("OPENAI_API_KEY")
        
        return missing_fields
    
    # JWT (Updated with proper naming and production security)
    # CRITICAL: These MUST be set in production environment
    SECRET_KEY: str = Field(default="", env="SECRET_KEY")
    encryption_key: str = Field(default="", env="ENCRYPTION_KEY")
    jwt_secret: str = Field(default="", env="JWT_SECRET")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Validate critical security settings in production
        if self.environment == "production":
            if not self.SECRET_KEY or self.SECRET_KEY == "your-secret-key-change-this-in-production":
                logger.error("🚨 CRITICAL: SECRET_KEY must be set in production environment")
                logger.error("   Set environment variable: SECRET_KEY=your-secure-secret-key")
                raise ValueError("CRITICAL: SECRET_KEY must be set in production environment")
            
            # Generate encryption key if not provided (with warning)
            if not self.encryption_key or len(self.encryption_key) < 32:
                logger.warning("⚠️  ENCRYPTION_KEY not set in production - generating temporary key")
                logger.warning("   This is NOT secure for production! Set environment variable:")
                logger.warning("   ENCRYPTION_KEY=your-32-character-encryption-key")
                import secrets
                import string
                self.encryption_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
                logger.warning(f"   Generated temporary key: {self.encryption_key}")
            
            if not self.jwt_secret:
                # Use SECRET_KEY as fallback for JWT_SECRET
                if self.SECRET_KEY:
                    logger.warning("⚠️  JWT_SECRET not set - using SECRET_KEY as fallback")
                    self.jwt_secret = self.SECRET_KEY
                else:
                    logger.error("🚨 CRITICAL: JWT_SECRET or SECRET_KEY must be set in production") 
                    logger.error("   Set environment variable: JWT_SECRET=your-jwt-secret")
                    raise ValueError("CRITICAL: JWT_SECRET must be set in production environment")
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_seconds: int = 900  # 15 minutes (secure for production)
    jwt_refresh_ttl_seconds: int = 604800  # 7 days (reduced from 14 for security)
    
    # Redis/Celery
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    celery_broker_url: str = ""  # Will default to redis_url if empty
    celery_result_backend: str = ""  # Will default to redis_url if empty
    
    # Open SaaS Configuration
    enable_registration: bool = Field(default=True, env="ENABLE_REGISTRATION")
    require_email_verification: bool = Field(default=False, env="REQUIRE_EMAIL_VERIFICATION")
    frontend_url: str = Field(default="https://lily-ai-socialmedia.com", env="FRONTEND_URL")
    backend_url: str = Field(default="https://socialmedia-api-wxip.onrender.com", env="BACKEND_URL")
    email_verification_expiry_hours: int = Field(default=24, env="EMAIL_VERIFICATION_EXPIRY_HOURS")
    password_reset_expiry_hours: int = Field(default=2, env="PASSWORD_RESET_EXPIRY_HOURS")
    
    # Email Service Configuration
    from_email: str = Field(default="noreply@lily-ai-socialmedia.com", env="FROM_EMAIL")
    email_provider: str = Field(default="smtp", env="EMAIL_PROVIDER")  # smtp, sendgrid, ses, resend
    
    # SMTP Settings
    smtp_host: str = Field(default="", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(default="", env="SMTP_USERNAME")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    
    # Provider API Keys
    sendgrid_api_key: str = Field(default="", env="SENDGRID_API_KEY")
    resend_api_key: str = Field(default="", env="RESEND_API_KEY")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    aws_access_key_id: str = Field(default="", env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", env="AWS_SECRET_ACCESS_KEY")
    
    # Social Media APIs - Twitter/X OAuth 2.0 (Primary)
    twitter_client_id: str = ""
    twitter_client_secret: str = ""
    
    # Twitter API (Legacy - for backwards compatibility)
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_token_secret: str = ""
    twitter_bearer_token: str = ""
    
    # LinkedIn - REMOVED (too restrictive API)
    
    # Meta Graph API (2025) - Unified Facebook/Instagram
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_access_token: str = ""
    meta_api_version: str = "v22.0"
    
    # Facebook Page
    facebook_page_id: str = ""
    facebook_page_access_token: str = ""
    
    # Instagram Business Account
    instagram_business_account_id: str = ""
    
    # Legacy (backwards compatibility)
    facebook_app_id: str = ""  # Maps to meta_app_id
    facebook_app_secret: str = ""  # Maps to meta_app_secret
    instagram_app_id: str = ""  # Maps to meta_app_id
    instagram_app_secret: str = ""  # Maps to meta_app_secret
    
    # Server
    port: int = 8000
    host: str = "0.0.0.0"
    
    # CORS & Security
    allowed_hosts: str = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
    cors_origins: str = os.getenv("CORS_ORIGINS", "")
    
    # Feature Flags
    feature_flags: str = ""
    feature_partner_oauth: bool = Field(default=False, env="FEATURE_PARTNER_OAUTH")
    
    # Partner OAuth Configuration
    meta_graph_version: str = Field(default="v18.0", env="META_GRAPH_VERSION")
    token_encryption_key: str = Field(default="", env="TOKEN_ENCRYPTION_KEY")
    
    # Phase 8: Rate Limiting & Circuit Breaker Configuration
    publish_bucket_capacity: int = Field(default=60, env="PUBLISH_BUCKET_CAPACITY")
    publish_bucket_window_s: int = Field(default=60, env="PUBLISH_BUCKET_WINDOW_S")
    meta_publish_max_rps: int = Field(default=1, env="META_PUBLISH_MAX_RPS")
    x_publish_max_rps: int = Field(default=1, env="X_PUBLISH_MAX_RPS")
    cb_fail_threshold: int = Field(default=5, env="CB_FAIL_THRESHOLD")
    cb_cooldown_s: int = Field(default=120, env="CB_COOLDOWN_S")
    
    # File Upload Configuration
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")
    max_file_size: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB default
    allowed_image_types: str = Field(default="jpg,jpeg,png,gif,webp", env="ALLOWED_IMAGE_TYPES")
    
    # OpenTelemetry
    otel_service_name: str = "ai-social-agent-api"
    otel_exporter_otlp_endpoint: str = ""
    
    # Monitoring & Observability
    sentry_dsn: str = ""
    prometheus_enabled: bool = False
    
    # Production Features (Hardened defaults)
    demo_mode: str = "false"
    mock_social_apis: str = "false"
    show_sample_data: str = "false"
    enable_registration: str = "true"  # Enable registration for open SaaS
    require_email_verification: str = "false"  # Disable email verification until email service is configured
    
    # Timezone Configuration
    timezone: str = "America/New_York"
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="allow"  # Allow extra fields from environment
    )
    
    def model_post_init(self, __context):
        # If META_GRAPH_VERSION is set explicitly in the environment,
        # prefer it to override meta_api_version.
        if os.getenv("META_GRAPH_VERSION"):
            self.meta_api_version = self.meta_graph_version
    
    
    def get_celery_broker_url(self) -> str:
        """Get Celery broker URL, defaulting to redis_url if not set"""
        broker_url = self.celery_broker_url or self.redis_url
        
        # If no Redis is configured and we're in production, log an info message
        # Note: Background tasks are not critical for core functionality
        if broker_url == "redis://localhost:6379/0" and self.environment == "production":
            import logging
            logger = logging.getLogger(__name__)
            logger.info("ℹ️ Redis not available for background tasks. Core functionality will work without Celery.")
        
        return broker_url
    
    def get_celery_result_backend(self) -> str:
        """Get Celery result backend URL, defaulting to redis_url if not set"""
        return self.celery_result_backend or self.redis_url

@lru_cache()
def get_settings():
    """Get settings instance based on environment"""
    env = os.getenv("ENVIRONMENT", "development")
    
    # Force production settings when DATABASE_URL is set (Render/Heroku pattern)
    if os.getenv("DATABASE_URL") and not os.getenv("DATABASE_URL").startswith("sqlite"):
        settings = Settings()
        settings.environment = "production"
        settings.debug = False
        return settings
    
    return Settings()

# Global settings instance
settings = get_settings()