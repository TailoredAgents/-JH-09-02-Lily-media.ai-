"""
Monitoring middleware for automatic metrics collection
Integrates Prometheus and Sentry monitoring into FastAPI requests
"""
import logging
import time
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from backend.core.monitoring import monitoring_service

logger = logging.getLogger(__name__)

class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect metrics for all requests
    """
    
    def __init__(self, app, skip_paths: Optional[list] = None):
        super().__init__(app)
        self.skip_paths = skip_paths or [
            "/health",
            "/docs", 
            "/openapi.json",
            "/favicon.ico",
            "/static/"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> StarletteResponse:
        """Process request and collect metrics"""
        
        # Skip monitoring for certain paths
        if any(request.url.path.startswith(skip_path) for skip_path in self.skip_paths):
            return await call_next(request)
        
        start_time = time.time()
        method = request.method
        endpoint = request.url.path
        status_code = 200
        user_id = None
        
        try:
            # Extract user ID if available
            if hasattr(request.state, 'user') and request.state.user:
                user_id = getattr(request.state.user, 'id', None)
            
            # Process request
            response: Response = await call_next(request)
            status_code = response.status_code
            
            return response
            
        except Exception as e:
            status_code = getattr(e, 'status_code', 500)
            
            # Record error in monitoring system
            monitoring_service.record_error(
                e,
                context={
                    "request": {
                        "method": method,
                        "endpoint": endpoint,
                        "user_id": user_id,
                        "headers": dict(request.headers) if hasattr(request, 'headers') else {}
                    }
                }
            )
            
            raise
            
        finally:
            # Record request metrics
            duration = time.time() - start_time
            
            try:
                monitoring_service.record_request(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    duration=duration,
                    user_id=user_id
                )
            except Exception as e:
                # Don't let monitoring failures break the application
                logger.error(f"Failed to record request metrics: {e}")

class DatabaseMonitoringMiddleware:
    """
    Database monitoring integration for SQLAlchemy
    """
    
    @staticmethod
    def setup_db_monitoring(engine):
        """Setup database query monitoring"""
        from sqlalchemy import event
        
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
            context._query_statement = statement
        
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            try:
                duration = time.time() - getattr(context, '_query_start_time', time.time())
                
                # Determine query type
                query_type = "unknown"
                statement_lower = statement.lower().strip()
                
                if statement_lower.startswith('select'):
                    query_type = "select"
                elif statement_lower.startswith('insert'):
                    query_type = "insert"
                elif statement_lower.startswith('update'):
                    query_type = "update"
                elif statement_lower.startswith('delete'):
                    query_type = "delete"
                elif statement_lower.startswith('create'):
                    query_type = "create"
                elif statement_lower.startswith('alter'):
                    query_type = "alter"
                
                # Record metrics
                monitoring_service.prometheus.record_db_query(query_type, duration)
                
                # Log slow queries
                if duration > 1.0:  # Queries slower than 1 second
                    monitoring_service.sentry.capture_message(
                        f"Slow database query detected: {duration:.2f}s",
                        level="warning",
                        context={
                            "database": {
                                "query_type": query_type,
                                "duration": duration,
                                "statement": statement[:200]  # Truncated for privacy
                            }
                        }
                    )
                    
            except Exception as e:
                logger.error(f"Failed to record database metrics: {e}")

class CeleryMonitoringIntegration:
    """
    Celery task monitoring integration
    """
    
    @staticmethod
    def setup_celery_monitoring(celery_app):
        """Setup Celery task monitoring"""
        
        @celery_app.task_prerun.connect
        def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
            """Called before task execution"""
            task._monitoring_start_time = time.time()
        
        @celery_app.task_success.connect
        def task_success_handler(sender=None, task_id=None, result=None, **kwds):
            """Called when task succeeds"""
            duration = getattr(sender, '_monitoring_start_time', None)
            if duration:
                duration = time.time() - duration
                
            monitoring_service.record_task_completion(
                task_name=sender.name,
                status="success",
                duration=duration
            )
        
        @celery_app.task_failure.connect
        def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
            """Called when task fails"""
            duration = getattr(sender, '_monitoring_start_time', None)
            if duration:
                duration = time.time() - duration
                
            monitoring_service.record_task_completion(
                task_name=sender.name,
                status="failed",
                duration=duration
            )
            
            # Record error details
            if exception:
                monitoring_service.record_error(
                    exception,
                    context={
                        "task": {
                            "name": sender.name,
                            "task_id": task_id,
                            "duration": duration
                        }
                    }
                )
        
        logger.info("Celery monitoring integration setup completed")

def setup_monitoring_middleware(app):
    """Setup all monitoring middleware and integrations"""
    
    # Add HTTP monitoring middleware
    app.add_middleware(MonitoringMiddleware)
    
    logger.info("Monitoring middleware setup completed")
    
    return app