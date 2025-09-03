"""
API Versioning Configuration

Provides centralized API version management and automatic prefix injection.
All routers will automatically use the versioned prefix (/api/v1) unless explicitly configured otherwise.
"""
import os
from fastapi import APIRouter

# Current API version
API_VERSION = os.getenv("API_VERSION", "v1")

def create_versioned_router(
    prefix="",
    version=None,
    tags=None,
    legacy=False,
    **kwargs
):
    """
    Create an APIRouter with automatic versioning.
    
    Args:
        prefix: Router prefix (will be prefixed with /api/{version} automatically)
        version: API version (defaults to current API_VERSION)
        tags: Router tags
        legacy: If True, uses legacy /api prefix without versioning
        **kwargs: Additional APIRouter arguments
        
    Returns:
        APIRouter with versioned prefix
    """
    if version is None:
        version = API_VERSION
    
    if legacy:
        # Use legacy /api prefix for backward compatibility
        full_prefix = "/api{}".format(prefix) if prefix else "/api"
    else:
        # Use versioned prefix
        full_prefix = "/api/{}{}".format(version, prefix) if prefix else "/api/{}".format(version)
    
    # Clean up double slashes
    full_prefix = full_prefix.replace("//", "/").rstrip("/")
    
    return APIRouter(
        prefix=full_prefix,
        tags=tags or [],
        **kwargs
    )

def get_api_version():
    """Get the current API version."""
    return API_VERSION

def get_versioned_prefix(path="", version=None):
    """
    Get a versioned API prefix for a given path.
    
    Args:
        path: Path to append to the versioned prefix
        version: API version (defaults to current API_VERSION)
        
    Returns:
        Full versioned path
    """
    if version is None:
        version = API_VERSION
        
    if path:
        return "/api/{}/{}".format(version, path.lstrip('/'))
    return "/api/{}".format(version)