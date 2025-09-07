"""
Content Safety Middleware

Intercepts content publication requests and applies safety validation
before content reaches social media platforms. Prevents brand damage
by blocking unsafe content and enforcing brand guidelines.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.services.content_safety_service import get_content_safety_service, SafetyLevel
from backend.core.observability import get_observability_manager

logger = logging.getLogger(__name__)
observability = get_observability_manager()


class ContentSafetyMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce content safety before publication"""
    
    def __init__(self, app):
        super().__init__(app)
        self.content_safety_service = get_content_safety_service()
        
        # Endpoints that require content safety validation
        self.protected_endpoints = {
            '/api/content/publish',
            '/api/content/schedule', 
            '/api/social-platforms/post',
            '/api/content/create',
            '/api/content/update'
        }
        
        # Content fields to validate in request bodies
        self.content_fields = ['content', 'text', 'caption', 'description', 'message']
        
    async def dispatch(self, request: Request, call_next):
        """Process request with content safety validation"""
        
        # Check if this endpoint needs content safety validation
        if not self._should_validate_content(request):
            return await call_next(request)
        
        # Extract content from request
        content_data = await self._extract_content_from_request(request)
        
        if content_data:
            # Perform safety validation
            safety_result = await self._validate_content_safety(request, content_data)
            
            # Block unsafe content
            if safety_result and not safety_result["publish_approved"]:
                return self._create_safety_blocked_response(safety_result, request)
            
            # Log safety validation for audit
            if safety_result:
                self._log_safety_validation(request, safety_result, content_data)
        
        # Proceed with request
        response = await call_next(request)
        
        return response
    
    def _should_validate_content(self, request: Request) -> bool:
        """Check if request needs content safety validation"""
        path = request.url.path
        method = request.method
        
        # Only validate POST/PUT requests to protected endpoints
        if method not in ["POST", "PUT", "PATCH"]:
            return False
            
        # Check if path matches protected endpoints
        for protected_path in self.protected_endpoints:
            if path.startswith(protected_path):
                return True
                
        return False
    
    async def _extract_content_from_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract content data from request body"""
        try:
            # Clone request body for processing
            body = await request.body()
            if not body:
                return None
                
            # Parse JSON body
            try:
                request_data = json.loads(body.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None
            
            # Extract content fields
            content_data = {}
            
            for field in self.content_fields:
                if field in request_data:
                    content_data[field] = request_data[field]
            
            # Add platform information if available
            if 'platform' in request_data:
                content_data['platform'] = request_data['platform']
            
            # Add user context if available
            if hasattr(request.state, 'current_user'):
                content_data['user_id'] = request.state.current_user.id
            
            return content_data if content_data else None
            
        except Exception as e:
            logger.warning(f"Failed to extract content from request: {e}")
            return None
    
    async def _validate_content_safety(self, request: Request, content_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate content safety"""
        try:
            # Get the main content text (try different field names)
            content_text = (
                content_data.get('content') or
                content_data.get('text') or 
                content_data.get('caption') or
                content_data.get('description') or
                content_data.get('message') or
                ""
            )
            
            if not content_text.strip():
                return None  # No content to validate
            
            # Perform safety analysis
            safety_result = await self.content_safety_service.analyze_content_safety(
                content_text=content_text,
                platform=content_data.get('platform', 'general'),
                user_id=content_data.get('user_id')
            )
            
            return {
                "content_text": content_text[:100] + "..." if len(content_text) > 100 else content_text,
                "safety_level": safety_result.safety_level.value,
                "brand_alignment_score": safety_result.brand_alignment_score,
                "publish_approved": safety_result.publish_approved,
                "review_required": safety_result.review_required,
                "violations": safety_result.violations,
                "recommendations": safety_result.recommendations,
                "confidence_score": safety_result.confidence_score,
                "platform": content_data.get('platform', 'general'),
                "validated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Content safety validation failed: {e}")
            
            # Return cautious result on error
            return {
                "content_text": "Content validation error",
                "safety_level": "caution",
                "brand_alignment_score": 0.5,
                "publish_approved": False,
                "review_required": True,
                "violations": [{"type": "validation_error", "message": "Safety validation failed"}],
                "recommendations": ["Manual review required due to validation error"],
                "confidence_score": 0.0,
                "error": str(e),
                "validated_at": datetime.utcnow().isoformat()
            }
    
    def _create_safety_blocked_response(self, safety_result: Dict[str, Any], request: Request) -> JSONResponse:
        """Create response for blocked content"""
        
        # Determine response based on safety level
        safety_level = safety_result.get("safety_level")
        
        if safety_level == "blocked":
            status_code = status.HTTP_403_FORBIDDEN
            message = "Content blocked due to safety policy violations"
        elif safety_level == "unsafe":
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY  
            message = "Content requires revision before publication"
        else:
            status_code = status.HTTP_400_BAD_REQUEST
            message = "Content does not meet publication standards"
        
        response_data = {
            "error": "content_safety_violation",
            "message": message,
            "details": {
                "safety_level": safety_result.get("safety_level"),
                "brand_alignment_score": safety_result.get("brand_alignment_score"),
                "violations": safety_result.get("violations", [])[:3],  # Limit for response size
                "recommendations": safety_result.get("recommendations", [])[:3],
                "review_required": safety_result.get("review_required", True)
            },
            "support": {
                "help_center": "https://help.lilymedia.ai/content-guidelines",
                "content_policy": "https://lilymedia.ai/content-policy",
                "contact_support": "support@lilymedia.ai"
            },
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    def _log_safety_validation(self, request: Request, safety_result: Dict[str, Any], content_data: Dict[str, Any]):
        """Log content safety validation for audit purposes"""
        
        user_id = content_data.get('user_id', 'unknown')
        platform = content_data.get('platform', 'general')
        safety_level = safety_result.get('safety_level')
        
        log_data = {
            "event_type": "content_safety_validation",
            "user_id": user_id,
            "platform": platform,
            "endpoint": request.url.path,
            "method": request.method,
            "safety_level": safety_level,
            "brand_alignment_score": safety_result.get("brand_alignment_score"),
            "publish_approved": safety_result.get("publish_approved"),
            "violations_count": len(safety_result.get("violations", [])),
            "confidence_score": safety_result.get("confidence_score"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if safety_level in ["blocked", "unsafe"]:
            logger.warning(f"Content safety violation detected", extra=log_data)
        elif safety_level == "caution":
            logger.info(f"Content flagged for review", extra=log_data)
        else:
            logger.debug(f"Content passed safety validation", extra=log_data)
        
        # Add Sentry breadcrumb for monitoring
        if observability:
            observability.add_sentry_breadcrumb(
                f"Content safety: {safety_level}",
                category="content_safety",
                data=log_data,
                level="warning" if safety_level in ["blocked", "unsafe"] else "info"
            )


def setup_content_safety_middleware(app):
    """Setup content safety middleware for the FastAPI app"""
    try:
        app.add_middleware(ContentSafetyMiddleware)
        logger.info("Content safety middleware configured successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup content safety middleware: {e}")
        return False