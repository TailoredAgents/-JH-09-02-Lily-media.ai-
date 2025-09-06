"""
Enhanced observability middleware with custom metrics and tracing
"""
import time
import logging
from typing import Callable, Dict, Any
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.telemetry import telemetry_manager, get_tracer, get_meter, OPENTELEMETRY_AVAILABLE

# Optional OpenTelemetry imports
if OPENTELEMETRY_AVAILABLE:
    try:
        from opentelemetry import trace, metrics
        from opentelemetry.trace import Status, StatusCode
        from opentelemetry.propagate import extract
    except ImportError:
        OPENTELEMETRY_AVAILABLE = False

# Mock implementations for when OpenTelemetry is not available
if not OPENTELEMETRY_AVAILABLE:
    class MockStatus:
        def __init__(self, status_code, description=""):
            self.status_code = status_code
            self.description = description
    
    class MockStatusCode:
        OK = "OK"
        ERROR = "ERROR"
    
    def extract(headers):
        return None
    
    trace = None
    metrics = None
    Status = MockStatus
    StatusCode = MockStatusCode

logger = logging.getLogger(__name__)

class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced middleware for detailed observability with OpenTelemetry
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.tracer = get_tracer()
        self.meter = get_meter()
        
        # Initialize metrics
        self._setup_metrics()
        
    def _setup_metrics(self):
        """Setup custom business metrics"""
        if not self.meter:
            self.request_counter = None
            self.request_duration = None
            self.active_connections = None
            self.error_counter = None
            self.business_metrics = {}
            return
            
        # HTTP request metrics
        self.request_counter = self.meter.create_counter(
            name="http_requests_total",
            description="Total number of HTTP requests",
            unit="request"
        )
        
        self.request_duration = self.meter.create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s"
        )
        
        self.active_connections = self.meter.create_up_down_counter(
            name="http_active_connections",
            description="Number of active HTTP connections",
            unit="connection"
        )
        
        self.error_counter = self.meter.create_counter(
            name="http_errors_total",
            description="Total number of HTTP errors",
            unit="error"
        )
        
        # Business metrics
        self.business_metrics = {
            'user_registrations': self.meter.create_counter(
                name="user_registrations_total",
                description="Total number of user registrations",
                unit="registration"
            ),
            'oauth_connections': self.meter.create_counter(
                name="oauth_connections_total", 
                description="Total number of OAuth connections",
                unit="connection"
            ),
            'content_generations': self.meter.create_counter(
                name="content_generations_total",
                description="Total number of content generations",
                unit="generation"
            ),
            'api_rate_limits': self.meter.create_counter(
                name="api_rate_limits_total",
                description="Total number of API rate limit hits",
                unit="limit"
            ),
            'webhook_events': self.meter.create_counter(
                name="webhook_events_total",
                description="Total number of webhook events processed",
                unit="event"
            ),
            'database_connections': self.meter.create_histogram(
                name="database_connection_duration_seconds",
                description="Database connection duration",
                unit="s"
            ),
            'redis_operations': self.meter.create_histogram(
                name="redis_operation_duration_seconds", 
                description="Redis operation duration",
                unit="s"
            ),
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with enhanced observability"""
        start_time = time.time()
        request_id = str(uuid4())
        
        # Add request ID to context
        request.state.request_id = request_id
        
        # Extract distributed trace context
        context = extract(request.headers)
        
        # Start tracing span
        if self.tracer and OPENTELEMETRY_AVAILABLE and trace and hasattr(trace, 'SpanKind'):
            with self.tracer.start_as_current_span(
                f"{request.method} {request.url.path}",
                context=context,
                kind=trace.SpanKind.SERVER
            ) as span:
                return await self._process_request_with_span(
                    request, call_next, start_time, request_id, span
                )
        elif self.tracer:
            with self.tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
                return await self._process_request_with_span(
                    request, call_next, start_time, request_id, span
                )
        else:
            return await self._process_request_without_span(
                request, call_next, start_time, request_id
            )
    
    async def _process_request_with_span(
        self, 
        request: Request, 
        call_next: Callable, 
        start_time: float,
        request_id: str,
        span: Any  # trace.Span when available
    ) -> Response:
        """Process request with OpenTelemetry span"""
        # Add span attributes
        span.set_attributes({
            "http.method": request.method,
            "http.url": str(request.url),
            "http.path": request.url.path,
            "http.query": request.url.query or "",
            "http.user_agent": request.headers.get("user-agent", ""),
            "http.client_ip": self._get_client_ip(request),
            "request.id": request_id,
            "service.name": "lily-media-api",
        })
        
        # Add organization context if available
        if hasattr(request.state, 'current_user') and request.state.current_user:
            span.set_attributes({
                "user.id": str(request.state.current_user.id),
                "organization.id": str(getattr(request.state.current_user, 'organization_id', '')),
            })
        
        # Increment active connections
        if self.active_connections:
            self.active_connections.add(1, {"method": request.method, "path": request.url.path})
        
        try:
            response = await call_next(request)
            
            # Record successful request metrics
            duration = time.time() - start_time
            self._record_request_metrics(request, response, duration)
            
            # Update span with response info
            span.set_attributes({
                "http.status_code": response.status_code,
                "http.response_size": len(response.body) if hasattr(response, 'body') else 0,
            })
            
            # Mark span as successful
            if OPENTELEMETRY_AVAILABLE and Status and StatusCode:
                if response.status_code < 400:
                    span.set_status(Status(StatusCode.OK))
                else:
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                
            return response
            
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            self._record_error_metrics(request, e, duration)
            
            # Update span with error info
            span.record_exception(e)
            if OPENTELEMETRY_AVAILABLE and Status and StatusCode:
                span.set_status(Status(StatusCode.ERROR, str(e)))
            
            raise
        finally:
            # Decrement active connections
            if self.active_connections:
                self.active_connections.add(-1, {"method": request.method, "path": request.url.path})
    
    async def _process_request_without_span(
        self, 
        request: Request, 
        call_next: Callable, 
        start_time: float,
        request_id: str
    ) -> Response:
        """Process request without OpenTelemetry span (fallback)"""
        # Increment active connections
        if self.active_connections:
            self.active_connections.add(1, {"method": request.method, "path": request.url.path})
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            self._record_request_metrics(request, response, duration)
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_error_metrics(request, e, duration)
            raise
        finally:
            # Decrement active connections
            if self.active_connections:
                self.active_connections.add(-1, {"method": request.method, "path": request.url.path})
    
    def _record_request_metrics(self, request: Request, response: Response, duration: float):
        """Record metrics for successful requests"""
        labels = {
            "method": request.method,
            "path": self._normalize_path(request.url.path),
            "status_code": str(response.status_code),
        }
        
        if self.request_counter:
            self.request_counter.add(1, labels)
            
        if self.request_duration:
            self.request_duration.record(duration, labels)
        
        # Record business metrics based on endpoint
        self._record_business_metrics(request, response)
    
    def _record_error_metrics(self, request: Request, exception: Exception, duration: float):
        """Record metrics for failed requests"""
        labels = {
            "method": request.method,
            "path": self._normalize_path(request.url.path),
            "error_type": type(exception).__name__,
        }
        
        if self.error_counter:
            self.error_counter.add(1, labels)
            
        if self.request_duration:
            self.request_duration.record(duration, {**labels, "status_code": "error"})
    
    def _record_business_metrics(self, request: Request, response: Response):
        """Record business-specific metrics based on endpoint and response"""
        path = request.url.path
        method = request.method
        
        # User registration metrics
        if method == "POST" and "/api/register" in path and response.status_code == 201:
            if self.business_metrics.get('user_registrations'):
                self.business_metrics['user_registrations'].add(1, {"type": "new_user"})
        
        # OAuth connection metrics  
        if method == "POST" and "/api/oauth" in path and response.status_code in [200, 201]:
            if self.business_metrics.get('oauth_connections'):
                platform = self._extract_oauth_platform(path)
                self.business_metrics['oauth_connections'].add(1, {"platform": platform})
        
        # Content generation metrics
        if method == "POST" and "/api/content" in path and response.status_code in [200, 201]:
            if self.business_metrics.get('content_generations'):
                content_type = self._extract_content_type(path)
                self.business_metrics['content_generations'].add(1, {"type": content_type})
        
        # Rate limit metrics
        if response.status_code == 429:
            if self.business_metrics.get('api_rate_limits'):
                self.business_metrics['api_rate_limits'].add(1, {"endpoint": path})
        
        # Webhook metrics
        if method == "POST" and "/api/webhooks" in path and response.status_code == 200:
            if self.business_metrics.get('webhook_events'):
                platform = self._extract_webhook_platform(path)
                self.business_metrics['webhook_events'].add(1, {"platform": platform})
    
    def _normalize_path(self, path: str) -> str:
        """Normalize URL path for metrics to avoid high cardinality"""
        # Replace UUIDs and IDs with placeholders
        import re
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{uuid}', path)
        path = re.sub(r'/\d+', '/{id}', path)
        return path
    
    def _extract_oauth_platform(self, path: str) -> str:
        """Extract OAuth platform from path"""
        if "meta" in path.lower():
            return "meta"
        elif "twitter" in path.lower() or "x.com" in path.lower():
            return "twitter"
        elif "linkedin" in path.lower():
            return "linkedin"
        else:
            return "unknown"
    
    def _extract_content_type(self, path: str) -> str:
        """Extract content type from path"""
        if "generate" in path:
            return "ai_generated"
        elif "schedule" in path:
            return "scheduled"
        elif "draft" in path:
            return "draft"
        else:
            return "manual"
    
    def _extract_webhook_platform(self, path: str) -> str:
        """Extract webhook platform from path"""
        if "meta" in path.lower():
            return "meta"
        elif "twitter" in path.lower():
            return "twitter"
        elif "stripe" in path.lower():
            return "stripe"
        else:
            return "unknown"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers"""
        # Check for common proxy headers
        for header in ['X-Forwarded-For', 'X-Real-IP', 'X-Client-IP']:
            if header.lower() in request.headers:
                return request.headers[header].split(',')[0].strip()
        
        # Fallback to direct client
        return getattr(request.client, 'host', 'unknown')

def setup_observability_middleware(app: FastAPI):
    """Setup observability middleware for the FastAPI app"""
    try:
        # Initialize telemetry first
        telemetry_manager.initialize(app)
        
        # Add observability middleware
        app.add_middleware(ObservabilityMiddleware)
        
        logger.info("Observability middleware configured successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup observability middleware: {e}")
        return False