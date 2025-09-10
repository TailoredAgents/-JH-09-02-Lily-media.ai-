"""
P0-2d: Secrets Management and Validation System
Prevents hard-coded secrets from being used in production environments
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class SecretType(Enum):
    """Types of secrets to validate"""
    API_KEY = "api_key"
    DATABASE_PASSWORD = "database_password"
    JWT_SECRET = "jwt_secret"
    ENCRYPTION_KEY = "encryption_key"
    WEBHOOK_SECRET = "webhook_secret"
    OAUTH_SECRET = "oauth_secret"

class SecretSeverity(Enum):
    """Severity levels for secret validation failures"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class SecretValidationResult:
    """Result of secret validation"""
    is_valid: bool
    secret_type: SecretType
    severity: SecretSeverity
    message: str
    recommendations: List[str]

class SecretsValidator:
    """
    Production-ready secrets validator to prevent hard-coded secrets
    and ensure proper secret management practices
    """
    
    def __init__(self, environment: str = "production"):
        self.environment = environment.lower()
        
        # Dangerous patterns that indicate hard-coded secrets
        self.dangerous_patterns = {
            SecretType.API_KEY: [
                r'sk-[a-zA-Z0-9]{32,}',  # OpenAI API keys
                r'xai-[a-zA-Z0-9]{32,}',  # xAI API keys
                r'pk_(test|live)_[a-zA-Z0-9]{24,}',  # Stripe public keys
                r'sk_(test|live)_[a-zA-Z0-9]{24,}',  # Stripe secret keys
                r'whsec_[a-zA-Z0-9]{32,}'  # Stripe webhook secrets
            ],
            SecretType.DATABASE_PASSWORD: [
                r'postgresql://[^:]+:[^@]{8,}@[^/]+/',  # PostgreSQL with embedded password
                r'mysql://[^:]+:[^@]{8,}@[^/]+/',  # MySQL with embedded password
                r'mongodb://[^:]+:[^@]{8,}@[^/]+/'  # MongoDB with embedded password
            ],
            SecretType.JWT_SECRET: [
                r'[a-zA-Z0-9+/]{64,}={0,2}',  # Base64-encoded secrets (64+ chars)
            ],
            SecretType.ENCRYPTION_KEY: [
                r'[a-fA-F0-9]{64,}',  # Hex-encoded keys (64+ chars)
                r'[a-zA-Z0-9]{32,}'  # Random alphanumeric keys (32+ chars)
            ]
        }
        
        # Placeholder/example patterns that should not be used in production
        self.placeholder_patterns = [
            r'placeholder',
            r'example',
            r'your-.*-here',
            r'test-.*-key',
            r'development.*only',
            r'change.*production',
            r'replace.*with',
            r'dummy',
            r'fake'
        ]
        
        # Environment-specific validation rules
        self.environment_rules = {
            "production": {
                "allow_placeholders": False,
                "require_complex_secrets": True,
                "minimum_key_length": 32
            },
            "staging": {
                "allow_placeholders": False,
                "require_complex_secrets": True,
                "minimum_key_length": 24
            },
            "development": {
                "allow_placeholders": True,
                "require_complex_secrets": False,
                "minimum_key_length": 16
            }
        }
        
        logger.info(f"Secrets validator initialized for {self.environment} environment")
    
    def validate_secret(self, key: str, value: str) -> SecretValidationResult:
        """
        Validate a single secret key-value pair
        
        Args:
            key: Environment variable name
            value: Secret value to validate
            
        Returns:
            SecretValidationResult with validation outcome
        """
        if not value:
            return SecretValidationResult(
                is_valid=False,
                secret_type=SecretType.API_KEY,
                severity=SecretSeverity.HIGH,
                message=f"Secret '{key}' is empty or not set",
                recommendations=["Set a proper value for this environment variable"]
            )
        
        # Check for placeholder/example patterns
        placeholder_issues = self._check_placeholder_patterns(key, value)
        if placeholder_issues:
            return placeholder_issues
        
        # Check for hard-coded dangerous patterns
        dangerous_issues = self._check_dangerous_patterns(key, value)
        if dangerous_issues:
            return dangerous_issues
        
        # Check environment-specific rules
        env_issues = self._check_environment_rules(key, value)
        if env_issues:
            return env_issues
        
        # Determine secret type and perform type-specific validation
        secret_type = self._determine_secret_type(key)
        type_issues = self._validate_secret_type(key, value, secret_type)
        if type_issues:
            return type_issues
        
        return SecretValidationResult(
            is_valid=True,
            secret_type=secret_type,
            severity=SecretSeverity.LOW,
            message=f"Secret '{key}' passes validation",
            recommendations=[]
        )
    
    def validate_all_secrets(self) -> Dict[str, SecretValidationResult]:
        """
        Validate all environment variables that contain secrets
        
        Returns:
            Dictionary mapping secret names to validation results
        """
        secret_keys = [
            'SECRET_KEY', 'JWT_SECRET', 'JWT_SECRET_KEY',
            'TOKEN_ENCRYPTION_KEY', 'TOKEN_ENCRYPTION_SALT',
            'OPENAI_API_KEY', 'XAI_API_KEY', 'ANTHROPIC_API_KEY',
            'DATABASE_URL', 'REDIS_URL',
            'STRIPE_SECRET_KEY', 'STRIPE_PUBLISHABLE_KEY', 'STRIPE_WEBHOOK_SECRET',
            'TWITTER_CLIENT_SECRET', 'FACEBOOK_CLIENT_SECRET', 'INSTAGRAM_CLIENT_SECRET',
            'LINKEDIN_CLIENT_SECRET', 'GITHUB_CLIENT_SECRET', 'GOOGLE_CLIENT_SECRET'
        ]
        
        results = {}
        
        for key in secret_keys:
            value = os.getenv(key)
            if value:
                results[key] = self.validate_secret(key, value)
            else:
                results[key] = SecretValidationResult(
                    is_valid=key.endswith('_CLIENT_SECRET'),  # OAuth secrets are optional
                    secret_type=self._determine_secret_type(key),
                    severity=SecretSeverity.MEDIUM if key.endswith('_CLIENT_SECRET') else SecretSeverity.HIGH,
                    message=f"Secret '{key}' not set in environment",
                    recommendations=[f"Set {key} environment variable with proper value"]
                )
        
        return results
    
    def _check_placeholder_patterns(self, key: str, value: str) -> Optional[SecretValidationResult]:
        """Check if secret contains placeholder/example patterns"""
        rules = self.environment_rules.get(self.environment, {})
        
        if not rules.get("allow_placeholders", False):
            for pattern in self.placeholder_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    return SecretValidationResult(
                        is_valid=False,
                        secret_type=self._determine_secret_type(key),
                        severity=SecretSeverity.CRITICAL,
                        message=f"Secret '{key}' contains placeholder/example value: {pattern}",
                        recommendations=[
                            f"Replace placeholder value in {key}",
                            "Generate a proper secret for production use",
                            "Never use example values in production"
                        ]
                    )
        
        return None
    
    def _check_dangerous_patterns(self, key: str, value: str) -> Optional[SecretValidationResult]:
        """Check if secret matches known dangerous patterns"""
        for secret_type, patterns in self.dangerous_patterns.items():
            for pattern in patterns:
                if re.search(pattern, value):
                    if self._is_production_like_secret(value):
                        return SecretValidationResult(
                            is_valid=False,
                            secret_type=secret_type,
                            severity=SecretSeverity.CRITICAL,
                            message=f"Secret '{key}' appears to contain a real {secret_type.value}",
                            recommendations=[
                                f"Never hard-code {secret_type.value} in source code",
                                f"Move {key} to environment variables",
                                "Rotate this secret immediately if exposed",
                                "Review version control history for exposure"
                            ]
                        )
        
        return None
    
    def _check_environment_rules(self, key: str, value: str) -> Optional[SecretValidationResult]:
        """Check environment-specific rules"""
        rules = self.environment_rules.get(self.environment, {})
        
        min_length = rules.get("minimum_key_length", 16)
        if len(value) < min_length:
            return SecretValidationResult(
                is_valid=False,
                secret_type=self._determine_secret_type(key),
                severity=SecretSeverity.HIGH,
                message=f"Secret '{key}' is too short ({len(value)} < {min_length} chars)",
                recommendations=[
                    f"Use at least {min_length} characters for {key}",
                    "Generate a stronger secret with more entropy"
                ]
            )
        
        if rules.get("require_complex_secrets", False):
            if not self._is_complex_secret(value):
                return SecretValidationResult(
                    is_valid=False,
                    secret_type=self._determine_secret_type(key),
                    severity=SecretSeverity.MEDIUM,
                    message=f"Secret '{key}' lacks complexity for {self.environment} environment",
                    recommendations=[
                        "Use a mix of uppercase, lowercase, numbers, and symbols",
                        "Generate secrets using cryptographically secure methods"
                    ]
                )
        
        return None
    
    def _determine_secret_type(self, key: str) -> SecretType:
        """Determine the type of secret based on key name"""
        key_lower = key.lower()
        
        if 'api_key' in key_lower or key_lower.endswith('_key'):
            return SecretType.API_KEY
        elif 'database' in key_lower or 'db_' in key_lower:
            return SecretType.DATABASE_PASSWORD
        elif 'jwt' in key_lower:
            return SecretType.JWT_SECRET
        elif 'encryption' in key_lower or 'encrypt' in key_lower:
            return SecretType.ENCRYPTION_KEY
        elif 'webhook' in key_lower:
            return SecretType.WEBHOOK_SECRET
        elif 'client_secret' in key_lower or 'oauth' in key_lower:
            return SecretType.OAUTH_SECRET
        else:
            return SecretType.API_KEY
    
    def _validate_secret_type(self, key: str, value: str, secret_type: SecretType) -> Optional[SecretValidationResult]:
        """Perform type-specific validation"""
        if secret_type == SecretType.DATABASE_PASSWORD:
            return self._validate_database_url(key, value)
        elif secret_type == SecretType.JWT_SECRET:
            return self._validate_jwt_secret(key, value)
        elif secret_type == SecretType.ENCRYPTION_KEY:
            return self._validate_encryption_key(key, value)
        
        return None
    
    def _validate_database_url(self, key: str, value: str) -> Optional[SecretValidationResult]:
        """Validate database URL format and security"""
        if not value.startswith(('postgresql://', 'mysql://', 'sqlite:///')):
            return SecretValidationResult(
                is_valid=False,
                secret_type=SecretType.DATABASE_PASSWORD,
                severity=SecretSeverity.HIGH,
                message=f"Database URL '{key}' has unsupported format",
                recommendations=["Use postgresql://, mysql://, or sqlite:/// format"]
            )
        
        # Check for localhost in production
        if self.environment == "production" and "localhost" in value:
            return SecretValidationResult(
                is_valid=False,
                secret_type=SecretType.DATABASE_PASSWORD,
                severity=SecretSeverity.HIGH,
                message=f"Database URL '{key}' uses localhost in production",
                recommendations=["Use proper production database host"]
            )
        
        return None
    
    def _validate_jwt_secret(self, key: str, value: str) -> Optional[SecretValidationResult]:
        """Validate JWT secret strength"""
        if len(value) < 64:
            return SecretValidationResult(
                is_valid=False,
                secret_type=SecretType.JWT_SECRET,
                severity=SecretSeverity.HIGH,
                message=f"JWT secret '{key}' should be at least 64 characters",
                recommendations=["Generate a longer JWT secret for better security"]
            )
        
        return None
    
    def _validate_encryption_key(self, key: str, value: str) -> Optional[SecretValidationResult]:
        """Validate encryption key format"""
        if len(value) not in [16, 24, 32]:  # AES key lengths
            return SecretValidationResult(
                is_valid=False,
                secret_type=SecretType.ENCRYPTION_KEY,
                severity=SecretSeverity.MEDIUM,
                message=f"Encryption key '{key}' has non-standard length ({len(value)})",
                recommendations=["Use 16, 24, or 32 character encryption keys for AES"]
            )
        
        return None
    
    def _is_production_like_secret(self, value: str) -> bool:
        """Check if secret looks like a real production secret"""
        # Check for patterns that indicate real secrets
        real_patterns = [
            r'sk-[a-zA-Z0-9]{32,}',  # Real OpenAI keys
            r'xai-[a-zA-Z0-9]{32,}',  # Real xAI keys
            r'pk_live_[a-zA-Z0-9]{24,}',  # Live Stripe keys
            r'sk_live_[a-zA-Z0-9]{24,}',  # Live Stripe keys
        ]
        
        for pattern in real_patterns:
            if re.search(pattern, value):
                return True
        
        return False
    
    def _is_complex_secret(self, value: str) -> bool:
        """Check if secret has sufficient complexity"""
        has_upper = any(c.isupper() for c in value)
        has_lower = any(c.islower() for c in value)
        has_digit = any(c.isdigit() for c in value)
        has_symbol = any(not c.isalnum() for c in value)
        
        complexity_score = sum([has_upper, has_lower, has_digit, has_symbol])
        return complexity_score >= 3


def validate_secrets_on_startup(environment: str = "production") -> Tuple[bool, List[str]]:
    """
    Validate all secrets on application startup
    
    Args:
        environment: Current environment (production, staging, development)
        
    Returns:
        Tuple of (all_valid, error_messages)
    """
    validator = SecretsValidator(environment)
    results = validator.validate_all_secrets()
    
    errors = []
    critical_failures = 0
    
    for key, result in results.items():
        if not result.is_valid:
            if result.severity == SecretSeverity.CRITICAL:
                critical_failures += 1
                errors.append(f"CRITICAL: {result.message}")
            elif result.severity == SecretSeverity.HIGH:
                errors.append(f"HIGH: {result.message}")
            elif result.severity == SecretSeverity.MEDIUM:
                errors.append(f"MEDIUM: {result.message}")
    
    # In production, any critical failure should stop startup
    if environment == "production" and critical_failures > 0:
        return False, errors
    
    # Log all errors but allow startup in development
    if errors:
        logger.warning(f"Secrets validation found {len(errors)} issues in {environment}")
        for error in errors:
            logger.warning(f"Secret validation: {error}")
    
    return len(errors) == 0 or environment == "development", errors


def generate_secure_secret(length: int = 64) -> str:
    """
    Generate a cryptographically secure secret
    
    Args:
        length: Length of secret to generate
        
    Returns:
        Base64-encoded secure random secret
    """
    import secrets
    import base64
    
    # Generate random bytes
    random_bytes = secrets.token_bytes(length // 4 * 3)  # Adjust for base64 encoding
    
    # Base64 encode to get URL-safe string
    secret = base64.urlsafe_b64encode(random_bytes).decode('utf-8')
    
    # Trim to exact length requested
    return secret[:length]


def get_secrets_validator() -> SecretsValidator:
    """Get a configured secrets validator for the current environment"""
    environment = os.getenv("ENVIRONMENT", "production")
    return SecretsValidator(environment)