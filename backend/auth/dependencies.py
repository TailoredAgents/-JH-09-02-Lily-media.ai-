"""
Authentication dependencies for FastAPI routes
"""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User
# Auth0 removed - using local JWT authentication only
from backend.auth.jwt_handler import JWTHandler

# Security scheme
security = HTTPBearer()
jwt_handler = JWTHandler()

class AuthUser:
    """Authenticated user model"""
    def __init__(self, user_id: str, email: str, username: str, auth_method: str = 'local'):
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

# Auth0 verification removed - using local JWT only

async def verify_local_token(token: str = Depends(get_token)) -> Dict[str, Any]:
    """Verify locally issued JWT token"""
    return jwt_handler.verify_token(token)

async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(get_token)
) -> AuthUser:
    """Get current authenticated user using local JWT authentication"""
    
    # Verify local JWT token
    payload = jwt_handler.verify_token(token)
    user_id = payload.get("sub")
    email = payload.get("email")
    username = payload.get("username")
    
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return AuthUser(user_id=user_id, email=email, username=username, auth_method="local")

# Auth0 sync function removed - using local user management only

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
    # Use plan-based logic instead of legacy tier system
    if current_user.plan and current_user.plan.name in ["pro", "enterprise"]:
        return current_user
    elif current_user.tier in ["pro", "enterprise"]:  # Fallback for legacy users
        return current_user
    else:
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