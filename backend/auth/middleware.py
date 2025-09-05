"""
Advanced JWT Validation Middleware for FastAPI
Provides comprehensive local JWT validation with enhanced error handling and caching
"""
import time
import logging
from typing import Optional, Dict, Any, Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import asyncio
from functools import lru_cache

# Auth0 removed - using local JWT authentication only
from backend.auth.jwt_handler import JWTHandler
from backend.core.config import get_settings
from backend.services.redis_cache import redis_cache

# Get logger (use application's logging configuration)
logger = logging.getLogger(__name__)

settings = get_settings()
jwt_handler = JWTHandler()

class JWTValidationMiddleware:
    """
    Advanced JWT Validation Middleware
    
    Features:
    - Local JWT token validation with caching
    - Request rate limiting per user
    - Comprehensive error logging and metrics
    - Token blacklist support
    - Automatic token refresh handling
    - CORS-compliant error responses
    """
    
    def __init__(self):
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.rate_limit_window = 300  # 5 minutes
        self.max_requests_per_window = 1000  # Max requests per user per window
        
        logger.info("JWTValidationMiddleware initialized with Redis caching and rate limiting")
    
    async def _is_token_cached_and_valid(self, token: str) -> Optional[Dict[str, Any]]:
        """Check if token is cached and still valid"""
        try:
            cached_data = await redis_cache.get("auth", "token_validation", resource_id=token)
            if cached_data:
                return cached_data
        except Exception as e:
            logger.warning(f"Redis token cache check failed: {e}")
        return None
    
    async def _cache_token(self, token: str, payload: Dict[str, Any]):
        """Cache validated token with TTL"""
        try:
            await redis_cache.set("auth", "token_validation", payload, resource_id=token, ttl=self.cache_ttl)
        except Exception as e:
            logger.warning(f"Failed to cache token in Redis: {e}")
    
    async def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        try:
            blacklisted = await redis_cache.get("auth", "blacklist", resource_id=token)
            return blacklisted is not None
        except Exception as e:
            logger.warning(f"Redis blacklist check failed: {e}")
            return False
    
    async def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit using Redis"""
        try:
            current_time = time.time()
            key = f"rate_limit:{user_id}"
            
            # Get current request timestamps from Redis
            request_timestamps = await redis_cache.get("auth", "rate_limit", resource_id=key)
            if request_timestamps is None:
                request_timestamps = []
            
            # Clean up old entries
            request_timestamps = [
                timestamp for timestamp in request_timestamps
                if current_time - timestamp < self.rate_limit_window
            ]
            
            # Check if user has exceeded limit
            if len(request_timestamps) >= self.max_requests_per_window:
                return False
            
            # Add current request timestamp
            request_timestamps.append(current_time)
            
            # Store updated timestamps in Redis
            await redis_cache.set("auth", "rate_limit", request_timestamps, resource_id=key, ttl=self.rate_limit_window)
            
            return True
            
        except Exception as e:
            logger.warning(f"Redis rate limit check failed: {e}, allowing request")
            return True  # Fail open for availability
    
    def _extract_token_from_request(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers"""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        
        if not auth_header.startswith("Bearer "):
            return None
        
        return auth_header[7:]  # Remove "Bearer " prefix
    
    async def _validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token using local JWT validation"""
        # Check cache first
        cached_payload = await self._is_token_cached_and_valid(token)
        if cached_payload:
            return cached_payload
        
        # Check blacklist
        if await self._is_token_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        # Local JWT validation only
        try:
            payload = jwt_handler.verify_token(token)
            await self._cache_token(token, payload)
            logger.info(f"Successfully validated local JWT token for user: {payload.get('sub')}")
            return payload
        except HTTPException as local_error:
            logger.error(f"Local JWT validation failed: {local_error.detail}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    def _create_error_response(self, status_code: int, detail: str, headers: Optional[Dict[str, str]] = None) -> JSONResponse:
        """Create standardized error response"""
        response_data = {
            "error": "authentication_failed",
            "message": detail,
            "status_code": status_code,
            "timestamp": time.time()
        }
        
        response_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
        }
        
        if headers:
            response_headers.update(headers)
        
        return JSONResponse(
            content=response_data,
            status_code=status_code,
            headers=response_headers
        )
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Middleware execution"""
        start_time = time.time()
        
        # Skip validation for health checks and public endpoints
        if request.url.path in ["/", "/docs", "/redoc", "/openapi.json", "/api/health"]:
            return await call_next(request)
        
        # Skip validation for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Only validate API endpoints that require authentication
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
            
        # Skip auth endpoints themselves
        if request.url.path.startswith("/api/auth/"):
            return await call_next(request)
        
        try:
            # Extract token
            token = self._extract_token_from_request(request)
            
            if not token:
                logger.warning(f"No token provided for protected endpoint: {request.url.path}")
                return self._create_error_response(
                    status.HTTP_401_UNAUTHORIZED,
                    "Authentication token required",
                    {"WWW-Authenticate": "Bearer"}
                )
            
            # Validate token
            payload = await self._validate_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                logger.error("Token payload missing 'sub' claim")
                return self._create_error_response(
                    status.HTTP_401_UNAUTHORIZED,
                    "Invalid token payload"
                )
            
            # Check rate limit
            if not await self._check_rate_limit(user_id):
                logger.warning(f"Rate limit exceeded for user: {user_id}")
                return self._create_error_response(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "Rate limit exceeded. Please try again later."
                )
            
            # Add user information to request state
            request.state.user_id = user_id
            request.state.user_email = payload.get("email")
            request.state.user_payload = payload
            request.state.auth_method = "local"
            
            # Process request
            response = await call_next(request)
            
            # Add performance headers
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Auth-Method"] = request.state.auth_method
            
            logger.info(f"Successfully processed authenticated request for {user_id} in {process_time:.3f}s")
            
            return response
            
        except HTTPException as e:
            logger.error(f"Authentication failed for {request.url.path}: {e.detail}")
            return self._create_error_response(e.status_code, e.detail, e.headers)
        
        except Exception as e:
            logger.error(f"Unexpected error in JWT middleware: {str(e)}")
            return self._create_error_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Internal authentication error"
            )
    
    async def blacklist_token(self, token: str):
        """Add token to blacklist"""
        try:
            # Add to Redis blacklist with long TTL (24 hours)
            await redis_cache.set("auth", "blacklist", True, resource_id=token, ttl=86400)
            # Remove from token cache if present
            await redis_cache.delete("auth", "token_validation", resource_id=token)
            logger.info("Token added to blacklist")
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
    
    async def clear_user_cache(self, user_id: str):
        """Clear cached tokens for a specific user"""
        try:
            # Clear rate limit cache for the user
            await redis_cache.delete("auth", "rate_limit", resource_id=f"rate_limit:{user_id}")
            
            # Note: We can't easily iterate through all tokens to find user-specific ones in Redis
            # This would require storing a user->token mapping or using Redis patterns
            # For now, we'll log that the rate limit cache was cleared
            logger.info(f"Cleared rate limit cache for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to clear user cache: {e}")
    
    async def get_middleware_stats(self) -> Dict[str, Any]:
        """Get middleware performance statistics"""
        try:
            redis_stats = await redis_cache.get_cache_stats()
            return {
                "redis_connected": redis_stats.get("redis_connected", False),
                "redis_cache_stats": redis_stats,
                "middleware_type": "redis_distributed",
                "note": "Token and rate limit data stored in Redis for distributed access"
            }
        except Exception as e:
            logger.error(f"Failed to get middleware stats: {e}")
            return {
                "error": str(e),
                "middleware_type": "redis_distributed",
                "redis_connected": False
            }

# Singleton middleware instance
jwt_middleware = JWTValidationMiddleware()

# Dependency function for manual token validation in specific routes
async def validate_jwt_token(request: Request) -> Dict[str, Any]:
    """
    Dependency function for manual JWT validation in specific routes
    Use this when you need token validation outside of middleware
    """
    token = jwt_middleware._extract_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return await jwt_middleware._validate_token(token)

@lru_cache(maxsize=100)
def get_jwt_cache_status():
    """Get JWT cache status for monitoring"""
    try:
        # Check if JWT handler is functional
        jwt_handler.get_algorithm()  # Simple check
        return {
            "status": "healthy",
            "handler_type": "local_jwt",
            "last_updated": time.time()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "last_updated": time.time()
        }