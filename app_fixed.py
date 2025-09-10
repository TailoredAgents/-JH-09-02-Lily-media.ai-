#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production-ready FastAPI app with comprehensive error handling
"""
import sys
import os
import logging
from pathlib import Path

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Starting AI Social Media Content Agent (Production)")
logger.info(f"Python version: {sys.version}")
logger.info(f"Working directory: {os.getcwd()}")

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
    logger.info(f"Added backend path: {backend_path}")

# Import FastAPI with fallback
try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    logger.info("FastAPI imported successfully")
except ImportError as e:
    logger.error(f"Failed to import FastAPI: {e}")
    logger.error("Please ensure FastAPI is installed: pip install fastapi")
    sys.exit(1)

# Create FastAPI app
app = FastAPI(
    title="AI Social Media Content Agent",
    description="Complete autonomous social media management platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://socialmedia-frontend-pycc.onrender.com",  # Production frontend
        "https://socialmedia-api-wxip.onrender.com",       # Production API (self)
        "http://localhost:3000",                           # Development frontend
        "http://localhost:8000"                            # Development backend
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "User-Agent", "DNT", "Cache-Control", "X-Mx-ReqToken", "Keep-Alive", "X-Requested-With", "If-Modified-Since"],
)

# Add error tracking middleware
try:
    from backend.middleware.error_tracking import error_tracking_middleware, log_404_errors
    app.middleware("http")(error_tracking_middleware)
    app.middleware("http")(log_404_errors)
    logger.info("Error tracking middleware added")
except Exception as e:
    logger.warning(f"Could not add error tracking middleware: {e}")

# Track loaded routers
loaded_routers = []
failed_routers = []

# Define all routers to load (routers define their own prefixes)
routers_config = [
    ("system_logs", "backend.api.system_logs"),
    ("content", "backend.api.content"),
    ("autonomous", "backend.api.autonomous"),
    ("memory", "backend.api.memory"),
    ("goals", "backend.api.goals"),
    ("auth", "backend.api.auth"),
    ("notifications", "backend.api.notifications"),
    ("image_streaming", "backend.api.image_streaming"),
    ("workflow", "backend.api.workflow"),
    ("memory_v2", "backend.api.memory_v2"),
    ("goals_v2", "backend.api.goals_v2"),
    ("workflow_v2", "backend.api.workflow_v2"),
]

# Load routers with detailed error handling
for router_name, module_path in routers_config:
    try:
        module = __import__(module_path, fromlist=['router'])
        router = getattr(module, 'router', None)
        if router:
            app.include_router(router, tags=[router_name])
            loaded_routers.append(router_name)
            logger.info(f"{router_name} router loaded successfully")
        else:
            failed_routers.append((router_name, "No router attribute"))
            logger.warning(f"{router_name}: No router attribute found")
    except ImportError as e:
        failed_routers.append((router_name, str(e)))
        logger.warning(f"{router_name} router failed to load: {e}")
    except Exception as e:
        failed_routers.append((router_name, str(e)))
        logger.error(f"{router_name} router error: {type(e).__name__} - {e}")

# Root endpoints
@app.get("/")
async def root():
    """Root endpoint with detailed status"""
    return {
        "message": "AI Social Media Content Agent API",
        "status": "operational",
        "version": "2.0.0",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "loaded_modules": loaded_routers,
        "failed_modules": [f[0] for f in failed_routers],
        "total_routes": len(app.routes),
        "api_docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "uptime": "Running",
        "features": {
            "environment": os.getenv("ENVIRONMENT", "production"),
            "available_features": loaded_routers,
            "missing_dependencies": [f"{name}: {error}" for name, error in failed_routers],
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

@app.exception_handler(404)
async def not_found_handler(request, exc):
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
            available_endpoints.append(f"/api/{router_name}/")
    
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
logger.info(f"Loaded {len(loaded_routers)} routers successfully")
logger.info(f"Failed to load {len(failed_routers)} routers")
logger.info(f"Total routes: {len(app.routes)}")
logger.info("=" * 50)

# Export the app
__all__ = ["app"]