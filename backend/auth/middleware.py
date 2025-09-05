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
        self.token_cache = {}  # Simple in-memory cache for validated tokens
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.blacklisted_tokens = set()  # Token blacklist
        self.user_request_counts = {}  # Rate limiting per user
        self.rate_limit_window = 300  # 5 minutes
        self.max_requests_per_window = 1000  # Max requests per user per window
        
        logger.info("JWTValidationMiddleware initialized with caching and rate limiting")
    
    def _is_token_cached_and_valid(self, token: str) -> Optional[Dict[str, Any]]:
        """Check if token is cached and still valid"""
        if token in self.token_cache:
            cached_data = self.token_cache[token]
            if time.time() < cached_data['expires_at']:
                return cached_data['payload']
            else:
                # Remove expired token from cache
                del self.token_cache[token]
        return None
    
    def _cache_token(self, token: str, payload: Dict[str, Any]):
        """Cache validated token with TTL"""
        self.token_cache[token] = {
            'payload': payload,
            'expires_at': time.time() + self.cache_ttl
        }
        
        # Clean up cache periodically (simple cleanup)
        if len(self.token_cache) > 1000:
            current_time = time.time()
            expired_tokens = [
                token for token, data in self.token_cache.items() 
                if current_time >= data['expires_at']
            ]
            for expired_token in expired_tokens:
                del self.token_cache[expired_token]
    
    def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        return token in self.blacklisted_tokens
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit"""
        current_time = time.time()
        
        if user_id not in self.user_request_counts:
            self.user_request_counts[user_id] = []
        
        # Clean up old entries
        self.user_request_counts[user_id] = [
            timestamp for timestamp in self.user_request_counts[user_id]
            if current_time - timestamp < self.rate_limit_window
        ]
        
        # Check if user has exceeded limit
        if len(self.user_request_counts[user_id]) >= self.max_requests_per_window:
            return False
        
        # Add current request
        self.user_request_counts[user_id].append(current_time)
        return True
    
    def _extract_token_from_request(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers"""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        
        if not auth_header.startswith("Bearer "):
            return None
        
        return auth_header[7:]  # Remove "Bearer " prefix
    
    def _validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token using Auth0 or local validation"""
        # Check cache first
        cached_payload = self._is_token_cached_and_valid(token)
        if cached_payload:
            return cached_payload
        
        # Check blacklist
        if self._is_token_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        # Try Auth0 validation first
        try:
            payload = auth0_verifier.verify_token(token)
            self._cache_token(token, payload)
            logger.info(f"Successfully validated Auth0 token for user: {payload.get('sub')}")
            return payload
        except HTTPException as auth0_error:
            logger.warning(f"Auth0 validation failed: {auth0_error.detail}")
            
            # Fallback to local JWT validation
            try:
                payload = jwt_handler.verify_token(token)
                self._cache_token(token, payload)
                logger.info(f"Successfully validated local JWT token for user: {payload.get('sub')}")
                return payload
            except HTTPException as local_error:
                logger.error(f"Both Auth0 and local JWT validation failed. Auth0: {auth0_error.detail}, Local: {local_error.detail}")
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
            payload = self._validate_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                logger.error("Token payload missing 'sub' claim")
                return self._create_error_response(
                    status.HTTP_401_UNAUTHORIZED,
                    "Invalid token payload"
                )
            
            # Check rate limit
            if not self._check_rate_limit(user_id):
                logger.warning(f"Rate limit exceeded for user: {user_id}")
                return self._create_error_response(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "Rate limit exceeded. Please try again later."
                )
            
            # Add user information to request state
            request.state.user_id = user_id
            request.state.user_email = payload.get("email")
            request.state.user_payload = payload
            request.state.auth_method = "auth0" if "@" in user_id else "local"
            
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
    
    def blacklist_token(self, token: str):
        """Add token to blacklist"""
        self.blacklisted_tokens.add(token)
        # Remove from cache if present
        if token in self.token_cache:
            del self.token_cache[token]
        logger.info("Token added to blacklist")
    
    def clear_user_cache(self, user_id: str):
        """Clear cached tokens for a specific user"""
        tokens_to_remove = []
        for token, data in self.token_cache.items():
            if data['payload'].get('sub') == user_id:
                tokens_to_remove.append(token)
        
        for token in tokens_to_remove:
            del self.token_cache[token]
        
        logger.info(f"Cleared cache for user: {user_id}")
    
    def get_middleware_stats(self) -> Dict[str, Any]:
        """Get middleware performance statistics"""
        current_time = time.time()
        active_cache_count = sum(
            1 for data in self.token_cache.values() 
            if current_time < data['expires_at']
        )
        
        return {
            "cached_tokens": active_cache_count,
            "blacklisted_tokens": len(self.blacklisted_tokens),
            "active_users": len(self.user_request_counts),
            "cache_hit_ratio": "Not implemented",  # Could be added with counters
            "total_cache_size": len(self.token_cache)
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
    
    return jwt_middleware._validate_token(token)

@lru_cache(maxsize=100)
def get_jwks_cache_status():
    """Get JWKS cache status for monitoring"""
    try:
        jwks = auth0_verifier.get_jwks()
        return {
            "status": "healthy",
            "keys_count": len(jwks.get("keys", [])),
            "last_updated": time.time()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "last_updated": time.time()
        }