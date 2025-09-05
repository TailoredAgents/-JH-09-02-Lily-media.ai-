"""
Performance optimization utilities and monitoring for production deployment
Includes query optimization, caching, connection pooling, and performance metrics
"""
import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import event, text
from sqlalchemy.pool import QueuePool
from fastapi import HTTPException, status
import json

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """
    Performance metrics collector for monitoring API and database performance
    """
    
    def __init__(self):
        self.metrics = {
            "api_calls": {},
            "db_queries": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "slow_queries": []
        }
    
    def record_api_call(self, endpoint: str, duration: float, status_code: int):
        """Record API call metrics"""
        if endpoint not in self.metrics["api_calls"]:
            self.metrics["api_calls"][endpoint] = {
                "count": 0,
                "total_duration": 0,
                "avg_duration": 0,
                "status_codes": {}
            }
        
        endpoint_metrics = self.metrics["api_calls"][endpoint]
        endpoint_metrics["count"] += 1
        endpoint_metrics["total_duration"] += duration
        endpoint_metrics["avg_duration"] = endpoint_metrics["total_duration"] / endpoint_metrics["count"]
        
        status_str = str(status_code)
        endpoint_metrics["status_codes"][status_str] = endpoint_metrics["status_codes"].get(status_str, 0) + 1
    
    def record_db_query(self, query: str, duration: float):
        """Record database query metrics"""
        query_hash = hash(query)
        
        if query_hash not in self.metrics["db_queries"]:
            self.metrics["db_queries"][query_hash] = {
                "query": query[:200],  # Truncate for storage
                "count": 0,
                "total_duration": 0,
                "avg_duration": 0
            }
        
        query_metrics = self.metrics["db_queries"][query_hash]
        query_metrics["count"] += 1
        query_metrics["total_duration"] += duration
        query_metrics["avg_duration"] = query_metrics["total_duration"] / query_metrics["count"]
        
        # Track slow queries
        if duration > 1.0:  # Queries slower than 1 second
            self.metrics["slow_queries"].append({
                "query": query[:200],
                "duration": duration,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Keep only last 100 slow queries
            if len(self.metrics["slow_queries"]) > 100:
                self.metrics["slow_queries"] = self.metrics["slow_queries"][-100:]
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.metrics["cache_hits"] += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.metrics["cache_misses"] += 1
    
    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_requests = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        if total_requests == 0:
            return 0.0
        return self.metrics["cache_hits"] / total_requests
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        return {
            "api_performance": {
                "total_endpoints": len(self.metrics["api_calls"]),
                "total_calls": sum(m["count"] for m in self.metrics["api_calls"].values()),
                "avg_response_time": sum(m["avg_duration"] for m in self.metrics["api_calls"].values()) / max(len(self.metrics["api_calls"]), 1)
            },
            "db_performance": {
                "total_query_types": len(self.metrics["db_queries"]),
                "total_queries": sum(m["count"] for m in self.metrics["db_queries"].values()),
                "avg_query_time": sum(m["avg_duration"] for m in self.metrics["db_queries"].values()) / max(len(self.metrics["db_queries"]), 1),
                "slow_query_count": len(self.metrics["slow_queries"])
            },
            "cache_performance": {
                "hit_rate": self.get_cache_hit_rate(),
                "total_hits": self.metrics["cache_hits"],
                "total_misses": self.metrics["cache_misses"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }

# Global metrics collector
performance_metrics = PerformanceMetrics()

def performance_monitor(endpoint_name: Optional[str] = None):
    """
    Decorator to monitor API endpoint performance
    
    Args:
        endpoint_name: Custom name for the endpoint (optional)
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
            except HTTPException as e:
                status_code = e.status_code
                raise
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                name = endpoint_name or func.__name__
                performance_metrics.record_api_call(name, duration, status_code)
                
                if duration > 2.0:  # Log slow endpoints
                    logger.warning(f"Slow endpoint {name}: {duration:.2f}s")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            
            try:
                result = func(*args, **kwargs)
                return result
            except HTTPException as e:
                status_code = e.status_code
                raise
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                name = endpoint_name or func.__name__
                performance_metrics.record_api_call(name, duration, status_code)
                
                if duration > 2.0:  # Log slow endpoints
                    logger.warning(f"Slow endpoint {name}: {duration:.2f}s")
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def monitor_db_queries(engine):
    """
    Set up database query monitoring
    
    Args:
        engine: SQLAlchemy engine
    """
    
    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()
    
    @event.listens_for(engine, "after_cursor_execute")  
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        duration = time.time() - context._query_start_time
        performance_metrics.record_db_query(statement, duration)

class DatabaseOptimizer:
    """
    Database optimization utilities and connection management
    """
    
    @staticmethod
    def optimize_connection_pool(engine_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize database connection pool settings
        
        Args:
            engine_kwargs: Current engine configuration
            
        Returns:
            Optimized engine configuration
        """
        optimized = engine_kwargs.copy()
        
        # Connection pool optimization
        optimized.update({
            "poolclass": QueuePool,
            "pool_size": 20,  # Base connection pool size
            "max_overflow": 30,  # Additional connections when needed
            "pool_pre_ping": True,  # Verify connections before use
            "pool_recycle": 3600,  # Recycle connections every hour
            "pool_timeout": 30,  # Timeout for getting connection
        })
        
        # PostgreSQL-specific optimizations
        if "postgresql" in optimized.get("url", ""):
            connect_args = optimized.get("connect_args", {})
            connect_args.update({
                "sslmode": "require",
                "connect_timeout": 10,
                "command_timeout": 60,
                "server_side_cursors": True,  # For large result sets
            })
            optimized["connect_args"] = connect_args
        
        logger.info("Database connection pool optimized")
        return optimized
    
    @staticmethod
    def get_query_optimization_hints() -> Dict[str, str]:
        """
        Get database-specific query optimization hints
        
        Returns:
            Dictionary of optimization hints
        """
        return {
            "use_indexes": "Ensure proper indexes on commonly queried columns",
            "limit_results": "Always use LIMIT for potentially large result sets", 
            "avoid_n_plus_1": "Use eager loading to avoid N+1 query problems",
            "batch_operations": "Use bulk operations for multiple inserts/updates",
            "analyze_slow_queries": "Monitor and optimize queries taking >1 second",
        }

class CacheOptimizer:
    """
    Caching optimization utilities
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_stats = {"hits": 0, "misses": 0, "evictions": 0}
        self.max_cache_size = 10000
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            self.cache_stats["hits"] += 1
            performance_metrics.record_cache_hit()
            
            # Move to end for LRU
            value = self.cache.pop(key)
            self.cache[key] = value
            return value
        else:
            self.cache_stats["misses"] += 1
            performance_metrics.record_cache_miss()
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        # Implement LRU eviction
        if len(self.cache) >= self.max_cache_size:
            # Remove oldest item
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self.cache_stats["evictions"] += 1
        
        self.cache[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl) if ttl else None
        }
    
    def delete(self, key: str):
        """Delete value from cache"""
        self.cache.pop(key, None)
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = self.cache_stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_cache_size,
            "hit_rate": hit_rate,
            "stats": self.cache_stats
        }

# Global cache instance
cache_optimizer = CacheOptimizer()

def cached(key: str, ttl: int = 300):
    """
    Caching decorator for expensive operations
    
    Args:
        key: Cache key template (can use {args} for formatting)
        ttl: Time to live in seconds
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = key.format(args=str(args), kwargs=str(kwargs))
            
            # Try to get from cache
            cached_result = cache_optimizer.get(cache_key)
            if cached_result is not None:
                return cached_result["value"]
            
            # Execute function and cache result
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            cache_optimizer.set(cache_key, result, ttl)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = key.format(args=str(args), kwargs=str(kwargs))
            
            # Try to get from cache
            cached_result = cache_optimizer.get(cache_key)
            if cached_result is not None:
                return cached_result["value"]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_optimizer.set(cache_key, result, ttl)
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

class ResponseOptimizer:
    """
    Response optimization utilities for better client performance
    """
    
    @staticmethod
    def compress_large_responses(data: Any, threshold: int = 1024) -> Any:
        """
        Compress large response data
        
        Args:
            data: Response data
            threshold: Size threshold in bytes
            
        Returns:
            Potentially compressed data
        """
        if isinstance(data, (dict, list)):
            json_str = json.dumps(data)
            if len(json_str.encode()) > threshold:
                # In production, implement actual compression here
                logger.debug(f"Large response detected: {len(json_str)} bytes")
        
        return data
    
    @staticmethod
    def optimize_json_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize JSON response structure
        
        Args:
            data: Response data
            
        Returns:
            Optimized response data
        """
        # Remove null values to reduce payload size
        def remove_nulls(obj):
            if isinstance(obj, dict):
                return {k: remove_nulls(v) for k, v in obj.items() if v is not None}
            elif isinstance(obj, list):
                return [remove_nulls(item) for item in obj]
            else:
                return obj
        
        return remove_nulls(data)

# Performance monitoring context managers
@contextmanager
def monitor_performance(operation_name: str):
    """
    Context manager for monitoring operation performance
    
    Args:
        operation_name: Name of the operation being monitored
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.debug(f"Operation {operation_name} took {duration:.3f}s")
        
        if duration > 1.0:
            logger.warning(f"Slow operation detected: {operation_name} ({duration:.3f}s)")

@asynccontextmanager
async def monitor_async_performance(operation_name: str):
    """
    Async context manager for monitoring operation performance
    
    Args:
        operation_name: Name of the operation being monitored
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.debug(f"Async operation {operation_name} took {duration:.3f}s")
        
        if duration > 1.0:
            logger.warning(f"Slow async operation detected: {operation_name} ({duration:.3f}s)")

# Performance analysis utilities
def analyze_performance_bottlenecks() -> Dict[str, Any]:
    """
    Analyze current performance bottlenecks and provide recommendations
    
    Returns:
        Analysis results with recommendations
    """
    metrics = performance_metrics.get_summary()
    
    recommendations = []
    
    # Check API performance
    if metrics["api_performance"]["avg_response_time"] > 1.0:
        recommendations.append({
            "type": "api_performance",
            "issue": "High average API response time",
            "recommendation": "Review slow endpoints and optimize database queries"
        })
    
    # Check database performance
    if metrics["db_performance"]["avg_query_time"] > 0.5:
        recommendations.append({
            "type": "db_performance", 
            "issue": "Slow database queries detected",
            "recommendation": "Add indexes, optimize queries, or implement query caching"
        })
    
    # Check cache performance
    if metrics["cache_performance"]["hit_rate"] < 0.8:
        recommendations.append({
            "type": "cache_performance",
            "issue": "Low cache hit rate",
            "recommendation": "Review caching strategy and increase cache TTL for stable data"
        })
    
    return {
        "metrics": metrics,
        "recommendations": recommendations,
        "analysis_timestamp": datetime.utcnow().isoformat()
    }