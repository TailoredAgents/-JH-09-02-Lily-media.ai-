"""
Connection Health Helper Module.

Provides pure helper functions for calculating connection health fields.
Extracted from partner_oauth.py to reduce complexity and improve testability.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
try:
    from backend.core.constants import TOKEN_EXPIRY_SOON_HOURS, SECONDS_PER_HOUR
except ImportError:
    # Fallback for direct module testing
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from core.constants import TOKEN_EXPIRY_SOON_HOURS, SECONDS_PER_HOUR

# Type-only import to avoid circular deps in runtime
try:
    from backend.db.models import SocialConnection  # noqa: F401
except Exception:
    pass


def _expires_info(connection) -> Dict[str, Optional[str]]:
    """Calculate expiration information for a connection."""
    now = datetime.now(timezone.utc)
    expires_at_iso = None
    expires_in_hours = None
    needs_reconnect = False

    if getattr(connection, "token_expires_at", None):
        expires_at_iso = connection.token_expires_at.isoformat()
        expires_in_hours = int((connection.token_expires_at - now).total_seconds() / SECONDS_PER_HOUR)
        
        if connection.token_expires_at <= now + timedelta(hours=TOKEN_EXPIRY_SOON_HOURS):
            needs_reconnect = True

    return {
        "expires_at": expires_at_iso,
        "expires_in_hours": expires_in_hours,
        "needs_reconnect": needs_reconnect,
    }


def _last_checked_info(connection) -> Dict[str, Optional[str]]:
    """Calculate last checked information for a connection."""
    last_checked_at_iso = None
    if getattr(connection, "updated_at", None):
        last_checked_at_iso = connection.updated_at.isoformat()
    return {"last_checked_at": last_checked_at_iso}


def compute_connection_health(connection) -> Dict[str, Any]:
    """
    Pure helper that calculates connection health fields only.
    
    Args:
        connection: SocialConnection instance
        
    Returns:
        Dictionary with health metrics including expiration and last checked info
    """
    base = {}
    base.update(_expires_info(connection))
    base.update(_last_checked_info(connection))
    base["created_at"] = getattr(connection, "created_at", None).isoformat() if getattr(connection, "created_at", None) else None
    return base