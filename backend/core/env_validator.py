"""
Environment Variable Validation for Production Readiness
Validates all required and optional environment variables on startup
"""
import os
import logging
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation level for environment variables"""
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"

class EnvironmentValidator:
    """Comprehensive environment variable validator"""
    
    def __init__(self):
        self.validation_rules = {
            # Core application settings
            "SECRET_KEY": {
                "level": ValidationLevel.REQUIRED,
                "description": "Secret key for JWT and encryption",
                "min_length": 32,
                "example": "your-super-secret-key-here-make-it-long-and-random"
            },
            "DATABASE_URL": {
                "level": ValidationLevel.REQUIRED,
                "description": "Database connection URL",
                "example": "postgresql://user:password@localhost/dbname"
            },
            "ENVIRONMENT": {
                "level": ValidationLevel.RECOMMENDED,
                "description": "Application environment",
                "allowed_values": ["development", "staging", "production"],
                "default": "development"
            },
            
            # External service configurations
            "OPENAI_API_KEY": {
                "level": ValidationLevel.REQUIRED,
                "description": "OpenAI API key for content generation",
                "pattern": r"^sk-[a-zA-Z0-9]{48}$",
                "example": "sk-youropenaiapikey..."
            },
            "SERPER_API_KEY": {
                "level": ValidationLevel.RECOMMENDED,
                "description": "Serper API key for web search",
                "example": "your-serper-api-key"
            },
            
            # Security and Token Encryption
            "TOKEN_ENCRYPTION_KEY": {
                "level": ValidationLevel.REQUIRED,
                "description": "32-character encryption key for partner OAuth tokens",
                "min_length": 32,
                "example": "your-secure-32-char-encryption-key-here"
            },
            
            # Redis configuration
            "REDIS_URL": {
                "level": ValidationLevel.RECOMMENDED,
                "description": "Redis URL for caching and session storage",
                "example": "redis://localhost:6379/0"
            },
            
            # Social media platform configurations
            "TWITTER_API_KEY": {
                "level": ValidationLevel.OPTIONAL,
                "description": "Twitter API key for X/Twitter integration"
            },
            "TWITTER_API_SECRET": {
                "level": ValidationLevel.OPTIONAL,
                "description": "Twitter API secret"
            },
            "TWITTER_BEARER_TOKEN": {
                "level": ValidationLevel.OPTIONAL,
                "description": "Twitter Bearer token for API v2"
            },
            "INSTAGRAM_CLIENT_ID": {
                "level": ValidationLevel.OPTIONAL,
                "description": "Instagram Client ID for Instagram integration"
            },
            "INSTAGRAM_CLIENT_SECRET": {
                "level": ValidationLevel.OPTIONAL,
                "description": "Instagram Client Secret"
            },
            "LINKEDIN_CLIENT_ID": {
                "level": ValidationLevel.OPTIONAL,
                "description": "LinkedIn Client ID for LinkedIn integration"
            },
            "LINKEDIN_CLIENT_SECRET": {
                "level": ValidationLevel.OPTIONAL,
                "description": "LinkedIn Client Secret"
            },
            "FACEBOOK_APP_ID": {
                "level": ValidationLevel.OPTIONAL,
                "description": "Facebook App ID for Facebook integration"
            },
            "FACEBOOK_APP_SECRET": {
                "level": ValidationLevel.OPTIONAL,
                "description": "Facebook App Secret"
            },
            
            # Monitoring and logging
            "LOG_LEVEL": {
                "level": ValidationLevel.OPTIONAL,
                "description": "Logging level",
                "allowed_values": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "default": "INFO"
            },
            "SENTRY_DSN": {
                "level": ValidationLevel.OPTIONAL,
                "description": "Sentry DSN for error tracking"
            },
            
            # Security Headers and Production Settings
            "FORCE_HTTPS": {
                "level": ValidationLevel.RECOMMENDED,
                "description": "Force HTTPS in production",
                "type": "boolean",
                "allowed_values": ["true", "false"],
                "default": "false"
            },
            "SECURE_COOKIES": {
                "level": ValidationLevel.RECOMMENDED,
                "description": "Enable secure cookie flags",
                "type": "boolean",
                "allowed_values": ["true", "false"],
                "default": "false"
            },
            "SECURE_HEADERS": {
                "level": ValidationLevel.RECOMMENDED,
                "description": "Enable security headers (CSP, HSTS, etc)",
                "type": "boolean",
                "allowed_values": ["true", "false"],
                "default": "false"
            },
            "CORS_ORIGINS": {
                "level": ValidationLevel.RECOMMENDED,
                "description": "Allowed CORS origins for production",
                "example": "https://your-domain.com,https://www.your-domain.com"
            },
            
            # Performance and scaling
            "MAX_WORKERS": {
                "level": ValidationLevel.OPTIONAL,
                "description": "Maximum number of worker processes",
                "type": "integer",
                "default": "4"
            },
            "REQUEST_TIMEOUT": {
                "level": ValidationLevel.OPTIONAL,
                "description": "Request timeout in seconds",
                "type": "integer",
                "default": "120"
            }
        }
    
    def validate_single_variable(self, var_name: str, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single environment variable"""
        result = {
            "name": var_name,
            "level": rule["level"].value,
            "description": rule["description"],
            "status": "missing",
            "value_provided": False,
            "errors": [],
            "warnings": []
        }
        
        value = os.getenv(var_name)
        
        if value:
            result["value_provided"] = True
            result["status"] = "present"
            
            # Length validation
            if "min_length" in rule and len(value) < rule["min_length"]:
                result["errors"].append(f"Value too short (minimum {rule['min_length']} characters)")
                result["status"] = "invalid"
            
            # Pattern validation
            if "pattern" in rule:
                import re
                if not re.match(rule["pattern"], value):
                    result["errors"].append(f"Value does not match required pattern")
                    result["status"] = "invalid"
            
            # Allowed values validation
            if "allowed_values" in rule and value not in rule["allowed_values"]:
                result["errors"].append(f"Value must be one of: {', '.join(rule['allowed_values'])}")
                result["status"] = "invalid"
            
            # Type validation
            if "type" in rule:
                if rule["type"] == "integer":
                    try:
                        int(value)
                    except ValueError:
                        result["errors"].append("Value must be an integer")
                        result["status"] = "invalid"
            
            # Check for default values in production
            if os.getenv("ENVIRONMENT") == "production":
                if "example" in rule and value == rule["example"]:
                    result["warnings"].append("Using example value in production")
                    result["status"] = "warning"
        else:
            # Check if there's a default value
            if "default" in rule:
                result["default_available"] = rule["default"]
                result["status"] = "using_default"
            
            # Check dependencies
            if "dependency" in rule:
                dependency_value = os.getenv(rule["dependency"])
                if dependency_value:
                    result["warnings"].append(f"Required when {rule['dependency']} is set")
        
        return result
    
    def validate_environment(self) -> Dict[str, Any]:
        """Validate all environment variables"""
        results = {}
        errors = []
        warnings = []
        
        for var_name, rule in self.validation_rules.items():
            validation_result = self.validate_single_variable(var_name, rule)
            results[var_name] = validation_result
            
            # Collect errors and warnings
            if validation_result["errors"]:
                errors.extend([f"{var_name}: {error}" for error in validation_result["errors"]])
            
            if validation_result["warnings"]:
                warnings.extend([f"{var_name}: {warning}" for warning in validation_result["warnings"]])
            
            # Check required variables
            if rule["level"] == ValidationLevel.REQUIRED and validation_result["status"] == "missing":
                errors.append(f"{var_name}: Required environment variable is missing")
        
        # Calculate completeness
        total_vars = len(self.validation_rules)
        provided_vars = len([r for r in results.values() if r["value_provided"]])
        required_vars = len([r for r in self.validation_rules.values() if r["level"] == ValidationLevel.REQUIRED])
        required_provided = len([
            r for r in results.values() 
            if r["value_provided"] and 
            self.validation_rules[r["name"]]["level"] == ValidationLevel.REQUIRED
        ])
        
        completeness = (provided_vars / total_vars) * 100
        required_completeness = (required_provided / required_vars) * 100 if required_vars > 0 else 100
        
        # Generate recommendations
        recommendations = []
        
        if completeness < 80:
            recommendations.append("Consider setting more optional environment variables for enhanced functionality")
        
        if not os.getenv("REDIS_URL"):
            recommendations.append("Set up Redis for improved caching and performance")
        
        # Security-specific recommendations
        if not os.getenv("TOKEN_ENCRYPTION_KEY"):
            recommendations.append("CRITICAL: Generate a secure TOKEN_ENCRYPTION_KEY for partner OAuth tokens")
        
        if os.getenv("TOKEN_ENCRYPTION_KEY") == "your-secure-32-char-encryption-key-here":
            recommendations.append("SECURITY RISK: Change TOKEN_ENCRYPTION_KEY from default example value")
        
        # Environment-specific recommendations
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production":
            if not os.getenv("SENTRY_DSN"):
                recommendations.append("Set up Sentry DSN for error monitoring in production")
            
            if os.getenv("LOG_LEVEL") == "DEBUG":
                recommendations.append("Consider using INFO or WARNING log level in production")
            
            # Production security hardening recommendations
            if not os.getenv("FORCE_HTTPS") or os.getenv("FORCE_HTTPS").lower() != "true":
                recommendations.append("SECURITY: Enable FORCE_HTTPS=true for production")
            
            if not os.getenv("SECURE_HEADERS") or os.getenv("SECURE_HEADERS").lower() != "true":
                recommendations.append("SECURITY: Enable SECURE_HEADERS=true for security headers (CSP, HSTS, etc)")
            
            if not os.getenv("SECURE_COOKIES") or os.getenv("SECURE_COOKIES").lower() != "true":
                recommendations.append("SECURITY: Enable SECURE_COOKIES=true for production")
            
            if not os.getenv("CORS_ORIGINS"):
                recommendations.append("SECURITY: Set specific CORS_ORIGINS instead of allowing all origins")
            
            # Strong secret key validation
            secret_key = os.getenv("SECRET_KEY", "")
            if len(secret_key) < 32:
                recommendations.append("SECURITY RISK: SECRET_KEY should be at least 32 characters long")
            
            if secret_key == "your-super-secret-key-change-this":
                recommendations.append("CRITICAL: Change SECRET_KEY from default example value")
        
        return {
            "validation_passed": len(errors) == 0,
            "environment": env,
            "configuration_completeness": round(completeness, 1),
            "required_completeness": round(required_completeness, 1),
            "total_variables": total_vars,
            "provided_variables": provided_vars,
            "required_variables": required_vars,
            "required_provided": required_provided,
            "results": results,
            "errors": errors,
            "warnings": warnings,
            "recommendations": recommendations,
            "summary": {
                "status": "valid" if len(errors) == 0 else "invalid",
                "missing_required": required_vars - required_provided,
                "total_issues": len(errors) + len(warnings)
            }
        }

# Global validator instance
env_validator = EnvironmentValidator()

def validate_environment() -> Dict[str, Any]:
    """Validate environment variables and return results"""
    return env_validator.validate_environment()

def validate_on_startup():
    """Validate environment on startup and log critical issues"""
    validation_result = validate_environment()
    
    if not validation_result["validation_passed"]:
        logger.error("❌ Environment validation failed!")
        for error in validation_result["errors"]:
            logger.error(f"  - {error}")
        
        # Don't start if required variables are missing
        missing_required = validation_result["summary"]["missing_required"]
        if missing_required > 0:
            raise EnvironmentError(
                f"Missing {missing_required} required environment variables. "
                f"Check logs for details or run environment validation endpoint."
            )
    else:
        logger.info("✅ Environment validation passed")
        
        # Log warnings if any
        if validation_result["warnings"]:
            logger.warning(f"Environment validation warnings ({len(validation_result['warnings'])}):")
            for warning in validation_result["warnings"]:
                logger.warning(f"  - {warning}")
        
        # Log completeness
        completeness = validation_result["configuration_completeness"]
        logger.info(f"📊 Environment configuration: {completeness}% complete")
        
        # Log recommendations
        if validation_result["recommendations"]:
            logger.info("💡 Environment recommendations:")
            for rec in validation_result["recommendations"]:
                logger.info(f"  - {rec}")
