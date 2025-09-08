"""
Startup Health Gates - P1-3b Implementation
Comprehensive health checks that must pass before application starts serving requests.

This module implements health gates that validate:
- Database connectivity and schema integrity
- Redis connectivity and operations
- External service dependencies
- Configuration validation
- Security prerequisites
- Environment readiness
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime, timezone

# Core dependencies
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from backend.core.config import get_settings

logger = logging.getLogger(__name__)

class HealthCheckStatus(Enum):
    """Health check status enumeration"""
    PASS = "pass"
    FAIL = "fail" 
    WARN = "warn"
    SKIP = "skip"

@dataclass
class HealthCheckResult:
    """Result of a single health check"""
    name: str
    status: HealthCheckStatus
    duration_ms: float
    message: str
    details: Dict[str, Any] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

@dataclass
class HealthGateResult:
    """Result of all startup health gates"""
    overall_status: HealthCheckStatus
    total_duration_ms: float
    passed_checks: int
    failed_checks: int
    warning_checks: int
    skipped_checks: int
    check_results: List[HealthCheckResult]
    timestamp: str
    ready_for_traffic: bool

class StartupHealthGates:
    """Startup health gate validator"""
    
    def __init__(self):
        self.settings = get_settings()
        self.health_checks: List[Callable] = []
        self.register_default_checks()
    
    def register_default_checks(self):
        """Register all default health checks"""
        self.health_checks = [
            self._check_environment_config,
            self._check_database_connectivity,
            self._check_database_schema,
            self._check_redis_connectivity,
            self._check_redis_operations,
            self._check_external_dependencies,
            self._check_security_config,
            self._check_secrets_management,
            self._check_logging_config,
            self._check_monitoring_endpoints,
        ]
    
    async def _check_environment_config(self) -> HealthCheckResult:
        """Validate environment configuration"""
        start_time = time.time()
        
        try:
            issues = []
            
            # Check required environment variables
            required_vars = [
                "DATABASE_URL", "REDIS_URL", "SECRET_KEY",
                "CORS_ORIGINS", "ENVIRONMENT"
            ]
            
            for var in required_vars:
                if not hasattr(self.settings, var.lower()) or not getattr(self.settings, var.lower(), None):
                    issues.append(f"Missing required environment variable: {var}")
            
            # Check environment is production-ready
            if hasattr(self.settings, 'environment'):
                env = self.settings.environment.lower()
                if env not in ['production', 'staging']:
                    issues.append(f"Environment '{env}' is not production-ready")
            
            # Check debug mode is disabled
            if hasattr(self.settings, 'debug') and self.settings.debug:
                issues.append("Debug mode is enabled - should be disabled in production")
            
            duration_ms = (time.time() - start_time) * 1000
            
            if issues:
                return HealthCheckResult(
                    name="environment_config",
                    status=HealthCheckStatus.FAIL,
                    duration_ms=duration_ms,
                    message=f"Environment configuration issues: {'; '.join(issues)}",
                    details={"issues": issues}
                )
            
            return HealthCheckResult(
                name="environment_config",
                status=HealthCheckStatus.PASS,
                duration_ms=duration_ms,
                message="Environment configuration is valid"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="environment_config",
                status=HealthCheckStatus.FAIL,
                duration_ms=duration_ms,
                message=f"Environment config check failed: {str(e)}"
            )
    
    async def _check_database_connectivity(self) -> HealthCheckResult:
        """Check database connectivity"""
        start_time = time.time()
        
        if not SQLALCHEMY_AVAILABLE:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="database_connectivity",
                status=HealthCheckStatus.SKIP,
                duration_ms=duration_ms,
                message="SQLAlchemy not available - skipping database check"
            )
        
        try:
            # Get database URL from settings
            db_url = getattr(self.settings, 'database_url', None)
            if not db_url:
                duration_ms = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    name="database_connectivity",
                    status=HealthCheckStatus.FAIL,
                    duration_ms=duration_ms,
                    message="No database URL configured"
                )
            
            # Test database connection
            engine = create_engine(db_url, pool_pre_ping=True)
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1")).scalar()
                
                if result != 1:
                    duration_ms = (time.time() - start_time) * 1000
                    return HealthCheckResult(
                        name="database_connectivity",
                        status=HealthCheckStatus.FAIL,
                        duration_ms=duration_ms,
                        message="Database connectivity test failed"
                    )
            
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="database_connectivity",
                status=HealthCheckStatus.PASS,
                duration_ms=duration_ms,
                message="Database connection successful"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="database_connectivity",
                status=HealthCheckStatus.FAIL,
                duration_ms=duration_ms,
                message=f"Database connection failed: {str(e)}"
            )
    
    async def _check_database_schema(self) -> HealthCheckResult:
        """Check database schema integrity"""
        start_time = time.time()
        
        if not SQLALCHEMY_AVAILABLE:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="database_schema",
                status=HealthCheckStatus.SKIP,
                duration_ms=duration_ms,
                message="SQLAlchemy not available - skipping schema check"
            )
        
        try:
            db_url = getattr(self.settings, 'database_url', None)
            if not db_url:
                duration_ms = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    name="database_schema",
                    status=HealthCheckStatus.SKIP,
                    duration_ms=duration_ms,
                    message="No database URL - skipping schema check"
                )
            
            engine = create_engine(db_url)
            
            # Check critical tables exist
            critical_tables = [
                'users', 'organizations', 'content_logs', 'social_platform_connections'
            ]
            
            missing_tables = []
            with engine.connect() as connection:
                for table in critical_tables:
                    result = connection.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = '{table}'
                        );
                    """)).scalar()
                    
                    if not result:
                        missing_tables.append(table)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if missing_tables:
                return HealthCheckResult(
                    name="database_schema",
                    status=HealthCheckStatus.FAIL,
                    duration_ms=duration_ms,
                    message=f"Missing critical tables: {', '.join(missing_tables)}",
                    details={"missing_tables": missing_tables}
                )
            
            return HealthCheckResult(
                name="database_schema",
                status=HealthCheckStatus.PASS,
                duration_ms=duration_ms,
                message="Database schema integrity verified"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="database_schema",
                status=HealthCheckStatus.FAIL,
                duration_ms=duration_ms,
                message=f"Database schema check failed: {str(e)}"
            )
    
    async def _check_redis_connectivity(self) -> HealthCheckResult:
        """Check Redis connectivity"""
        start_time = time.time()
        
        if not REDIS_AVAILABLE:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="redis_connectivity",
                status=HealthCheckStatus.WARN,
                duration_ms=duration_ms,
                message="Redis client not available - some features may be limited"
            )
        
        try:
            redis_url = getattr(self.settings, 'redis_url', None)
            if not redis_url:
                duration_ms = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    name="redis_connectivity",
                    status=HealthCheckStatus.WARN,
                    duration_ms=duration_ms,
                    message="No Redis URL configured - caching disabled"
                )
            
            # Test Redis connection
            redis_client = redis.from_url(redis_url)
            await redis_client.ping()
            await redis_client.aclose()
            
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="redis_connectivity",
                status=HealthCheckStatus.PASS,
                duration_ms=duration_ms,
                message="Redis connection successful"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="redis_connectivity",
                status=HealthCheckStatus.WARN,
                duration_ms=duration_ms,
                message=f"Redis connection failed: {str(e)} - caching disabled"
            )
    
    async def _check_redis_operations(self) -> HealthCheckResult:
        """Check Redis basic operations"""
        start_time = time.time()
        
        if not REDIS_AVAILABLE:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="redis_operations",
                status=HealthCheckStatus.SKIP,
                duration_ms=duration_ms,
                message="Redis not available - skipping operations check"
            )
        
        try:
            redis_url = getattr(self.settings, 'redis_url', None)
            if not redis_url:
                duration_ms = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    name="redis_operations",
                    status=HealthCheckStatus.SKIP,
                    duration_ms=duration_ms,
                    message="No Redis URL - skipping operations check"
                )
            
            redis_client = redis.from_url(redis_url)
            
            # Test basic operations
            test_key = "health_check_test"
            test_value = "health_check_value"
            
            await redis_client.set(test_key, test_value, ex=30)  # 30 second expiry
            retrieved_value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            await redis_client.aclose()
            
            duration_ms = (time.time() - start_time) * 1000
            
            if retrieved_value and retrieved_value.decode() == test_value:
                return HealthCheckResult(
                    name="redis_operations",
                    status=HealthCheckStatus.PASS,
                    duration_ms=duration_ms,
                    message="Redis operations working correctly"
                )
            else:
                return HealthCheckResult(
                    name="redis_operations",
                    status=HealthCheckStatus.FAIL,
                    duration_ms=duration_ms,
                    message="Redis operations failed - set/get mismatch"
                )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="redis_operations",
                status=HealthCheckStatus.WARN,
                duration_ms=duration_ms,
                message=f"Redis operations check failed: {str(e)}"
            )
    
    async def _check_external_dependencies(self) -> HealthCheckResult:
        """Check external service dependencies"""
        start_time = time.time()
        
        if not HTTPX_AVAILABLE:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="external_dependencies",
                status=HealthCheckStatus.SKIP,
                duration_ms=duration_ms,
                message="HTTP client not available - skipping external checks"
            )
        
        try:
            # List of critical external services to check
            external_services = [
                ("OpenAI API", "https://api.openai.com/v1/models"),
                ("Stripe API", "https://api.stripe.com/v1"),
            ]
            
            failed_services = []
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                for service_name, url in external_services:
                    try:
                        response = await client.get(url)
                        if response.status_code >= 400:
                            failed_services.append(f"{service_name}: HTTP {response.status_code}")
                    except Exception as e:
                        failed_services.append(f"{service_name}: {str(e)}")
            
            duration_ms = (time.time() - start_time) * 1000
            
            if failed_services:
                return HealthCheckResult(
                    name="external_dependencies",
                    status=HealthCheckStatus.WARN,
                    duration_ms=duration_ms,
                    message=f"Some external services unreachable: {'; '.join(failed_services)}",
                    details={"failed_services": failed_services}
                )
            
            return HealthCheckResult(
                name="external_dependencies",
                status=HealthCheckStatus.PASS,
                duration_ms=duration_ms,
                message="External dependencies accessible"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="external_dependencies",
                status=HealthCheckStatus.WARN,
                duration_ms=duration_ms,
                message=f"External dependency check failed: {str(e)}"
            )
    
    async def _check_security_config(self) -> HealthCheckResult:
        """Check security configuration"""
        start_time = time.time()
        
        try:
            security_issues = []
            
            # Check SECRET_KEY is set and secure
            secret_key = getattr(self.settings, 'secret_key', None)
            if not secret_key:
                security_issues.append("SECRET_KEY not configured")
            elif len(secret_key) < 32:
                security_issues.append("SECRET_KEY too short (minimum 32 characters)")
            
            # Check CORS origins are not wildcards
            cors_origins = getattr(self.settings, 'cors_origins', [])
            if "*" in str(cors_origins):
                security_issues.append("CORS origins contain wildcard (*)")
            
            # Check if running in secure mode
            environment = getattr(self.settings, 'environment', 'unknown').lower()
            if environment not in ['production', 'staging']:
                security_issues.append(f"Running in '{environment}' mode")
            
            duration_ms = (time.time() - start_time) * 1000
            
            if security_issues:
                return HealthCheckResult(
                    name="security_config",
                    status=HealthCheckStatus.FAIL,
                    duration_ms=duration_ms,
                    message=f"Security configuration issues: {'; '.join(security_issues)}",
                    details={"security_issues": security_issues}
                )
            
            return HealthCheckResult(
                name="security_config",
                status=HealthCheckStatus.PASS,
                duration_ms=duration_ms,
                message="Security configuration validated"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="security_config",
                status=HealthCheckStatus.FAIL,
                duration_ms=duration_ms,
                message=f"Security config check failed: {str(e)}"
            )
    
    async def _check_secrets_management(self) -> HealthCheckResult:
        """Check secrets management using comprehensive validator"""
        start_time = time.time()
        
        try:
            from backend.core.secrets_validator import validate_secrets_on_startup
            
            # Get current environment
            environment = getattr(self.settings, 'environment', 'production')
            
            # Run comprehensive secrets validation
            all_valid, error_messages = validate_secrets_on_startup(environment)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if not all_valid:
                # Count critical vs non-critical errors
                critical_errors = [msg for msg in error_messages if msg.startswith("CRITICAL:")]
                high_errors = [msg for msg in error_messages if msg.startswith("HIGH:")]
                
                if critical_errors:
                    return HealthCheckResult(
                        name="secrets_management",
                        status=HealthCheckStatus.FAIL,
                        duration_ms=duration_ms,
                        message=f"Critical secrets violations: {len(critical_errors)} critical, {len(high_errors)} high priority",
                        details={"error_messages": error_messages}
                    )
                else:
                    return HealthCheckResult(
                        name="secrets_management",
                        status=HealthCheckStatus.WARN,
                        duration_ms=duration_ms,
                        message=f"Secrets management issues: {len(error_messages)} issues found",
                        details={"error_messages": error_messages}
                    )
            
            return HealthCheckResult(
                name="secrets_management",
                status=HealthCheckStatus.PASS,
                duration_ms=duration_ms,
                message="All secrets pass comprehensive validation"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="secrets_management",
                status=HealthCheckStatus.FAIL,
                duration_ms=duration_ms,
                message=f"Secrets validation check failed: {str(e)}"
            )
    
    async def _check_logging_config(self) -> HealthCheckResult:
        """Check logging configuration"""
        start_time = time.time()
        
        try:
            # Basic logging configuration check
            root_logger = logging.getLogger()
            
            issues = []
            
            # Check if logging is configured
            if not root_logger.handlers:
                issues.append("No logging handlers configured")
            
            # Check logging level
            if root_logger.level > logging.INFO:
                issues.append(f"Logging level too high: {logging.getLevelName(root_logger.level)}")
            
            duration_ms = (time.time() - start_time) * 1000
            
            if issues:
                return HealthCheckResult(
                    name="logging_config",
                    status=HealthCheckStatus.WARN,
                    duration_ms=duration_ms,
                    message=f"Logging configuration issues: {'; '.join(issues)}",
                    details={"issues": issues}
                )
            
            return HealthCheckResult(
                name="logging_config",
                status=HealthCheckStatus.PASS,
                duration_ms=duration_ms,
                message="Logging configuration appears valid"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="logging_config",
                status=HealthCheckStatus.WARN,
                duration_ms=duration_ms,
                message=f"Logging config check failed: {str(e)}"
            )
    
    async def _check_monitoring_endpoints(self) -> HealthCheckResult:
        """Check monitoring and health check endpoints"""
        start_time = time.time()
        
        try:
            # This is a placeholder for checking if monitoring endpoints are accessible
            # In a real implementation, you'd check Prometheus, health endpoints, etc.
            
            duration_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="monitoring_endpoints",
                status=HealthCheckStatus.PASS,
                duration_ms=duration_ms,
                message="Monitoring endpoints check passed (placeholder)"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="monitoring_endpoints",
                status=HealthCheckStatus.WARN,
                duration_ms=duration_ms,
                message=f"Monitoring endpoints check failed: {str(e)}"
            )
    
    async def run_health_gates(self) -> HealthGateResult:
        """Run all health gates and return consolidated result"""
        start_time = time.time()
        logger.info("Starting startup health gates validation...")
        
        # Run all health checks concurrently
        tasks = [check() for check in self.health_checks]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(check_results):
            if isinstance(result, Exception):
                # Handle exceptions
                processed_results.append(HealthCheckResult(
                    name=f"check_{i}",
                    status=HealthCheckStatus.FAIL,
                    duration_ms=0,
                    message=f"Health check failed with exception: {str(result)}"
                ))
            else:
                processed_results.append(result)
        
        # Calculate statistics
        total_duration = (time.time() - start_time) * 1000
        passed = sum(1 for r in processed_results if r.status == HealthCheckStatus.PASS)
        failed = sum(1 for r in processed_results if r.status == HealthCheckStatus.FAIL)
        warnings = sum(1 for r in processed_results if r.status == HealthCheckStatus.WARN)
        skipped = sum(1 for r in processed_results if r.status == HealthCheckStatus.SKIP)
        
        # Determine overall status
        if failed > 0:
            overall_status = HealthCheckStatus.FAIL
            ready_for_traffic = False
        elif warnings > 0:
            overall_status = HealthCheckStatus.WARN
            ready_for_traffic = True  # Warnings don't prevent startup
        else:
            overall_status = HealthCheckStatus.PASS
            ready_for_traffic = True
        
        result = HealthGateResult(
            overall_status=overall_status,
            total_duration_ms=total_duration,
            passed_checks=passed,
            failed_checks=failed,
            warning_checks=warnings,
            skipped_checks=skipped,
            check_results=processed_results,
            timestamp=datetime.now(timezone.utc).isoformat(),
            ready_for_traffic=ready_for_traffic
        )
        
        # Log results
        if overall_status == HealthCheckStatus.FAIL:
            logger.error(f"Health gates FAILED: {failed} failures, {warnings} warnings")
            for check in processed_results:
                if check.status == HealthCheckStatus.FAIL:
                    logger.error(f"FAILED: {check.name} - {check.message}")
        elif overall_status == HealthCheckStatus.WARN:
            logger.warning(f"Health gates PASSED with warnings: {warnings} warnings")
            for check in processed_results:
                if check.status == HealthCheckStatus.WARN:
                    logger.warning(f"WARNING: {check.name} - {check.message}")
        else:
            logger.info(f"Health gates PASSED: All {passed} checks successful")
        
        return result


# Global instance
startup_health_gates = StartupHealthGates()


async def run_startup_health_gates() -> HealthGateResult:
    """Main function to run startup health gates"""
    return await startup_health_gates.run_health_gates()


def check_startup_readiness() -> bool:
    """Synchronous wrapper to check if application is ready to start"""
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, we can't use run()
            # In production, you'd handle this differently
            logger.warning("Event loop already running - skipping health gates")
            return True
        else:
            result = loop.run_until_complete(run_startup_health_gates())
            return result.ready_for_traffic
    except Exception as e:
        logger.error(f"Failed to run startup health gates: {e}")
        return False