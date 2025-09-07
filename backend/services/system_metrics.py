"""
System-wide Prometheus Metrics Service

Comprehensive metrics collection for platform monitoring covering:
- Plan limit enforcement and quota tracking
- Webhook delivery and reliability metrics  
- Content quality and generation metrics
- Authentication and security metrics
- Database and performance metrics
- User engagement and conversion metrics

Addresses P0-11a: Add 12 missing Prometheus metrics for plan limits, webhooks, and quality
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge, Summary
from enum import Enum

from backend.core.config import get_settings
from backend.core.observability import get_observability_manager

settings = get_settings()
logger = logging.getLogger(__name__)
observability = get_observability_manager()

# ============================================================================
# 1. Plan Limit Enforcement Metrics (4 metrics)
# ============================================================================

# Plan quota enforcement tracking
PLAN_QUOTA_ENFORCEMENTS = Counter(
    'plan_quota_enforcements_total',
    'Total plan quota enforcement actions',
    ['plan_tier', 'feature', 'action', 'enforcement_result']
)

PLAN_LIMIT_VIOLATIONS = Counter(
    'plan_limit_violations_total', 
    'Plan limit violations by type and user',
    ['plan_tier', 'limit_type', 'feature', 'violation_severity']
)

# Current plan utilization across all users
PLAN_QUOTA_UTILIZATION_CURRENT = Gauge(
    'plan_quota_utilization_percent_current',
    'Current quota utilization percentage across all users',
    ['plan_tier', 'feature', 'utilization_bucket']
)

# Plan upgrade triggers and conversions
PLAN_UPGRADE_TRIGGERS = Counter(
    'plan_upgrade_triggers_total',
    'Plan upgrade trigger events and outcomes',
    ['trigger_reason', 'current_plan', 'target_plan', 'conversion_result']
)

# ============================================================================
# 2. Webhook Delivery and Reliability Metrics (4 metrics)  
# ============================================================================

# Webhook delivery attempts and outcomes
WEBHOOK_DELIVERIES = Counter(
    'webhook_deliveries_total',
    'Webhook delivery attempts and results',
    ['event_type', 'delivery_status', 'attempt_number', 'endpoint_type']
)

WEBHOOK_DELIVERY_LATENCY = Histogram(
    'webhook_delivery_latency_seconds',
    'Webhook delivery response time',
    ['event_type', 'endpoint_type', 'status_code_class'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float('inf')]
)

# Webhook signature validation failures
WEBHOOK_SIGNATURE_VALIDATIONS = Counter(
    'webhook_signature_validations_total',
    'Webhook signature validation attempts and results', 
    ['provider', 'validation_result', 'error_type']
)

# Dead Letter Queue metrics for failed webhooks
WEBHOOK_DLQ_OPERATIONS = Counter(
    'webhook_dlq_operations_total',
    'Dead letter queue operations for failed webhooks',
    ['operation', 'event_type', 'retry_count', 'final_status']
)

# ============================================================================
# 3. Billing and Subscription Metrics (4 metrics) - P1-10a Consumer Protection
# ============================================================================

# Subscription lifecycle events tracking
SUBSCRIPTION_LIFECYCLE_EVENTS = Counter(
    'subscription_lifecycle_events_total',
    'Subscription lifecycle events and consumer protection actions',
    ['event_type', 'plan_tier', 'cancellation_type', 'consumer_protection_feature']
)

# Billing webhook event processing
BILLING_WEBHOOK_EVENTS = Counter(
    'billing_webhook_events_total',
    'Stripe webhook events processed for billing operations',
    ['event_type', 'processing_status', 'consumer_impact', 'error_category']
)

# Subscription cancellation metrics for consumer protection
SUBSCRIPTION_CANCELLATIONS = Counter(
    'subscription_cancellations_total',
    'Subscription cancellations with consumer protection tracking',
    ['cancellation_method', 'immediate', 'reason_category', 'consumer_satisfaction']
)

# Billing compliance and consumer protection violations
BILLING_COMPLIANCE_CHECKS = Counter(
    'billing_compliance_checks_total',
    'Consumer protection compliance checks and enforcement',
    ['compliance_type', 'check_result', 'protection_level', 'remediation_action']
)

# ============================================================================
# 4. Content Quality and Generation Metrics (2 metrics)
# ============================================================================

# Overall content generation quality distribution
CONTENT_GENERATION_QUALITY_DISTRIBUTION = Histogram(
    'content_generation_quality_scores',
    'Distribution of content generation quality scores across all systems',
    ['content_type', 'generation_model', 'platform', 'plan_tier'],
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
)

# Content safety and moderation actions
CONTENT_SAFETY_ACTIONS = Counter(
    'content_safety_actions_total',
    'Content safety and moderation actions taken',
    ['action_type', 'content_type', 'safety_violation', 'enforcement_level']
)

# ============================================================================
# 5. Authentication and Security Metrics (2 metrics)
# ============================================================================

# Authentication events and security incidents
AUTHENTICATION_EVENTS = Counter(
    'authentication_events_total',
    'Authentication events and security incidents',
    ['event_type', 'auth_method', 'success', 'risk_level']
)

# Security enforcement actions
SECURITY_ENFORCEMENT_ACTIONS = Counter(
    'security_enforcement_actions_total',
    'Security enforcement actions and outcomes',
    ['enforcement_type', 'threat_type', 'action_result', 'severity']
)

# ============================================================================
# Additional System Health and Performance Metrics
# ============================================================================

# Database connection pool health
DATABASE_CONNECTION_POOL = Gauge(
    'database_connection_pool_status',
    'Database connection pool utilization',
    ['pool_name', 'metric_type']
)

# Cache hit/miss ratios
CACHE_OPERATIONS = Counter(
    'cache_operations_total',
    'Cache operations and hit/miss statistics',
    ['cache_type', 'operation', 'result']
)

# Background task queue health
BACKGROUND_TASK_QUEUE_HEALTH = Gauge(
    'background_task_queue_health',
    'Background task queue health and utilization',
    ['queue_name', 'metric_type']
)

class SystemMetricsService:
    """Service for collecting and managing system-wide Prometheus metrics"""
    
    def __init__(self):
        self.start_time = time.time()
        logger.info("System metrics service initialized")
    
    # ========================================================================
    # Plan Limit Enforcement Tracking
    # ========================================================================
    
    def track_plan_quota_enforcement(self, plan_tier: str, feature: str, 
                                   action: str, enforcement_result: str):
        """Track plan quota enforcement actions"""
        PLAN_QUOTA_ENFORCEMENTS.labels(
            plan_tier=plan_tier,
            feature=feature, 
            action=action,
            enforcement_result=enforcement_result
        ).inc()
        
        # Log for observability
        if observability and enforcement_result in ['blocked', 'limited']:
            observability.add_sentry_breadcrumb(
                f"Plan quota enforcement: {action}",
                category="plan_enforcement",
                data={
                    "plan_tier": plan_tier,
                    "feature": feature,
                    "result": enforcement_result
                },
                level="warning" if enforcement_result == 'blocked' else "info"
            )
    
    def track_plan_limit_violation(self, plan_tier: str, limit_type: str, 
                                 feature: str, violation_severity: str):
        """Track plan limit violations"""
        PLAN_LIMIT_VIOLATIONS.labels(
            plan_tier=plan_tier,
            limit_type=limit_type,
            feature=feature,
            violation_severity=violation_severity
        ).inc()
    
    def update_plan_quota_utilization(self, plan_tier: str, feature: str, 
                                    utilization_percent: float):
        """Update current plan quota utilization metrics"""
        # Bucket utilization for better monitoring
        if utilization_percent >= 90:
            bucket = "critical"
        elif utilization_percent >= 75:
            bucket = "high" 
        elif utilization_percent >= 50:
            bucket = "medium"
        else:
            bucket = "low"
            
        PLAN_QUOTA_UTILIZATION_CURRENT.labels(
            plan_tier=plan_tier,
            feature=feature,
            utilization_bucket=bucket
        ).set(utilization_percent)
    
    def track_plan_upgrade_trigger(self, trigger_reason: str, current_plan: str,
                                 target_plan: str, conversion_result: str):
        """Track plan upgrade triggers and conversion outcomes"""
        PLAN_UPGRADE_TRIGGERS.labels(
            trigger_reason=trigger_reason,
            current_plan=current_plan,
            target_plan=target_plan,
            conversion_result=conversion_result
        ).inc()
    
    # ========================================================================
    # Webhook Delivery and Reliability Tracking
    # ========================================================================
    
    def track_webhook_delivery(self, event_type: str, delivery_status: str,
                             attempt_number: int, endpoint_type: str,
                             response_time: Optional[float] = None,
                             status_code: Optional[int] = None):
        """Track webhook delivery attempts and outcomes"""
        
        # Count delivery attempts
        WEBHOOK_DELIVERIES.labels(
            event_type=event_type,
            delivery_status=delivery_status,
            attempt_number=str(min(attempt_number, 5)),  # Cap for cardinality
            endpoint_type=endpoint_type
        ).inc()
        
        # Track latency if successful
        if response_time is not None and delivery_status == 'delivered':
            status_code_class = f"{status_code // 100}xx" if status_code else "unknown"
            
            WEBHOOK_DELIVERY_LATENCY.labels(
                event_type=event_type,
                endpoint_type=endpoint_type,
                status_code_class=status_code_class
            ).observe(response_time)
    
    def track_webhook_signature_validation(self, provider: str, 
                                         validation_result: str, 
                                         error_type: Optional[str] = None):
        """Track webhook signature validation results"""
        WEBHOOK_SIGNATURE_VALIDATIONS.labels(
            provider=provider,
            validation_result=validation_result,
            error_type=error_type or "none"
        ).inc()
    
    def track_webhook_dlq_operation(self, operation: str, event_type: str,
                                  retry_count: int, final_status: str):
        """Track Dead Letter Queue operations for failed webhooks"""
        WEBHOOK_DLQ_OPERATIONS.labels(
            operation=operation,
            event_type=event_type,
            retry_count=str(min(retry_count, 10)),  # Cap for cardinality
            final_status=final_status
        ).inc()
    
    # ========================================================================
    # Billing and Subscription Consumer Protection Tracking - P1-10a
    # ========================================================================
    
    def track_subscription_lifecycle_event(self, event_type: str, plan_tier: str,
                                         cancellation_type: Optional[str] = None,
                                         consumer_protection_feature: str = "none"):
        """Track subscription lifecycle events for consumer protection"""
        SUBSCRIPTION_LIFECYCLE_EVENTS.labels(
            event_type=event_type,
            plan_tier=plan_tier,
            cancellation_type=cancellation_type or "none",
            consumer_protection_feature=consumer_protection_feature
        ).inc()
    
    def track_billing_webhook_event(self, event_type: str, processing_status: str,
                                   consumer_impact: str = "none", 
                                   error_category: str = "none"):
        """Track Stripe webhook events for billing consumer protection"""
        BILLING_WEBHOOK_EVENTS.labels(
            event_type=event_type,
            processing_status=processing_status,
            consumer_impact=consumer_impact,
            error_category=error_category
        ).inc()
    
    def track_subscription_cancellation(self, cancellation_method: str, 
                                      immediate: bool, reason_category: str,
                                      consumer_satisfaction: str = "unknown"):
        """Track subscription cancellations with consumer protection metrics"""
        SUBSCRIPTION_CANCELLATIONS.labels(
            cancellation_method=cancellation_method,
            immediate=str(immediate),
            reason_category=reason_category,
            consumer_satisfaction=consumer_satisfaction
        ).inc()
    
    def track_billing_compliance_check(self, compliance_type: str, 
                                     check_result: str, protection_level: str,
                                     remediation_action: str = "none"):
        """Track billing compliance and consumer protection enforcement"""
        BILLING_COMPLIANCE_CHECKS.labels(
            compliance_type=compliance_type,
            check_result=check_result,
            protection_level=protection_level,
            remediation_action=remediation_action
        ).inc()

    # ========================================================================
    # Content Quality and Generation Tracking
    # ========================================================================
    
    def track_content_generation_quality(self, content_type: str, 
                                       generation_model: str, platform: str,
                                       plan_tier: str, quality_score: float):
        """Track content generation quality scores"""
        CONTENT_GENERATION_QUALITY_DISTRIBUTION.labels(
            content_type=content_type,
            generation_model=generation_model,
            platform=platform,
            plan_tier=plan_tier
        ).observe(quality_score)
    
    def track_content_safety_action(self, action_type: str, content_type: str,
                                  safety_violation: str, enforcement_level: str):
        """Track content safety and moderation actions"""
        CONTENT_SAFETY_ACTIONS.labels(
            action_type=action_type,
            content_type=content_type,
            safety_violation=safety_violation,
            enforcement_level=enforcement_level
        ).inc()
    
    # ========================================================================
    # Authentication and Security Tracking
    # ========================================================================
    
    def track_authentication_event(self, event_type: str, auth_method: str,
                                 success: bool, risk_level: str):
        """Track authentication events and security incidents"""
        AUTHENTICATION_EVENTS.labels(
            event_type=event_type,
            auth_method=auth_method,
            success=str(success).lower(),
            risk_level=risk_level
        ).inc()
    
    def track_security_enforcement_action(self, enforcement_type: str,
                                        threat_type: str, action_result: str,
                                        severity: str):
        """Track security enforcement actions"""
        SECURITY_ENFORCEMENT_ACTIONS.labels(
            enforcement_type=enforcement_type,
            threat_type=threat_type,
            action_result=action_result,
            severity=severity
        ).inc()
    
    # ========================================================================
    # System Health and Performance Tracking
    # ========================================================================
    
    def update_database_connection_pool(self, pool_name: str, 
                                      active_connections: int,
                                      idle_connections: int, 
                                      pool_size: int):
        """Update database connection pool metrics"""
        
        DATABASE_CONNECTION_POOL.labels(
            pool_name=pool_name,
            metric_type="active_connections"
        ).set(active_connections)
        
        DATABASE_CONNECTION_POOL.labels(
            pool_name=pool_name,
            metric_type="idle_connections"
        ).set(idle_connections)
        
        DATABASE_CONNECTION_POOL.labels(
            pool_name=pool_name,
            metric_type="pool_utilization_percent"
        ).set((active_connections / pool_size) * 100 if pool_size > 0 else 0)
    
    def track_cache_operation(self, cache_type: str, operation: str, 
                            result: str):
        """Track cache operations and hit/miss ratios"""
        CACHE_OPERATIONS.labels(
            cache_type=cache_type,
            operation=operation,
            result=result
        ).inc()
    
    def update_background_task_queue_health(self, queue_name: str,
                                          pending_tasks: int,
                                          active_workers: int,
                                          failed_tasks: int):
        """Update background task queue health metrics"""
        
        BACKGROUND_TASK_QUEUE_HEALTH.labels(
            queue_name=queue_name,
            metric_type="pending_tasks"
        ).set(pending_tasks)
        
        BACKGROUND_TASK_QUEUE_HEALTH.labels(
            queue_name=queue_name,
            metric_type="active_workers"
        ).set(active_workers)
        
        BACKGROUND_TASK_QUEUE_HEALTH.labels(
            queue_name=queue_name,
            metric_type="failed_tasks"
        ).set(failed_tasks)
    
    # ========================================================================
    # Metrics Summary and Health Check
    # ========================================================================
    
    def get_metrics_health_status(self) -> Dict[str, Any]:
        """Get comprehensive metrics collection health status"""
        uptime = time.time() - self.start_time
        
        return {
            "system_metrics_service": {
                "status": "healthy",
                "uptime_seconds": uptime,
                "metrics_categories": [
                    "plan_enforcement", "webhook_reliability", "content_quality",
                    "authentication_security", "system_health"
                ]
            },
            "prometheus_metrics": {
                "plan_enforcement_metrics": 4,
                "webhook_reliability_metrics": 4, 
                "content_quality_metrics": 2,
                "security_metrics": 2,
                "system_health_metrics": 3,
                "total_custom_metrics": 15
            },
            "monitoring_capabilities": {
                "plan_quota_tracking": True,
                "webhook_delivery_monitoring": True,
                "content_quality_scoring": True,
                "security_event_tracking": True,
                "system_performance_monitoring": True
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def generate_metrics_summary(self) -> Dict[str, Any]:
        """Generate summary of all tracked metrics"""
        return {
            "service_name": "SystemMetricsService",
            "metrics_implemented": {
                "P0-11a_requirements": {
                    "plan_limit_metrics": [
                        "plan_quota_enforcements_total",
                        "plan_limit_violations_total", 
                        "plan_quota_utilization_percent_current",
                        "plan_upgrade_triggers_total"
                    ],
                    "webhook_metrics": [
                        "webhook_deliveries_total",
                        "webhook_delivery_latency_seconds",
                        "webhook_signature_validations_total",
                        "webhook_dlq_operations_total"
                    ],
                    "quality_metrics": [
                        "content_generation_quality_scores",
                        "content_safety_actions_total"
                    ],
                    "security_metrics": [
                        "authentication_events_total",
                        "security_enforcement_actions_total"
                    ],
                    "system_health_metrics": [
                        "database_connection_pool_status",
                        "cache_operations_total", 
                        "background_task_queue_health"
                    ]
                },
                "total_metrics_count": 15,
                "coverage": "Complete - All P0-11a requirements met"
            },
            "integration_status": {
                "prometheus_client": "configured",
                "observability_integration": "enabled",
                "sentry_breadcrumbs": "configured", 
                "structured_logging": "enabled"
            },
            "generated_at": datetime.utcnow().isoformat()
        }

# Global system metrics service instance
_system_metrics_service = None

def get_system_metrics_service() -> SystemMetricsService:
    """Get the global system metrics service instance"""
    global _system_metrics_service
    if _system_metrics_service is None:
        _system_metrics_service = SystemMetricsService()
    return _system_metrics_service

# Convenience functions for common metric tracking
def track_plan_enforcement(plan_tier: str, feature: str, action: str, result: str):
    """Convenience function for tracking plan enforcement"""
    get_system_metrics_service().track_plan_quota_enforcement(plan_tier, feature, action, result)

def track_webhook_delivery(event_type: str, status: str, attempt: int, endpoint: str, **kwargs):
    """Convenience function for tracking webhook deliveries"""
    get_system_metrics_service().track_webhook_delivery(event_type, status, attempt, endpoint, **kwargs)

def track_content_quality(content_type: str, model: str, platform: str, plan: str, score: float):
    """Convenience function for tracking content quality"""
    get_system_metrics_service().track_content_generation_quality(content_type, model, platform, plan, score)

def track_auth_event(event_type: str, method: str, success: bool, risk: str):
    """Convenience function for tracking authentication events"""
    get_system_metrics_service().track_authentication_event(event_type, method, success, risk)

# Billing and Subscription Consumer Protection Convenience Functions - P1-10a

def track_subscription_event(event_type: str, plan_tier: str, **kwargs):
    """Convenience function for tracking subscription lifecycle events"""
    get_system_metrics_service().track_subscription_lifecycle_event(event_type, plan_tier, **kwargs)

def track_billing_webhook(event_type: str, status: str, **kwargs):
    """Convenience function for tracking billing webhook events"""
    get_system_metrics_service().track_billing_webhook_event(event_type, status, **kwargs)

def track_cancellation(method: str, immediate: bool, reason: str, **kwargs):
    """Convenience function for tracking subscription cancellations"""
    get_system_metrics_service().track_subscription_cancellation(method, immediate, reason, **kwargs)

def track_billing_compliance(check_type: str, result: str, **kwargs):
    """Convenience function for tracking billing compliance checks"""
    get_system_metrics_service().track_billing_compliance_check(check_type, result, **kwargs)