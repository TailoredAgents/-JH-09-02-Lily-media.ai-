"""
Feature Flag Enforcement Middleware
Enforces feature flags on API endpoints and provides decorators for feature gating
"""
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from functools import wraps

from backend.core.feature_flags import ff, feature_flags

logger = logging.getLogger(__name__)


class FeatureFlagDependencies:
    """
    FastAPI dependencies for feature flag enforcement
    """
    
    @staticmethod
    def require_flag(flag_name: str, error_message: Optional[str] = None):
        """
        FastAPI dependency factory to require a feature flag to be enabled
        
        Usage:
            @router.post("/experimental-endpoint")
            async def experimental_endpoint(
                _: None = Depends(require_flag("EXPERIMENTAL_FEATURE"))
            ):
                ...
        
        Args:
            flag_name: Name of the feature flag to check
            error_message: Custom error message (optional)
            
        Returns:
            FastAPI dependency function
        """
        def dependency() -> None:
            if not ff(flag_name):
                message = error_message or f"Feature '{flag_name}' is not enabled"
                logger.warning(f"Feature flag check failed: {flag_name}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "error": "feature_disabled",
                        "message": message,
                        "flag": flag_name,
                        "enabled": False
                    }
                )
            return None
        
        return dependency
    
    @staticmethod
    def require_any_flag(*flag_names: str, error_message: Optional[str] = None):
        """
        FastAPI dependency factory to require at least one of multiple feature flags
        
        Usage:
            @router.post("/multi-feature-endpoint")
            async def endpoint(
                _: None = Depends(require_any_flag("FEATURE_A", "FEATURE_B"))
            ):
                ...
        """
        def dependency() -> None:
            enabled_flags = [name for name in flag_names if ff(name)]
            
            if not enabled_flags:
                flags_str = "', '".join(flag_names)
                message = error_message or f"At least one of these features must be enabled: '{flags_str}'"
                logger.warning(f"Multi-flag check failed: none of {flag_names} are enabled")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "error": "features_disabled",
                        "message": message,
                        "required_flags": list(flag_names),
                        "enabled_flags": enabled_flags
                    }
                )
            return None
        
        return dependency
    
    @staticmethod
    def require_all_flags(*flag_names: str, error_message: Optional[str] = None):
        """
        FastAPI dependency factory to require all specified feature flags
        
        Usage:
            @router.post("/advanced-endpoint") 
            async def endpoint(
                _: None = Depends(require_all_flags("FEATURE_A", "FEATURE_B"))
            ):
                ...
        """
        def dependency() -> None:
            disabled_flags = [name for name in flag_names if not ff(name)]
            
            if disabled_flags:
                disabled_str = "', '".join(disabled_flags)
                message = error_message or f"These features must be enabled: '{disabled_str}'"
                logger.warning(f"Multi-flag check failed: {disabled_flags} are disabled")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "error": "features_disabled", 
                        "message": message,
                        "required_flags": list(flag_names),
                        "disabled_flags": disabled_flags
                    }
                )
            return None
        
        return dependency


# Convenience instances for common usage
require_flag = FeatureFlagDependencies.require_flag
require_any_flag = FeatureFlagDependencies.require_any_flag
require_all_flags = FeatureFlagDependencies.require_all_flags

# Common feature flag requirements based on current flags
require_workflow_v2 = require_flag("WORKFLOW_V2")
require_deep_research = require_flag("ENABLE_DEEP_RESEARCH")

# Function decorator for non-FastAPI usage
def feature_flag_required(flag_name: str, error_message: Optional[str] = None):
    """
    Function decorator to require feature flag for regular functions
    
    Usage:
        @feature_flag_required("EXPERIMENTAL_FEATURE")
        def experimental_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not ff(flag_name):
                message = error_message or f"Feature '{flag_name}' is not enabled"
                logger.warning(f"Feature flag check failed in {func.__name__}: {flag_name}")
                raise RuntimeError(message)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_enabled_flags() -> Dict[str, bool]:
    """
    Get all currently enabled feature flags
    
    Returns:
        Dictionary of flag names and their status
    """
    return feature_flags()


def is_feature_enabled(flag_name: str) -> bool:
    """
    Check if a specific feature flag is enabled
    
    Args:
        flag_name: Name of the feature flag
        
    Returns:
        True if enabled, False otherwise
    """
    return ff(flag_name)


def get_flag_status_report() -> Dict[str, Any]:
    """
    Get detailed report of all feature flags
    
    Returns:
        Detailed status report
    """
    flags = feature_flags()
    enabled_count = sum(flags.values())
    total_count = len(flags)
    
    return {
        "total_flags": total_count,
        "enabled_flags": enabled_count,
        "disabled_flags": total_count - enabled_count,
        "flags": flags,
        "summary": {
            "auth0_disabled": not flags.get("AUTH0_ENABLED", False),
            "workflow_v2_enabled": flags.get("WORKFLOW_V2", False),
            "deep_research_available": flags.get("ENABLE_DEEP_RESEARCH", False),
            "using_stub_integrations": flags.get("USE_STUB_INTEGRATIONS", False)
        }
    }