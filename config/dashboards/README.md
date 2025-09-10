# Grafana Dashboards for Lily Media AI

This directory contains production-ready Grafana dashboards for monitoring the Lily Media AI platform.

## Dashboard Overview

### 1. Business Metrics (`business_metrics.json`)
**Purpose**: Executive and business stakeholder visibility into key performance indicators

**Key Metrics**:
- Active users and new registrations
- Revenue metrics and subscription trends
- Plan distribution and feature adoption
- Content generation usage patterns
- User engagement across plans

**Refresh Rate**: 30 seconds
**Time Range**: 24 hours (default)

### 2. Technical Metrics (`technical_metrics.json`)
**Purpose**: Engineering team operational visibility into system performance

**Key Metrics**:
- API response times (P50, P95, P99)
- Database connection pool status
- Vector store performance and fragmentation
- Memory and cache utilization
- Error rates and background task performance

**Refresh Rate**: 30 seconds
**Time Range**: 1 hour (default)

### 3. SRE Metrics (`sre_metrics.json`)
**Purpose**: Site Reliability Engineering focus on SLOs, error budgets, and capacity planning

**Key Metrics**:
- Service Level Objective (SLO) status and trends
- Error budget consumption tracking
- Incident metrics (MTTR, MTTD)
- Availability trends and capacity planning
- Active alerts and remediation status

**Refresh Rate**: 1 minute
**Time Range**: 7 days (default)

## Installation

### Option 1: Docker Compose with Grafana
```yaml
services:
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    ports:
      - "3000:3000"
    volumes:
      - ./config/dashboards:/etc/grafana/provisioning/dashboards
```

### Option 2: Manual Import
1. Open Grafana UI (typically http://localhost:3000)
2. Navigate to Dashboards → Import
3. Upload each `.json` file from the `grafana/` directory
4. Configure data source (Prometheus)

### Option 3: Kubernetes ConfigMaps
```bash
kubectl create configmap grafana-dashboards \
  --from-file=config/dashboards/grafana/ \
  -n monitoring
```

## Data Source Configuration

These dashboards expect a Prometheus data source named "Prometheus" with the following metrics available:

### Required Metrics
- `http_requests_total` - HTTP request counter with status labels
- `http_request_duration_seconds` - HTTP request duration histogram
- `user_registrations_total` - User registration counter
- `subscription_revenue_total` - Revenue tracking counter
- `vector_store_operations_duration_seconds` - Vector store operation timing
- `database_connection_pool_status` - Database pool metrics
- `cache_hits_total` / `cache_misses_total` - Cache performance
- `celery_tasks_total` - Background task metrics

### Custom Metrics (Lily Media AI Specific)
- `research_requests_total` - Research system usage
- `content_generation_requests_total` - Content generation metrics
- `image_generation_requests_total` - Image generation tracking
- `vector_store_fragmentation_ratio` - Index fragmentation
- `vector_store_growth_rate_vectors_per_hour` - Storage growth

## Alert Integration

The dashboards include annotations for:
- **Deployments**: Automatically marked when new versions are deployed
- **Active Alerts**: Current firing alerts displayed in context
- **Incidents**: Incident tracking and resolution timeline

## Customization

### Adding New Panels
1. Open the dashboard in Grafana UI
2. Add panels using the visual editor
3. Export updated JSON
4. Replace the corresponding file in this directory

### Modifying Thresholds
Update the `thresholds` section in each panel's `fieldConfig`:
```json
"thresholds": {
  "mode": "absolute",
  "steps": [
    {"color": "green", "value": 0},
    {"color": "yellow", "value": 80},
    {"color": "red", "value": 95}
  ]
}
```

### Template Variables
Each dashboard supports template variables for filtering:
- **Business**: Plan selection, time ranges
- **Technical**: Instance selection, service filtering  
- **SRE**: Time range selection, severity filtering

## Performance Considerations

- **Refresh Rates**: Adjust based on data volume and Prometheus retention
- **Time Ranges**: Longer ranges may impact query performance
- **Panel Count**: Consider dashboard load times with many panels
- **Query Optimization**: Use recording rules for complex calculations

## Troubleshooting

### Common Issues
1. **No Data**: Verify Prometheus data source and metric names
2. **Slow Loading**: Reduce time range or panel count
3. **Missing Panels**: Check metric availability in Prometheus

### Metric Validation
```bash
# Check if metrics are available
curl http://prometheus:9090/api/v1/label/__name__/values | grep -E "(http_requests|vector_store|user_)"
```

## Maintenance

- **Weekly**: Review dashboard performance and user feedback
- **Monthly**: Update thresholds based on system growth
- **Quarterly**: Add new metrics for new features
- **Annually**: Archive unused dashboards and metrics

## Related Documentation

- [Prometheus Metrics Guide](../alerting/README.md)
- [SRE Runbooks](../../docs/sre/)
- [Monitoring Architecture](../monitoring/)