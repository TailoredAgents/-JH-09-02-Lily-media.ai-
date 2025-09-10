#!/usr/bin/env python3
"""
Complete FastAPI application with all endpoints and functionality
"""
import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os

# Import production config for graceful degradation
try:
    from backend.core.production_config import production_config
except ImportError:
    # Fallback if production config fails
    class MockProductionConfig:
        def get_feature_status(self):
            return {"status": "minimal", "error": "Production config failed"}
    production_config = MockProductionConfig()

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept", "X-CSRF-Token"],
)

# Include API routers
try:
    from backend.api.content import router as content_router
    app.include_router(content_router)
    logger.info("✅ Content router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import content router: {e}")

try:
    from backend.api.autonomous import router as autonomous_router
    app.include_router(autonomous_router)
    logger.info("✅ Autonomous router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import autonomous router: {e}")

try:
    from backend.api.memory import router as memory_router
    app.include_router(memory_router)
    logger.info("✅ Memory router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import memory router: {e}")

try:
    from backend.api.goals import router as goals_router
    app.include_router(goals_router)
    logger.info("✅ Goals router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import goals router: {e}")

try:
    from backend.api.auth import router as auth_router
    app.include_router(auth_router)
    logger.info("✅ Auth router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import auth router: {e}")

try:
    from backend.api.notifications import router as notifications_router
    app.include_router(notifications_router)
    logger.info("✅ Notifications router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import notifications router: {e}")

try:
    from backend.api.image_streaming import router as image_streaming_router
    app.include_router(image_streaming_router)
    logger.info("✅ Image streaming router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import image streaming router: {e}")

try:
    from backend.api.social_inbox import router as social_inbox_router
    app.include_router(social_inbox_router)
    logger.info("✅ Social inbox router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import social inbox router: {e}")

try:
    from backend.api.webhooks import router as webhooks_router
    app.include_router(webhooks_router)
    logger.info("✅ Webhooks router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import webhooks router: {e}")

# Include assistant chat router
try:
    from backend.api.assistant_chat import router as assistant_chat_router
    app.include_router(assistant_chat_router, prefix="/api")
    logger.info("✅ Assistant chat router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import assistant chat router: {e}")

@app.get("/")
async def root():
    """Root endpoint with production status"""
    feature_status = production_config.get_feature_status()
    return {
        "message": "AI Social Media Content Agent API is running",
        "status": "success",
        "version": "2.0.0",
        "environment": feature_status.get("environment", "unknown"),
        "available_features": feature_status.get("available_features", []),
        "feature_count": feature_status.get("total_features", 0),
        "deployment_status": feature_status.get("status", "unknown")
    }

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint for Render"""
    feature_status = production_config.get_feature_status()
    return {
        "status": "healthy",
        "version": "2.0.0",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "uptime": "Running",
        "features": feature_status,
        "endpoints": {
            "total_routes": len(app.routes),
            "api_routes": len([r for r in app.routes if hasattr(r, 'methods') and any('/api/' in str(r.path) for r in [r])]),
        },
        "services": {
            "openai": "available" if os.getenv("OPENAI_API_KEY") else "missing_key",
            "database": "configured" if os.getenv("DATABASE_URL") else "not_configured",
            "redis": "configured" if os.getenv("REDIS_URL") else "not_configured"
        }
    }

@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    return {
        "status": "operational",
        "version": "2.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "autonomous_agent": "active",
        "last_updated": "2025-08-01"
    }

@app.get("/api/features")
async def get_features():
    """Get available API features"""
    return {
        "autonomous_posting": {
            "description": "Automated content creation and posting",
            "endpoints": ["/api/autonomous/execute-cycle", "/api/autonomous/status"]
        },
        "content_management": {
            "description": "Create, edit, and manage social media content",
            "endpoints": ["/api/content/", "/api/content/generate", "/api/content/generate-image"]
        },
        "industry_research": {
            "description": "Automated industry trend analysis",
            "endpoints": ["/api/autonomous/research", "/api/autonomous/research/latest"]
        },
        "image_generation": {
            "description": "AI-powered image creation for social media",
            "endpoints": ["/api/content/generate-image"]
        },
        "analytics": {
            "description": "Performance tracking and insights",
            "endpoints": ["/api/content/analytics/summary"]
        }
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "message": "The requested endpoint does not exist",
            "available_endpoints": [
                "/docs",
                "/api/status",
                "/api/features",
                "/api/autonomous/execute-cycle",
                "/api/content/generate-image"
            ]
        }
    )

@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)