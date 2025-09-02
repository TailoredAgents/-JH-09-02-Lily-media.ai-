"""
Shared authentication validators and utilities.
"""
from typing import Optional

def normalize_and_validate_backup_code(v: Optional[str]) -> Optional[str]:
    """
    Normalize and validate 2FA backup codes.
    
    Accepts formats like:
    - "ABCD-1234"
    - "ABCD1234"
    - "abcd 1234"
    
    Args:
        v: Raw backup code input
        
    Returns:
        Normalized backup code (8 uppercase alphanumeric chars)
        
    Raises:
        ValueError: If backup code format is invalid
    """
    if v is None:
        return v
    
    # Normalize: remove spaces/hyphens and convert to uppercase
    v = v.replace(" ", "").replace("-", "").upper()
    
    # Validate: must be exactly 8 alphanumeric characters
    if len(v) != 8 or not all(c.isalnum() for c in v):
        raise ValueError("Invalid backup code format")
    
    return v