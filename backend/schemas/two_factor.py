"""
Pydantic schemas for Two-Factor Authentication
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional


class Enable2FARequest(BaseModel):
    """Request to enable 2FA - requires current password verification"""
    password: str = Field(..., min_length=1, description="Current account password")


class Setup2FAResponse(BaseModel):
    """Response for 2FA setup initiation"""
    qr_code: str = Field(..., description="QR code data URL for authenticator app")
    manual_entry_key: str = Field(..., description="Manual entry key for authenticator app")
    backup_codes: List[str] = Field(..., description="Backup recovery codes")
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                "manual_entry_key": "JBSWY3DPEHPK3PXP",
                "backup_codes": ["A1B2-C3D4", "E5F6-G7H8", "I9J0-K1L2"]
            }
    })


class Verify2FASetupRequest(BaseModel):
    """Request to verify and activate 2FA"""
    token: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code from authenticator app")
    
    @field_validator('token')
    @classmethod
    def validate_token(cls, v):
        if not v.isdigit():
            raise ValueError('Token must be 6 digits')
        return v


class Disable2FARequest(BaseModel):
    """Request to disable 2FA"""
    password: str = Field(..., min_length=1, description="Current account password")
    verification_code: str = Field(..., description="TOTP code or backup code")


class Login2FARequest(BaseModel):
    """Enhanced login request with 2FA support"""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6, description="6-digit TOTP code")
    backup_code: Optional[str] = Field(None, description="Backup recovery code")
    
    @field_validator('totp_code')
    @classmethod
    def validate_totp_code(cls, v):
        if v is not None and not v.isdigit():
            raise ValueError('TOTP code must be 6 digits')
        return v
    
    @field_validator('backup_code')
    @classmethod
    def validate_backup_code(cls, v):
        from backend.auth.validators import normalize_and_validate_backup_code
        return normalize_and_validate_backup_code(v)


class TwoFactorStatusResponse(BaseModel):
    """Response showing 2FA status"""
    enabled: bool = Field(..., description="Whether 2FA is enabled")
    backup_codes_remaining: Optional[int] = Field(None, description="Number of unused backup codes")
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "enabled": True,
                "backup_codes_remaining": 8
            }
    })


class RegenerateBackupCodesRequest(BaseModel):
    """Request to regenerate backup codes"""
    password: str = Field(..., min_length=1, description="Current account password")
    totp_code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")
    
    @field_validator('totp_code')
    @classmethod
    def validate_token(cls, v):
        if not v.isdigit():
            raise ValueError('TOTP code must be 6 digits')
        return v


class RegenerateBackupCodesResponse(BaseModel):
    """Response with new backup codes"""
    backup_codes: List[str] = Field(..., description="New backup recovery codes")
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "backup_codes": ["A1B2-C3D4", "E5F6-G7H8", "I9J0-K1L2"]
            }
    })