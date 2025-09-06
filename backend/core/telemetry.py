"""
OpenTelemetry tracing and metrics configuration for production observability
"""
import os
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Optional OpenTelemetry imports with fallbacks
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.b3 import B3MultiFormat
    from opentelemetry.propagators.jaeger import JaegerPropagator
    from opentelemetry.propagators.composite import CompositePropagator
    
    OPENTELEMETRY_AVAILABLE = True
    logger.info("OpenTelemetry libraries imported successfully")
    
except ImportError as e:
    logger.warning(f"OpenTelemetry libraries not available: {e}")
    OPENTELEMETRY_AVAILABLE = False
    
    # Fallback classes for when OpenTelemetry is not available
    class MockTracer:
        def start_as_current_span(self, name, context=None, kind=None):
            return MockSpan()
    
    class MockSpan:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def set_attributes(self, attributes):
            pass
        def record_exception(self, exception):
            pass
        def set_status(self, status):
            pass
        def get_span_context(self):
            return MockSpanContext()
    
    class MockSpanContext:
        def __init__(self):
            self.trace_id = 0
            self.span_id = 0
    
    class MockMeter:
        def create_counter(self, name, description="", unit=""):
            return MockMetric()
        def create_histogram(self, name, description="", unit=""):
            return MockMetric()
        def create_observable_gauge(self, name, description="", unit=""):
            return MockMetric()
    
    class MockMetric:
        def add(self, value, attributes=None):
            pass
        def record(self, value, attributes=None):
            pass
    
    # Mock classes for missing OpenTelemetry components
    TracerProvider = None
    MeterProvider = None
    Resource = None
    trace = None
    metrics = None

class TelemetryManager:
    """
    Centralized telemetry management for OpenTelemetry tracing and metrics
    """
    
    def __init__(self):
        self.tracer_provider: Optional[TracerProvider] = None
        self.meter_provider: Optional[MeterProvider] = None
        self.tracer = None
        self.meter = None
        self.enabled = os.getenv('OTEL_ENABLED', 'false').lower() == 'true'
        self.service_name = os.getenv('OTEL_SERVICE_NAME', 'lily-media-api')
        self.service_version = os.getenv('OTEL_SERVICE_VERSION', '1.0.0')
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
    def initialize(self, app=None) -> bool:
        """
        Initialize OpenTelemetry tracing and metrics
        
        Returns:
            bool: True if telemetry was successfully initialized
        """
        if not self.enabled:
            logger.info("OpenTelemetry telemetry disabled")
            return False
            
        if not OPENTELEMETRY_AVAILABLE:
            logger.warning("OpenTelemetry libraries not available - using mock implementations")
            self.tracer = MockTracer()
            self.meter = MockMeter()
            return True
            
        try:
            # Create resource with service metadata
            resource = Resource.create({
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: self.service_version,
                "environment": self.environment,
                "deployment.platform": "render",
            })
            
            # Initialize tracing
            self._setup_tracing(resource)
            
            # Initialize metrics
            self._setup_metrics(resource)
            
            # Setup propagation
            self._setup_propagation()
            
            # Auto-instrument libraries
            self._setup_auto_instrumentation(app)
            
            logger.info(f"OpenTelemetry initialized successfully for {self.service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")
            # Fallback to mock implementations
            self.tracer = MockTracer()
            self.meter = MockMeter()
            return True
    
    def _setup_tracing(self, resource: Resource):
        """Setup distributed tracing with OTLP and Jaeger exporters"""
        self.tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(self.tracer_provider)
        
        # OTLP exporter for production observability platforms
        otlp_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=f"{otlp_endpoint}/v1/traces",
                headers=self._get_otlp_headers(),
            )
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter, max_export_batch_size=512)
            )
            logger.info(f"OTLP trace exporter configured: {otlp_endpoint}")
        
        # Jaeger exporter for development and debugging
        jaeger_endpoint = os.getenv('JAEGER_AGENT_HOST')
        if jaeger_endpoint:
            jaeger_port = int(os.getenv('JAEGER_AGENT_PORT', '6832'))
            jaeger_exporter = JaegerExporter(
                agent_host_name=jaeger_endpoint,
                agent_port=jaeger_port,
            )
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )
            logger.info(f"Jaeger trace exporter configured: {jaeger_endpoint}:{jaeger_port}")
        
        self.tracer = trace.get_tracer(__name__)
    
    def _setup_metrics(self, resource: Resource):
        """Setup metrics collection with OTLP and Prometheus exporters"""
        readers = []
        
        # OTLP metrics exporter
        otlp_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
        if otlp_endpoint:
            otlp_metric_exporter = OTLPMetricExporter(
                endpoint=f"{otlp_endpoint}/v1/metrics",
                headers=self._get_otlp_headers(),
            )
            readers.append(
                PeriodicExportingMetricReader(
                    exporter=otlp_metric_exporter,
                    export_interval_millis=30000,  # 30 seconds
                )
            )
        
        # Prometheus metrics exporter
        if os.getenv('PROMETHEUS_ENABLED', 'false').lower() == 'true':
            prometheus_port = int(os.getenv('PROMETHEUS_PORT', '8000'))
            readers.append(
                PrometheusMetricReader(port=prometheus_port)
            )
            logger.info(f"Prometheus metrics exposed on port {prometheus_port}")
        
        if readers:
            self.meter_provider = MeterProvider(
                resource=resource,
                metric_readers=readers,
            )
            metrics.set_meter_provider(self.meter_provider)
            self.meter = metrics.get_meter(__name__)
            logger.info("OpenTelemetry metrics configured")
    
    def _setup_propagation(self):
        """Setup trace context propagation for distributed tracing"""
        propagators = []
        
        # B3 propagation (Zipkin compatible)
        propagators.append(B3MultiFormat())
        
        # Jaeger propagation
        if os.getenv('JAEGER_AGENT_HOST'):
            propagators.append(JaegerPropagator())
        
        if propagators:
            set_global_textmap(CompositePropagator(propagators))
            logger.info("Trace propagation configured")
    
    def _setup_auto_instrumentation(self, app=None):
        """Setup automatic instrumentation for common libraries"""
        try:
            # FastAPI instrumentation
            if app:
                FastAPIInstrumentor.instrument_app(
                    app,
                    tracer_provider=self.tracer_provider,
                    excluded_urls="health,metrics,favicon.ico",
                )
                logger.info("FastAPI auto-instrumentation enabled")
            
            # SQLAlchemy instrumentation
            SQLAlchemyInstrumentor().instrument(
                tracer_provider=self.tracer_provider,
                enable_commenter=True,
                commenter_options={
                    'db_framework': True,
                    'opentelemetry_values': True,
                }
            )
            logger.info("SQLAlchemy auto-instrumentation enabled")
            
            # Redis instrumentation
            RedisInstrumentor().instrument(
                tracer_provider=self.tracer_provider,
            )
            logger.info("Redis auto-instrumentation enabled")
            
            # Requests instrumentation for HTTP clients
            RequestsInstrumentor().instrument(
                tracer_provider=self.tracer_provider,
            )
            logger.info("Requests auto-instrumentation enabled")
            
            # Celery instrumentation for background tasks
            CeleryInstrumentor().instrument(
                tracer_provider=self.tracer_provider,
            )
            logger.info("Celery auto-instrumentation enabled")
            
        except Exception as e:
            logger.error(f"Error setting up auto-instrumentation: {e}")
    
    def _get_otlp_headers(self) -> Dict[str, str]:
        """Get OTLP headers for authentication"""
        headers = {}
        
        # Common OTLP authentication patterns
        api_key = os.getenv('OTEL_API_KEY')
        if api_key:
            headers['x-api-key'] = api_key
            
        auth_token = os.getenv('OTEL_AUTH_TOKEN')
        if auth_token:
            headers['authorization'] = f"Bearer {auth_token}"
            
        return headers
    
    @contextmanager
    def trace_operation(self, operation_name: str, attributes: Dict[str, Any] = None):
        """
        Context manager for manual tracing of operations
        
        Args:
            operation_name: Name of the operation being traced
            attributes: Additional attributes to add to the span
        """
        if not self.tracer:
            yield None
            return
            
        with self.tracer.start_as_current_span(operation_name) as span:
            if attributes:
                span.set_attributes(attributes)
            
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
    
    def create_counter(self, name: str, description: str = "", unit: str = ""):
        """Create a counter metric"""
        if not self.meter:
            return None
        return self.meter.create_counter(name, description, unit)
    
    def create_histogram(self, name: str, description: str = "", unit: str = ""):
        """Create a histogram metric"""
        if not self.meter:
            return None
        return self.meter.create_histogram(name, description, unit)
    
    def create_gauge(self, name: str, description: str = "", unit: str = ""):
        """Create a gauge metric"""
        if not self.meter:
            return None
        return self.meter.create_observable_gauge(name, description, unit)
    
    def shutdown(self):
        """Shutdown telemetry providers gracefully"""
        try:
            if self.tracer_provider:
                self.tracer_provider.shutdown()
            if self.meter_provider:
                self.meter_provider.shutdown()
            logger.info("OpenTelemetry shutdown completed")
        except Exception as e:
            logger.error(f"Error during telemetry shutdown: {e}")

# Global telemetry manager instance
telemetry_manager = TelemetryManager()

# Convenience functions for common operations
def trace_operation(operation_name: str, attributes: Dict[str, Any] = None):
    """Decorator and context manager for tracing operations"""
    return telemetry_manager.trace_operation(operation_name, attributes)

def get_tracer():
    """Get the configured tracer"""
    return telemetry_manager.tracer

def get_meter():
    """Get the configured meter"""
    return telemetry_manager.meter