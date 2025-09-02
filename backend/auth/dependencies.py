"""
Authentication dependencies for FastAPI routes
"""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User
from backend.auth.auth0 import auth0_verifier
from backend.auth.jwt_handler import JWTHandler

# Security scheme
security = HTTPBearer()
jwt_handler = JWTHandler()

class AuthUser:
    """Authenticated user model"""
    def __init__(self, user_id: str, email: str, username: str, auth_method: str = 'auth0'):
        self.user_id = user_id
        self.email = email
        self.username = username
        self.auth_method = auth_method

async def get_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract JWT token from Authorization header"""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

async def verify_auth0_token(token: str = Depends(get_token)) -> Dict[str, Any]:
    """Verify Auth0 JWT token"""
    return auth0_verifier.verify_token(token)

async def verify_local_token(token: str = Depends(get_token)) -> Dict[str, Any]:
    """Verify locally issued JWT token"""
    return jwt_handler.verify_token(token)

async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(get_token)
) -> AuthUser:
    """Get current authenticated user (supports both Auth0 and local JWT)"""
    
    # Try local JWT first (primary authentication method)
    try:
        payload = jwt_handler.verify_token(token)
        user_id = payload.get("sub")
        email = payload.get("email")
        username = payload.get("username")
        
        return AuthUser(user_id=user_id, email=email, username=username, auth_method="local")
    
    except HTTPException:
        # Fallback to Auth0 for backward compatibility (if configured)
        try:
            if auth0_verifier.enabled:
                payload = auth0_verifier.verify_token(token)
                user_id = payload.get("sub")
                email = payload.get("email")
                username = payload.get("nickname") or payload.get("preferred_username") or email
                
                # Ensure user exists in local database
                await sync_auth0_user(db, user_id, email, username)
                
                return AuthUser(user_id=user_id, email=email, username=username, auth_method="auth0")
            else:
                # Auth0 not configured, skip fallback
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

async def sync_auth0_user(db: Session, auth0_id: str, email: str, username: str) -> User:
    """Sync Auth0 user with local database"""
    # Check if user exists
    user = db.query(User).filter_by(email=email).first()
    
    if not user:
        # Create new user
        user = User(
            email=email,
            username=username,
            full_name=username,
            is_active=True,
            tier="base"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user

def get_current_active_user(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Get current active user from database"""
    user = db.query(User).filter_by(email=current_user.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user

def get_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Require admin user for protected routes"""
    if current_user.tier not in ["pro", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user

# Optional authentication dependency
async def get_optional_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """Get user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        current_user = await get_current_user(db, token)
        return get_current_active_user(current_user, db)
    except HTTPException:
        return None