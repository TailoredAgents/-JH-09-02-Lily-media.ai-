"""
Production Webhook Endpoints

Handles incoming webhooks from social media platforms:
- Facebook Graph API webhooks
- Instagram Graph API webhooks  
- X/Twitter Account Activity API webhooks
- Meta (Partner OAuth) webhooks for Pages and Instagram Business accounts

All endpoints include proper security validation and signature verification.
"""

import logging
import os
import hmac
import hashlib
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User, SocialPlatformConnection
from backend.services.facebook_webhook_handler import FacebookWebhookHandler, InstagramWebhookHandler
from backend.services.twitter_webhook_handler import TwitterWebhookHandler, TwitterV2WebhookHandler
from backend.services.social_webhook_service import get_webhook_service
from backend.core.config import get_settings

# Import Meta webhook service for partner OAuth
try:
    from backend.services.meta_webhook_service import get_meta_webhook_service, MetaWebhookService
except ImportError:
    # Service will be created in next step
    get_meta_webhook_service = None
    MetaWebhookService = None

# Import webhook reliability service for enhanced processing
try:
    from backend.services.webhook_reliability_service import get_webhook_reliability_service
except ImportError:
    get_webhook_reliability_service = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Initialize webhook handlers
FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET')
INSTAGRAM_APP_SECRET = os.getenv('INSTAGRAM_APP_SECRET', FACEBOOK_APP_SECRET)  # Often same as Facebook
TWITTER_CONSUMER_SECRET = os.getenv('TWITTER_CONSUMER_SECRET')

facebook_handler = FacebookWebhookHandler(FACEBOOK_APP_SECRET) if FACEBOOK_APP_SECRET else None
instagram_handler = InstagramWebhookHandler(INSTAGRAM_APP_SECRET) if INSTAGRAM_APP_SECRET else None
twitter_handler = TwitterWebhookHandler(TWITTER_CONSUMER_SECRET) if TWITTER_CONSUMER_SECRET else None
twitter_v2_handler = TwitterV2WebhookHandler(TWITTER_CONSUMER_SECRET) if TWITTER_CONSUMER_SECRET else None


def is_partner_oauth_enabled(settings=None) -> bool:
    """Check if partner OAuth feature is enabled"""
    if settings is None:
        settings = get_settings()
    
    return getattr(settings, 'feature_partner_oauth', False)


# =============================================================================
# META (PARTNER OAUTH) WEBHOOK ENDPOINTS
# =============================================================================

@router.get("/meta", response_class=PlainTextResponse)
async def verify_meta_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    settings = Depends(get_settings)
) -> str:
    """
    Meta webhook verification endpoint
    
    Meta calls this endpoint during webhook setup to verify ownership.
    We verify the token and return the challenge if valid.
    
    Args:
        hub_mode: Should be "subscribe" for verification
        hub_verify_token: Token to verify against our configured token
        hub_challenge: Challenge string to return if verification passes
        settings: Application settings
        
    Returns:
        hub_challenge if verification passes, otherwise 403 error
    """
    try:
        # Don't log query parameters to avoid exposing tokens
        logger.info(f"Meta webhook verification attempt: mode={hub_mode}")
        
        # Check if feature is enabled
        if not is_partner_oauth_enabled(settings):
            logger.warning("Meta webhook verification attempted but feature disabled")
            raise HTTPException(
                status_code=404,
                detail={"error": "feature_disabled", "message": "Partner OAuth feature is disabled"}
            )
        
        # Validate required parameters
        if not hub_mode or not hub_verify_token or not hub_challenge:
            logger.warning("Meta webhook verification missing required parameters")
            raise HTTPException(status_code=400, detail="Missing required parameters")
        
        # Check if this is a subscription verification
        if hub_mode != "subscribe":
            logger.warning(f"Meta webhook verification invalid mode: {hub_mode}")
            raise HTTPException(status_code=400, detail="Invalid hub mode")
        
        # Get our configured verify token
        expected_token = getattr(settings, 'meta_verify_token', '')
        if not expected_token:
            logger.error("META_VERIFY_TOKEN not configured")
            raise HTTPException(status_code=500, detail="Webhook verification not configured")
        
        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(hub_verify_token, expected_token):
            logger.warning("Meta webhook verification token mismatch")
            raise HTTPException(status_code=403, detail="Invalid verify token")
        
        # Verification successful - return challenge
        logger.info("Meta webhook verification successful")
        return hub_challenge
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Meta webhook verification error: {e}")
        raise HTTPException(status_code=500, detail="Verification failed")


@router.post("/meta")
async def handle_meta_webhook(
    request: Request,
    settings = Depends(get_settings)
) -> JSONResponse:
    """
    Meta webhook events endpoint
    
    Receives webhook events from Meta (Facebook/Instagram Graph API).
    Verifies HMAC signature and enqueues processing to Celery.
    
    Args:
        request: FastAPI request object with raw body
        settings: Application settings
        
    Returns:
        200 OK immediately after validation and enqueueing
    """
    try:
        # Check if feature is enabled
        if not is_partner_oauth_enabled(settings):
            logger.warning("Meta webhook event received but feature disabled")
            return JSONResponse(
                status_code=404,
                content={"error": "feature_disabled", "message": "Partner OAuth feature is disabled"}
            )
        
        # Check if webhook service is available
        if not get_meta_webhook_service:
            logger.error("Meta webhook service not available")
            return JSONResponse(status_code=200, content={"status": "service_unavailable"})
        
        webhook_service = get_meta_webhook_service()
        
        # Get raw body for HMAC verification
        raw_body = await request.body()
        
        # Get signature from headers
        signature = request.headers.get("X-Hub-Signature-256")
        if not signature:
            logger.warning("Meta webhook missing X-Hub-Signature-256 header")
            raise HTTPException(status_code=403, detail="Missing signature")
        
        # Verify HMAC signature
        if not await webhook_service.verify_signature(raw_body, signature):
            logger.warning("Meta webhook signature verification failed")
            raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Parse JSON payload (after signature verification)
        try:
            import json
            payload = json.loads(raw_body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Meta webhook invalid JSON payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Quick validation of payload structure
        if not isinstance(payload, dict) or 'object' not in payload:
            logger.warning("Meta webhook payload missing required fields")
            raise HTTPException(status_code=400, detail="Invalid payload structure")
        
        # Extract minimal event info for logging (no sensitive data)
        event_info = {
            "object": payload.get("object"),
            "entry_count": len(payload.get("entry", [])),
            "received_at": None  # Will be set by processing task
        }
        
        # Log event receipt (no raw payload or tokens)
        logger.info(f"Meta webhook event received: {event_info}")
        
        # Enqueue processing to Celery
        await webhook_service.enqueue_event_processing(payload, event_info)
        
        # Return 200 OK immediately
        logger.info("Meta webhook event enqueued successfully")
        return JSONResponse(status_code=200, content={"status": "received"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Meta webhook processing error: {e}")
        # Still return 200 to avoid Meta retries for our internal errors
        # Log the error for monitoring but don't expose details
        return JSONResponse(status_code=200, content={"status": "error"})


# =============================================================================
# EXISTING WEBHOOK ENDPOINTS
# =============================================================================

@router.get("/facebook")
async def facebook_webhook_verification(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token")
):
    """Facebook webhook verification endpoint"""
    
    expected_token = os.getenv('FACEBOOK_WEBHOOK_VERIFY_TOKEN')
    if not expected_token:
        raise HTTPException(status_code=500, detail="Webhook verify token not configured")
    
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("Facebook webhook verified successfully")
        return PlainTextResponse(hub_challenge)
    else:
        logger.warning(f"Facebook webhook verification failed: mode={hub_mode}, token_match={hub_verify_token == expected_token}")
        raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/facebook/{user_id}")
async def facebook_webhook_handler(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Facebook webhook event handler"""
    
    if not facebook_handler:
        raise HTTPException(status_code=500, detail="Facebook webhook handler not configured")
    
    # Get signature from headers
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature header")
    
    # Read request body
    payload = await request.body()
    
    # Verify user exists and has Facebook connection
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    facebook_connection = db.query(SocialPlatformConnection).filter(
        SocialPlatformConnection.user_id == user_id,
        SocialPlatformConnection.platform == "facebook",
        SocialPlatformConnection.is_active == True
    ).first()
    
    if not facebook_connection:
        logger.warning(f"Facebook webhook received for user {user_id} without active connection")
        raise HTTPException(status_code=404, detail="No active Facebook connection")
    
    # Set webhook service for the handler
    facebook_handler.webhook_service = get_webhook_service()
    
    # Process webhook
    try:
        result = await facebook_handler.process_webhook(payload, signature, user_id)
        logger.info(f"Processed Facebook webhook for user {user_id}: {result['processed_events']} events")
        return result
    except Exception as e:
        logger.error(f"Error processing Facebook webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.get("/instagram")
async def instagram_webhook_verification(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token")
):
    """Instagram webhook verification endpoint"""
    
    expected_token = os.getenv('INSTAGRAM_WEBHOOK_VERIFY_TOKEN', os.getenv('FACEBOOK_WEBHOOK_VERIFY_TOKEN'))
    if not expected_token:
        raise HTTPException(status_code=500, detail="Webhook verify token not configured")
    
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("Instagram webhook verified successfully")
        return PlainTextResponse(hub_challenge)
    else:
        logger.warning(f"Instagram webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/instagram/{user_id}")
async def instagram_webhook_handler(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Instagram webhook event handler"""
    
    if not instagram_handler:
        raise HTTPException(status_code=500, detail="Instagram webhook handler not configured")
    
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature header")
    
    payload = await request.body()
    
    # Verify user and Instagram connection
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    instagram_connection = db.query(SocialPlatformConnection).filter(
        SocialPlatformConnection.user_id == user_id,
        SocialPlatformConnection.platform == "instagram",
        SocialPlatformConnection.is_active == True
    ).first()
    
    if not instagram_connection:
        raise HTTPException(status_code=404, detail="No active Instagram connection")
    
    # Set webhook service for the handler
    instagram_handler.webhook_service = get_webhook_service()
    
    try:
        result = await instagram_handler.process_webhook(payload, signature, user_id)
        logger.info(f"Processed Instagram webhook for user {user_id}: {result['processed_events']} events")
        return result
    except Exception as e:
        logger.error(f"Error processing Instagram webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.get("/twitter/crc")
async def twitter_webhook_crc(
    crc_token: str = Query(...),
    user_id: int = Query(...)
):
    """Twitter webhook CRC (Challenge Response Check) endpoint"""
    
    if not twitter_handler:
        raise HTTPException(status_code=500, detail="Twitter webhook handler not configured")
    
    try:
        response_token = twitter_handler.create_crc_response(crc_token)
        logger.info(f"Twitter CRC check successful for user {user_id}")
        return {"response_token": f"sha256={response_token}"}
    except Exception as e:
        logger.error(f"Twitter CRC check failed: {e}")
        raise HTTPException(status_code=500, detail="CRC check failed")

@router.post("/twitter/{user_id}")
async def twitter_webhook_handler(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Twitter Account Activity API webhook handler"""
    
    if not twitter_handler:
        raise HTTPException(status_code=500, detail="Twitter webhook handler not configured")
    
    signature = request.headers.get('X-Twitter-Webhooks-Signature')
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature header")
    
    payload = await request.body()
    
    # Verify signature first using enhanced security
    try:
        is_valid, error_msg = verify_webhook_signature(
            platform="twitter",
            payload=payload,
            signature=signature,
            headers=dict(request.headers)
        )
        
        if not is_valid:
            logger.warning(f"Twitter webhook signature verification failed: {error_msg}")
            raise HTTPException(status_code=403, detail="Invalid signature")
            
    except (InvalidSignatureError, MissingSignatureError) as e:
        logger.warning(f"Twitter webhook signature error: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except ExpiredWebhookError as e:
        logger.warning(f"Twitter webhook expired: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    # Verify user and Twitter connection
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    twitter_connection = db.query(SocialPlatformConnection).filter(
        SocialPlatformConnection.user_id == user_id,
        SocialPlatformConnection.platform == "twitter",
        SocialPlatformConnection.is_active == True
    ).first()
    
    if not twitter_connection:
        raise HTTPException(status_code=404, detail="No active Twitter connection")
    
    # Set webhook service for the handler
    twitter_handler.webhook_service = get_webhook_service()
    
    try:
        result = await twitter_handler.process_webhook(payload, signature, user_id)
        logger.info(f"Processed Twitter webhook for user {user_id}: {result['processed_events']} events")
        return result
    except Exception as e:
        logger.error(f"Error processing Twitter webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.post("/twitter/v2/{user_id}")
async def twitter_v2_webhook_handler(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Twitter API v2 webhook handler"""
    
    if not twitter_v2_handler:
        raise HTTPException(status_code=500, detail="Twitter v2 webhook handler not configured")
    
    signature = request.headers.get('X-Twitter-Webhooks-Signature')
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature header")
    
    payload = await request.body()
    
    # Verify signature first using enhanced security
    try:
        is_valid, error_msg = verify_webhook_signature(
            platform="twitter_v2",
            payload=payload,
            signature=signature,
            headers=dict(request.headers)
        )
        
        if not is_valid:
            logger.warning(f"Twitter v2 webhook signature verification failed: {error_msg}")
            raise HTTPException(status_code=403, detail="Invalid signature")
            
    except (InvalidSignatureError, MissingSignatureError) as e:
        logger.warning(f"Twitter v2 webhook signature error: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except ExpiredWebhookError as e:
        logger.warning(f"Twitter v2 webhook expired: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    # Verify user and Twitter connection
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    twitter_connection = db.query(SocialPlatformConnection).filter(
        SocialPlatformConnection.user_id == user_id,
        SocialPlatformConnection.platform == "twitter",
        SocialPlatformConnection.is_active == True
    ).first()
    
    if not twitter_connection:
        raise HTTPException(status_code=404, detail="No active Twitter connection")
    
    # Set webhook service for the handler
    twitter_v2_handler.webhook_service = get_webhook_service()
    
    try:
        result = await twitter_v2_handler.process_webhook(payload, signature, user_id)
        logger.info(f"Processed Twitter v2 webhook for user {user_id}: {result['processed_events']} events")
        return result
    except Exception as e:
        logger.error(f"Error processing Twitter v2 webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.get("/status")
async def webhook_status():
    """Get comprehensive webhook configuration and reliability status"""
    
    # Basic platform configuration
    platform_status = {
        "facebook": {
            "configured": facebook_handler is not None,
            "app_secret_set": bool(FACEBOOK_APP_SECRET),
            "verify_token_set": bool(os.getenv('FACEBOOK_WEBHOOK_VERIFY_TOKEN'))
        },
        "instagram": {
            "configured": instagram_handler is not None,
            "app_secret_set": bool(INSTAGRAM_APP_SECRET),
            "verify_token_set": bool(os.getenv('INSTAGRAM_WEBHOOK_VERIFY_TOKEN', os.getenv('FACEBOOK_WEBHOOK_VERIFY_TOKEN')))
        },
        "twitter": {
            "configured": twitter_handler is not None,
            "consumer_secret_set": bool(TWITTER_CONSUMER_SECRET),
            "v2_handler": twitter_v2_handler is not None
        },
        "meta": {
            "configured": get_meta_webhook_service is not None,
            "partner_oauth_enabled": is_partner_oauth_enabled(),
            "verify_token_set": bool(getattr(get_settings(), 'meta_verify_token', None))
        }
    }
    
    # Webhook endpoints
    endpoints = {
        "facebook_verify": "/webhooks/facebook",
        "facebook_handler": "/webhooks/facebook/{user_id}",
        "instagram_verify": "/webhooks/instagram", 
        "instagram_handler": "/webhooks/instagram/{user_id}",
        "twitter_crc": "/webhooks/twitter/crc",
        "twitter_handler": "/webhooks/twitter/{user_id}",
        "twitter_v2_handler": "/webhooks/twitter/v2/{user_id}",
        "meta_verify": "/webhooks/meta",
        "meta_handler": "/webhooks/meta"
    }
    
    # Webhook reliability status
    reliability_status = {
        "service_available": get_webhook_reliability_service is not None,
        "features": {
            "idempotency_tracking": False,
            "delivery_monitoring": False,
            "automatic_recovery": False,
            "dlq_integration": True
        }
    }
    
    # Get reliability statistics if service is available
    if get_webhook_reliability_service:
        try:
            reliability_service = get_webhook_reliability_service()
            reliability_stats = reliability_service.get_webhook_reliability_stats()
            
            reliability_status["features"] = {
                "idempotency_tracking": True,
                "delivery_monitoring": True,
                "automatic_recovery": True,
                "dlq_integration": True
            }
            reliability_status["statistics"] = {
                "recent_deliveries_24h": reliability_stats.get('delivery_statistics', {}).get('recent_deliveries_24h', 0),
                "success_rate_24h_percent": reliability_stats.get('delivery_statistics', {}).get('success_rate_24h_percent', 0),
                "pending_retries": reliability_stats.get('delivery_statistics', {}).get('pending_retries', 0),
                "duplicates_prevented_24h": reliability_stats.get('idempotency_statistics', {}).get('duplicates_prevented_24h', 0)
            }
            reliability_status["last_updated"] = reliability_stats.get('timestamp')
            
        except Exception as e:
            logger.warning(f"Failed to get webhook reliability stats: {e}")
            reliability_status["error"] = "Failed to retrieve reliability statistics"
    
    return {
        "platforms": platform_status,
        "endpoints": endpoints,
        "reliability": reliability_status,
        "service_info": {
            "version": "1.0",
            "enhanced_reliability": get_webhook_reliability_service is not None,
            "dlq_enabled": True,
            "partner_oauth_support": get_meta_webhook_service is not None
        }
    }