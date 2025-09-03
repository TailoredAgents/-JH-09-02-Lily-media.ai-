"""
Service Factory Pattern

Replaces global singletons with dependency injection and factory pattern.
Enables better testing, configuration, and lifecycle management.
"""
import logging
from typing import Dict, Any, Optional, Type, TypeVar, Callable
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceFactory:
    """
    Factory for creating and managing service instances.
    
    Supports:
    - Dependency injection
    - Scoped instances (singleton, per-request, per-call)
    - Configuration injection
    - Testing overrides
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._scopes: Dict[str, str] = {}  # 'singleton', 'scoped', 'transient'
        
    def register(
        self, 
        service_name: str, 
        factory: Callable, 
        scope: str = 'singleton',
        dependencies: Optional[Dict[str, Any]] = None
    ):
        """
        Register a service factory.
        
        Args:
            service_name: Unique service identifier
            factory: Factory function/class constructor
            scope: Instance scope ('singleton', 'scoped', 'transient')
            dependencies: Optional dependencies to inject
        """
        self._factories[service_name] = factory
        self._scopes[service_name] = scope
        
        if dependencies:
            self._services[service_name] = dependencies
            
        logger.debug("Registered service '{}' with scope '{}'".format(service_name, scope))
    
    def get(self, service_name: str, **kwargs) -> Any:
        """
        Get service instance.
        
        Args:
            service_name: Service identifier
            **kwargs: Additional parameters to pass to factory
            
        Returns:
            Service instance
        """
        if service_name not in self._factories:
            raise ValueError("Service '{}' not registered".format(service_name))
        
        scope = self._scopes.get(service_name, 'singleton')
        
        if scope == 'singleton':
            if service_name not in self._singletons:
                self._singletons[service_name] = self._create_instance(service_name, **kwargs)
            return self._singletons[service_name]
        
        elif scope == 'transient':
            # Always create new instance
            return self._create_instance(service_name, **kwargs)
        
        else:  # scoped
            # For now, treat scoped as singleton (can be extended for request scopes)
            return self.get(service_name)
    
    def _create_instance(self, service_name: str, **kwargs) -> Any:
        """Create service instance with dependency injection."""
        factory = self._factories[service_name]
        dependencies = self._services.get(service_name, {})
        
        # Merge dependencies with provided kwargs
        combined_kwargs = {**dependencies, **kwargs}
        
        try:
            return factory(**combined_kwargs)
        except Exception as e:
            logger.error("Failed to create service '{}': {}".format(service_name, e))
            raise
    
    def override(self, service_name: str, instance: Any):
        """
        Override service instance (useful for testing).
        
        Args:
            service_name: Service to override
            instance: Instance to use instead
        """
        self._singletons[service_name] = instance
        logger.debug("Overrode service '{}'".format(service_name))
    
    def reset(self, service_name: Optional[str] = None):
        """
        Reset service instances.
        
        Args:
            service_name: Specific service to reset, or None for all
        """
        if service_name:
            self._singletons.pop(service_name, None)
            logger.debug("Reset service '{}'".format(service_name))
        else:
            self._singletons.clear()
            logger.debug("Reset all services")
    
    def close(self):
        """Close all services that have close methods."""
        for service_name, instance in self._singletons.items():
            if hasattr(instance, 'close'):
                try:
                    if hasattr(instance, '__aenter__'):  # Async context manager
                        import asyncio
                        asyncio.create_task(instance.__aexit__(None, None, None))
                    else:
                        instance.close()
                    logger.debug("Closed service '{}'".format(service_name))
                except Exception as e:
                    logger.warning("Failed to close service '{}': {}".format(service_name, e))


# Global factory instance
_factory: Optional[ServiceFactory] = None


def get_factory() -> ServiceFactory:
    """Get the global service factory."""
    global _factory
    if _factory is None:
        _factory = ServiceFactory()
    return _factory


def register_service(
    service_name: str,
    factory: Callable,
    scope: str = 'singleton',
    dependencies: Optional[Dict[str, Any]] = None
):
    """Register a service with the global factory."""
    get_factory().register(service_name, factory, scope, dependencies)


def get_service(service_name: str, **kwargs) -> Any:
    """Get service from global factory."""
    return get_factory().get(service_name, **kwargs)


def override_service(service_name: str, instance: Any):
    """Override service in global factory."""
    get_factory().override(service_name, instance)


def reset_services(service_name: Optional[str] = None):
    """Reset services in global factory."""
    get_factory().reset(service_name)


# Service registration decorator
def service(name: str, scope: str = 'singleton', dependencies: Optional[Dict[str, Any]] = None):
    """
    Decorator to register a service.
    
    Args:
        name: Service name
        scope: Instance scope
        dependencies: Dependencies to inject
    """
    def decorator(cls):
        register_service(name, cls, scope, dependencies)
        return cls
    return decorator


@asynccontextmanager
async def service_context():
    """Context manager for service lifecycle."""
    factory = get_factory()
    try:
        yield factory
    finally:
        factory.close()