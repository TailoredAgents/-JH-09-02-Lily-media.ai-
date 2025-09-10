"""
SLO/SLI Tracking and Capacity Planning Service
P1-8b: Comprehensive Service Level Objective monitoring and capacity planning

This service provides:
- SLO/SLI definition and tracking
- Error budget calculation and monitoring
- Capacity planning metrics and forecasting
- Automated SLO violation alerting
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, NamedTuple
from dataclasses import dataclass, asdict
from enum import Enum
from prometheus_client import Gauge, Counter, Histogram
import numpy as np

from backend.core.monitoring import monitoring_service
from backend.core.structured_logging import structured_logger_service, LogLevel

logger = logging.getLogger(__name__)

class SLOStatus(Enum):
    """SLO status enumeration"""
    HEALTHY = "healthy"
    AT_RISK = "at_risk"
    VIOLATED = "violated"
    UNKNOWN = "unknown"

class SLIType(Enum):
    """Service Level Indicator types"""
    AVAILABILITY = "availability"
    LATENCY = "latency"
    THROUGHPUT = "throughput" 
    ERROR_RATE = "error_rate"
    CAPACITY = "capacity"

@dataclass
class SLI:
    """Service Level Indicator definition"""
    name: str
    sli_type: SLIType
    query: str
    unit: str
    description: str

@dataclass
class SLO:
    """Service Level Objective definition"""
    name: str
    service: str
    sli: SLI
    target_percentage: float  # e.g., 99.5 for 99.5% availability
    time_window_days: int     # e.g., 30 for 30-day rolling window
    description: str
    alert_threshold: float = 0.1  # Alert when error budget < 10%

@dataclass
class SLOStatus:
    """Current SLO status"""
    slo: SLO
    current_percentage: float
    target_percentage: float
    error_budget_remaining: float  # 0.0 to 1.0
    error_budget_hours: float
    status: SLOStatus
    last_updated: datetime

class SLOTrackingService:
    """
    Service Level Objective tracking and monitoring service
    P1-8b Implementation: Comprehensive SLO/SLI tracking with capacity planning
    """
    
    def __init__(self):
        # Define core SLOs for Lily Media AI platform
        self.slos = {
            "api_availability": SLO(
                name="API Availability",
                service="api",
                sli=SLI(
                    name="HTTP Success Rate",
                    sli_type=SLIType.AVAILABILITY,
                    query='(1 - (rate(http_requests_total{status=~"5.."}[${window}]) / rate(http_requests_total[${window}]))) * 100',
                    unit="percent",
                    description="Percentage of HTTP requests that succeed (non-5xx)"
                ),
                target_percentage=99.5,
                time_window_days=30,
                description="API should be available 99.5% of the time over 30 days"
            ),
            
            "api_latency": SLO(
                name="API Response Time",
                service="api", 
                sli=SLI(
                    name="P95 Latency",
                    sli_type=SLIType.LATENCY,
                    query='histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[${window}]))',
                    unit="seconds",
                    description="95th percentile API response time"
                ),
                target_percentage=95.0,  # 95% of requests under 2s
                time_window_days=7,
                description="95% of API requests should complete within 2 seconds",
                alert_threshold=0.2
            ),
            
            "database_availability": SLO(
                name="Database Availability",
                service="database",
                sli=SLI(
                    name="Query Success Rate", 
                    sli_type=SLIType.AVAILABILITY,
                    query='(1 - (rate(database_query_errors_total[${window}]) / rate(database_queries_total[${window}]))) * 100',
                    unit="percent",
                    description="Percentage of database queries that succeed"
                ),
                target_percentage=99.9,
                time_window_days=30,
                description="Database should be available 99.9% of the time over 30 days"
            ),
            
            "vector_search_performance": SLO(
                name="Vector Search Performance",
                service="vector_store",
                sli=SLI(
                    name="Search Latency P95",
                    sli_type=SLIType.LATENCY,
                    query='histogram_quantile(0.95, rate(vector_store_operations_duration_seconds_bucket{operation="search_similarity"}[${window}]))',
                    unit="seconds",
                    description="95th percentile vector search response time"
                ),
                target_percentage=90.0,  # 90% of searches under 500ms
                time_window_days=7,
                description="90% of vector searches should complete within 500ms"
            )
        }
        
        # Prometheus metrics for SLO tracking
        self.slo_status_gauge = Gauge(
            'slo_status',
            'Current SLO status (0=violated, 1=at_risk, 2=healthy)',
            ['slo_name', 'service']
        )
        
        self.slo_current_percentage = Gauge(
            'slo_current_percentage',
            'Current SLI percentage for SLO',
            ['slo_name', 'service']
        )
        
        self.error_budget_remaining = Gauge(
            'slo_error_budget_remaining',
            'Remaining error budget as fraction (0.0 to 1.0)',
            ['slo_name', 'service']
        )
        
        self.slo_violations_total = Counter(
            'slo_violations_total',
            'Total SLO violations',
            ['slo_name', 'service', 'severity']
        )
        
        # Capacity planning metrics
        self.capacity_utilization = Gauge(
            'capacity_utilization_percentage',
            'Current capacity utilization percentage',
            ['resource_type', 'component']
        )
        
        self.capacity_forecast_days = Gauge(
            'capacity_forecast_days_remaining',
            'Forecasted days until capacity limit',
            ['resource_type', 'component']
        )
        
        logger.info(f"SLO tracking service initialized with {len(self.slos)} SLOs")
    
    async def evaluate_slo_status(self, slo_name: str) -> Optional[SLOStatus]:
        """Evaluate current status of a specific SLO"""
        try:
            if slo_name not in self.slos:
                logger.error(f"Unknown SLO: {slo_name}")
                return None
            
            slo = self.slos[slo_name]
            
            # TODO: Implement Prometheus query execution
            # For now, simulate based on SLO type
            current_value = await self._query_prometheus(slo.sli.query, slo.time_window_days)
            
            if current_value is None:
                return None
            
            # Calculate error budget
            target = slo.target_percentage
            current = current_value
            
            if slo.sli.sli_type == SLIType.LATENCY:
                # For latency SLOs, calculate percentage under threshold
                threshold = 2.0 if "api" in slo_name else 0.5  # 2s for API, 500ms for vector
                percentage_under_threshold = min(100.0, (threshold / current) * 100) if current > 0 else 100.0
                current_percentage = percentage_under_threshold
            else:
                current_percentage = current
            
            # Error budget calculation
            allowed_error = 100.0 - target
            actual_error = 100.0 - current_percentage
            error_budget_consumed = actual_error / allowed_error if allowed_error > 0 else 0.0
            error_budget_remaining = max(0.0, 1.0 - error_budget_consumed)
            
            # Calculate error budget in hours
            total_hours = slo.time_window_days * 24
            error_budget_hours = error_budget_remaining * allowed_error / 100.0 * total_hours
            
            # Determine status
            if error_budget_remaining <= 0.0:
                status = SLOStatus.VIOLATED
            elif error_budget_remaining <= slo.alert_threshold:
                status = SLOStatus.AT_RISK
            else:
                status = SLOStatus.HEALTHY
            
            slo_status = SLOStatus(
                slo=slo,
                current_percentage=current_percentage,
                target_percentage=target,
                error_budget_remaining=error_budget_remaining,
                error_budget_hours=error_budget_hours,
                status=status,
                last_updated=datetime.now(timezone.utc)
            )
            
            # Update Prometheus metrics
            self._update_slo_metrics(slo_status)
            
            # Log SLO status
            self._log_slo_status(slo_status)
            
            return slo_status
            
        except Exception as e:
            logger.error(f"Failed to evaluate SLO {slo_name}: {e}")
            return None
    
    async def _query_prometheus(self, query_template: str, window_days: int) -> Optional[float]:
        """Execute Prometheus query (placeholder implementation)"""
        # TODO: Implement actual Prometheus client
        # For now, simulate realistic values
        
        if "availability" in query_template.lower():
            # Simulate 99.7% availability
            return 99.7
        elif "latency" in query_template.lower() or "duration" in query_template.lower():
            # Simulate 1.2s P95 latency 
            return 1.2
        elif "error" in query_template.lower():
            # Simulate low error rate
            return 0.3
        else:
            return 95.0
    
    def _update_slo_metrics(self, slo_status: SLOStatus):
        """Update Prometheus metrics for SLO status"""
        try:
            slo_name = slo_status.slo.name
            service = slo_status.slo.service
            
            # Map status enum to numeric value
            status_value = {
                SLOStatus.VIOLATED: 0,
                SLOStatus.AT_RISK: 1, 
                SLOStatus.HEALTHY: 2,
                SLOStatus.UNKNOWN: -1
            }[slo_status.status]
            
            self.slo_status_gauge.labels(
                slo_name=slo_name,
                service=service
            ).set(status_value)
            
            self.slo_current_percentage.labels(
                slo_name=slo_name,
                service=service
            ).set(slo_status.current_percentage)
            
            self.error_budget_remaining.labels(
                slo_name=slo_name,
                service=service
            ).set(slo_status.error_budget_remaining)
            
            # Track violations
            if slo_status.status in [SLOStatus.VIOLATED, SLOStatus.AT_RISK]:
                severity = "critical" if slo_status.status == SLOStatus.VIOLATED else "warning"
                self.slo_violations_total.labels(
                    slo_name=slo_name,
                    service=service,
                    severity=severity
                ).inc()
                
        except Exception as e:
            logger.error(f"Failed to update SLO metrics: {e}")
    
    def _log_slo_status(self, slo_status: SLOStatus):
        """Log structured SLO status event"""
        level = LogLevel.ERROR if slo_status.status == SLOStatus.VIOLATED else \
                LogLevel.WARNING if slo_status.status == SLOStatus.AT_RISK else \
                LogLevel.DEBUG
        
        message = f"SLO '{slo_status.slo.name}' status: {slo_status.status.value}"
        
        structured_logger_service.log_security_event(
            event_type="slo_evaluation",
            severity=level.value,
            message=message,
            level=level,
            metadata={
                "slo_name": slo_status.slo.name,
                "service": slo_status.slo.service,
                "current_percentage": slo_status.current_percentage,
                "target_percentage": slo_status.target_percentage,
                "error_budget_remaining": slo_status.error_budget_remaining,
                "error_budget_hours": slo_status.error_budget_hours,
                "status": slo_status.status.value
            }
        )
    
    async def evaluate_all_slos(self) -> Dict[str, SLOStatus]:
        """Evaluate all defined SLOs"""
        results = {}
        
        for slo_name in self.slos.keys():
            status = await self.evaluate_slo_status(slo_name)
            if status:
                results[slo_name] = status
        
        logger.info(f"Evaluated {len(results)} SLOs")
        return results
    
    def get_slo_summary(self) -> Dict[str, Any]:
        """Get comprehensive SLO summary for dashboards"""
        return {
            "total_slos": len(self.slos),
            "slo_definitions": {name: asdict(slo) for name, slo in self.slos.items()},
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # Capacity Planning Methods
    def calculate_capacity_utilization(self, resource_type: str, current_usage: float, 
                                     capacity_limit: float) -> float:
        """Calculate current capacity utilization percentage"""
        try:
            utilization = (current_usage / capacity_limit) * 100.0
            
            self.capacity_utilization.labels(
                resource_type=resource_type,
                component="total"
            ).set(utilization)
            
            return utilization
            
        except Exception as e:
            logger.error(f"Failed to calculate capacity utilization: {e}")
            return 0.0
    
    def forecast_capacity_exhaustion(self, resource_type: str, 
                                   usage_history: List[float],
                                   capacity_limit: float) -> Optional[int]:
        """Forecast days until capacity exhaustion based on growth trend"""
        try:
            if len(usage_history) < 7:
                return None
                
            # Simple linear regression for growth trend
            x = np.arange(len(usage_history))
            y = np.array(usage_history)
            
            # Calculate trend (slope)
            if len(x) > 1:
                trend = np.polyfit(x, y, 1)[0]  # Linear slope
            else:
                trend = 0
            
            if trend <= 0:
                return None  # No growth trend
            
            current_usage = usage_history[-1]
            remaining_capacity = capacity_limit - current_usage
            
            # Calculate days until exhaustion
            days_remaining = int(remaining_capacity / trend)
            
            self.capacity_forecast_days.labels(
                resource_type=resource_type,
                component="forecast"
            ).set(max(0, days_remaining))
            
            return max(0, days_remaining)
            
        except Exception as e:
            logger.error(f"Failed to forecast capacity: {e}")
            return None

# Global SLO tracking service instance
slo_tracking_service = SLOTrackingService()

# Convenience functions for integration
async def evaluate_slo(slo_name: str) -> Optional[SLOStatus]:
    """Evaluate a specific SLO status"""
    return await slo_tracking_service.evaluate_slo_status(slo_name)

async def get_all_slo_status() -> Dict[str, SLOStatus]:
    """Get status of all defined SLOs"""
    return await slo_tracking_service.evaluate_all_slos()

def get_slo_dashboard_data() -> Dict[str, Any]:
    """Get SLO data formatted for dashboard consumption"""
    return slo_tracking_service.get_slo_summary()

def calculate_capacity_usage(resource_type: str, usage: float, limit: float) -> float:
    """Calculate and track capacity utilization"""
    return slo_tracking_service.calculate_capacity_utilization(resource_type, usage, limit)