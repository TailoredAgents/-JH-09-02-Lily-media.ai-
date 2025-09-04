"""
Two-Factor Authentication Service
"""
import pyotp
import qrcode
import io
import base64
import secrets
from typing import List, Optional, Tuple
from cryptography.fernet import Fernet
from backend.core.config import settings
import hashlib


class TwoFactorService:
    """Service for handling two-factor authentication with TOTP"""
    
    def __init__(self, app_name: str = "Lily AI Social Media"):
        self.app_name = app_name
        # Create encryption key from settings secret key
        key = hashlib.sha256(settings.SECRET_KEY.get_secret_value().encode()).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key))
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    def encrypt_secret(self, secret: str) -> str:
        """Encrypt TOTP secret for database storage"""
        return self.cipher.encrypt(secret.encode()).decode()
    
    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt TOTP secret from database"""
        return self.cipher.decrypt(encrypted_secret.encode()).decode()
    
    def generate_qr_code(self, email: str, secret: str) -> str:
        """Generate QR code data URL for TOTP setup"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name=self.app_name
        )
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        # Convert to image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 data URL
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        qr_data = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{qr_data}"
    
    def verify_token(self, secret: str, token: str, window: int = 1) -> bool:
        """
        Verify TOTP token
        
        Args:
            secret: The TOTP secret (plain text)
            token: The 6-digit token from authenticator app
            window: Time window tolerance (default 1 = ±30 seconds)
        
        Returns:
            bool: True if token is valid
        """
        if not secret or not token:
            return False
        
        # Remove any spaces or formatting from token
        token = token.replace(" ", "").replace("-", "")
        
        # Verify token length
        if len(token) != 6 or not token.isdigit():
            return False
        
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """
        Generate backup recovery codes
        
        Args:
            count: Number of backup codes to generate
        
        Returns:
            List of backup codes in format XXXX-XXXX
        """
        codes = []
        for _ in range(count):
            # Generate 8-character code and format as XXXX-XXXX
            code = secrets.token_hex(4).upper()
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
        
        return codes
    
    def hash_backup_code(self, code: str) -> str:
        """Hash backup code for secure storage"""
        return hashlib.sha256(code.encode()).hexdigest()
    
    def verify_backup_code(self, code: str, hashed_codes: List[str]) -> Tuple[bool, str]:
        """
        Verify backup code and return the hash if valid
        
        Args:
            code: The backup code to verify
            hashed_codes: List of hashed backup codes
        
        Returns:
            Tuple of (is_valid, code_hash)
        """
        if not code or not hashed_codes:
            return False, ""
        
        # Normalize the code format
        code = code.replace(" ", "").replace("-", "").upper()
        if len(code) == 8:
            code = f"{code[:4]}-{code[4:]}"
        
        code_hash = self.hash_backup_code(code)
        return code_hash in hashed_codes, code_hash
    
    def get_current_totp(self, secret: str) -> str:
        """Get current TOTP code for testing purposes"""
        totp = pyotp.TOTP(secret)
        return totp.now()


# Global service instance
two_factor_service = TwoFactorService()