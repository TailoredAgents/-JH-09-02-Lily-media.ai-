"""
Admin API endpoints for user management, system administration, and analytics
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc, and_, or_
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
import secrets
from enum import Enum

from backend.db.database import get_db
from backend.db.models import User, UserSetting, ContentItem, ContentLog
from backend.db.admin_models import (
    AdminUser, AdminSession, AdminRole, AdminAuditLog, 
    UserManagement, SystemSettings, ApiKeyRevocation, RegistrationKey
)
from backend.auth.admin_auth import (
    admin_auth, AdminAuthUser, get_current_admin_user,
    require_super_admin, require_admin_or_higher, require_moderator_or_higher
)
from backend.middleware.feature_flag_enforcement import require_flag

router = APIRouter(prefix="/api/admin", tags=["admin"])


# Pydantic Models for Admin API
class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class AdminLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    admin_user: Dict[str, Any]


class CreateAdminUserRequest(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    password: str
    role: AdminRole = AdminRole.ADMIN
    is_superuser: bool = False


class UpdateAdminUserRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[AdminRole] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserManagementRequest(BaseModel):
    monthly_request_limit: Optional[int] = None
    daily_request_limit: Optional[int] = None
    is_suspended: Optional[bool] = None
    suspension_reason: Optional[str] = None
    is_verified: Optional[bool] = None
    verification_notes: Optional[str] = None
    subscription_tier: Optional[str] = None


class SystemSettingRequest(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None
    setting_type: str = "string"
    is_public: bool = False
    is_readonly: bool = False


class AdminDashboardStats(BaseModel):
    total_users: int
    active_users_today: int
    new_users_this_week: int
    total_content_items: int
    content_created_today: int
    total_api_requests: int
    failed_logins_today: int
    suspended_users: int


# Authentication Endpoints
@router.post("/auth/login", response_model=AdminLoginResponse)
async def admin_login(
    request: AdminLoginRequest,
    req: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(require_flag("ADMIN_ACCESS"))
):
    """Admin login with enhanced security"""
    
    admin_user, tokens = await admin_auth.authenticate_admin(
        request.email,
        request.password, 
        request.totp_code,
        req,
        db
    )
    
    # Set secure HTTP-only cookie for refresh token
    response.set_cookie(
        key="admin_refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="none",  # Allow cross-origin cookie sending
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    return AdminLoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=tokens["expires_in"],
        admin_user={
            "id": admin_user.id,
            "email": admin_user.email,
            "username": admin_user.username,
            "full_name": admin_user.full_name,
            "role": admin_user.role.value,
            "is_superuser": admin_user.is_superuser
        }
    )


@router.post("/auth/logout")
async def admin_logout(
    request: Request,
    response: Response,
    current_admin: AdminAuthUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Admin logout"""
    
    # Get token from header
    authorization = request.headers.get("Authorization", "")
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else ""
    
    await admin_auth.logout_admin(current_admin.admin_id, token, request, db)
    
    # Clear refresh token cookie
    response.delete_cookie(key="admin_refresh_token")
    
    return {"message": "Successfully logged out"}


@router.get("/auth/me")
async def get_admin_profile(
    current_admin: AdminAuthUser = Depends(get_current_admin_user)
):
    """Get current admin user profile"""
    return {
        "id": current_admin.admin_id,
        "email": current_admin.email,
        "username": current_admin.username,
        "full_name": current_admin.full_name,
        "role": current_admin.role.value,
        "is_superuser": current_admin.is_superuser,
        "is_active": current_admin.is_active,
        "session_info": {
            "ip_address": current_admin.session.ip_address if current_admin.session else None,
            "last_activity": current_admin.session.last_activity if current_admin.session else None
        }
    }


# Dashboard and Analytics
@router.get("/dashboard", response_model=AdminDashboardStats)
async def get_admin_dashboard(
    current_admin: AdminAuthUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get admin dashboard statistics"""
    
    today = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # Get statistics
    total_users = db.query(func.count(User.id)).scalar()
    
    active_users_today = db.query(func.count(User.id)).filter(
        func.date(User.last_login) == today
    ).scalar() if hasattr(User, 'last_login') else 0
    
    new_users_this_week = db.query(func.count(User.id)).filter(
        User.created_at >= week_ago
    ).scalar()
    
    total_content_items = db.query(func.count(ContentItem.id)).scalar()
    
    content_created_today = db.query(func.count(ContentItem.id)).filter(
        func.date(ContentItem.created_at) == today
    ).scalar()
    
    # API requests (if you have an API usage tracking table)
    total_api_requests = db.query(func.sum(UserManagement.monthly_requests_used)).scalar() or 0
    
    # Failed logins today
    failed_logins_today = db.query(func.count(AdminAuditLog.id)).filter(
        and_(
            AdminAuditLog.action == "FAILED_LOGIN",
            func.date(AdminAuditLog.created_at) == today
        )
    ).scalar()
    
    # Suspended users
    suspended_users = db.query(func.count(UserManagement.id)).filter(
        UserManagement.is_suspended == True
    ).scalar()
    
    return AdminDashboardStats(
        total_users=total_users,
        active_users_today=active_users_today,
        new_users_this_week=new_users_this_week,
        total_content_items=total_content_items,
        content_created_today=content_created_today,
        total_api_requests=total_api_requests,
        failed_logins_today=failed_logins_today,
        suspended_users=suspended_users
    )


# User Management Endpoints
@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_suspended: Optional[bool] = None,
    current_admin: AdminAuthUser = Depends(require_moderator_or_higher),
    db: Session = Depends(get_db)
):
    """List all users with filtering and pagination"""
    
    # Build query
    query = db.query(User).options(joinedload(User.management_info))
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if is_suspended is not None:
        query = query.join(UserManagement, User.id == UserManagement.user_id, isouter=True)
        query = query.filter(UserManagement.is_suspended == is_suspended)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    users = query.offset(offset).limit(limit).all()
    
    # Format response
    user_list = []
    for user in users:
        user_data = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "tier": user.tier,
            "created_at": user.created_at,
            "management_info": None
        }
        
        if user.management_info:
            mgmt = user.management_info
            user_data["management_info"] = {
                "api_key": mgmt.api_key[:8] + "..." if mgmt.api_key else None,
                "monthly_request_limit": mgmt.monthly_request_limit,
                "monthly_requests_used": mgmt.monthly_requests_used,
                "is_suspended": mgmt.is_suspended,
                "suspension_reason": mgmt.suspension_reason,
                "is_verified": mgmt.is_verified,
                "subscription_tier": mgmt.subscription_tier
            }
        
        user_list.append(user_data)
    
    return {
        "users": user_list,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: int,
    current_admin: AdminAuthUser = Depends(require_moderator_or_higher),
    db: Session = Depends(get_db)
):
    """Get detailed user information"""
    
    user = db.query(User).options(joinedload(User.management_info)).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's content statistics
    content_stats = db.query(
        func.count(ContentItem.id).label("total_content"),
        func.count(ContentItem.id).filter(ContentItem.status == "published").label("published_content"),
        func.count(ContentItem.id).filter(ContentItem.status == "draft").label("draft_content")
    ).filter(ContentItem.user_id == user_id).first()
    
    # Get recent activity (last 10 content items)
    recent_content = db.query(ContentItem).filter(ContentItem.user_id == user_id).order_by(
        desc(ContentItem.created_at)
    ).limit(10).all()
    
    user_data = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "tier": user.tier,
        "auth_provider": user.auth_provider,
        "created_at": user.created_at,
        "content_stats": {
            "total_content": content_stats.total_content if content_stats else 0,
            "published_content": content_stats.published_content if content_stats else 0,
            "draft_content": content_stats.draft_content if content_stats else 0
        },
        "recent_content": [
            {
                "id": item.id,
                "title": item.title,
                "platform": item.platform,
                "status": item.status,
                "created_at": item.created_at
            } for item in recent_content
        ],
        "management_info": None
    }
    
    if user.management_info:
        mgmt = user.management_info
        user_data["management_info"] = {
            "api_key": mgmt.api_key,
            "api_key_created_at": mgmt.api_key_created_at,
            "api_key_last_used": mgmt.api_key_last_used,
            "api_key_usage_count": mgmt.api_key_usage_count,
            "monthly_request_limit": mgmt.monthly_request_limit,
            "monthly_requests_used": mgmt.monthly_requests_used,
            "daily_request_limit": mgmt.daily_request_limit,
            "daily_requests_used": mgmt.daily_requests_used,
            "is_suspended": mgmt.is_suspended,
            "suspension_reason": mgmt.suspension_reason,
            "suspended_at": mgmt.suspended_at,
            "suspension_expires": mgmt.suspension_expires,
            "is_verified": mgmt.is_verified,
            "verification_notes": mgmt.verification_notes,
            "verified_at": mgmt.verified_at,
            "subscription_tier": mgmt.subscription_tier,
            "subscription_expires": mgmt.subscription_expires,
            "created_at": mgmt.created_at,
            "updated_at": mgmt.updated_at
        }
    
    return user_data


@router.put("/users/{user_id}/management")
async def update_user_management(
    user_id: int,
    update_data: UserManagementRequest,
    request: Request,
    current_admin: AdminAuthUser = Depends(require_admin_or_higher),
    db: Session = Depends(get_db)
):
    """Update user management settings"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get or create management record
    mgmt = db.query(UserManagement).filter(UserManagement.user_id == user_id).first()
    if not mgmt:
        mgmt = UserManagement(
            user_id=user_id,
            managed_by_id=current_admin.admin_id
        )
        db.add(mgmt)
    
    # Store old values for audit
    old_values = {
        "monthly_request_limit": mgmt.monthly_request_limit,
        "daily_request_limit": mgmt.daily_request_limit,
        "is_suspended": mgmt.is_suspended,
        "suspension_reason": mgmt.suspension_reason,
        "is_verified": mgmt.is_verified,
        "verification_notes": mgmt.verification_notes,
        "subscription_tier": mgmt.subscription_tier
    }
    
    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(mgmt, field, value)
    
    # Handle suspension
    if update_data.is_suspended is not None:
        if update_data.is_suspended:
            mgmt.suspended_at = datetime.utcnow()
            # Default 30-day suspension if not specified
            if not mgmt.suspension_expires:
                mgmt.suspension_expires = datetime.utcnow() + timedelta(days=30)
        else:
            mgmt.suspended_at = None
            mgmt.suspension_expires = None
            mgmt.suspension_reason = None
    
    # Handle verification
    if update_data.is_verified is not None and update_data.is_verified:
        mgmt.verified_at = datetime.utcnow()
    
    mgmt.updated_at = datetime.utcnow()
    mgmt.managed_by_id = current_admin.admin_id
    
    db.commit()
    
    # Log the change
    await admin_auth._log_audit_event(
        current_admin.admin_id,
        "UPDATE_USER_MANAGEMENT",
        "user_management",
        str(user_id),
        {
            "old_values": old_values,
            "new_values": update_dict,
            "user_email": user.email
        },
        request,
        db
    )
    
    return {"message": "User management settings updated successfully"}


# API Key Management
@router.post("/users/{user_id}/api-key")
async def generate_user_api_key(
    user_id: int,
    request: Request,
    current_admin: AdminAuthUser = Depends(require_admin_or_higher),
    db: Session = Depends(get_db)
):
    """Generate new API key for user"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate API key and secret
    api_key, api_secret = admin_auth.generate_api_key()
    hashed_secret = admin_auth.hash_api_secret(api_secret)
    
    # Get or create management record
    mgmt = db.query(UserManagement).filter(UserManagement.user_id == user_id).first()
    if not mgmt:
        mgmt = UserManagement(
            user_id=user_id,
            managed_by_id=current_admin.admin_id
        )
        db.add(mgmt)
    
    # Revoke old API key if exists
    if mgmt.api_key:
        revocation = ApiKeyRevocation(
            api_key=mgmt.api_key,
            user_id=user_id,
            revoked_by=current_admin.admin_id,
            reason="Replaced with new key"
        )
        db.add(revocation)
    
    # Update with new API key
    mgmt.api_key = api_key
    mgmt.api_secret = hashed_secret
    mgmt.api_key_created_at = datetime.utcnow()
    mgmt.api_key_usage_count = 0
    mgmt.api_key_last_used = None
    
    db.commit()
    
    # Log the action
    await admin_auth._log_audit_event(
        current_admin.admin_id,
        "GENERATE_API_KEY",
        "user_api_key",
        str(user_id),
        {
            "user_email": user.email,
            "api_key": api_key[:8] + "..."
        },
        request,
        db
    )
    
    return {
        "message": "API key generated successfully",
        "api_key": api_key,
        "api_secret": api_secret,  # Only shown once
        "created_at": mgmt.api_key_created_at
    }


@router.delete("/users/{user_id}/api-key")
async def revoke_user_api_key(
    user_id: int,
    request: Request,
    reason: str = "Admin revocation",
    current_admin: AdminAuthUser = Depends(require_admin_or_higher),
    db: Session = Depends(get_db)
):
    """Revoke user's API key"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    mgmt = db.query(UserManagement).filter(UserManagement.user_id == user_id).first()
    if not mgmt or not mgmt.api_key:
        raise HTTPException(status_code=404, detail="No API key found for user")
    
    # Create revocation record
    revocation = ApiKeyRevocation(
        api_key=mgmt.api_key,
        user_id=user_id,
        revoked_by=current_admin.admin_id,
        reason=reason
    )
    db.add(revocation)
    
    # Clear API key from management record
    old_api_key = mgmt.api_key
    mgmt.api_key = None
    mgmt.api_secret = None
    
    db.commit()
    
    # Log the action
    await admin_auth._log_audit_event(
        current_admin.admin_id,
        "REVOKE_API_KEY",
        "user_api_key",
        str(user_id),
        {
            "user_email": user.email,
            "revoked_api_key": old_api_key[:8] + "...",
            "reason": reason
        },
        request,
        db
    )
    
    return {"message": "API key revoked successfully"}


# Admin User Management (Super Admin Only)
@router.post("/admin-users")
async def create_admin_user(
    admin_data: CreateAdminUserRequest,
    request: Request,
    current_admin: AdminAuthUser = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Create new admin user (Super Admin only)"""
    
    # Check if admin with email or username already exists
    existing = db.query(AdminUser).filter(
        or_(
            AdminUser.email == admin_data.email,
            AdminUser.username == admin_data.username
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="Admin user with this email or username already exists"
        )
    
    # Create new admin user
    hashed_password = admin_auth.hash_password(admin_data.password)
    
    new_admin = AdminUser(
        email=admin_data.email,
        username=admin_data.username,
        full_name=admin_data.full_name,
        hashed_password=hashed_password,
        role=admin_data.role,
        is_superuser=admin_data.is_superuser,
        created_by=current_admin.admin_id
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    # Log the action
    await admin_auth._log_audit_event(
        current_admin.admin_id,
        "CREATE_ADMIN_USER",
        "admin_user",
        new_admin.id,
        {
            "email": admin_data.email,
            "username": admin_data.username,
            "role": admin_data.role.value,
            "is_superuser": admin_data.is_superuser
        },
        request,
        db
    )
    
    return {
        "message": "Admin user created successfully",
        "admin_user": {
            "id": new_admin.id,
            "email": new_admin.email,
            "username": new_admin.username,
            "role": new_admin.role.value,
            "is_superuser": new_admin.is_superuser,
            "created_at": new_admin.created_at
        }
    }


@router.get("/admin-users")
async def list_admin_users(
    current_admin: AdminAuthUser = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """List all admin users (Super Admin only)"""
    
    admin_users = db.query(AdminUser).order_by(AdminUser.created_at.desc()).all()
    
    return {
        "admin_users": [
            {
                "id": admin.id,
                "email": admin.email,
                "username": admin.username,
                "full_name": admin.full_name,
                "role": admin.role.value,
                "is_superuser": admin.is_superuser,
                "is_active": admin.is_active,
                "last_login": admin.last_login,
                "created_at": admin.created_at
            } for admin in admin_users
        ]
    }


# System Settings Management
@router.get("/settings")
async def get_system_settings(
    current_admin: AdminAuthUser = Depends(require_moderator_or_higher),
    db: Session = Depends(get_db)
):
    """Get system settings"""
    
    settings = db.query(SystemSettings).order_by(SystemSettings.key).all()
    
    return {
        "settings": [
            {
                "id": setting.id,
                "key": setting.key,
                "value": setting.value,
                "description": setting.description,
                "setting_type": setting.setting_type,
                "is_public": setting.is_public,
                "is_readonly": setting.is_readonly,
                "updated_at": setting.updated_at
            } for setting in settings
        ]
    }


@router.put("/settings/{setting_key}")
async def update_system_setting(
    setting_key: str,
    setting_data: SystemSettingRequest,
    request: Request,
    current_admin: AdminAuthUser = Depends(require_admin_or_higher),
    db: Session = Depends(get_db)
):
    """Update system setting"""
    
    setting = db.query(SystemSettings).filter(SystemSettings.key == setting_key).first()
    
    # Check if setting exists and permissions
    if setting and setting.is_readonly and not current_admin.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Only super admins can modify read-only settings"
        )
    
    old_value = setting.value if setting else None
    
    if not setting:
        # Create new setting
        setting = SystemSettings(
            key=setting_key,
            value=setting_data.value,
            description=setting_data.description,
            setting_type=setting_data.setting_type,
            is_public=setting_data.is_public,
            is_readonly=setting_data.is_readonly,
            created_by=current_admin.admin_id,
            updated_by=current_admin.admin_id
        )
        db.add(setting)
    else:
        # Update existing setting
        setting.value = setting_data.value
        if setting_data.description is not None:
            setting.description = setting_data.description
        setting.updated_by = current_admin.admin_id
        setting.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Log the action
    await admin_auth._log_audit_event(
        current_admin.admin_id,
        "UPDATE_SYSTEM_SETTING",
        "system_setting",
        setting_key,
        {
            "old_value": old_value,
            "new_value": setting_data.value,
            "setting_type": setting_data.setting_type
        },
        request,
        db
    )
    
    return {"message": "System setting updated successfully"}


# Audit Log Endpoints
@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    admin_user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_admin: AdminAuthUser = Depends(require_admin_or_higher),
    db: Session = Depends(get_db)
):
    """Get audit logs with filtering"""
    
    query = db.query(AdminAuditLog).options(joinedload(AdminAuditLog.admin_user))
    
    # Apply filters
    if action:
        query = query.filter(AdminAuditLog.action == action)
    
    if admin_user_id:
        query = query.filter(AdminAuditLog.admin_user_id == admin_user_id)
    
    if start_date:
        query = query.filter(AdminAuditLog.created_at >= start_date)
    
    if end_date:
        query = query.filter(AdminAuditLog.created_at <= end_date)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    offset = (page - 1) * limit
    logs = query.order_by(desc(AdminAuditLog.created_at)).offset(offset).limit(limit).all()
    
    return {
        "logs": [
            {
                "id": log.id,
                "admin_user_id": log.admin_user_id,
                "admin_user_email": log.admin_user.email if log.admin_user else "system",
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "success": log.success,
                "error_message": log.error_message,
                "ip_address": log.ip_address,
                "created_at": log.created_at
            } for log in logs
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


# Registration Key Management Endpoints

class CreateRegistrationKeyRequest(BaseModel):
    description: Optional[str] = None
    max_uses: int = 1
    email_domain_restriction: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True

class RegistrationKeyResponse(BaseModel):
    id: str
    key: str
    description: Optional[str]
    max_uses: int
    current_uses: int
    is_active: bool
    email_domain_restriction: Optional[str]
    expires_at: Optional[datetime]
    created_at: datetime
    created_by_admin: str
    users_registered: int

@router.post("/registration-keys", response_model=Dict[str, Any])
async def create_registration_key(
    request: CreateRegistrationKeyRequest,
    current_admin: AdminAuthUser = Depends(require_admin_or_higher),
    db: Session = Depends(get_db)
):
    """Create a new registration key for user registration"""
    
    # Generate secure registration key
    registration_key = secrets.token_urlsafe(32)
    
    new_key = RegistrationKey(
        key=registration_key,
        description=request.description,
        max_uses=request.max_uses,
        email_domain_restriction=request.email_domain_restriction,
        expires_at=request.expires_at,
        is_active=request.is_active,
        created_by=current_admin.admin_id
    )
    
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    
    # Log the action
    await admin_auth._log_audit_event(
        current_admin.admin_id,
        "CREATE_REGISTRATION_KEY",
        "registration_key",
        new_key.id,
        {
            "description": request.description,
            "max_uses": request.max_uses,
            "email_domain_restriction": request.email_domain_restriction,
            "expires_at": str(request.expires_at) if request.expires_at else None
        },
        db_session=db
    )
    
    return {
        "message": "Registration key created successfully",
        "registration_key": {
            "id": new_key.id,
            "key": registration_key,
            "description": new_key.description,
            "max_uses": new_key.max_uses,
            "current_uses": new_key.current_uses,
            "is_active": new_key.is_active,
            "email_domain_restriction": new_key.email_domain_restriction,
            "expires_at": new_key.expires_at,
            "created_at": new_key.created_at
        }
    }

@router.get("/registration-keys", response_model=Dict[str, Any])
async def get_registration_keys(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(False),
    current_admin: AdminAuthUser = Depends(require_admin_or_higher),
    db: Session = Depends(get_db)
):
    """Get list of registration keys with pagination"""
    
    query = db.query(RegistrationKey).options(joinedload(RegistrationKey.created_by_admin))
    
    if active_only:
        query = query.filter(RegistrationKey.is_active == True)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    keys = query.order_by(desc(RegistrationKey.created_at)).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "registration_keys": [
            {
                "id": key.id,
                "key": key.key,
                "description": key.description,
                "max_uses": key.max_uses,
                "current_uses": key.current_uses,
                "is_active": key.is_active,
                "email_domain_restriction": key.email_domain_restriction,
                "expires_at": key.expires_at,
                "created_at": key.created_at,
                "created_by_admin": key.created_by_admin.email if key.created_by_admin else "system",
                "users_registered": len(key.users_registered),
                "is_expired": key.expires_at and datetime.utcnow() > key.expires_at,
                "is_used_up": key.max_uses is not None and key.current_uses >= key.max_uses
            } for key in keys
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }

@router.put("/registration-keys/{key_id}/deactivate")
async def deactivate_registration_key(
    key_id: str,
    current_admin: AdminAuthUser = Depends(require_admin_or_higher),
    db: Session = Depends(get_db)
):
    """Deactivate a registration key"""
    
    registration_key = db.query(RegistrationKey).filter(RegistrationKey.id == key_id).first()
    if not registration_key:
        raise HTTPException(status_code=404, detail="Registration key not found")
    
    registration_key.is_active = False
    registration_key.updated_at = datetime.utcnow()
    db.commit()
    
    # Log the action
    await admin_auth._log_audit_event(
        current_admin.admin_id,
        "DEACTIVATE_REGISTRATION_KEY",
        "registration_key",
        key_id,
        {"reason": "Admin deactivation"},
        db_session=db
    )
    
    return {"message": "Registration key deactivated successfully"}

@router.delete("/registration-keys/{key_id}")
async def delete_registration_key(
    key_id: str,
    current_admin: AdminAuthUser = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Delete a registration key (super admin only)"""
    
    registration_key = db.query(RegistrationKey).filter(RegistrationKey.id == key_id).first()
    if not registration_key:
        raise HTTPException(status_code=404, detail="Registration key not found")
    
    # Check if key has been used
    if registration_key.current_uses > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete registration key that has been used {registration_key.current_uses} times"
        )
    
    db.delete(registration_key)
    db.commit()
    
    # Log the action
    await admin_auth._log_audit_event(
        current_admin.admin_id,
        "DELETE_REGISTRATION_KEY",
        "registration_key",
        key_id,
        {"key": registration_key.key, "reason": "Super admin deletion"},
        db_session=db
    )
    
    return {"message": "Registration key deleted successfully"}

# P1-5a: Tier to Plan Migration Endpoints

@router.get("/migration/tier-to-plan/status")
async def get_tier_migration_status(
    current_admin: AdminAuthUser = Depends(require_admin_or_higher),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """P1-5a: Get tier to plan migration status"""
    try:
        from backend.utils.tier_to_plan_migration import get_migration_status_report
        
        report = get_migration_status_report(db)
        
        # Log the action
        await admin_auth._log_audit_event(
            current_admin.admin_id,
            "TIER_MIGRATION_STATUS_CHECK",
            "system",
            "tier_migration",
            {"status": report["migration_status"]},
            db_session=db
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Failed to get tier migration status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve migration status"
        )

@router.post("/migration/tier-to-plan/execute")
async def execute_tier_migration(
    current_admin: AdminAuthUser = Depends(require_super_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """P1-5a: Execute tier to plan migration (super admin only)"""
    try:
        from backend.utils.tier_to_plan_migration import run_migration_if_needed
        
        # Execute migration
        result = run_migration_if_needed(db)
        
        # Log the action
        await admin_auth._log_audit_event(
            current_admin.admin_id,
            "TIER_MIGRATION_EXECUTED",
            "system",
            "tier_migration",
            {
                "migration_run": result.get("migration_run", False),
                "stats": result.get("stats", {}),
                "verification": result.get("verification", {})
            },
            db_session=db
        )
        
        return {
            "message": "Tier migration completed successfully" if result.get("migration_run") else "No migration was needed",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Failed to execute tier migration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}"
        )