"""
Webhook Reliability API Endpoints

Provides endpoints for monitoring webhook reliability, idempotency tracking,
and delivery status. Used for production monitoring and debugging.

Addresses P0-11c: Implement webhook reliability improvements
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from backend.services.webhook_reliability_service import get_webhook_reliability_service
from backend.auth.admin_auth import get_current_admin_user
from backend.db.models import User
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook-reliability", tags=["webhook-reliability"])
settings = get_settings()


@router.get("/status")
async def get_webhook_reliability_status(
    admin_user: User = Depends(get_current_admin_user)
) -> JSONResponse:
    """
    Get comprehensive webhook reliability status and statistics
    
    Returns:
        Webhook reliability metrics and health information
    """
    try:
        reliability_service = get_webhook_reliability_service()
        stats = reliability_service.get_webhook_reliability_stats()
        
        return JSONResponse(
            status_code=200,
            content={
                "webhook_reliability_status": stats,
                "service": "webhook_reliability_api",
                "version": "1.0"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get webhook reliability status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve webhook reliability status: {str(e)}"
        )


@router.get("/idempotency/stats")
async def get_idempotency_statistics(
    admin_user: User = Depends(get_current_admin_user),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    hours: int = Query(24, description="Time window in hours")
) -> JSONResponse:
    """
    Get idempotency effectiveness statistics
    
    Args:
        admin_user: Authenticated admin user
        platform: Optional platform filter
        hours: Time window for statistics (default 24 hours)
        
    Returns:
        Idempotency tracking statistics
    """
    try:
        reliability_service = get_webhook_reliability_service()
        
        # Get comprehensive stats (includes idempotency info)
        all_stats = reliability_service.get_webhook_reliability_stats()
        idempotency_stats = all_stats.get('idempotency_statistics', {})
        
        # Add platform filter info if requested
        filter_info = {}
        if platform:
            filter_info['platform_filter'] = platform
        
        filter_info['time_window_hours'] = hours
        
        return JSONResponse(
            status_code=200,
            content={
                "idempotency_statistics": idempotency_stats,
                "filter_info": filter_info,
                "timestamp": all_stats.get('timestamp')
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get idempotency statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve idempotency statistics: {str(e)}"
        )


@router.get("/delivery/stats")
async def get_delivery_statistics(
    admin_user: User = Depends(get_current_admin_user),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    status: Optional[str] = Query(None, description="Filter by delivery status")
) -> JSONResponse:
    """
    Get webhook delivery statistics
    
    Args:
        admin_user: Authenticated admin user
        platform: Optional platform filter
        status: Optional delivery status filter
        
    Returns:
        Webhook delivery statistics
    """
    try:
        reliability_service = get_webhook_reliability_service()
        
        # Get comprehensive stats
        all_stats = reliability_service.get_webhook_reliability_stats()
        delivery_stats = all_stats.get('delivery_statistics', {})
        
        # Add filter info
        filter_info = {}
        if platform:
            filter_info['platform_filter'] = platform
        if status:
            filter_info['status_filter'] = status
        
        return JSONResponse(
            status_code=200,
            content={
                "delivery_statistics": delivery_stats,
                "filter_info": filter_info,
                "timestamp": all_stats.get('timestamp')
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get delivery statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve delivery statistics: {str(e)}"
        )


@router.post("/recovery/trigger")
async def trigger_webhook_recovery(
    admin_user: User = Depends(get_current_admin_user),
    limit: int = Query(50, description="Maximum webhooks to process")
) -> JSONResponse:
    """
    Manually trigger webhook recovery process
    
    Args:
        admin_user: Authenticated admin user
        limit: Maximum number of failed webhooks to process
        
    Returns:
        Recovery process results
    """
    try:
        reliability_service = get_webhook_reliability_service()
        
        # Process failed webhooks for recovery
        recovery_results = await reliability_service.process_failed_webhooks_recovery(limit=limit)
        
        return JSONResponse(
            status_code=200,
            content={
                "recovery_triggered": True,
                "recovery_results": recovery_results,
                "triggered_by": admin_user.email,
                "limit": limit
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger webhook recovery: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger webhook recovery: {str(e)}"
        )


@router.post("/cleanup/trigger")
async def trigger_webhook_cleanup(
    admin_user: User = Depends(get_current_admin_user),
    batch_size: int = Query(1000, description="Number of records to process")
) -> JSONResponse:
    """
    Manually trigger webhook cleanup process
    
    Args:
        admin_user: Authenticated admin user
        batch_size: Number of records to process per batch
        
    Returns:
        Cleanup process results
    """
    try:
        reliability_service = get_webhook_reliability_service()
        
        # Clean up expired records
        cleanup_results = await reliability_service.cleanup_expired_records(batch_size=batch_size)
        
        return JSONResponse(
            status_code=200,
            content={
                "cleanup_triggered": True,
                "cleanup_results": cleanup_results,
                "triggered_by": admin_user.email,
                "batch_size": batch_size
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger webhook cleanup: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger webhook cleanup: {str(e)}"
        )


@router.get("/health")
async def webhook_reliability_health_check() -> JSONResponse:
    """
    Health check endpoint for webhook reliability service
    
    Returns:
        Service health status
    """
    try:
        reliability_service = get_webhook_reliability_service()
        
        # Get basic health info
        health_info = {
            "service": "webhook_reliability",
            "status": "healthy",
            "features": {
                "idempotency_tracking": True,
                "delivery_monitoring": True,
                "automatic_recovery": True,
                "dlq_integration": True
            },
            "version": "1.0"
        }
        
        # Try to get basic stats to ensure service is working
        try:
            stats = reliability_service.get_webhook_reliability_stats()
            health_info["last_stats_check"] = stats.get('timestamp')
            health_info["service_operational"] = True
        except Exception as stats_error:
            logger.warning(f"Webhook reliability stats check failed: {stats_error}")
            health_info["service_operational"] = False
            health_info["stats_error"] = str(stats_error)
            health_info["status"] = "degraded"
        
        status_code = 200 if health_info["service_operational"] else 503
        
        return JSONResponse(
            status_code=status_code,
            content=health_info
        )
        
    except Exception as e:
        logger.error(f"Webhook reliability health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "service": "webhook_reliability",
                "status": "unhealthy",
                "error": str(e),
                "version": "1.0"
            }
        )