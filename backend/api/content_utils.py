"""
Shared utilities for content API operations.
"""
from typing import Optional, Dict, Any

def build_user_settings_dict(user_settings) -> Dict[str, Any]:
    """
    Build normalized user settings dictionary from UserSetting model.
    
    Args:
        user_settings: UserSetting model instance or None
        
    Returns:
        Dictionary with user settings, or empty dict if no settings
    """
    if not user_settings:
        return {}
    
    return {
        "industry_type": user_settings.industry_type,
        "visual_style": user_settings.visual_style,
        "primary_color": user_settings.primary_color,
        "secondary_color": user_settings.secondary_color,
        "image_mood": user_settings.image_mood or ["professional", "clean"],
        "brand_keywords": user_settings.brand_keywords or [],
        "avoid_list": user_settings.avoid_list or [],
        "preferred_image_style": user_settings.preferred_image_style or {},
        "image_quality": user_settings.image_quality or "high",
    }