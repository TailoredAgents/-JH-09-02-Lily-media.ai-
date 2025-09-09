"""
P1-4b: OAuth Token Refresh Monitoring
Comprehensive monitoring for OAuth token refresh operations with metrics and alerting
"""
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

from backend.core.structured_logging import structured_logger_service, LogLevel
from backend.core.monitoring import monitoring_service
from backend.db.models import SocialConnection, SocialPlatformConnection
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

logger = logging.getLogger(__name__)

class TokenStatus(Enum):
    """OAuth token status states"""
    HEALTHY = "healthy"
    EXPIRING_SOON = "expiring_soon"  # < 24 hours
    EXPIRED = "expired"
    REFRESH_FAILED = "refresh_failed"
    MISSING = "missing"

class RefreshStatus(Enum):
    """Token refresh operation status"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    IN_PROGRESS = "in_progress"

@dataclass
class TokenHealthMetrics:
    """OAuth token health metrics"""
    platform: str
    total_tokens: int = 0
    healthy_tokens: int = 0
    expiring_soon_tokens: int = 0
    expired_tokens: int = 0
    failed_tokens: int = 0
    missing_tokens: int = 0
    last_refresh_success_rate: float = 0.0
    avg_token_age_hours: float = 0.0
    
    def get_health_score(self) -> float:
        """Calculate health score (0-100)"""
        if self.total_tokens == 0:
            return 100.0
        
        health_weight = 0.5
        expiring_weight = 0.3
        expired_weight = -0.8
        failed_weight = -0.6
        
        score = (
            (self.healthy_tokens * health_weight) +
            (self.expiring_soon_tokens * expiring_weight) +
            (self.expired_tokens * expired_weight) +
            (self.failed_tokens * failed_weight)
        ) / self.total_tokens * 100
        
        return max(0.0, min(100.0, score))

@dataclass
class RefreshOperationMetrics:
    """Token refresh operation metrics"""
    operation_id: str
    platform: str
    connection_id: int
    organization_id: int
    start_time: float
    end_time: Optional[float] = None
    status: RefreshStatus = RefreshStatus.IN_PROGRESS
    duration_ms: Optional[float] = None
    old_expiry: Optional[str] = None
    new_expiry: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0

class OAuthTokenMonitor:
    """
    Comprehensive OAuth token monitoring service
    P1-4b Implementation: Advanced token refresh monitoring with alerting
    """
    
    def __init__(self):
        self.refresh_metrics: Dict[str, RefreshOperationMetrics] = {}
        self.health_thresholds = {
            "expiring_soon_hours": 24,
            "critical_health_score": 30.0,
            "warning_health_score": 60.0,
            "max_failed_refresh_rate": 0.20  # 20% failure rate
        }
    
    async def get_token_health_metrics(self, db: Session, platform: Optional[str] = None) -> Dict[str, TokenHealthMetrics]:
        """
        Get comprehensive token health metrics across platforms
        
        Args:
            db: Database session
            platform: Specific platform to check (None for all)
            
        Returns:
            Dictionary of platform -> TokenHealthMetrics
        """
        try:
            platforms_to_check = [platform] if platform else ["meta", "x", "linkedin", "tiktok"]
            metrics = {}
            
            for plat in platforms_to_check:
                metrics[plat] = await self._calculate_platform_health(db, plat)
            
            # Log health metrics
            for platform_name, health_metrics in metrics.items():
                self._log_token_health(platform_name, health_metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get token health metrics: {e}")
            structured_logger_service.log_integration_event(
                platform="oauth_monitoring",
                event_type="metrics_collection_failed",
                message=f"Token health metrics collection failed: {str(e)}",
                level=LogLevel.ERROR,
                metadata={"error": str(e)}
            )
            return {}
    
    async def _calculate_platform_health(self, db: Session, platform: str) -> TokenHealthMetrics:
        """Calculate health metrics for a specific platform"""
        try:
            now = datetime.now(timezone.utc)
            expiring_threshold = now + timedelta(hours=self.health_thresholds["expiring_soon_hours"])
            
            # Query all connections for this platform
            connections = db.query(SocialConnection).filter(
                SocialConnection.platform == platform,
                SocialConnection.is_active == True
            ).all()
            
            # Query SocialPlatformConnection tokens if available
            platform_connections = []
            try:
                platform_connections = db.query(SocialPlatformConnection).filter(
                    SocialPlatformConnection.platform == platform,
                    SocialPlatformConnection.is_active == True
                ).all()
            except Exception:
                # SocialPlatformConnection table might not exist in all deployments
                pass
            
            metrics = TokenHealthMetrics(platform=platform)
            metrics.total_tokens = len(connections) + len(platform_connections)
            
            # Analyze SocialConnection tokens
            for conn in connections:
                if conn.token_expires_at:
                    if conn.token_expires_at <= now:
                        metrics.expired_tokens += 1
                    elif conn.token_expires_at <= expiring_threshold:
                        metrics.expiring_soon_tokens += 1
                    else:
                        metrics.healthy_tokens += 1
                else:
                    # No expiry usually means long-lived token
                    metrics.healthy_tokens += 1
            
            # Analyze SocialPlatformConnection entries
            for token in platform_connections:
                if token.token_expires_at:
                    if token.token_expires_at <= now:
                        metrics.expired_tokens += 1
                    elif token.token_expires_at <= expiring_threshold:
                        metrics.expiring_soon_tokens += 1
                    else:
                        metrics.healthy_tokens += 1
                else:
                    metrics.healthy_tokens += 1
            
            # Calculate success rate from recent refresh operations
            recent_refreshes = await self._get_recent_refresh_operations(db, platform, hours=24)
            if recent_refreshes:
                successful = sum(1 for op in recent_refreshes if op["status"] == "success")
                metrics.last_refresh_success_rate = successful / len(recent_refreshes)
            
            # Calculate average token age
            token_ages = []
            for conn in connections:
                if conn.created_at:
                    age_hours = (now - conn.created_at).total_seconds() / 3600
                    token_ages.append(age_hours)
            
            if token_ages:
                metrics.avg_token_age_hours = sum(token_ages) / len(token_ages)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate health for platform {platform}: {e}")
            return TokenHealthMetrics(platform=platform)
    
    async def start_refresh_monitoring(
        self,
        platform: str,
        connection_id: int,
        organization_id: int,
        old_expiry: Optional[datetime] = None
    ) -> str:
        """
        Start monitoring a token refresh operation
        
        Returns:
            operation_id for tracking
        """
        operation_id = f"{platform}_{connection_id}_{int(time.time() * 1000)}"
        
        metrics = RefreshOperationMetrics(
            operation_id=operation_id,
            platform=platform,
            connection_id=connection_id,
            organization_id=organization_id,
            start_time=time.time(),
            status=RefreshStatus.IN_PROGRESS,
            old_expiry=old_expiry.isoformat() if old_expiry else None
        )
        
        self.refresh_metrics[operation_id] = metrics
        
        # Log refresh start
        structured_logger_service.log_integration_event(
            platform=platform,
            event_type="token_refresh_started",
            message=f"OAuth token refresh started for {platform} connection {connection_id}",
            level=LogLevel.INFO,
            organization_id=str(organization_id),
            metadata={
                "operation_id": operation_id,
                "connection_id": connection_id,
                "old_expiry": metrics.old_expiry
            }
        )
        
        return operation_id
    
    async def complete_refresh_monitoring(
        self,
        operation_id: str,
        success: bool,
        new_expiry: Optional[datetime] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0
    ):
        """Complete monitoring of a token refresh operation"""
        if operation_id not in self.refresh_metrics:
            logger.warning(f"Unknown refresh operation ID: {operation_id}")
            return
        
        metrics = self.refresh_metrics[operation_id]
        metrics.end_time = time.time()
        metrics.duration_ms = (metrics.end_time - metrics.start_time) * 1000
        metrics.status = RefreshStatus.SUCCESS if success else RefreshStatus.FAILED
        metrics.new_expiry = new_expiry.isoformat() if new_expiry else None
        metrics.error_message = error_message
        metrics.retry_count = retry_count
        
        # Determine log level based on outcome
        if success:
            level = LogLevel.INFO
            message = f"OAuth token refresh succeeded for {metrics.platform} connection {metrics.connection_id}"
        else:
            level = LogLevel.ERROR
            message = f"OAuth token refresh failed for {metrics.platform} connection {metrics.connection_id}: {error_message}"
        
        # Log completion
        structured_logger_service.log_integration_event(
            platform=metrics.platform,
            event_type="token_refresh_completed",
            message=message,
            level=level,
            organization_id=str(metrics.organization_id),
            duration_ms=metrics.duration_ms,
            metadata=asdict(metrics)
        )
        
        # Send to Prometheus metrics
        try:
            monitoring_service.record_oauth_refresh(
                platform=metrics.platform,
                success=success,
                duration_seconds=metrics.duration_ms / 1000 if metrics.duration_ms else 0,
                organization_id=str(metrics.organization_id)
            )
        except Exception as e:
            logger.debug(f"Failed to record Prometheus metrics: {e}")
        
        # Check for alerting conditions
        await self._check_refresh_alerts(metrics)
        
        # Clean up completed operation after some time
        # Keep in memory for debugging for a while
        del self.refresh_metrics[operation_id]
    
    def _log_token_health(self, platform: str, metrics: TokenHealthMetrics):
        """Log structured token health metrics"""
        health_score = metrics.get_health_score()
        
        # Determine log level based on health score
        if health_score < self.health_thresholds["critical_health_score"]:
            level = LogLevel.CRITICAL
        elif health_score < self.health_thresholds["warning_health_score"]:
            level = LogLevel.WARNING
        else:
            level = LogLevel.INFO
        
        structured_logger_service.log_integration_event(
            platform=platform,
            event_type="token_health_check",
            message=f"{platform} token health score: {health_score:.1f}/100",
            level=level,
            metadata={
                "health_score": health_score,
                "total_tokens": metrics.total_tokens,
                "healthy_tokens": metrics.healthy_tokens,
                "expiring_soon_tokens": metrics.expiring_soon_tokens,
                "expired_tokens": metrics.expired_tokens,
                "failed_tokens": metrics.failed_tokens,
                "refresh_success_rate": metrics.last_refresh_success_rate,
                "avg_token_age_hours": metrics.avg_token_age_hours
            }
        )
    
    async def _check_refresh_alerts(self, metrics: RefreshOperationMetrics):
        """Check if refresh operation should trigger alerts"""
        try:
            # Alert on failures
            if metrics.status == RefreshStatus.FAILED:
                structured_logger_service.log_security_event(
                    event_type="oauth_token_refresh_failure",
                    message=f"OAuth token refresh failed for {metrics.platform} (connection {metrics.connection_id})",
                    level=LogLevel.ERROR,
                    organization_id=str(metrics.organization_id),
                    metadata={
                        "platform": metrics.platform,
                        "connection_id": metrics.connection_id,
                        "error": metrics.error_message,
                        "retry_count": metrics.retry_count,
                        "duration_ms": metrics.duration_ms
                    }
                )
            
            # Alert on slow refresh operations (> 30 seconds)
            if metrics.duration_ms and metrics.duration_ms > 30000:
                structured_logger_service.log_performance_event(
                    operation="oauth_token_refresh",
                    duration_ms=metrics.duration_ms,
                    message=f"Slow OAuth token refresh for {metrics.platform} ({metrics.duration_ms:.0f}ms)",
                    level=LogLevel.WARNING,
                    metadata={
                        "platform": metrics.platform,
                        "connection_id": metrics.connection_id,
                        "organization_id": metrics.organization_id
                    }
                )
            
        except Exception as e:
            logger.error(f"Failed to check refresh alerts: {e}")
    
    async def _get_recent_refresh_operations(self, db: Session, platform: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent refresh operations from audit logs"""
        try:
            from backend.db.models import SocialAudit
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            audits = db.query(SocialAudit).filter(
                and_(
                    SocialAudit.platform == platform,
                    SocialAudit.action == "refresh",
                    SocialAudit.created_at >= cutoff_time
                )
            ).all()
            
            return [
                {
                    "status": audit.status,
                    "created_at": audit.created_at.isoformat(),
                    "connection_id": audit.connection_id,
                    "organization_id": audit.organization_id
                }
                for audit in audits
            ]
            
        except Exception as e:
            logger.error(f"Failed to get recent refresh operations: {e}")
            return []
    
    async def get_expiring_tokens_report(self, db: Session, hours_threshold: int = 48) -> Dict[str, Any]:
        """
        Generate report of tokens expiring soon
        
        Args:
            db: Database session
            hours_threshold: Hours ahead to check for expiring tokens
            
        Returns:
            Dictionary with expiring tokens report
        """
        try:
            now = datetime.now(timezone.utc)
            expiring_threshold = now + timedelta(hours=hours_threshold)
            
            # Check SocialConnection tokens
            expiring_connections = db.query(SocialConnection).filter(
                and_(
                    SocialConnection.is_active == True,
                    SocialConnection.token_expires_at.isnot(None),
                    SocialConnection.token_expires_at <= expiring_threshold,
                    SocialConnection.token_expires_at > now
                )
            ).order_by(SocialConnection.token_expires_at).all()
            
            # Check SocialPlatformConnection entries
            expiring_platform_connections = []
            try:
                expiring_platform_connections = db.query(SocialPlatformConnection).filter(
                    and_(
                        SocialPlatformConnection.is_active == True,
                        SocialPlatformConnection.token_expires_at.isnot(None),
                        SocialPlatformConnection.token_expires_at <= expiring_threshold,
                        SocialPlatformConnection.token_expires_at > now
                    )
                ).order_by(SocialPlatformConnection.token_expires_at).all()
            except Exception:
                # SocialPlatformConnection table might not exist
                pass
            
            # Group by platform
            platform_summary = {}
            
            for conn in expiring_connections:
                platform = conn.platform
                if platform not in platform_summary:
                    platform_summary[platform] = {"connections": 0, "oauth_tokens": 0, "earliest_expiry": None}
                
                platform_summary[platform]["connections"] += 1
                if not platform_summary[platform]["earliest_expiry"] or conn.token_expires_at < platform_summary[platform]["earliest_expiry"]:
                    platform_summary[platform]["earliest_expiry"] = conn.token_expires_at
            
            for token in expiring_platform_connections:
                platform = token.platform
                if platform not in platform_summary:
                    platform_summary[platform] = {"connections": 0, "platform_connections": 0, "earliest_expiry": None}
                
                platform_summary[platform]["platform_connections"] += 1
                if not platform_summary[platform]["earliest_expiry"] or token.token_expires_at < platform_summary[platform]["earliest_expiry"]:
                    platform_summary[platform]["earliest_expiry"] = token.token_expires_at
            
            total_expiring = len(expiring_connections) + len(expiring_platform_connections)
            
            report = {
                "timestamp": now.isoformat(),
                "threshold_hours": hours_threshold,
                "total_expiring": total_expiring,
                "platform_summary": platform_summary,
                "expiring_connections": [
                    {
                        "id": conn.id,
                        "platform": conn.platform,
                        "organization_id": conn.organization_id,
                        "expires_at": conn.token_expires_at.isoformat(),
                        "hours_until_expiry": (conn.token_expires_at - now).total_seconds() / 3600
                    }
                    for conn in expiring_connections
                ],
                "expiring_platform_connections": [
                    {
                        "id": token.id,
                        "platform": token.platform,
                        "organization_id": getattr(token, 'organization_id', None),
                        "user_id": token.user_id,
                        "account_name": token.account_name,
                        "expires_at": token.token_expires_at.isoformat(),
                        "hours_until_expiry": (token.token_expires_at - now).total_seconds() / 3600
                    }
                    for token in expiring_platform_connections
                ]
            }
            
            # Log expiring tokens summary
            if total_expiring > 0:
                structured_logger_service.log_security_event(
                    event_type="oauth_tokens_expiring_soon",
                    message=f"{total_expiring} OAuth tokens expiring within {hours_threshold} hours",
                    level=LogLevel.WARNING,
                    metadata={
                        "total_expiring": total_expiring,
                        "platform_summary": platform_summary
                    }
                )
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate expiring tokens report: {e}")
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

# Global OAuth token monitor instance
oauth_token_monitor = OAuthTokenMonitor()

# Convenience functions for integration with token refresh service
async def monitor_token_refresh(platform: str, connection_id: int, organization_id: int, old_expiry: Optional[datetime] = None) -> str:
    """Start monitoring a token refresh operation"""
    return await oauth_token_monitor.start_refresh_monitoring(platform, connection_id, organization_id, old_expiry)

async def complete_token_refresh_monitoring(operation_id: str, success: bool, new_expiry: Optional[datetime] = None, error_message: Optional[str] = None, retry_count: int = 0):
    """Complete monitoring a token refresh operation"""
    await oauth_token_monitor.complete_refresh_monitoring(operation_id, success, new_expiry, error_message, retry_count)

async def get_token_health_dashboard(db: Session) -> Dict[str, Any]:
    """Get comprehensive token health dashboard data"""
    return await oauth_token_monitor.get_token_health_metrics(db)

async def get_expiring_tokens_dashboard(db: Session, hours: int = 48) -> Dict[str, Any]:
    """Get expiring tokens dashboard"""
    return await oauth_token_monitor.get_expiring_tokens_report(db, hours)