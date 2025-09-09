"""
Production Monitoring Dashboard API
P1-3c: Comprehensive monitoring system with real-time metrics and alerting
"""
import logging
import time
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from pydantic import BaseModel

from backend.db.database import get_db
from backend.db.models import User, ContentLog, Organization
from backend.auth.dependencies import get_current_active_user
from backend.core.monitoring import monitoring_service
from backend.core.startup_health_gates import StartupHealthGates
from backend.services.redis_cache import redis_cache

router = APIRouter(prefix="/api/monitoring/dashboard", tags=["monitoring-dashboard"])
logger = logging.getLogger(__name__)

class ComprehensiveMetrics(BaseModel):
    """Comprehensive metrics model"""
    timestamp: str
    system: Dict[str, Any]
    application: Dict[str, Any]
    database: Dict[str, Any]
    cache: Dict[str, Any]
    business: Dict[str, Any]
    health_gates: Dict[str, Any]

class AlertConfig(BaseModel):
    """Alert configuration model"""
    metric_name: str
    threshold_value: float
    comparison: str  # "greater_than", "less_than", "equals"
    severity: str    # "critical", "warning", "info"
    enabled: bool = True

class MonitoringDashboard:
    """
    Comprehensive monitoring dashboard for production environments
    P1-3c Implementation: Advanced monitoring with alerting and visualization
    """
    
    def __init__(self):
        self.alert_configs = {
            "cpu_usage": AlertConfig(
                metric_name="cpu_usage",
                threshold_value=80.0,
                comparison="greater_than",
                severity="warning",
                enabled=True
            ),
            "memory_usage": AlertConfig(
                metric_name="memory_usage", 
                threshold_value=85.0,
                comparison="greater_than",
                severity="critical",
                enabled=True
            ),
            "response_time": AlertConfig(
                metric_name="avg_response_time",
                threshold_value=2.0,
                comparison="greater_than", 
                severity="warning",
                enabled=True
            ),
            "error_rate": AlertConfig(
                metric_name="error_rate",
                threshold_value=5.0,
                comparison="greater_than",
                severity="critical",
                enabled=True
            ),
            "database_connections": AlertConfig(
                metric_name="db_connection_usage",
                threshold_value=90.0,
                comparison="greater_than",
                severity="warning",
                enabled=True
            )
        }
        
        self.metrics_cache = {}
        self.metrics_history = []
        self.alerts_history = []
        self.startup_time = datetime.utcnow()
    
    async def get_comprehensive_metrics(self, db: Session) -> ComprehensiveMetrics:
        """Get comprehensive metrics across all system components"""
        
        timestamp = datetime.utcnow().isoformat()
        
        # System metrics (CPU, Memory, Disk, Network)
        system_metrics = await self._get_system_metrics()
        
        # Application metrics (requests, errors, users)
        application_metrics = await self._get_application_metrics(db)
        
        # Database metrics (connections, query performance, health)
        database_metrics = await self._get_database_metrics(db)
        
        # Cache metrics (Redis performance, hit rates)
        cache_metrics = await self._get_cache_metrics()
        
        # Business metrics (content generation, social posts, user activity)
        business_metrics = await self._get_business_metrics(db)
        
        # Health gates status
        health_gates_metrics = await self._get_health_gates_metrics()
        
        metrics = ComprehensiveMetrics(
            timestamp=timestamp,
            system=system_metrics,
            application=application_metrics,
            database=database_metrics,
            cache=cache_metrics,
            business=business_metrics,
            health_gates=health_gates_metrics
        )
        
        # Store in history for trending
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 1000:  # Keep last 1000 entries
            self.metrics_history = self.metrics_history[-1000:]
        
        # Check alerts
        await self._check_and_fire_alerts(metrics)
        
        return metrics
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network metrics
            network_io = psutil.net_io_counters()
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                "cpu": {
                    "usage_percent": round(cpu_percent, 2),
                    "count": cpu_count,
                    "load_average": {
                        "1min": round(load_avg[0], 2),
                        "5min": round(load_avg[1], 2),
                        "15min": round(load_avg[2], 2)
                    }
                },
                "memory": {
                    "total_gb": round(memory.total / 1024**3, 2),
                    "used_gb": round(memory.used / 1024**3, 2),
                    "available_gb": round(memory.available / 1024**3, 2),
                    "usage_percent": round(memory.percent, 2),
                    "swap_total_gb": round(swap.total / 1024**3, 2),
                    "swap_used_gb": round(swap.used / 1024**3, 2),
                    "swap_percent": round(swap.percent, 2)
                },
                "disk": {
                    "total_gb": round(disk.total / 1024**3, 2),
                    "used_gb": round(disk.used / 1024**3, 2),
                    "free_gb": round(disk.free / 1024**3, 2),
                    "usage_percent": round((disk.used / disk.total) * 100, 2),
                    "io": {
                        "reads": disk_io.read_count if disk_io else 0,
                        "writes": disk_io.write_count if disk_io else 0,
                        "read_bytes": disk_io.read_bytes if disk_io else 0,
                        "write_bytes": disk_io.write_bytes if disk_io else 0
                    }
                },
                "network": {
                    "bytes_sent": network_io.bytes_sent,
                    "bytes_recv": network_io.bytes_recv,
                    "packets_sent": network_io.packets_sent,
                    "packets_recv": network_io.packets_recv
                },
                "process": {
                    "memory_mb": round(process_memory.rss / 1024**2, 2),
                    "threads": process.num_threads(),
                    "cpu_percent": round(process.cpu_percent(), 2),
                    "open_files": len(process.open_files())
                }
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {"error": str(e)}
    
    async def _get_application_metrics(self, db: Session) -> Dict[str, Any]:
        """Get application-specific metrics"""
        try:
            uptime = (datetime.utcnow() - self.startup_time).total_seconds()
            
            # Get user metrics
            total_users = db.query(func.count(User.id)).scalar() or 0
            active_users_24h = db.query(func.count(User.id)).filter(
                User.last_login >= datetime.utcnow() - timedelta(days=1)
            ).scalar() or 0
            
            # Get organization metrics
            total_orgs = db.query(func.count(Organization.id)).scalar() or 0
            
            return {
                "uptime_seconds": uptime,
                "uptime_formatted": self._format_uptime(uptime),
                "users": {
                    "total": total_users,
                    "active_24h": active_users_24h,
                    "active_ratio": round((active_users_24h / total_users) * 100, 2) if total_users > 0 else 0
                },
                "organizations": {
                    "total": total_orgs,
                    "avg_users_per_org": round(total_users / total_orgs, 2) if total_orgs > 0 else 0
                },
                "requests": {
                    "total": 0,  # Will be populated from Prometheus metrics
                    "errors": 0,  # Will be populated from Prometheus metrics
                    "error_rate": 0.0  # Calculated from above
                }
            }
        except Exception as e:
            logger.error(f"Error getting application metrics: {e}")
            return {"error": str(e)}
    
    async def _get_database_metrics(self, db: Session) -> Dict[str, Any]:
        """Get database performance metrics"""
        try:
            start_time = time.time()
            
            # Test query performance
            result = db.execute(text("SELECT 1")).fetchone()
            query_time = (time.time() - start_time) * 1000  # ms
            
            # Get connection pool info
            engine = db.get_bind()
            pool = engine.pool
            
            # Get table counts
            content_logs_count = db.query(func.count(ContentLog.id)).scalar() or 0
            users_count = db.query(func.count(User.id)).scalar() or 0
            
            return {
                "connection_health": "healthy" if result else "unhealthy",
                "query_response_time_ms": round(query_time, 2),
                "connection_pool": {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid()
                },
                "table_counts": {
                    "content_logs": content_logs_count,
                    "users": users_count
                }
            }
        except Exception as e:
            logger.error(f"Error getting database metrics: {e}")
            return {"error": str(e)}
    
    async def _get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        try:
            cache_health = await redis_cache.health_check()
            cache_stats = await redis_cache.get_cache_stats() 
            
            return {
                "status": cache_health.get("status", "unknown"),
                "response_time_ms": cache_health.get("response_time_ms", 0),
                "memory_usage": cache_stats.get("memory", {}),
                "hit_rate": cache_stats.get("hit_rate", 0.0),
                "operations": cache_stats.get("operations", {}),
                "error_count": cache_stats.get("errors", 0)
            }
        except Exception as e:
            logger.error(f"Error getting cache metrics: {e}")
            return {"error": str(e)}
    
    async def _get_business_metrics(self, db: Session) -> Dict[str, Any]:
        """Get business-specific metrics"""
        try:
            # Content generation metrics (last 24h)
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            content_generated_24h = db.query(func.count(ContentLog.id)).filter(
                ContentLog.created_at >= yesterday
            ).scalar() or 0
            
            # Get content by platform (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            content_by_platform = {}
            
            platforms = ["twitter", "instagram", "facebook", "linkedin", "tiktok"]
            for platform in platforms:
                count = db.query(func.count(ContentLog.id)).filter(
                    ContentLog.created_at >= week_ago,
                    ContentLog.platform == platform
                ).scalar() or 0
                content_by_platform[platform] = count
            
            return {
                "content": {
                    "generated_24h": content_generated_24h,
                    "generated_7d": sum(content_by_platform.values()),
                    "by_platform_7d": content_by_platform
                },
                "performance": {
                    "avg_generation_time": 0.0,  # Would track from metrics
                    "success_rate": 0.0  # Would track from metrics
                }
            }
        except Exception as e:
            logger.error(f"Error getting business metrics: {e}")
            return {"error": str(e)}
    
    async def _get_health_gates_metrics(self) -> Dict[str, Any]:
        """Get startup health gates status"""
        try:
            health_gates = StartupHealthGates()
            result = await health_gates.run_health_gates()
            
            return {
                "overall_status": "passed" if result.passed else "failed",
                "total_checks": len(result.passed_checks) + len(result.failed_checks),
                "passed_checks": len(result.passed_checks),
                "failed_checks": len(result.failed_checks),
                "execution_time_ms": round(result.execution_time * 1000, 2),
                "check_details": {
                    "passed": [{"name": check.name, "message": check.message} for check in result.passed_checks],
                    "failed": [{"name": check.name, "message": check.message} for check in result.failed_checks]
                }
            }
        except Exception as e:
            logger.error(f"Error getting health gates metrics: {e}")
            return {"error": str(e)}
    
    async def _check_and_fire_alerts(self, metrics: ComprehensiveMetrics):
        """Check metrics against thresholds and fire alerts"""
        current_alerts = []
        
        try:
            # Check CPU usage
            cpu_usage = metrics.system.get("cpu", {}).get("usage_percent", 0)
            if cpu_usage > self.alert_configs["cpu_usage"].threshold_value:
                current_alerts.append({
                    "metric": "cpu_usage",
                    "value": cpu_usage,
                    "threshold": self.alert_configs["cpu_usage"].threshold_value,
                    "severity": "warning",
                    "message": f"High CPU usage: {cpu_usage}%"
                })
            
            # Check memory usage
            memory_usage = metrics.system.get("memory", {}).get("usage_percent", 0)
            if memory_usage > self.alert_configs["memory_usage"].threshold_value:
                current_alerts.append({
                    "metric": "memory_usage",
                    "value": memory_usage,
                    "threshold": self.alert_configs["memory_usage"].threshold_value,
                    "severity": "critical",
                    "message": f"High memory usage: {memory_usage}%"
                })
            
            # Check database response time
            db_response_time = metrics.database.get("query_response_time_ms", 0) / 1000
            if db_response_time > self.alert_configs["response_time"].threshold_value:
                current_alerts.append({
                    "metric": "database_response_time",
                    "value": db_response_time,
                    "threshold": self.alert_configs["response_time"].threshold_value,
                    "severity": "warning", 
                    "message": f"Slow database response: {db_response_time:.2f}s"
                })
            
            # Store alerts in history
            if current_alerts:
                alert_entry = {
                    "timestamp": metrics.timestamp,
                    "alerts": current_alerts
                }
                self.alerts_history.append(alert_entry)
                
                # Keep only last 100 alert entries
                if len(self.alerts_history) > 100:
                    self.alerts_history = self.alerts_history[-100:]
                
                # Log critical alerts
                for alert in current_alerts:
                    if alert["severity"] == "critical":
                        logger.error(f"CRITICAL ALERT: {alert['message']}")
                    else:
                        logger.warning(f"WARNING ALERT: {alert['message']}")
        
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

# Global dashboard instance
dashboard = MonitoringDashboard()

@router.get("/metrics", response_model=ComprehensiveMetrics, summary="Comprehensive Monitoring Metrics")
async def get_comprehensive_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get comprehensive monitoring metrics across all system components
    P1-3c: Complete monitoring dashboard with real-time metrics
    """
    try:
        metrics = await dashboard.get_comprehensive_metrics(db)
        return metrics
    except Exception as e:
        logger.error(f"Error getting comprehensive metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")

@router.get("/alerts", summary="Active Alerts")
async def get_active_alerts(current_user: User = Depends(get_current_active_user)):
    """Get current active alerts and alert history"""
    try:
        # Get latest metrics to check current alerts
        current_alerts = []
        if dashboard.alerts_history:
            latest_alert_entry = dashboard.alerts_history[-1]
            # Only include alerts from last 10 minutes
            latest_time = datetime.fromisoformat(latest_alert_entry["timestamp"])
            if (datetime.utcnow() - latest_time).total_seconds() < 600:
                current_alerts = latest_alert_entry["alerts"]
        
        return {
            "active_alerts": current_alerts,
            "alert_history": dashboard.alerts_history[-20:],  # Last 20 alert entries
            "alert_configs": {name: config.dict() for name, config in dashboard.alert_configs.items()},
            "summary": {
                "active_count": len(current_alerts),
                "critical_count": len([a for a in current_alerts if a["severity"] == "critical"]),
                "warning_count": len([a for a in current_alerts if a["severity"] == "warning"])
            }
        }
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")

@router.get("/trends", summary="Metrics Trends")
async def get_metrics_trends(
    hours: int = 24,
    current_user: User = Depends(get_current_active_user)
):
    """Get metrics trends over time for dashboard visualization"""
    try:
        hours = min(hours, 168)  # Max 1 week
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter metrics history
        filtered_metrics = [
            m for m in dashboard.metrics_history
            if datetime.fromisoformat(m.timestamp) >= cutoff_time
        ]
        
        if not filtered_metrics:
            return {"message": "No metrics data available for the specified time period"}
        
        # Extract trend data
        timestamps = [m.timestamp for m in filtered_metrics]
        cpu_usage = [m.system.get("cpu", {}).get("usage_percent", 0) for m in filtered_metrics]
        memory_usage = [m.system.get("memory", {}).get("usage_percent", 0) for m in filtered_metrics]
        db_response_time = [m.database.get("query_response_time_ms", 0) for m in filtered_metrics]
        
        return {
            "period_hours": hours,
            "data_points": len(filtered_metrics),
            "trends": {
                "timestamps": timestamps,
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "database_response_time_ms": db_response_time
            },
            "averages": {
                "cpu_usage": round(sum(cpu_usage) / len(cpu_usage), 2),
                "memory_usage": round(sum(memory_usage) / len(memory_usage), 2),
                "database_response_time_ms": round(sum(db_response_time) / len(db_response_time), 2)
            }
        }
    except Exception as e:
        logger.error(f"Error getting metrics trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trends")

@router.post("/test-alert", summary="Test Alert System")
async def test_alert_system(current_user: User = Depends(get_current_active_user)):
    """Test the alerting system by generating a test alert"""
    try:
        test_alert = {
            "metric": "test_metric",
            "value": 100.0,
            "threshold": 50.0,
            "severity": "warning",
            "message": "Test alert generated for monitoring system validation"
        }
        
        alert_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "alerts": [test_alert]
        }
        
        dashboard.alerts_history.append(alert_entry)
        
        logger.warning(f"TEST ALERT: {test_alert['message']}")
        
        return {
            "success": True,
            "message": "Test alert generated successfully",
            "alert": test_alert,
            "timestamp": alert_entry["timestamp"]
        }
    except Exception as e:
        logger.error(f"Error generating test alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate test alert")