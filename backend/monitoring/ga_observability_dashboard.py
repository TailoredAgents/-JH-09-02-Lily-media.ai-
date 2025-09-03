"""
GA Checklist Observability Dashboard
Required monitoring for production readiness

Dashboards: queue depth, publish success/fail, throttled count, 
circuit-breaker state, token refresh outcomes
Alerts: repeated 429/5xx, failed refresh, webhook verification failures
"""
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from backend.db.database import get_db
from backend.db.models import SocialConnection, SocialAudit
from backend.auth.dependencies import get_current_user
from backend.core.config import get_settings
from backend.services.redis_cache import redis_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/observability", tags=["observability"])


@dataclass
class QueueDepthMetrics:
    """Queue depth metrics for Celery monitoring"""
    total_pending: int = 0
    publishing_queue: int = 0
    webhook_queue: int = 0
    token_health_queue: int = 0
    x_polling_queue: int = 0
    research_queue: int = 0
    failed_tasks: int = 0
    retry_queue: int = 0
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class PublishMetrics:
    """Publishing success/failure metrics"""
    successful_publishes: int = 0
    failed_publishes: int = 0
    total_attempts: int = 0
    success_rate: float = 0.0
    average_response_time: float = 0.0
    platform_breakdown: Dict[str, Any] = None
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.total_attempts > 0:
            self.success_rate = (self.successful_publishes / self.total_attempts) * 100
        if not self.platform_breakdown:
            self.platform_breakdown = {}


@dataclass
class ThrottleMetrics:
    """Rate limiting and throttling metrics"""
    throttled_requests: int = 0
    rate_limited_organizations: List[str] = None
    platform_limits_hit: Dict[str, int] = None
    average_wait_time: float = 0.0
    circuit_breaker_trips: int = 0
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.rate_limited_organizations:
            self.rate_limited_organizations = []
        if not self.platform_limits_hit:
            self.platform_limits_hit = {}


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker state metrics"""
    total_breakers: int = 0
    closed_state: int = 0
    open_state: int = 0
    half_open_state: int = 0
    recent_trips: int = 0
    recovery_attempts: int = 0
    platform_states: Dict[str, str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.platform_states:
            self.platform_states = {}


@dataclass
class TokenHealthMetrics:
    """Token refresh and health metrics"""
    total_tokens: int = 0
    healthy_tokens: int = 0
    expired_tokens: int = 0
    refresh_failures: int = 0
    successful_refreshes: int = 0
    tokens_near_expiry: int = 0
    platform_health: Dict[str, Dict[str, int]] = None
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.platform_health:
            self.platform_health = {}


class GAObservabilityService:
    """Service for GA checklist observability requirements"""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
    
    async def get_queue_depth_metrics(self) -> QueueDepthMetrics:
        """
        Get Celery queue depth metrics
        
        Returns:
            QueueDepthMetrics with current queue states
        """
        try:
            # Try to get metrics from Redis/Celery
            metrics = QueueDepthMetrics()
            
            # In a real implementation, you would query Celery/Redis for actual queue depths
            # For now, we'll use Redis keys to estimate queue activity
            
            if hasattr(redis_cache, 'redis_client') and redis_cache.redis_client:
                try:
                    # Look for queue-related keys in Redis
                    queue_keys = await redis_cache.redis_client.keys("celery:*")
                    
                    # Estimate queue depths based on Redis keys
                    publishing_keys = [k for k in queue_keys if b'posting' in k or b'publish' in k]
                    webhook_keys = [k for k in queue_keys if b'webhook' in k]
                    token_keys = [k for k in queue_keys if b'token' in k]
                    
                    metrics.publishing_queue = len(publishing_keys)
                    metrics.webhook_queue = len(webhook_keys) 
                    metrics.token_health_queue = len(token_keys)
                    metrics.total_pending = len(queue_keys)
                    
                except Exception as e:
                    logger.warning(f"Failed to get Redis queue metrics: {e}")
            
            # Fallback to audit log analysis for queue activity estimation
            recent_time = datetime.now(timezone.utc) - timedelta(minutes=15)
            
            # Count recent publishing attempts
            recent_publishes = self.db.query(func.count(SocialAudit.id)).filter(
                and_(
                    SocialAudit.action.in_(['publish_content', 'schedule_content']),
                    SocialAudit.created_at >= recent_time
                )
            ).scalar() or 0
            
            # Count recent failures (proxy for retry queue)
            recent_failures = self.db.query(func.count(SocialAudit.id)).filter(
                and_(
                    SocialAudit.status == 'failure',
                    SocialAudit.created_at >= recent_time
                )
            ).scalar() or 0
            
            metrics.failed_tasks = recent_failures
            metrics.retry_queue = min(recent_failures, 10)  # Estimate retry queue
            
            logger.info(f"Queue depth metrics: {asdict(metrics)}")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get queue depth metrics: {e}")
            return QueueDepthMetrics()  # Return empty metrics on error
    
    def get_publish_metrics(self, hours_back: int = 24) -> PublishMetrics:
        """
        Get publishing success/failure metrics
        
        Args:
            hours_back: How many hours back to analyze
            
        Returns:
            PublishMetrics with success/failure data
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            
            # Query publishing attempts from audit logs
            publish_audits = self.db.query(SocialAudit).filter(
                and_(
                    SocialAudit.action.in_([
                        'publish_content', 'schedule_content', 'connection_publish'
                    ]),
                    SocialAudit.created_at >= cutoff_time
                )
            ).all()
            
            metrics = PublishMetrics()
            platform_stats = {}
            response_times = []
            
            for audit in publish_audits:
                metrics.total_attempts += 1
                
                # Track per-platform stats
                platform = audit.platform or 'unknown'
                if platform not in platform_stats:
                    platform_stats[platform] = {'success': 0, 'failure': 0}
                
                if audit.status == 'success':
                    metrics.successful_publishes += 1
                    platform_stats[platform]['success'] += 1
                else:
                    metrics.failed_publishes += 1
                    platform_stats[platform]['failure'] += 1
                
                # Extract response time from metadata if available
                if audit.audit_metadata and 'response_time' in audit.audit_metadata:
                    response_times.append(audit.audit_metadata['response_time'])
            
            metrics.platform_breakdown = platform_stats
            
            if response_times:
                metrics.average_response_time = sum(response_times) / len(response_times)
            
            logger.info(f"Publish metrics ({hours_back}h): {asdict(metrics)}")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get publish metrics: {e}")
            return PublishMetrics()
    
    async def get_throttle_metrics(self, hours_back: int = 24) -> ThrottleMetrics:
        """
        Get rate limiting and throttling metrics
        
        Args:
            hours_back: How many hours back to analyze
            
        Returns:
            ThrottleMetrics with throttling data
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            
            # Query rate limiting events from audit logs
            throttle_audits = self.db.query(SocialAudit).filter(
                and_(
                    or_(
                        SocialAudit.status == 'rate_limited',
                        SocialAudit.audit_metadata.op('->>')('error').like('%rate%limit%'),
                        SocialAudit.audit_metadata.op('->>')('error').like('%429%'),
                        SocialAudit.audit_metadata.op('->>')('status_code') == '429'
                    ),
                    SocialAudit.created_at >= cutoff_time
                )
            ).all()
            
            metrics = ThrottleMetrics()
            platform_limits = {}
            wait_times = []
            rate_limited_orgs = set()
            
            for audit in throttle_audits:
                metrics.throttled_requests += 1
                
                # Track organizations that hit rate limits
                if audit.organization_id:
                    rate_limited_orgs.add(str(audit.organization_id))
                
                # Track per-platform rate limiting
                platform = audit.platform or 'unknown'
                platform_limits[platform] = platform_limits.get(platform, 0) + 1
                
                # Extract wait time if available
                if audit.audit_metadata and 'retry_after' in audit.audit_metadata:
                    try:
                        wait_time = float(audit.audit_metadata['retry_after'])
                        wait_times.append(wait_time)
                    except (ValueError, TypeError):
                        pass
            
            metrics.rate_limited_organizations = list(rate_limited_orgs)
            metrics.platform_limits_hit = platform_limits
            
            if wait_times:
                metrics.average_wait_time = sum(wait_times) / len(wait_times)
            
            # Check for circuit breaker trips
            circuit_breaker_audits = self.db.query(func.count(SocialAudit.id)).filter(
                and_(
                    SocialAudit.action == 'circuit_breaker_trip',
                    SocialAudit.created_at >= cutoff_time
                )
            ).scalar() or 0
            
            metrics.circuit_breaker_trips = circuit_breaker_audits
            
            logger.info(f"Throttle metrics ({hours_back}h): {asdict(metrics)}")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get throttle metrics: {e}")
            return ThrottleMetrics()
    
    async def get_circuit_breaker_metrics(self) -> CircuitBreakerMetrics:
        """
        Get circuit breaker state metrics
        
        Returns:
            CircuitBreakerMetrics with current circuit breaker states
        """
        try:
            metrics = CircuitBreakerMetrics()
            
            # Get active connections to check circuit breaker states
            active_connections = self.db.query(SocialConnection).filter(
                SocialConnection.is_active == True
            ).all()
            
            platform_states = {}
            
            for connection in active_connections:
                platform = connection.platform
                
                # Initialize platform tracking
                if platform not in platform_states:
                    platform_states[platform] = {
                        'closed': 0, 'open': 0, 'half_open': 0
                    }
                
                # Check connection health to infer circuit breaker state
                if connection.last_health_check:
                    time_since_check = datetime.now(timezone.utc) - connection.last_health_check
                    
                    if connection.health_status == 'healthy':
                        # Healthy connection = closed circuit breaker
                        platform_states[platform]['closed'] += 1
                        metrics.closed_state += 1
                    elif connection.health_status == 'unhealthy':
                        # Unhealthy connection = open circuit breaker
                        platform_states[platform]['open'] += 1
                        metrics.open_state += 1
                    elif connection.health_status == 'recovering':
                        # Recovering connection = half-open circuit breaker
                        platform_states[platform]['half_open'] += 1
                        metrics.half_open_state += 1
                else:
                    # No health check = assume closed (default state)
                    platform_states[platform]['closed'] += 1
                    metrics.closed_state += 1
                
                metrics.total_breakers += 1
            
            metrics.platform_states = {
                platform: max(states.items(), key=lambda x: x[1])[0]  # Most common state
                for platform, states in platform_states.items()
            }
            
            # Count recent circuit breaker trips
            recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_trips = self.db.query(func.count(SocialAudit.id)).filter(
                and_(
                    SocialAudit.action == 'circuit_breaker_trip',
                    SocialAudit.created_at >= recent_time
                )
            ).scalar() or 0
            
            metrics.recent_trips = recent_trips
            
            logger.info(f"Circuit breaker metrics: {asdict(metrics)}")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get circuit breaker metrics: {e}")
            return CircuitBreakerMetrics()
    
    def get_token_health_metrics(self) -> TokenHealthMetrics:
        """
        Get token refresh and health metrics
        
        Returns:
            TokenHealthMetrics with token health data
        """
        try:
            metrics = TokenHealthMetrics()
            platform_health = {}
            
            # Get all active connections
            all_connections = self.db.query(SocialConnection).all()
            
            for connection in all_connections:
                platform = connection.platform
                
                if platform not in platform_health:
                    platform_health[platform] = {
                        'total': 0, 'healthy': 0, 'expired': 0, 'near_expiry': 0
                    }
                
                platform_health[platform]['total'] += 1
                metrics.total_tokens += 1
                
                if connection.is_active:
                    if connection.token_expires_at:
                        now = datetime.now(timezone.utc)
                        expires_at = connection.token_expires_at
                        
                        if expires_at < now:
                            # Token is expired
                            platform_health[platform]['expired'] += 1
                            metrics.expired_tokens += 1
                        elif expires_at < now + timedelta(days=7):
                            # Token expires within 7 days
                            platform_health[platform]['near_expiry'] += 1
                            metrics.tokens_near_expiry += 1
                            platform_health[platform]['healthy'] += 1
                            metrics.healthy_tokens += 1
                        else:
                            # Token is healthy
                            platform_health[platform]['healthy'] += 1
                            metrics.healthy_tokens += 1
                    else:
                        # No expiry info = assume healthy
                        platform_health[platform]['healthy'] += 1
                        metrics.healthy_tokens += 1
            
            metrics.platform_health = platform_health
            
            # Count recent token refresh attempts
            recent_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            refresh_audits = self.db.query(SocialAudit).filter(
                and_(
                    SocialAudit.action.in_(['token_refresh', 'token_validation']),
                    SocialAudit.created_at >= recent_time
                )
            ).all()
            
            for audit in refresh_audits:
                if audit.status == 'success':
                    metrics.successful_refreshes += 1
                else:
                    metrics.refresh_failures += 1
            
            logger.info(f"Token health metrics: {asdict(metrics)}")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get token health metrics: {e}")
            return TokenHealthMetrics()


@router.get("/dashboard/queue-depth")
async def get_queue_depth_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> JSONResponse:
    """
    GA Checklist: Queue depth dashboard
    
    Returns current Celery queue depth metrics
    """
    try:
        service = GAObservabilityService(db)
        metrics = await service.get_queue_depth_metrics()
        
        return JSONResponse(content={
            "dashboard": "queue_depth",
            "metrics": asdict(metrics),
            "alerts": []  # Add alerts if queues are too deep
        })
        
    except Exception as e:
        logger.error(f"Queue depth dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get queue depth metrics")


@router.get("/dashboard/publish-success-fail")
async def get_publish_success_fail_dashboard(
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> JSONResponse:
    """
    GA Checklist: Publish success/fail dashboard
    
    Returns publishing success and failure metrics
    """
    try:
        service = GAObservabilityService(db)
        metrics = service.get_publish_metrics(hours)
        
        alerts = []
        if metrics.success_rate < 90:  # Alert if success rate below 90%
            alerts.append({
                "severity": "warning",
                "message": f"Publishing success rate is {metrics.success_rate:.1f}%",
                "threshold": 90
            })
        
        return JSONResponse(content={
            "dashboard": "publish_success_fail",
            "time_window_hours": hours,
            "metrics": asdict(metrics),
            "alerts": alerts
        })
        
    except Exception as e:
        logger.error(f"Publish success/fail dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get publish metrics")


@router.get("/dashboard/throttled-count")
async def get_throttled_count_dashboard(
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> JSONResponse:
    """
    GA Checklist: Throttled count dashboard
    
    Returns rate limiting and throttling metrics
    """
    try:
        service = GAObservabilityService(db)
        metrics = await service.get_throttle_metrics(hours)
        
        alerts = []
        if metrics.throttled_requests > 100:  # Alert for high throttling
            alerts.append({
                "severity": "warning",
                "message": f"{metrics.throttled_requests} requests throttled in {hours}h",
                "threshold": 100
            })
        
        return JSONResponse(content={
            "dashboard": "throttled_count",
            "time_window_hours": hours,
            "metrics": asdict(metrics),
            "alerts": alerts
        })
        
    except Exception as e:
        logger.error(f"Throttled count dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get throttling metrics")


@router.get("/dashboard/circuit-breaker-state")
async def get_circuit_breaker_state_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> JSONResponse:
    """
    GA Checklist: Circuit breaker state dashboard
    
    Returns current circuit breaker states
    """
    try:
        service = GAObservabilityService(db)
        metrics = await service.get_circuit_breaker_metrics()
        
        alerts = []
        if metrics.open_state > 0:
            alerts.append({
                "severity": "critical",
                "message": f"{metrics.open_state} circuit breakers are OPEN",
                "platforms": [p for p, s in metrics.platform_states.items() if s == 'open']
            })
        
        return JSONResponse(content={
            "dashboard": "circuit_breaker_state",
            "metrics": asdict(metrics),
            "alerts": alerts
        })
        
    except Exception as e:
        logger.error(f"Circuit breaker state dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get circuit breaker metrics")


@router.get("/dashboard/token-refresh-outcomes")
async def get_token_refresh_outcomes_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> JSONResponse:
    """
    GA Checklist: Token refresh outcomes dashboard
    
    Returns token health and refresh metrics
    """
    try:
        service = GAObservabilityService(db)
        metrics = service.get_token_health_metrics()
        
        alerts = []
        if metrics.expired_tokens > 0:
            alerts.append({
                "severity": "warning",
                "message": f"{metrics.expired_tokens} tokens have expired",
                "action": "Refresh tokens immediately"
            })
        
        if metrics.tokens_near_expiry > 0:
            alerts.append({
                "severity": "info", 
                "message": f"{metrics.tokens_near_expiry} tokens expire within 7 days",
                "action": "Schedule token refresh"
            })
        
        return JSONResponse(content={
            "dashboard": "token_refresh_outcomes",
            "metrics": asdict(metrics),
            "alerts": alerts
        })
        
    except Exception as e:
        logger.error(f"Token refresh outcomes dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get token health metrics")


@router.get("/dashboard/unified")
async def get_unified_ga_dashboard(
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> JSONResponse:
    """
    Unified GA checklist dashboard with all required metrics
    
    Returns all GA checklist observability metrics in one response
    """
    try:
        service = GAObservabilityService(db)
        
        # Collect all metrics
        dashboard_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "time_window_hours": hours,
            "queue_depth": asdict(await service.get_queue_depth_metrics()),
            "publish_metrics": asdict(service.get_publish_metrics(hours)),
            "throttle_metrics": asdict(await service.get_throttle_metrics(hours)),
            "circuit_breaker": asdict(await service.get_circuit_breaker_metrics()),
            "token_health": asdict(service.get_token_health_metrics())
        }
        
        # Collect all alerts
        all_alerts = []
        
        # Add critical alerts for immediate attention
        if dashboard_data["circuit_breaker"]["open_state"] > 0:
            all_alerts.append({
                "severity": "critical",
                "category": "circuit_breaker",
                "message": f"{dashboard_data['circuit_breaker']['open_state']} circuit breakers are OPEN"
            })
        
        if dashboard_data["token_health"]["expired_tokens"] > 0:
            all_alerts.append({
                "severity": "warning",
                "category": "token_health",
                "message": f"{dashboard_data['token_health']['expired_tokens']} tokens have expired"
            })
        
        if dashboard_data["publish_metrics"]["success_rate"] < 90:
            all_alerts.append({
                "severity": "warning",
                "category": "publish_success",
                "message": f"Publishing success rate is {dashboard_data['publish_metrics']['success_rate']:.1f}%"
            })
        
        dashboard_data["alerts"] = all_alerts
        dashboard_data["overall_health"] = "healthy" if len(all_alerts) == 0 else "degraded"
        
        return JSONResponse(content=dashboard_data)
        
    except Exception as e:
        logger.error(f"Unified GA dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate unified dashboard")