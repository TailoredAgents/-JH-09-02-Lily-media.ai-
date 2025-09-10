"""
P1-7b: Vector Store Performance Monitoring
Comprehensive monitoring for FAISS and pgvector operations with performance metrics and alerting
"""
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import contextmanager
import psutil
import numpy as np

from backend.core.structured_logging import structured_logger_service, LogLevel
from backend.core.monitoring import monitoring_service

logger = logging.getLogger(__name__)

class VectorOperation(Enum):
    """Types of vector operations"""
    ADD_SINGLE = "add_single"
    ADD_BATCH = "add_batch"
    SEARCH_SIMILARITY = "search_similarity"
    SEARCH_BATCH = "search_batch"
    UPDATE_VECTOR = "update_vector"
    DELETE_VECTOR = "delete_vector"
    REBUILD_INDEX = "rebuild_index"
    SAVE_INDEX = "save_index"
    LOAD_INDEX = "load_index"

@dataclass
class VectorOperationMetrics:
    """Metrics for a single vector operation"""
    operation: VectorOperation
    duration_ms: float
    vector_count: int
    index_size: int
    memory_usage_mb: float
    success: bool
    error_message: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

@dataclass
class VectorStoreHealthMetrics:
    """Overall vector store health metrics"""
    total_vectors: int = 0
    index_size_mb: float = 0.0
    memory_usage_mb: float = 0.0
    avg_search_time_ms: float = 0.0
    avg_add_time_ms: float = 0.0
    operations_per_minute: float = 0.0
    error_rate: float = 0.0
    last_rebuild_time: Optional[str] = None
    fragmentation_score: float = 0.0  # 0-100, higher = more fragmented

class VectorStoreMonitor:
    """
    Comprehensive vector store performance monitoring
    P1-7b Implementation: Advanced performance metrics and optimization insights
    """
    
    def __init__(self):
        self.recent_operations: List[VectorOperationMetrics] = []
        self.max_recent_operations = 1000
        self.performance_thresholds = {
            "slow_search_ms": 100,     # Searches over 100ms are slow
            "slow_add_ms": 500,        # Adds over 500ms are slow
            "high_error_rate": 0.05,   # 5% error rate is concerning
            "high_memory_mb": 2048,    # 2GB memory usage is high
            "fragmentation_warning": 70,  # 70% fragmentation needs attention
        }
        
    @contextmanager
    def monitor_operation(
        self,
        operation: VectorOperation,
        vector_count: int = 1,
        index_size: Optional[int] = None
    ):
        """
        Context manager for monitoring vector operations
        
        Args:
            operation: Type of vector operation
            vector_count: Number of vectors involved
            index_size: Current index size (optional)
            
        Usage:
            with monitor.monitor_operation(VectorOperation.SEARCH_SIMILARITY, vector_count=10):
                results = vector_store.search(query, k=10)
        """
        start_time = time.time()
        start_memory = self._get_memory_usage_mb()
        success = True
        error_message = None
        
        try:
            yield
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Vector operation {operation.value} failed: {e}")
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            end_memory = self._get_memory_usage_mb()
            
            metrics = VectorOperationMetrics(
                operation=operation,
                duration_ms=duration_ms,
                vector_count=vector_count,
                index_size=index_size or 0,
                memory_usage_mb=end_memory,
                success=success,
                error_message=error_message
            )
            
            self._record_operation(metrics)
    
    def _record_operation(self, metrics: VectorOperationMetrics):
        """Record operation metrics and send to monitoring systems"""
        try:
            # Store recent operations
            self.recent_operations.append(metrics)
            if len(self.recent_operations) > self.max_recent_operations:
                self.recent_operations = self.recent_operations[-self.max_recent_operations:]
            
            # Log structured event
            self._log_operation_event(metrics)
            
            # Send to Prometheus metrics
            self._send_prometheus_metrics(metrics)
            
            # Check for alerting conditions
            self._check_performance_alerts(metrics)
            
        except Exception as e:
            logger.error(f"Failed to record vector operation metrics: {e}")
    
    def _log_operation_event(self, metrics: VectorOperationMetrics):
        """Log structured vector operation event"""
        if metrics.success:
            # Log successful operations at debug level unless they're slow
            level = LogLevel.DEBUG
            if (metrics.operation in [VectorOperation.SEARCH_SIMILARITY, VectorOperation.SEARCH_BATCH] and 
                metrics.duration_ms > self.performance_thresholds["slow_search_ms"]):
                level = LogLevel.WARNING
            elif (metrics.operation in [VectorOperation.ADD_SINGLE, VectorOperation.ADD_BATCH] and 
                  metrics.duration_ms > self.performance_thresholds["slow_add_ms"]):
                level = LogLevel.WARNING
        else:
            level = LogLevel.ERROR
        
        message = f"Vector {metrics.operation.value} "
        if metrics.success:
            message += f"completed in {metrics.duration_ms:.1f}ms"
        else:
            message += f"failed after {metrics.duration_ms:.1f}ms: {metrics.error_message}"
        
        structured_logger_service.log_performance_event(
            operation=f"vector_store_{metrics.operation.value}",
            duration_ms=metrics.duration_ms,
            message=message,
            level=level,
            metadata={
                "operation": metrics.operation.value,
                "vector_count": metrics.vector_count,
                "index_size": metrics.index_size,
                "memory_usage_mb": metrics.memory_usage_mb,
                "success": metrics.success,
                "error": metrics.error_message
            }
        )
    
    def _send_prometheus_metrics(self, metrics: VectorOperationMetrics):
        """Send metrics to Prometheus"""
        try:
            # Record operation counter and duration
            monitoring_service.record_vector_store_operation(
                operation=metrics.operation.value,
                success=metrics.success,
                duration_seconds=metrics.duration_ms / 1000,
                vector_count=metrics.vector_count
            )
            
            # Record memory usage
            monitoring_service.record_vector_store_memory_usage(
                memory_mb=metrics.memory_usage_mb
            )
            
            # Record index size
            if metrics.index_size > 0:
                monitoring_service.record_vector_store_index_size(
                    size_vectors=metrics.index_size
                )
                
            # Storage growth monitoring (P1-7d)
            if metrics.memory_usage_mb > 0:
                monitoring_service.record_vector_store_memory_usage(
                    component="faiss_index",
                    memory_bytes=int(metrics.memory_usage_mb * 1024 * 1024)
                )
            
            # Record rebuild operations
            if metrics.operation == VectorOperation.REBUILD_INDEX and metrics.success:
                monitoring_service.record_vector_store_rebuild(trigger_reason="scheduled")
                
        except Exception as e:
            logger.debug(f"Failed to send vector store metrics to Prometheus: {e}")
    
    def _check_performance_alerts(self, metrics: VectorOperationMetrics):
        """Check if operation should trigger performance alerts"""
        try:
            # Alert on slow operations
            if metrics.success:
                if (metrics.operation in [VectorOperation.SEARCH_SIMILARITY, VectorOperation.SEARCH_BATCH] and 
                    metrics.duration_ms > self.performance_thresholds["slow_search_ms"]):
                    
                    structured_logger_service.log_performance_event(
                        operation="vector_store_slow_search",
                        duration_ms=metrics.duration_ms,
                        message=f"Slow vector search detected: {metrics.duration_ms:.1f}ms for {metrics.vector_count} vectors",
                        level=LogLevel.WARNING,
                        metadata={
                            "threshold_ms": self.performance_thresholds["slow_search_ms"],
                            "vector_count": metrics.vector_count,
                            "index_size": metrics.index_size
                        }
                    )
                
                elif (metrics.operation in [VectorOperation.ADD_SINGLE, VectorOperation.ADD_BATCH] and 
                      metrics.duration_ms > self.performance_thresholds["slow_add_ms"]):
                    
                    structured_logger_service.log_performance_event(
                        operation="vector_store_slow_add",
                        duration_ms=metrics.duration_ms,
                        message=f"Slow vector add detected: {metrics.duration_ms:.1f}ms for {metrics.vector_count} vectors",
                        level=LogLevel.WARNING,
                        metadata={
                            "threshold_ms": self.performance_thresholds["slow_add_ms"],
                            "vector_count": metrics.vector_count,
                            "index_size": metrics.index_size
                        }
                    )
            
            # Alert on high memory usage
            if metrics.memory_usage_mb > self.performance_thresholds["high_memory_mb"]:
                structured_logger_service.log_performance_event(
                    operation="vector_store_high_memory",
                    duration_ms=metrics.duration_ms,
                    message=f"High vector store memory usage: {metrics.memory_usage_mb:.1f}MB",
                    level=LogLevel.WARNING,
                    metadata={
                        "memory_mb": metrics.memory_usage_mb,
                        "threshold_mb": self.performance_thresholds["high_memory_mb"],
                        "operation": metrics.operation.value
                    }
                )
            
        except Exception as e:
            logger.error(f"Failed to check performance alerts: {e}")
    
    def _get_memory_usage_mb(self) -> float:
        """Get current process memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance summary for the specified time period
        
        Args:
            hours: Hours to look back for metrics
            
        Returns:
            Dictionary with performance statistics
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Filter recent operations
            recent_ops = [
                op for op in self.recent_operations
                if datetime.fromisoformat(op.timestamp) > cutoff_time
            ]
            
            if not recent_ops:
                return {
                    "period_hours": hours,
                    "total_operations": 0,
                    "error": "No operations in time period"
                }
            
            # Calculate statistics
            total_ops = len(recent_ops)
            successful_ops = sum(1 for op in recent_ops if op.success)
            failed_ops = total_ops - successful_ops
            
            # Operation type breakdown
            operation_stats = {}
            for op in recent_ops:
                op_type = op.operation.value
                if op_type not in operation_stats:
                    operation_stats[op_type] = {"count": 0, "avg_duration_ms": 0.0, "failures": 0}
                
                operation_stats[op_type]["count"] += 1
                operation_stats[op_type]["avg_duration_ms"] += op.duration_ms
                if not op.success:
                    operation_stats[op_type]["failures"] += 1
            
            # Calculate averages
            for op_type, stats in operation_stats.items():
                if stats["count"] > 0:
                    stats["avg_duration_ms"] /= stats["count"]
                    stats["failure_rate"] = stats["failures"] / stats["count"]
            
            # Performance metrics
            search_ops = [op for op in recent_ops if op.operation in [VectorOperation.SEARCH_SIMILARITY, VectorOperation.SEARCH_BATCH]]
            add_ops = [op for op in recent_ops if op.operation in [VectorOperation.ADD_SINGLE, VectorOperation.ADD_BATCH]]
            
            avg_search_time = np.mean([op.duration_ms for op in search_ops]) if search_ops else 0.0
            avg_add_time = np.mean([op.duration_ms for op in add_ops]) if add_ops else 0.0
            
            # Memory and size metrics
            if recent_ops:
                latest_op = max(recent_ops, key=lambda x: x.timestamp)
                current_memory_mb = latest_op.memory_usage_mb
                current_index_size = latest_op.index_size
            else:
                current_memory_mb = 0.0
                current_index_size = 0
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "period_hours": hours,
                "summary": {
                    "total_operations": total_ops,
                    "successful_operations": successful_ops,
                    "failed_operations": failed_ops,
                    "success_rate": successful_ops / total_ops if total_ops > 0 else 1.0,
                    "operations_per_hour": total_ops / hours if hours > 0 else 0
                },
                "performance": {
                    "avg_search_time_ms": float(avg_search_time),
                    "avg_add_time_ms": float(avg_add_time),
                    "current_memory_mb": current_memory_mb,
                    "current_index_size": current_index_size
                },
                "operation_breakdown": operation_stats,
                "thresholds": self.performance_thresholds
            }
            
        except Exception as e:
            logger.error(f"Failed to generate performance summary: {e}")
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
    
    def get_slow_operations(self, hours: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of slow operations for debugging"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            slow_ops = []
            for op in self.recent_operations:
                if datetime.fromisoformat(op.timestamp) <= cutoff_time:
                    continue
                
                is_slow = False
                if op.operation in [VectorOperation.SEARCH_SIMILARITY, VectorOperation.SEARCH_BATCH]:
                    is_slow = op.duration_ms > self.performance_thresholds["slow_search_ms"]
                elif op.operation in [VectorOperation.ADD_SINGLE, VectorOperation.ADD_BATCH]:
                    is_slow = op.duration_ms > self.performance_thresholds["slow_add_ms"]
                else:
                    # For other operations, consider anything over 1 second as slow
                    is_slow = op.duration_ms > 1000
                
                if is_slow:
                    slow_ops.append(asdict(op))
            
            # Sort by duration (slowest first)
            slow_ops.sort(key=lambda x: x["duration_ms"], reverse=True)
            
            return slow_ops[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get slow operations: {e}")
            return []
    
    # Storage Growth Monitoring (P1-7d)
    def calculate_growth_rate(self, hours: int = 24) -> float:
        """Calculate vector addition growth rate over the specified period"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            add_operations = [
                op for op in self.recent_operations
                if datetime.fromisoformat(op.timestamp) > cutoff_time
                and op.operation in [VectorOperation.ADD_SINGLE, VectorOperation.ADD_BATCH]
                and op.success
            ]
            
            total_vectors_added = sum(op.vector_count for op in add_operations)
            growth_rate_per_hour = total_vectors_added / hours if hours > 0 else 0.0
            
            return growth_rate_per_hour
            
        except Exception as e:
            logger.error(f"Failed to calculate growth rate: {e}")
            return 0.0
    
    def estimate_fragmentation_ratio(self) -> float:
        """Estimate index fragmentation based on operation patterns"""
        try:
            # Simple fragmentation estimation based on:
            # - Number of delete operations
            # - Ratio of rebuilds to total operations
            # - Recent operation patterns
            
            recent_24h = [
                op for op in self.recent_operations
                if datetime.fromisoformat(op.timestamp) > datetime.now(timezone.utc) - timedelta(hours=24)
            ]
            
            if not recent_24h:
                return 0.0
            
            delete_operations = sum(
                1 for op in recent_24h 
                if op.operation == VectorOperation.DELETE_VECTOR
            )
            
            rebuild_operations = sum(
                1 for op in recent_24h
                if op.operation == VectorOperation.REBUILD_INDEX
            )
            
            total_operations = len(recent_24h)
            
            # Fragmentation estimation (0-1 scale)
            # Higher delete ratio increases fragmentation
            # Recent rebuilds reduce fragmentation
            delete_ratio = delete_operations / total_operations if total_operations > 0 else 0
            rebuild_ratio = rebuild_operations / total_operations if total_operations > 0 else 0
            
            # Simple fragmentation model
            fragmentation = min(delete_ratio * 2.0 - rebuild_ratio * 0.5, 1.0)
            return max(fragmentation, 0.0)
            
        except Exception as e:
            logger.error(f"Failed to estimate fragmentation: {e}")
            return 0.0
    
    def update_storage_growth_metrics(self):
        """Update storage growth metrics in Prometheus"""
        try:
            growth_rate = self.calculate_growth_rate()
            fragmentation = self.estimate_fragmentation_ratio()
            
            monitoring_service.record_vector_store_growth_rate(growth_rate)
            monitoring_service.record_vector_store_fragmentation(fragmentation)
            
        except Exception as e:
            logger.error(f"Failed to update storage growth metrics: {e}")

# Global vector store monitor instance
vector_store_monitor = VectorStoreMonitor()

# Convenience functions for integration
def monitor_vector_search(vector_count: int = 1, index_size: Optional[int] = None):
    """Context manager for monitoring vector search operations"""
    return vector_store_monitor.monitor_operation(
        VectorOperation.SEARCH_SIMILARITY, 
        vector_count=vector_count, 
        index_size=index_size
    )

def monitor_vector_add(vector_count: int = 1, index_size: Optional[int] = None):
    """Context manager for monitoring vector add operations"""
    operation = VectorOperation.ADD_BATCH if vector_count > 1 else VectorOperation.ADD_SINGLE
    return vector_store_monitor.monitor_operation(
        operation, 
        vector_count=vector_count, 
        index_size=index_size
    )

def monitor_vector_operation(operation: VectorOperation, vector_count: int = 1, index_size: Optional[int] = None):
    """Generic context manager for monitoring vector operations"""
    return vector_store_monitor.monitor_operation(operation, vector_count, index_size)

def get_vector_store_performance_dashboard() -> Dict[str, Any]:
    """Get comprehensive vector store performance dashboard"""
    return vector_store_monitor.get_performance_summary()

def get_vector_store_slow_operations(hours: int = 1) -> List[Dict[str, Any]]:
    """Get recent slow vector store operations"""
    return vector_store_monitor.get_slow_operations(hours)

def get_storage_growth_metrics() -> Dict[str, float]:
    """Get current storage growth metrics"""
    return {
        "growth_rate_vectors_per_hour": vector_store_monitor.calculate_growth_rate(),
        "fragmentation_ratio": vector_store_monitor.estimate_fragmentation_ratio()
    }

def update_storage_monitoring():
    """Update storage growth metrics in Prometheus"""
    vector_store_monitor.update_storage_growth_metrics()