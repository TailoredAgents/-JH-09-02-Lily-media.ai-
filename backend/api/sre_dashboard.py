"""
SRE Dashboard API - Enhanced Observability and Operations
Provides comprehensive operational dashboards and SRE tools
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.db.database import get_db
from backend.auth.dependencies import get_current_active_user
from backend.db.models import User
from backend.core.monitoring import monitoring_service
from backend.core.alerting import alerting_service, AlertSeverity, Alert
from backend.core.runbooks import automated_runbooks, RunbookExecution
from backend.services.redis_cache import redis_cache
from backend.db.database_optimized import db_optimizer
from backend.services.slo_tracking_service import slo_tracking_service, get_all_slo_status, get_slo_dashboard_data
from backend.services.alerting_service import get_alerting_service

router = APIRouter(prefix="/api/sre", tags=["SRE Dashboard"])
logger = logging.getLogger(__name__)

class SREMetrics(BaseModel):
    """SRE key metrics model"""
    availability_percentage: float = Field(..., description="System availability percentage")
    error_budget_remaining: float = Field(..., description="Remaining error budget percentage")
    mean_time_to_recovery: Optional[float] = Field(None, description="MTTR in minutes")
    mean_time_to_detection: Optional[float] = Field(None, description="MTTD in minutes")
    deployment_frequency: float = Field(..., description="Deployments per week")
    change_failure_rate: float = Field(..., description="Change failure rate percentage")

class ServiceLevelObjective(BaseModel):
    """Service Level Objective definition"""
    name: str
    description: str
    target_percentage: float
    current_percentage: float
    error_budget_hours: float
    error_budget_consumed: float
    status: str  # healthy, at_risk, violated

class IncidentSummary(BaseModel):
    """Incident summary model"""
    total_incidents: int
    open_incidents: int
    incidents_this_month: int
    avg_resolution_time_hours: float
    severity_breakdown: Dict[str, int]

@router.get("/dashboard/overview", response_model=Dict[str, Any])
async def get_sre_overview(current_user: User = Depends(get_current_active_user)):
    """
    Get comprehensive SRE dashboard overview
    
    Provides high-level SRE metrics, SLO status, and system health
    """
    try:
        # Get system health
        health_status = await monitoring_service.get_health_status()
        
        # Get alerting metrics
        alert_metrics = await alerting_service.get_alert_metrics()
        
        # Calculate SRE metrics
        sre_metrics = await _calculate_sre_metrics()
        
        # Get SLO status
        slos = await _get_service_level_objectives()
        
        # Get incident summary
        incident_summary = await _get_incident_summary()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "sre_metrics": sre_metrics,
            "service_level_objectives": slos,
            "incident_summary": incident_summary,
            "system_health": health_status,
            "alert_metrics": alert_metrics,
            "operational_status": {
                "runbooks_available": len(automated_runbooks.runbooks),
                "active_runbook_executions": len(automated_runbooks.active_executions),
                "monitoring_systems": {
                    "prometheus_available": monitoring_service.prometheus.prometheus_available if hasattr(monitoring_service.prometheus, 'prometheus_available') else False,
                    "sentry_initialized": monitoring_service.sentry.initialized if hasattr(monitoring_service, 'sentry') else False,
                    "alerting_channels": len(alerting_service.notification_channels)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting SRE overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/slos", response_model=List[ServiceLevelObjective])
async def get_service_level_objectives(current_user: User = Depends(get_current_active_user)):
    """
    Get current Service Level Objectives status
    
    Returns all defined SLOs with current performance metrics
    """
    try:
        return await _get_service_level_objectives()
        
    except Exception as e:
        logger.error(f"Error getting SLOs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/error-budget/{slo_name}")
async def get_error_budget_details(
    slo_name: str,
    days: int = 30,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get detailed error budget analysis for specific SLO
    
    Args:
        slo_name: Name of the SLO to analyze
        days: Number of days to analyze (default 30)
    """
    try:
        error_budget_data = await _calculate_error_budget_details(slo_name, days)
        return error_budget_data
        
    except Exception as e:
        logger.error(f"Error getting error budget details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/incidents", response_model=Dict[str, Any])
async def get_incident_dashboard(
    days: int = 30,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get incident management dashboard
    
    Args:
        days: Number of days of incident history to include
    """
    try:
        # Get active alerts (current incidents)
        active_alerts = await alerting_service.get_active_alerts()
        
        # Get alert metrics
        alert_metrics = await alerting_service.get_alert_metrics()
        
        # Calculate incident trends
        incident_trends = await _calculate_incident_trends(days)
        
        return {
            "active_incidents": len(active_alerts),
            "incident_summary": await _get_incident_summary(),
            "incident_trends": incident_trends,
            "recent_alerts": [
                {
                    "id": alert.id,
                    "name": alert.name,
                    "severity": alert.severity.value,
                    "source": alert.source,
                    "timestamp": alert.timestamp.isoformat(),
                    "status": alert.status.value,
                    "acknowledged": alert.status.value == "acknowledged"
                }
                for alert in active_alerts[:20]  # Last 20 alerts
            ],
            "alert_metrics": alert_metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting incident dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/incidents/{alert_id}/acknowledge")
async def acknowledge_incident(
    alert_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Acknowledge an active incident/alert
    
    Args:
        alert_id: ID of the alert to acknowledge
    """
    try:
        success = await alerting_service.acknowledge_alert(alert_id, current_user.email)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "success": True,
            "alert_id": alert_id,
            "acknowledged_by": current_user.email,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/incidents/{alert_id}/resolve")
async def resolve_incident(
    alert_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Resolve an active incident/alert
    
    Args:
        alert_id: ID of the alert to resolve
    """
    try:
        success = await alerting_service.resolve_alert(alert_id, current_user.email)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "success": True,
            "alert_id": alert_id,
            "resolved_by": current_user.email,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runbooks", response_model=Dict[str, Any])
async def get_runbooks_dashboard(current_user: User = Depends(get_current_active_user)):
    """
    Get automated runbooks dashboard
    
    Shows available runbooks, execution history, and current status
    """
    try:
        return {
            "available_runbooks": {
                runbook_id: {
                    "id": runbook_id,
                    "steps": len(steps),
                    "estimated_duration": sum(step.timeout_seconds for step in steps),
                    "critical_steps": sum(1 for step in steps if step.critical)
                }
                for runbook_id, steps in automated_runbooks.runbooks.items()
            },
            "active_executions": {
                exec_id: {
                    "runbook_id": execution.runbook_id,
                    "status": execution.status.value,
                    "progress": f"{execution.completed_steps}/{execution.total_steps}",
                    "started_at": execution.started_at.isoformat(),
                    "triggered_by": execution.triggered_by
                }
                for exec_id, execution in automated_runbooks.active_executions.items()
            },
            "recent_executions": [
                {
                    "runbook_id": execution.runbook_id,
                    "status": execution.status.value,
                    "started_at": execution.started_at.isoformat(),
                    "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
                    "duration_minutes": (
                        (execution.finished_at - execution.started_at).total_seconds() / 60
                        if execution.finished_at else None
                    ),
                    "success_rate": execution.completed_steps / execution.total_steps * 100
                }
                for execution in automated_runbooks.execution_history[-20:]  # Last 20 executions
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting runbooks dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/runbooks/{runbook_id}/execute")
async def execute_runbook(
    runbook_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Execute an automated runbook
    
    Args:
        runbook_id: ID of the runbook to execute
    """
    try:
        execution_id = await automated_runbooks.execute_runbook(
            runbook_id,
            f"manual_{current_user.email}"
        )
        
        return {
            "success": True,
            "execution_id": execution_id,
            "runbook_id": runbook_id,
            "triggered_by": current_user.email,
            "started_at": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing runbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runbooks/executions/{execution_id}")
async def get_runbook_execution_status(
    execution_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get status of a runbook execution
    
    Args:
        execution_id: ID of the execution to check
    """
    try:
        execution = await automated_runbooks.get_execution_status(execution_id)
        
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return {
            "execution_id": execution_id,
            "runbook_id": execution.runbook_id,
            "status": execution.status.value,
            "started_at": execution.started_at.isoformat(),
            "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
            "current_step": execution.current_step,
            "completed_steps": execution.completed_steps,
            "total_steps": execution.total_steps,
            "progress_percentage": (execution.completed_steps / execution.total_steps * 100),
            "errors": execution.errors,
            "results": execution.results,
            "triggered_by": execution.triggered_by
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting runbook execution status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/prometheus/metrics")
async def get_prometheus_metrics(current_user: User = Depends(get_current_active_user)):
    """
    Get Prometheus metrics in text format
    
    Returns metrics compatible with Prometheus scraping
    """
    try:
        metrics = monitoring_service.get_prometheus_metrics()
        return {"metrics": metrics}
        
    except Exception as e:
        logger.error(f"Error getting Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/capacity-planning")
async def get_capacity_planning_data(
    days: int = 30,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get capacity planning data and projections
    
    Args:
        days: Number of days of historical data to analyze
    """
    try:
        capacity_data = await _calculate_capacity_metrics(days)
        return capacity_data
        
    except Exception as e:
        logger.error(f"Error getting capacity planning data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance-trends")
async def get_performance_trends(
    hours: int = 24,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get system performance trends
    
    Args:
        hours: Number of hours of trend data to return
    """
    try:
        trends_data = await _calculate_performance_trends(hours)
        return trends_data
        
    except Exception as e:
        logger.error(f"Error getting performance trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/webhook")
async def receive_prometheus_webhook(webhook_data: Dict[str, Any]):
    """
    Receive Prometheus Alertmanager webhook and trigger runbooks
    
    This endpoint receives webhooks from Prometheus Alertmanager and automatically
    triggers appropriate runbooks for remediation.
    
    P1-8c Implementation: Integrate SRE runbooks with monitoring alerts
    """
    try:
        alerting_service = get_alerting_service()
        execution_ids = await alerting_service.process_prometheus_webhook(webhook_data)
        
        return {
            "status": "processed",
            "webhook_received_at": datetime.utcnow().isoformat(),
            "alerts_processed": len(webhook_data.get("alerts", [])),
            "runbooks_triggered": len(execution_ids),
            "execution_ids": execution_ids
        }
        
    except Exception as e:
        logger.error(f"Error processing Prometheus webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runbooks/integration-status")
async def get_runbook_integration_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get runbook integration status for monitoring
    
    Returns the current status of runbook integration with alerts
    """
    try:
        alerting_service = get_alerting_service()
        status = alerting_service.get_runbook_integration_status()
        return status
        
    except Exception as e:
        logger.error(f"Error getting runbook integration status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def _calculate_sre_metrics() -> SREMetrics:
    """Calculate key SRE metrics"""
    
    # Calculate availability (example: 99.9% uptime)
    availability = 99.95  # This would be calculated from actual uptime data
    
    # Calculate error budget remaining
    target_availability = 99.9
    error_budget_remaining = max(0, (availability - target_availability) / (100 - target_availability) * 100)
    
    # Get alert metrics for MTTR calculation
    alert_metrics = await alerting_service.get_alert_metrics()
    
    return SREMetrics(
        availability_percentage=availability,
        error_budget_remaining=error_budget_remaining,
        mean_time_to_recovery=alert_metrics.get("mean_time_to_resolve"),
        mean_time_to_detection=alert_metrics.get("mean_time_to_acknowledge"),
        deployment_frequency=2.5,  # Deployments per week
        change_failure_rate=2.0    # 2% change failure rate
    )

async def _get_service_level_objectives() -> List[ServiceLevelObjective]:
    """Get current SLO status using real tracking service"""
    try:
        # Get all SLO status from tracking service
        slo_statuses = await get_all_slo_status()
        
        slos = []
        for slo_name, status in slo_statuses.items():
            slo_model = ServiceLevelObjective(
                name=status.slo.name,
                description=status.slo.description,
                target_percentage=status.target_percentage,
                current_percentage=status.current_percentage,
                error_budget_hours=status.error_budget_hours,
                error_budget_consumed=(1.0 - status.error_budget_remaining) * status.error_budget_hours,
                status=status.status.value
            )
            slos.append(slo_model)
        
        return slos
        
    except Exception as e:
        logger.error(f"Failed to get SLO status: {e}")
        # Fallback to empty list if service unavailable
        return []

async def _get_incident_summary() -> IncidentSummary:
    """Get incident summary statistics"""
    
    # Get current active alerts
    active_alerts = await alerting_service.get_active_alerts()
    alert_metrics = await alerting_service.get_alert_metrics()
    
    # Calculate severity breakdown
    severity_breakdown = {}
    for alert in active_alerts:
        severity = alert.severity.value
        severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1
    
    return IncidentSummary(
        total_incidents=alert_metrics.get("alerts_last_24h", 0),
        open_incidents=len(active_alerts),
        incidents_this_month=alert_metrics.get("alerts_last_24h", 0) * 30,  # Rough estimate
        avg_resolution_time_hours=(alert_metrics.get("mean_time_to_resolve", 0) / 60),  # Convert from minutes
        severity_breakdown=severity_breakdown
    )

async def _calculate_error_budget_details(slo_name: str, days: int) -> Dict[str, Any]:
    """Calculate detailed error budget analysis"""
    
    # This would analyze actual metrics data
    return {
        "slo_name": slo_name,
        "period_days": days,
        "target_percentage": 99.9,
        "actual_percentage": 99.95,
        "error_budget_total": 8.76 * (days/30),  # Scale monthly budget
        "error_budget_consumed": 2.1 * (days/30),
        "error_budget_remaining": 6.66 * (days/30),
        "burn_rate": 0.24,  # Error budget burn rate per day
        "projected_exhaustion_date": None,  # Would be calculated if burning fast
        "daily_breakdown": [
            {
                "date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"),
                "availability": 99.95 + (i * 0.001),  # Example trend
                "error_budget_consumed": 0.1 * i
            }
            for i in range(min(days, 30))  # Limit to 30 days of daily data
        ]
    }

async def _calculate_incident_trends(days: int) -> Dict[str, Any]:
    """Calculate incident trends over specified period"""
    
    return {
        "period_days": days,
        "total_incidents": 15,
        "incidents_by_severity": {
            "critical": 2,
            "high": 5, 
            "medium": 6,
            "low": 2
        },
        "incidents_by_source": {
            "database": 4,
            "external_apis": 6,
            "infrastructure": 3,
            "application": 2
        },
        "resolution_time_trend": [
            {"week": 1, "avg_resolution_minutes": 45},
            {"week": 2, "avg_resolution_minutes": 38},
            {"week": 3, "avg_resolution_minutes": 42},
            {"week": 4, "avg_resolution_minutes": 35}
        ],
        "mttr_trend": "improving",  # improving, stable, degrading
        "incident_frequency": 3.75  # incidents per week
    }

async def _calculate_capacity_metrics(days: int) -> Dict[str, Any]:
    """Calculate capacity planning metrics using real data"""
    try:
        # Get current capacity utilization from monitoring
        current_capacity = {
            "vector_store_memory_mb": monitoring_service.get_vector_store_memory_usage(),
            "database_connections": monitoring_service.get_database_connection_pool_usage(),
            "api_requests_per_hour": monitoring_service.get_current_request_rate() * 3600,
            "vector_store_size": monitoring_service.get_vector_store_size(),
        }
        
        # Calculate capacity utilization percentages
        database_pool_util = slo_tracking_service.calculate_capacity_utilization(
            "database_connections", 
            current_capacity["database_connections"], 
            100  # Assuming 100 max connections
        )
        
        vector_memory_util = slo_tracking_service.calculate_capacity_utilization(
            "vector_store_memory",
            current_capacity["vector_store_memory_mb"],
            2048  # 2GB memory limit
        )
        
        # Get growth trends (simulate with realistic data)
        growth_trends = {
            "vector_store_growth_vectors_per_day": monitoring_service.get_vector_growth_rate() * 24,
            "api_traffic_growth_percent_per_month": 8.5,  # Realistic SaaS growth
            "memory_usage_growth_percent_per_month": 5.2,
            "database_growth_percent_per_month": 3.8
        }
        
        # Generate capacity warnings based on utilization
        warnings = []
        if vector_memory_util > 80:
            warnings.append({
                "resource": "vector_store_memory",
                "current_utilization": vector_memory_util,
                "projected_exhaustion": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                "recommendation": "Consider increasing vector store memory allocation"
            })
        
        if database_pool_util > 75:
            warnings.append({
                "resource": "database_connections", 
                "current_utilization": database_pool_util,
                "projected_exhaustion": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
                "recommendation": "Scale database connection pool or add read replicas"
            })
        
        return {
            "period_days": days,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_capacity": {
                "vector_store_memory_mb": current_capacity["vector_store_memory_mb"],
                "database_connection_utilization_percent": database_pool_util,
                "vector_memory_utilization_percent": vector_memory_util,
                "api_requests_per_hour": current_capacity["api_requests_per_hour"],
                "vector_store_size": current_capacity["vector_store_size"]
            },
            "growth_trends": growth_trends,
            "capacity_warnings": warnings,
            "recommendations": [
                "Monitor vector store memory usage trend",
                "Consider implementing vector pruning for old embeddings",
                "Plan database scaling for Q2 growth projections"
            ],
            "scaling_recommendations": [
                "Consider adding horizontal database replicas",
                "Implement Redis memory optimization",
                "Scale API server instances for peak traffic"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate capacity metrics: {e}")
        # Fallback data
        return {
            "period_days": days,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_capacity": {
                "status": "monitoring_unavailable"
            },
            "error": str(e)
        }

async def _calculate_performance_trends(hours: int) -> Dict[str, Any]:
    """Calculate system performance trends"""
    
    # Generate example trend data
    hourly_data = []
    for i in range(hours):
        timestamp = datetime.utcnow() - timedelta(hours=i)
        hourly_data.append({
            "timestamp": timestamp.isoformat(),
            "response_time_ms": 85 + (i % 10) * 5,  # Example fluctuation
            "error_rate": 0.5 + (i % 5) * 0.1,
            "throughput_rpm": 150 + (i % 8) * 10
        })
    
    return {
        "period_hours": hours,
        "hourly_metrics": list(reversed(hourly_data)),  # Most recent first
        "performance_summary": {
            "avg_response_time_ms": 92.5,
            "p95_response_time_ms": 125.0,
            "p99_response_time_ms": 180.0,
            "avg_error_rate": 0.8,
            "avg_throughput_rpm": 165
        },
        "performance_alerts": [
            {
                "metric": "response_time",
                "threshold": 100,
                "current_value": 125,
                "status": "warning"
            }
        ]
    }