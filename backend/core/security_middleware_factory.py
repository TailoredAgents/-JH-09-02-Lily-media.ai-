"""
Security Middleware Factory - P0-13b Migration Support
Provides migration path from legacy to distributed security middleware
"""
import logging
from typing import Optional
from fastapi import FastAPI

from backend.core.distributed_security_config import (
    get_distributed_security_config, 
    validate_distributed_security_setup
)

logger = logging.getLogger(__name__)

def setup_security_middleware_with_migration(app: FastAPI, environment: str = "production") -> bool:
    """
    Setup security middleware with migration support
    
    This function handles the migration from legacy security middleware
    to distributed Redis-only middleware for P0-13b compliance.
    
    Args:
        app: FastAPI application instance
        environment: Environment name
        
    Returns:
        bool: Success status
    """
    config = get_distributed_security_config()
    migration_strategy = config.get_migration_strategy()
    
    logger.info(f"🔄 Setting up security middleware with migration strategy: {migration_strategy}")
    
    try:
        if migration_strategy == "distributed_only":
            # P0-13b: Use distributed Redis-only security middleware
            return _setup_distributed_security(app, environment, config)
            
        elif migration_strategy == "hybrid":
            # Hybrid mode: Run both systems for comparison/validation
            return _setup_hybrid_security(app, environment, config)
            
        else:  # legacy
            # Fallback to legacy middleware
            return _setup_legacy_security(app, environment)
    
    except Exception as e:
        logger.error(f"❌ Failed to setup security middleware: {e}")
        
        # Fallback to legacy in case of errors
        if migration_strategy != "legacy":
            logger.warning("🔄 Falling back to legacy security middleware")
            return _setup_legacy_security(app, environment)
        
        raise

def _setup_distributed_security(app: FastAPI, environment: str, config) -> bool:
    """Setup distributed Redis-only security middleware"""
    logger.info("🔒 Setting up DISTRIBUTED security middleware (Redis-only)")
    
    # Validate configuration first
    if not validate_distributed_security_setup():
        if environment == "production":
            raise RuntimeError("Distributed security validation failed in production")
        else:
            logger.warning("Distributed security validation failed, falling back to legacy")
            return _setup_legacy_security(app, environment)
    
    try:
        # Import distributed middleware
        from backend.core.distributed_security_middleware import setup_distributed_security_middleware
        
        # Setup distributed security stack
        setup_distributed_security_middleware(app, environment)
        
        logger.info("✅ Distributed security middleware setup completed")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import distributed security middleware: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to setup distributed security middleware: {e}")
        raise

def _setup_hybrid_security(app: FastAPI, environment: str, config) -> bool:
    """Setup hybrid security (both legacy and distributed for comparison)"""
    logger.info("🔀 Setting up HYBRID security middleware (legacy + distributed)")
    
    # This is primarily for testing and gradual migration
    # Not recommended for production use
    
    success_legacy = False
    success_distributed = False
    
    try:
        # Setup legacy first
        success_legacy = _setup_legacy_security(app, environment)
        
        # Setup distributed with different configuration
        if config.is_feature_enabled("distributed_rate_limiting"):
            try:
                from backend.core.distributed_security_middleware import DistributedRateLimitMiddleware
                from backend.services.distributed_rate_limiter import RateLimitConfig
                
                rate_config = config.get_rate_limiting_config()
                
                # Add distributed rate limiter in monitoring mode
                app.add_middleware(
                    DistributedRateLimitMiddleware,
                    **rate_config,
                    environment=f"{environment}_hybrid"
                )
                
                success_distributed = True
                logger.info("✅ Hybrid distributed rate limiting added")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to add distributed component to hybrid setup: {e}")
    
    except Exception as e:
        logger.error(f"❌ Hybrid security setup failed: {e}")
        return False
    
    if success_legacy:
        logger.info("✅ Hybrid security middleware setup completed (legacy base)")
        return True
    else:
        logger.error("❌ Hybrid security setup failed - legacy component failed")
        return False

def _setup_legacy_security(app: FastAPI, environment: str) -> bool:
    """Setup legacy security middleware"""
    logger.info("🔒 Setting up LEGACY security middleware (with Redis fallback)")
    
    try:
        # Import legacy middleware
        from backend.core.security_middleware import setup_security_middleware
        
        # Setup legacy security stack
        setup_security_middleware(app, environment)
        
        logger.info("✅ Legacy security middleware setup completed")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import legacy security middleware: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to setup legacy security middleware: {e}")
        return False

def get_security_middleware_status() -> dict:
    """Get current security middleware status and configuration"""
    config = get_distributed_security_config()
    
    status = {
        "migration_strategy": config.get_migration_strategy(),
        "distributed_enabled": config.is_feature_enabled("distributed_rate_limiting"),
        "environment": config.environment,
        "feature_flags": {
            "distributed_rate_limiting": config.is_feature_enabled("distributed_rate_limiting"),
            "enhanced_session_security": config.is_feature_enabled("enhanced_session_security"),
            "fail_open_on_redis_error": config.should_fail_open_on_redis_error(),
        },
        "rate_limiting_config": config.get_rate_limiting_config(),
        "redis_config": {
            "url_configured": bool(config.get_config("redis_url")),
            "connection_timeout": config.get_config("redis_connection_timeout"),
            "max_connections": config.get_config("redis_max_connections")
        },
        "validation": config.validate_configuration()
    }
    
    return status

def migrate_to_distributed_security() -> bool:
    """
    Migrate from legacy to distributed security middleware
    
    This function can be called during runtime to switch middleware
    (requires application restart in most cases)
    """
    config = get_distributed_security_config()
    
    logger.info("🔄 Initiating migration to distributed security")
    
    # Validate distributed setup
    validation = config.validate_configuration()
    if not validation["valid"]:
        logger.error("❌ Cannot migrate - distributed security validation failed")
        return False
    
    # Set feature flag
    import os
    os.environ["DISTRIBUTED_RATE_LIMITING_ENABLED"] = "true"
    
    logger.info("✅ Migration flag set - restart application to complete migration")
    return True

def rollback_to_legacy_security() -> bool:
    """
    Rollback from distributed to legacy security middleware
    
    Emergency rollback function for production issues
    """
    logger.warning("🔄 Initiating ROLLBACK to legacy security middleware")
    
    # Disable distributed features
    import os
    os.environ["DISTRIBUTED_RATE_LIMITING_ENABLED"] = "false"
    os.environ["HYBRID_RATE_LIMITING"] = "false"
    
    logger.info("✅ Rollback flag set - restart application to complete rollback")
    return True