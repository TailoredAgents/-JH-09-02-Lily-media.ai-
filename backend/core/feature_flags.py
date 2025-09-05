from functools import lru_cache
import json
import os
from typing import Dict

_DEFAULT_FLAGS = {
    "USE_STUB_INTEGRATIONS": False,
    "WORKFLOW_V2": True,
    "ENABLE_DEEP_RESEARCH": False,
    "AUTH0_ENABLED": False,
    "IMAGE_GENERATION": True,
    
    # AI-Powered Features
    "AI_CONTENT_GENERATION": True,
    "AI_SUGGESTIONS": True,
    "AI_SOCIAL_RESPONSES": True,
    
    # Advanced Features
    "ADVANCED_MEMORY": True,
    "VECTOR_SEARCH": True,
    "ADVANCED_WORKFLOWS": True,
    "AUTONOMOUS_FEATURES": True,
    
    # Administrative Features
    "ADMIN_ACCESS": True,
    "ORGANIZATION_MANAGEMENT": True,
    
    # Premium Features
    "BILLING_MANAGEMENT": True,
    "ADVANCED_ANALYTICS": True,
}

def _parse_env_flags() -> Dict[str, bool]:
    """Parse feature flags from environment variable"""
    # Accept JSON or comma list: "A=1,B=0"
    raw = os.getenv("FEATURE_FLAGS", "").strip()
    if not raw:
        return {}
    try:
        return {k: bool(v) for k, v in json.loads(raw).items()}
    except Exception:
        result = {}
        for pair in raw.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                result[k.strip()] = v.strip().lower() in ("1", "true", "yes", "on")
        return result

@lru_cache
def feature_flags() -> Dict[str, bool]:
    """Get all feature flags with defaults merged"""
    merged = dict(_DEFAULT_FLAGS)
    merged.update(_parse_env_flags())
    return merged

def ff(name: str) -> bool:
    """Get feature flag value by name"""
    return bool(feature_flags().get(name, False))