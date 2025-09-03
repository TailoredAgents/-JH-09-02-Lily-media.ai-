"""
Error tracking middleware for automatic error logging
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import time
import traceback
import logging
from typing import Callable
import json

logger = logging.getLogger(__name__)

async def error_tracking_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware to track all errors and performance"""
    start_time = time.time()
    
    # Get request details
    request_info = {
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "query": dict(request.query_params),
        "headers": dict(request.headers),
        "client": request.client.host if request.client else None
    }
    
    # Skip body for file uploads
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.body()
            if body:
                request_info["body"] = json.loads(body)
        except Exception as parse_err:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug("Failed to parse request body in error tracker", 
                        exc_info=parse_err)
    
    try:
        # Process request
        response = await call_next(request)
        
        # Ensure we got a valid response
        if response is None:
            logger.error(f"No response returned from call_next for {request.method} {request.url.path}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "No response generated",
                    "path": request.url.path
                }
            )
        
        # Log slow requests
        process_time = time.time() - start_time
        if process_time > 1.0:  # Log requests taking more than 1 second
            logger.warning(
                f"Slow request: {request.method} {request.url.path} took {process_time:.2f}s",
                extra={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "duration": process_time,
                    "status_code": getattr(response, 'status_code', 'unknown')
                }
            )
        
        # Log errors (4xx and 5xx)
        if hasattr(response, 'status_code') and response.status_code >= 400:
            logger.error(
                f"Request failed: {request.method} {request.url.path} - Status {response.status_code}",
                extra={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "request_info": request_info,
                    "duration": process_time
                }
            )
        
        return response
        
    except Exception as e:
        # Log unhandled exceptions
        process_time = time.time() - start_time
        
        logger.error(
            f"Unhandled exception: {request.method} {request.url.path}",
            exc_info=True,
            extra={
                "endpoint": request.url.path,
                "method": request.method,
                "request_info": request_info,
                "duration": process_time,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        
        # Return error response
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(e) if logger.level <= logging.DEBUG else "An unexpected error occurred",
                "request_id": request_info.get("headers", {}).get("x-request-id"),
                "path": request.url.path
            }
        )

async def log_404_errors(request: Request, call_next: Callable) -> Response:
    """Special middleware to log 404 errors with suggestions"""
    try:
        response = await call_next(request)
        
        # Ensure we got a valid response
        if response is None:
            logger.error(f"No response returned from call_next in 404 middleware for {request.method} {request.url.path}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error", 
                    "message": "No response generated",
                    "path": request.url.path
                }
            )
    except Exception as e:
        logger.error(f"Exception in 404 middleware for {request.method} {request.url.path}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "Error in 404 middleware", 
                "path": request.url.path
            }
        )
    
    if hasattr(response, 'status_code') and response.status_code == 404:
        # Log 404 with helpful context
        from backend.api.system_logs import error_store
        
        error_data = {
            "endpoint": request.url.path,
            "method": request.method,
            "severity": "warning",
            "error_type": "NotFound",
            "error_message": f"Endpoint not found: {request.method} {request.url.path}",
            "client": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "referer": request.headers.get("referer")
        }
        
        # Add suggestions for common mistakes
        path = request.url.path
        suggestions = []
        
        if path.startswith("/api/"):
            if "notification" in path and not path.endswith("/"):
                suggestions.append(f"Try: {path}/")
            if path.endswith("//"):
                suggestions.append(f"Try: {path.rstrip('/')}/")
            if "/metrics" in path and not "/api/metrics" in path:
                suggestions.append("Try: /api/system/logs/stats for metrics")
                
        if suggestions:
            error_data["suggestions"] = suggestions
            
        error_store.add_warning(error_data)
    
    return response