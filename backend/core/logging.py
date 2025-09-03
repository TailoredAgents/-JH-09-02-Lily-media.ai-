"""
Centralized Logging Configuration

Provides standardized logging setup with JSON formatting for structured logs.
Replaces scattered logging.basicConfig() calls with centralized configuration.
"""
import os
import logging
import logging.config
import json
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        # Add extra fields from record
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
            
        return json.dumps(log_entry, default=str)


def setup_logging(
    level=None,
    format_type='standard',
    log_file=None,
    service_name='ai-social-media'
):
    """
    Setup centralized logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: 'json' for structured JSON logs, 'standard' for human-readable
        log_file: Optional file path for log output
        service_name: Service name to include in logs
    """
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
    # Convert string level to logging constant
    numeric_level = getattr(logging, level, logging.INFO)
    
    # Choose formatter based on environment and format_type
    environment = os.getenv('ENVIRONMENT', 'development').lower()
    use_json = (format_type == 'json' or 
               environment == 'production' or 
               os.getenv('USE_JSON_LOGGING', '').lower() == 'true')
    
    if use_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels for noisy third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('alembic').setLevel(logging.WARNING)
    
    # Create service-specific logger
    service_logger = logging.getLogger(service_name)
    
    return service_logger


def get_logger(name=None, **context):
    """
    Get a logger with optional context.
    
    Args:
        name: Logger name (defaults to caller's module)
        **context: Additional context to include in all log messages
        
    Returns:
        Logger instance with context
    """
    if name is None:
        # Get caller's module name
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    
    logger = logging.getLogger(name)
    
    # Add context as extra fields
    if context:
        class ContextAdapter(logging.LoggerAdapter):
            def process(self, msg, kwargs):
                for key, value in self.extra.items():
                    if not hasattr(kwargs.get('extra', {}), key):
                        kwargs.setdefault('extra', {})[key] = value
                return msg, kwargs
        
        logger = ContextAdapter(logger, context)
    
    return logger


# Quick setup functions for common scenarios
def setup_development_logging():
    """Setup logging for development environment."""
    return setup_logging(
        level='DEBUG',
        format_type='standard',
        service_name='ai-social-media-dev'
    )


def setup_production_logging(log_file=None):
    """Setup logging for production environment."""
    return setup_logging(
        level='INFO',
        format_type='json',
        log_file=log_file,
        service_name='ai-social-media-prod'
    )


def setup_test_logging():
    """Setup logging for test environment."""
    return setup_logging(
        level='WARNING',
        format_type='standard',
        service_name='ai-social-media-test'
    )