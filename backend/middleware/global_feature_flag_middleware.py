"""
Global Feature Flag Middleware - Strategic enforcement across all endpoints
Provides automatic feature flag enforcement based on endpoint patterns
"""
import logging
from typing import Dict, List, Optional, Pattern
import re
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from backend.core.feature_flags import ff

logger = logging.getLogger(__name__)


class GlobalFeatureFlagMiddleware:
    """
    Middleware to enforce feature flags globally based on URL patterns
    More efficient than adding individual dependencies to every endpoint
    """
    
    def __init__(self):
        # Define URL patterns and their required feature flags
        self.endpoint_patterns: Dict[Pattern, Dict[str, str]] = {
            # AI-powered content generation
            re.compile(r"/api/content/generate.*"): {"flag": "AI_CONTENT_GENERATION", "feature": "AI Content Generation"},
            re.compile(r"/api/ai-suggestions/.*"): {"flag": "AI_SUGGESTIONS", "feature": "AI Suggestions"},
            
            # Image generation and editing
            re.compile(r".*/generate-image.*"): {"flag": "IMAGE_GENERATION", "feature": "Image Generation"},
            re.compile(r".*/edit-image.*"): {"flag": "IMAGE_GENERATION", "feature": "Image Generation"},
            re.compile(r".*/regenerate-image.*"): {"flag": "IMAGE_GENERATION", "feature": "Image Generation"},
            
            # Autonomous features
            re.compile(r"/api/autonomous/.*"): {"flag": "AUTONOMOUS_FEATURES", "feature": "Autonomous Features"},
            
            # Advanced workflows
            re.compile(r"/api/v?1?/workflow/.*"): {"flag": "ADVANCED_WORKFLOWS", "feature": "Advanced Workflows"},
            
            # Deep research capabilities
            re.compile(r"/api/v1/deep-research/.*"): {"flag": "ENABLE_DEEP_RESEARCH", "feature": "Deep Research"},
            
            # Administrative functions (CRITICAL for security)
            re.compile(r"/api/admin/.*"): {"flag": "ADMIN_ACCESS", "feature": "Administrative Access"},
            
            # Billing and financial operations
            re.compile(r"/api/billing/.*"): {"flag": "BILLING_MANAGEMENT", "feature": "Billing Management"},
            
            # Organization management (multi-tenant)
            re.compile(r"/api/organizations/.*"): {"flag": "ORGANIZATION_MANAGEMENT", "feature": "Organization Management"},
            
            # Advanced analytics and metrics
            re.compile(r"/api/dashboard-metrics/.*"): {"flag": "ADVANCED_ANALYTICS", "feature": "Advanced Analytics"},
            re.compile(r"/api/performance-dashboard/.*"): {"flag": "ADVANCED_ANALYTICS", "feature": "Advanced Analytics"},
            
            # Vector search and advanced memory
            re.compile(r"/api/vector-search/.*"): {"flag": "VECTOR_SEARCH", "feature": "Vector Search"},
            re.compile(r"/api/memory/.*(store|search|recommendations)"): {"flag": "ADVANCED_MEMORY", "feature": "Advanced Memory"},
            
            # AI social responses
            re.compile(r"/api/social-inbox/.*(generate-response|respond)"): {"flag": "AI_SOCIAL_RESPONSES", "feature": "AI Social Responses"},
        }
        
        # Endpoints that should always be allowed (health checks, auth, etc.)
        self.allowed_patterns: List[Pattern] = [
            re.compile(r"/health.*"),
            re.compile(r"/api/monitoring/.*"),
            re.compile(r"/api/auth/.*"),
            re.compile(r"/api/feature-flags/.*"),
            re.compile(r"/docs.*"),
            re.compile(r"/openapi.json"),
            re.compile(r"/redoc.*"),
            re.compile(r"/api/database/.*"),  # Database health checks
        ]

    async def __call__(self, request: Request, call_next):
        """Process request and enforce feature flags"""
        
        try:
            # Check if this is an always-allowed endpoint
            path = request.url.path
            
            for allowed_pattern in self.allowed_patterns:
                if allowed_pattern.match(path):
                    # Allow through without checking feature flags
                    response = await call_next(request)
                    return response
            
            # Check feature flag requirements
            for pattern, config in self.endpoint_patterns.items():
                if pattern.match(path):
                    flag_name = config["flag"]
                    feature_name = config["feature"]
                    
                    if not ff(flag_name):
                        logger.warning(f"Feature flag check failed for {path}: {flag_name}")
                        
                        return JSONResponse(
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            content={
                                "error": "feature_disabled",
                                "message": f"Feature '{feature_name}' is not enabled",
                                "flag": flag_name,
                                "enabled": False,
                                "path": path
                            }
                        )
                    
                    # Feature flag is enabled, continue
                    break
            
            # Process the request normally
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Global feature flag middleware error: {e}")
            # Don't block requests due to middleware errors
            response = await call_next(request)
            return response


class FeatureFlagStatusMiddleware:
    """
    Middleware to add feature flag status to response headers (for debugging)
    """
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
    
    async def __call__(self, request: Request, call_next):
        """Add feature flag status to response headers if in debug mode"""
        response = await call_next(request)
        
        if self.debug_mode:
            from backend.core.feature_flags import feature_flags
            
            # Add current feature flags to response headers for debugging
            flags = feature_flags()
            response.headers["X-Feature-Flags-Total"] = str(len(flags))
            response.headers["X-Feature-Flags-Enabled"] = str(sum(flags.values()))
            
            # Add specific flags that might be relevant to the request
            path = request.url.path
            if "/ai" in path or "/generate" in path:
                response.headers["X-AI-Features-Enabled"] = str(flags.get("AI_CONTENT_GENERATION", False))
            if "/admin" in path:
                response.headers["X-Admin-Access-Enabled"] = str(flags.get("ADMIN_ACCESS", False))
        
        return response


# Helper functions for integration

def get_feature_requirements_for_endpoint(path: str) -> Optional[Dict[str, str]]:
    """
    Get feature flag requirements for a specific endpoint path
    Useful for API documentation and client-side feature detection
    """
    middleware = GlobalFeatureFlagMiddleware()
    
    for pattern, config in middleware.endpoint_patterns.items():
        if pattern.match(path):
            return config
    
    return None


def validate_all_feature_flags() -> Dict[str, bool]:
    """
    Validate all feature flags are properly defined
    Returns dict of flag_name -> is_valid
    """
    from backend.core.feature_flags import feature_flags
    
    middleware = GlobalFeatureFlagMiddleware()
    flags = feature_flags()
    
    required_flags = set()
    for config in middleware.endpoint_patterns.values():
        required_flags.add(config["flag"])
    
    validation_results = {}
    for flag in required_flags:
        validation_results[flag] = flag in flags
    
    return validation_results


def get_feature_flag_coverage_report() -> Dict[str, any]:
    """
    Generate a coverage report for feature flag enforcement
    """
    middleware = GlobalFeatureFlagMiddleware()
    
    return {
        "total_patterns": len(middleware.endpoint_patterns),
        "protected_endpoints": list(middleware.endpoint_patterns.keys()),
        "allowed_patterns": len(middleware.allowed_patterns),
        "flags_in_use": list(set(config["flag"] for config in middleware.endpoint_patterns.values())),
        "coverage_summary": {
            "ai_features": sum(1 for config in middleware.endpoint_patterns.values() if "AI" in config["flag"]),
            "admin_features": sum(1 for config in middleware.endpoint_patterns.values() if "ADMIN" in config["flag"]),
            "premium_features": sum(1 for config in middleware.endpoint_patterns.values() if "ADVANCED" in config["flag"]),
        }
    }


# Integration with FastAPI app
def add_feature_flag_middleware(app, debug_mode: bool = False):
    """
    Add feature flag middleware to FastAPI app
    Call this in your main app setup
    """
    # Add global feature flag enforcement
    app.add_middleware(GlobalFeatureFlagMiddleware)
    
    # Add debug headers if in debug mode
    if debug_mode:
        app.add_middleware(FeatureFlagStatusMiddleware, debug_mode=True)
    
    logger.info("Feature flag middleware added to application")


# Endpoint for getting feature requirements (for API clients)
def create_feature_info_endpoint():
    """
    Create an endpoint that returns feature flag requirements
    Can be added to any router for client-side feature detection
    """
    from fastapi import APIRouter
    
    router = APIRouter()
    
    @router.get("/feature-requirements")
    async def get_feature_requirements():
        """Get feature flag requirements for all endpoints"""
        middleware = GlobalFeatureFlagMiddleware()
        
        requirements = {}
        for pattern, config in middleware.endpoint_patterns.items():
            requirements[pattern.pattern] = config
        
        return {
            "requirements": requirements,
            "current_flags": feature_flags(),
            "validation": validate_all_feature_flags()
        }
    
    return router