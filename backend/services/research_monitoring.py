"""
Research Usage Metrics and Monitoring Service

Comprehensive Prometheus metrics collection for research system monitoring,
usage tracking, and performance analysis. Provides detailed insights into:
- Research operation performance and latency
- Usage patterns and quota tracking
- Error rates and failure analysis
- Feature utilization across plans
- Vector store performance metrics
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from prometheus_client import Counter, Histogram, Gauge, Summary
from dataclasses import dataclass

from backend.core.config import get_settings
from backend.core.observability import get_observability_manager

settings = get_settings()
logger = logging.getLogger(__name__)
observability = get_observability_manager()

# ============================================================================
# Research Operation Metrics
# ============================================================================

# Research Request Tracking
RESEARCH_REQUESTS_TOTAL = Counter(
    'research_requests_total',
    'Total research requests by type and outcome',
    ['research_type', 'user_plan', 'status', 'industry']
)

RESEARCH_OPERATION_DURATION = Histogram(
    'research_operation_duration_seconds',
    'Time spent on research operations',
    ['operation_type', 'user_plan', 'industry'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, float('inf')]
)

# Knowledge Base Query Metrics
KNOWLEDGE_BASE_QUERIES_TOTAL = Counter(
    'knowledge_base_queries_total',
    'Total knowledge base queries',
    ['query_type', 'user_plan', 'result_quality']
)

KNOWLEDGE_BASE_QUERY_LATENCY = Histogram(
    'knowledge_base_query_latency_seconds',
    'Knowledge base query response time',
    ['query_type', 'result_count'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')]
)

KNOWLEDGE_BASE_RESULT_COUNT = Histogram(
    'knowledge_base_result_count',
    'Number of results returned from knowledge base queries',
    ['query_type', 'user_plan'],
    buckets=[0, 1, 5, 10, 25, 50, 100, 250, 500, 1000, float('inf')]
)

# ============================================================================
# Deep Research System Metrics
# ============================================================================

DEEP_RESEARCH_TASKS_TOTAL = Counter(
    'deep_research_tasks_total',
    'Total deep research tasks executed',
    ['task_type', 'industry', 'trigger', 'status']
)

DEEP_RESEARCH_TASK_DURATION = Histogram(
    'deep_research_task_duration_seconds',
    'Deep research task execution time',
    ['task_type', 'industry', 'complexity'],
    buckets=[30.0, 60.0, 120.0, 300.0, 600.0, 1200.0, 1800.0, 3600.0, float('inf')]
)

RESEARCH_SCHEDULER_HEALTH = Gauge(
    'research_scheduler_health_score',
    'Health score of research scheduler (0-100)',
    ['component']
)

INDUSTRY_RESEARCH_ACTIVE = Gauge(
    'industry_research_configurations_active',
    'Number of active industry research configurations',
    ['plan_tier']
)

# Research Intelligence Quality Metrics
RESEARCH_INTELLIGENCE_QUALITY = Histogram(
    'research_intelligence_quality_score',
    'Quality score of generated research intelligence',
    ['industry', 'research_type'],
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
)

RESEARCH_SOURCE_COUNT = Counter(
    'research_sources_processed_total',
    'Total research sources processed',
    ['source_type', 'industry', 'quality_tier']
)

# ============================================================================
# Vector Store Performance Metrics
# ============================================================================

VECTOR_STORE_OPERATIONS_TOTAL = Counter(
    'vector_store_operations_total',
    'Total vector store operations',
    ['operation', 'status', 'dimension']
)

VECTOR_STORE_OPERATION_LATENCY = Histogram(
    'vector_store_operation_latency_seconds',
    'Vector store operation response time',
    ['operation', 'vector_count'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, float('inf')]
)

VECTOR_STORE_SIZE = Gauge(
    'vector_store_size_total',
    'Total number of vectors in store',
    ['collection', 'dimension']
)

VECTOR_STORE_MEMORY_USAGE = Gauge(
    'vector_store_memory_usage_bytes',
    'Memory usage of vector store',
    ['collection', 'component']
)

# Embedding Generation Metrics
EMBEDDING_GENERATION_REQUESTS = Counter(
    'embedding_generation_requests_total',
    'Total embedding generation requests',
    ['model', 'status', 'content_type']
)

EMBEDDING_GENERATION_LATENCY = Histogram(
    'embedding_generation_latency_seconds',
    'Embedding generation response time',
    ['model', 'text_length'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, float('inf')]
)

# ============================================================================
# Usage Quota and Plan Enforcement Metrics
# ============================================================================

RESEARCH_QUOTA_USAGE = Counter(
    'research_quota_usage_total',
    'Research feature usage against quotas',
    ['feature', 'user_plan', 'user_id']
)

RESEARCH_QUOTA_EXCEEDED = Counter(
    'research_quota_exceeded_total',
    'Research quota violations',
    ['feature', 'user_plan', 'limit_type']
)

RESEARCH_PLAN_ENFORCEMENT = Counter(
    'research_plan_enforcement_total',
    'Plan enforcement actions',
    ['action', 'user_plan', 'feature']
)

# Current quota utilization
RESEARCH_QUOTA_UTILIZATION = Gauge(
    'research_quota_utilization_percent',
    'Current quota utilization percentage',
    ['feature', 'user_id', 'user_plan']
)

# ============================================================================
# Error and Failure Tracking
# ============================================================================

RESEARCH_ERRORS_TOTAL = Counter(
    'research_errors_total',
    'Total research system errors',
    ['error_type', 'component', 'severity']
)

RESEARCH_CIRCUIT_BREAKER_STATE = Gauge(
    'research_circuit_breaker_state',
    'Circuit breaker states (0=closed, 1=open, 2=half-open)',
    ['service', 'endpoint']
)

RESEARCH_RETRY_ATTEMPTS = Counter(
    'research_retry_attempts_total',
    'Total retry attempts in research operations',
    ['operation', 'retry_reason', 'success']
)

# ============================================================================
# Research Content Generation Metrics
# ============================================================================

CONTENT_OPPORTUNITIES_GENERATED = Counter(
    'content_opportunities_generated_total',
    'Content opportunities identified from research',
    ['industry', 'urgency', 'opportunity_type']
)

CONTENT_OPPORTUNITY_QUALITY = Histogram(
    'content_opportunity_quality_score',
    'Quality score of generated content opportunities',
    ['industry', 'opportunity_type'],
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
)

RESEARCH_CONTENT_CONVERSION = Counter(
    'research_content_conversion_total',
    'Research insights converted to content',
    ['conversion_type', 'industry', 'success']
)

# ============================================================================
# Monitoring Service Class
# ============================================================================

@dataclass
class ResearchMetrics:
    """Container for research operation metrics"""
    operation_type: str
    duration: float
    success: bool
    user_plan: str
    industry: Optional[str] = None
    error_type: Optional[str] = None
    result_count: Optional[int] = None
    quality_score: Optional[float] = None

class ResearchMonitoringService:
    """Service for comprehensive research system monitoring and metrics collection"""
    
    def __init__(self):
        self.start_time = time.time()
        logger.info("Research monitoring service initialized")
    
    # ========================================================================
    # Research Operation Tracking
    # ========================================================================
    
    def track_research_request(self, research_type: str, user_plan: str, 
                             industry: str, status: str):
        """Track research request metrics"""
        RESEARCH_REQUESTS_TOTAL.labels(
            research_type=research_type,
            user_plan=user_plan,
            status=status,
            industry=industry
        ).inc()
    
    def record_research_operation(self, metrics: ResearchMetrics):
        """Record comprehensive research operation metrics"""
        # Duration tracking
        RESEARCH_OPERATION_DURATION.labels(
            operation_type=metrics.operation_type,
            user_plan=metrics.user_plan,
            industry=metrics.industry or 'general'
        ).observe(metrics.duration)
        
        # Request tracking with status
        status = 'success' if metrics.success else 'failure'
        RESEARCH_REQUESTS_TOTAL.labels(
            research_type=metrics.operation_type,
            user_plan=metrics.user_plan,
            status=status,
            industry=metrics.industry or 'general'
        ).inc()
        
        # Error tracking if applicable
        if not metrics.success and metrics.error_type:
            RESEARCH_ERRORS_TOTAL.labels(
                error_type=metrics.error_type,
                component='research_operation',
                severity='error'
            ).inc()
        
        # Quality tracking if available
        if metrics.quality_score is not None:
            RESEARCH_INTELLIGENCE_QUALITY.labels(
                industry=metrics.industry or 'general',
                research_type=metrics.operation_type
            ).observe(metrics.quality_score)
    
    # ========================================================================
    # Knowledge Base Query Tracking
    # ========================================================================
    
    def track_knowledge_base_query(self, query_type: str, user_plan: str, 
                                 duration: float, result_count: int, 
                                 result_quality: str = 'good'):
        """Track knowledge base query metrics"""
        
        # Query count and quality
        KNOWLEDGE_BASE_QUERIES_TOTAL.labels(
            query_type=query_type,
            user_plan=user_plan,
            result_quality=result_quality
        ).inc()
        
        # Query latency
        KNOWLEDGE_BASE_QUERY_LATENCY.labels(
            query_type=query_type,
            result_count=str(min(result_count, 100))  # Cap for cardinality
        ).observe(duration)
        
        # Result count distribution
        KNOWLEDGE_BASE_RESULT_COUNT.labels(
            query_type=query_type,
            user_plan=user_plan
        ).observe(result_count)
    
    # ========================================================================
    # Deep Research Task Tracking
    # ========================================================================
    
    def track_deep_research_task(self, task_type: str, industry: str, 
                               trigger: str, duration: float, 
                               success: bool, complexity: str = 'standard'):
        """Track deep research task execution"""
        
        status = 'completed' if success else 'failed'
        
        DEEP_RESEARCH_TASKS_TOTAL.labels(
            task_type=task_type,
            industry=industry,
            trigger=trigger,
            status=status
        ).inc()
        
        if success:
            DEEP_RESEARCH_TASK_DURATION.labels(
                task_type=task_type,
                industry=industry,
                complexity=complexity
            ).observe(duration)
    
    def update_scheduler_health(self, component: str, health_score: float):
        """Update research scheduler health metrics"""
        RESEARCH_SCHEDULER_HEALTH.labels(
            component=component
        ).set(health_score)
    
    def update_active_research_count(self, plan_tier: str, count: int):
        """Update count of active industry research configurations"""
        INDUSTRY_RESEARCH_ACTIVE.labels(
            plan_tier=plan_tier
        ).set(count)
    
    # ========================================================================
    # Vector Store Performance Tracking
    # ========================================================================
    
    def track_vector_operation(self, operation: str, duration: float, 
                             vector_count: int, success: bool, 
                             dimension: int = 3072):
        """Track vector store operations"""
        
        status = 'success' if success else 'failure'
        
        VECTOR_STORE_OPERATIONS_TOTAL.labels(
            operation=operation,
            status=status,
            dimension=str(dimension)
        ).inc()
        
        if success:
            VECTOR_STORE_OPERATION_LATENCY.labels(
                operation=operation,
                vector_count=str(min(vector_count, 1000))  # Cap for cardinality
            ).observe(duration)
    
    def update_vector_store_metrics(self, collection: str, vector_count: int, 
                                  memory_usage: int, dimension: int = 3072):
        """Update vector store size and memory metrics"""
        
        VECTOR_STORE_SIZE.labels(
            collection=collection,
            dimension=str(dimension)
        ).set(vector_count)
        
        VECTOR_STORE_MEMORY_USAGE.labels(
            collection=collection,
            component='total'
        ).set(memory_usage)
    
    def track_embedding_generation(self, model: str, duration: float, 
                                 text_length: int, success: bool, 
                                 content_type: str = 'research'):
        """Track embedding generation metrics"""
        
        status = 'success' if success else 'failure'
        
        EMBEDDING_GENERATION_REQUESTS.labels(
            model=model,
            status=status,
            content_type=content_type
        ).inc()
        
        if success:
            # Bucket text length for cardinality control
            length_bucket = 'short' if text_length < 100 else 'medium' if text_length < 1000 else 'long'
            
            EMBEDDING_GENERATION_LATENCY.labels(
                model=model,
                text_length=length_bucket
            ).observe(duration)
    
    # ========================================================================
    # Quota and Plan Enforcement Tracking
    # ========================================================================
    
    def track_quota_usage(self, feature: str, user_id: str, user_plan: str, 
                         amount: int = 1):
        """Track research feature usage against quotas"""
        RESEARCH_QUOTA_USAGE.labels(
            feature=feature,
            user_plan=user_plan,
            user_id=user_id
        ).inc(amount)
    
    def track_quota_exceeded(self, feature: str, user_plan: str, 
                           limit_type: str = 'daily'):
        """Track quota violations"""
        RESEARCH_QUOTA_EXCEEDED.labels(
            feature=feature,
            user_plan=user_plan,
            limit_type=limit_type
        ).inc()
    
    def track_plan_enforcement(self, action: str, user_plan: str, feature: str):
        """Track plan enforcement actions"""
        RESEARCH_PLAN_ENFORCEMENT.labels(
            action=action,
            user_plan=user_plan,
            feature=feature
        ).inc()
    
    def update_quota_utilization(self, feature: str, user_id: str, 
                               user_plan: str, utilization_percent: float):
        """Update current quota utilization"""
        RESEARCH_QUOTA_UTILIZATION.labels(
            feature=feature,
            user_id=user_id,
            user_plan=user_plan
        ).set(utilization_percent)
    
    # ========================================================================
    # Error and Circuit Breaker Tracking
    # ========================================================================
    
    def track_research_error(self, error_type: str, component: str, 
                           severity: str = 'error'):
        """Track research system errors"""
        RESEARCH_ERRORS_TOTAL.labels(
            error_type=error_type,
            component=component,
            severity=severity
        ).inc()
        
        # Also log to observability system
        if observability:
            observability.add_sentry_breadcrumb(
                f"Research error: {error_type}",
                category="research_monitoring",
                data={
                    "component": component,
                    "severity": severity,
                    "error_type": error_type
                },
                level=severity
            )
    
    def update_circuit_breaker_state(self, service: str, endpoint: str, 
                                   state: str):
        """Update circuit breaker state (closed=0, open=1, half-open=2)"""
        state_value = {'closed': 0, 'open': 1, 'half-open': 2}.get(state, 0)
        
        RESEARCH_CIRCUIT_BREAKER_STATE.labels(
            service=service,
            endpoint=endpoint
        ).set(state_value)
    
    def track_retry_attempt(self, operation: str, retry_reason: str, 
                          success: bool):
        """Track retry attempts"""
        RESEARCH_RETRY_ATTEMPTS.labels(
            operation=operation,
            retry_reason=retry_reason,
            success=str(success).lower()
        ).inc()
    
    # ========================================================================
    # Content Generation Metrics
    # ========================================================================
    
    def track_content_opportunity(self, industry: str, urgency: str, 
                                opportunity_type: str, quality_score: float):
        """Track content opportunities generated from research"""
        
        CONTENT_OPPORTUNITIES_GENERATED.labels(
            industry=industry,
            urgency=urgency,
            opportunity_type=opportunity_type
        ).inc()
        
        CONTENT_OPPORTUNITY_QUALITY.labels(
            industry=industry,
            opportunity_type=opportunity_type
        ).observe(quality_score)
    
    def track_content_conversion(self, conversion_type: str, industry: str, 
                               success: bool):
        """Track research-to-content conversion"""
        RESEARCH_CONTENT_CONVERSION.labels(
            conversion_type=conversion_type,
            industry=industry,
            success=str(success).lower()
        ).inc()
    
    # ========================================================================
    # Health and Status Reporting
    # ========================================================================
    
    def get_research_system_health(self) -> Dict[str, Any]:
        """Get comprehensive research system health metrics"""
        uptime = time.time() - self.start_time
        
        return {
            "monitoring_service": {
                "status": "healthy",
                "uptime_seconds": uptime,
                "metrics_collected": True
            },
            "research_operations": {
                "tracking_enabled": True,
                "metrics_available": [
                    "request_counts", "duration_histograms", 
                    "quality_scores", "error_rates"
                ]
            },
            "vector_store": {
                "monitoring_active": True,
                "metrics_tracked": [
                    "operation_latency", "memory_usage", 
                    "vector_counts", "embedding_generation"
                ]
            },
            "quota_enforcement": {
                "tracking_enabled": True,
                "features_monitored": [
                    "knowledge_base_queries", "immediate_research",
                    "setup_industry_research", "deep_research"
                ]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def generate_usage_report(self, user_id: str, user_plan: str, 
                            days: int = 7) -> Dict[str, Any]:
        """Generate usage report for a specific user (placeholder for implementation)"""
        # This would typically query Prometheus for historical data
        # For now, return a structured response format
        
        return {
            "user_id": user_id,
            "user_plan": user_plan,
            "report_period_days": days,
            "features_used": {
                "knowledge_base_queries": "tracked",
                "immediate_research": "tracked", 
                "deep_research": "tracked",
                "vector_operations": "tracked"
            },
            "quota_utilization": "tracked_in_prometheus",
            "performance_metrics": "available_via_prometheus",
            "generated_at": datetime.utcnow().isoformat(),
            "note": "Historical data available through Prometheus queries"
        }

# Global monitoring service instance
_research_monitoring_service = None

def get_research_monitoring_service() -> ResearchMonitoringService:
    """Get the global research monitoring service instance"""
    global _research_monitoring_service
    if _research_monitoring_service is None:
        _research_monitoring_service = ResearchMonitoringService()
    return _research_monitoring_service

# Context manager for automatic research operation tracking
class ResearchOperationTracker:
    """Context manager for automatic research operation tracking"""
    
    def __init__(self, operation_type: str, user_plan: str, 
                 industry: Optional[str] = None):
        self.operation_type = operation_type
        self.user_plan = user_plan
        self.industry = industry
        self.start_time = None
        self.monitoring_service = get_research_monitoring_service()
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        
        metrics = ResearchMetrics(
            operation_type=self.operation_type,
            duration=duration,
            success=success,
            user_plan=self.user_plan,
            industry=self.industry,
            error_type=exc_type.__name__ if exc_type else None
        )
        
        self.monitoring_service.record_research_operation(metrics)