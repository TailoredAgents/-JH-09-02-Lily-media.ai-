"""
Distributed Authentication Middleware - P0-13c Integration
Enhanced authentication with distributed session management and token blacklisting
"""
import logging
import time
from typing import Optional, Dict, Any, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.services.distributed_session_manager import (
    distributed_session_manager,
    RevocationReason,
    SessionState
)
from backend.core.security import jwt_handler
from backend.db.models import User
from backend.db.database import get_db

logger = logging.getLogger(__name__)

class DistributedAuthMiddleware(BaseHTTPMiddleware):
    """
    Enhanced authentication middleware with distributed session management
    
    Features:
    - Distributed session validation across app instances
    - Real-time token blacklist checking
    - Session activity tracking
    - Suspicious activity detection
    - Automatic session cleanup
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.exempt_paths = {
            "/health", "/ready", "/metrics", "/docs", "/redoc", "/openapi.json",
            "/api/auth/login", "/api/auth/register", "/api/auth/forgot-password",
            "/api/auth/reset-password", "/api/auth/verify-email", "/api/auth/csrf-token",
            "/", "/render-health"
        }
    
    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch with distributed session validation"""
        
        # Skip authentication for exempt paths
        if self._is_exempt_path(request.url.path):
            return await call_next(request)
        
        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        try:
            # Initialize session manager
            if not distributed_session_manager.is_initialized:
                await distributed_session_manager.initialize()
            
            # Extract and validate tokens
            auth_result = await self._validate_authentication(request)
            
            if auth_result["authenticated"]:
                # Add user info to request state
                request.state.user_id = auth_result["user_id"]
                request.state.session_id = auth_result.get("session_id")
                request.state.organization_id = auth_result.get("organization_id")
                
                # Update session activity
                if auth_result.get("session_id"):
                    await distributed_session_manager.update_session_activity(
                        auth_result["session_id"]
                    )
                
                # Process request normally
                response = await call_next(request)
                
                # Add session info to response headers
                self._add_session_headers(response, auth_result)
                
                return response
            else:
                # Authentication failed
                return self._create_auth_error_response(auth_result)
                
        except Exception as e:
            logger.error(f"Distributed auth middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Authentication service unavailable",
                    "message": "Authentication middleware encountered an error"
                }
            )
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from authentication"""
        # Exact path matches
        if path in self.exempt_paths:
            return True
        
        # Pattern matches
        if path.startswith("/static/") or path.startswith("/assets/"):
            return True
        
        # Check for public API endpoints
        if path.startswith("/api/public/"):
            return True
        
        return False
    
    async def _validate_authentication(self, request: Request) -> Dict[str, Any]:
        """
        Validate authentication with distributed session management
        
        Returns:
            Dictionary with authentication result and details
        """
        result = {
            "authenticated": False,
            "user_id": None,
            "session_id": None,
            "organization_id": None,
            "error": None,
            "reason": None
        }
        
        # Extract tokens from request
        access_token = self._extract_access_token(request)
        refresh_token = request.cookies.get("refresh_token")
        
        if not access_token:
            result["error"] = "No access token provided"
            result["reason"] = "missing_token"
            return result
        
        try:
            # Check if token is blacklisted
            if await distributed_session_manager.is_token_blacklisted(access_token):
                result["error"] = "Token has been revoked"
                result["reason"] = "blacklisted_token"
                return result
            
            # Verify token signature and expiry
            try:
                payload = jwt_handler.verify_token(access_token)
            except HTTPException as e:
                # Token is invalid or expired, try refresh if available
                if refresh_token and e.status_code == status.HTTP_401_UNAUTHORIZED:
                    return await self._attempt_token_refresh(request, refresh_token)
                
                result["error"] = "Invalid or expired access token"
                result["reason"] = "invalid_token"
                return result
            
            # Extract user information from token
            user_id = int(payload.get("sub"))
            session_id = payload.get("session_id")
            
            if not user_id:
                result["error"] = "Invalid token payload"
                result["reason"] = "invalid_payload"
                return result
            
            # Validate session if session_id is present
            if session_id:
                session_info = await distributed_session_manager.get_session(session_id)
                
                if not session_info:
                    result["error"] = "Session not found"
                    result["reason"] = "session_not_found"
                    return result
                
                if not session_info.is_active():
                    result["error"] = f"Session is {session_info.state.value}"
                    result["reason"] = f"session_{session_info.state.value}"
                    
                    # If session was revoked, blacklist the token
                    if session_info.state == SessionState.REVOKED:
                        await distributed_session_manager.blacklist_token(
                            access_token,
                            user_id,
                            session_id,
                            session_info.revocation_reason or RevocationReason.ADMIN_REVOKE
                        )
                    
                    return result
                
                # Check for suspicious activity
                if await self._detect_suspicious_activity(request, session_info):
                    # Revoke session and blacklist token
                    await distributed_session_manager.revoke_session(
                        session_id,
                        RevocationReason.SUSPICIOUS_ACTIVITY
                    )
                    await distributed_session_manager.blacklist_token(
                        access_token,
                        user_id,
                        session_id,
                        RevocationReason.SUSPICIOUS_ACTIVITY
                    )
                    
                    result["error"] = "Suspicious activity detected"
                    result["reason"] = "suspicious_activity"
                    return result
                
                result["session_id"] = session_id
                result["organization_id"] = session_info.organization_id
            
            # All checks passed
            result["authenticated"] = True
            result["user_id"] = user_id
            
            return result
            
        except Exception as e:
            logger.error(f"Authentication validation error: {e}")
            result["error"] = "Authentication validation failed"
            result["reason"] = "validation_error"
            return result
    
    def _extract_access_token(self, request: Request) -> Optional[str]:
        """Extract access token from Authorization header"""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        
        if not auth_header.startswith("Bearer "):
            return None
        
        return auth_header[7:]  # Remove "Bearer " prefix
    
    async def _attempt_token_refresh(self, request: Request, refresh_token: str) -> Dict[str, Any]:
        """
        Attempt to refresh access token
        
        Args:
            request: FastAPI request
            refresh_token: Refresh token from cookie
            
        Returns:
            Authentication result after refresh attempt
        """
        result = {
            "authenticated": False,
            "user_id": None,
            "session_id": None,
            "organization_id": None,
            "error": None,
            "reason": None,
            "refreshed": False
        }
        
        try:
            # Check if refresh token is blacklisted
            if await distributed_session_manager.is_token_blacklisted(refresh_token):
                result["error"] = "Refresh token has been revoked"
                result["reason"] = "blacklisted_refresh_token"
                return result
            
            # Verify refresh token
            try:
                payload = jwt_handler.verify_token(refresh_token)
            except HTTPException:
                result["error"] = "Invalid or expired refresh token"
                result["reason"] = "invalid_refresh_token"
                return result
            
            # Ensure this is a refresh token
            if payload.get("type") != "refresh":
                result["error"] = "Invalid token type"
                result["reason"] = "invalid_token_type"
                return result
            
            user_id = int(payload.get("sub"))
            session_id = payload.get("session_id")
            
            # Validate session
            if session_id:
                session_info = await distributed_session_manager.get_session(session_id)
                if not session_info or not session_info.is_active():
                    result["error"] = "Session is no longer valid"
                    result["reason"] = "invalid_session"
                    return result
            
            # Rotate refresh token (security best practice)
            new_refresh_token = await distributed_session_manager.rotate_refresh_token(
                refresh_token, user_id, session_id
            )
            
            if not new_refresh_token:
                result["error"] = "Failed to rotate refresh token"
                result["reason"] = "rotation_failed"
                return result
            
            # Generate new access token
            token_data = {"sub": str(user_id), "session_id": session_id}
            new_access_token = jwt_handler.create_access_token(token_data)
            
            # Update request state for the new token
            result["authenticated"] = True
            result["user_id"] = user_id
            result["session_id"] = session_id
            result["refreshed"] = True
            result["new_access_token"] = new_access_token
            result["new_refresh_token"] = new_refresh_token
            
            return result
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            result["error"] = "Token refresh failed"
            result["reason"] = "refresh_error"
            return result
    
    async def _detect_suspicious_activity(self, request: Request, session_info) -> bool:
        """
        Detect suspicious activity patterns
        
        Args:
            request: FastAPI request
            session_info: Session information
            
        Returns:
            True if suspicious activity detected
        """
        try:
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("User-Agent", "")
            
            # Check for IP address changes
            original_ip = session_info.client_info.get("ip_address")
            if original_ip and original_ip != client_ip:
                # Allow for some flexibility (NAT, mobile networks, etc.)
                # But flag significant changes
                logger.warning(f"IP change detected for session {session_info.session_id}: "
                             f"{original_ip} -> {client_ip}")
                # For now, just log - could implement geolocation checks
            
            # Check for user agent changes
            original_ua = session_info.client_info.get("user_agent")
            if original_ua and original_ua != user_agent:
                # Significant user agent changes might indicate session hijacking
                if self._significant_ua_change(original_ua, user_agent):
                    logger.warning(f"Significant user agent change for session {session_info.session_id}")
                    return True
            
            # Check for unusual access patterns
            if session_info.access_count > 1000:  # Very high access count
                time_since_creation = time.time() - session_info.created_at
                if time_since_creation < 3600:  # High activity in short time
                    logger.warning(f"Unusually high activity for session {session_info.session_id}: "
                                 f"{session_info.access_count} requests in {time_since_creation/60:.1f} minutes")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Suspicious activity detection error: {e}")
            return False
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, handling proxies"""
        # Check for forwarded headers (from load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _significant_ua_change(self, original_ua: str, current_ua: str) -> bool:
        """Check if user agent change is significant enough to flag"""
        # Simple heuristic - could be made more sophisticated
        # Check for different browser families or major version changes
        
        # Extract browser name (simplified)
        def extract_browser(ua):
            ua_lower = ua.lower()
            if "chrome" in ua_lower and "chromium" not in ua_lower:
                return "chrome"
            elif "firefox" in ua_lower:
                return "firefox"
            elif "safari" in ua_lower and "chrome" not in ua_lower:
                return "safari"
            elif "edge" in ua_lower:
                return "edge"
            else:
                return "other"
        
        original_browser = extract_browser(original_ua)
        current_browser = extract_browser(current_ua)
        
        return original_browser != current_browser
    
    def _create_auth_error_response(self, auth_result: Dict[str, Any]) -> JSONResponse:
        """Create authentication error response"""
        error_message = auth_result.get("error", "Authentication required")
        reason = auth_result.get("reason", "authentication_failed")
        
        # Map reasons to appropriate HTTP status codes
        status_code = status.HTTP_401_UNAUTHORIZED
        if reason in ["blacklisted_token", "session_revoked", "suspicious_activity"]:
            status_code = status.HTTP_403_FORBIDDEN
        
        response_content = {
            "error": "Authentication failed",
            "message": error_message,
            "reason": reason
        }
        
        # Add refresh hint if token expired and refresh might work
        if reason in ["invalid_token", "session_expired"] and "refresh" not in reason:
            response_content["hint"] = "Try refreshing your authentication token"
        
        return JSONResponse(
            status_code=status_code,
            content=response_content,
            headers={
                "WWW-Authenticate": "Bearer",
                "X-Auth-Reason": reason
            }
        )
    
    def _add_session_headers(self, response, auth_result: Dict[str, Any]):
        """Add session information to response headers"""
        try:
            if auth_result.get("session_id"):
                response.headers["X-Session-ID"] = auth_result["session_id"][:16] + "..."  # Partial for security
            
            if auth_result.get("refreshed"):
                response.headers["X-Token-Refreshed"] = "true"
                
                # If tokens were refreshed, add them to response
                if auth_result.get("new_refresh_token"):
                    response.set_cookie(
                        key="refresh_token",
                        value=auth_result["new_refresh_token"],
                        httponly=True,
                        secure=True,
                        samesite="lax",
                        max_age=7*24*60*60  # 7 days
                    )
                
                if auth_result.get("new_access_token"):
                    # Note: In a real implementation, you might want to return 
                    # the new access token in the response body for the client to use
                    response.headers["X-New-Token-Available"] = "true"
            
            response.headers["X-Auth-Backend"] = "distributed-session"
            
        except Exception as e:
            logger.error(f"Error adding session headers: {e}")

def create_session_from_request(request: Request, user_id: int, organization_id: Optional[str] = None):
    """
    Helper function to create session from request context
    
    Args:
        request: FastAPI request
        user_id: User ID
        organization_id: Organization ID
        
    Returns:
        Session creation coroutine
    """
    auth_middleware = DistributedAuthMiddleware(None)
    client_ip = auth_middleware._get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")
    
    client_info = {
        "ip_address": client_ip,
        "user_agent": user_agent,
        "timestamp": time.time()
    }
    
    return distributed_session_manager.create_session(
        user_id=user_id,
        client_info=client_info,
        organization_id=organization_id
    )