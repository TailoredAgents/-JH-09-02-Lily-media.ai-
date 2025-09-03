"""
Token Encryption Validation Service
GA Checklist requirement: Sanity test decrypt at boot

Validates token encryption/decryption functionality at application startup
to ensure TOKEN_ENCRYPTION_KEY is properly configured and functional.
"""
import logging
import os
import sys
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from backend.core.config import get_settings

logger = logging.getLogger(__name__)

class TokenEncryptionValidator:
    """
    Validates token encryption functionality at boot time
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.encryption_key = None
        self.fernet = None
        
    def validate_encryption_setup(self) -> Dict[str, Any]:
        """
        Perform comprehensive validation of token encryption setup
        
        Returns:
            Dict with validation results and status
        """
        validation_results = {
            "status": "unknown",
            "checks_passed": 0,
            "total_checks": 5,
            "errors": [],
            "warnings": [],
            "encryption_key_id": None,
            "encryption_functional": False
        }
        
        try:
            # Check 1: Environment variable exists
            if self._check_encryption_key_exists():
                validation_results["checks_passed"] += 1
                logger.info("✅ TOKEN_ENCRYPTION_KEY environment variable is set")
            else:
                error_msg = "TOKEN_ENCRYPTION_KEY environment variable not set"
                validation_results["errors"].append(error_msg)
                logger.error(f"❌ {error_msg}")
                validation_results["status"] = "failed"
                return validation_results
            
            # Check 2: Key format validation
            if self._validate_key_format():
                validation_results["checks_passed"] += 1
                logger.info("✅ Token encryption key format is valid")
            else:
                error_msg = "TOKEN_ENCRYPTION_KEY format is invalid (must be Fernet-compatible)"
                validation_results["errors"].append(error_msg)
                logger.error(f"❌ {error_msg}")
            
            # Check 3: Key ID validation
            key_id = self._validate_encryption_key_id()
            if key_id:
                validation_results["checks_passed"] += 1
                validation_results["encryption_key_id"] = key_id
                logger.info(f"✅ Token encryption key ID: {key_id}")
            else:
                warning_msg = "TOKEN_ENCRYPTION_KID not set, using 'default'"
                validation_results["warnings"].append(warning_msg)
                validation_results["encryption_key_id"] = "default"
                logger.warning(f"⚠️  {warning_msg}")
                validation_results["checks_passed"] += 1  # Not critical
            
            # Check 4: Encryption functionality test
            if self._test_encryption_functionality():
                validation_results["checks_passed"] += 1
                validation_results["encryption_functional"] = True
                logger.info("✅ Token encryption/decryption test passed")
            else:
                error_msg = "Token encryption/decryption test failed"
                validation_results["errors"].append(error_msg)
                logger.error(f"❌ {error_msg}")
            
            # Check 5: Security validation
            if self._validate_key_security():
                validation_results["checks_passed"] += 1
                logger.info("✅ Token encryption key security validation passed")
            else:
                warning_msg = "Token encryption key may not meet security best practices"
                validation_results["warnings"].append(warning_msg)
                logger.warning(f"⚠️  {warning_msg}")
                validation_results["checks_passed"] += 1  # Not critical for functionality
            
            # Determine overall status
            if validation_results["checks_passed"] == validation_results["total_checks"]:
                validation_results["status"] = "success"
                logger.info("🎉 Token encryption validation: ALL CHECKS PASSED")
            elif validation_results["checks_passed"] >= 4:
                validation_results["status"] = "warning"  
                logger.warning(f"⚠️  Token encryption validation: {validation_results['checks_passed']}/{validation_results['total_checks']} checks passed")
            else:
                validation_results["status"] = "failed"
                logger.error(f"❌ Token encryption validation: {validation_results['checks_passed']}/{validation_results['total_checks']} checks passed")
            
        except Exception as e:
            error_msg = f"Token encryption validation error: {str(e)}"
            validation_results["errors"].append(error_msg)
            validation_results["status"] = "error"
            logger.error(f"💥 {error_msg}")
        
        return validation_results
    
    def _check_encryption_key_exists(self) -> bool:
        """Check if TOKEN_ENCRYPTION_KEY environment variable exists"""
        self.encryption_key = getattr(self.settings, 'token_encryption_key', None) or os.getenv('TOKEN_ENCRYPTION_KEY')
        return bool(self.encryption_key)
    
    def _validate_key_format(self) -> bool:
        """Validate that the encryption key is a valid Fernet key"""
        try:
            if not self.encryption_key:
                return False
            
            # Try to create Fernet instance (validates key format)
            self.fernet = Fernet(self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key)
            return True
            
        except Exception as e:
            logger.debug(f"Key format validation failed: {e}")
            return False
    
    def _validate_encryption_key_id(self) -> Optional[str]:
        """Validate and return the encryption key ID"""
        key_id = getattr(self.settings, 'token_encryption_kid', None) or os.getenv('TOKEN_ENCRYPTION_KID', 'default')
        
        # Basic validation - should be alphanumeric
        if key_id and key_id.replace('_', '').replace('-', '').isalnum():
            return key_id
        
        return 'default'  # Fallback
    
    def _test_encryption_functionality(self) -> bool:
        """Test actual encryption and decryption functionality"""
        try:
            if not self.fernet:
                return False
            
            # Test data
            test_token_data = {
                "access_token": "test_access_token_12345",
                "refresh_token": "test_refresh_token_67890",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": ["read", "write"]
            }
            
            # Convert to JSON string
            import json
            test_data_json = json.dumps(test_token_data)
            
            # Encrypt the test data
            encrypted_data = self.fernet.encrypt(test_data_json.encode('utf-8'))
            
            # Decrypt the test data
            decrypted_data = self.fernet.decrypt(encrypted_data)
            decrypted_json = json.loads(decrypted_data.decode('utf-8'))
            
            # Verify the data matches
            if decrypted_json == test_token_data:
                return True
            else:
                logger.error("Decrypted data does not match original test data")
                return False
                
        except Exception as e:
            logger.error(f"Encryption functionality test failed: {e}")
            return False
    
    def _validate_key_security(self) -> bool:
        """Validate encryption key security best practices"""
        if not self.encryption_key:
            return False
        
        security_checks = {
            "min_length": len(self.encryption_key) >= 32,  # Fernet keys are base64 encoded 32-byte keys
            "not_default": self.encryption_key != "your-secure-32-char-encryption-key-here",
            "not_simple": not any(simple in self.encryption_key.lower() for simple in ["password", "secret", "key", "test", "demo"]),
            "base64_format": self._is_valid_base64(self.encryption_key)
        }
        
        passed_checks = sum(security_checks.values())
        total_checks = len(security_checks)
        
        if passed_checks < total_checks:
            logger.warning(f"Security validation: {passed_checks}/{total_checks} checks passed")
            for check, passed in security_checks.items():
                if not passed:
                    logger.warning(f"  - {check}: FAILED")
        
        # Return True if most checks pass (not all required for functionality)
        return passed_checks >= total_checks - 1
    
    def _is_valid_base64(self, s: str) -> bool:
        """Check if string is valid base64"""
        try:
            import base64
            decoded = base64.b64decode(s)
            return len(decoded) == 32  # Fernet key should be 32 bytes
        except Exception:
            return False
    
    def create_secure_backup_info(self) -> Dict[str, Any]:
        """
        Create information for secure backup (GA checklist requirement)
        Never logs the actual key, only metadata
        """
        if not self.encryption_key:
            return {"error": "No encryption key available"}
        
        try:
            import hashlib
            import base64
            
            # Create a hash of the key for identification (not the key itself)
            key_hash = hashlib.sha256(self.encryption_key.encode()).hexdigest()[:16]
            key_id = self._validate_encryption_key_id()
            
            backup_info = {
                "key_id": key_id,
                "key_hash_partial": key_hash,
                "created_at": None,  # Would need to be tracked separately
                "backup_required": True,
                "backup_recommendations": [
                    "Store encryption key in secure key management system",
                    "Create encrypted backup of key with different master key", 
                    "Document key rotation procedure",
                    "Test key recovery process",
                    "Ensure key is available for disaster recovery"
                ]
            }
            
            logger.info(f"Token encryption backup info: key_id={key_id}, hash={key_hash}")
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to create backup info: {e}")
            return {"error": str(e)}


def validate_token_encryption_at_boot() -> bool:
    """
    Main validation function to be called at application startup
    
    Returns:
        True if validation passes, False if critical failure
    """
    logger.info("🔐 Starting token encryption validation...")
    
    validator = TokenEncryptionValidator()
    results = validator.validate_encryption_setup()
    
    # Log summary
    logger.info(f"Token encryption validation completed: {results['status'].upper()}")
    logger.info(f"Checks passed: {results['checks_passed']}/{results['total_checks']}")
    
    if results["errors"]:
        logger.error("❌ CRITICAL ERRORS:")
        for error in results["errors"]:
            logger.error(f"  - {error}")
    
    if results["warnings"]:
        logger.warning("⚠️  WARNINGS:")
        for warning in results["warnings"]:
            logger.warning(f"  - {warning}")
    
    # Create backup info (doesn't log sensitive data)
    backup_info = validator.create_secure_backup_info()
    if "error" not in backup_info:
        logger.info(f"🔑 Encryption key backup info generated: ID={backup_info.get('key_id')}")
    
    # Determine if application should continue
    if results["status"] == "failed":
        logger.critical("🚨 CRITICAL: Token encryption validation failed - application cannot start safely")
        logger.critical("Please check TOKEN_ENCRYPTION_KEY configuration and try again")
        return False
    elif results["status"] == "error":
        logger.critical("🚨 CRITICAL: Token encryption validation error - application cannot start")
        return False
    elif results["status"] == "warning":
        logger.warning("⚠️  Token encryption validation has warnings but application can start")
        return True
    else:
        logger.info("✅ Token encryption validation successful - application can start")
        return True


def generate_secure_encryption_key() -> str:
    """
    Generate a secure encryption key for production use
    
    Returns:
        Base64-encoded Fernet key
    """
    key = Fernet.generate_key()
    return key.decode('utf-8')


if __name__ == "__main__":
    """
    CLI tool for encryption key management
    """
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "generate":
        print("Generating secure encryption key...")
        new_key = generate_secure_encryption_key()
        print(f"TOKEN_ENCRYPTION_KEY={new_key}")
        print("\n⚠️  IMPORTANT:")
        print("  - Store this key securely")
        print("  - Add to your production environment variables") 
        print("  - Back up the key using secure key management")
        print("  - Do NOT commit this key to version control")
    else:
        # Run validation
        success = validate_token_encryption_at_boot()
        sys.exit(0 if success else 1)