"""
Distributed Security Configuration - P0-13b
Feature flag and configuration system for distributed security middleware migration
"""
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DistributedSecurityConfig:
    """Configuration for distributed security features"""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "production").lower()
        
        # Feature flags for gradual rollout
        self._feature_flags = {
            # P0-13b: Distributed rate limiting
            "distributed_rate_limiting": self._get_bool_env("DISTRIBUTED_RATE_LIMITING_ENABLED", True),
            
            # P0-13c: Enhanced session security (future)
            "enhanced_session_security": self._get_bool_env("ENHANCED_SESSION_SECURITY_ENABLED", False),
            
            # Fallback behavior
            "fail_open_on_redis_error": self._get_bool_env("FAIL_OPEN_ON_REDIS_ERROR", False),  # Fail closed by default
            
            # Migration flags
            "hybrid_rate_limiting": self._get_bool_env("HYBRID_RATE_LIMITING", False),  # Use old + new in parallel
            "rate_limiting_debug": self._get_bool_env("RATE_LIMITING_DEBUG", False)
        }
        
        # Configuration
        self._config = {
            # Redis configuration
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            "redis_connection_timeout": int(os.getenv("REDIS_CONNECTION_TIMEOUT", "5")),
            "redis_socket_timeout": int(os.getenv("REDIS_SOCKET_TIMEOUT", "10")),
            "redis_max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "20")),
            
            # Rate limiting configuration
            "rate_limit_per_second": int(os.getenv("RATE_LIMIT_PER_SECOND", "10")),
            "rate_limit_per_minute": int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
            "rate_limit_per_hour": int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
            "rate_limit_burst": int(os.getenv("RATE_LIMIT_BURST", "20")),
            "rate_limit_burst_window": int(os.getenv("RATE_LIMIT_BURST_WINDOW", "10")),
            
            # Production adjustments
            "production_rate_limit_per_minute": int(os.getenv("PRODUCTION_RATE_LIMIT_PER_MINUTE", "120")),
            "production_rate_limit_per_hour": int(os.getenv("PRODUCTION_RATE_LIMIT_PER_HOUR", "2000")),
            "production_burst_limit": int(os.getenv("PRODUCTION_BURST_LIMIT", "30")),
            
            # Security settings
            "enable_csrf_protection": self._get_bool_env("CSRF_PROTECTION_ENABLED", True),
            "enable_request_validation": self._get_bool_env("REQUEST_VALIDATION_ENABLED", True),
            "enable_security_headers": self._get_bool_env("SECURITY_HEADERS_ENABLED", True),
            
            # Monitoring and observability
            "enable_security_metrics": self._get_bool_env("SECURITY_METRICS_ENABLED", True),
            "security_log_level": os.getenv("SECURITY_LOG_LEVEL", "INFO").upper(),
        }
        
        logger.info(f"Distributed security config initialized for {self.environment}")
        self._log_configuration()
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable with default"""
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on", "enabled")
    
    def _log_configuration(self):
        """Log current configuration (excluding sensitive data)"""
        logger.info("🔒 Distributed Security Configuration:")
        logger.info(f"  Environment: {self.environment}")
        logger.info("  Feature Flags:")
        for flag, enabled in self._feature_flags.items():
            status = "✅ ENABLED" if enabled else "❌ DISABLED"
            logger.info(f"    {flag}: {status}")
        
        logger.info("  Rate Limiting:")
        logger.info(f"    Per Second: {self._config['rate_limit_per_second']}")
        logger.info(f"    Per Minute: {self._config['rate_limit_per_minute']}")
        logger.info(f"    Per Hour: {self._config['rate_limit_per_hour']}")
        logger.info(f"    Burst Limit: {self._config['rate_limit_burst']}")
        
        if self.environment == "production":
            logger.info("  Production Overrides:")
            logger.info(f"    Per Minute: {self._config['production_rate_limit_per_minute']}")
            logger.info(f"    Per Hour: {self._config['production_rate_limit_per_hour']}")
            logger.info(f"    Burst: {self._config['production_burst_limit']}")
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature flag is enabled"""
        return self._feature_flags.get(feature, False)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)
    
    def get_rate_limiting_config(self) -> Dict[str, int]:
        """Get rate limiting configuration for current environment"""
        if self.environment == "production":
            return {
                "requests_per_second": self._config["rate_limit_per_second"],
                "requests_per_minute": self._config["production_rate_limit_per_minute"],
                "requests_per_hour": self._config["production_rate_limit_per_hour"],
                "burst_limit": self._config["production_burst_limit"],
                "burst_window_seconds": self._config["rate_limit_burst_window"]
            }
        else:
            return {
                "requests_per_second": self._config["rate_limit_per_second"],
                "requests_per_minute": self._config["rate_limit_per_minute"],
                "requests_per_hour": self._config["rate_limit_per_hour"],
                "burst_limit": self._config["rate_limit_burst"],
                "burst_window_seconds": self._config["rate_limit_burst_window"]
            }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration"""
        return {
            "redis_url": self._config["redis_url"],
            "connection_timeout": self._config["redis_connection_timeout"],
            "socket_timeout": self._config["redis_socket_timeout"],
            "max_connections": self._config["redis_max_connections"]
        }
    
    def should_use_distributed_security(self) -> bool:
        """Determine if distributed security should be used"""
        return self.is_feature_enabled("distributed_rate_limiting")
    
    def should_fail_open_on_redis_error(self) -> bool:
        """Determine fail-open vs fail-closed behavior for Redis errors"""
        if self.environment == "production":
            # Production: fail closed by default for security
            return self._feature_flags.get("fail_open_on_redis_error", False)
        else:
            # Development: more lenient, can fail open
            return self._feature_flags.get("fail_open_on_redis_error", True)
    
    def get_migration_strategy(self) -> str:
        """Get current migration strategy"""
        if self.is_feature_enabled("hybrid_rate_limiting"):
            return "hybrid"  # Run both old and new systems in parallel
        elif self.is_feature_enabled("distributed_rate_limiting"):
            return "distributed_only"  # Use only distributed system
        else:
            return "legacy"  # Use only legacy system
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration and return status"""
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "redis_available": False,
            "rate_limits_configured": True
        }
        
        # Check Redis availability if distributed features are enabled
        if self.should_use_distributed_security():
            try:
                import redis
                redis_client = redis.from_url(self._config["redis_url"], socket_connect_timeout=1)
                redis_client.ping()
                validation_result["redis_available"] = True
                redis_client.close()
            except Exception as e:
                validation_result["redis_available"] = False
                if self.environment == "production":
                    validation_result["errors"].append(f"Redis not available for distributed security: {e}")
                    validation_result["valid"] = False
                else:
                    validation_result["warnings"].append(f"Redis not available, will use fallback: {e}")
        
        # Validate rate limiting configuration
        rate_config = self.get_rate_limiting_config()
        if rate_config["requests_per_minute"] <= 0:
            validation_result["errors"].append("Invalid rate limit configuration: requests_per_minute must be > 0")
            validation_result["valid"] = False
        
        if rate_config["burst_limit"] > rate_config["requests_per_minute"]:
            validation_result["warnings"].append("Burst limit exceeds per-minute limit - may cause unexpected behavior")
        
        return validation_result

# Global configuration instance
distributed_security_config = DistributedSecurityConfig()

def get_distributed_security_config() -> DistributedSecurityConfig:
    """Get the global distributed security configuration"""
    return distributed_security_config

def validate_distributed_security_setup() -> bool:
    """Validate that distributed security is properly configured"""
    config = get_distributed_security_config()
    validation = config.validate_configuration()
    
    if not validation["valid"]:
        logger.error("❌ Distributed security configuration validation failed:")
        for error in validation["errors"]:
            logger.error(f"  - {error}")
        return False
    
    if validation["warnings"]:
        logger.warning("⚠️ Distributed security configuration warnings:")
        for warning in validation["warnings"]:
            logger.warning(f"  - {warning}")
    
    logger.info("✅ Distributed security configuration validated successfully")
    return True