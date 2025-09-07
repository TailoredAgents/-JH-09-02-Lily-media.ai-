"""
Production configuration for AI Social Media Content Agent
"""
import os
from typing import Optional, List
from pydantic import Field, ConfigDict
from backend.core.config import Settings

class ProductionSettings(Settings):
    """Production-specific configuration settings"""
    
    # Environment
    environment: str = Field("production", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(30, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(3600, env="DATABASE_POOL_RECYCLE")
    
    # Redis Configuration
    redis_url: str = Field(..., env="REDIS_URL")
    redis_max_connections: int = Field(50, env="REDIS_MAX_CONNECTIONS")
    redis_retry_on_timeout: bool = Field(True, env="REDIS_RETRY_ON_TIMEOUT")
    
    # Celery Configuration
    celery_broker_url: str = Field(..., env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(..., env="CELERY_RESULT_BACKEND")
    celery_task_serializer: str = Field("json", env="CELERY_TASK_SERIALIZER")
    celery_result_serializer: str = Field("json", env="CELERY_RESULT_SERIALIZER")
    celery_accept_content: List[str] = Field(["json"], env="CELERY_ACCEPT_CONTENT")
    celery_timezone: str = Field("UTC", env="CELERY_TIMEZONE")
    celery_enable_utc: bool = Field(True, env="CELERY_ENABLE_UTC")
    
    # Security Configuration
    secret_key: str = Field(..., env="SECRET_KEY")
    access_token_expire_minutes: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(30, env="REFRESH_TOKEN_EXPIRE_DAYS")
    password_hash_rounds: int = Field(12, env="PASSWORD_HASH_ROUNDS")
    
    # JWT Configuration (Local Authentication Only)
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_access_ttl_seconds: int = Field(900, env="JWT_ACCESS_TTL_SECONDS")  # 15 minutes
    jwt_refresh_ttl_seconds: int = Field(1209600, env="JWT_REFRESH_TTL_SECONDS")  # 14 days
    
    # OpenAI Configuration - Updated for GPT-5 Models
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-5", env="OPENAI_MODEL")  # Default to GPT-5 for content generation
    openai_research_model: str = Field("gpt-5-mini", env="OPENAI_RESEARCH_MODEL")  # GPT-5 mini for research
    openai_deep_research_model: str = Field("gpt-5", env="OPENAI_DEEP_RESEARCH_MODEL")  # GPT-5 for deep analysis
    openai_categorization_model: str = Field("gpt-5-mini", env="OPENAI_CATEGORIZATION_MODEL")  # GPT-5 mini for categorization
    xai_image_model: str = Field("grok-2-image", env="XAI_IMAGE_MODEL")  # Grok-2 Image for all image generation
    openai_embedding_model: str = Field("text-embedding-3-large", env="OPENAI_EMBEDDING_MODEL")  # text-embedding-3-large
    openai_max_tokens: int = Field(2000, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(0.7, env="OPENAI_TEMPERATURE")
    openai_request_timeout: int = Field(60, env="OPENAI_REQUEST_TIMEOUT")
    openai_max_retries: int = Field(3, env="OPENAI_MAX_RETRIES")
    
    # FAISS Configuration - Updated for text-embedding-3-large (3072 dimensions)
    faiss_index_path: str = Field("/app/data/faiss_index", env="FAISS_INDEX_PATH")
    faiss_dimension: int = Field(3072, env="FAISS_DIMENSION")  # Updated for text-embedding-3-large
    faiss_index_type: str = Field("IndexFlatIP", env="FAISS_INDEX_TYPE")
    faiss_backup_interval: int = Field(3600, env="FAISS_BACKUP_INTERVAL")  # seconds
    faiss_max_vectors: int = Field(100000, env="FAISS_MAX_VECTORS")
    
    # Social Media API Configuration
    twitter_api_key: Optional[str] = Field(None, env="TWITTER_API_KEY")
    twitter_api_secret: Optional[str] = Field(None, env="TWITTER_API_SECRET")
    twitter_bearer_token: Optional[str] = Field(None, env="TWITTER_BEARER_TOKEN")
    
    linkedin_client_id: Optional[str] = Field(None, env="LINKEDIN_CLIENT_ID")
    linkedin_client_secret: Optional[str] = Field(None, env="LINKEDIN_CLIENT_SECRET")
    
    instagram_app_id: Optional[str] = Field(None, env="INSTAGRAM_APP_ID")
    instagram_app_secret: Optional[str] = Field(None, env="INSTAGRAM_APP_SECRET")
    
    facebook_app_id: Optional[str] = Field(None, env="FACEBOOK_APP_ID")
    facebook_app_secret: Optional[str] = Field(None, env="FACEBOOK_APP_SECRET")
    
    # API Configuration
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    api_workers: int = Field(4, env="API_WORKERS")
    api_max_request_size: int = Field(16 * 1024 * 1024, env="API_MAX_REQUEST_SIZE")  # 16MB
    api_timeout: int = Field(60, env="API_TIMEOUT")
    
    # CORS Configuration
    cors_allowed_origins: List[str] = Field([
        "https://lilymedia.ai",
        "https://www.lilymedia.ai",
        "https://app.lilymedia.ai"
    ], env="CORS_ALLOWED_ORIGINS")
    cors_allow_credentials: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    cors_allowed_methods: List[str] = Field(["GET", "POST", "PUT", "DELETE", "PATCH"], env="CORS_ALLOWED_METHODS")
    cors_allowed_headers: List[str] = Field(["*"], env="CORS_ALLOWED_HEADERS")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(100, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst: int = Field(200, env="RATE_LIMIT_BURST")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")  # json or text
    log_file: Optional[str] = Field("/var/log/aisocial/app.log", env="LOG_FILE")
    log_max_size: str = Field("100MB", env="LOG_MAX_SIZE")
    log_backup_count: int = Field(5, env="LOG_BACKUP_COUNT")
    
    # Monitoring Configuration
    monitoring_enabled: bool = Field(True, env="MONITORING_ENABLED")
    metrics_port: int = Field(9090, env="METRICS_PORT")
    health_check_interval: int = Field(30, env="HEALTH_CHECK_INTERVAL")  # seconds
    
    # Performance Configuration
    enable_query_caching: bool = Field(True, env="ENABLE_QUERY_CACHING")
    cache_ttl: int = Field(300, env="CACHE_TTL")  # seconds
    enable_compression: bool = Field(True, env="ENABLE_COMPRESSION")
    max_concurrent_requests: int = Field(1000, env="MAX_CONCURRENT_REQUESTS")
    
    # Background Task Configuration
    task_max_retries: int = Field(3, env="TASK_MAX_RETRIES")
    task_retry_delay: int = Field(60, env="TASK_RETRY_DELAY")  # seconds
    task_soft_time_limit: int = Field(300, env="TASK_SOFT_TIME_LIMIT")  # seconds
    task_hard_time_limit: int = Field(600, env="TASK_HARD_TIME_LIMIT")  # seconds
    
    # File Storage Configuration
    storage_backend: str = Field("s3", env="STORAGE_BACKEND")  # s3, gcs, azure
    aws_s3_bucket: Optional[str] = Field(None, env="AWS_S3_BUCKET")
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field("us-east-1", env="AWS_REGION")
    
    # Content Safety Configuration
    content_moderation_enabled: bool = Field(True, env="CONTENT_MODERATION_ENABLED")
    max_content_length: int = Field(10000, env="MAX_CONTENT_LENGTH")
    profanity_filter_enabled: bool = Field(True, env="PROFANITY_FILTER_ENABLED")
    
    # Email Configuration
    email_backend: str = Field("smtp", env="EMAIL_BACKEND")
    smtp_host: Optional[str] = Field(None, env="SMTP_HOST")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(None, env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(True, env="SMTP_USE_TLS")
    from_email: str = Field("noreply@aisocialagent.com", env="FROM_EMAIL")
    
    # Feature Flags
    enable_ai_content_generation: bool = Field(True, env="ENABLE_AI_CONTENT_GENERATION")
    enable_social_posting: bool = Field(True, env="ENABLE_SOCIAL_POSTING")
    enable_analytics: bool = Field(True, env="ENABLE_ANALYTICS")
    enable_workflow_automation: bool = Field(True, env="ENABLE_WORKFLOW_AUTOMATION")
    enable_real_time_notifications: bool = Field(True, env="ENABLE_REAL_TIME_NOTIFICATIONS")
    
    # Third-party Integrations
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    datadog_api_key: Optional[str] = Field(None, env="DATADOG_API_KEY")
    mixpanel_token: Optional[str] = Field(None, env="MIXPANEL_TOKEN")
    
    model_config = ConfigDict(
        env_file=".env.production",
        case_sensitive=False
    )

def get_production_settings() -> ProductionSettings:
    """Get production settings instance"""
    return ProductionSettings()

# Database connection configuration for production
def get_database_config():
    """Get database configuration for production"""
    settings = get_production_settings()
    
    return {
        "url": settings.database_url,
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_timeout": settings.database_pool_timeout,
        "pool_recycle": settings.database_pool_recycle,
        "pool_pre_ping": True,
        "echo": False,  # Disable SQL echo in production
        "echo_pool": False,
        "connect_args": {
            "sslmode": "require",
            "connect_timeout": 10,
            "application_name": "aisocial_backend"
        }
    }

# Redis connection configuration for production
def get_redis_config():
    """Get Redis configuration for production"""
    settings = get_production_settings()
    
    return {
        "url": settings.redis_url,
        "max_connections": settings.redis_max_connections,
        "retry_on_timeout": settings.redis_retry_on_timeout,
        "socket_connect_timeout": 5,
        "socket_timeout": 5,
        "connection_pool_kwargs": {
            "socket_keepalive": True,
            "socket_keepalive_options": {},
        }
    }

# Celery configuration for production
def get_celery_config():
    """Get Celery configuration for production"""
    settings = get_production_settings()
    
    return {
        "broker_url": settings.celery_broker_url,
        "result_backend": settings.celery_result_backend,
        "task_serializer": settings.celery_task_serializer,
        "result_serializer": settings.celery_result_serializer,
        "accept_content": settings.celery_accept_content,
        "timezone": settings.celery_timezone,
        "enable_utc": settings.celery_enable_utc,
        "task_routes": {
            "backend.tasks.goals_tasks.*": {"queue": "goals"},
            "backend.tasks.automation_tasks.*": {"queue": "automation"},
            "backend.services.content_automation.*": {"queue": "content"},
            "backend.services.metrics_collection.*": {"queue": "metrics"}
        },
        "task_default_queue": "default",
        "task_default_exchange": "default",
        "task_default_routing_key": "default",
        "worker_prefetch_multiplier": 4,
        "task_acks_late": True,
        "worker_disable_rate_limits": False,
        "task_soft_time_limit": settings.task_soft_time_limit,
        "task_time_limit": settings.task_hard_time_limit,
        "task_max_retries": settings.task_max_retries,
        "task_default_retry_delay": settings.task_retry_delay
    }

# Uvicorn configuration for production
def get_uvicorn_config():
    """Get Uvicorn configuration for production"""
    settings = get_production_settings()
    
    return {
        "host": settings.api_host,
        "port": settings.api_port,
        "workers": settings.api_workers,
        "loop": "uvloop",
        "http": "httptools",
        "access_log": True,
        "log_level": settings.log_level.lower(),
        "timeout_keep_alive": 65,
        "timeout_notify": 30,
        "max_requests": 1000,
        "max_requests_jitter": 100,
        "backlog": 2048
    }