"""
JWT Authentication configuration validator
"""
from typing import Dict, List, Any
from backend.core.config import get_settings

class AuthConfigValidator:
    """Validate local JWT authentication configuration"""
    
    def __init__(self):
        self.settings = get_settings()
    
    def validate_jwt_config(self) -> Dict[str, Any]:
        """Validate JWT configuration"""
        config_status = {
            "secret_key": bool(self.settings.secret_key and self.settings.secret_key != "your-secret-key-change-this"),
            "algorithm": self.settings.algorithm == "HS256",
            "token_expire_minutes": self.settings.access_token_expire_minutes > 0,
        }
        
        config_status["jwt_enabled"] = all(config_status.values())
        
        return config_status
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Get overall JWT authentication status"""
        jwt_status = self.validate_jwt_config()
        
        return {
            "jwt": jwt_status,
            "enabled": jwt_status.get("jwt_enabled", False),
            "recommendations": self._get_recommendations(jwt_status)
        }
    
    def _get_recommendations(self, jwt_status: Dict) -> List[str]:
        """Get JWT configuration recommendations"""
        recommendations = []
        
        if not jwt_status["secret_key"]:
            recommendations.append("Set a secure SECRET_KEY in environment variables")
        
        if not jwt_status["jwt_enabled"]:
            recommendations.append("Critical: JWT authentication is not properly configured")
            
        return recommendations

# Global instance
auth_config_validator = AuthConfigValidator()