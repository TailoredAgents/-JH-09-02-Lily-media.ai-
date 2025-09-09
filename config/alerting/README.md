# Prometheus Alerting Configuration

This directory contains the production alerting configuration for the Lily AI Social Media platform.

## Overview

The alerting system provides comprehensive monitoring coverage across all critical platform components with proper escalation policies.

### Alert Configuration

- **Configuration File**: `prometheus-alerts.yml`
- **Total Alert Rules**: 25 rules across 8 groups
- **Escalation Levels**: P0 (Critical), P1 (High), P2 (Medium)

### Alert Groups

1. **system_critical** (3 rules) - Critical system health
2. **plan_enforcement** (3 rules) - Subscription plan enforcement
3. **webhook_reliability** (4 rules) - Webhook delivery reliability
4. **content_quality** (3 rules) - Content generation quality
5. **research_system** (3 rules) - Research system health
6. **security** (3 rules) - Security and authentication
7. **performance** (4 rules) - System performance
8. **business_metrics** (2 rules) - Business KPIs

### Escalation Policies

#### P0 - Critical (6 alerts)
- **Response Time**: <5 minutes
- **Escalation**: Primary → Secondary → Manager (15 min intervals)
- **Channels**: PagerDuty + Slack + Email
- **Examples**: Service down, security attacks, database issues

#### P1 - High Priority (13 alerts)
- **Response Time**: <1 hour (business), <4 hours (off-hours)
- **Escalation**: Primary → Secondary (2 hour intervals)
- **Channels**: Slack + Email
- **Examples**: Performance degradation, webhook failures, content issues

#### P2 - Medium Priority (6 alerts)
- **Response Time**: <24 hours
- **Escalation**: Slack notification only
- **Channels**: Slack
- **Examples**: Resource warnings, business metrics, minor performance

### Team Assignments

- **Platform Team** (7 alerts): System health, performance, infrastructure
- **Security Team** (4 alerts): Authentication, security enforcement
- **Integrations Team** (3 alerts): Webhook reliability, partner APIs
- **Research Team** (3 alerts): Research system, vector store performance
- **Growth Team** (3 alerts): Business metrics, user engagement
- **Billing Team** (2 alerts): Plan enforcement, quota violations
- **Content Team** (2 alerts): Content quality, image generation
- **Safety Team** (1 alert): Content safety violations

## Usage

### Loading Configuration

```python
from backend.services.alerting_service import get_alerting_service

service = get_alerting_service()
summary = service.get_alerting_summary()
```

### Validation

The alerting service automatically validates:
- Configuration file existence and syntax
- Required alert groups and coverage
- Team assignments
- Runbook URL presence
- Escalation policy completeness

### Health Check

```python
health = service.generate_alerting_health_check()
print(f"Status: {health['alerting_system_health']['status']}")
```

## Integration

### Prometheus Configuration

Add to prometheus.yml:

```yaml
rule_files:
  - "/path/to/prometheus-alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Alertmanager Integration

Configure routing in alertmanager.yml based on labels:
- `escalation_level`: p0, p1, p2
- `team`: platform, security, etc.
- `severity`: critical, warning

### Example Routes

```yaml
routes:
  - match:
      escalation_level: p0
    receiver: 'pagerduty-critical'
    
  - match:
      escalation_level: p1
    receiver: 'slack-high-priority'
    
  - match:
      escalation_level: p2
    receiver: 'slack-medium-priority'
```

## Runbook URLs

All alerts include runbook URLs following the pattern:
`https://runbooks.lilymedia.ai/{category}/{alert-name}`

Runbooks should contain:
1. Alert description and impact
2. Immediate investigation steps
3. Common causes and solutions
4. Escalation procedures
5. Related monitoring dashboards

## Maintenance

### Adding New Alerts

1. Define alert in appropriate group in `prometheus-alerts.yml`
2. Include all required labels: `severity`, `escalation_level`, `team`
3. Add comprehensive annotations: `summary`, `description`, `runbook_url`
4. Test with `alerting_service.validate_alerting_config()`
5. Create corresponding runbook

### Modifying Thresholds

Update thresholds based on:
- Historical performance data
- False positive/negative rates
- Business impact assessment
- On-call engineer feedback

### Testing Alerts

Use Prometheus rule evaluation:

```bash
promtool test rules alerting_tests.yml
```

## Monitoring the Monitoring

The alerting system itself is monitored for:
- Configuration load errors
- Missing runbooks
- Alert fatigue (too many alerts)
- Coverage gaps
- Escalation effectiveness

Access alerting service health at `/api/observability/alerting/health`.