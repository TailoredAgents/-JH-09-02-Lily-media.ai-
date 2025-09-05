"""
Monitoring and observability integration for Prometheus and Sentry
Provides centralized metrics collection and error tracking for production deployment
"""
import logging
import os
import time
from typing import Dict, Any, Optional, List
from functools import wraps
from contextlib import contextmanager
from datetime import datetime, timedelta

# Optional dependencies for monitoring
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from backend.core.config import settings

logger = logging.getLogger(__name__)

class PrometheusMetrics:
    """Prometheus metrics collector for application monitoring"""
    
    def __init__(self):
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus client not available. Install prometheus_client for metrics.")
            return
            
        self.registry = CollectorRegistry()
        
        # API Metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Database Metrics
        self.db_queries_total = Counter(
            'db_queries_total',
            'Total database queries',
            ['query_type'],
            registry=self.registry
        )
        
        self.db_query_duration_seconds = Histogram(
            'db_query_duration_seconds',
            'Database query duration in seconds',
            ['query_type'],
            registry=self.registry
        )
        
        self.db_connections_active = Gauge(
            'db_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        # Application Metrics
        self.cache_hits_total = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_misses_total = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache_type'],
            registry=self.registry
        )
        
        self.active_users = Gauge(
            'active_users',
            'Number of active users',
            registry=self.registry
        )
        
        # Social Media Platform Metrics
        self.social_posts_total = Counter(
            'social_posts_total',
            'Total social media posts',
            ['platform', 'status'],
            registry=self.registry
        )
        
        self.social_api_calls_total = Counter(
            'social_api_calls_total',
            'Total social platform API calls',
            ['platform', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        # Celery Task Metrics
        self.celery_tasks_total = Counter(
            'celery_tasks_total',
            'Total Celery tasks',
            ['task_name', 'status'],
            registry=self.registry
        )
        
        self.celery_task_duration_seconds = Histogram(
            'celery_task_duration_seconds',
            'Celery task duration in seconds',
            ['task_name'],
            registry=self.registry
        )
        
        logger.info("Prometheus metrics initialized successfully")
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
            
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_db_query(self, query_type: str, duration: float):
        """Record database query metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
            
        self.db_queries_total.labels(query_type=query_type).inc()
        self.db_query_duration_seconds.labels(query_type=query_type).observe(duration)
    
    def record_cache_hit(self, cache_type: str = "default"):
        """Record cache hit"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.cache_hits_total.labels(cache_type=cache_type).inc()
    
    def record_cache_miss(self, cache_type: str = "default"):
        """Record cache miss"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.cache_misses_total.labels(cache_type=cache_type).inc()
    
    def record_social_post(self, platform: str, status: str):
        """Record social media post"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.social_posts_total.labels(platform=platform, status=status).inc()
    
    def record_social_api_call(self, platform: str, endpoint: str, status_code: int):
        """Record social platform API call"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.social_api_calls_total.labels(
            platform=platform,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
    
    def record_celery_task(self, task_name: str, status: str, duration: Optional[float] = None):
        """Record Celery task metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
            
        self.celery_tasks_total.labels(task_name=task_name, status=status).inc()
        
        if duration is not None:
            self.celery_task_duration_seconds.labels(task_name=task_name).observe(duration)
    
    def update_active_users(self, count: int):
        """Update active users count"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.active_users.set(count)
    
    def update_db_connections(self, count: int):
        """Update database connections count"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.db_connections_active.set(count)
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        if not PROMETHEUS_AVAILABLE:
            return ""
        return generate_latest(self.registry).decode('utf-8')

class SentryIntegration:
    """Sentry error tracking and performance monitoring"""
    
    def __init__(self):
        self.initialized = False
        
        if not SENTRY_AVAILABLE:
            logger.warning("Sentry SDK not available. Install sentry-sdk for error tracking.")
            return
            
        self.dsn = getattr(settings, 'SENTRY_DSN', None) or os.getenv('SENTRY_DSN')
        
        if not self.dsn:
            logger.warning("Sentry DSN not configured. Set SENTRY_DSN environment variable.")
            return
        
        try:
            sentry_sdk.init(
                dsn=self.dsn,
                integrations=[
                    FastApiIntegration(),
                    SqlalchemyIntegration(),
                    CeleryIntegration()
                ],
                traces_sample_rate=0.1,  # Capture 10% of transactions for performance monitoring
                send_default_pii=False,  # Don't send personally identifiable information
                environment=getattr(settings, 'ENVIRONMENT', 'development'),
                release=getattr(settings, 'VERSION', 'unknown')
            )
            
            self.initialized = True
            logger.info("Sentry error tracking initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
    
    def capture_exception(self, exception: Exception, context: Optional[Dict[str, Any]] = None):
        """Capture exception with context"""
        if not self.initialized:
            return
            
        if context:
            with sentry_sdk.configure_scope() as scope:
                for key, value in context.items():
                    scope.set_context(key, value)
        
        sentry_sdk.capture_exception(exception)
    
    def capture_message(self, message: str, level: str = "info", context: Optional[Dict[str, Any]] = None):
        """Capture message with context"""
        if not self.initialized:
            return
            
        if context:
            with sentry_sdk.configure_scope() as scope:
                for key, value in context.items():
                    scope.set_context(key, value)
        
        sentry_sdk.capture_message(message, level=level)
    
    def set_user_context(self, user_id: str, email: Optional[str] = None, username: Optional[str] = None):
        """Set user context for error tracking"""
        if not self.initialized:
            return
            
        with sentry_sdk.configure_scope() as scope:
            scope.user = {
                "id": user_id,
                "email": email,
                "username": username
            }
    
    def set_tag(self, key: str, value: str):
        """Set tag for filtering errors"""
        if not self.initialized:
            return
            
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag(key, value)
    
    @contextmanager
    def transaction(self, name: str, op: str = "http.server"):
        """Create a performance transaction"""
        if not self.initialized:
            yield None
            return
            
        with sentry_sdk.start_transaction(op=op, name=name) as transaction:
            yield transaction

class MonitoringService:
    """Unified monitoring service combining Prometheus and Sentry"""
    
    def __init__(self):
        self.prometheus = PrometheusMetrics()
        self.sentry = SentryIntegration()
        self.start_time = time.time()
        
        logger.info("Monitoring service initialized")
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float, 
                      user_id: Optional[str] = None):
        """Record HTTP request across all monitoring systems"""
        
        # Record in Prometheus
        self.prometheus.record_http_request(method, endpoint, status_code, duration)
        
        # Set user context in Sentry if provided
        if user_id:
            self.sentry.set_user_context(user_id)
        
        # Log slow requests
        if duration > 5.0:  # Requests slower than 5 seconds
            self.sentry.capture_message(
                f"Slow request detected: {method} {endpoint} took {duration:.2f}s",
                level="warning",
                context={"request": {"method": method, "endpoint": endpoint, "duration": duration}}
            )
    
    def record_error(self, exception: Exception, context: Optional[Dict[str, Any]] = None):
        """Record error across all monitoring systems"""
        
        # Log locally
        logger.error(f"Application error: {exception}", exc_info=True)
        
        # Send to Sentry
        self.sentry.capture_exception(exception, context)
    
    def record_social_activity(self, platform: str, action: str, status: str, user_id: Optional[str] = None):
        """Record social media platform activity"""
        
        self.prometheus.record_social_post(platform, status)
        
        if user_id:
            self.sentry.set_user_context(user_id)
        
        # Log social media errors
        if status == "failed":
            self.sentry.capture_message(
                f"Social media {action} failed on {platform}",
                level="error",
                context={"social": {"platform": platform, "action": action, "status": status}}
            )
    
    def record_task_completion(self, task_name: str, status: str, duration: Optional[float] = None):
        """Record Celery task completion"""
        
        self.prometheus.record_celery_task(task_name, status, duration)
        
        if status == "failed":
            self.sentry.capture_message(
                f"Celery task failed: {task_name}",
                level="error",
                context={"task": {"name": task_name, "status": status, "duration": duration}}
            )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get monitoring system health status"""
        uptime = time.time() - self.start_time
        
        return {
            "monitoring": {
                "prometheus_available": PROMETHEUS_AVAILABLE,
                "sentry_available": SENTRY_AVAILABLE,
                "sentry_initialized": self.sentry.initialized,
                "uptime_seconds": uptime
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics"""
        return self.prometheus.get_metrics()

# Global monitoring instance
monitoring_service = MonitoringService()

def monitor_endpoint(endpoint_name: Optional[str] = None):
    """Decorator to monitor endpoint performance"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = getattr(e, 'status_code', 500)
                monitoring_service.record_error(e, context={"endpoint": endpoint_name or func.__name__})
                raise
            finally:
                duration = time.time() - start_time
                name = endpoint_name or func.__name__
                monitoring_service.record_request("", name, status_code, duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = getattr(e, 'status_code', 500)
                monitoring_service.record_error(e, context={"endpoint": endpoint_name or func.__name__})
                raise
            finally:
                duration = time.time() - start_time
                name = endpoint_name or func.__name__
                monitoring_service.record_request("", name, status_code, duration)
        
        import asyncio
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def monitor_task(task_name: Optional[str] = None):
    """Decorator to monitor Celery task performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            name = task_name or func.__name__
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                monitoring_service.record_task_completion(name, "success", duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                monitoring_service.record_task_completion(name, "failed", duration)
                monitoring_service.record_error(e, context={"task": name})
                raise
        
        return wrapper
    return decorator