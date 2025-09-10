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
        
        # OAuth Token Refresh Metrics (P1-4b)
        self.oauth_token_refresh_total = Counter(
            'oauth_token_refresh_total',
            'Total OAuth token refresh operations',
            ['platform', 'success', 'organization_id'],
            registry=self.registry
        )
        
        self.oauth_token_refresh_duration_seconds = Histogram(
            'oauth_token_refresh_duration_seconds',
            'OAuth token refresh operation duration in seconds',
            ['platform'],
            registry=self.registry
        )
        
        # Webhook Validation Metrics (P1-4c)
        self.webhook_validations_total = Counter(
            'webhook_validations_total',
            'Total webhook signature validations',
            ['platform', 'result', 'threat_level'],
            registry=self.registry
        )
        
        self.webhook_validation_duration_seconds = Histogram(
            'webhook_validation_duration_seconds',
            'Webhook signature validation duration in seconds',
            ['platform'],
            registry=self.registry
        )
        
        self.webhook_threats_total = Counter(
            'webhook_threats_total',
            'Total webhook security threats detected',
            ['platform', 'threat_type'],
            registry=self.registry
        )
        
        self.webhook_delivery_success_rate = Gauge(
            'webhook_delivery_success_rate',
            'Current webhook delivery success rate percentage',
            ['platform'],
            registry=self.registry
        )
        
        # Embedding Validation Metrics (P1-7a)
        self.embedding_validations_total = Counter(
            'embedding_validations_total',
            'Total embedding validation attempts',
            ['result', 'dimension'],
            registry=self.registry
        )
        
        self.embedding_validation_duration_seconds = Histogram(
            'embedding_validation_duration_seconds',
            'Embedding validation duration in seconds',
            registry=self.registry
        )
        
        self.embedding_dimension_mismatches_total = Counter(
            'embedding_dimension_mismatches_total',
            'Total embedding dimension mismatches',
            ['expected_dimension', 'actual_dimension'],
            registry=self.registry
        )
        
        # Vector Store Performance Metrics (P1-7b)
        self.vector_store_operations_total = Counter(
            'vector_store_operations_total',
            'Total vector store operations',
            ['operation', 'success'],
            registry=self.registry
        )
        
        self.vector_store_operation_duration_seconds = Histogram(
            'vector_store_operation_duration_seconds',
            'Vector store operation duration in seconds',
            ['operation'],
            registry=self.registry
        )
        
        self.vector_store_memory_usage_mb = Gauge(
            'vector_store_memory_usage_mb',
            'Vector store memory usage in MB',
            registry=self.registry
        )
        
        self.vector_store_index_size_vectors = Gauge(
            'vector_store_index_size_vectors',
            'Number of vectors in the index',
            registry=self.registry
        )
        
        # Storage Growth Monitoring (P1-7d)
        self.vector_store_memory_usage_bytes = Gauge(
            'vector_store_memory_usage_bytes',
            'Memory usage of vector store in bytes',
            ['component'],
            registry=self.registry
        )
        
        self.vector_store_disk_usage_bytes = Gauge(
            'vector_store_disk_usage_bytes',
            'Disk usage of vector store in bytes',
            ['component', 'file_type'],
            registry=self.registry
        )
        
        self.vector_store_growth_rate = Gauge(
            'vector_store_growth_rate_vectors_per_hour',
            'Rate of vector additions per hour',
            registry=self.registry
        )
        
        # Index Performance Monitoring (P1-7d)  
        self.vector_store_fragmentation_ratio = Gauge(
            'vector_store_fragmentation_ratio',
            'Index fragmentation ratio (0-1, higher is more fragmented)',
            registry=self.registry
        )
        
        self.vector_store_rebuild_frequency = Counter(
            'vector_store_rebuild_operations_total',
            'Total vector store rebuild operations',
            ['trigger_reason'],
            registry=self.registry
        )
        
        self.vector_store_search_accuracy = Histogram(
            'vector_store_search_accuracy_score',
            'Search result accuracy scores',
            buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.98, 1.0],
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
        
        # P0-11a: Missing Prometheus Metrics for Plan Limits, Webhooks, and Quality
        
        # Plan Limit Enforcement Metrics (4 metrics)
        self.plan_limit_checks_total = Counter(
            'plan_limit_checks_total',
            'Total plan limit checks performed',
            ['plan_type', 'feature', 'result'],
            registry=self.registry
        )
        
        self.plan_limit_violations_total = Counter(
            'plan_limit_violations_total',
            'Total plan limit violations blocked',
            ['plan_type', 'feature', 'violation_type'],
            registry=self.registry
        )
        
        self.plan_quota_usage_percent = Histogram(
            'plan_quota_usage_percent',
            'Current plan quota usage as percentage',
            ['plan_type', 'feature'],
            buckets=[10, 25, 50, 75, 90, 95, 98, 99, 100],
            registry=self.registry
        )
        
        self.plan_upgrade_suggestions_total = Counter(
            'plan_upgrade_suggestions_total',
            'Total plan upgrade suggestions shown to users',
            ['current_plan', 'suggested_plan', 'trigger'],
            registry=self.registry
        )
        
# Duplicate webhook metrics removed - using P1-4c section metrics instead
        
        # Image Quality Monitoring Metrics (4 metrics) 
        self.image_quality_scores_distribution = Histogram(
            'image_quality_scores_distribution',
            'Distribution of image quality scores',
            ['model', 'platform', 'quality_preset'],
            buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 98, 100],
            registry=self.registry
        )
        
        self.image_quality_threshold_breaches_total = Counter(
            'image_quality_threshold_breaches_total',
            'Total image quality threshold breaches',
            ['model', 'platform', 'threshold_type'],
            registry=self.registry
        )
        
        self.image_fallback_generations_total = Counter(
            'image_fallback_generations_total',
            'Total text-only fallbacks due to poor image quality',
            ['model', 'platform', 'fallback_reason'],
            registry=self.registry
        )
        
        self.image_regeneration_requests_total = Counter(
            'image_regeneration_requests_total',
            'Total image regeneration requests due to quality issues',
            ['model', 'platform', 'retry_reason'],
            registry=self.registry
        )
        
        logger.info("Prometheus metrics initialized successfully with P0-11a plan limits, webhooks, and quality metrics")
    
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
    
    def record_oauth_refresh(self, platform: str, success: bool, duration_seconds: float, organization_id: str):
        """Record OAuth token refresh operation (P1-4b)"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        # Record total count with success/failure
        self.oauth_token_refresh_total.labels(
            platform=platform,
            success=str(success).lower(),
            organization_id=organization_id
        ).inc()
        
        # Record duration
        self.oauth_token_refresh_duration_seconds.labels(platform=platform).observe(duration_seconds)
    
    def record_webhook_validation(self, platform: str, result: str, threat_level: str):
        """Record webhook signature validation (P1-4c)"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.webhook_validations_total.labels(
            platform=platform,
            result=result,
            threat_level=threat_level
        ).inc()
    
    def record_webhook_validation_time(self, platform: str, duration_seconds: float):
        """Record webhook validation duration (P1-4c)"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.webhook_validation_duration_seconds.labels(platform=platform).observe(duration_seconds)
    
    def record_webhook_threat(self, platform: str, threat_type: str):
        """Record webhook security threat (P1-4c)"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.webhook_threats_total.labels(
            platform=platform,
            threat_type=threat_type
        ).inc()
    
    def record_embedding_validation(self, is_valid: bool, dimension: int, duration_seconds: float):
        """Record embedding validation result (P1-7a)"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        result = "valid" if is_valid else "invalid"
        self.embedding_validations_total.labels(
            result=result,
            dimension=str(dimension)
        ).inc()
        
        self.embedding_validation_duration_seconds.observe(duration_seconds)
    
    def record_embedding_dimension_mismatch(self, expected_dimension: int, actual_dimension: int):
        """Record embedding dimension mismatch (P1-7a)"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.embedding_dimension_mismatches_total.labels(
            expected_dimension=str(expected_dimension),
            actual_dimension=str(actual_dimension)
        ).inc()
    
    def record_vector_store_operation(self, operation: str, success: bool, duration_seconds: float, vector_count: int):
        """Record vector store operation (P1-7b)"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        # Record operation count
        self.vector_store_operations_total.labels(
            operation=operation,
            success=str(success).lower()
        ).inc()
        
        # Record operation duration
        self.vector_store_operation_duration_seconds.labels(
            operation=operation
        ).observe(duration_seconds)
    
    def record_vector_store_memory_usage(self, memory_mb: float):
        """Record vector store memory usage (P1-7b)"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.vector_store_memory_usage_mb.set(memory_mb)
    
    def record_vector_store_index_size(self, size_vectors: int):
        """Record vector store index size (P1-7b)"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.vector_store_index_size_vectors.set(size_vectors)
    
    # Storage Growth Monitoring Methods (P1-7d)
    def record_vector_store_memory_usage(self, component: str, memory_bytes: int):
        """Record vector store memory usage by component"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.vector_store_memory_usage_bytes.labels(component=component).set(memory_bytes)
    
    def record_vector_store_disk_usage(self, component: str, file_type: str, disk_bytes: int):
        """Record vector store disk usage by component and file type"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.vector_store_disk_usage_bytes.labels(
            component=component,
            file_type=file_type
        ).set(disk_bytes)
    
    def record_vector_store_growth_rate(self, vectors_per_hour: float):
        """Record vector store growth rate"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.vector_store_growth_rate.set(vectors_per_hour)
    
    # Index Performance Monitoring Methods (P1-7d)
    def record_vector_store_fragmentation(self, fragmentation_ratio: float):
        """Record vector store index fragmentation ratio"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.vector_store_fragmentation_ratio.set(fragmentation_ratio)
    
    def record_vector_store_rebuild(self, trigger_reason: str):
        """Record vector store rebuild operation"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.vector_store_rebuild_frequency.labels(trigger_reason=trigger_reason).inc()
    
    def record_vector_store_search_accuracy(self, accuracy_score: float):
        """Record search result accuracy score"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.vector_store_search_accuracy.observe(accuracy_score)
    
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
    
    # P0-11a: Methods for recording plan limits, webhooks, and quality metrics
    
    def record_plan_limit_check(self, plan_type: str, feature: str, result: str):
        """Record plan limit check"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.plan_limit_checks_total.labels(
            plan_type=plan_type,
            feature=feature,
            result=result
        ).inc()
    
    def record_plan_limit_violation(self, plan_type: str, feature: str, violation_type: str):
        """Record plan limit violation"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.plan_limit_violations_total.labels(
            plan_type=plan_type,
            feature=feature,
            violation_type=violation_type
        ).inc()
    
    def record_plan_quota_usage(self, plan_type: str, feature: str, usage_percent: float):
        """Record plan quota usage percentage"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.plan_quota_usage_percent.labels(
            plan_type=plan_type,
            feature=feature
        ).observe(usage_percent)
    
    def record_plan_upgrade_suggestion(self, current_plan: str, suggested_plan: str, trigger: str):
        """Record plan upgrade suggestion shown to user"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.plan_upgrade_suggestions_total.labels(
            current_plan=current_plan,
            suggested_plan=suggested_plan,
            trigger=trigger
        ).inc()
    
    def record_webhook_validation(self, platform: str, result: str, threat_level: str):
        """Record webhook signature validation"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.webhook_validations_total.labels(
            platform=platform,
            result=result,
            threat_level=threat_level
        ).inc()
    
    def record_webhook_validation_time(self, platform: str, duration_seconds: float):
        """Record webhook validation duration"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.webhook_validation_duration_seconds.labels(platform=platform).observe(duration_seconds)
    
    def record_webhook_threat_detected(self, platform: str, threat_type: str):
        """Record webhook security threat detected (duplicate method - use record_webhook_threat instead)"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.webhook_threats_total.labels(
            platform=platform,
            threat_type=threat_type
        ).inc()
    
    def update_webhook_success_rate(self, platform: str, success_rate: float):
        """Update webhook delivery success rate"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.webhook_delivery_success_rate.labels(platform=platform).set(success_rate)
    
    def record_image_quality_score(self, model: str, platform: str, quality_preset: str, score: float):
        """Record image quality score"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.image_quality_scores_distribution.labels(
            model=model,
            platform=platform,
            quality_preset=quality_preset
        ).observe(score)
    
    def record_image_quality_breach(self, model: str, platform: str, threshold_type: str):
        """Record image quality threshold breach"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.image_quality_threshold_breaches_total.labels(
            model=model,
            platform=platform,
            threshold_type=threshold_type
        ).inc()
    
    def record_image_fallback(self, model: str, platform: str, fallback_reason: str):
        """Record image fallback to text-only"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.image_fallback_generations_total.labels(
            model=model,
            platform=platform,
            fallback_reason=fallback_reason
        ).inc()
    
    def record_image_regeneration(self, model: str, platform: str, retry_reason: str):
        """Record image regeneration request"""
        if not PROMETHEUS_AVAILABLE:
            return
        self.image_regeneration_requests_total.labels(
            model=model,
            platform=platform,
            retry_reason=retry_reason
        ).inc()
    
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