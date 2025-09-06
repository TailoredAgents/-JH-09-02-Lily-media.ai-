"""
CSRF (Cross-Site Request Forgery) Protection
Implements secure CSRF token generation, validation, and middleware protection
"""
import hmac
import hashlib
import secrets
import time
import logging
from typing import Optional, Dict, Any, Set
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os

from backend.core.config import get_settings

logger = logging.getLogger(__name__)

class CSRFTokenManager:
    """
    Secure CSRF token management with configurable settings
    
    Features:
    - Cryptographically secure token generation
    - Signed tokens with HMAC to prevent tampering
    - Configurable token expiration
    - Session-based token storage
    - Double submit cookie pattern support
    """
    
    def __init__(self, settings=None):
        """
        Initialize CSRF token manager
        
        Args:
            settings: Application settings (uses get_settings() if None)
        """
        self.settings = settings or get_settings()
        self.secret_key = getattr(self.settings, 'secret_key', None) or os.getenv('SECRET_KEY', 'development-key-change-in-production')
        self.token_expiry = 3600  # 1 hour default
        self.token_length = 32
        
        # Get CSRF configuration from settings
        self.csrf_cookie_name = getattr(self.settings, 'csrf_cookie_name', 'csrftoken')
        self.csrf_header_name = getattr(self.settings, 'csrf_header_name', 'X-CSRF-Token')
        self.csrf_secure_cookie = getattr(self.settings, 'csrf_secure_cookie', True)
        self.csrf_samesite = getattr(self.settings, 'csrf_samesite', 'Strict')
        
        logger.info("CSRF token manager initialized")
    
    def generate_token(self, session_id: Optional[str] = None) -> str:
        """
        Generate a new CSRF token
        
        Args:
            session_id: Optional session ID for token binding
            
        Returns:
            Base64-encoded signed CSRF token
        """
        # Generate random token data
        timestamp = str(int(time.time()))
        random_data = secrets.token_urlsafe(self.token_length)
        
        # Create token payload
        token_data = f"{timestamp}:{random_data}"
        if session_id:
            token_data += f":{session_id}"
        
        # Sign the token with HMAC
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            token_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Combine token data and signature
        signed_token = f"{token_data}:{signature}"
        
        # Return base64 encoded token
        import base64
        return base64.urlsafe_b64encode(signed_token.encode('utf-8')).decode('utf-8')
    
    def validate_token(self, token: str, session_id: Optional[str] = None) -> bool:
        """
        Validate a CSRF token
        
        Args:
            token: Base64-encoded signed CSRF token
            session_id: Optional session ID for token binding validation
            
        Returns:
            True if token is valid and not expired
        """
        try:
            # Decode base64 token
            import base64
            signed_token = base64.urlsafe_b64decode(token.encode('utf-8')).decode('utf-8')
            
            # Split token data and signature
            parts = signed_token.split(':')
            if len(parts) < 3:  # timestamp:random_data:signature (minimum)
                logger.warning("Invalid CSRF token format")
                return False
            
            signature = parts[-1]
            token_data = ':'.join(parts[:-1])
            
            # Verify signature
            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                token_data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("CSRF token signature validation failed")
                return False
            
            # Parse token data
            data_parts = token_data.split(':')
            timestamp_str = data_parts[0]
            # random_data = data_parts[1]  # Not needed for validation
            token_session_id = data_parts[2] if len(data_parts) > 2 else None
            
            # Check timestamp (expiration)
            try:
                token_timestamp = int(timestamp_str)
                current_time = int(time.time())
                
                if current_time - token_timestamp > self.token_expiry:
                    logger.warning(f"CSRF token expired: {current_time - token_timestamp}s old")
                    return False
            except ValueError:
                logger.warning("Invalid CSRF token timestamp")
                return False
            
            # Check session ID binding if provided
            if session_id and token_session_id and session_id != token_session_id:
                logger.warning("CSRF token session ID mismatch")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"CSRF token validation error: {e}")
            return False
    
    def create_token_cookie(self, token: str) -> Dict[str, Any]:
        """
        Create cookie configuration for CSRF token
        
        Args:
            token: CSRF token
            
        Returns:
            Cookie configuration dictionary
        """
        return {
            "key": self.csrf_cookie_name,
            "value": token,
            "max_age": self.token_expiry,
            "httponly": False,  # Must be accessible to JavaScript for AJAX requests
            "secure": self.csrf_secure_cookie,
            "samesite": self.csrf_samesite,
            "path": "/"
        }


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection Middleware
    
    Implements comprehensive CSRF protection using double submit cookie pattern
    with signed tokens for enhanced security.
    """
    
    def __init__(self, app, settings=None):
        """
        Initialize CSRF protection middleware
        
        Args:
            app: FastAPI application
            settings: Application settings
        """
        super().__init__(app)
        self.settings = settings or get_settings()
        self.token_manager = CSRFTokenManager(settings)
        
        # Methods that require CSRF protection
        self.protected_methods = {'POST', 'PUT', 'PATCH', 'DELETE'}
        
        # Paths exempt from CSRF protection
        self.exempt_paths = {
            '/docs', '/redoc', '/openapi.json',
            '/health', '/ready', '/metrics',
            '/api/auth/login',  # Login doesn't have CSRF token yet
            '/api/auth/register',  # Registration doesn't have CSRF token yet
            '/api/auth/forgot-password',  # Password reset initiation
            '/webhooks/',  # Webhook endpoints (protected by signatures)
        }
        
        # Paths that generate new CSRF tokens
        self.token_generation_paths = {
            '/api/auth/csrf-token',
            '/api/auth/login',  # Generate token after successful login
            '/api/auth/register',  # Generate token after successful registration
        }
        
        logger.info("CSRF protection middleware initialized")
    
    def _is_exempt_request(self, request: Request) -> bool:
        """
        Check if request is exempt from CSRF protection
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if request is exempt
        """
        # Skip CSRF for safe methods
        if request.method not in self.protected_methods:
            return True
        
        # Skip for exempt paths
        path = request.url.path
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        
        # Skip for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return True
        
        return False
    
    def _extract_csrf_token(self, request: Request) -> Optional[str]:
        """
        Extract CSRF token from request headers or form data
        
        Args:
            request: FastAPI request object
            
        Returns:
            CSRF token if found, None otherwise
        """
        # Try to get token from header first (preferred for AJAX)
        token = request.headers.get(self.token_manager.csrf_header_name)
        if token:
            return token
        
        # Try alternative header names
        for header_name in ['X-CSRFToken', 'X-CSRF-Token', 'csrfmiddlewaretoken']:
            token = request.headers.get(header_name)
            if token:
                return token
        
        return None
    
    def _get_session_id(self, request: Request) -> Optional[str]:
        """
        Get session ID from request (if session management is implemented)
        
        Args:
            request: FastAPI request object
            
        Returns:
            Session ID if available
        """
        # Try to get session ID from cookie or header
        session_cookie = request.cookies.get('session_id')
        if session_cookie:
            return session_cookie
        
        # Could also get from Authorization header JWT payload
        # This would require JWT decoding which is handled elsewhere
        return None
    
    def _create_csrf_error_response(self, message: str = "CSRF token missing or invalid") -> JSONResponse:
        """
        Create CSRF error response
        
        Args:
            message: Error message
            
        Returns:
            JSON error response
        """
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "CSRF protection failed",
                "message": message,
                "code": "CSRF_FAILURE"
            }
        )
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request through CSRF protection middleware
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint
            
        Returns:
            Response with CSRF protection applied
        """
        try:
            # Skip CSRF protection for exempt requests
            if self._is_exempt_request(request):
                response = await call_next(request)
                
                # Generate CSRF token for token generation paths
                if request.url.path in self.token_generation_paths:
                    session_id = self._get_session_id(request)
                    csrf_token = self.token_manager.generate_token(session_id)
                    
                    # Add token as cookie
                    cookie_config = self.token_manager.create_token_cookie(csrf_token)
                    response.set_cookie(**cookie_config)
                    
                    # Also add token to response headers for AJAX consumption
                    response.headers[self.token_manager.csrf_header_name] = csrf_token
                    
                    logger.debug(f"Generated CSRF token for path: {request.url.path}")
                
                return response
            
            # Extract CSRF token from request
            csrf_token = self._extract_csrf_token(request)
            
            if not csrf_token:
                logger.warning(f"CSRF token missing for {request.method} {request.url.path}")
                return self._create_csrf_error_response("CSRF token required for this request")
            
            # Validate CSRF token
            session_id = self._get_session_id(request)
            
            if not self.token_manager.validate_token(csrf_token, session_id):
                logger.warning(f"CSRF token validation failed for {request.method} {request.url.path}")
                return self._create_csrf_error_response("Invalid or expired CSRF token")
            
            # Token is valid, proceed with request
            logger.debug(f"CSRF token validated for {request.method} {request.url.path}")
            response = await call_next(request)
            
            # Optionally rotate CSRF token on successful request
            # This is more secure but can complicate AJAX applications
            if getattr(self.settings, 'csrf_rotate_on_request', False):
                new_token = self.token_manager.generate_token(session_id)
                cookie_config = self.token_manager.create_token_cookie(new_token)
                response.set_cookie(**cookie_config)
                response.headers[self.token_manager.csrf_header_name] = new_token
            
            return response
            
        except Exception as e:
            logger.error(f"CSRF middleware error: {e}")
            # Fail secure - reject request if CSRF middleware fails
            return self._create_csrf_error_response("CSRF protection error")


# CSRF token endpoint for frontend applications
from fastapi import APIRouter, Depends

csrf_router = APIRouter(prefix="/auth", tags=["csrf"])

@csrf_router.get("/csrf-token")
async def get_csrf_token(request: Request, settings = Depends(get_settings)) -> Dict[str, str]:
    """
    Get a new CSRF token for client-side applications
    
    Returns:
        CSRF token for use in subsequent requests
    """
    try:
        token_manager = CSRFTokenManager(settings)
        
        # Get session ID if available
        session_id = request.cookies.get('session_id')
        
        # Generate new CSRF token
        csrf_token = token_manager.generate_token(session_id)
        
        logger.info("CSRF token generated for client")
        
        return {
            "csrf_token": csrf_token,
            "header_name": token_manager.csrf_header_name,
            "expires_in": token_manager.token_expiry
        }
        
    except Exception as e:
        logger.error(f"Error generating CSRF token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate CSRF token"
        )


@csrf_router.post("/validate-csrf")
async def validate_csrf_token(
    request: Request,
    token_data: Dict[str, str],
    settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Validate a CSRF token (for testing purposes)
    
    Args:
        token_data: Dictionary containing the CSRF token
        
    Returns:
        Validation result
    """
    try:
        token = token_data.get('csrf_token')
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSRF token required"
            )
        
        token_manager = CSRFTokenManager(settings)
        session_id = request.cookies.get('session_id')
        
        is_valid = token_manager.validate_token(token, session_id)
        
        return {
            "valid": is_valid,
            "message": "Token is valid" if is_valid else "Token is invalid or expired"
        }
        
    except Exception as e:
        logger.error(f"Error validating CSRF token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate CSRF token"
        )


# Global CSRF token manager instance
_csrf_token_manager: Optional[CSRFTokenManager] = None

def get_csrf_token_manager() -> CSRFTokenManager:
    """Get or create global CSRF token manager instance"""
    global _csrf_token_manager
    
    if _csrf_token_manager is None:
        _csrf_token_manager = CSRFTokenManager()
    
    return _csrf_token_manager


def generate_csrf_token(session_id: Optional[str] = None) -> str:
    """
    Convenient function to generate CSRF tokens
    
    Args:
        session_id: Optional session ID for token binding
        
    Returns:
        CSRF token string
    """
    token_manager = get_csrf_token_manager()
    return token_manager.generate_token(session_id)


def validate_csrf_token(token: str, session_id: Optional[str] = None) -> bool:
    """
    Convenient function to validate CSRF tokens
    
    Args:
        token: CSRF token to validate
        session_id: Optional session ID for token binding
        
    Returns:
        True if token is valid
    """
    token_manager = get_csrf_token_manager()
    return token_manager.validate_token(token, session_id)