#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production-ready FastAPI app with comprehensive security hardening
"""
import sys
import os
from pathlib import Path

# Add backend to path FIRST so we can import our warning suppression
backend_path = Path(__file__).parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import warning suppression before any third-party libraries
try:
    from backend.core.suppress_warnings import suppress_third_party_warnings
    suppress_third_party_warnings()
except ImportError:
    # Fallback if module not available
    import warnings
    warnings.filterwarnings("ignore", category=SyntaxWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)

import logging

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Starting AI Social Media Content Agent (Production)")
logger.info("Python version: {}".format(sys.version))
logger.info("Working directory: {}".format(os.getcwd()))
logger.info("Backend path already added: {}".format(backend_path))

# Import FastAPI with fallback
try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    logger.info("FastAPI imported successfully")
except ImportError as e:
    logger.error("Failed to import FastAPI: {}".format(e))
    logger.error("Please ensure FastAPI is installed: pip install fastapi")
    sys.exit(1)

# Validate environment on startup
try:
    from backend.core.env_validator_simple import validate_on_startup
    validate_on_startup()
    logger.info("Environment validation completed")
except Exception as e:
    logger.warning("Environment validation failed: {}".format(e))

# Create FastAPI app
environment = os.getenv("ENVIRONMENT", "production").lower()
app = FastAPI(
    title="AI Social Media Content Agent",
    description="Complete autonomous social media management platform with security hardening",
    version="2.0.0",
    docs_url="/docs" if environment != "production" else None,  # Disable docs in production
    redoc_url="/redoc" if environment != "production" else None  # Disable redoc in production
)

# Respect proxy headers when behind a load balancer (ALB/Render)
try:
    from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
    logger.info("Proxy headers middleware enabled")
except Exception as e:
    logger.warning("Could not add ProxyHeadersMiddleware: %s", e)

# Setup comprehensive security middleware
security_middleware_success = False
try:
    from backend.core.security_middleware import setup_security_middleware
    from backend.core.audit_logger import AuditTrackingMiddleware, AuditLogger
    
    # Initialize audit logger and add audit tracking middleware
    audit_logger = AuditLogger()
    app.add_middleware(AuditTrackingMiddleware, audit_logger=audit_logger)
    
    # Setup all security middleware
    setup_security_middleware(app, environment=environment)
    security_middleware_success = True
    
    logger.info("Security middleware configured for {} environment".format(environment))
except Exception as e:
    logger.error("Failed to setup security middleware: {}".format(e))

# Setup observability middleware with OpenTelemetry
try:
    from backend.core.observability_middleware import setup_observability_middleware
    observability_success = setup_observability_middleware(app)
    if observability_success:
        logger.info("OpenTelemetry observability middleware configured successfully")
    else:
        logger.warning("OpenTelemetry observability middleware setup failed")
except Exception as e:
    logger.error("Failed to setup observability middleware: {}".format(e))

# Only add fallback CORS if security middleware failed
if not security_middleware_success:
    logger.warning("Using fallback CORS configuration")
    from fastapi.middleware.cors import CORSMiddleware
    
    if environment == "development":
        # Development: Allow all origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
    else:
        # Production: Restrict origins
        # Check both ALLOWED_ORIGINS and CORS_ORIGINS for compatibility
        allowed_origins_env = os.getenv("ALLOWED_ORIGINS") or os.getenv("CORS_ORIGINS", "")
        logger.info(f"CORS environment variables - ALLOWED_ORIGINS: {os.getenv('ALLOWED_ORIGINS')}")
        logger.info(f"CORS environment variables - CORS_ORIGINS: {os.getenv('CORS_ORIGINS')}")
        
        if allowed_origins_env:
            allowed_origins = allowed_origins_env.split(",")
            allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]
        else:
            allowed_origins = []
        
        if not allowed_origins:
            # Current production domains as fallback
            allowed_origins = [
                "https://socialmedia-frontend-pycc.onrender.com",
                "https://socialmedia-api-wxip.onrender.com",
                "https://www.lily-ai-socialmedia.com",
                "https://lily-ai-socialmedia.com"
                # REMOVED localhost from production CORS - security risk
            ]
            logger.warning("No CORS environment variables found, using current production domains as fallback")
        
        logger.info(f"CORS allowed origins: {allowed_origins}")
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Accept",
                "Accept-Language", 
                "Content-Language",
                "Content-Type",
                "Authorization",
                "X-Requested-With"
            ]
        )

# Add error tracking middleware
try:
    from backend.middleware.error_tracking import error_tracking_middleware, log_404_errors
    app.middleware("http")(error_tracking_middleware)
    app.middleware("http")(log_404_errors)
    logger.info("Error tracking middleware added")
except Exception as e:
    logger.warning("Could not add error tracking middleware: {}".format(e))

# Track loaded routers
loaded_routers = []
failed_routers = []

# Load routers from centralized registry
try:
    from backend.api._registry import ROUTERS
    logger.info("Loading {} routers from registry".format(len(ROUTERS)))
    
    for router in ROUTERS:
        try:
            router_name = getattr(router, 'prefix', 'unknown').replace('/api/', '') or 'root'
            app.include_router(router)
            loaded_routers.append(router_name)
            logger.info("✅ {} router loaded successfully".format(router_name))
        except Exception as e:
            router_name = getattr(router, 'prefix', 'unknown')
            failed_routers.append((router_name, str(e)))
            logger.error("❌ {} router error: {} - {}".format(router_name, type(e).__name__, e))
            continue
            
except ImportError as e:
    logger.error("Failed to import router registry: {}".format(e))
    # Fallback to minimal routers
    try:
        from backend.api import auth, two_factor
        app.include_router(auth.router)
        app.include_router(two_factor.router)
        loaded_routers.append("auth")
        loaded_routers.append("two_factor")
        logger.info("✅ Fallback auth and 2FA routers loaded")
    except Exception as fallback_e:
        logger.error("❌ Fallback routers failed: {}".format(fallback_e))

# Static file serving for uploaded images
try:
    from pathlib import Path
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    
    app.mount("/api/files/uploads", StaticFiles(directory="uploads"), name="uploads")
    logger.info("✅ Static file serving configured for uploads")
except Exception as e:
    logger.error("❌ Failed to setup static file serving: {}".format(e))

# Root endpoints
@app.get("/")
async def root():
    """Root endpoint for service status"""
    return {
        "name": "AI Social Media Content Agent",
        "version": "2.0.0",
        "status": "operational",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "message": "Service is running. Visit /docs for API documentation (if enabled).",
        "health_check": "/health",
        "routes_loaded": len(loaded_routers),
        "total_endpoints": len(app.routes)
    }

@app.head("/")
async def root_head():
    """HEAD endpoint for health checks"""
    return {}

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "python_version": "{}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro),
        "environment": os.getenv("ENVIRONMENT", "production"),
        "uptime": "Running",
        "routers_loaded": len(loaded_routers),
        "routers": loaded_routers,
        "features": {
            "environment": os.getenv("ENVIRONMENT", "production"),
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
    """Render-specific health check"""
    return {
        "status": "healthy",
        "mode": "production",
        "version": "2.0.0",
        "python_version": sys.version,
        "available_routes": len(app.routes),
        "loaded_modules": loaded_routers,
        "failed_modules": len(failed_routers)
    }

# Fallback endpoints to prevent 404s if routers don't load
@app.get("/api/notifications/")
async def notifications_fallback():
    """Fallback for notifications endpoint"""
    return {
        "notifications": [],
        "total": 0,
        "message": "Sorry, my notification system is taking a little break right now! 😴 - Lily"
    }

@app.get("/api/system/logs")
async def system_logs_fallback():
    """Fallback for system logs endpoint"""
    return {
        "logs": [],
        "total": 0,
        "message": "Sorry, my system logs are taking a little nap right now! 😴 - Lily"
    }

@app.get("/api/system/logs/stats")
async def system_logs_stats_fallback():
    """Fallback for system logs stats endpoint"""
    return {
        "total_errors": 0,
        "total_warnings": 0,
        "errors_last_hour": 0,
        "errors_last_day": 0,
        "message": "Sorry, my system logs are taking a little nap right now! 😴 - Lily"
    }

@app.get("/api/workflow/status/summary")
async def workflow_status_fallback():
    """Fallback for workflow status endpoint"""
    return {
        "status": "unavailable",
        "message": "Sorry, my workflow service is taking a little nap right now! 😴 - Lily"
    }

@app.get("/api/metrics")
async def metrics_fallback():
    """Fallback for metrics endpoint"""
    return {
        "metrics": {},
        "message": "Sorry, my metrics service is taking a little nap right now! 😴 - Lily"
    }

@app.get("/api/autonomous/research/latest")
async def autonomous_research_fallback():
    """Fallback for autonomous research endpoint"""
    return {
        "research": [],
        "message": "Sorry, my research service is taking a little nap right now! 😴 - Lily"
    }

# Handle all OPTIONS requests (CORS preflight)
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle CORS preflight requests for any path"""
    return {"message": "CORS preflight OK"}

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler with helpful information"""
    available_endpoints = [
        "/docs",
        "/health",
        "/render-health",
        "/api/content/generate-image"
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
            "documentation": "/docs"
        }
    )

# Log startup summary
logger.info("=" * 50)
logger.info("Loaded {} routers successfully".format(len(loaded_routers)))
logger.info("Failed to load {} routers".format(len(failed_routers)))
logger.info("Total routes: {}".format(len(app.routes)))
logger.info("=" * 50)

# Database schema safety net (migrations should be run separately)
try:
    from backend.db.ensure_columns import ensure_user_columns, ensure_notifications_table, ensure_content_logs_table, ensure_social_inbox_tables
    logger.info("Running database schema safety net...")
    
    # Only run safety net for critical tables
    ensure_user_columns()
    ensure_notifications_table() 
    ensure_content_logs_table()
    ensure_social_inbox_tables()
    
    logger.info("✅ Database schema safety net completed")
    
except Exception as e:
    logger.warning(f"⚠️ Schema safety net warnings: {e}")
    logger.info("App will continue - database tables may need manual creation")

# AI Suggestions Performance Fix - Auto-migration on startup
try:
    from backend.db.auto_migrate import init_database_schema
    logger.info("🚀 Initializing AI suggestions performance fix...")
    init_database_schema()
    logger.info("✅ AI suggestions performance optimization completed")
except Exception as e:
    logger.warning(f"⚠️ AI suggestions auto-migration warnings: {e}")
    logger.info("AI suggestions may be slower until database schema is updated manually")

# Export the app
__all__ = ["app"]
