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

# P1-2a: Validate environment on startup with strict production enforcement
try:
    from backend.core.env_validator import validate_on_startup, validate_environment
    environment = os.getenv("ENVIRONMENT", "production").lower()
    
    # Get detailed validation results for better startup diagnostics
    validation_results = validate_environment()
    
    if validation_results["validation_passed"]:
        logger.info("✅ Environment validation passed - {} environment".format(environment))
        logger.info("📊 Configuration completeness: {}%".format(validation_results["configuration_completeness"]))
        
        # Log critical warnings
        if validation_results["warnings"]:
            logger.warning("⚠️  Environment validation warnings ({}):".format(len(validation_results["warnings"])))
            for warning in validation_results["warnings"][:5]:  # Log first 5 warnings
                logger.warning("  - {}".format(warning))
    else:
        logger.error("❌ Environment validation failed!")
        logger.error("Missing required variables: {}".format(validation_results["summary"]["missing_required"]))
        
        # In production, strict validation - fail fast with detailed error
        if environment == "production":
            logger.error("🚫 PRODUCTION: Environment validation failure is not permitted")
            logger.error("Required environment variables must be set before startup")
            for error in validation_results["errors"]:
                logger.error("  - {}".format(error))
            sys.exit(1)
        else:
            # In development, log errors but continue
            logger.warning("🔄 DEVELOPMENT: Continuing despite validation errors")
            for error in validation_results["errors"][:3]:  # Log first 3 errors
                logger.warning("  - {}".format(error))
    
    # Run the startup validation function for additional checks
    validate_on_startup()
    logger.info("🔍 Startup environment validation completed")
    
    # P0-2d: Validate secrets management and security
    try:
        from backend.core.secrets_validator import validate_secrets_on_startup
        
        secrets_valid, secret_errors = validate_secrets_on_startup(environment)
        
        if secrets_valid:
            logger.info("🔐 Secrets validation passed - secure configuration detected")
        else:
            logger.error("❌ CRITICAL: Secrets validation failed!")
            
            # In production, critical secret failures prevent startup
            if environment == "production":
                logger.error("🚫 PRODUCTION: Critical secret security issues detected")
                for error in secret_errors:
                    logger.error(f"  - {error}")
                logger.error("🛡️ SECURITY: Cannot start with compromised secrets configuration")
                sys.exit(1)
            else:
                # In development, log warnings but continue
                logger.warning("🔄 DEVELOPMENT: Secret validation issues detected")
                for error in secret_errors[:5]:  # Log first 5 errors
                    logger.warning(f"  - {error}")
        
        logger.info("🔐 Secrets security validation completed")
        
    except ImportError as e:
        logger.error(f"❌ Critical: Secrets validator not available: {e}")
        if environment == "production":
            logger.error("🚫 PRODUCTION: Cannot start without secrets validation")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Secrets validation failed: {e}")
        if environment == "production":
            logger.error("🚫 PRODUCTION: Cannot start with secrets validation error")
            sys.exit(1)
    
except ImportError as e:
    logger.error("❌ Critical: Environment validator module not available: {}".format(e))
    if os.getenv("ENVIRONMENT", "production").lower() == "production":
        logger.error("🚫 PRODUCTION: Cannot start without environment validation")
        sys.exit(1)
except Exception as e:
    logger.error("❌ Environment validation failed with error: {}".format(e))
    if os.getenv("ENVIRONMENT", "production").lower() == "production":
        logger.error("🚫 PRODUCTION: Cannot start with invalid environment configuration")
        sys.exit(1)
    else:
        logger.warning("🔄 DEVELOPMENT: Continuing despite validation error")

# Create FastAPI app using factory pattern with health gates
environment = os.getenv("ENVIRONMENT", "production").lower()
logger.info("Creating FastAPI app using factory pattern with health gates for {} environment".format(environment))

try:
    from backend.core.app_factory import create_app, AppConfig
    
    # Create app configuration
    config = AppConfig(
        environment=environment,
        title="AI Social Media Content Agent",
        description="Complete autonomous social media management platform with security hardening",
        version="2.0.0",
        debug=environment == "development",
        enable_docs=environment != "production"
    )
    
    # Create app with health gates (production) or without (development)
    app = create_app(config)
    logger.info("✅ FastAPI app created successfully with health gates integration")
    
except ImportError as e:
    logger.error("❌ Failed to import app factory: {}".format(e))
    logger.info("Falling back to direct FastAPI app creation")
    
    # Fallback to direct app creation
    app = FastAPI(
        title="AI Social Media Content Agent",
        description="Complete autonomous social media management platform with security hardening",
        version="2.0.0",
        docs_url="/docs" if environment != "production" else None,
        redoc_url="/redoc" if environment != "production" else None
    )

# All middleware is now handled by the app factory pattern
# This includes: proxy headers, security, CORS, audit logging, observability, plan enforcement, etc.
logger.info("All middleware configuration delegated to app factory pattern")

# Router loading is also handled by the app factory pattern  
logger.info("Router configuration delegated to app factory pattern")

# Static file serving is also handled by the app factory pattern
logger.info("Static file serving delegated to app factory pattern")

# Health endpoints are also handled by the app factory pattern
logger.info("Health endpoints delegated to app factory pattern")

@app.head("/")
async def root_head():
    """HEAD endpoint for health checks"""
    return {}

@app.get("/health")
async def health_check():
    """Comprehensive health check with P0-13b security status"""
    
    # Get security middleware status
    security_status = {}
    try:
        from backend.core.security_middleware_factory import get_security_middleware_status
        security_status = get_security_middleware_status()
    except Exception as e:
        security_status = {"error": str(e)}
    
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
        },
        "security": {
            "middleware_status": security_status,
            "p0_13b_compliance": security_status.get("distributed_enabled", False)
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
