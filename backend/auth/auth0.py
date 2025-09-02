"""
Auth0 integration for user authentication
"""
import json
import requests
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from jose import jwt, JWTError
from backend.core.config import get_settings

settings = get_settings()

class Auth0Verifier:
    """Auth0 JWT token verifier"""
    
    def __init__(self):
        # Auth0 settings are optional - only initialize if configured
        self.domain = getattr(settings, 'auth0_domain', None)
        self.audience = getattr(settings, 'auth0_audience', None)
        self.algorithm = "RS256"
        self._jwks = None
        
        # If Auth0 not configured, this verifier will be disabled
        self.enabled = bool(self.domain and self.audience)
    
    def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set from Auth0"""
        if not self.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth0 authentication is not configured"
            )
        
        if self._jwks is None:
            try:
                response = requests.get(f"https://{self.domain}/.well-known/jwks.json", timeout=10)
                response.raise_for_status()
                self._jwks = response.json()
            except requests.RequestException as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Unable to fetch Auth0 JWKS: {str(e)}"
                )
        return self._jwks
    
    def get_rsa_key(self, token: str) -> Optional[Dict[str, Any]]:
        """Get RSA key for token verification"""
        if not self.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth0 authentication is not configured"
            )
        
        try:
            unverified_header = jwt.get_unverified_header(token)
            jwks = self.get_jwks()
            
            for key in jwks["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    return {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"]
                    }
        except (JWTError, KeyError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Unable to parse authentication token: {str(e)}"
            )
        return None
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify Auth0 JWT token and return payload"""
        if not self.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth0 authentication is not configured"
            )
        
        rsa_key = self.get_rsa_key(token)
        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key"
            )
        
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=f"https://{self.domain}/"
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTClaimsError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims"
            )
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )

class Auth0UserManager:
    """Manage Auth0 user operations"""
    
    def __init__(self):
        # Auth0 settings are optional - only initialize if configured
        self.domain = getattr(settings, 'auth0_domain', None)
        self.client_id = getattr(settings, 'auth0_client_id', None)
        self.client_secret = getattr(settings, 'auth0_client_secret', None)
        self._management_token = None
        
        # If Auth0 not configured, this manager will be disabled
        self.enabled = bool(self.domain and self.client_id and self.client_secret)
    
    def get_management_token(self) -> str:
        """Get Auth0 Management API token"""
        if not self.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth0 management API is not configured"
            )
        
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": f"https://{self.domain}/api/v2/",
            "grant_type": "client_credentials"
        }
        
        try:
            response = requests.post(
                f"https://{self.domain}/oauth/token",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            self._management_token = response.json()["access_token"]
            return self._management_token
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to get Auth0 management token: {str(e)}"
            )
    
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information from Auth0"""
        if not self.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth0 management API is not configured"
            )
        
        token = self.get_management_token()
        
        try:
            response = requests.get(
                f"https://{self.domain}/api/v2/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {str(e)}"
            )

# Global instances
auth0_verifier = Auth0Verifier()
auth0_user_manager = Auth0UserManager()