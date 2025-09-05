"""
Observability Integration for Production Monitoring
2025 Best Practices: Prometheus metrics + Sentry error tracking

This module provides:
- Prometheus metrics instrumentation 
- Sentry error tracking and performance monitoring
- Custom metrics endpoint not exposed in OpenAPI
- Production-ready observability for autonomous social media AI
"""
import os
import logging
from typing import Optional
from contextlib import asynccontextmanager

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge, Info
from starlette.responses import Response
import prometheus_client

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Custom Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint', 'status']
)

ACTIVE_CONNECTIONS = Gauge(
    'http_active_connections',
    'Number of active HTTP connections'
)

AI_GENERATION_REQUESTS = Counter(
    'ai_content_generation_requests_total',
    'Total AI content generation requests',
    ['type', 'platform', 'status']
)

AI_GENERATION_LATENCY = Histogram(
    'ai_content_generation_duration_seconds',
    'AI content generation latency in seconds',
    ['type', 'platform']
)

SOCIAL_PLATFORM_POSTS = Counter(
    'social_platform_posts_total',
    'Total posts to social platforms',
    ['platform', 'status']
)

AUTONOMOUS_CYCLES = Counter(
    'autonomous_posting_cycles_total',
    'Total autonomous posting cycles',
    ['status']
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections_active',
    'Active database connections'
)

REDIS_OPERATIONS = Counter(
    'redis_operations_total',
    'Total Redis operations',
    ['operation', 'status']
)

# Application info
APP_INFO = Info('app_info', 'Application information')


class PrometheusResponse(Response):
    """Custom response class for Prometheus metrics that doesn't appear in OpenAPI spec"""
    media_type = prometheus_client.CONTENT_TYPE_LATEST


class ObservabilityManager:
    """Manages all observability components for the application"""
    
    def __init__(self):
        self.instrumentator: Optional[Instrumentator] = None
        self.sentry_initialized = False
        
    def initialize_sentry(self, environment: str = "production") -> bool:
        """Initialize Sentry error tracking and performance monitoring"""
        try:
            sentry_dsn = os.getenv("SENTRY_DSN")
            if not sentry_dsn:
                logger.info("SENTRY_DSN not configured, skipping Sentry initialization")
                return False
            
            # Determine sample rates based on environment
            if environment == "development":
                traces_sample_rate = 1.0  # 100% in development
                profiles_sample_rate = 1.0
            else:
                traces_sample_rate = 0.1  # 10% in production
                profiles_sample_rate = 0.1
            
            # Configure integrations for comprehensive monitoring
            integrations = [
                FastApiIntegration(
                    transaction_style="endpoint",
                    failed_request_status_codes={403, *range(500, 599)},
                    http_methods_to_capture=("GET", "POST", "PUT", "DELETE", "PATCH"),
                ),
                StarletteIntegration(
                    transaction_style="endpoint",
                    failed_request_status_codes={403, *range(500, 599)},
                    http_methods_to_capture=("GET", "POST", "PUT", "DELETE", "PATCH"),
                ),
                SqlalchemyIntegration(),
                RedisIntegration(),
                CeleryIntegration(
                    monitor_beat_tasks=True,
                    propagate_traces=True,
                ),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR
                )
            ]
            
            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=environment,
                release=f"socialmedia-ai@{settings.api_version}",
                
                # Performance monitoring
                traces_sample_rate=traces_sample_rate,
                profiles_sample_rate=profiles_sample_rate,
                
                # Error tracking
                send_default_pii=False,  # Don't send sensitive data
                attach_stacktrace=True,
                
                # Integrations
                integrations=integrations,
                
                # Custom tags
                before_send=self._filter_sentry_events,
            )
            
            # Set custom context
            sentry_sdk.set_tag("service", "autonomous-social-media")
            sentry_sdk.set_tag("component", "fastapi-backend")
            
            self.sentry_initialized = True
            logger.info(f"Sentry initialized for {environment} environment")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
            return False
    
    def _filter_sentry_events(self, event, hint):
        """Filter sensitive information from Sentry events"""
        # Remove sensitive headers
        if 'request' in event and 'headers' in event['request']:
            sensitive_headers = ['authorization', 'cookie', 'x-api-key']
            headers = event['request']['headers']
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = '[Filtered]'
        
        # Filter out health check 404s
        if event.get('transaction') in ['/health', '/render-health', '/metrics']:
            return None
            
        return event
    
    def initialize_prometheus(self, app, environment: str = "production") -> bool:
        """Initialize Prometheus metrics instrumentation"""
        try:
            # Create instrumentator with custom configuration
            self.instrumentator = Instrumentator(
                should_group_status_codes=True,
                should_ignore_untemplated=True,
                should_respect_env_var=True,
                should_instrument_requests_inprogress=True,
                excluded_handlers=["/metrics", "/health", "/render-health"],
                env_var_name="ENABLE_METRICS",
                inprogress_name="http_requests_inprogress",
                inprogress_labels=True,
            )
            
            # Add custom metrics
            self.instrumentator.add(
                self._track_custom_metrics()
            )
            
            # Instrument the app
            self.instrumentator.instrument(app)
            
            # Expose metrics endpoint with custom response class (not in OpenAPI)
            self.instrumentator.expose(
                app,
                endpoint="/metrics", 
                response_class=PrometheusResponse,
                include_in_schema=False,  # Critical: exclude from OpenAPI spec
                tags=[]  # No tags to avoid OpenAPI documentation
            )
            
            # Set application info
            APP_INFO.info({
                'version': settings.api_version,
                'environment': environment,
                'service': 'autonomous-social-media-ai'
            })
            
            logger.info(f"Prometheus metrics initialized for {environment} environment")
            logger.info("Metrics endpoint: /metrics (excluded from OpenAPI)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Prometheus: {e}")
            return False
    
    def _track_custom_metrics(self):
        """Custom metrics tracking function"""
        def instrumentation(info):
            # Track request counts and latency
            REQUEST_COUNT.labels(
                method=info.method,
                endpoint=info.modified_handler,
                status=info.response.status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=info.method,
                endpoint=info.modified_handler,
                status=info.response.status_code
            ).observe(info.modified_duration)
            
        return instrumentation
    
    def track_ai_generation(self, content_type: str, platform: str, status: str, duration: float):
        """Track AI content generation metrics"""
        AI_GENERATION_REQUESTS.labels(
            type=content_type,
            platform=platform, 
            status=status
        ).inc()
        
        if duration > 0:
            AI_GENERATION_LATENCY.labels(
                type=content_type,
                platform=platform
            ).observe(duration)
    
    def track_social_post(self, platform: str, status: str):
        """Track social media posting metrics"""
        SOCIAL_PLATFORM_POSTS.labels(
            platform=platform,
            status=status
        ).inc()
    
    def track_autonomous_cycle(self, status: str):
        """Track autonomous posting cycle metrics"""
        AUTONOMOUS_CYCLES.labels(status=status).inc()
    
    def track_database_connections(self, count: int):
        """Track active database connections"""
        DATABASE_CONNECTIONS.set(count)
    
    def track_redis_operation(self, operation: str, status: str):
        """Track Redis operations"""
        REDIS_OPERATIONS.labels(
            operation=operation,
            status=status
        ).inc()
    
    def set_active_connections(self, count: int):
        """Set current active HTTP connections"""
        ACTIVE_CONNECTIONS.set(count)
    
    def add_sentry_breadcrumb(self, message: str, category: str = "info", level: str = "info", data: dict = None):
        """Add breadcrumb to Sentry for debugging context"""
        if self.sentry_initialized:
            sentry_sdk.add_breadcrumb(
                message=message,
                category=category,
                level=level,
                data=data or {}
            )
    
    def capture_exception(self, exception: Exception, extra_context: dict = None):
        """Capture exception with Sentry"""
        if self.sentry_initialized:
            with sentry_sdk.push_scope() as scope:
                if extra_context:
                    for key, value in extra_context.items():
                        scope.set_extra(key, value)
                sentry_sdk.capture_exception(exception)
    
    def capture_message(self, message: str, level: str = "info", extra_context: dict = None):
        """Capture message with Sentry"""
        if self.sentry_initialized:
            with sentry_sdk.push_scope() as scope:
                if extra_context:
                    for key, value in extra_context.items():
                        scope.set_extra(key, value)
                sentry_sdk.capture_message(message, level=level)


# Global observability manager instance
observability = ObservabilityManager()


@asynccontextmanager
async def setup_observability(app, environment: str = "production"):
    """
    Async context manager for observability setup using 2025 lifespan pattern
    """
    try:
        logger.info("Initializing observability components...")
        
        # Initialize Sentry
        sentry_success = observability.initialize_sentry(environment)
        
        # Initialize Prometheus
        prometheus_success = observability.initialize_prometheus(app, environment)
        
        if sentry_success or prometheus_success:
            logger.info("Observability initialization completed")
            logger.info(f"Sentry: {'✓' if sentry_success else '✗'}")
            logger.info(f"Prometheus: {'✓' if prometheus_success else '✗'}")
            
            # Add initial breadcrumb
            observability.add_sentry_breadcrumb(
                "Application started with observability",
                category="lifecycle",
                data={"environment": environment}
            )
        else:
            logger.warning("No observability components initialized")
        
        yield
        
    except Exception as e:
        logger.error(f"Observability setup failed: {e}")
        yield
    finally:
        logger.info("Observability cleanup completed")


def get_observability_manager() -> ObservabilityManager:
    """Get the global observability manager instance"""
    return observability