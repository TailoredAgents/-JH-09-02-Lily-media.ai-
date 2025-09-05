"""
Monitoring and metrics API endpoints
Provides Prometheus metrics endpoint and monitoring system status
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from backend.auth.dependencies import get_current_admin_user, AuthUser
from backend.core.monitoring import monitoring_service
from backend.core.api_version import create_versioned_router

logger = logging.getLogger(__name__)
router = create_versioned_router(prefix="/monitoring", tags=["monitoring"])

# Response models
class MonitoringHealthResponse(BaseModel):
    """Monitoring system health response"""
    monitoring: Dict[str, Any]
    timestamp: str
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class SystemMetricsResponse(BaseModel):
    """System metrics summary response"""
    requests_total: int
    errors_total: int
    active_users: int
    uptime_seconds: float
    database_connections: int
    cache_hit_rate: float
    timestamp: str
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

@router.get("/health", response_model=MonitoringHealthResponse)
async def get_monitoring_health():
    """
    Get monitoring system health status
    
    Public endpoint for health checks
    """
    try:
        health_status = monitoring_service.get_health_status()
        
        return MonitoringHealthResponse(
            monitoring=health_status["monitoring"],
            timestamp=health_status["timestamp"]
        )
        
    except Exception as e:
        logger.error(f"Error getting monitoring health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve monitoring health status"
        )

@router.get("/metrics")
async def get_prometheus_metrics():
    """
    Get Prometheus metrics endpoint
    
    Returns metrics in Prometheus exposition format
    """
    try:
        metrics_content = monitoring_service.get_prometheus_metrics()
        
        # Return in Prometheus format
        return Response(
            content=metrics_content,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Error getting Prometheus metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )

@router.get("/system", response_model=SystemMetricsResponse)
async def get_system_metrics(
    current_user: AuthUser = Depends(get_current_admin_user)
):
    """
    Get system metrics summary
    
    Requires admin access for security
    """
    try:
        # Get metrics from monitoring service
        health_status = monitoring_service.get_health_status()
        
        # Calculate derived metrics
        uptime = health_status["monitoring"]["uptime_seconds"]
        
        return SystemMetricsResponse(
            requests_total=0,  # Will be populated from Prometheus metrics
            errors_total=0,    # Will be populated from Prometheus metrics
            active_users=0,    # Will be populated from database
            uptime_seconds=uptime,
            database_connections=0,  # Will be populated from connection pool
            cache_hit_rate=0.0,      # Will be populated from cache stats
            timestamp=health_status["timestamp"]
        )
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system metrics"
        )

@router.post("/test-error")
async def test_error_tracking(
    current_user: AuthUser = Depends(get_current_admin_user)
):
    """
    Test error tracking integration
    
    Requires admin access for security
    """
    try:
        # Simulate an error for testing
        test_exception = Exception("Test error for monitoring integration")
        
        monitoring_service.record_error(
            test_exception,
            context={
                "test": True,
                "user_id": current_user.user_id,
                "action": "test_error_tracking"
            }
        )
        
        return {
            "message": "Test error recorded successfully",
            "monitoring_available": {
                "prometheus": monitoring_service.prometheus.__class__.__name__,
                "sentry": monitoring_service.sentry.initialized
            }
        }
        
    except Exception as e:
        logger.error(f"Error in test error tracking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test error tracking"
        )

@router.get("/status")
async def get_monitoring_status():
    """
    Get detailed monitoring system status
    
    Public endpoint for service discovery
    """
    try:
        from backend.core.monitoring import PROMETHEUS_AVAILABLE, SENTRY_AVAILABLE
        
        return {
            "monitoring_systems": {
                "prometheus": {
                    "available": PROMETHEUS_AVAILABLE,
                    "endpoint": "/api/monitoring/metrics"
                },
                "sentry": {
                    "available": SENTRY_AVAILABLE,
                    "initialized": monitoring_service.sentry.initialized
                }
            },
            "endpoints": [
                "/api/monitoring/health",
                "/api/monitoring/metrics", 
                "/api/monitoring/system",
                "/api/monitoring/status"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        return {
            "error": "Failed to retrieve monitoring status",
            "timestamp": datetime.utcnow().isoformat()
        }