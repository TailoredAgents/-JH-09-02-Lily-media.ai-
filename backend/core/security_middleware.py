"""
Security Middleware for Production
Implements security headers, CORS, rate limiting, and request validation
"""
import time
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta
import hashlib
import json

from fastapi import Request, Response, HTTPException, status
from .constants import (
    DEFAULT_RATE_LIMIT_PER_MINUTE,
    DEFAULT_RATE_LIMIT_PER_HOUR,
    DEFAULT_BURST_LIMIT,
    PRODUCTION_RATE_LIMIT_PER_MINUTE,
    PRODUCTION_RATE_LIMIT_PER_HOUR,
    PRODUCTION_BURST_LIMIT,
    BURST_WINDOW_SECONDS,
    REQUEST_BODY_SCAN_LIMIT_BYTES,
    RATE_LIMIT_REDIS_KEY_TTL_SECONDS,
    MINUTE_RATE_LIMIT_TTL_SECONDS,
    HOUR_RATE_LIMIT_TTL_SECONDS
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import os

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
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
            
            return response
        except Exception as e:
            logger.error(f"Security headers middleware error: {e}")
            # Return a safe error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error", "message": "Security middleware encountered an error"}
            )

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed rate limiting middleware for production scalability"""
    
    def __init__(self, app, 
                 requests_per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE, 
                 requests_per_hour: int = DEFAULT_RATE_LIMIT_PER_HOUR,
                 burst_limit: int = DEFAULT_BURST_LIMIT):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        
        # Always initialize in-memory storage as fallback
        self.minute_counts: Dict[str, deque] = defaultdict(deque)
        self.hour_counts: Dict[str, deque] = defaultdict(deque)
        self.burst_counts: Dict[str, List[float]] = defaultdict(list)
        
        # Try to use Redis for distributed rate limiting
        self.use_redis = False
        self.redis_client = None
        
        try:
            import redis.asyncio as redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            self.use_redis = True
            logger.info("Rate limiting using async Redis for distributed storage with memory fallback")
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory rate limiting only: {e}")
            self.use_redis = False
    
    async def _test_redis_connection(self) -> bool:
        """Test Redis connection health"""
        if not self.use_redis or not self.redis_client:
            return False
        try:
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection test failed: {e}")
            return False
        
    def _get_limit_for_type(self, limit_type: str) -> int:
        """Get the limit value for a given limit type"""
        if limit_type == "burst":
            return self.burst_limit
        elif limit_type == "minute": 
            return self.requests_per_minute
        elif limit_type == "hour":
            return self.requests_per_hour
        else:
            return 0
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address, handling proxies"""
        # Check for forwarded headers (from load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP if multiple
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
            
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    async def _redis_rate_check(self, client_ip: str) -> Optional[Dict[str, Any]]:
        """Redis-based rate limiting check using async operations"""
        if not self.use_redis or not await self._test_redis_connection():
            return self._memory_rate_check(client_ip)
        
        try:
            now = time.time()
            current_minute = int(now // 60)
            current_hour = int(now // 3600)
            
            # Redis keys for different time windows
            burst_key = f"rate_limit:{client_ip}:burst"
            minute_key = f"rate_limit:{client_ip}:minute:{current_minute}"
            hour_key = f"rate_limit:{client_ip}:hour:{current_hour}"
            
            # Check burst limit (sliding window)
            burst_count = await self.redis_client.zcard(burst_key)
            if burst_count >= self.burst_limit:
                return {
                    "limit_type": "burst", 
                    "retry_after": BURST_WINDOW_SECONDS,
                    "message": f"Burst limit exceeded: max {self.burst_limit} requests per {BURST_WINDOW_SECONDS} seconds"
                }
            
            # Check minute limit
            minute_count = await self.redis_client.get(minute_key) or 0
            if int(minute_count) >= self.requests_per_minute:
                return {
                    "limit_type": "minute",
                    "retry_after": 60,
                    "message": f"Rate limit exceeded: max {self.requests_per_minute} requests per minute"
                }
            
            # Check hour limit
            hour_count = await self.redis_client.get(hour_key) or 0
            if int(hour_count) >= self.requests_per_hour:
                return {
                    "limit_type": "hour",
                    "retry_after": HOUR_RATE_LIMIT_TTL_SECONDS - 100,  # slightly less than TTL
                    "message": f"Rate limit exceeded: max {self.requests_per_hour} requests per hour"
                }
            
            # Record this request in Redis using async pipeline
            pipe = self.redis_client.pipeline()
            
            # Burst counter (sliding window)
            pipe.zadd(burst_key, {str(now): now})
            pipe.zremrangebyscore(burst_key, 0, now - BURST_WINDOW_SECONDS)
            pipe.expire(burst_key, RATE_LIMIT_REDIS_KEY_TTL_SECONDS)
            
            # Minute counter
            pipe.incr(minute_key)
            pipe.expire(minute_key, MINUTE_RATE_LIMIT_TTL_SECONDS)
            
            # Hour counter  
            pipe.incr(hour_key)
            pipe.expire(hour_key, HOUR_RATE_LIMIT_TTL_SECONDS)
            
            await pipe.execute()
            
            return None  # Not rate limited
            
        except Exception as e:
            logger.warning(f"Redis rate limiting failed, falling back to memory: {e}")
            return self._memory_rate_check(client_ip)
    
    def _memory_rate_check(self, client_ip: str) -> Optional[Dict[str, Any]]:
        """Memory-based rate limiting fallback"""
        now = time.time()
        current_minute = int(now // 60)
        current_hour = int(now // 3600)
        
        # Clean old entries
        minute_deque = self.minute_counts[client_ip]
        while minute_deque and minute_deque[0] < current_minute:
            minute_deque.popleft()
            
        hour_deque = self.hour_counts[client_ip]
        while hour_deque and hour_deque[0] < current_hour:
            hour_deque.popleft()
        
        # Check burst limit (sliding window)
        burst_times = self.burst_counts[client_ip]
        burst_times[:] = [t for t in burst_times if now - t < BURST_WINDOW_SECONDS]
        
        # Rate limit checks
        if len(burst_times) >= self.burst_limit:
            return {
                "limit_type": "burst",
                "retry_after": BURST_WINDOW_SECONDS,
                "message": f"Burst limit exceeded: max {self.burst_limit} requests per {BURST_WINDOW_SECONDS} seconds"
            }
            
        if len(minute_deque) >= self.requests_per_minute:
            return {
                "limit_type": "minute",
                "retry_after": 60,
                "message": f"Rate limit exceeded: max {self.requests_per_minute} requests per minute"
            }
            
        if len(hour_deque) >= self.requests_per_hour:
            return {
                "limit_type": "hour",
                "retry_after": 3600,
                "message": f"Rate limit exceeded: max {self.requests_per_hour} requests per hour"
            }
        
        # Record this request
        minute_deque.append(current_minute)
        hour_deque.append(current_hour)
        burst_times.append(now)
        
        return None
    
    def _is_exempt_request(self, request: Request) -> bool:
        """Check if request should be exempt from rate limiting"""
        exempt_paths = [
            "/health", "/ready", "/metrics", 
            "/api/auth/refresh",
            "/docs", "/redoc", "/openapi.json"
        ]
        return request.url.path in exempt_paths or request.method == "OPTIONS"
    
    def _create_rate_limit_response(self, client_ip: str, limit_info: Dict[str, Any]) -> JSONResponse:
        """Create rate limit exceeded response"""
        logger.warning(f"Rate limit exceeded for {client_ip}: {limit_info['message']}")
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": limit_info["message"],
                "retry_after": limit_info["retry_after"]
            },
            headers={
                "Retry-After": str(limit_info["retry_after"]),
                "X-RateLimit-Limit": str(self._get_limit_for_type(limit_info['limit_type'])),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time() + limit_info["retry_after"]))
            }
        )
    
    def _add_rate_limit_headers(self, response: Response, client_ip: str) -> Response:
        """Add rate limit headers to successful responses"""
        minute_remaining = max(0, self.requests_per_minute - len(self.minute_counts[client_ip]))
        hour_remaining = max(0, self.requests_per_hour - len(self.hour_counts[client_ip]))
        
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(minute_remaining)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(hour_remaining)
        
        return response
    
    async def _handle_fallback_request(self, request: Request, call_next) -> JSONResponse:
        """Handle fallback request processing when rate limiting fails"""
        try:
            return await call_next(request)
        except Exception as inner_e:
            logger.error(f"Fallback request processing failed: {inner_e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error", "message": "Rate limiting middleware encountered an error"}
            )

    async def dispatch(self, request: Request, call_next):
        try:
            if self._is_exempt_request(request):
                return await call_next(request)
            
            client_ip = self.get_client_ip(request)
            limit_info = await self._redis_rate_check(client_ip)
            
            if limit_info:
                return self._create_rate_limit_response(client_ip, limit_info)
            
            response = await call_next(request)
            return self._add_rate_limit_headers(response, client_ip)
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            return await self._handle_fallback_request(request, call_next)

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate incoming requests for security threats"""
    
    def __init__(self, app):
        super().__init__(app)
        
        # Common SQL injection patterns
        self.sql_patterns = [
            "union select", "drop table", "delete from", "insert into",
            "update set", "create table", "alter table", "exec(",
            "execute(", "sp_executesql", "xp_cmdshell", "information_schema"
        ]
        
        # Common XSS patterns
        self.xss_patterns = [
            "<script", "javascript:", "onload=", "onerror=", "onclick=",
            "onmouseover=", "eval(", "expression(", "vbscript:", "data:text/html"
        ]
        
        # Path traversal patterns
        self.path_traversal_patterns = [
            "../", "..\\", "....//", "....\\\\", "/etc/passwd", 
            "/etc/shadow", "c:\\windows\\system32", ".htaccess"
        ]
    
    def check_suspicious_content(self, content: str) -> Optional[str]:
        """Check content for suspicious patterns"""
        content_lower = content.lower()
        
        # Check SQL injection
        for pattern in self.sql_patterns:
            if pattern in content_lower:
                return f"Potential SQL injection attempt: {pattern}"
        
        # Check XSS
        for pattern in self.xss_patterns:
            if pattern in content_lower:
                return f"Potential XSS attempt: {pattern}"
        
        # Check path traversal
        for pattern in self.path_traversal_patterns:
            if pattern in content_lower:
                return f"Potential path traversal attempt: {pattern}"
        
        return None
    
    async def dispatch(self, request: Request, call_next):
        try:
            # Skip validation for health checks and CORS preflight requests
            if request.url.path in ["/health", "/ready", "/metrics"] or request.method == "OPTIONS":
                return await call_next(request)
            
            # Check URL path
            try:
                suspicious = self.check_suspicious_content(str(request.url))
                if suspicious:
                    logger.warning(f"Suspicious request from {request.client.host if request.client else 'unknown'}: {suspicious}")
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"error": "Invalid request", "message": "Request contains suspicious content"}
                    )
            except Exception as e:
                logger.error(f"Error checking URL path: {e}")
            
            # Check query parameters
            try:
                for key, value in request.query_params.items():
                    suspicious = self.check_suspicious_content(f"{key}={value}")
                    if suspicious:
                        logger.warning(f"Suspicious query parameter from {request.client.host if request.client else 'unknown'}: {suspicious}")
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={"error": "Invalid request", "message": "Request contains suspicious content"}
                        )
            except Exception as e:
                logger.error(f"Error checking query parameters: {e}")
            
            # Check headers for suspicious content
            try:
                for header_name, header_value in request.headers.items():
                    if header_name.lower() not in ["authorization", "cookie", "user-agent"]:  # Skip sensitive headers
                        suspicious = self.check_suspicious_content(f"{header_name}: {header_value}")
                        if suspicious:
                            logger.warning(f"Suspicious header from {request.client.host if request.client else 'unknown'}: {suspicious}")
                            return JSONResponse(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                content={"error": "Invalid request", "message": "Request contains suspicious content"}
                            )
            except Exception as e:
                logger.error(f"Error checking headers: {e}")
            
            # For POST/PUT requests, check body (limited to prevent DoS)
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    # Only check first portion to prevent DoS
                    body = await request.body()
                    if len(body) > REQUEST_BODY_SCAN_LIMIT_BYTES:
                        body = body[:REQUEST_BODY_SCAN_LIMIT_BYTES]
                    
                    if body:
                        try:
                            body_str = body.decode('utf-8', errors='ignore')
                            suspicious = self.check_suspicious_content(body_str)
                            if suspicious:
                                logger.warning(f"Suspicious request body from {request.client.host if request.client else 'unknown'}: {suspicious}")
                                return JSONResponse(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"error": "Invalid request", "message": "Request contains suspicious content"}
                                )
                        except Exception as decode_e:
                            logger.debug(f"Could not decode request body for validation: {decode_e}")
                            # If we can't decode, skip body validation
                            pass
                except Exception as e:
                    logger.error(f"Error checking request body: {e}")
            
            # Process request normally
            response = await call_next(request)
            
            # Check if response is None (indicates endpoint didn't return anything)
            if response is None:
                logger.error(f"No response returned from endpoint: {request.method} {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"error": "Internal server error", "message": "No response returned."}
                )
            return response
            
        except Exception as e:
            logger.error(f"Request validation middleware error: {e}")
            # Fail open - allow request to continue if validation fails
            try:
                response = await call_next(request)
                
                # Check fallback response too
                if response is None:
                    logger.error(f"No response returned from fallback endpoint: {request.method} {request.url.path}")
                    return JSONResponse(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        content={"error": "Internal server error", "message": "No response returned."}
                    )
                return response
                
            except Exception as inner_e:
                logger.error(f"Fallback request processing failed: {inner_e}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"error": "Internal server error", "message": "Request validation middleware encountered an error"}
                )

def get_cors_middleware_config(environment: str = "production"):
    """Get CORS middleware configuration based on environment"""
    
    if environment.lower() == "development":
        # Development: Allow all origins
        return {
            "allow_origins": ["*"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"]
        }
    else:
        # Production: Restrict origins
        # Check both ALLOWED_ORIGINS and CORS_ORIGINS for compatibility
        allowed_origins_env = os.getenv("ALLOWED_ORIGINS") or os.getenv("CORS_ORIGINS", "")
        logger.info(f"Security middleware CORS - ALLOWED_ORIGINS: {os.getenv('ALLOWED_ORIGINS')}")
        logger.info(f"Security middleware CORS - CORS_ORIGINS: {os.getenv('CORS_ORIGINS')}")
        
        if allowed_origins_env:
            allowed_origins = allowed_origins_env.split(",")
            allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]
        else:
            allowed_origins = []
        
        if not allowed_origins:
            # Current production domains as defaults
            allowed_origins = [
                "https://socialmedia-frontend-pycc.onrender.com",
                "https://socialmedia-api-wxip.onrender.com",
                "https://www.lily-ai-socialmedia.com",
                "https://lily-ai-socialmedia.com",
                "https://localhost", 
                "http://localhost"
            ]
            logger.warning("No CORS environment variables found, using default origins including current production domains")
        
        logger.info(f"Security middleware CORS allowed origins: {allowed_origins}")
        
        return {
            "allow_origins": allowed_origins,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Accept",
                "Accept-Encoding",
                "Accept-Language",
                "Access-Control-Request-Headers",
                "Access-Control-Request-Method",
                "Cache-Control",
                "Connection",
                "Content-Language", 
                "Content-Type",
                "Authorization",
                "Origin",
                "Pragma",
                "Referer",
                "User-Agent",
                "X-Requested-With",
                "X-CSRF-Token",
                "X-Request-ID"
            ]
        }

def get_trusted_host_middleware(environment: str = "production"):
    """Get trusted host middleware configuration for production"""
    
    if environment.lower() == "development":
        # Development: Allow all hosts
        return None
    
    # Production: Restrict allowed hosts
    allowed_hosts = os.getenv("ALLOWED_HOSTS", "").split(",")
    allowed_hosts = [host.strip() for host in allowed_hosts if host.strip()]
    
    if not allowed_hosts:
        # Default to current production domains and common patterns
        allowed_hosts = [
            "localhost", 
            "127.0.0.1", 
            "socialmedia-api-wxip.onrender.com",
            "socialmedia-frontend-pycc.onrender.com",
            "lily-ai-socialmedia.com",
            "www.lily-ai-socialmedia.com",
            "*.herokuapp.com", 
            "*.render.com"
        ]
        logger.warning("No ALLOWED_HOSTS specified, using default patterns including current production domains")
    
    # Return configuration dict for middleware, not the class itself
    return {"allowed_hosts": allowed_hosts}

def setup_security_middleware(app, environment: str = "production"):
    """Setup all security middleware for the application"""
    
    logger.info(f"Setting up security middleware for {environment} environment")
    
    try:
        # 1. Request validation (first layer)
        try:
            app.add_middleware(RequestValidationMiddleware)
            logger.info("✅ Request validation middleware added")
        except Exception as e:
            logger.error(f"❌ Failed to add request validation middleware: {e}")
        
        # 2. Rate limiting with production-ready defaults
        try:
            # More generous defaults for SaaS applications
            default_per_minute = str(PRODUCTION_RATE_LIMIT_PER_MINUTE) if environment == "production" else str(DEFAULT_RATE_LIMIT_PER_MINUTE)
            default_per_hour = str(PRODUCTION_RATE_LIMIT_PER_HOUR) if environment == "production" else str(DEFAULT_RATE_LIMIT_PER_HOUR)
            default_burst = str(PRODUCTION_BURST_LIMIT) if environment == "production" else str(DEFAULT_BURST_LIMIT)
            
            requests_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", default_per_minute))
            requests_per_hour = int(os.getenv("RATE_LIMIT_PER_HOUR", default_per_hour))
            burst_limit = int(os.getenv("RATE_LIMIT_BURST", default_burst))
            
            app.add_middleware(
                RateLimitMiddleware,
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_hour,
                burst_limit=burst_limit
            )
            logger.info(f"✅ Rate limiting middleware added: {requests_per_minute}/min, {requests_per_hour}/hr, burst={burst_limit}")
        except Exception as e:
            logger.error(f"❌ Failed to add rate limiting middleware: {e}")
        
        # 3. Security headers
        try:
            app.add_middleware(SecurityHeadersMiddleware, environment=environment)
            logger.info("✅ Security headers middleware added")
        except Exception as e:
            logger.error(f"❌ Failed to add security headers middleware: {e}")
        
        # 4. CORS (if needed)
        try:
            cors_config = get_cors_middleware_config(environment)
            if cors_config:
                app.add_middleware(CORSMiddleware, **cors_config)
                logger.info("✅ CORS middleware added")
            else:
                logger.info("CORS middleware skipped (no config)")
        except Exception as e:
            logger.error(f"❌ Failed to add CORS middleware: {e}")
        
        # 5. Trusted hosts (production only)
        try:
            trusted_host_config = get_trusted_host_middleware(environment)
            if trusted_host_config:
                app.add_middleware(TrustedHostMiddleware, **trusted_host_config)
                logger.info("✅ Trusted host middleware added")
            else:
                logger.info("Trusted host middleware skipped (development mode)")
        except Exception as e:
            logger.error(f"❌ Failed to add trusted host middleware: {e}")
        
        logger.info("Security middleware setup completed")
        
    except Exception as e:
        logger.error(f"❌ Critical error during security middleware setup: {e}")
        logger.warning("Some security middleware may not be active")
    
    return app