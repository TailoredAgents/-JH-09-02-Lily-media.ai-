"""
Shared I/O utilities for JSON metadata operations.
"""
import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def load_json_dict(path: str) -> Dict[str, Any]:
    """
    Load JSON dictionary from file path.
    
    Args:
        path: File path to JSON file
        
    Returns:
        Loaded dictionary, or empty dict if file doesn't exist or has errors
    """
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading {path}: {e}. Returning empty dict.")
    return {}

def save_json_dict(path: str, data: Dict[str, Any]) -> None:
    """
    Save dictionary as JSON to file path.
    
    Args:
        path: File path to save JSON
        data: Dictionary to save
    """
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)