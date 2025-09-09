# SRE Runbook Integration with Monitoring Alerts

This document describes the integration between Prometheus alerts and automated SRE runbooks for the Lily Media AI platform.

## Overview

P1-8c Implementation: The system automatically triggers appropriate remediation runbooks when critical alerts fire, reducing manual intervention and improving mean time to recovery (MTTR).

## Architecture

```
Prometheus → AlertManager → Webhook → SRE API → Runbook Engine
```

### Components

1. **Prometheus**: Monitors metrics and evaluates alert rules
2. **AlertManager**: Handles alert routing and notifications 
3. **SRE Webhook API**: Receives alerts and triggers runbooks (`/api/sre/alerts/webhook`)
4. **Runbook Engine**: Executes automated remediation procedures
5. **Monitoring Dashboard**: Tracks runbook execution status

## Alert → Runbook Mappings

| Alert Name | Runbook ID | Description |
|------------|------------|-------------|
| `ServiceDown` | `service_unavailable` | Service health checks and restart procedures |
| `HighErrorRate` | `high_error_rate` | Error analysis and circuit breaker application |
| `DatabaseConnectionPoolExhausted` | `db_performance_degradation` | Database performance diagnostics and optimization |
| `VectorStorePerformanceDegraded` | `vector_store_optimization` | Vector store performance tuning |
| `HighAuthenticationFailureRate` | `security_incident` | Security incident response |
| `ResearchSystemDown` | `research_system_recovery` | Research system recovery procedures |

## Configuration

### AlertManager Configuration

Located at `config/alerting/alertmanager.yml`:

```yaml
receivers:
- name: 'web.hook.runbook_automation'
  webhook_configs:
  - url: 'https://socialmedia-api-wxip.onrender.com/api/sre/alerts/webhook'
    send_resolved: true
    max_alerts: 10
```

### Alert Rules Enhancement

Alert rules in `prometheus-alerts.yml` include `automation_runbook` annotations:

```yaml
annotations:
  summary: "Service {{ $labels.instance }} is down"
  description: "Service down for more than 30 seconds"
  runbook_url: "https://runbooks.lilymedia.ai/service-down"
  automation_runbook: "service_unavailable"  # ← Triggers automation
```

## API Endpoints

### Webhook Receiver
- **Endpoint**: `POST /api/sre/alerts/webhook`
- **Purpose**: Receives Prometheus AlertManager webhooks
- **Response**: Returns runbook execution IDs

### Integration Status
- **Endpoint**: `GET /api/sre/runbooks/integration-status`  
- **Purpose**: Monitor integration health
- **Auth**: Requires authentication

## Runbook Execution Flow

1. **Alert Fires**: Prometheus evaluates rules and fires alert
2. **Alert Processing**: AlertManager receives and routes alert
3. **Webhook Delivery**: AlertManager sends webhook to SRE API
4. **Mapping Resolution**: System maps alert name to runbook ID
5. **Context Creation**: Alert labels/annotations become runbook context
6. **Runbook Execution**: Automated runbook starts in background
7. **Tracking**: Execution tracked with unique ID
8. **Monitoring**: Dashboard shows execution status and results

## Example Webhook Payload

```json
{
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "ServiceDown",
        "instance": "api-server-1",
        "severity": "critical"
      },
      "annotations": {
        "summary": "Service api-server-1 is down",
        "automation_runbook": "service_unavailable"
      },
      "startsAt": "2024-12-09T10:00:00.000Z"
    }
  ]
}
```

## Runbook Context

When runbooks are triggered, they receive context from the alert:

```python
context = {
    "alert_name": "ServiceDown",
    "alert_labels": {
        "instance": "api-server-1",
        "severity": "critical"
    },
    "alert_annotations": {
        "summary": "Service api-server-1 is down"
    },
    "triggered_at": "2024-12-09T10:00:00.000Z",
    "severity": "critical",
    "instance": "api-server-1"
}
```

## Monitoring Integration Health

### Status Check
```bash
curl -X GET "https://socialmedia-api-wxip.onrender.com/api/sre/runbooks/integration-status" \
  -H "Authorization: Bearer <token>"
```

### Response Example
```json
{
  "status": "enabled",
  "available_runbooks": 6,
  "active_executions": 2,
  "runbook_alert_mappings": {
    "ServiceDown": "service_unavailable",
    "HighErrorRate": "high_error_rate"
  },
  "last_updated": "2024-12-09T10:00:00.000Z"
}
```

## Benefits

1. **Reduced MTTR**: Automated remediation starts immediately when alerts fire
2. **Consistent Response**: Same procedures executed every time
3. **24/7 Coverage**: Automation works during off-hours
4. **Audit Trail**: All executions tracked and logged
5. **Escalation**: Failed automation triggers human escalation

## Safety Features

- **Timeouts**: Each runbook step has configurable timeout
- **Retry Logic**: Failed steps can be retried automatically
- **Rollback**: Critical steps can trigger rollback procedures
- **Circuit Breakers**: Prevent cascading failures
- **Human Override**: Engineers can stop/modify executions

## Testing

### Manual Webhook Test
```bash
curl -X POST "https://socialmedia-api-wxip.onrender.com/api/sre/alerts/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [
      {
        "status": "firing",
        "labels": {"alertname": "ServiceDown", "severity": "critical"},
        "annotations": {"summary": "Test alert"}
      }
    ]
  }'
```

### Expected Response
```json
{
  "status": "processed",
  "alerts_processed": 1,
  "runbooks_triggered": 1,
  "execution_ids": ["service_unavailable_1638181200"]
}
```

## Troubleshooting

### Common Issues

1. **Runbook Not Triggered**
   - Check alert name mapping in `handle_alert_with_runbook()`
   - Verify webhook is reaching the endpoint
   - Check AlertManager configuration

2. **Runbook Execution Fails**
   - Check runbook step timeouts
   - Verify system dependencies are available
   - Review execution logs in dashboard

3. **Integration Disabled**
   - Check `RUNBOOKS_AVAILABLE` flag
   - Verify runbooks module imports correctly
   - Check system dependencies

### Debug Commands

```bash
# Check webhook endpoint health
curl -X GET "https://socialmedia-api-wxip.onrender.com/health"

# Check runbook availability
python -c "from backend.core.runbooks import automated_runbooks; print(list(automated_runbooks.runbooks.keys()))"

# Check alerting service
python -c "from backend.services.alerting_service import get_alerting_service; print(get_alerting_service().get_runbook_integration_status())"
```

## Future Enhancements

- **ML-Based Alerts**: Use machine learning to predict and prevent issues
- **Dynamic Mapping**: Configure alert-to-runbook mappings via API
- **Feedback Loop**: Use execution results to improve runbook effectiveness
- **Cross-Service**: Coordinate runbooks across multiple services
- **A/B Testing**: Test different remediation strategies