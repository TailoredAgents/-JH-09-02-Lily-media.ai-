# Production Alerting Configuration

This document describes the comprehensive alerting setup for the Lily Media AI platform, addressing P0-11b requirements for proper thresholds and escalation policies.

## Overview

The alerting system provides 24/7 monitoring coverage across all critical platform components with intelligent escalation based on severity and business impact.

### Alert Categories

1. **System Critical (P0)** - Immediate response required
2. **Plan Enforcement (P1)** - Business logic and billing issues  
3. **Webhook Reliability (P1)** - Integration and delivery monitoring
4. **Content Quality (P1)** - AI generation and safety monitoring
5. **Research System (P0/P1)** - Deep research and vector store health
6. **Security (P0/P1)** - Authentication and threat detection
7. **Performance (P2)** - Resource utilization and response times
8. **Business Metrics (P2)** - Growth and engagement monitoring

## Escalation Levels

### P0 - Critical (Immediate Response)
- **Response Time**: 5 minutes
- **Channels**: PagerDuty, Slack, Email, SMS
- **Escalation**: Primary → Secondary → Manager (15 min intervals)
- **Coverage**: 24/7

**Triggers:**
- Service completely down (`up == 0`)
- High error rates (>10% 5xx errors)
- Database connection pool exhausted (>95% utilization)
- Security incidents (auth failures >50/min, signature validation failures)
- Research system down (health score <50)

### P1 - High Priority (1 Hour Response)
- **Response Time**: 1 hour (business hours), 4 hours (off-hours)
- **Channels**: Slack, Email
- **Escalation**: Team Lead → Backup Lead (2 hour intervals)
- **Coverage**: Business hours priority, off-hours monitored

**Triggers:**
- Plan limit violations (>10 violations/min)
- Webhook delivery failures (>5% failure rate)
- Content quality degradation (median score <50)
- High security enforcement actions (>10 actions/min)
- Vector store performance issues (p95 latency >2s)

### P2 - Medium Priority (24 Hour Response)  
- **Response Time**: 24 hours
- **Channels**: Slack notifications only
- **Escalation**: Team notification only
- **Coverage**: Business hours

**Triggers:**
- High response times (p95 >5s for >10 min)
- Memory usage warnings (>90% for >5 min)
- Cache eviction spikes (>100 evictions/sec)
- Background task queue backlogs (>10k tasks)
- User engagement drops (API requests <100/hour)

## Alert Rules Summary

### Critical System Health (5 rules)
- `ServiceDown`: Service unavailable (30s threshold)
- `HighErrorRate`: >10% 5xx errors (2 min threshold)  
- `DatabaseConnectionPoolExhausted`: >95% utilization (1 min threshold)
- `WebhookSignatureValidationFailures`: >1 failure/sec (2 min threshold)
- `ResearchSystemDown`: Health score <50 (2 min threshold)

### Business Logic & Plan Enforcement (3 rules)
- `HighPlanLimitViolationRate`: >10 violations/sec (3 min threshold)
- `PlanQuotaUtilizationCritical`: Users >90% quota (5 min threshold)
- `PlanUpgradeConversionDrop`: >80% upgrade declines (10 min threshold)

### Integration Reliability (3 rules)
- `WebhookDeliveryFailureRate`: >5% failure rate (3 min threshold)
- `WebhookDeliveryLatencyHigh`: p95 >30s (5 min threshold)  
- `WebhookDLQBacklog`: >1000 failed events (10 min threshold)

### Content & AI Quality (3 rules)
- `ContentQualityDegraded`: Median score <50 (5 min threshold)
- `HighContentSafetyViolations`: >5 blocks/sec (2 min threshold)
- `ImageGenerationFailureSpike`: >2 failures/sec (3 min threshold)

### Research & Vector Store (2 rules)  
- `VectorStorePerformanceDegraded`: p95 latency >2s (5 min threshold)
- `ResearchQuotaExceededFrequent`: >10 violations/sec (3 min threshold)

### Security & Authentication (3 rules)
- `HighAuthenticationFailureRate`: >50 failures/sec (2 min threshold)
- `SecurityEnforcementActionsSpike`: >10 actions/sec (1 min threshold)
- `SuspiciousAuthenticationPattern`: >5 high-risk events/sec (3 min threshold)

### Performance & Resources (4 rules)
- `HighResponseTime`: p95 >5s (10 min threshold)
- `HighMemoryUsage`: >90% utilization (5 min threshold) 
- `HighCacheEvictionRate`: >100 evictions/sec (5 min threshold)
- `BackgroundTaskQueueBacklog`: >10k pending tasks (10 min threshold)

### Business Intelligence (2 rules)
- `UserEngagementDrop`: Content API <100 requests/hour (30 min threshold)
- `LowContentGenerationVolume`: <50 pieces/hour (1 hour threshold)

## Team Assignments

### Platform Team
- System health and availability
- Performance and resource utilization  
- Database and infrastructure issues

### Security Team
- Authentication and authorization failures
- Security enforcement actions
- Webhook signature validation

### Billing Team  
- Plan enforcement and quota violations
- Subscription and payment issues
- Usage tracking problems

### Content Team
- AI generation quality and failures
- Content safety and moderation
- Image generation pipeline issues

### Research Team
- Research system health and performance
- Vector store operations and capacity
- Research quota and access control

### Integrations Team
- Webhook delivery and reliability
- Third-party API integrations
- Dead letter queue management

### Growth Team
- User engagement and conversion metrics
- Plan upgrade and downgrade flows
- Business intelligence alerts

## Notification Channels

### Slack Channels
- `#alerts-critical` - P0 alerts, immediate attention
- `#alerts-high` - P1 alerts, business hours priority
- `#alerts-medium` - P2 alerts, informational
- `#team-platform` - Platform-specific alerts
- `#team-security` - Security-specific alerts

### Email Lists
- `oncall-engineers@lilymedia.ai` - Critical alerts only
- `team-leads@lilymedia.ai` - High priority escalations
- `engineering-all@lilymedia.ai` - Weekly alert summaries

### PagerDuty Integration
- **Critical Service**: P0 alerts with immediate paging
- **High Priority Service**: P1 alerts with escalation
- **Escalation Policies**: Automated rotation and backup coverage

## Runbook Integration

All alerts include runbook URLs with detailed troubleshooting steps:

- **Base URL**: `https://runbooks.lilymedia.ai/`
- **Format**: `{base-url}/{alert-name-kebab-case}`
- **Contents**: Symptoms, causes, investigation steps, resolution procedures

### Key Runbooks
- `/service-down` - Service availability troubleshooting
- `/high-error-rate` - Error rate investigation and resolution  
- `/database-pool-exhaustion` - Connection pool optimization
- `/webhook-failures` - Webhook delivery debugging
- `/content-safety` - Content moderation review procedures
- `/security-enforcement` - Security incident response

## Monitoring Integration

### Prometheus Configuration
```yaml
rule_files:
  - "config/alerting/prometheus-alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboards
- **Alert Overview**: Real-time alert status and trends
- **Team Dashboards**: Team-specific alert views
- **Escalation Tracking**: Response time and escalation metrics
- **Alert Fatigue Analysis**: False positive and noise reduction

### Alert Manager Configuration  
```yaml
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default'
  routes:
  - match:
      severity: critical
    receiver: 'pager-critical'
  - match:
      severity: warning
      escalation_level: p1
    receiver: 'slack-high'
  - match:
      severity: warning  
      escalation_level: p2
    receiver: 'slack-medium'

receivers:
- name: 'pager-critical'
  pagerduty_configs:
  - service_key: '<pagerduty-integration-key>'
    description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
    
- name: 'slack-high'
  slack_configs:
  - api_url: '<slack-webhook-url>'
    channel: '#alerts-high'
    title: 'High Priority Alert'
    
- name: 'slack-medium'
  slack_configs:
  - api_url: '<slack-webhook-url>' 
    channel: '#alerts-medium'
    title: 'Medium Priority Alert'
```

## Maintenance and Tuning

### Regular Review Process
1. **Weekly**: Alert fatigue analysis and threshold tuning
2. **Monthly**: Escalation effectiveness review
3. **Quarterly**: Coverage gap analysis and new alert requirements

### Threshold Optimization
- Monitor alert frequency and false positive rates
- Adjust thresholds based on historical performance data
- Seasonal adjustments for expected traffic patterns

### Coverage Expansion
- Add new alerts for new features and services
- Expand business logic monitoring as requirements evolve
- Integrate third-party service health monitoring

## Compliance and Audit

### Documentation Requirements
- All alert rules documented with business justification
- Escalation procedures tested and validated monthly
- Response time SLAs tracked and reported quarterly

### Change Management
- Alert rule changes require engineering review
- Critical alert modifications need management approval
- All changes tracked in version control with approval history

---

**Last Updated**: September 6, 2025  
**Version**: 1.0  
**Owner**: Platform Engineering Team  
**Review Cycle**: Quarterly