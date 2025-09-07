"""
Standardized Error Handling for AI Social Media Content Agent Backend

This module provides consistent error handling patterns, exception types,
and HTTP response formatting across all API endpoints and services.
"""
import logging
from typing import Dict, Any, Optional, Union, Type
from datetime import datetime, timezone
from enum import Enum

from fastapi import HTTPException, status
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standardized error codes for consistent error identification"""
    
    # Authentication & Authorization
    AUTHENTICATION_FAILED = "AUTH_001"
    INVALID_TOKEN = "AUTH_002"
    TOKEN_EXPIRED = "AUTH_003"
    INSUFFICIENT_PERMISSIONS = "AUTH_004"
    ACCOUNT_SUSPENDED = "AUTH_005"
    
    # Content Management
    CONTENT_NOT_FOUND = "CONTENT_001"
    CONTENT_VALIDATION_ERROR = "CONTENT_002"
    CONTENT_GENERATION_FAILED = "CONTENT_003"
    CONTENT_PUBLISHING_FAILED = "CONTENT_004"
    CONTENT_QUOTA_EXCEEDED = "CONTENT_005"
    
    # Memory & Vector Search
    MEMORY_STORAGE_ERROR = "MEMORY_001"
    VECTOR_SEARCH_FAILED = "MEMORY_002"
    EMBEDDING_GENERATION_FAILED = "MEMORY_003"
    FAISS_INDEX_ERROR = "MEMORY_004"
    
    # Goals & Progress
    GOAL_NOT_FOUND = "GOAL_001"
    GOAL_VALIDATION_ERROR = "GOAL_002"
    PROGRESS_TRACKING_ERROR = "GOAL_003"
    MILESTONE_UPDATE_FAILED = "GOAL_004"
    
    # Social Media Integration
    PLATFORM_API_ERROR = "SOCIAL_001"
    OAUTH_ERROR = "SOCIAL_002"
    RATE_LIMIT_EXCEEDED = "SOCIAL_003"
    PLATFORM_UNAVAILABLE = "SOCIAL_004"
    INVALID_CREDENTIALS = "SOCIAL_005"
    
    # Workflow & Automation
    WORKFLOW_EXECUTION_ERROR = "WORKFLOW_001"
    TASK_SCHEDULING_ERROR = "WORKFLOW_002"
    AUTOMATION_FAILURE = "WORKFLOW_003"
    
    # Database & Storage
    DATABASE_CONNECTION_ERROR = "DB_001"
    DATA_INTEGRITY_ERROR = "DB_002"
    TRANSACTION_FAILED = "DB_003"
    CONSTRAINT_VIOLATION = "DB_004"
    
    # External Services
    OPENAI_API_ERROR = "EXTERNAL_001"
    REDIS_CONNECTION_ERROR = "EXTERNAL_002"
    CELERY_TASK_ERROR = "EXTERNAL_003"
    
    # System & Infrastructure
    INTERNAL_SERVER_ERROR = "SYSTEM_001"
    SERVICE_UNAVAILABLE = "SYSTEM_002"
    CONFIGURATION_ERROR = "SYSTEM_003"
    RESOURCE_EXHAUSTED = "SYSTEM_004"
    
    # Validation & Input
    INVALID_INPUT = "VALIDATION_001"
    MISSING_REQUIRED_FIELD = "VALIDATION_002"
    INVALID_FORMAT = "VALIDATION_003"
    VALUE_OUT_OF_RANGE = "VALIDATION_004"


class ErrorDetail(BaseModel):
    """Structured error detail for consistent API responses"""
    code: str
    message: str
    field: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.now(timezone.utc)


class APIError(Exception):
    """Base exception class for all API errors"""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        field: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.field = field
        self.context = context or {}
        super().__init__(message)
    
    def to_detail(self) -> ErrorDetail:
        """Convert to structured error detail"""
        return ErrorDetail(
            code=self.error_code.value,
            message=self.message,
            field=self.field,
            context=self.context
        )
    
    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException"""
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_detail().dict()
        )


# Specific exception classes for common error types
class AuthenticationError(APIError):
    """Authentication-related errors"""
    def __init__(self, error_code: ErrorCode, message: str, **kwargs):
        super().__init__(error_code, message, status.HTTP_401_UNAUTHORIZED, **kwargs)


class AuthorizationError(APIError):
    """Authorization-related errors"""
    def __init__(self, error_code: ErrorCode, message: str, **kwargs):
        super().__init__(error_code, message, status.HTTP_403_FORBIDDEN, **kwargs)


class ValidationError(APIError):
    """Input validation errors"""
    def __init__(self, error_code: ErrorCode, message: str, field: str = None, **kwargs):
        super().__init__(error_code, message, status.HTTP_422_UNPROCESSABLE_ENTITY, field=field, **kwargs)


class NotFoundError(APIError):
    """Resource not found errors"""
    def __init__(self, error_code: ErrorCode, message: str, **kwargs):
        super().__init__(error_code, message, status.HTTP_404_NOT_FOUND, **kwargs)


class ConflictError(APIError):
    """Resource conflict errors"""
    def __init__(self, error_code: ErrorCode, message: str, **kwargs):
        super().__init__(error_code, message, status.HTTP_409_CONFLICT, **kwargs)


class ExternalServiceError(APIError):
    """External service integration errors"""
    def __init__(self, error_code: ErrorCode, message: str, **kwargs):
        super().__init__(error_code, message, status.HTTP_502_BAD_GATEWAY, **kwargs)


class RateLimitError(APIError):
    """Rate limiting errors"""
    def __init__(self, error_code: ErrorCode, message: str, **kwargs):
        super().__init__(error_code, message, status.HTTP_429_TOO_MANY_REQUESTS, **kwargs)


def handle_database_error(e: Exception, operation: str = "database operation") -> APIError:
    """Standardized database error handling"""
    logger.error(f"Database error during {operation}: {str(e)}")
    
    # Map specific database exceptions to appropriate error codes
    error_msg = str(e).lower()
    
    if "connection" in error_msg or "connect" in error_msg:
        return APIError(
            ErrorCode.DATABASE_CONNECTION_ERROR,
            f"Database connection failed during {operation}",
            status.HTTP_503_SERVICE_UNAVAILABLE,
            context={"operation": operation}
        )
    elif "constraint" in error_msg or "violation" in error_msg:
        return APIError(
            ErrorCode.CONSTRAINT_VIOLATION,
            f"Data constraint violation during {operation}",
            status.HTTP_400_BAD_REQUEST,
            context={"operation": operation}
        )
    elif "integrity" in error_msg:
        return APIError(
            ErrorCode.DATA_INTEGRITY_ERROR,
            f"Data integrity error during {operation}",
            status.HTTP_400_BAD_REQUEST,
            context={"operation": operation}
        )
    else:
        return APIError(
            ErrorCode.TRANSACTION_FAILED,
            f"Database transaction failed during {operation}",
            context={"operation": operation, "original_error": str(e)}
        )


def handle_external_service_error(
    e: Exception, 
    service: str, 
    operation: str = "external service call"
) -> APIError:
    """Standardized external service error handling"""
    logger.error(f"External service error ({service}) during {operation}: {str(e)}")
    
    error_msg = str(e).lower()
    
    if "rate limit" in error_msg or "429" in error_msg:
        return RateLimitError(
            ErrorCode.RATE_LIMIT_EXCEEDED,
            f"Rate limit exceeded for {service}",
            context={"service": service, "operation": operation}
        )
    elif "unauthorized" in error_msg or "401" in error_msg:
        return ExternalServiceError(
            ErrorCode.INVALID_CREDENTIALS,
            f"Invalid credentials for {service}",
            context={"service": service, "operation": operation}
        )
    elif "timeout" in error_msg or "connection" in error_msg:
        return ExternalServiceError(
            ErrorCode.PLATFORM_UNAVAILABLE,
            f"Service {service} is temporarily unavailable",
            status.HTTP_503_SERVICE_UNAVAILABLE,
            context={"service": service, "operation": operation}
        )
    else:
        return ExternalServiceError(
            ErrorCode.PLATFORM_API_ERROR,
            f"Error calling {service} API: {str(e)[:100]}",
            context={"service": service, "operation": operation}
        )


def handle_validation_error(
    field: str, 
    value: Any, 
    expected: str, 
    error_code: ErrorCode = ErrorCode.INVALID_INPUT
) -> ValidationError:
    """Standardized validation error creation"""
    return ValidationError(
        error_code,
        f"Invalid value for field '{field}': expected {expected}",
        field=field,
        context={"provided_value": str(value), "expected_format": expected}
    )


def log_and_raise(error: APIError, logger_instance: logging.Logger = logger, context: Optional[Dict[str, Any]] = None) -> None:
    """Log error details with taxonomy integration and raise as HTTPException"""
    logger_instance.error(
        f"API Error [{error.error_code.value}]: {error.message}",
        extra={
            "error_code": error.error_code.value,
            "status_code": error.status_code,
            "field": error.field,
            "context": error.context
        }
    )
    
    # Integrate with error taxonomy service for comprehensive error handling
    try:
        from backend.services.error_taxonomy_service import classify_and_handle_error
        
        # Classify and handle error with taxonomy
        taxonomy_info = classify_and_handle_error(error, context)
        
        # Log additional taxonomy information
        if taxonomy_info.get("requires_alert"):
            logger_instance.critical(
                f"Alert required for error {error.error_code.value}",
                extra={
                    "taxonomy_classification": taxonomy_info["taxonomy"]["category"],
                    "severity": taxonomy_info["taxonomy"]["severity"],
                    "escalation_required": taxonomy_info.get("requires_escalation", False)
                }
            )
    except Exception as taxonomy_error:
        # Don't fail the main error flow if taxonomy service fails
        logger_instance.warning(f"Error taxonomy classification failed: {taxonomy_error}")
    
    raise error.to_http_exception()


def safe_execute(
    operation: str,
    func: callable,
    *args,
    error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
    error_message: str = None,
    **kwargs
) -> Any:
    """Safely execute a function with standardized error handling"""
    try:
        return func(*args, **kwargs)
    except APIError:
        # Re-raise API errors as-is
        raise
    except Exception as e:
        logger.error(f"Error during {operation}: {str(e)}")
        
        # Determine appropriate error handling based on exception type
        if "database" in str(type(e)).lower() or "sql" in str(type(e)).lower():
            raise handle_database_error(e, operation).to_http_exception()
        
        # Default to internal server error
        error_msg = error_message or f"Internal error during {operation}"
        raise APIError(
            error_code,
            error_msg,
            context={"operation": operation, "original_error": str(e)}
        ).to_http_exception()


# Circuit Breaker Pattern Implementation
class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker for external service calls"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise ExternalServiceError(
                    ErrorCode.PLATFORM_UNAVAILABLE,
                    "Service temporarily unavailable (circuit breaker open)",
                    context={"circuit_breaker_state": self.state.value}
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self):
        """Check if circuit breaker should attempt reset"""
        return (
            self.last_failure_time and
            (datetime.now(timezone.utc).timestamp() - self.last_failure_time) > self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc).timestamp()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

# Retry Logic Implementation
import asyncio
import functools
from typing import Callable

def retry_on_failure(
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        # Last attempt failed
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {str(e)}")
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = delay_seconds * (backoff_multiplier ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {delay}s: {str(e)}")
                    
                    await asyncio.sleep(delay)
            
            # All attempts failed
            raise last_exception
        
        return wrapper
    return decorator

# Enhanced error handling with circuit breakers
_circuit_breakers = {}

def get_circuit_breaker(service_name: str) -> CircuitBreaker:
    """Get or create circuit breaker for service"""
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker()
    return _circuit_breakers[service_name]

def with_circuit_breaker(service_name: str):
    """Decorator to add circuit breaker protection"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            circuit_breaker = get_circuit_breaker(service_name)
            
            try:
                if asyncio.iscoroutinefunction(func):
                    return circuit_breaker.call(lambda: asyncio.create_task(func(*args, **kwargs)))
                else:
                    return circuit_breaker.call(func, *args, **kwargs)
            except Exception as e:
                logger.error(f"Circuit breaker call failed for {service_name}: {str(e)}")
                raise
        
        return wrapper
    return decorator

# Decorator for endpoint error handling
def handle_errors(operation: str):
    """Decorator for standardized endpoint error handling"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTP exceptions
                raise
            except APIError as e:
                # Convert API errors to HTTP exceptions
                raise e.to_http_exception()
            except Exception as e:
                logger.error(f"Unhandled error in {operation}: {str(e)}")
                raise APIError(
                    ErrorCode.INTERNAL_SERVER_ERROR,
                    f"Internal server error during {operation}",
                    context={"operation": operation, "error": str(e)}
                ).to_http_exception()
        return wrapper
    return decorator

# Enhanced exception handling for async operations
class AsyncErrorHandler:
    """Centralized async error handling"""
    
    @staticmethod
    async def handle_async_operation(
        operation: str,
        async_func: Callable,
        *args,
        **kwargs
    ):
        """Handle async operations with comprehensive error handling"""
        try:
            result = await async_func(*args, **kwargs)
            return result
        except asyncio.TimeoutError:
            raise ExternalServiceError(
                ErrorCode.PLATFORM_UNAVAILABLE,
                f"Operation {operation} timed out",
                context={"operation": operation}
            )
        except asyncio.CancelledError:
            logger.info(f"Operation {operation} was cancelled")
            raise
        except APIError:
            # Re-raise API errors
            raise
        except Exception as e:
            logger.error(f"Async operation {operation} failed: {str(e)}")
            raise APIError(
                ErrorCode.INTERNAL_SERVER_ERROR,
                f"Async operation {operation} failed",
                context={"operation": operation, "error": str(e)}
            )