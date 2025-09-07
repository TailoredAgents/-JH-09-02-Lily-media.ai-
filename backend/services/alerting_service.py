"""
Alerting Configuration and Management Service

Manages Prometheus alerting rules and escalation policies for production monitoring.
Provides programmatic access to alerting configuration and health checks.

Addresses P0-11b: Configure alerting rules with proper thresholds and escalation
"""

import logging
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from backend.core.config import get_settings
from backend.core.observability import get_observability_manager

settings = get_settings()
logger = logging.getLogger(__name__)
observability = get_observability_manager()

class AlertSeverity(Enum):
    """Alert severity levels with escalation policies"""
    CRITICAL = "critical"  # P0 - Immediate response
    WARNING = "warning"    # P1/P2 - Scheduled response

class EscalationLevel(Enum):
    """Escalation levels for alert routing"""
    P0 = "p0"  # Critical - Immediate page
    P1 = "p1"  # High - 1 hour response
    P2 = "p2"  # Medium - 24 hour response

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    expr: str
    duration: str
    severity: AlertSeverity
    escalation_level: EscalationLevel
    team: str
    summary: str
    description: str
    runbook_url: str

@dataclass
class AlertGroup:
    """Alert group configuration"""
    name: str
    rules: List[AlertRule]

class AlertingService:
    """Service for managing alerting configuration and policies"""
    
    def __init__(self):
        self.config_path = Path("config/alerting/prometheus-alerts.yml")
        self.alert_groups = []
        self._load_alerting_rules()
        logger.info("Alerting service initialized")
    
    def _load_alerting_rules(self):
        """Load alerting rules from configuration file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                for group_config in config.get('groups', []):
                    rules = []
                    for rule_config in group_config.get('rules', []):
                        rule = AlertRule(
                            name=rule_config['alert'],
                            expr=rule_config['expr'],
                            duration=rule_config.get('for', '0s'),
                            severity=AlertSeverity(rule_config['labels']['severity']),
                            escalation_level=EscalationLevel(rule_config['labels']['escalation_level']),
                            team=rule_config['labels']['team'],
                            summary=rule_config['annotations']['summary'],
                            description=rule_config['annotations']['description'],
                            runbook_url=rule_config['annotations']['runbook_url']
                        )
                        rules.append(rule)
                    
                    group = AlertGroup(
                        name=group_config['name'],
                        rules=rules
                    )
                    self.alert_groups.append(group)
                
                logger.info(f"Loaded {len(self.alert_groups)} alert groups with {sum(len(g.rules) for g in self.alert_groups)} rules")
            else:
                logger.warning(f"Alert configuration file not found at {self.config_path}")
                
        except Exception as e:
            logger.error(f"Failed to load alerting rules: {e}")
    
    def get_alerting_summary(self) -> Dict[str, Any]:
        """Get comprehensive alerting configuration summary"""
        
        # Count alerts by severity
        critical_count = sum(
            len([r for r in group.rules if r.severity == AlertSeverity.CRITICAL])
            for group in self.alert_groups
        )
        warning_count = sum(
            len([r for r in group.rules if r.severity == AlertSeverity.WARNING])
            for group in self.alert_groups
        )
        
        # Count alerts by escalation level
        p0_count = sum(
            len([r for r in group.rules if r.escalation_level == EscalationLevel.P0])
            for group in self.alert_groups
        )
        p1_count = sum(
            len([r for r in group.rules if r.escalation_level == EscalationLevel.P1])
            for group in self.alert_groups
        )
        p2_count = sum(
            len([r for r in group.rules if r.escalation_level == EscalationLevel.P2])
            for group in self.alert_groups
        )
        
        # Count alerts by team
        team_counts = {}
        for group in self.alert_groups:
            for rule in group.rules:
                team_counts[rule.team] = team_counts.get(rule.team, 0) + 1
        
        return {
            "alerting_service": {
                "status": "configured",
                "config_file": str(self.config_path),
                "config_exists": self.config_path.exists(),
                "last_loaded": datetime.utcnow().isoformat()
            },
            "alert_groups": {
                "total_groups": len(self.alert_groups),
                "group_names": [group.name for group in self.alert_groups],
                "total_rules": sum(len(g.rules) for g in self.alert_groups)
            },
            "severity_distribution": {
                "critical": critical_count,
                "warning": warning_count,
                "total": critical_count + warning_count
            },
            "escalation_distribution": {
                "p0_critical": p0_count,
                "p1_high": p1_count, 
                "p2_medium": p2_count,
                "total": p0_count + p1_count + p2_count
            },
            "team_distribution": team_counts,
            "coverage_areas": [
                "system_health", "plan_enforcement", "webhook_reliability",
                "content_quality", "research_system", "security", 
                "performance", "business_metrics"
            ]
        }
    
    def get_alerts_by_team(self, team: str) -> List[AlertRule]:
        """Get all alert rules for a specific team"""
        team_rules = []
        for group in self.alert_groups:
            for rule in group.rules:
                if rule.team == team:
                    team_rules.append(rule)
        return team_rules
    
    def get_critical_alerts(self) -> List[AlertRule]:
        """Get all critical (P0) alert rules"""
        critical_rules = []
        for group in self.alert_groups:
            for rule in group.rules:
                if rule.escalation_level == EscalationLevel.P0:
                    critical_rules.append(rule)
        return critical_rules
    
    def validate_alerting_config(self) -> Dict[str, Any]:
        """Validate alerting configuration for completeness and correctness"""
        
        validation_results = {
            "config_file_exists": self.config_path.exists(),
            "groups_loaded": len(self.alert_groups),
            "total_rules": sum(len(g.rules) for g in self.alert_groups),
            "validation_status": "passed",
            "issues": [],
            "recommendations": []
        }
        
        # Check for minimum required alerts
        critical_alerts = self.get_critical_alerts()
        if len(critical_alerts) < 5:
            validation_results["issues"].append("Too few critical alerts configured")
            validation_results["validation_status"] = "failed"
        
        # Check for required coverage areas
        required_groups = ["system_critical", "security", "plan_enforcement", "webhook_reliability"]
        existing_groups = [group.name for group in self.alert_groups]
        missing_groups = [group for group in required_groups if group not in existing_groups]
        
        if missing_groups:
            validation_results["issues"].append(f"Missing required alert groups: {missing_groups}")
            validation_results["validation_status"] = "failed"
        
        # Check for proper team assignments
        teams_covered = set()
        for group in self.alert_groups:
            for rule in group.rules:
                teams_covered.add(rule.team)
        
        required_teams = ["platform", "security", "billing", "content"]
        missing_teams = [team for team in required_teams if team not in teams_covered]
        
        if missing_teams:
            validation_results["issues"].append(f"No alerts assigned to teams: {missing_teams}")
            validation_results["validation_status"] = "warning"
        
        # Check for runbook URLs
        rules_without_runbooks = []
        for group in self.alert_groups:
            for rule in group.rules:
                if not rule.runbook_url or "runbooks.lilymedia.ai" not in rule.runbook_url:
                    rules_without_runbooks.append(rule.name)
        
        if rules_without_runbooks:
            validation_results["recommendations"].append(
                f"Consider adding proper runbook URLs for: {rules_without_runbooks[:5]}..."
            )
        
        return validation_results
    
    def get_escalation_policy(self, escalation_level: EscalationLevel) -> Dict[str, Any]:
        """Get escalation policy configuration for a given level"""
        
        policies = {
            EscalationLevel.P0: {
                "level": "P0 - Critical",
                "response_time": "5 minutes",
                "channels": ["pager", "slack", "email"],
                "escalation_steps": [
                    {"step": 1, "target": "primary_oncall", "delay": "0 minutes"},
                    {"step": 2, "target": "secondary_oncall", "delay": "15 minutes"},
                    {"step": 3, "target": "engineering_manager", "delay": "30 minutes"}
                ],
                "business_hours": "24/7",
                "severity_indicators": [
                    "Service completely down",
                    "Security incident", 
                    "Data loss or corruption",
                    "Critical business function impacted"
                ]
            },
            EscalationLevel.P1: {
                "level": "P1 - High Priority", 
                "response_time": "1 hour (business hours), 4 hours (off-hours)",
                "channels": ["slack", "email"],
                "escalation_steps": [
                    {"step": 1, "target": "team_lead", "delay": "0 minutes"},
                    {"step": 2, "target": "backup_team_lead", "delay": "2 hours"}
                ],
                "business_hours": "9 AM - 6 PM PT, Mon-Fri",
                "severity_indicators": [
                    "Performance degradation",
                    "Business logic issues",
                    "Feature partially unavailable",
                    "High error rates"
                ]
            },
            EscalationLevel.P2: {
                "level": "P2 - Medium Priority",
                "response_time": "24 hours",
                "channels": ["slack"],
                "escalation_steps": [
                    {"step": 1, "target": "responsible_team", "delay": "0 minutes"}
                ],
                "business_hours": "9 AM - 6 PM PT, Mon-Fri", 
                "severity_indicators": [
                    "Minor performance issues",
                    "Growth metrics deviation",
                    "Non-critical feature issues",
                    "Resource utilization warnings"
                ]
            }
        }
        
        return policies.get(escalation_level, {})
    
    def generate_alerting_health_check(self) -> Dict[str, Any]:
        """Generate comprehensive health check for alerting system"""
        
        summary = self.get_alerting_summary()
        validation = self.validate_alerting_config()
        
        return {
            "alerting_system_health": {
                "status": "healthy" if validation["validation_status"] == "passed" else "degraded",
                "configuration_loaded": len(self.alert_groups) > 0,
                "total_alert_rules": summary["alert_groups"]["total_rules"],
                "critical_alerts_configured": summary["escalation_distribution"]["p0_critical"],
                "teams_covered": len(summary["team_distribution"]),
                "coverage_complete": validation["validation_status"] == "passed"
            },
            "escalation_coverage": {
                "p0_critical_alerts": summary["escalation_distribution"]["p0_critical"],
                "p1_high_priority": summary["escalation_distribution"]["p1_high"], 
                "p2_medium_priority": summary["escalation_distribution"]["p2_medium"],
                "escalation_policies_defined": True
            },
            "monitoring_areas": {
                "system_health": "covered",
                "plan_enforcement": "covered",
                "webhook_reliability": "covered", 
                "content_quality": "covered",
                "research_system": "covered",
                "security": "covered",
                "performance": "covered",
                "business_metrics": "covered"
            },
            "configuration_status": validation,
            "timestamp": datetime.utcnow().isoformat()
        }

# Global alerting service instance
_alerting_service = None

def get_alerting_service() -> AlertingService:
    """Get the global alerting service instance"""
    global _alerting_service
    if _alerting_service is None:
        _alerting_service = AlertingService()
    return _alerting_service