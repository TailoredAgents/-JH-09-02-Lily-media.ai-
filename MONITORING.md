# Monitoring Setup Guide

This document provides instructions for setting up monitoring with Prometheus and Sentry integration for the Lily Media AI platform.

## Overview

The monitoring system provides:

- **Prometheus Metrics**: Application performance metrics, request counts, database queries, cache statistics
- **Sentry Error Tracking**: Exception monitoring, performance tracing, error alerting
- **Health Monitoring**: System health checks and uptime monitoring

## Production Environment Variables

### Required for Sentry Integration

```bash
# Sentry DSN for error tracking (get from sentry.io)
SENTRY_DSN=https://your-dsn@o123456.ingest.sentry.io/123456

# Environment identifier
ENVIRONMENT=production
VERSION=1.0.0
```

### Optional Monitoring Configuration

```bash
# Enable detailed performance tracing (0.0-1.0)
SENTRY_TRACES_SAMPLE_RATE=0.1

# Disable PII collection for GDPR compliance
SENTRY_SEND_DEFAULT_PII=false
```

## Installation

### 1. Install Dependencies

The monitoring dependencies are already included in `requirements.txt`:

```
sentry-sdk[fastapi]==2.35.0
prometheus-client==0.20.0
```

### 2. Prometheus Setup

Prometheus metrics are automatically exposed at:

```
GET /api/monitoring/metrics
```

This endpoint provides metrics in Prometheus exposition format including:

- HTTP request metrics (count, duration, status codes)
- Database query metrics (count, duration by query type)
- Cache performance (hits, misses, hit rate)
- Social media platform metrics (posts, API calls)
- Celery task metrics (count, duration, success/failure)

### 3. Grafana Dashboard

Example Grafana queries:

```promql
# HTTP request rate
rate(http_requests_total[5m])

# Average response time
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Database query rate by type
rate(db_queries_total[5m])

# Cache hit rate
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))

# Celery task failure rate
rate(celery_tasks_total{status="failed"}[5m]) / rate(celery_tasks_total[5m])
```

## API Endpoints

### Health Check

```http
GET /api/monitoring/health
```

Returns monitoring system status (public endpoint).

### Metrics Endpoint

```http
GET /api/monitoring/metrics
```

Returns Prometheus metrics in exposition format (public endpoint).

### System Metrics

```http
GET /api/monitoring/system
```

Returns system metrics summary (requires admin authentication).

### Test Error Tracking

```http
POST /api/monitoring/test-error
```

Test endpoint for verifying Sentry integration (requires admin authentication).

## Development vs Production

### Development Mode

- Sentry integration requires DSN configuration
- Prometheus metrics are always available
- Health endpoint shows available monitoring systems

### Production Mode

- Configure all environment variables
- Set up external Prometheus server to scrape `/api/monitoring/metrics`
- Configure Sentry project for error tracking
- Set up alerting rules in Prometheus/Grafana

## Monitoring Features

### Automatic Monitoring

The system automatically monitors:

1. **HTTP Requests**: All API endpoints (method, path, status, duration)
2. **Database Queries**: Query type classification and performance
3. **Cache Operations**: Hit/miss ratios and performance
4. **Celery Tasks**: Task execution and failure tracking
5. **Social Media APIs**: Platform-specific metrics

### Custom Monitoring

Use decorators for custom monitoring:

```python
from backend.core.monitoring import monitor_endpoint, monitor_task

@monitor_endpoint("custom_endpoint")
async def my_endpoint():
    # Your endpoint code
    pass

@monitor_task("custom_task")
def my_task():
    # Your task code
    pass
```

### Error Context

Errors are automatically enriched with context:

```python
from backend.core.monitoring import monitoring_service

# Record custom error with context
monitoring_service.record_error(
    exception,
    context={
        "user_id": user_id,
        "action": "custom_action",
        "metadata": {"key": "value"}
    }
)
```

## Alert Recommendations

### Critical Alerts

1. **High Error Rate**: >5% 5xx responses over 5 minutes
2. **Slow Response Time**: >2s average response time over 5 minutes
3. **Database Issues**: >1s average query time over 5 minutes
4. **Task Failures**: >10% Celery task failure rate over 15 minutes

### Warning Alerts

1. **Cache Performance**: <70% cache hit rate over 15 minutes
2. **Social API Errors**: >5% social platform API errors over 10 minutes
3. **Queue Backlog**: Celery queue size >100 pending tasks

## Troubleshooting

### Sentry Not Initializing

- Verify `SENTRY_DSN` environment variable is set
- Check DSN format: `https://key@organization.ingest.sentry.io/project`
- Review application logs for Sentry initialization errors

### Prometheus Metrics Missing

- Verify prometheus-client is installed
- Check `/api/monitoring/health` endpoint for status
- Ensure application is receiving traffic to generate metrics

### Performance Impact

The monitoring system is designed for minimal overhead:

- Prometheus metrics use in-memory counters
- Database monitoring uses SQLAlchemy event hooks
- Sentry sampling reduces performance trace volume
- Critical path operations are protected with try/catch blocks

## Security Considerations

1. **PII Protection**: Sentry is configured to not send personally identifiable information
2. **Admin Endpoints**: System metrics require admin authentication
3. **Rate Limiting**: Monitor endpoints respect application rate limits
4. **Data Retention**: Configure appropriate retention policies in external systems