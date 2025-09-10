"""
P1-4a: Structured Logging for Rate Limits and Circuit Breakers
Comprehensive structured logging system for observability and monitoring
"""
import logging
import json
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import contextmanager

from backend.core.monitoring import monitoring_service

# Configure structured logger
structured_logger = logging.getLogger("structured_logging")
structured_logger.setLevel(logging.INFO)

class LogLevel(Enum):
    """Log levels for structured logging"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogCategory(Enum):
    """Log categories for filtering and monitoring"""
    RATE_LIMITING = "rate_limiting"
    CIRCUIT_BREAKER = "circuit_breaker" 
    AUTHENTICATION = "authentication"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    INTEGRATION = "integration"
    DATABASE = "database"

@dataclass
class StructuredLogEntry:
    """Structured log entry with standardized fields"""
    timestamp: str
    level: str
    category: str
    service: str
    message: str
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    platform: Optional[str] = None
    action: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Remove None values to keep logs clean
        return {k: v for k, v in result.items() if v is not None}

@dataclass
class RateLimitLogEvent:
    """Rate limiting specific log event"""
    event_type: str  # "limit_exceeded", "limit_allowed", "limit_reset", "config_change"
    identifier: str  # IP, user_id, org_id, etc.
    limit_type: str  # "second", "minute", "hour", "burst"
    limit_value: int
    current_usage: int
    remaining: int
    reset_time_unix: float
    retry_after_seconds: Optional[int] = None
    window_size_seconds: Optional[int] = None
    algorithm: str = "sliding_window"  # "token_bucket", "sliding_window", "fixed_window"

@dataclass 
class CircuitBreakerLogEvent:
    """Circuit breaker specific log event"""
    event_type: str  # "state_change", "request_blocked", "request_allowed", "failure_recorded", "success_recorded"
    circuit_name: str
    previous_state: Optional[str] = None  # "closed", "open", "half_open"
    current_state: str = "closed"
    failure_count: int = 0
    failure_threshold: int = 5
    success_count: int = 0
    last_failure_time: Optional[float] = None
    cooldown_expires_at: Optional[float] = None
    request_result: Optional[str] = None  # "allowed", "blocked"

class StructuredLogger:
    """
    Centralized structured logging service for rate limits, circuit breakers, and more
    Provides consistent log formatting, correlation tracking, and monitoring integration
    """
    
    def __init__(self):
        self.service_name = "lily_media_ai"
        self.version = "2.0.0"
        self._correlation_stack: List[str] = []
    
    def _create_base_log_entry(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        **kwargs
    ) -> StructuredLogEntry:
        """Create base log entry with common fields"""
        return StructuredLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level.value,
            category=category.value,
            service=self.service_name,
            message=message,
            correlation_id=self._correlation_stack[-1] if self._correlation_stack else None,
            **kwargs
        )
    
    def _emit_log(self, entry: StructuredLogEntry):
        """Emit structured log entry"""
        log_data = entry.to_dict()
        
        # Emit to structured logger as JSON
        structured_logger.log(
            getattr(logging, entry.level),
            json.dumps(log_data, default=str),
            extra={"structured_data": log_data}
        )
        
        # Send to monitoring service for metrics
        try:
            if entry.category == LogCategory.RATE_LIMITING.value:
                monitoring_service.prometheus.record_cache_miss("rate_limit_events")
            elif entry.category == LogCategory.CIRCUIT_BREAKER.value:
                monitoring_service.prometheus.record_cache_miss("circuit_breaker_events")
        except Exception as e:
            # Don't let monitoring failures break logging
            pass
    
    @contextmanager
    def correlation_context(self, correlation_id: str):
        """Context manager for correlation tracking"""
        self._correlation_stack.append(correlation_id)
        try:
            yield correlation_id
        finally:
            self._correlation_stack.pop()
    
    # === RATE LIMITING STRUCTURED LOGGING ===
    
    def log_rate_limit_exceeded(
        self,
        identifier: str,
        limit_type: str,
        limit_value: int,
        current_usage: int,
        reset_time: float,
        retry_after: Optional[int] = None,
        organization_id: Optional[str] = None,
        platform: Optional[str] = None
    ):
        """Log rate limit exceeded event"""
        event = RateLimitLogEvent(
            event_type="limit_exceeded",
            identifier=identifier,
            limit_type=limit_type,
            limit_value=limit_value,
            current_usage=current_usage,
            remaining=0,
            reset_time_unix=reset_time,
            retry_after_seconds=retry_after
        )
        
        entry = self._create_base_log_entry(
            level=LogLevel.WARNING,
            category=LogCategory.RATE_LIMITING,
            message=f"Rate limit exceeded: {limit_type} limit of {limit_value}/window for {identifier}",
            organization_id=organization_id,
            platform=platform,
            action="rate_limit_exceeded",
            metadata=asdict(event)
        )
        
        self._emit_log(entry)
    
    def log_rate_limit_allowed(
        self,
        identifier: str,
        limit_type: str,
        limit_value: int,
        remaining: int,
        reset_time: float,
        organization_id: Optional[str] = None,
        platform: Optional[str] = None
    ):
        """Log rate limit allowed event"""
        event = RateLimitLogEvent(
            event_type="limit_allowed",
            identifier=identifier,
            limit_type=limit_type,
            limit_value=limit_value,
            current_usage=limit_value - remaining,
            remaining=remaining,
            reset_time_unix=reset_time
        )
        
        entry = self._create_base_log_entry(
            level=LogLevel.DEBUG,
            category=LogCategory.RATE_LIMITING,
            message=f"Rate limit check passed: {remaining}/{limit_value} remaining for {identifier}",
            organization_id=organization_id,
            platform=platform,
            action="rate_limit_allowed",
            metadata=asdict(event)
        )
        
        self._emit_log(entry)
    
    def log_rate_limit_reset(
        self,
        identifier: str,
        limit_type: str,
        organization_id: Optional[str] = None,
        platform: Optional[str] = None
    ):
        """Log rate limit reset/window refresh"""
        entry = self._create_base_log_entry(
            level=LogLevel.INFO,
            category=LogCategory.RATE_LIMITING,
            message=f"Rate limit window reset for {identifier} - {limit_type}",
            organization_id=organization_id,
            platform=platform,
            action="rate_limit_reset",
            metadata={"event_type": "limit_reset", "identifier": identifier, "limit_type": limit_type}
        )
        
        self._emit_log(entry)
    
    def log_rate_limit_config_change(
        self,
        identifier: str,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        changed_by: Optional[str] = None
    ):
        """Log rate limiting configuration changes"""
        entry = self._create_base_log_entry(
            level=LogLevel.INFO,
            category=LogCategory.RATE_LIMITING,
            message=f"Rate limiting configuration updated for {identifier}",
            user_id=changed_by,
            action="rate_limit_config_change",
            metadata={
                "event_type": "config_change",
                "identifier": identifier,
                "old_config": old_config,
                "new_config": new_config,
                "config_diff": self._calculate_config_diff(old_config, new_config)
            }
        )
        
        self._emit_log(entry)
    
    # === CIRCUIT BREAKER STRUCTURED LOGGING ===
    
    def log_circuit_breaker_state_change(
        self,
        circuit_name: str,
        previous_state: str,
        current_state: str,
        failure_count: int,
        failure_threshold: int,
        reason: str,
        organization_id: Optional[str] = None,
        platform: Optional[str] = None
    ):
        """Log circuit breaker state transitions"""
        event = CircuitBreakerLogEvent(
            event_type="state_change",
            circuit_name=circuit_name,
            previous_state=previous_state,
            current_state=current_state,
            failure_count=failure_count,
            failure_threshold=failure_threshold,
            last_failure_time=time.time()
        )
        
        level = LogLevel.CRITICAL if current_state == "open" else LogLevel.WARNING
        
        entry = self._create_base_log_entry(
            level=level,
            category=LogCategory.CIRCUIT_BREAKER,
            message=f"Circuit breaker '{circuit_name}' state: {previous_state} → {current_state} ({reason})",
            organization_id=organization_id,
            platform=platform,
            action="circuit_state_change",
            metadata=asdict(event)
        )
        
        self._emit_log(entry)
    
    def log_circuit_breaker_request_blocked(
        self,
        circuit_name: str,
        current_state: str,
        cooldown_remaining: float,
        organization_id: Optional[str] = None,
        platform: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log requests blocked by circuit breaker"""
        event = CircuitBreakerLogEvent(
            event_type="request_blocked",
            circuit_name=circuit_name,
            current_state=current_state,
            request_result="blocked",
            cooldown_expires_at=time.time() + cooldown_remaining
        )
        
        entry = self._create_base_log_entry(
            level=LogLevel.WARNING,
            category=LogCategory.CIRCUIT_BREAKER,
            message=f"Request blocked by circuit breaker '{circuit_name}' (state: {current_state})",
            organization_id=organization_id,
            platform=platform,
            request_id=request_id,
            action="circuit_request_blocked",
            metadata=asdict(event)
        )
        
        self._emit_log(entry)
    
    def log_circuit_breaker_request_allowed(
        self,
        circuit_name: str,
        current_state: str,
        organization_id: Optional[str] = None,
        platform: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log requests allowed through circuit breaker"""
        event = CircuitBreakerLogEvent(
            event_type="request_allowed",
            circuit_name=circuit_name,
            current_state=current_state,
            request_result="allowed"
        )
        
        entry = self._create_base_log_entry(
            level=LogLevel.DEBUG,
            category=LogCategory.CIRCUIT_BREAKER,
            message=f"Request allowed through circuit breaker '{circuit_name}' (state: {current_state})",
            organization_id=organization_id,
            platform=platform,
            request_id=request_id,
            action="circuit_request_allowed",
            metadata=asdict(event)
        )
        
        self._emit_log(entry)
    
    def log_circuit_breaker_failure(
        self,
        circuit_name: str,
        error: Exception,
        failure_count: int,
        failure_threshold: int,
        duration_ms: float,
        organization_id: Optional[str] = None,
        platform: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log circuit breaker failure events"""
        event = CircuitBreakerLogEvent(
            event_type="failure_recorded",
            circuit_name=circuit_name,
            current_state="closed",  # Will be updated if threshold reached
            failure_count=failure_count,
            failure_threshold=failure_threshold,
            last_failure_time=time.time()
        )
        
        entry = self._create_base_log_entry(
            level=LogLevel.ERROR,
            category=LogCategory.CIRCUIT_BREAKER,
            message=f"Circuit breaker '{circuit_name}' recorded failure ({failure_count}/{failure_threshold})",
            organization_id=organization_id,
            platform=platform,
            request_id=request_id,
            action="circuit_failure_recorded",
            duration_ms=duration_ms,
            error_details={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "is_timeout": "timeout" in str(error).lower(),
                "is_connection_error": "connection" in str(error).lower()
            },
            metadata=asdict(event)
        )
        
        self._emit_log(entry)
    
    def log_circuit_breaker_success(
        self,
        circuit_name: str,
        current_state: str,
        success_count: int,
        duration_ms: float,
        organization_id: Optional[str] = None,
        platform: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log circuit breaker success events"""
        event = CircuitBreakerLogEvent(
            event_type="success_recorded",
            circuit_name=circuit_name,
            current_state=current_state,
            success_count=success_count
        )
        
        entry = self._create_base_log_entry(
            level=LogLevel.DEBUG,
            category=LogCategory.CIRCUIT_BREAKER,
            message=f"Circuit breaker '{circuit_name}' recorded success (state: {current_state})",
            organization_id=organization_id,
            platform=platform,
            request_id=request_id,
            action="circuit_success_recorded",
            duration_ms=duration_ms,
            metadata=asdict(event)
        )
        
        self._emit_log(entry)
    
    # === GENERAL PURPOSE STRUCTURED LOGGING ===
    
    def log_security_event(
        self,
        event_type: str,
        message: str,
        level: LogLevel = LogLevel.WARNING,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log security-related events"""
        entry = self._create_base_log_entry(
            level=level,
            category=LogCategory.SECURITY,
            message=message,
            user_id=user_id,
            organization_id=organization_id,
            action=event_type,
            metadata=metadata or {}
        )
        
        self._emit_log(entry)
    
    def log_performance_event(
        self,
        operation: str,
        duration_ms: float,
        message: str,
        level: LogLevel = LogLevel.INFO,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log performance-related events"""
        entry = self._create_base_log_entry(
            level=level,
            category=LogCategory.PERFORMANCE,
            message=message,
            action=operation,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        
        self._emit_log(entry)
    
    def log_integration_event(
        self,
        platform: str,
        event_type: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        organization_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log social platform integration events"""
        entry = self._create_base_log_entry(
            level=level,
            category=LogCategory.INTEGRATION,
            message=message,
            platform=platform,
            organization_id=organization_id,
            action=event_type,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        
        self._emit_log(entry)
    
    # === UTILITY METHODS ===
    
    def _calculate_config_diff(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate configuration differences"""
        diff = {}
        
        # Find changed values
        for key, new_value in new_config.items():
            old_value = old_config.get(key)
            if old_value != new_value:
                diff[key] = {
                    "old": old_value,
                    "new": new_value
                }
        
        # Find removed keys
        for key in old_config:
            if key not in new_config:
                diff[key] = {
                    "old": old_config[key],
                    "new": None
                }
        
        return diff

# Global structured logger instance
structured_logger_service = StructuredLogger()

# Convenience functions for common logging patterns
def log_rate_limit_exceeded(identifier: str, limit_type: str, limit_value: int, 
                          current_usage: int, reset_time: float, **kwargs):
    """Convenience function for logging rate limit exceeded"""
    structured_logger_service.log_rate_limit_exceeded(
        identifier, limit_type, limit_value, current_usage, reset_time, **kwargs
    )

def log_circuit_breaker_opened(circuit_name: str, failure_count: int, 
                              failure_threshold: int, **kwargs):
    """Convenience function for logging circuit breaker opening"""
    structured_logger_service.log_circuit_breaker_state_change(
        circuit_name, "closed", "open", failure_count, failure_threshold,
        f"Failure threshold reached ({failure_count}/{failure_threshold})", **kwargs
    )

def log_circuit_breaker_closed(circuit_name: str, **kwargs):
    """Convenience function for logging circuit breaker closing"""
    structured_logger_service.log_circuit_breaker_state_change(
        circuit_name, "half_open", "closed", 0, 5,
        "Circuit breaker reset - service recovered", **kwargs
    )

# Context managers for correlation tracking
@contextmanager
def correlation_context(correlation_id: str):
    """Context manager for request correlation"""
    with structured_logger_service.correlation_context(correlation_id):
        yield

# Performance timing decorator
@contextmanager
def performance_timing(operation: str, **kwargs):
    """Context manager for performance timing"""
    start_time = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000
        structured_logger_service.log_performance_event(
            operation=operation,
            duration_ms=duration_ms,
            message=f"Operation '{operation}' completed in {duration_ms:.2f}ms",
            **kwargs
        )