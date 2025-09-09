"""
P1-4c: Webhook Signature Validation Failure Metrics
Comprehensive monitoring for webhook signature validation with metrics and alerting
"""
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

from backend.core.structured_logging import structured_logger_service, LogLevel
from backend.core.monitoring import monitoring_service

logger = logging.getLogger(__name__)

class WebhookValidationResult(Enum):
    """Webhook validation results"""
    SUCCESS = "success"
    INVALID_SIGNATURE = "invalid_signature"
    MISSING_SIGNATURE = "missing_signature" 
    EXPIRED_WEBHOOK = "expired_webhook"
    MISSING_SECRET = "missing_secret"
    MALFORMED_SIGNATURE = "malformed_signature"
    UNKNOWN_PLATFORM = "unknown_platform"
    INTERNAL_ERROR = "internal_error"

class WebhookSecurityThreat(Enum):
    """Types of security threats detected"""
    SIGNATURE_ATTACK = "signature_attack"  # Multiple failed signatures from same IP
    REPLAY_ATTACK = "replay_attack"       # Old timestamps
    PLATFORM_SPOOFING = "platform_spoofing"  # Unknown platforms
    BRUTE_FORCE = "brute_force"          # Rapid signature attempts
    MALFORMED_PAYLOAD = "malformed_payload"  # Suspicious payload patterns

@dataclass
class WebhookValidationMetrics:
    """Webhook signature validation metrics"""
    platform: str
    total_validations: int = 0
    successful_validations: int = 0
    failed_validations: int = 0
    missing_signatures: int = 0
    expired_webhooks: int = 0
    malformed_signatures: int = 0
    unknown_platforms: int = 0
    internal_errors: int = 0
    avg_validation_time_ms: float = 0.0
    last_validation_time: Optional[str] = None
    
    def get_success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_validations == 0:
            return 100.0
        return (self.successful_validations / self.total_validations) * 100.0
    
    def get_security_score(self) -> float:
        """Calculate security score (0-100) based on validation patterns"""
        if self.total_validations == 0:
            return 100.0
        
        # Penalize high failure rates more heavily
        success_rate = self.get_success_rate()
        failure_penalty = (100 - success_rate) * 1.5
        
        # Additional penalties for security issues
        missing_sig_penalty = (self.missing_signatures / self.total_validations) * 20
        expired_penalty = (self.expired_webhooks / self.total_validations) * 15
        malformed_penalty = (self.malformed_signatures / self.total_validations) * 10
        
        score = 100 - failure_penalty - missing_sig_penalty - expired_penalty - malformed_penalty
        return max(0.0, min(100.0, score))

@dataclass
class WebhookValidationEvent:
    """Individual webhook validation event"""
    timestamp: str
    platform: str
    result: WebhookValidationResult
    validation_time_ms: float
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    payload_size_bytes: int = 0
    signature_header: Optional[str] = None
    error_message: Optional[str] = None
    threat_detected: Optional[WebhookSecurityThreat] = None

class WebhookSignatureMonitor:
    """
    Comprehensive webhook signature validation monitoring
    P1-4c Implementation: Advanced metrics and security monitoring
    """
    
    def __init__(self):
        self.platform_metrics: Dict[str, WebhookValidationMetrics] = {}
        self.recent_events: List[WebhookValidationEvent] = []
        self.threat_tracking: Dict[str, Dict[str, Any]] = {}  # IP -> threat info
        self.max_recent_events = 1000
        
        # Security thresholds
        self.security_thresholds = {
            "max_failures_per_ip_per_minute": 10,
            "max_failures_per_platform_per_minute": 50,
            "critical_failure_rate_threshold": 25.0,  # 25% failure rate
            "warning_failure_rate_threshold": 10.0,   # 10% failure rate
            "replay_attack_threshold_minutes": 5,
            "brute_force_window_minutes": 1
        }
    
    def log_validation_attempt(
        self,
        platform: str,
        result: WebhookValidationResult,
        validation_time_ms: float,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        payload_size: int = 0,
        signature_header: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """
        Log a webhook signature validation attempt
        
        Args:
            platform: Platform name (meta, twitter, stripe, etc.)
            result: Validation result
            validation_time_ms: Time taken for validation in milliseconds
            ip_address: Client IP address (for threat detection)
            user_agent: Client User-Agent header
            payload_size: Size of webhook payload in bytes
            signature_header: Signature header value (for analysis)
            error_message: Error message if validation failed
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Update platform metrics
            if platform not in self.platform_metrics:
                self.platform_metrics[platform] = WebhookValidationMetrics(platform=platform)
            
            metrics = self.platform_metrics[platform]
            metrics.total_validations += 1
            metrics.last_validation_time = timestamp
            
            # Update counters based on result
            if result == WebhookValidationResult.SUCCESS:
                metrics.successful_validations += 1
            else:
                metrics.failed_validations += 1
                
                if result == WebhookValidationResult.MISSING_SIGNATURE:
                    metrics.missing_signatures += 1
                elif result == WebhookValidationResult.EXPIRED_WEBHOOK:
                    metrics.expired_webhooks += 1
                elif result == WebhookValidationResult.MALFORMED_SIGNATURE:
                    metrics.malformed_signatures += 1
                elif result == WebhookValidationResult.UNKNOWN_PLATFORM:
                    metrics.unknown_platforms += 1
                elif result == WebhookValidationResult.INTERNAL_ERROR:
                    metrics.internal_errors += 1
            
            # Update average validation time
            total_time = metrics.avg_validation_time_ms * (metrics.total_validations - 1) + validation_time_ms
            metrics.avg_validation_time_ms = total_time / metrics.total_validations
            
            # Detect security threats
            threat_detected = self._detect_security_threats(
                platform, result, ip_address, payload_size, signature_header
            )
            
            # Create validation event
            event = WebhookValidationEvent(
                timestamp=timestamp,
                platform=platform,
                result=result,
                validation_time_ms=validation_time_ms,
                ip_address=ip_address,
                user_agent=user_agent,
                payload_size_bytes=payload_size,
                signature_header=signature_header[:50] if signature_header else None,  # Truncate for logging
                error_message=error_message,
                threat_detected=threat_detected
            )
            
            # Store recent events (with rotation)
            self.recent_events.append(event)
            if len(self.recent_events) > self.max_recent_events:
                self.recent_events = self.recent_events[-self.max_recent_events:]
            
            # Log structured event
            self._log_validation_event(event, metrics)
            
            # Send to Prometheus metrics
            self._send_prometheus_metrics(platform, result, validation_time_ms, threat_detected)
            
            # Check for alerting conditions
            self._check_validation_alerts(platform, result, metrics, threat_detected, ip_address)
            
        except Exception as e:
            logger.error(f"Failed to log webhook validation attempt: {e}")
    
    def _detect_security_threats(
        self,
        platform: str,
        result: WebhookValidationResult,
        ip_address: Optional[str],
        payload_size: int,
        signature_header: Optional[str]
    ) -> Optional[WebhookSecurityThreat]:
        """Detect potential security threats based on validation patterns"""
        try:
            if not ip_address:
                return None
            
            now = time.time()
            
            # Initialize threat tracking for IP
            if ip_address not in self.threat_tracking:
                self.threat_tracking[ip_address] = {
                    "failed_attempts": [],
                    "platforms_attempted": set(),
                    "last_seen": now,
                    "total_requests": 0
                }
            
            ip_data = self.threat_tracking[ip_address]
            ip_data["last_seen"] = now
            ip_data["total_requests"] += 1
            ip_data["platforms_attempted"].add(platform)
            
            # Clean old failed attempts (older than 5 minutes)
            cutoff_time = now - (5 * 60)
            ip_data["failed_attempts"] = [
                attempt for attempt in ip_data["failed_attempts"] 
                if attempt["timestamp"] > cutoff_time
            ]
            
            # Track failed attempts
            if result != WebhookValidationResult.SUCCESS:
                ip_data["failed_attempts"].append({
                    "timestamp": now,
                    "platform": platform,
                    "result": result.value,
                    "payload_size": payload_size
                })
            
            # Detect brute force attacks
            recent_failures = len([
                attempt for attempt in ip_data["failed_attempts"]
                if attempt["timestamp"] > (now - 60)  # Last minute
            ])
            
            if recent_failures > self.security_thresholds["max_failures_per_ip_per_minute"]:
                return WebhookSecurityThreat.BRUTE_FORCE
            
            # Detect replay attacks
            if result == WebhookValidationResult.EXPIRED_WEBHOOK:
                return WebhookSecurityThreat.REPLAY_ATTACK
            
            # Detect platform spoofing
            if result == WebhookValidationResult.UNKNOWN_PLATFORM:
                return WebhookSecurityThreat.PLATFORM_SPOOFING
            
            # Detect signature attacks (multiple signature format failures)
            signature_failures = len([
                attempt for attempt in ip_data["failed_attempts"]
                if attempt["result"] in ["invalid_signature", "malformed_signature"]
                and attempt["timestamp"] > (now - 60)
            ])
            
            if signature_failures > 5:  # More than 5 signature failures per minute
                return WebhookSecurityThreat.SIGNATURE_ATTACK
            
            # Detect malformed payloads (unusually large payloads)
            if payload_size > 1024 * 1024:  # > 1MB payload
                return WebhookSecurityThreat.MALFORMED_PAYLOAD
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting security threats: {e}")
            return None
    
    def _log_validation_event(self, event: WebhookValidationEvent, metrics: WebhookValidationMetrics):
        """Log structured webhook validation event"""
        # Determine log level based on result and threat
        if event.threat_detected:
            level = LogLevel.CRITICAL
        elif event.result != WebhookValidationResult.SUCCESS:
            level = LogLevel.WARNING
        else:
            level = LogLevel.DEBUG  # Successful validations at debug level
        
        # Create message
        if event.result == WebhookValidationResult.SUCCESS:
            message = f"Webhook signature validated successfully for {event.platform}"
        else:
            message = f"Webhook signature validation failed for {event.platform}: {event.result.value}"
        
        if event.threat_detected:
            message += f" (THREAT: {event.threat_detected.value})"
        
        structured_logger_service.log_security_event(
            event_type="webhook_signature_validation",
            message=message,
            level=level,
            metadata={
                "platform": event.platform,
                "result": event.result.value,
                "validation_time_ms": event.validation_time_ms,
                "payload_size_bytes": event.payload_size_bytes,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "error_message": event.error_message,
                "threat_detected": event.threat_detected.value if event.threat_detected else None,
                "platform_success_rate": metrics.get_success_rate(),
                "platform_total_validations": metrics.total_validations
            }
        )
    
    def _send_prometheus_metrics(
        self,
        platform: str,
        result: WebhookValidationResult,
        validation_time_ms: float,
        threat_detected: Optional[WebhookSecurityThreat]
    ):
        """Send metrics to Prometheus"""
        try:
            # Record webhook validation counter
            monitoring_service.record_webhook_validation(
                platform=platform,
                result=result.value,
                threat_level="high" if threat_detected else "none"
            )
            
            # Record validation timing
            monitoring_service.record_webhook_validation_time(
                platform=platform,
                duration_seconds=validation_time_ms / 1000
            )
            
            # Record threats
            if threat_detected:
                monitoring_service.record_webhook_threat(
                    platform=platform,
                    threat_type=threat_detected.value
                )
                
        except Exception as e:
            logger.debug(f"Failed to send Prometheus metrics: {e}")
    
    def _check_validation_alerts(
        self,
        platform: str,
        result: WebhookValidationResult,
        metrics: WebhookValidationMetrics,
        threat_detected: Optional[WebhookSecurityThreat],
        ip_address: Optional[str]
    ):
        """Check if validation results should trigger alerts"""
        try:
            # Alert on security threats
            if threat_detected:
                structured_logger_service.log_security_event(
                    event_type="webhook_security_threat_detected",
                    message=f"Webhook security threat detected: {threat_detected.value} on {platform}",
                    level=LogLevel.CRITICAL,
                    metadata={
                        "platform": platform,
                        "threat_type": threat_detected.value,
                        "ip_address": ip_address,
                        "result": result.value
                    }
                )
            
            # Alert on high failure rates
            success_rate = metrics.get_success_rate()
            if metrics.total_validations >= 10:  # Only alert if we have enough data
                if success_rate < self.security_thresholds["critical_failure_rate_threshold"]:
                    structured_logger_service.log_security_event(
                        event_type="webhook_validation_critical_failure_rate",
                        message=f"Critical webhook validation failure rate for {platform}: {success_rate:.1f}%",
                        level=LogLevel.CRITICAL,
                        metadata={
                            "platform": platform,
                            "success_rate": success_rate,
                            "total_validations": metrics.total_validations,
                            "failed_validations": metrics.failed_validations
                        }
                    )
                elif success_rate < self.security_thresholds["warning_failure_rate_threshold"]:
                    structured_logger_service.log_security_event(
                        event_type="webhook_validation_warning_failure_rate",
                        message=f"High webhook validation failure rate for {platform}: {success_rate:.1f}%",
                        level=LogLevel.WARNING,
                        metadata={
                            "platform": platform,
                            "success_rate": success_rate,
                            "total_validations": metrics.total_validations
                        }
                    )
            
            # Alert on slow validations (> 100ms is concerning for signature validation)
            if metrics.avg_validation_time_ms > 100:
                structured_logger_service.log_performance_event(
                    operation="webhook_signature_validation",
                    duration_ms=metrics.avg_validation_time_ms,
                    message=f"Slow webhook signature validation for {platform}: {metrics.avg_validation_time_ms:.1f}ms average",
                    level=LogLevel.WARNING,
                    metadata={
                        "platform": platform,
                        "avg_validation_time_ms": metrics.avg_validation_time_ms,
                        "total_validations": metrics.total_validations
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to check validation alerts: {e}")
    
    def get_platform_metrics(self, platform: Optional[str] = None) -> Dict[str, WebhookValidationMetrics]:
        """
        Get webhook validation metrics for platforms
        
        Args:
            platform: Specific platform to get metrics for (None for all)
            
        Returns:
            Dictionary of platform metrics
        """
        if platform:
            return {platform: self.platform_metrics.get(platform, WebhookValidationMetrics(platform=platform))}
        return self.platform_metrics.copy()
    
    def get_recent_events(self, platform: Optional[str] = None, limit: int = 100) -> List[WebhookValidationEvent]:
        """
        Get recent webhook validation events
        
        Args:
            platform: Filter by platform (None for all)
            limit: Maximum number of events to return
            
        Returns:
            List of recent validation events
        """
        events = self.recent_events
        
        if platform:
            events = [event for event in events if event.platform == platform]
        
        return events[-limit:] if limit else events
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get comprehensive security summary"""
        try:
            now = time.time()
            cutoff_time = now - (24 * 3600)  # Last 24 hours
            
            # Filter recent events
            recent_events = [
                event for event in self.recent_events
                if datetime.fromisoformat(event.timestamp).timestamp() > cutoff_time
            ]
            
            # Calculate summary statistics
            total_validations = len(recent_events)
            successful_validations = len([e for e in recent_events if e.result == WebhookValidationResult.SUCCESS])
            threats_detected = len([e for e in recent_events if e.threat_detected])
            
            # Group by platform
            platform_stats = {}
            for event in recent_events:
                platform = event.platform
                if platform not in platform_stats:
                    platform_stats[platform] = {"total": 0, "success": 0, "threats": 0}
                
                platform_stats[platform]["total"] += 1
                if event.result == WebhookValidationResult.SUCCESS:
                    platform_stats[platform]["success"] += 1
                if event.threat_detected:
                    platform_stats[platform]["threats"] += 1
            
            # Calculate success rates
            for platform, stats in platform_stats.items():
                stats["success_rate"] = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 100
            
            # Threat analysis
            threat_types = {}
            for event in recent_events:
                if event.threat_detected:
                    threat_type = event.threat_detected.value
                    threat_types[threat_type] = threat_types.get(threat_type, 0) + 1
            
            # Active IPs with threats
            threat_ips = set()
            for event in recent_events:
                if event.threat_detected and event.ip_address:
                    threat_ips.add(event.ip_address)
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "period_hours": 24,
                "summary": {
                    "total_validations": total_validations,
                    "successful_validations": successful_validations,
                    "success_rate": (successful_validations / total_validations) * 100 if total_validations > 0 else 100,
                    "threats_detected": threats_detected,
                    "threat_rate": (threats_detected / total_validations) * 100 if total_validations > 0 else 0,
                    "active_platforms": len(platform_stats),
                    "threat_ips": len(threat_ips)
                },
                "platform_stats": platform_stats,
                "threat_analysis": {
                    "threat_types": threat_types,
                    "threat_ips": list(threat_ips)[:10]  # Limit to first 10 for privacy
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate security summary: {e}")
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

# Global webhook signature monitor instance
webhook_signature_monitor = WebhookSignatureMonitor()

# Convenience functions for integration with webhook validation
def log_webhook_validation(
    platform: str,
    success: bool,
    validation_time_ms: float,
    error_message: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    payload_size: int = 0,
    signature_header: Optional[str] = None
):
    """Log webhook signature validation result"""
    result = WebhookValidationResult.SUCCESS if success else WebhookValidationResult.INVALID_SIGNATURE
    
    if not success and error_message:
        # Map error messages to specific result types
        error_lower = error_message.lower()
        if "missing" in error_lower and "signature" in error_lower:
            result = WebhookValidationResult.MISSING_SIGNATURE
        elif "expired" in error_lower or "timestamp" in error_lower:
            result = WebhookValidationResult.EXPIRED_WEBHOOK
        elif "malformed" in error_lower or "format" in error_lower:
            result = WebhookValidationResult.MALFORMED_SIGNATURE
        elif "secret" in error_lower and "missing" in error_lower:
            result = WebhookValidationResult.MISSING_SECRET
        elif "platform" in error_lower or "unsupported" in error_lower:
            result = WebhookValidationResult.UNKNOWN_PLATFORM
        elif "internal" in error_lower or "error" in error_lower:
            result = WebhookValidationResult.INTERNAL_ERROR
    
    webhook_signature_monitor.log_validation_attempt(
        platform=platform,
        result=result,
        validation_time_ms=validation_time_ms,
        ip_address=ip_address,
        user_agent=user_agent,
        payload_size=payload_size,
        signature_header=signature_header,
        error_message=error_message
    )

def get_webhook_validation_metrics(platform: Optional[str] = None) -> Dict[str, Any]:
    """Get webhook validation metrics dashboard"""
    metrics = webhook_signature_monitor.get_platform_metrics(platform)
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform_metrics": {
            platform: {
                "total_validations": m.total_validations,
                "success_rate": m.get_success_rate(),
                "security_score": m.get_security_score(),
                "failed_validations": m.failed_validations,
                "missing_signatures": m.missing_signatures,
                "expired_webhooks": m.expired_webhooks,
                "avg_validation_time_ms": m.avg_validation_time_ms,
                "last_validation": m.last_validation_time
            }
            for platform, m in metrics.items()
        }
    }

def get_webhook_security_dashboard() -> Dict[str, Any]:
    """Get comprehensive webhook security dashboard"""
    return webhook_signature_monitor.get_security_summary()