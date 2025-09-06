"""
Enhanced Alerting System for SRE Operations
Provides intelligent alerting, notification routing, and escalation policies
"""
import asyncio
import json
import logging
import smtplib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable
from urllib.parse import urlencode
import aiohttp

from backend.core.config import settings
from backend.services.redis_cache import redis_cache

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class AlertStatus(Enum):
    """Alert lifecycle status"""
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"

@dataclass
class Alert:
    """Individual alert definition"""
    id: str
    name: str
    description: str
    severity: AlertSeverity
    source: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.FIRING
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    escalation_level: int = 0
    last_notification_sent: Optional[datetime] = None

@dataclass
class NotificationChannel:
    """Notification delivery channel"""
    name: str
    type: str  # email, slack, webhook, pagerduty
    config: Dict[str, Any]
    enabled: bool = True
    severity_filter: List[AlertSeverity] = field(default_factory=list)

@dataclass
class EscalationPolicy:
    """Alert escalation configuration"""
    name: str
    steps: List[Dict[str, Any]]  # [{"wait_minutes": 15, "channels": ["email"]}, ...]
    enabled: bool = True

class AlertingService:
    """
    Comprehensive alerting system with intelligent routing and escalation
    
    Features:
    - Multi-channel notifications (email, Slack, webhooks, PagerDuty)
    - Smart alert aggregation and deduplication
    - Escalation policies with time-based triggers
    - Alert acknowledgment and resolution tracking
    - Integration with monitoring metrics
    - Runbook automation triggers
    """
    
    def __init__(self):
        self.active_alerts: Dict[str, Alert] = {}
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self.escalation_policies: Dict[str, EscalationPolicy] = {}
        self.alert_history: List[Alert] = []
        self.max_history_size = 10000
        
        # Initialize default notification channels
        self._setup_default_channels()
        self._setup_default_escalation_policies()
        
        # Background processing will be started when event loop is available
        self._processor_task = None
        
        logger.info("Alerting service initialized")
    
    def _setup_default_channels(self):
        """Setup default notification channels"""
        
        # Email notifications
        if hasattr(settings, 'SMTP_SERVER') and settings.SMTP_SERVER:
            self.notification_channels["email_critical"] = NotificationChannel(
                name="Critical Email Alerts",
                type="email",
                config={
                    "smtp_server": getattr(settings, 'SMTP_SERVER', 'localhost'),
                    "smtp_port": getattr(settings, 'SMTP_PORT', 587),
                    "smtp_user": getattr(settings, 'SMTP_USER', ''),
                    "smtp_password": getattr(settings, 'SMTP_PASSWORD', ''),
                    "from_email": getattr(settings, 'ALERT_FROM_EMAIL', 'alerts@example.com'),
                    "to_emails": getattr(settings, 'CRITICAL_ALERT_EMAILS', 'ops@example.com').split(',')
                },
                severity_filter=[AlertSeverity.CRITICAL, AlertSeverity.HIGH]
            )
        
        # Slack notifications
        if hasattr(settings, 'SLACK_WEBHOOK_URL') and settings.SLACK_WEBHOOK_URL:
            self.notification_channels["slack_ops"] = NotificationChannel(
                name="Operations Slack Channel",
                type="slack",
                config={
                    "webhook_url": settings.SLACK_WEBHOOK_URL,
                    "channel": getattr(settings, 'SLACK_ALERTS_CHANNEL', '#alerts'),
                    "username": "AlertBot"
                },
                severity_filter=[AlertSeverity.CRITICAL, AlertSeverity.HIGH, AlertSeverity.MEDIUM]
            )
        
        # PagerDuty integration
        if hasattr(settings, 'PAGERDUTY_API_KEY') and settings.PAGERDUTY_API_KEY:
            self.notification_channels["pagerduty"] = NotificationChannel(
                name="PagerDuty Integration",
                type="pagerduty",
                config={
                    "api_key": settings.PAGERDUTY_API_KEY,
                    "service_id": getattr(settings, 'PAGERDUTY_SERVICE_ID', ''),
                },
                severity_filter=[AlertSeverity.CRITICAL]
            )
    
    def _setup_default_escalation_policies(self):
        """Setup default escalation policies"""
        
        self.escalation_policies["critical_escalation"] = EscalationPolicy(
            name="Critical Alert Escalation",
            steps=[
                {"wait_minutes": 0, "channels": ["slack_ops", "email_critical"]},
                {"wait_minutes": 15, "channels": ["pagerduty"]},
                {"wait_minutes": 30, "channels": ["email_critical"]}  # Re-notify
            ]
        )
        
        self.escalation_policies["standard_escalation"] = EscalationPolicy(
            name="Standard Alert Escalation", 
            steps=[
                {"wait_minutes": 0, "channels": ["slack_ops"]},
                {"wait_minutes": 60, "channels": ["email_critical"]}
            ]
        )
    
    async def fire_alert(self, alert: Alert) -> str:
        """Fire a new alert or update existing one"""
        
        # Start processor if not already running
        if self._processor_task is None or self._processor_task.done():
            try:
                self._processor_task = asyncio.create_task(self._alert_processor())
            except RuntimeError:
                # No event loop running, processor will be started later
                pass
        
        # Check for existing alert
        existing_alert = self.active_alerts.get(alert.id)
        
        if existing_alert:
            # Update existing alert
            existing_alert.timestamp = alert.timestamp
            existing_alert.annotations.update(alert.annotations)
            existing_alert.labels.update(alert.labels)
            
            logger.info(f"Updated existing alert: {alert.id}")
            return alert.id
        
        # Store new alert
        self.active_alerts[alert.id] = alert
        
        # Add to history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size:]
        
        # Store in Redis for persistence
        await redis_cache.set(
            f"alert:{alert.id}",
            json.dumps(self._serialize_alert(alert)),
            expire=86400 * 7  # 7 days
        )
        
        logger.warning(f"Alert fired: {alert.name} [{alert.severity.value}] - {alert.description}")
        
        # Trigger immediate notification for critical alerts
        if alert.severity == AlertSeverity.CRITICAL:
            await self._send_notifications(alert)
        
        return alert.id
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an active alert"""
        
        alert = self.active_alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.utcnow()
        
        # Update in Redis
        await redis_cache.set(
            f"alert:{alert_id}",
            json.dumps(self._serialize_alert(alert)),
            expire=86400 * 7
        )
        
        logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
        
        # Send acknowledgment notification
        await self._send_acknowledgment_notification(alert)
        
        return True
    
    async def resolve_alert(self, alert_id: str, resolved_by: Optional[str] = None) -> bool:
        """Resolve an active alert"""
        
        alert = self.active_alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        
        # Remove from active alerts
        del self.active_alerts[alert_id]
        
        # Update in Redis
        await redis_cache.set(
            f"alert:{alert_id}",
            json.dumps(self._serialize_alert(alert)),
            expire=86400 * 30  # Keep resolved alerts for 30 days
        )
        
        logger.info(f"Alert resolved: {alert_id}")
        
        # Send resolution notification
        await self._send_resolution_notification(alert)
        
        return True
    
    async def get_active_alerts(self, severity_filter: Optional[List[AlertSeverity]] = None) -> List[Alert]:
        """Get all active alerts, optionally filtered by severity"""
        
        alerts = list(self.active_alerts.values())
        
        if severity_filter:
            alerts = [a for a in alerts if a.severity in severity_filter]
        
        return sorted(alerts, key=lambda a: (a.severity.value, a.timestamp), reverse=True)
    
    async def get_alert_metrics(self) -> Dict[str, Any]:
        """Get alerting system metrics"""
        
        now = datetime.utcnow()
        last_24h = now - timedelta(days=1)
        
        recent_alerts = [a for a in self.alert_history if a.timestamp >= last_24h]
        
        return {
            "active_alerts": len(self.active_alerts),
            "alerts_last_24h": len(recent_alerts),
            "critical_alerts": len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.CRITICAL]),
            "acknowledged_alerts": len([a for a in self.active_alerts.values() if a.status == AlertStatus.ACKNOWLEDGED]),
            "notification_channels": len([c for c in self.notification_channels.values() if c.enabled]),
            "escalation_policies": len([p for p in self.escalation_policies.values() if p.enabled]),
            "alerts_by_source": self._get_alerts_by_source(),
            "mean_time_to_acknowledge": self._calculate_mtta(),
            "mean_time_to_resolve": self._calculate_mttr()
        }
    
    def _get_alerts_by_source(self) -> Dict[str, int]:
        """Get alert counts grouped by source"""
        sources = {}
        for alert in self.active_alerts.values():
            sources[alert.source] = sources.get(alert.source, 0) + 1
        return sources
    
    def _calculate_mtta(self) -> Optional[float]:
        """Calculate Mean Time To Acknowledge in minutes"""
        acknowledged_alerts = [
            a for a in self.alert_history 
            if a.acknowledged_at and a.timestamp
        ]
        
        if not acknowledged_alerts:
            return None
        
        total_time = sum(
            (a.acknowledged_at - a.timestamp).total_seconds() 
            for a in acknowledged_alerts
        )
        
        return (total_time / len(acknowledged_alerts)) / 60  # Convert to minutes
    
    def _calculate_mttr(self) -> Optional[float]:
        """Calculate Mean Time To Resolve in minutes"""
        resolved_alerts = [
            a for a in self.alert_history 
            if a.resolved_at and a.timestamp
        ]
        
        if not resolved_alerts:
            return None
        
        total_time = sum(
            (a.resolved_at - a.timestamp).total_seconds() 
            for a in resolved_alerts
        )
        
        return (total_time / len(resolved_alerts)) / 60  # Convert to minutes
    
    async def _alert_processor(self):
        """Background task to process alerts and handle escalations"""
        
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = datetime.utcnow()
                
                for alert in list(self.active_alerts.values()):
                    if alert.status == AlertStatus.FIRING:
                        await self._process_escalation(alert, current_time)
                
            except Exception as e:
                logger.error(f"Alert processor error: {e}")
    
    async def _process_escalation(self, alert: Alert, current_time: datetime):
        """Process alert escalation based on policies"""
        
        # Determine escalation policy
        policy_name = "critical_escalation" if alert.severity == AlertSeverity.CRITICAL else "standard_escalation"
        policy = self.escalation_policies.get(policy_name)
        
        if not policy or not policy.enabled:
            return
        
        # Check if it's time for next escalation step
        alert_age_minutes = (current_time - alert.timestamp).total_seconds() / 60
        
        for step_index, step in enumerate(policy.steps):
            if step_index <= alert.escalation_level:
                continue
            
            wait_minutes = step["wait_minutes"]
            
            if alert_age_minutes >= wait_minutes:
                # Time for escalation
                alert.escalation_level = step_index
                await self._send_notifications(alert, step["channels"])
                
                logger.info(f"Alert escalated: {alert.id} to level {step_index}")
                break
    
    async def _send_notifications(self, alert: Alert, channel_names: Optional[List[str]] = None):
        """Send notifications through specified channels"""
        
        if channel_names is None:
            # Use all applicable channels based on severity
            channel_names = [
                name for name, channel in self.notification_channels.items()
                if channel.enabled and (
                    not channel.severity_filter or alert.severity in channel.severity_filter
                )
            ]
        
        for channel_name in channel_names:
            channel = self.notification_channels.get(channel_name)
            if channel and channel.enabled:
                try:
                    await self._send_notification(alert, channel)
                except Exception as e:
                    logger.error(f"Failed to send notification via {channel_name}: {e}")
        
        alert.last_notification_sent = datetime.utcnow()
    
    async def _send_notification(self, alert: Alert, channel: NotificationChannel):
        """Send notification through specific channel"""
        
        if channel.type == "email":
            await self._send_email_notification(alert, channel)
        elif channel.type == "slack":
            await self._send_slack_notification(alert, channel)
        elif channel.type == "webhook":
            await self._send_webhook_notification(alert, channel)
        elif channel.type == "pagerduty":
            await self._send_pagerduty_notification(alert, channel)
    
    async def _send_email_notification(self, alert: Alert, channel: NotificationChannel):
        """Send email notification"""
        
        config = channel.config
        
        try:
            msg = MIMEMultipart()
            msg['From'] = config['from_email']
            msg['To'] = ', '.join(config['to_emails'])
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.name}"
            
            body = f"""
Alert: {alert.name}
Severity: {alert.severity.value.upper()}
Source: {alert.source}
Time: {alert.timestamp.isoformat()}
Description: {alert.description}

Labels: {json.dumps(alert.labels, indent=2)}
Annotations: {json.dumps(alert.annotations, indent=2)}

Alert ID: {alert.id}
Status: {alert.status.value}
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            
            if config['smtp_user']:
                server.login(config['smtp_user'], config['smtp_password'])
            
            server.sendmail(config['from_email'], config['to_emails'], msg.as_string())
            server.quit()
            
            logger.info(f"Email notification sent for alert {alert.id}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            raise
    
    async def _send_slack_notification(self, alert: Alert, channel: NotificationChannel):
        """Send Slack notification"""
        
        config = channel.config
        
        color = {
            AlertSeverity.CRITICAL: "danger",
            AlertSeverity.HIGH: "warning", 
            AlertSeverity.MEDIUM: "warning",
            AlertSeverity.LOW: "good",
            AlertSeverity.INFO: "good"
        }.get(alert.severity, "warning")
        
        payload = {
            "channel": config.get("channel", "#alerts"),
            "username": config.get("username", "AlertBot"),
            "attachments": [{
                "color": color,
                "title": f"[{alert.severity.value.upper()}] {alert.name}",
                "text": alert.description,
                "fields": [
                    {"title": "Source", "value": alert.source, "short": True},
                    {"title": "Alert ID", "value": alert.id, "short": True},
                    {"title": "Time", "value": alert.timestamp.isoformat(), "short": True},
                    {"title": "Status", "value": alert.status.value, "short": True}
                ],
                "timestamp": int(alert.timestamp.timestamp())
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(config['webhook_url'], json=payload) as resp:
                if resp.status != 200:
                    raise Exception(f"Slack webhook returned {resp.status}")
        
        logger.info(f"Slack notification sent for alert {alert.id}")
    
    async def _send_webhook_notification(self, alert: Alert, channel: NotificationChannel):
        """Send generic webhook notification"""
        
        config = channel.config
        
        payload = {
            "alert": self._serialize_alert(alert),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        headers = config.get("headers", {"Content-Type": "application/json"})
        
        async with aiohttp.ClientSession() as session:
            async with session.post(config['url'], json=payload, headers=headers) as resp:
                if resp.status not in [200, 201, 202]:
                    raise Exception(f"Webhook returned {resp.status}")
        
        logger.info(f"Webhook notification sent for alert {alert.id}")
    
    async def _send_pagerduty_notification(self, alert: Alert, channel: NotificationChannel):
        """Send PagerDuty notification"""
        
        config = channel.config
        
        payload = {
            "routing_key": config['api_key'],
            "event_action": "trigger",
            "dedup_key": alert.id,
            "payload": {
                "summary": f"{alert.name}: {alert.description}",
                "severity": alert.severity.value,
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat(),
                "custom_details": {
                    "labels": alert.labels,
                    "annotations": alert.annotations
                }
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload
            ) as resp:
                if resp.status != 202:
                    raise Exception(f"PagerDuty API returned {resp.status}")
        
        logger.info(f"PagerDuty notification sent for alert {alert.id}")
    
    async def _send_acknowledgment_notification(self, alert: Alert):
        """Send notification that alert was acknowledged"""
        
        # Send simplified notification to Slack only
        slack_channel = self.notification_channels.get("slack_ops")
        if slack_channel and slack_channel.enabled:
            try:
                payload = {
                    "channel": slack_channel.config.get("channel", "#alerts"),
                    "username": slack_channel.config.get("username", "AlertBot"),
                    "text": f"✅ Alert acknowledged: {alert.name} by {alert.acknowledged_by}"
                }
                
                async with aiohttp.ClientSession() as session:
                    await session.post(slack_channel.config['webhook_url'], json=payload)
            
            except Exception as e:
                logger.error(f"Failed to send acknowledgment notification: {e}")
    
    async def _send_resolution_notification(self, alert: Alert):
        """Send notification that alert was resolved"""
        
        # Send simplified notification to Slack only
        slack_channel = self.notification_channels.get("slack_ops")
        if slack_channel and slack_channel.enabled:
            try:
                duration = ""
                if alert.resolved_at and alert.timestamp:
                    duration_seconds = (alert.resolved_at - alert.timestamp).total_seconds()
                    duration = f" (duration: {int(duration_seconds/60)}min)"
                
                payload = {
                    "channel": slack_channel.config.get("channel", "#alerts"),
                    "username": slack_channel.config.get("username", "AlertBot"),
                    "text": f"✅ Alert resolved: {alert.name}{duration}"
                }
                
                async with aiohttp.ClientSession() as session:
                    await session.post(slack_channel.config['webhook_url'], json=payload)
            
            except Exception as e:
                logger.error(f"Failed to send resolution notification: {e}")
    
    def _serialize_alert(self, alert: Alert) -> Dict[str, Any]:
        """Serialize alert for storage/transmission"""
        
        return {
            "id": alert.id,
            "name": alert.name,
            "description": alert.description,
            "severity": alert.severity.value,
            "source": alert.source,
            "timestamp": alert.timestamp.isoformat(),
            "status": alert.status.value,
            "labels": alert.labels,
            "annotations": alert.annotations,
            "acknowledged_by": alert.acknowledged_by,
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            "escalation_level": alert.escalation_level,
            "last_notification_sent": alert.last_notification_sent.isoformat() if alert.last_notification_sent else None
        }

# Global alerting service instance
alerting_service = AlertingService()

# Convenience functions for creating alerts
async def fire_critical_alert(name: str, description: str, source: str, **kwargs) -> str:
    """Fire a critical severity alert"""
    
    alert = Alert(
        id=f"{source}_{name}_{int(time.time())}".replace(" ", "_").lower(),
        name=name,
        description=description,
        severity=AlertSeverity.CRITICAL,
        source=source,
        timestamp=datetime.utcnow(),
        labels=kwargs.get("labels", {}),
        annotations=kwargs.get("annotations", {})
    )
    
    return await alerting_service.fire_alert(alert)

async def fire_high_alert(name: str, description: str, source: str, **kwargs) -> str:
    """Fire a high severity alert"""
    
    alert = Alert(
        id=f"{source}_{name}_{int(time.time())}".replace(" ", "_").lower(),
        name=name,
        description=description,
        severity=AlertSeverity.HIGH,
        source=source,
        timestamp=datetime.utcnow(),
        labels=kwargs.get("labels", {}),
        annotations=kwargs.get("annotations", {})
    )
    
    return await alerting_service.fire_alert(alert)

async def fire_medium_alert(name: str, description: str, source: str, **kwargs) -> str:
    """Fire a medium severity alert"""
    
    alert = Alert(
        id=f"{source}_{name}_{int(time.time())}".replace(" ", "_").lower(),
        name=name,
        description=description,
        severity=AlertSeverity.MEDIUM,
        source=source,
        timestamp=datetime.utcnow(),
        labels=kwargs.get("labels", {}),
        annotations=kwargs.get("annotations", {})
    )
    
    return await alerting_service.fire_alert(alert)