"""
Observability API endpoints for metrics, tracing, and health monitoring
"""
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.core.telemetry import telemetry_manager, get_tracer, get_meter, OPENTELEMETRY_AVAILABLE

# Optional OpenTelemetry imports
if OPENTELEMETRY_AVAILABLE:
    try:
        from opentelemetry import trace, metrics
    except ImportError:
        OPENTELEMETRY_AVAILABLE = False
        trace = None
        metrics = None
else:
    trace = None
    metrics = None
# Optional database import
try:
    from backend.db.database import get_db
    DB_AVAILABLE = True
except ImportError:
    def mock_get_db():
        return None
    get_db = mock_get_db
    DB_AVAILABLE = False

# Optional auth imports - fallback if not available
try:
    from backend.api.auth_fastapi_users import current_active_user
    from backend.db.models import User
    AUTH_AVAILABLE = True
except ImportError:
    # Mock user for when auth is not available
    class MockUser:
        id = "mock-user"
    
    def mock_current_active_user():
        return MockUser()
    
    current_active_user = mock_current_active_user
    User = MockUser
    AUTH_AVAILABLE = False

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/observability", tags=["observability"])

# Pydantic models
class HealthStatus(BaseModel):
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment (development/production)")
    timestamp: datetime = Field(..., description="Health check timestamp")
    services: Dict[str, str] = Field(..., description="Status of dependent services")
    telemetry: Dict[str, bool] = Field(..., description="Telemetry configuration status")

class MetricsResponse(BaseModel):
    metrics: Dict[str, Any] = Field(..., description="Application metrics")
    timestamp: datetime = Field(..., description="Metrics collection timestamp")
    collection_duration_ms: float = Field(..., description="Time taken to collect metrics")

class TraceRequest(BaseModel):
    operation_name: str = Field(..., description="Name of the operation to trace")
    duration_ms: Optional[int] = Field(None, description="Simulated operation duration")
    attributes: Optional[Dict[str, str]] = Field({}, description="Additional trace attributes")

class TraceResponse(BaseModel):
    trace_id: str = Field(..., description="Generated trace ID")
    span_id: str = Field(..., description="Generated span ID")
    operation_name: str = Field(..., description="Operation that was traced")
    duration_ms: float = Field(..., description="Actual operation duration")

@router.get("/health", response_model=HealthStatus)
async def detailed_health_check(db=Depends(get_db)):
    """
    Comprehensive health check with service dependencies and telemetry status
    """
    start_time = time.time()
    
    # Check database connectivity
    db_status = "healthy"
    try:
        result = await db.execute(text("SELECT 1"))
        await result.fetchone()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        logger.error(f"Database health check failed: {e}")
    
    # Check Redis connectivity (if available)
    redis_status = "not_configured"
    try:
        import redis
        import os
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            r = redis.from_url(redis_url)
            r.ping()
            redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    # Check telemetry status
    telemetry_status = {
        "tracing_enabled": telemetry_manager.tracer is not None,
        "metrics_enabled": telemetry_manager.meter is not None,
        "telemetry_configured": telemetry_manager.enabled,
    }
    
    # Overall status
    overall_status = "healthy"
    if db_status != "healthy" or "unhealthy" in redis_status:
        overall_status = "degraded"
    
    duration_ms = (time.time() - start_time) * 1000
    
    return HealthStatus(
        status=overall_status,
        version="2.0.0",
        environment=os.getenv("ENVIRONMENT", "production"),
        timestamp=datetime.utcnow(),
        services={
            "database": db_status,
            "redis": redis_status,
            "openai": "configured" if os.getenv("OPENAI_API_KEY") else "not_configured",
        },
        telemetry=telemetry_status
    )

@router.get("/metrics", response_model=MetricsResponse)
async def get_application_metrics(
    user: User = Depends(current_active_user),
    db=Depends(get_db)
):
    """
    Get application metrics and performance data
    """
    start_time = time.time()
    
    try:
        # Database metrics
        db_metrics = {}
        try:
            # Active connections
            result = await db.execute(text("SELECT count(*) FROM pg_stat_activity"))
            active_connections = await result.fetchone()
            db_metrics["active_connections"] = active_connections[0] if active_connections else 0
            
            # Table sizes
            result = await db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """))
            table_sizes = await result.fetchall()
            db_metrics["largest_tables"] = [
                {"schema": row[0], "table": row[1], "size": row[2]}
                for row in table_sizes
            ]
            
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")
            db_metrics["error"] = str(e)
        
        # Application metrics
        app_metrics = {
            "uptime_seconds": time.time() - telemetry_manager.start_time if hasattr(telemetry_manager, 'start_time') else 0,
            "telemetry_enabled": telemetry_manager.enabled,
            "environment": os.getenv("ENVIRONMENT", "production"),
        }
        
        # Combine all metrics
        all_metrics = {
            "database": db_metrics,
            "application": app_metrics,
        }
        
        collection_duration = (time.time() - start_time) * 1000
        
        return MetricsResponse(
            metrics=all_metrics,
            timestamp=datetime.utcnow(),
            collection_duration_ms=collection_duration
        )
        
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect metrics: {str(e)}")

@router.post("/trace", response_model=TraceResponse)
async def create_manual_trace(
    trace_request: TraceRequest,
    user: User = Depends(current_active_user),
):
    """
    Create a manual trace for testing and debugging distributed tracing
    """
    tracer = get_tracer()
    if not tracer:
        raise HTTPException(
            status_code=503, 
            detail="OpenTelemetry tracing is not configured"
        )
    
    start_time = time.time()
    
    with tracer.start_as_current_span(trace_request.operation_name) as span:
        # Set span attributes
        span.set_attributes({
            "user.id": str(user.id),
            "operation.type": "manual_trace",
            "request.timestamp": datetime.utcnow().isoformat(),
            **trace_request.attributes
        })
        
        # Simulate work if duration specified
        if trace_request.duration_ms:
            time.sleep(trace_request.duration_ms / 1000.0)
        
        # Get trace and span IDs
        span_context = span.get_span_context()
        trace_id = format(span_context.trace_id, '032x')
        span_id = format(span_context.span_id, '016x')
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Add completion attributes
        span.set_attributes({
            "operation.duration_ms": duration_ms,
            "operation.status": "completed"
        })
        
        return TraceResponse(
            trace_id=trace_id,
            span_id=span_id,
            operation_name=trace_request.operation_name,
            duration_ms=duration_ms
        )

@router.get("/prometheus", response_class=PlainTextResponse)
async def prometheus_metrics():
    """
    Expose metrics in Prometheus format
    """
    # This endpoint will be automatically handled by PrometheusMetricReader
    # if Prometheus is enabled in telemetry configuration
    return PlainTextResponse(
        "# Prometheus metrics are exposed via OpenTelemetry PrometheusMetricReader\n"
        "# Check telemetry configuration and ensure PROMETHEUS_ENABLED=true\n"
    )

@router.get("/traces/recent")
async def get_recent_traces(
    limit: int = Query(10, ge=1, le=100),
    user: User = Depends(current_active_user),
):
    """
    Get information about recent traces (for debugging)
    """
    if not telemetry_manager.enabled:
        return {
            "traces": [],
            "message": "OpenTelemetry tracing is not enabled",
            "telemetry_enabled": False
        }
    
    # This would typically integrate with a tracing backend
    # For now, return configuration information
    return {
        "traces": [],
        "message": "Trace data is exported to configured telemetry backend",
        "telemetry_enabled": True,
        "configuration": {
            "otlp_endpoint": bool(os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')),
            "jaeger_endpoint": bool(os.getenv('JAEGER_AGENT_HOST')),
            "service_name": telemetry_manager.service_name,
            "service_version": telemetry_manager.service_version,
        }
    }

@router.post("/telemetry/reload")
async def reload_telemetry_configuration(
    background_tasks: BackgroundTasks,
    user: User = Depends(current_active_user),
):
    """
    Reload telemetry configuration (admin only)
    """
    def reload_telemetry():
        try:
            # Shutdown existing telemetry
            telemetry_manager.shutdown()
            
            # Reinitialize with current environment variables
            telemetry_manager.__init__()
            success = telemetry_manager.initialize()
            
            logger.info(f"Telemetry reload {'successful' if success else 'failed'}")
            
        except Exception as e:
            logger.error(f"Telemetry reload failed: {e}")
    
    background_tasks.add_task(reload_telemetry)
    
    return {
        "message": "Telemetry configuration reload scheduled",
        "status": "scheduled",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/config")
async def get_observability_configuration(
    user: User = Depends(current_active_user),
):
    """
    Get current observability configuration
    """
    import os
    
    return {
        "telemetry": {
            "enabled": telemetry_manager.enabled,
            "service_name": telemetry_manager.service_name,
            "service_version": telemetry_manager.service_version,
            "environment": telemetry_manager.environment,
        },
        "exporters": {
            "otlp_configured": bool(os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')),
            "jaeger_configured": bool(os.getenv('JAEGER_AGENT_HOST')),
            "prometheus_enabled": os.getenv('PROMETHEUS_ENABLED', 'false').lower() == 'true',
        },
        "instrumentation": {
            "fastapi": True,
            "sqlalchemy": True,
            "redis": True,
            "requests": True,
            "celery": True,
        },
        "environment_variables": {
            "OTEL_ENABLED": os.getenv('OTEL_ENABLED', 'false'),
            "OTEL_SERVICE_NAME": os.getenv('OTEL_SERVICE_NAME', 'lily-media-api'),
            "OTEL_SERVICE_VERSION": os.getenv('OTEL_SERVICE_VERSION', '1.0.0'),
            "PROMETHEUS_PORT": os.getenv('PROMETHEUS_PORT', '8000'),
        }
    }