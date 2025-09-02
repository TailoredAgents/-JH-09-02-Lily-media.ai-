"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from backend.db.database import get_db
from backend.db.models import User, UserSetting, RefreshTokenBlacklist
from backend.db.admin_models import RegistrationKey
from backend.auth.dependencies import get_current_user, get_current_active_user, AuthUser
from backend.auth.jwt_handler import jwt_handler
from backend.auth.two_factor import two_factor_service
from backend.core.feature_flags import ff

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Pydantic models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None
    backup_code: Optional[str] = None
    
    @validator('totp_code')
    def validate_totp_code(cls, v):
        if v is not None and (len(v) != 6 or not v.isdigit()):
            raise ValueError('TOTP code must be 6 digits')
        return v
    
    @validator('backup_code')
    def validate_backup_code(cls, v):
        from backend.auth.validators import normalize_and_validate_backup_code
        return normalize_and_validate_backup_code(v)

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str = ""
    registration_key: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    username: str


class TwoFactorChallengeResponse(BaseModel):
    requires_2fa: bool = True
    message: str = "Two-factor authentication code required"
    backup_code_available: bool = True

class UserProfile(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    is_active: bool
    tier: str
    created_at: str

@router.post("/register", response_model=TokenResponse)
async def register_user(request: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    """Register new user with local authentication - requires admin-generated registration key"""
    
    # Validate registration key first
    registration_key = db.query(RegistrationKey).filter(
        RegistrationKey.key == request.registration_key
    ).first()
    
    if not registration_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid registration key"
        )
    
    if not registration_key.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration key is expired or has been used up"
        )
    
    if not registration_key.can_register_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration key is not valid for this email domain"
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == request.email) | (User.username == request.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    # Create new user
    hashed_password = jwt_handler.hash_password(request.password)
    
    new_user = User(
        email=request.email,
        username=request.username,
        full_name=request.full_name or request.username,
        hashed_password=hashed_password,
        is_active=True,
        tier="base",
        auth_provider="local",
        registration_key_id=registration_key.id
    )
    
    # Increment registration key usage
    registration_key.current_uses += 1
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create default user settings
    user_settings = UserSetting(
        user_id=new_user.id,
        brand_name=request.full_name or request.username,
        brand_voice="professional",
        content_frequency=3,
        preferred_platforms=["twitter", "instagram"],
        posting_times={"twitter": "09:00", "instagram": "10:00"},
        creativity_level=0.7,
        enable_images=True,
        enable_repurposing=True
    )
    
    db.add(user_settings)
    db.commit()
    
    # Create personal organization for multi-tenancy
    try:
        from backend.middleware.tenant_isolation import create_personal_organization
        create_personal_organization(new_user, db)
    except Exception as e:
        # Log error but don't fail registration if org creation fails
        print(f"Warning: Failed to create personal organization for user {new_user.id}: {e}")
    
    # Create access and refresh tokens
    tokens = jwt_handler.create_user_tokens(
        user_id=str(new_user.id),
        email=new_user.email,
        username=new_user.username
    )
    
    # Set refresh token as HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,  # Use HTTPS in production
        samesite="none",  # Allow cross-origin cookie sending
        max_age=jwt_handler.refresh_token_expire_seconds
    )
    
    return TokenResponse(
        access_token=tokens["access_token"],
        user_id=str(new_user.id),
        email=new_user.email,
        username=new_user.username
    )

@router.post("/login")
async def login_user(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login user with local authentication and 2FA support"""
    
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Verify password for local auth users
    if user.auth_provider == "local" and user.hashed_password:
        if not jwt_handler.verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
    elif user.auth_provider == "local" and not user.hashed_password:
        # User exists but has no password (legacy user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please reset your password"
        )
    
    # Check if 2FA is required
    if user.two_factor_enabled:
        # If no 2FA code provided, challenge for it
        if not request.totp_code and not request.backup_code:
            return TwoFactorChallengeResponse(
                backup_code_available=bool(user.two_factor_backup_codes)
            )
        
        # Verify 2FA code
        verification_valid = False
        used_backup_code = None
        
        # Try TOTP code first
        if request.totp_code and user.two_factor_secret:
            try:
                secret = two_factor_service.decrypt_secret(user.two_factor_secret)
                verification_valid = two_factor_service.verify_token(secret, request.totp_code)
            except Exception:
                pass
        
        # Try backup code if TOTP failed
        if not verification_valid and request.backup_code and user.two_factor_backup_codes:
            is_valid, code_hash = two_factor_service.verify_backup_code(
                request.backup_code, user.two_factor_backup_codes
            )
            if is_valid:
                verification_valid = True
                used_backup_code = code_hash
        
        if not verification_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid two-factor authentication code"
            )
        
        # Remove used backup code
        if used_backup_code:
            user.two_factor_backup_codes = [
                code for code in user.two_factor_backup_codes 
                if code != used_backup_code
            ]
            db.commit()
    
    # Create access and refresh tokens
    tokens = jwt_handler.create_user_tokens(
        user_id=str(user.id),
        email=user.email,
        username=user.username
    )
    
    # Set refresh token as HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,  # Use HTTPS in production
        samesite="none",  # Allow cross-origin cookie sending
        max_age=jwt_handler.refresh_token_expire_seconds
    )
    
    return TokenResponse(
        access_token=tokens["access_token"],
        user_id=str(user.id),
        email=user.email,
        username=user.username
    )

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user profile"""
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name or "",
        is_active=current_user.is_active,
        tier=current_user.tier,
        created_at=current_user.created_at.isoformat() if current_user.created_at else ""
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response, 
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token from cookie"""
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    try:
        # Verify refresh token
        payload = jwt_handler.verify_token(refresh_token)
        
        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Check if token is blacklisted
        jti = payload.get("jti")
        if jti:
            blacklisted = db.query(RefreshTokenBlacklist).filter(
                RefreshTokenBlacklist.token_jti == jti
            ).first()
            if blacklisted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        username = payload.get("username")
        
        if not all([user_id, email, username]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Validate user still exists and is active
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            # User no longer exists or has been deactivated
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is no longer valid"
            )
        
        # Update user data in case it changed (email verification, etc.)
        current_user_data = {
            "user_id": str(user.id),
            "email": user.email,
            "username": user.username,
            "email_verified": user.email_verified,
            "tier": user.tier,
            "is_superuser": user.is_superuser
        }
        
        # Create new tokens with current user data
        new_tokens = jwt_handler.create_user_tokens(
            str(user.id), 
            user.email, 
            user.username
        )
        
        # Blacklist old refresh token
        if jti:
            old_token_blacklist = RefreshTokenBlacklist(
                token_jti=jti,
                user_id=int(user_id),
                expires_at=datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
            )
            db.add(old_token_blacklist)
            db.commit()
        
        # Set new refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=new_tokens["refresh_token"],
            httponly=True,
            secure=True,
            samesite="none",  # Allow cross-origin cookie sending
            max_age=jwt_handler.refresh_token_expire_seconds
        )
        
        return TokenResponse(
            access_token=new_tokens["access_token"],
            user_id=str(user.id),
            email=user.email,
            username=user.username,
            email_verified=user.email_verified,
            tier=user.tier,
            is_superuser=user.is_superuser
        )
        
    except HTTPException:
        # Clear invalid refresh token cookie on any authentication error
        response.delete_cookie(
            key="refresh_token",
            secure=True,
            samesite="none",
            httponly=True
        )
        raise
    except Exception as e:
        # Clear invalid refresh token cookie on any error
        response.delete_cookie(
            key="refresh_token",
            secure=True,
            samesite="none",
            httponly=True
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.post("/logout")
async def logout_user(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Logout user and blacklist refresh token"""
    
    # Clear refresh token cookie with proper attributes
    response.delete_cookie(
        key="refresh_token",
        secure=True,
        samesite="none",  # Match the cookie attributes used when setting
        httponly=True
    )
    
    # Blacklist refresh token if present
    if refresh_token:
        try:
            payload = jwt_handler.verify_token(refresh_token)
            jti = payload.get("jti")
            user_id = payload.get("sub")
            
            if jti and user_id:
                # Check if already blacklisted to avoid duplicates
                existing_blacklist = db.query(RefreshTokenBlacklist).filter(
                    RefreshTokenBlacklist.token_jti == jti
                ).first()
                
                if not existing_blacklist:
                    blacklist_entry = RefreshTokenBlacklist(
                        token_jti=jti,
                        user_id=int(user_id),
                        expires_at=datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
                    )
                    db.add(blacklist_entry)
                    db.commit()
                    logger.info(f"Refresh token blacklisted for user {user_id}")
                else:
                    logger.debug(f"Token already blacklisted for user {user_id}")
                    
        except Exception as e:
            # Token already invalid, just clear cookie
            logger.debug(f"Could not blacklist invalid token during logout: {e}")
            pass
    
    return {"message": "Successfully logged out"}

@router.get("/verify")
async def verify_token(current_user: AuthUser = Depends(get_current_user)):
    """Verify if current token is valid"""
    return {
        "valid": True,
        "user_id": current_user.user_id,
        "email": current_user.email,
        "username": current_user.username,
        "auth_method": "local"
    }