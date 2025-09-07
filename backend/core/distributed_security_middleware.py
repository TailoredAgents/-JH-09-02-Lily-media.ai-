"""
Distributed Security Middleware - P0-13b Implementation
Redis-only security middleware for distributed deployments without in-memory fallbacks
"""
import time
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime
import hashlib
import json

from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import os

from backend.services.distributed_rate_limiter import (
    distributed_rate_limiter, 
    RateLimitConfig, 
    RateLimitResult
)
from backend.core.constants import (
    DEFAULT_RATE_LIMIT_PER_MINUTE,
    DEFAULT_RATE_LIMIT_PER_HOUR,
    DEFAULT_BURST_LIMIT,
    PRODUCTION_RATE_LIMIT_PER_MINUTE,
    PRODUCTION_RATE_LIMIT_PER_HOUR,
    PRODUCTION_BURST_LIMIT,
    BURST_WINDOW_SECONDS,
    REQUEST_BODY_SCAN_LIMIT_BYTES
)

logger = logging.getLogger(__name__)

class DistributedRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Distributed Redis-only rate limiting middleware
    
    Key improvements for P0-13b:
    - Redis-only storage (no in-memory fallbacks)
    - Fail-closed security (deny on Redis errors)
    - Better distributed deployment support
    - Atomic operations via Lua scripts
    - Proper connection pooling
    """
    
    def __init__(self, app, 
                 requests_per_second: int = 10,
                 requests_per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE, 
                 requests_per_hour: int = DEFAULT_RATE_LIMIT_PER_HOUR,
                 burst_limit: int = DEFAULT_BURST_LIMIT,
                 environment: str = "production"):
        super().__init__(app)
        self.environment = environment.lower()
        
        # Rate limiting configuration
        self.rate_config = RateLimitConfig(
            requests_per_second=requests_per_second,
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            burst_limit=burst_limit,
            burst_window_seconds=BURST_WINDOW_SECONDS
        )
        
        # Initialize distributed rate limiter
        self._initialized = False
        
        logger.info(f"Distributed rate limiting initialized: {requests_per_minute}/min, "
                   f"{requests_per_hour}/hr, burst={burst_limit}, "
                   f"environment={environment}")
    
    async def _ensure_initialized(self):
        """Ensure rate limiter is initialized"""
        if not self._initialized:
            try:
                await distributed_rate_limiter.initialize()
                self._initialized = True
                logger.info("Distributed rate limiter initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize distributed rate limiter: {e}")
                if self.environment == "production":
                    # In production, we fail closed for security
                    raise RuntimeError(f"Rate limiting required for production: {e}")
                # In development, we might be more lenient
                logger.warning("Rate limiting unavailable in development mode")
    
    def get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Check for forwarded headers (from load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP if multiple
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                client_ip = real_ip
            else:
                # Fallback to direct connection
                client_ip = request.client.host if request.client else "unknown"
        
        # For authenticated requests, we could also use user ID
        # This provides per-user rate limiting in addition to IP-based
        user_agent = request.headers.get("User-Agent", "")
        
        # Create a compound identifier that's stable but not easily spoofed
        identifier_components = [client_ip]
        
        # Add user agent hash for additional uniqueness (optional)
        if user_agent and len(user_agent) > 10:  # Avoid empty/minimal user agents
            ua_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
            identifier_components.append(ua_hash)
        
        return ":".join(identifier_components)
    
    def get_organization_id(self, request: Request) -> Optional[str]:
        """Extract organization ID from request for tenant isolation"""
        # Check authorization header for JWT with org claim
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # In a real implementation, you would decode the JWT
                # and extract the organization ID claim
                # For now, we'll use a placeholder approach
                
                # Check for org ID in headers (custom header approach)
                org_id = request.headers.get("X-Organization-ID")
                if org_id:
                    return org_id
                
                # Could also check URL path for org context
                path_parts = request.url.path.split("/")
                if len(path_parts) > 3 and path_parts[1] == "org":
                    return path_parts[2]
                    
            except Exception as e:
                logger.debug(f"Failed to extract organization ID: {e}")
        
        return None
    
    def _is_exempt_request(self, request: Request) -> bool:
        """Check if request should be exempt from rate limiting"""
        exempt_paths = [
            "/health", "/ready", "/metrics", 
            "/api/auth/refresh",
            "/docs", "/redoc", "/openapi.json",
            "/api/auth/csrf-token"  # CSRF token endpoint
        ]
        
        # Exempt OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return True
        
        # Check exact path matches
        if request.url.path in exempt_paths:
            return True
        
        # Check pattern matches
        path = request.url.path
        if path.startswith("/static/") or path.startswith("/assets/"):
            return True
        
        return False
    
    async def _create_rate_limit_response(
        self, 
        identifier: str, 
        rate_limit_info: Any,
        org_id: Optional[str] = None
    ) -> JSONResponse:
        """Create rate limit exceeded response"""
        
        logger.warning(f"Rate limit exceeded for {identifier} (org: {org_id}): {rate_limit_info.message}")
        
        headers = {
            "Retry-After": str(rate_limit_info.retry_after or 60),
            "X-RateLimit-Limit": str(getattr(self.rate_config, f"requests_per_{rate_limit_info.limit_type or 'minute'}", 60)),
            "X-RateLimit-Remaining": str(rate_limit_info.remaining),
            "X-RateLimit-Reset": str(int(rate_limit_info.reset_time)),
            "X-RateLimit-Type": rate_limit_info.limit_type or "unknown"
        }
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": rate_limit_info.message or "Too many requests",
                "retry_after": rate_limit_info.retry_after or 60,
                "limit_type": rate_limit_info.limit_type or "minute"
            },
            headers=headers
        )
    
    async def _add_rate_limit_headers(
        self, 
        response: Response, 
        identifier: str,
        org_id: Optional[str] = None
    ) -> Response:
        """Add rate limit headers to successful responses"""
        try:
            # Get current rate limit status
            status_info = await distributed_rate_limiter.get_rate_limit_status(identifier, org_id)
            
            if "remaining" in status_info:
                remaining = status_info["remaining"]
                limits = status_info["limits"]
                
                response.headers["X-RateLimit-Limit-Minute"] = str(limits.get("minute", 60))
                response.headers["X-RateLimit-Remaining-Minute"] = str(remaining.get("minute", 0))
                response.headers["X-RateLimit-Limit-Hour"] = str(limits.get("hour", 1000))
                response.headers["X-RateLimit-Remaining-Hour"] = str(remaining.get("hour", 0))
                
                # Add reset time for next window
                next_reset = int(time.time() + 60)  # Next minute
                response.headers["X-RateLimit-Reset"] = str(next_reset)
        
        except Exception as e:
            logger.debug(f"Failed to add rate limit headers: {e}")
            # Don't fail the request for header issues
        
        return response
    
    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method"""
        try:
            # Check if request is exempt
            if self._is_exempt_request(request):
                return await call_next(request)
            
            # Ensure rate limiter is initialized
            await self._ensure_initialized()
            
            # Get client identifier and organization
            identifier = self.get_client_identifier(request)
            org_id = self.get_organization_id(request)
            
            # Check rate limits
            rate_limit_info = await distributed_rate_limiter.check_rate_limit(
                identifier=identifier,
                org_id=org_id,
                config=self.rate_config
            )
            
            # Handle rate limiting results
            if rate_limit_info.result == RateLimitResult.RATE_LIMITED:
                return await self._create_rate_limit_response(identifier, rate_limit_info, org_id)
            
            elif rate_limit_info.result == RateLimitResult.REDIS_ERROR:
                # For distributed systems, we fail closed on Redis errors
                if self.environment == "production":
                    logger.error(f"Rate limiting service unavailable - denying request from {identifier}")
                    return JSONResponse(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content={
                            "error": "Service temporarily unavailable",
                            "message": "Rate limiting service is unavailable",
                            "retry_after": 60
                        },
                        headers={"Retry-After": "60"}
                    )
                else:
                    # In development, log warning but allow request
                    logger.warning(f"Rate limiting unavailable in development - allowing request from {identifier}")
            
            # Process request normally
            response = await call_next(request)
            
            # Add rate limiting headers to response
            if rate_limit_info.result == RateLimitResult.ALLOWED:
                response = await self._add_rate_limit_headers(response, identifier, org_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Distributed rate limit middleware error: {e}")
            
            # In production, fail closed for security
            if self.environment == "production":
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "error": "Service temporarily unavailable", 
                        "message": "Security middleware encountered an error"
                    }
                )
            else:
                # In development, allow request to continue
                return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses - unchanged from original"""
    
    def __init__(self, app, environment: str = "production"):
        super().__init__(app)
        self.environment = environment.lower()
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            
            # Security headers for production
            if self.environment == "production":
                # Prevent XSS attacks
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["X-XSS-Protection"] = "1; mode=block"
                
                # HTTPS enforcement
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                
                # Content Security Policy
                csp = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://api.openai.com https://google.serper.dev"
                response.headers["Content-Security-Policy"] = csp
                
                # Referrer policy
                response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                
            # Remove server information
            if "server" in response.headers:
                del response.headers["server"]
            
            # Add custom security header
            response.headers["X-Security-Headers"] = "enabled"
            response.headers["X-Rate-Limit-Backend"] = "redis-distributed"
            
            return response
        except Exception as e:
            logger.error(f"Security headers middleware error: {e}")
            # Return a safe error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error", "message": "Security middleware encountered an error"}
            )

def setup_distributed_security_middleware(app, environment: str = "production"):
    """
    Setup distributed security middleware stack
    
    This replaces the original setup_security_middleware for P0-13b compliance
    """
    
    logger.info(f"Setting up DISTRIBUTED security middleware for {environment} environment")
    
    try:
        # Import CSRF protection if available
        try:
            from backend.core.csrf_protection import CSRFProtectionMiddleware
            CSRF_AVAILABLE = True
        except ImportError:
            CSRF_AVAILABLE = False
        
        # 1. CSRF Protection (first layer)
        if CSRF_AVAILABLE:
            csrf_enabled = os.getenv("CSRF_PROTECTION_ENABLED", "true").lower() == "true"
            if csrf_enabled:
                app.add_middleware(CSRFProtectionMiddleware)
                logger.info("✅ CSRF protection middleware added")
            else:
                logger.warning("⚠️  CSRF protection disabled via configuration")
        else:
            logger.warning("⚠️  CSRF protection middleware not available")
        
        # 2. Request validation (security scanning)
        from backend.core.security_middleware import RequestValidationMiddleware
        app.add_middleware(RequestValidationMiddleware)
        logger.info("✅ Request validation middleware added")
        
        # 3. DISTRIBUTED rate limiting (Redis-only)
        # Use production-appropriate defaults
        default_per_minute = PRODUCTION_RATE_LIMIT_PER_MINUTE if environment == "production" else DEFAULT_RATE_LIMIT_PER_MINUTE
        default_per_hour = PRODUCTION_RATE_LIMIT_PER_HOUR if environment == "production" else DEFAULT_RATE_LIMIT_PER_HOUR
        default_burst = PRODUCTION_BURST_LIMIT if environment == "production" else DEFAULT_BURST_LIMIT
        
        requests_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", default_per_minute))
        requests_per_hour = int(os.getenv("RATE_LIMIT_PER_HOUR", default_per_hour))
        burst_limit = int(os.getenv("RATE_LIMIT_BURST", default_burst))
        requests_per_second = int(os.getenv("RATE_LIMIT_PER_SECOND", 10))
        
        app.add_middleware(
            DistributedRateLimitMiddleware,
            requests_per_second=requests_per_second,
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            burst_limit=burst_limit,
            environment=environment
        )
        logger.info(f"✅ DISTRIBUTED rate limiting middleware added: {requests_per_minute}/min, "
                   f"{requests_per_hour}/hr, burst={burst_limit}, {requests_per_second}/sec")
        
        # 4. Security headers
        app.add_middleware(SecurityHeadersMiddleware, environment=environment)
        logger.info("✅ Security headers middleware added")
        
        # 5. CORS (if needed)
        from backend.core.security_middleware import get_cors_middleware_config
        cors_config = get_cors_middleware_config(environment)
        if cors_config:
            app.add_middleware(CORSMiddleware, **cors_config)
            logger.info("✅ CORS middleware added")
        else:
            logger.info("CORS middleware skipped (no config)")
        
        # 6. Trusted hosts (production only)
        from backend.core.security_middleware import get_trusted_host_middleware
        trusted_host_config = get_trusted_host_middleware(environment)
        if trusted_host_config:
            app.add_middleware(TrustedHostMiddleware, **trusted_host_config)
            logger.info("✅ Trusted host middleware added")
        else:
            logger.info("Trusted host middleware skipped (development mode)")
        
        logger.info("🔒 DISTRIBUTED security middleware setup completed - Redis-only rate limiting active")
        
    except Exception as e:
        logger.error(f"❌ Critical error during distributed security middleware setup: {e}")
        raise  # Re-raise to prevent application startup with broken security