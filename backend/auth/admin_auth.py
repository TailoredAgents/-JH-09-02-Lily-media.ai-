"""
Admin authentication system
Separate from regular user authentication for enhanced security
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from sqlalchemy.orm import Session
import uuid
import secrets
import pyotp
from ipaddress import ip_address, AddressValueError

from backend.core.config import get_settings
from backend.db.database import get_db
from backend.db.admin_models import AdminUser, AdminSession, AdminRole, AdminAuditLog
from backend.auth.dependencies import AuthUser

settings = get_settings()


class AdminAuthHandler:
    """Enhanced admin authentication with security features"""
    
    def __init__(self):
        self.secret_key = str(settings.jwt_secret.get_secret_value()) + "_ADMIN_SALT"  # Different from user JWT
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = 30  # Shorter for admins
        self.refresh_token_expire_days = 7   # Shorter refresh window
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 30
    
    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def generate_2fa_secret(self) -> str:
        """Generate 2FA secret for admin user"""
        return pyotp.random_base32()
    
    def verify_2fa_token(self, secret: str, token: str) -> bool:
        """Verify 2FA token"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=1)
        except Exception:
            return False
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token for admin"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "admin_access", "jti": str(uuid.uuid4())})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token for admin"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "admin_refresh", "jti": str(uuid.uuid4())})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = None) -> Dict[str, Any]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verify token type if specified
            if token_type and payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def get_client_info(self, request: Request) -> Dict[str, str]:
        """Extract client information from request"""
        return {
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "Unknown"),
            "location": self._get_location_from_ip(request)
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP considering proxies"""
        # Check for forwarded IP headers
        forwarded_ips = [
            request.headers.get("cf-connecting-ip"),  # Cloudflare
            request.headers.get("x-forwarded-for"),   # Standard proxy
            request.headers.get("x-real-ip"),         # Nginx
        ]
        
        for ip in forwarded_ips:
            if ip:
                # Take first IP if comma-separated
                ip = ip.split(",")[0].strip()
                try:
                    ip_address(ip)  # Validate IP
                    return ip
                except (AddressValueError, ValueError):
                    continue
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    def _get_location_from_ip(self, request: Request) -> Optional[str]:
        """Get location from IP (placeholder for GeoIP integration)"""
        # This could be enhanced with GeoIP database
        client_ip = self._get_client_ip(request)
        if client_ip in ["127.0.0.1", "localhost", "unknown"]:
            return "localhost"
        return "unknown"
    
    async def authenticate_admin(
        self, 
        email: str, 
        password: str, 
        totp_code: Optional[str], 
        request: Request,
        db: Session
    ) -> Tuple[AdminUser, Dict[str, str]]:
        """Authenticate admin user with enhanced security checks"""
        
        # Find admin user
        admin = db.query(AdminUser).filter(AdminUser.email == email).first()
        if not admin:
            await self._log_failed_attempt(email, "User not found", request, db)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if account is active
        if not admin.is_active:
            await self._log_failed_attempt(email, "Account inactive", request, db)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Check if account is locked
        if admin.locked_until and admin.locked_until > datetime.utcnow():
            await self._log_failed_attempt(email, "Account locked", request, db)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked until {admin.locked_until.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        # Verify password
        if not self.verify_password(password, admin.hashed_password):
            await self._handle_failed_login(admin, "Invalid password", request, db)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify 2FA if enabled
        if admin.two_factor_enabled:
            if not totp_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="2FA token required"
                )
            if not self.verify_2fa_token(admin.two_factor_secret, totp_code):
                await self._handle_failed_login(admin, "Invalid 2FA token", request, db)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid 2FA token"
                )
        
        # Authentication successful - reset failed attempts
        admin.failed_login_attempts = 0
        admin.locked_until = None
        admin.last_login = datetime.utcnow()
        
        # Create session tokens
        token_data = {
            "sub": admin.id,
            "email": admin.email,
            "username": admin.username,
            "role": admin.role.value,
            "is_superuser": admin.is_superuser
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        
        # Create session record
        client_info = self.get_client_info(request)
        session = AdminSession(
            admin_user_id=admin.id,
            session_token=access_token,
            refresh_token=refresh_token,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            location=client_info["location"],
            expires_at=datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        )
        
        db.add(session)
        db.commit()
        db.refresh(admin)
        
        # Log successful login
        await self._log_audit_event(
            admin.id, "ADMIN_LOGIN", "admin_session", session.id,
            {"ip_address": client_info["ip_address"], "user_agent": client_info["user_agent"]},
            request, db
        )
        
        return admin, {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60
        }
    
    async def _handle_failed_login(
        self, 
        admin: AdminUser, 
        reason: str, 
        request: Request, 
        db: Session
    ):
        """Handle failed login attempt with progressive lockout"""
        admin.failed_login_attempts += 1
        
        # Lock account after max attempts
        if admin.failed_login_attempts >= self.max_failed_attempts:
            admin.locked_until = datetime.utcnow() + timedelta(minutes=self.lockout_duration_minutes)
            reason += f" - Account locked for {self.lockout_duration_minutes} minutes"
        
        db.commit()
        await self._log_failed_attempt(admin.email, reason, request, db)
    
    async def _log_failed_attempt(
        self, 
        email: str, 
        reason: str, 
        request: Request, 
        db: Session
    ):
        """Log failed authentication attempt"""
        client_info = self.get_client_info(request)
        
        # This could be stored in a separate security log table
        # For now, we'll use the audit log
        audit_log = AdminAuditLog(
            admin_user_id="system",  # System generated
            action="FAILED_LOGIN",
            resource_type="authentication",
            resource_id=email,
            details={
                "reason": reason,
                "ip_address": client_info["ip_address"],
                "user_agent": client_info["user_agent"]
            },
            success=False,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )
        
        db.add(audit_log)
        db.commit()
    
    async def _log_audit_event(
        self,
        admin_user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Dict[str, Any],
        request: Request,
        db: Session
    ):
        """Log audit event"""
        client_info = self.get_client_info(request)
        
        audit_log = AdminAuditLog(
            admin_user_id=admin_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            success=True,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )
        
        db.add(audit_log)
        db.commit()
    
    async def logout_admin(
        self, 
        admin_id: str, 
        token: str, 
        request: Request, 
        db: Session
    ):
        """Logout admin and invalidate session"""
        # Find and invalidate session
        session = db.query(AdminSession).filter(
            AdminSession.admin_user_id == admin_id,
            AdminSession.session_token == token,
            AdminSession.is_active == True
        ).first()
        
        if session:
            session.is_active = False
            session.logout_at = datetime.utcnow()
            db.commit()
        
        # Log logout
        await self._log_audit_event(
            admin_id, "ADMIN_LOGOUT", "admin_session", session.id if session else "unknown",
            {"token_invalidated": bool(session)}, request, db
        )
    
    def generate_api_key(self) -> Tuple[str, str]:
        """Generate API key and secret for user"""
        # Generate a secure random API key (32 bytes = 64 hex chars)
        api_key = f"lily_{secrets.token_hex(32)}"
        
        # Generate API secret (64 bytes = 128 hex chars)  
        api_secret = secrets.token_hex(64)
        
        return api_key, api_secret
    
    def hash_api_secret(self, api_secret: str) -> str:
        """Hash API secret for storage"""
        return self.pwd_context.hash(api_secret)
    
    def verify_api_secret(self, plain_secret: str, hashed_secret: str) -> bool:
        """Verify API secret against hash"""
        return self.pwd_context.verify(plain_secret, hashed_secret)


# Global instance
admin_auth = AdminAuthHandler()


class AdminAuthUser:
    """Admin user information for dependency injection"""
    
    def __init__(self, admin_user: AdminUser, session: AdminSession = None):
        self.admin_id = admin_user.id
        self.email = admin_user.email
        self.username = admin_user.username
        self.full_name = admin_user.full_name
        self.role = admin_user.role
        self.is_superuser = admin_user.is_superuser
        self.is_active = admin_user.is_active
        self.session = session


async def get_current_admin_user(
    request: Request,
    db: Session = Depends(get_db)
) -> AdminAuthUser:
    """Dependency to get current admin user from JWT token"""
    
    # Extract token from Authorization header
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.split(" ")[1]
    
    # Verify token
    try:
        payload = admin_auth.verify_token(token, "admin_access")
        admin_id = payload.get("sub")
        if not admin_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed"
        )
    
    # Get admin user from database
    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin user not found or inactive"
        )
    
    # Get current session
    session = db.query(AdminSession).filter(
        AdminSession.admin_user_id == admin_id,
        AdminSession.session_token == token,
        AdminSession.is_active == True
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    # Update last activity
    session.last_activity = datetime.utcnow()
    db.commit()
    
    return AdminAuthUser(admin, session)


async def require_admin_role(
    required_roles: list[AdminRole],
    current_admin: AdminAuthUser = Depends(get_current_admin_user)
) -> AdminAuthUser:
    """Dependency to require specific admin role"""
    if current_admin.role not in required_roles and not current_admin.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of these roles: {[role.value for role in required_roles]}"
        )
    return current_admin


# Convenience dependencies for different role levels
async def require_super_admin(
    current_admin: AdminAuthUser = Depends(get_current_admin_user)
) -> AdminAuthUser:
    """Require super admin access"""
    if not current_admin.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_admin


async def require_admin_or_higher(
    current_admin: AdminAuthUser = Depends(get_current_admin_user)
) -> AdminAuthUser:
    """Require admin or super admin access"""
    allowed_roles = [AdminRole.ADMIN, AdminRole.SUPER_ADMIN]
    return await require_admin_role(allowed_roles, current_admin)


async def require_moderator_or_higher(
    current_admin: AdminAuthUser = Depends(get_current_admin_user)
) -> AdminAuthUser:
    """Require moderator, admin, or super admin access"""
    allowed_roles = [AdminRole.MODERATOR, AdminRole.ADMIN, AdminRole.SUPER_ADMIN]
    return await require_admin_role(allowed_roles, current_admin)