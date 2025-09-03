"""
Application Factory Pattern

Creates FastAPI app instances with configurable settings for different environments.
Enables better testing, dependency injection, and configuration management.
"""
import os
import sys
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Import centralized modules
from backend.core.logging import setup_logging, get_logger
from backend.core.api_version import get_api_version

logger = logging.getLogger(__name__)


class AppConfig:
    """Configuration for FastAPI application."""
    
    def __init__(
        self,
        environment: str = None,
        title: str = "AI Social Media Content Agent",
        description: str = "Complete autonomous social media management platform",
        version: str = "2.0.0",
        debug: bool = None,
        enable_docs: bool = None,
        cors_origins: List[str] = None,
        middleware: List[Dict[str, Any]] = None
    ):
        # Environment detection
        self.environment = environment or os.getenv("ENVIRONMENT", "production").lower()
        
        # Basic app settings
        self.title = title
        self.description = description
        self.version = version
        self.debug = debug if debug is not None else (self.environment == "development")
        
        # API documentation
        self.enable_docs = enable_docs if enable_docs is not None else (self.environment != "production")
        self.docs_url = "/docs" if self.enable_docs else None
        self.redoc_url = "/redoc" if self.enable_docs else None
        
        # CORS configuration
        self.cors_origins = cors_origins or self._get_default_cors_origins()
        
        # Middleware configuration
        self.middleware = middleware or []
        
        # API versioning
        self.api_version = get_api_version()
    
    def _get_default_cors_origins(self) -> List[str]:
        """Get default CORS origins based on environment."""
        # Check environment variables first
        cors_env = os.getenv("ALLOWED_ORIGINS") or os.getenv("CORS_ORIGINS", "")
        if cors_env:
            return [origin.strip() for origin in cors_env.split(",") if origin.strip()]
        
        # Environment-specific defaults
        if self.environment == "development":
            return ["*"]  # Allow all in development
        else:
            # Production defaults
            return [
                "https://socialmedia-frontend-pycc.onrender.com",
                "https://socialmedia-api-wxip.onrender.com", 
                "https://www.lily-ai-socialmedia.com",
                "https://lily-ai-socialmedia.com"
            ]


def setup_middleware(app: FastAPI, config: AppConfig) -> None:
    """Setup application middleware."""
    
    # Add proxy headers middleware if available
    try:
        from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
        logger.info("Proxy headers middleware enabled")
    except ImportError:
        logger.debug("ProxyHeadersMiddleware not available")
    
    # Setup security middleware
    try:
        from backend.core.security_middleware import setup_security_middleware
        from backend.core.audit_logger import AuditTrackingMiddleware, AuditLogger
        
        # Initialize audit logger and add audit tracking middleware
        audit_logger = AuditLogger()
        app.add_middleware(AuditTrackingMiddleware, audit_logger=audit_logger)
        
        # Setup all security middleware
        setup_security_middleware(app, environment=config.environment)
        logger.info("Security middleware configured for {} environment".format(config.environment))
        
    except ImportError as e:
        logger.warning("Security middleware not available: {}".format(e))
        # Fallback to basic CORS
        _setup_fallback_cors(app, config)
    
    # Add error tracking middleware
    try:
        from backend.middleware.error_tracking import error_tracking_middleware, log_404_errors
        app.middleware("http")(error_tracking_middleware)
        app.middleware("http")(log_404_errors)
        logger.info("Error tracking middleware added")
    except ImportError:
        logger.debug("Error tracking middleware not available")


def _setup_fallback_cors(app: FastAPI, config: AppConfig) -> None:
    """Setup fallback CORS middleware."""
    from fastapi.middleware.cors import CORSMiddleware
    
    logger.warning("Using fallback CORS configuration")
    logger.info("CORS allowed origins: {}".format(config.cors_origins))
    
    allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    allow_headers = [
        "Accept", "Accept-Language", "Content-Language", "Content-Type",
        "Authorization", "X-Requested-With"
    ]
    
    if config.environment == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=allow_methods,
            allow_headers=allow_headers
        )


def setup_routers(app: FastAPI) -> tuple:
    """Setup API routers."""
    loaded_routers = []
    failed_routers = []
    
    try:
        from backend.api._registry import ROUTERS
        logger.info("Loading {} routers from registry".format(len(ROUTERS)))
        
        for router in ROUTERS:
            try:
                router_name = getattr(router, 'prefix', 'unknown').replace('/api/', '') or 'root'
                app.include_router(router)
                loaded_routers.append(router_name)
                logger.info("Router '{}' loaded successfully".format(router_name))
            except Exception as e:
                router_name = getattr(router, 'prefix', 'unknown')
                failed_routers.append((router_name, str(e)))
                logger.error("Router '{}' failed: {} - {}".format(router_name, type(e).__name__, e))
                continue
                
    except ImportError as e:
        logger.error("Failed to import router registry: {}".format(e))
        # Fallback to minimal routers
        try:
            from backend.api import auth, two_factor
            app.include_router(auth.router)
            app.include_router(two_factor.router)
            loaded_routers.extend(["auth", "two_factor"])
            logger.info("Fallback auth and 2FA routers loaded")
        except Exception as fallback_e:
            logger.error("Fallback routers failed: {}".format(fallback_e))
    
    return loaded_routers, failed_routers


def setup_static_files(app: FastAPI) -> None:
    """Setup static file serving."""
    try:
        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)
        
        app.mount("/api/files/uploads", StaticFiles(directory="uploads"), name="uploads")
        logger.info("Static file serving configured for uploads")
    except Exception as e:
        logger.error("Failed to setup static file serving: {}".format(e))


def setup_exception_handlers(app: FastAPI, loaded_routers: List[str]) -> None:
    """Setup custom exception handlers."""
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: HTTPException):
        """Custom 404 handler with helpful information."""
        available_endpoints = [
            "/health", "/render-health", "/api/content/generate-image"
        ]
        
        # Add loaded router endpoints
        for router_name in loaded_routers:
            if router_name in ["content", "auth", "memory", "goals"]:
                available_endpoints.append("/api/{}/".format(router_name))
        
        return JSONResponse(
            status_code=404,
            content={
                "error": "Endpoint not found",
                "message": "The requested endpoint does not exist",
                "available_endpoints": available_endpoints,
                "loaded_modules": loaded_routers,
                "documentation": "/docs" if app.docs_url else None
            }
        )


def setup_health_endpoints(app: FastAPI, config: AppConfig, loaded_routers: List[str], failed_routers: List[tuple]) -> None:
    """Setup health check endpoints."""
    
    @app.get("/")
    async def root():
        """Root endpoint for service status."""
        return {
            "name": config.title,
            "version": config.version,
            "status": "operational",
            "environment": config.environment,
            "api_version": config.api_version,
            "message": "Service is running. Visit /docs for API documentation (if enabled).",
            "health_check": "/health",
            "routes_loaded": len(loaded_routers),
            "total_endpoints": len(app.routes)
        }
    
    @app.head("/")
    async def root_head():
        """HEAD endpoint for health checks."""
        return {}
    
    @app.get("/health")
    async def health_check():
        """Comprehensive health check."""
        return {
            "status": "healthy",
            "version": config.version,
            "api_version": config.api_version,
            "python_version": "{}.{}.{}".format(
                sys.version_info.major, sys.version_info.minor, sys.version_info.micro
            ),
            "environment": config.environment,
            "uptime": "Running",
            "routers_loaded": len(loaded_routers),
            "routers": loaded_routers,
            "features": {
                "environment": config.environment,
                "available_features": loaded_routers,
                "missing_dependencies": ["{}: {}".format(name, error) for name, error in failed_routers],
                "total_features": len(loaded_routers),
                "status": "healthy" if len(loaded_routers) > 0 else "degraded"
            },
            "endpoints": {
                "total_routes": len(app.routes),
                "api_routes": len([r for r in app.routes if hasattr(r, 'path') and '/api/' in str(r.path)])
            },
            "services": {
                "openai": "available" if os.getenv("OPENAI_API_KEY") else "missing_key",
                "database": "configured" if os.getenv("DATABASE_URL") else "not_configured",
                "redis": "configured" if os.getenv("REDIS_URL") else "not_configured"
            }
        }
    
    @app.get("/render-health")
    async def render_health():
        """Render-specific health check."""
        return {
            "status": "healthy",
            "mode": config.environment,
            "version": config.version,
            "api_version": config.api_version,
            "python_version": sys.version,
            "available_routes": len(app.routes),
            "loaded_modules": loaded_routers,
            "failed_modules": len(failed_routers)
        }


def create_app(config: Optional[AppConfig] = None) -> FastAPI:
    """
    Create FastAPI application with factory pattern.
    
    Args:
        config: Optional configuration object
        
    Returns:
        Configured FastAPI application
    """
    if config is None:
        config = AppConfig()
    
    # Setup logging first
    if config.environment == "development":
        from backend.core.logging import setup_development_logging
        setup_development_logging()
    else:
        from backend.core.logging import setup_production_logging
        setup_production_logging()
    
    logger.info("Creating FastAPI application")
    logger.info("Environment: {}".format(config.environment))
    logger.info("API Version: {}".format(config.api_version))
    
    # Create FastAPI app
    app = FastAPI(
        title=config.title,
        description=config.description,
        version=config.version,
        docs_url=config.docs_url,
        redoc_url=config.redoc_url,
        debug=config.debug
    )
    
    # Setup middleware
    setup_middleware(app, config)
    
    # Setup routers
    loaded_routers, failed_routers = setup_routers(app)
    
    # Setup static files
    setup_static_files(app)
    
    # Setup exception handlers
    setup_exception_handlers(app, loaded_routers)
    
    # Setup health endpoints
    setup_health_endpoints(app, config, loaded_routers, failed_routers)
    
    # Log startup summary
    logger.info("=" * 50)
    logger.info("FastAPI application created successfully")
    logger.info("Environment: {}".format(config.environment))
    logger.info("Loaded {} routers successfully".format(len(loaded_routers)))
    logger.info("Failed to load {} routers".format(len(failed_routers)))
    logger.info("Total routes: {}".format(len(app.routes)))
    logger.info("=" * 50)
    
    return app


# Convenience functions for common configurations
def create_development_app() -> FastAPI:
    """Create app configured for development."""
    config = AppConfig(environment="development", debug=True, enable_docs=True)
    return create_app(config)


def create_production_app() -> FastAPI:
    """Create app configured for production."""
    config = AppConfig(environment="production", debug=False, enable_docs=False)
    return create_app(config)


def create_test_app(cors_origins: List[str] = None) -> FastAPI:
    """Create app configured for testing."""
    config = AppConfig(
        environment="test", 
        debug=True, 
        enable_docs=False,
        cors_origins=cors_origins or ["http://testserver"]
    )
    return create_app(config)