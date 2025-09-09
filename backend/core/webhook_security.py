"""
Enhanced Webhook Security and Signature Validation
Provides cryptographically secure webhook verification for all supported platforms
"""
import hmac
import hashlib
import logging
import base64
import time
from typing import Dict, Optional, Any, Union, Tuple
from enum import Enum
from datetime import datetime, timedelta

from backend.core.config import get_settings

logger = logging.getLogger(__name__)

class WebhookPlatform(str, Enum):
    """Supported webhook platforms"""
    META = "meta"  # Facebook/Instagram via Graph API
    FACEBOOK = "facebook"  # Legacy Facebook webhooks
    INSTAGRAM = "instagram"  # Legacy Instagram webhooks
    TWITTER = "twitter"  # Twitter/X webhooks
    TWITTER_V2 = "twitter_v2"  # Twitter API v2 webhooks
    LINKEDIN = "linkedin"  # LinkedIn webhooks
    STRIPE = "stripe"  # Stripe payment webhooks
    GENERIC = "generic"  # Generic HMAC-SHA256 webhooks

class SignatureFormat(str, Enum):
    """Webhook signature formats"""
    HUB_SIGNATURE_256 = "x-hub-signature-256"  # Meta format: sha256=<hex>
    HUB_SIGNATURE_1 = "x-hub-signature"        # Facebook format: sha1=<hex>
    TWITTER_SIGNATURE = "x-twitter-webhooks-signature"  # Twitter format: sha256=<base64>
    STRIPE_SIGNATURE = "stripe-signature"      # Stripe format: t=<timestamp>,v1=<hex>
    LINKEDIN_SIGNATURE = "x-li-signature"      # LinkedIn format: <hex>
    GENERIC_HMAC = "authorization"             # Generic: HMAC-SHA256 <hex>

class WebhookSecurityError(Exception):
    """Base class for webhook security errors"""
    pass

class InvalidSignatureError(WebhookSecurityError):
    """Raised when webhook signature is invalid"""
    pass

class MissingSignatureError(WebhookSecurityError):
    """Raised when required webhook signature is missing"""
    pass

class ExpiredWebhookError(WebhookSecurityError):
    """Raised when webhook is too old (replay attack protection)"""
    pass

class WebhookSignatureValidator:
    """
    Secure webhook signature validation for multiple platforms
    
    Features:
    - Platform-specific signature verification
    - Timing attack protection using constant-time comparison
    - Replay attack protection with timestamp validation
    - Configurable tolerance and validation rules
    """
    
    # Platform-specific configuration
    PLATFORM_CONFIG = {
        WebhookPlatform.META: {
            "signature_header": "x-hub-signature-256",
            "algorithm": "sha256",
            "format": "sha256={signature}",
            "secret_env": "META_WEBHOOK_SECRET"
        },
        WebhookPlatform.FACEBOOK: {
            "signature_header": "x-hub-signature",
            "algorithm": "sha1", 
            "format": "sha1={signature}",
            "secret_env": "FACEBOOK_WEBHOOK_SECRET"
        },
        WebhookPlatform.INSTAGRAM: {
            "signature_header": "x-hub-signature",
            "algorithm": "sha1",
            "format": "sha1={signature}", 
            "secret_env": "INSTAGRAM_WEBHOOK_SECRET"
        },
        WebhookPlatform.TWITTER: {
            "signature_header": "x-twitter-webhooks-signature",
            "algorithm": "sha256",
            "format": "sha256={signature}",
            "secret_env": "TWITTER_WEBHOOK_SECRET"
        },
        WebhookPlatform.TWITTER_V2: {
            "signature_header": "x-twitter-webhooks-signature",
            "algorithm": "sha256", 
            "format": "sha256={signature}",
            "secret_env": "TWITTER_WEBHOOK_SECRET"
        },
        WebhookPlatform.LINKEDIN: {
            "signature_header": "x-li-signature",
            "algorithm": "sha256",
            "format": "{signature}",  # No prefix
            "secret_env": "LINKEDIN_WEBHOOK_SECRET"
        },
        WebhookPlatform.STRIPE: {
            "signature_header": "stripe-signature",
            "algorithm": "sha256",
            "format": "t={timestamp},v1={signature}",
            "secret_env": "STRIPE_WEBHOOK_SECRET"
        }
    }
    
    def __init__(self, settings=None):
        """
        Initialize webhook signature validator
        
        Args:
            settings: Application settings (uses get_settings() if None)
        """
        self.settings = settings or get_settings()
        self.max_timestamp_age = 300  # 5 minutes tolerance for timestamp drift
        
    def get_webhook_secret(self, platform: WebhookPlatform) -> Optional[str]:
        """
        Get webhook secret for platform from environment
        
        Args:
            platform: Webhook platform
            
        Returns:
            Webhook secret or None if not configured
        """
        config = self.PLATFORM_CONFIG.get(platform)
        if not config:
            logger.warning(f"No configuration found for platform: {platform}")
            return None
            
        secret_env = config["secret_env"]
        secret = getattr(self.settings, secret_env.lower(), None)
        
        if not secret:
            # Try alternative environment variable names
            import os
            secret = os.getenv(secret_env)
            
        return secret
    
    def verify_webhook_signature(
        self,
        platform: WebhookPlatform,
        payload: Union[str, bytes], 
        signature: str,
        headers: Optional[Dict[str, str]] = None,
        timestamp: Optional[int] = None
    ) -> bool:
        """
        Verify webhook signature for the specified platform
        
        Args:
            platform: Webhook platform
            payload: Raw webhook payload
            signature: Signature from webhook headers
            headers: Full request headers (for advanced verification)
            timestamp: Optional timestamp for replay protection
            
        Returns:
            True if signature is valid
            
        Raises:
            InvalidSignatureError: If signature is invalid
            MissingSignatureError: If signature is required but missing
            ExpiredWebhookError: If webhook is too old
        """
        try:
            # Get platform configuration
            config = self.PLATFORM_CONFIG.get(platform)
            if not config:
                logger.error(f"Unsupported webhook platform: {platform}")
                raise InvalidSignatureError(f"Unsupported platform: {platform}")
            
            # Get webhook secret
            secret = self.get_webhook_secret(platform)
            if not secret:
                logger.warning(f"No webhook secret configured for {platform}")
                # In development/test environments, we might allow unsigned webhooks
                # In production, this should be False
                allow_unsigned = getattr(self.settings, 'webhook_allow_unsigned', False)
                if allow_unsigned:
                    logger.warning(f"Allowing unsigned webhook for {platform} (development mode)")
                    return True
                raise MissingSignatureError(f"No webhook secret configured for {platform}")
            
            # Validate signature format
            if not signature or not signature.strip():
                raise MissingSignatureError("Webhook signature is empty")
            
            # Platform-specific verification
            if platform == WebhookPlatform.STRIPE:
                return self._verify_stripe_signature(payload, signature, secret, timestamp)
            elif platform in [WebhookPlatform.META, WebhookPlatform.FACEBOOK, WebhookPlatform.INSTAGRAM]:
                return self._verify_meta_signature(payload, signature, secret, config["algorithm"])
            elif platform in [WebhookPlatform.TWITTER, WebhookPlatform.TWITTER_V2]:
                return self._verify_twitter_signature(payload, signature, secret)
            elif platform == WebhookPlatform.LINKEDIN:
                return self._verify_linkedin_signature(payload, signature, secret)
            else:
                return self._verify_generic_hmac(payload, signature, secret, config["algorithm"])
                
        except WebhookSecurityError:
            # Re-raise security errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error during webhook signature verification: {e}")
            raise InvalidSignatureError(f"Signature verification failed: {e}")
    
    def _verify_meta_signature(self, payload: Union[str, bytes], signature: str, secret: str, algorithm: str) -> bool:
        """
        Verify Meta/Facebook/Instagram webhook signature
        
        Args:
            payload: Raw payload bytes
            signature: Signature header value (e.g., "sha256=abc123...")
            secret: Webhook secret
            algorithm: Hash algorithm (sha1 or sha256)
            
        Returns:
            True if signature is valid
        """
        # Ensure payload is bytes
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        # Parse signature format: "sha256=<hex_signature>"
        if not signature.startswith(f"{algorithm}="):
            logger.warning(f"Invalid Meta signature format: {signature[:20]}...")
            raise InvalidSignatureError("Invalid signature format")
        
        provided_signature = signature[len(f"{algorithm}="):]
        
        # Calculate expected signature
        hash_func = getattr(hashlib, algorithm)
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hash_func
        ).hexdigest()
        
        # Use constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(expected_signature, provided_signature)
        
        if not is_valid:
            logger.warning(f"Meta webhook signature verification failed for algorithm {algorithm}")
            
        return is_valid
    
    def _verify_twitter_signature(self, payload: Union[str, bytes], signature: str, secret: str) -> bool:
        """
        Verify Twitter webhook signature
        
        Args:
            payload: Raw payload bytes
            signature: Signature header value
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        # Ensure payload is bytes
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        # Twitter uses CRC (Challenge Response Check) for verification
        # The signature format is "sha256=<base64_signature>"
        if not signature.startswith("sha256="):
            logger.warning(f"Invalid Twitter signature format: {signature[:20]}...")
            raise InvalidSignatureError("Invalid Twitter signature format")
        
        provided_signature = signature[7:]  # Remove "sha256="
        
        # Calculate expected signature
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).digest()
        
        # Twitter uses base64 encoding
        expected_signature_b64 = base64.b64encode(expected_signature).decode('utf-8')
        
        # Use constant-time comparison
        is_valid = hmac.compare_digest(expected_signature_b64, provided_signature)
        
        if not is_valid:
            logger.warning("Twitter webhook signature verification failed")
            
        return is_valid
    
    def _verify_linkedin_signature(self, payload: Union[str, bytes], signature: str, secret: str) -> bool:
        """
        Verify LinkedIn webhook signature
        
        Args:
            payload: Raw payload bytes  
            signature: Signature header value (hex string)
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        # Ensure payload is bytes
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        # LinkedIn provides signature as raw hex string
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Use constant-time comparison
        is_valid = hmac.compare_digest(expected_signature, signature)
        
        if not is_valid:
            logger.warning("LinkedIn webhook signature verification failed")
            
        return is_valid
    
    def _verify_stripe_signature(self, payload: Union[str, bytes], signature: str, secret: str, timestamp: Optional[int] = None) -> bool:
        """
        Verify Stripe webhook signature with timestamp validation
        
        Args:
            payload: Raw payload bytes
            signature: Stripe signature header (t=timestamp,v1=signature)
            secret: Webhook secret
            timestamp: Optional timestamp override
            
        Returns:
            True if signature is valid
        """
        # Ensure payload is bytes
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        # Parse Stripe signature format: "t=1234567890,v1=abc123..."
        sig_parts = {}
        for part in signature.split(','):
            if '=' in part:
                key, value = part.split('=', 1)
                sig_parts[key] = value
        
        webhook_timestamp = sig_parts.get('t')
        webhook_signature = sig_parts.get('v1')
        
        if not webhook_timestamp or not webhook_signature:
            raise InvalidSignatureError("Missing timestamp or signature in Stripe webhook")
        
        # Validate timestamp to prevent replay attacks
        try:
            timestamp_int = int(webhook_timestamp)
        except ValueError:
            raise InvalidSignatureError("Invalid timestamp format")
        
        current_time = timestamp or int(time.time())
        if abs(current_time - timestamp_int) > self.max_timestamp_age:
            raise ExpiredWebhookError("Webhook timestamp is too old or too far in the future")
        
        # Calculate expected signature: "t={timestamp}.{payload}"
        signed_payload = f"{webhook_timestamp}.{payload.decode('utf-8')}"
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Use constant-time comparison
        is_valid = hmac.compare_digest(expected_signature, webhook_signature)
        
        if not is_valid:
            logger.warning("Stripe webhook signature verification failed")
            
        return is_valid
    
    def _verify_generic_hmac(self, payload: Union[str, bytes], signature: str, secret: str, algorithm: str) -> bool:
        """
        Verify generic HMAC signature
        
        Args:
            payload: Raw payload bytes
            signature: Signature (hex string)
            secret: Webhook secret
            algorithm: Hash algorithm (sha256, sha1, etc.)
            
        Returns:
            True if signature is valid
        """
        # Ensure payload is bytes
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        # Calculate expected signature
        hash_func = getattr(hashlib, algorithm, hashlib.sha256)
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hash_func
        ).hexdigest()
        
        # Use constant-time comparison
        is_valid = hmac.compare_digest(expected_signature, signature)
        
        if not is_valid:
            logger.warning(f"Generic HMAC webhook signature verification failed for algorithm {algorithm}")
            
        return is_valid
    
    def extract_signature_from_headers(self, platform: WebhookPlatform, headers: Dict[str, str]) -> Optional[str]:
        """
        Extract signature from request headers for the specified platform
        
        Args:
            platform: Webhook platform
            headers: HTTP request headers (case-insensitive)
            
        Returns:
            Signature string or None if not found
        """
        config = self.PLATFORM_CONFIG.get(platform)
        if not config:
            return None
        
        signature_header = config["signature_header"]
        
        # Case-insensitive header lookup
        for header_name, header_value in headers.items():
            if header_name.lower() == signature_header.lower():
                return header_value
        
        return None
    
    def validate_webhook_timing(self, timestamp: Optional[int] = None, tolerance: int = None) -> bool:
        """
        Validate webhook timestamp to prevent replay attacks
        
        Args:
            timestamp: Webhook timestamp (Unix epoch seconds)
            tolerance: Maximum age in seconds (default: 5 minutes)
            
        Returns:
            True if timestamp is within acceptable range
            
        Raises:
            ExpiredWebhookError: If webhook is too old
        """
        if timestamp is None:
            return True  # No timestamp validation
        
        max_age = tolerance or self.max_timestamp_age
        current_time = int(time.time())
        
        age = abs(current_time - timestamp)
        if age > max_age:
            raise ExpiredWebhookError(f"Webhook is {age} seconds old (max: {max_age})")
        
        return True


# Global webhook signature validator instance
webhook_validator = WebhookSignatureValidator()


def verify_webhook_signature(
    platform: str,
    payload: Union[str, bytes],
    signature: str,
    headers: Optional[Dict[str, str]] = None,
    timestamp: Optional[int] = None,
    request_info: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Convenient function to verify webhook signatures with monitoring
    
    Args:
        platform: Platform name (string)
        payload: Raw webhook payload
        signature: Signature from headers
        headers: Request headers
        timestamp: Optional timestamp
        request_info: Optional dict with ip_address, user_agent, etc. for monitoring
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    start_time = time.time()
    
    try:
        # Convert platform string to enum
        webhook_platform = WebhookPlatform(platform.lower())
        
        # Verify signature
        is_valid = webhook_validator.verify_webhook_signature(
            webhook_platform, payload, signature, headers, timestamp
        )
        
        validation_time_ms = (time.time() - start_time) * 1000
        
        # Log validation attempt for monitoring
        try:
            from backend.services.webhook_signature_monitoring import log_webhook_validation
            
            payload_size = len(payload) if payload else 0
            if isinstance(payload, str):
                payload_size = len(payload.encode('utf-8'))
            
            log_webhook_validation(
                platform=platform,
                success=is_valid,
                validation_time_ms=validation_time_ms,
                error_message=None,
                ip_address=request_info.get('ip_address') if request_info else None,
                user_agent=request_info.get('user_agent') if request_info else None,
                payload_size=payload_size,
                signature_header=signature
            )
        except Exception as monitor_error:
            logger.debug(f"Failed to log webhook validation monitoring: {monitor_error}")
        
        return is_valid, None
        
    except WebhookSecurityError as e:
        validation_time_ms = (time.time() - start_time) * 1000
        error_msg = str(e)
        
        logger.warning(f"Webhook security error for {platform}: {e}")
        
        # Log validation failure for monitoring
        try:
            from backend.services.webhook_signature_monitoring import log_webhook_validation
            
            payload_size = len(payload) if payload else 0
            if isinstance(payload, str):
                payload_size = len(payload.encode('utf-8'))
            
            log_webhook_validation(
                platform=platform,
                success=False,
                validation_time_ms=validation_time_ms,
                error_message=error_msg,
                ip_address=request_info.get('ip_address') if request_info else None,
                user_agent=request_info.get('user_agent') if request_info else None,
                payload_size=payload_size,
                signature_header=signature
            )
        except Exception as monitor_error:
            logger.debug(f"Failed to log webhook validation monitoring: {monitor_error}")
        
        return False, error_msg
    except Exception as e:
        validation_time_ms = (time.time() - start_time) * 1000
        error_msg = f"Verification failed: {e}"
        
        logger.error(f"Unexpected error verifying webhook signature for {platform}: {e}")
        
        # Log validation error for monitoring
        try:
            from backend.services.webhook_signature_monitoring import log_webhook_validation
            
            payload_size = len(payload) if payload else 0
            if isinstance(payload, str):
                payload_size = len(payload.encode('utf-8'))
            
            log_webhook_validation(
                platform=platform,
                success=False,
                validation_time_ms=validation_time_ms,
                error_message=error_msg,
                ip_address=request_info.get('ip_address') if request_info else None,
                user_agent=request_info.get('user_agent') if request_info else None,
                payload_size=payload_size,
                signature_header=signature
            )
        except Exception as monitor_error:
            logger.debug(f"Failed to log webhook validation monitoring: {monitor_error}")
        
        return False, error_msg


def extract_webhook_signature(platform: str, headers: Dict[str, str]) -> Optional[str]:
    """
    Extract webhook signature from headers
    
    Args:
        platform: Platform name
        headers: Request headers
        
    Returns:
        Signature string or None
    """
    try:
        webhook_platform = WebhookPlatform(platform.lower())
        return webhook_validator.extract_signature_from_headers(webhook_platform, headers)
    except Exception as e:
        logger.error(f"Error extracting signature for {platform}: {e}")
        return None