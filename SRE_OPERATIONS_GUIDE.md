# SRE Operations Guide

## Site Reliability Engineering for AI Social Media Content Agent

This document provides comprehensive operational guidance for maintaining the AI Social Media Content Agent in production environments.

## 📊 System Overview

### Architecture Components

- **API Gateway**: FastAPI application with comprehensive middleware
- **Database**: PostgreSQL with connection pooling and optimization
- **Cache**: Redis for session management and performance
- **Task Queue**: Celery with Redis broker for background processing
- **Monitoring**: Prometheus + Sentry integration
- **Alerting**: Multi-channel notification system
- **Runbooks**: Automated remediation procedures

### Service Level Objectives (SLOs)

| Service | SLO Target | Current Performance | Error Budget |
|---------|------------|-------------------|--------------|
| API Availability | 99.9% | 99.95% | 76% remaining |
| Database Response Time | 95% < 100ms | 96.2% | 68% remaining |
| Social Media API Success | 99% | 97.8% | 22% remaining ⚠️ |

## 🚨 Alert Severity Levels

### Critical (P0) - Immediate Response Required
- **Service completely unavailable**
- **Database connection failures**
- **Security breaches detected**
- **Data corruption events**

**Response**: Page on-call engineer immediately

### High (P1) - Respond within 15 minutes
- **High error rate (>5%)**
- **Performance degradation (>5s response)**
- **Authentication system failures**
- **External API quota exhaustion**

**Response**: Automated runbook execution + manual investigation

### Medium (P2) - Respond within 1 hour
- **Elevated error rate (2-5%)**
- **Slow database queries**
- **Memory usage warnings**
- **Non-critical feature failures**

**Response**: Automated remediation + scheduled investigation

### Low (P3) - Respond within 4 hours
- **Performance warnings**
- **Capacity planning alerts**
- **Informational notices**

**Response**: Log for review during business hours

## 🏃‍♂️ Runbook Procedures

### Available Automated Runbooks

#### 1. Database Performance Degradation
```bash
# Triggered automatically when:
# - Average query time > 100ms
# - Connection pool utilization > 90%
# - Slow queries detected

# Manual execution:
POST /api/sre/runbooks/db_performance_degradation/execute
```

**Steps:**
1. Analyze database performance metrics
2. Check active connections and pool status  
3. Identify and analyze slow queries
4. Apply automatic query optimizations
5. Restart connection pool if needed

#### 2. High Memory Usage
```bash
# Triggered automatically when:
# - System memory > 85%
# - Process memory > 1GB
# - Redis memory warnings

# Manual execution:  
POST /api/sre/runbooks/high_memory_usage/execute
```

**Steps:**
1. Analyze memory consumption patterns
2. Clear application-level caches
3. Optimize Redis memory usage
4. Force Python garbage collection

#### 3. API Quota Exhaustion
```bash
# Triggered automatically when:
# - Platform quota utilization > 90%
# - Multiple platforms in critical state

# Manual execution:
POST /api/sre/runbooks/api_quota_exhaustion/execute
```

**Steps:**
1. Identify platforms with quota issues
2. Redistribute quota across tenants
3. Enable burst mode for critical operations
4. Notify relevant stakeholders

#### 4. Service Unavailability
```bash
# Triggered automatically when:
# - Health check failures
# - 5xx error rates > 10%
# - External dependency failures

# Manual execution:
POST /api/sre/runbooks/service_unavailable/execute
```

**Steps:**
1. Comprehensive service health check
2. Restart failing service components
3. Verify external dependency connectivity
4. Enable degraded mode if necessary

#### 5. High Error Rate
```bash
# Triggered automatically when:
# - Error rate > 5% for 5+ minutes
# - Authentication failures spike

# Manual execution:
POST /api/sre/runbooks/high_error_rate/execute
```

**Steps:**
1. Analyze error patterns and sources
2. Check integration health status
3. Apply circuit breakers to failing services
4. Escalate if errors persist after remediation

## 🔧 Manual Troubleshooting Procedures

### Database Issues

#### Connection Pool Exhaustion
```bash
# Check current connections
GET /api/sre/metrics

# Restart connection pool
POST /api/sre/runbooks/db_performance_degradation/execute

# Manual connection pool restart
# (In emergency, restart the application)
```

#### Slow Queries
```bash
# Analyze slow queries
GET /api/monitoring/health/detailed

# Check database performance metrics
SELECT * FROM pg_stat_activity WHERE query_start < NOW() - INTERVAL '1 minute';

# Kill long-running queries (emergency only)
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE state = 'active' AND query_start < NOW() - INTERVAL '10 minutes';
```

### Memory Issues

#### High Memory Usage Investigation
```bash
# Check system memory
GET /api/sre/performance-trends?hours=24

# Check application memory
import psutil
process = psutil.Process()
print(f"Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")

# Force garbage collection
import gc
collected = gc.collect()
print(f"Collected {collected} objects")
```

### Redis Cache Issues

#### Cache Connection Problems
```bash
# Check Redis health
GET /api/monitoring/health/detailed

# Test Redis connectivity
redis-cli ping

# Clear problematic cache entries
redis-cli FLUSHDB

# Monitor Redis memory
redis-cli INFO memory
```

### Social Media API Issues

#### Rate Limit Management
```bash
# Check quota status
GET /api/sre/metrics

# Manual quota redistribution
POST /api/sre/runbooks/api_quota_exhaustion/execute

# Check platform-specific limits
GET /api/monitoring/metrics
```

## 📈 Key Metrics and Dashboards

### Primary SRE Dashboards

#### 1. Service Health Dashboard
- **URL**: `/api/sre/dashboard/overview`
- **Key Metrics**: 
  - System availability percentage
  - Error budget remaining
  - Active incidents count
  - Mean time to recovery (MTTR)

#### 2. Performance Dashboard
- **URL**: `/api/sre/performance-trends`
- **Key Metrics**:
  - API response times (p50, p95, p99)
  - Database query performance
  - Throughput (requests per minute)
  - Error rates by endpoint

#### 3. Capacity Planning Dashboard
- **URL**: `/api/sre/capacity-planning`
- **Key Metrics**:
  - CPU/Memory utilization trends
  - Database connection usage
  - Redis memory consumption
  - Growth rate projections

#### 4. Incident Management Dashboard
- **URL**: `/api/sre/incidents`
- **Key Metrics**:
  - Active incidents by severity
  - Incident resolution trends
  - Mean time to acknowledgment (MTTA)
  - Alert fatigue indicators

### Prometheus Metrics

Access raw metrics at `/api/sre/prometheus/metrics`:

```
# System metrics
http_requests_total{method="GET",endpoint="/api/health",status_code="200"}
http_request_duration_seconds{method="GET",endpoint="/api/health"}
db_queries_total{query_type="select"}
db_query_duration_seconds{query_type="select"}

# Business metrics  
social_posts_total{platform="twitter",status="success"}
social_api_calls_total{platform="instagram",status_code="200"}
active_users
celery_tasks_total{task_name="content_generation",status="success"}
```

## 🔔 Notification Channels

### Primary Channels

#### Slack Integration
- **Channel**: #ops-alerts
- **Webhook**: Configured via `SLACK_WEBHOOK_URL`
- **Coverage**: Critical, High, Medium severity alerts

#### Email Notifications
- **Recipients**: ops-team@company.com, sre-team@company.com  
- **Coverage**: Critical and High severity alerts
- **SMTP**: Configured via `SMTP_SERVER` settings

#### PagerDuty Integration
- **Service**: AI Social Media Agent Production
- **Coverage**: Critical severity alerts only
- **Configuration**: `PAGERDUTY_API_KEY` environment variable

### Alert Escalation Policy

#### Critical Alerts
1. **T+0min**: Slack + Email notification
2. **T+15min**: PagerDuty page if not acknowledged
3. **T+30min**: Email re-notification to management

#### High Alerts  
1. **T+0min**: Slack notification
2. **T+60min**: Email notification if not acknowledged

## 🚀 Deployment and Rollback Procedures

### Safe Deployment Checklist

#### Pre-Deployment
- [ ] Run full test suite
- [ ] Verify database migrations
- [ ] Check feature flag configurations
- [ ] Review monitoring alerts

#### During Deployment
- [ ] Monitor error rates in real-time
- [ ] Watch response time metrics
- [ ] Verify database connection health
- [ ] Confirm external integrations

#### Post-Deployment
- [ ] Run smoke tests on critical endpoints
- [ ] Verify all runbooks are functional
- [ ] Check alert configurations
- [ ] Update deployment frequency metrics

### Emergency Rollback

```bash
# Immediate rollback (if available)
git revert <commit-hash>
git push origin main

# Or restore from backup
# Follow organization-specific rollback procedures

# Monitor system recovery
GET /api/sre/dashboard/overview
```

## 📚 Incident Response Procedures

### Incident Lifecycle

#### 1. Detection
- Automated monitoring triggers alert
- Manual report via Slack/email
- Customer reports via support channels

#### 2. Triage and Classification
```bash
# Acknowledge alert
POST /api/sre/incidents/{alert_id}/acknowledge

# Classify severity based on impact:
# - Users affected
# - Financial impact  
# - Reputation risk
# - Duration of outage
```

#### 3. Investigation and Mitigation
- Check relevant runbooks for automated solutions
- Review recent deployments and changes
- Examine system metrics and logs
- Apply mitigation strategies

#### 4. Resolution
```bash
# Mark incident resolved
POST /api/sre/incidents/{alert_id}/resolve

# Document root cause and resolution steps
# Update relevant runbooks if needed
```

#### 5. Post-Incident Review
- Conduct blameless post-mortem
- Update monitoring and alerting if gaps found
- Improve runbooks based on manual steps taken
- Share learnings with team

### Incident Communication Template

```
🚨 INCIDENT ALERT

Severity: [P0/P1/P2/P3]
Service: AI Social Media Content Agent  
Impact: [Brief description of user impact]
Start Time: [UTC timestamp]

Current Status: [Investigating/Mitigating/Resolved]
Next Update: [Time commitment for next update]

Affected Components:
- [ ] API endpoints
- [ ] Database  
- [ ] Social media integrations
- [ ] Authentication system

Updates will be posted in #incidents channel.
```

## 🔄 Maintenance Procedures

### Scheduled Maintenance

#### Database Maintenance
```bash
# Monthly index optimization (during low traffic)
REINDEX DATABASE socialmedia_db;

# Analyze table statistics
ANALYZE;

# Clean up old log entries
DELETE FROM system_logs WHERE created_at < NOW() - INTERVAL '90 days';
```

#### Cache Maintenance
```bash
# Weekly Redis optimization
redis-cli MEMORY PURGE

# Review and clean expired keys
redis-cli --scan | xargs -L 1 redis-cli TTL | grep -E '^-1$'

# Memory defragmentation (if needed)
redis-cli MEMORY DOCTOR
```

#### Application Maintenance
```bash
# Update dependencies (test environment first)
pip install -r requirements.txt --upgrade

# Clear application logs
find /var/log/app -name "*.log" -mtime +30 -delete

# Restart workers to clear memory leaks
systemctl restart celery-workers
```

### Capacity Planning

#### Weekly Capacity Review
- Monitor growth trends in traffic and resource usage
- Project capacity needs for next 90 days  
- Plan infrastructure scaling based on projections
- Review and adjust alert thresholds

#### Monthly Performance Review
- Analyze SLO performance vs targets
- Review error budget consumption
- Update capacity planning based on usage patterns
- Optimize inefficient processes identified

## 📞 Escalation Contacts

### Primary On-Call
- **Role**: SRE Engineer
- **Response Time**: 15 minutes for P0/P1
- **Contact**: Via PagerDuty rotation

### Secondary On-Call  
- **Role**: Senior SRE/DevOps Lead
- **Response Time**: 30 minutes for P0
- **Contact**: Via PagerDuty escalation

### Management Escalation
- **Role**: Engineering Manager
- **Threshold**: P0 incidents lasting >2 hours
- **Contact**: Direct phone/email

### External Vendors
- **Database**: Managed PostgreSQL support
- **Infrastructure**: Cloud provider support
- **Third-party APIs**: Social platform developer support

## 🛡️ Security Incident Response

### Security Alert Classification

#### Critical Security Events
- Unauthorized access attempts
- Data breach indicators
- Injection attack patterns
- Privilege escalation attempts

#### Response Procedures
1. **Immediately**: Isolate affected systems
2. **Within 15min**: Notify security team
3. **Within 30min**: Begin forensic analysis
4. **Within 1hr**: Implement additional security measures

### Monitoring Security Metrics
```bash
# Check authentication failures
GET /api/monitoring/metrics?filter=auth_failures

# Review access patterns
GET /api/sre/incidents?severity=critical&source=security

# Monitor privilege escalation attempts  
grep "privilege" /var/log/app/security.log
```

## 🔍 Troubleshooting Common Issues

### Issue: High Response Times

**Symptoms**: API response times >1s consistently

**Investigation**:
1. Check database performance metrics
2. Review Redis cache hit rates
3. Analyze slow query logs  
4. Monitor CPU/memory usage

**Resolution**:
1. Execute database performance runbook
2. Scale up infrastructure if needed
3. Optimize slow queries
4. Increase cache TTL for static data

### Issue: Authentication Failures

**Symptoms**: 401/403 errors increasing

**Investigation**:
1. Check JWT token validation logs
2. Review Redis session storage
3. Verify external auth service status
4. Check for expired credentials

**Resolution**:
1. Clear expired sessions from Redis
2. Verify JWT secret key configuration
3. Restart authentication services
4. Update expired external API credentials

### Issue: Database Connection Errors

**Symptoms**: "Connection pool exhausted" errors

**Investigation**:
1. Check active database connections
2. Review connection pool configuration
3. Look for long-running queries
4. Monitor connection leak patterns

**Resolution**:
1. Restart connection pool
2. Kill long-running queries if safe
3. Increase connection pool size temporarily
4. Deploy fix for connection leaks

---

## 📋 Quick Reference Commands

### Health Checks
```bash
# System health
curl -s https://api.domain.com/api/sre/dashboard/overview | jq '.system_health.overall_status'

# Database health  
curl -s https://api.domain.com/api/monitoring/health | jq '.components.database.status'

# Cache health
curl -s https://api.domain.com/api/monitoring/health | jq '.components.cache.status'
```

### Runbook Execution
```bash
# List available runbooks
curl -s https://api.domain.com/api/sre/runbooks | jq '.available_runbooks'

# Execute specific runbook
curl -X POST https://api.domain.com/api/sre/runbooks/db_performance_degradation/execute \
  -H "Authorization: Bearer $TOKEN"

# Check execution status
curl -s https://api.domain.com/api/sre/runbooks/executions/$EXECUTION_ID | jq '.status'
```

### Incident Management
```bash
# Get active incidents
curl -s https://api.domain.com/api/sre/incidents | jq '.recent_alerts[]'

# Acknowledge incident
curl -X POST https://api.domain.com/api/sre/incidents/$ALERT_ID/acknowledge \
  -H "Authorization: Bearer $TOKEN"

# Resolve incident  
curl -X POST https://api.domain.com/api/sre/incidents/$ALERT_ID/resolve \
  -H "Authorization: Bearer $TOKEN"
```

### Metrics and Monitoring
```bash
# Get key SRE metrics
curl -s https://api.domain.com/api/sre/dashboard/overview | jq '.sre_metrics'

# Performance trends
curl -s https://api.domain.com/api/sre/performance-trends?hours=24 | jq '.performance_summary'

# Capacity planning data
curl -s https://api.domain.com/api/sre/capacity-planning | jq '.scaling_recommendations[]'
```

---

This guide should be reviewed and updated quarterly or after any major incidents. All procedures should be tested regularly in staging environments.

**Last Updated**: 2025-01-01  
**Next Review**: 2025-04-01  
**Document Owner**: SRE Team