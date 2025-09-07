# Encryption Key Rotation System

## Overview

The Lily AI Social Media platform implements a comprehensive encryption key rotation system to maintain the highest security standards and comply with industry best practices. This system ensures that encryption keys are regularly rotated to minimize the impact of potential key compromise and maintain forward secrecy.

## Key Types and Rotation Schedule

### 1. Token Encryption Keys
- **Purpose**: Encrypt OAuth tokens, API keys, and access credentials
- **Rotation Interval**: 90 days (3 months)
- **Grace Period**: 30 days
- **Critical**: High - protects user authentication

### 2. Database Encryption Keys
- **Purpose**: Encrypt sensitive database fields and PII
- **Rotation Interval**: 180 days (6 months)
- **Grace Period**: 90 days
- **Critical**: High - protects stored user data

### 3. File Encryption Keys
- **Purpose**: Encrypt uploaded files and documents
- **Rotation Interval**: 365 days (1 year)
- **Grace Period**: 180 days
- **Critical**: Medium - protects user content

### 4. Session Encryption Keys
- **Purpose**: Encrypt user session data and temporary storage
- **Rotation Interval**: 30 days (1 month)
- **Grace Period**: 7 days
- **Critical**: Medium - protects active sessions

### 5. API Signature Keys
- **Purpose**: Sign API requests and verify webhook signatures
- **Rotation Interval**: 90 days (3 months)
- **Grace Period**: 30 days
- **Critical**: High - protects API integrity

## Key Rotation Process

### Automated Schedule
1. **Daily Monitoring**: System checks key ages and schedules rotations
2. **Pre-rotation Notification**: Administrators notified 7 days before rotation
3. **Key Generation**: New keys generated with cryptographically secure randomness
4. **Gradual Migration**: Encrypted data migrated in batches to avoid service disruption
5. **Verification**: All migrations verified before old keys are deprecated
6. **Grace Period**: Old keys maintained for rollback capability
7. **Cleanup**: Expired keys securely destroyed after grace period

### Manual Rotation Triggers
- Security incident requiring immediate key rotation
- Suspected key compromise
- Compliance audit requirements
- Employee access revocation
- Planned maintenance windows

## Security Features

### Key Generation
- **Algorithm**: AES-256 with HMAC authentication (Fernet)
- **Entropy Source**: Cryptographically secure random number generator
- **Key Derivation**: PBKDF2 with SHA-256 and 100,000 iterations
- **Unique Key IDs**: Timestamped identifiers for tracking and versioning

### Key Storage
- **At Rest**: Keys encrypted with master key stored in secure key management service
- **In Transit**: TLS 1.3 encryption for all key material transmission
- **Memory**: Secure memory allocation with automatic clearing
- **Access Control**: Admin-only access with audit logging

### Data Migration
- **Envelope Encryption**: Versioned encryption format supports multiple keys
- **Batch Processing**: Configurable batch sizes to manage system load
- **Rollback Capability**: Ability to revert to previous keys if issues occur
- **Integrity Verification**: Checksums and validation for all migrated data

## API Endpoints

### Administrative Endpoints

#### Schedule Key Rotation
```http
POST /api/v1/key-rotation/schedule
Content-Type: application/json

{
  "key_type": "token_encryption",
  "force": false
}
```

#### Execute Key Rotation
```http
POST /api/v1/key-rotation/execute
Content-Type: application/json

{
  "event_id": "rotation_token_encryption_abc123",
  "batch_size": 1000
}
```

#### Get Rotation Schedule
```http
GET /api/v1/key-rotation/schedule
```

#### Get Rotation Report
```http
GET /api/v1/key-rotation/report
```

#### Emergency Rotation
```http
POST /api/v1/key-rotation/emergency-rotation?key_type=token_encryption&reason=security_incident
```

### Monitoring Endpoints

#### Health Check
```http
GET /api/v1/key-rotation/health
```

#### Active Keys
```http
GET /api/v1/key-rotation/keys/{key_type}
```

## Compliance and Audit

### Audit Logging
Every key rotation operation is logged with:
- **Event ID**: Unique identifier for tracking
- **Timestamp**: Precise timing of operations
- **User Context**: Administrator who initiated rotation
- **Key Details**: Key type, algorithm, and metadata
- **Migration Stats**: Records processed and any errors
- **Security Context**: Reason for rotation and authorization

### Compliance Standards
- **SOC 2 Type II**: Key rotation procedures documented and audited
- **ISO 27001**: Key management controls implemented
- **NIST Cybersecurity Framework**: Key lifecycle management
- **PCI DSS**: Cryptographic key management for payment data
- **GDPR/CCPA**: Encryption key management for personal data

### Reporting
- **Daily**: Key age monitoring and alerts
- **Weekly**: Rotation schedule compliance reports
- **Monthly**: Comprehensive key management audit reports
- **Quarterly**: Security posture and compliance assessments

## Emergency Procedures

### Key Compromise Response
1. **Immediate**: Execute emergency rotation for affected key type
2. **Assessment**: Determine scope of potential data exposure
3. **Notification**: Alert security team and relevant stakeholders
4. **Investigation**: Forensic analysis of compromise incident
5. **Remediation**: Additional security measures as needed
6. **Documentation**: Incident report and lessons learned

### Disaster Recovery
1. **Key Backup**: Secure backup of key material in separate facility
2. **Recovery Procedures**: Documented steps for key restoration
3. **Testing**: Regular testing of recovery procedures
4. **RTO/RPO**: Recovery time and point objectives defined
5. **Communication**: Stakeholder notification procedures

## Monitoring and Alerting

### Automated Monitoring
- **Key Age**: Daily monitoring of all key ages
- **Rotation Status**: Real-time tracking of rotation operations
- **Migration Progress**: Batch processing status and error rates
- **System Health**: Key rotation service availability
- **Compliance**: Adherence to rotation schedules

### Alert Conditions
- **Overdue Rotation**: Keys past scheduled rotation date
- **Migration Failure**: Errors during data migration process
- **Service Unavailable**: Key rotation service outages
- **Suspicious Activity**: Unusual key access patterns
- **Compliance Violation**: Deviation from security policies

### Alert Recipients
- **Security Team**: All critical security alerts
- **DevOps Team**: Service health and operational issues
- **Compliance Team**: Policy violations and audit items
- **Executive Team**: Major security incidents

## Performance Considerations

### Migration Optimization
- **Batch Sizing**: Configurable batch sizes based on system load
- **Rate Limiting**: Throttling to prevent database overload
- **Off-Peak Scheduling**: Major rotations during low-traffic periods
- **Progress Tracking**: Real-time monitoring of migration progress
- **Error Handling**: Robust retry mechanisms and error recovery

### Service Availability
- **Zero Downtime**: Rotations performed without service interruption
- **Graceful Degradation**: Fallback to old keys during migration
- **Health Checks**: Continuous monitoring during rotation process
- **Rollback Capability**: Quick rollback if issues detected
- **Performance Monitoring**: Impact assessment on system performance

## Best Practices

### Operational
1. **Regular Testing**: Test rotation procedures in staging environments
2. **Documentation**: Maintain up-to-date procedures and runbooks
3. **Training**: Ensure staff are trained on rotation procedures
4. **Change Management**: Follow change control processes for rotations
5. **Communication**: Notify relevant teams before major rotations

### Security
1. **Principle of Least Privilege**: Limit access to key rotation functions
2. **Separation of Duties**: Multiple approvals for sensitive operations
3. **Audit Trails**: Comprehensive logging of all key operations
4. **Secure Channels**: Use encrypted communications for key material
5. **Regular Reviews**: Periodic assessment of key management practices

### Technical
1. **Automated Testing**: Unit and integration tests for rotation logic
2. **Code Reviews**: Security-focused reviews of key management code
3. **Dependency Management**: Keep cryptographic libraries updated
4. **Configuration Management**: Version control for key rotation configs
5. **Monitoring Integration**: Integrate with existing monitoring systems

## Troubleshooting

### Common Issues
- **Migration Timeouts**: Increase batch size or add more processing time
- **Database Lock Contention**: Adjust batch timing and concurrency
- **Memory Usage**: Monitor and optimize memory allocation during migration
- **Network Issues**: Implement retry logic and error handling
- **Key Store Connectivity**: Ensure reliable access to key management service

### Recovery Procedures
- **Failed Migrations**: Rollback procedures and data integrity verification
- **Partial Rotations**: Complete interrupted rotations or rollback
- **Service Outages**: Emergency procedures and manual overrides
- **Data Corruption**: Backup restoration and integrity validation
- **Key Loss**: Recovery from secure backup and re-encryption procedures

## Operational Procedures Runbook

### Standard Key Rotation Procedure

#### Pre-Rotation Checklist
1. ✅ **Verify System Health**
   ```bash
   curl -s https://api.lilymedia.com/api/v1/key-rotation/health | jq '.status'
   ```

2. ✅ **Check Current Key Ages**
   ```bash
   curl -s https://api.lilymedia.com/api/v1/key-rotation/schedule | jq '.key_types'
   ```

3. ✅ **Verify Backup Systems**
   - Ensure database backups are current (< 24 hours)
   - Verify key backup accessibility
   - Test rollback procedures in staging

4. ✅ **Schedule Maintenance Window**
   - Notify stakeholders 48 hours in advance
   - Schedule during low-traffic periods (2-4 AM UTC)
   - Ensure on-call staff availability

#### Rotation Execution Steps

1. **Schedule the Rotation**
   ```bash
   curl -X POST https://api.lilymedia.com/api/v1/key-rotation/schedule \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{"key_type": "token_encryption", "force": false}'
   ```

2. **Monitor Schedule Response**
   - Record event_id for tracking
   - Verify rotation status is "pending"
   - Log scheduled time and administrator

3. **Execute the Rotation**
   ```bash
   curl -X POST https://api.lilymedia.com/api/v1/key-rotation/execute \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{"event_id": "rotation_event_id", "batch_size": 1000}'
   ```

4. **Monitor Progress**
   ```bash
   # Check status every 5 minutes during rotation
   watch -n 300 'curl -s https://api.lilymedia.com/api/v1/key-rotation/status/$EVENT_ID'
   ```

5. **Verify Completion**
   ```bash
   # Verify rotation completed successfully
   curl -s https://api.lilymedia.com/api/v1/key-rotation/report | jq '.summary'
   ```

#### Post-Rotation Verification

1. ✅ **Test Application Functionality**
   - Verify user authentication works
   - Test OAuth token decryption
   - Validate API endpoints respond correctly

2. ✅ **Check Error Logs**
   ```bash
   # Monitor for decryption errors
   tail -f /var/log/lilymedia/app.log | grep -i "encryption\|decryption\|token"
   ```

3. ✅ **Validate Key Status**
   ```bash
   curl -s https://api.lilymedia.com/api/v1/key-rotation/keys/token_encryption | jq '.active_keys'
   ```

4. ✅ **Update Documentation**
   - Record rotation completion time
   - Update key inventory
   - Document any issues encountered

### Emergency Key Rotation Procedure

#### Immediate Response (0-15 minutes)
1. **Assess Compromise Scope**
   ```bash
   # Check for suspicious key usage
   curl -s https://api.lilymedia.com/api/v1/audit/key-access?hours=24 | jq '.suspicious_activity'
   ```

2. **Initiate Emergency Rotation**
   ```bash
   curl -X POST https://api.lilymedia.com/api/v1/key-rotation/emergency-rotation \
     -H "Authorization: Bearer $EMERGENCY_TOKEN" \
     -d "key_type=token_encryption&reason=security_incident"
   ```

3. **Activate Incident Response Team**
   - Security team leader
   - Senior DevOps engineer
   - Compliance officer

#### Containment (15-60 minutes)
1. **Force User Re-authentication**
   ```bash
   # Invalidate all current sessions
   curl -X POST https://api.lilymedia.com/api/v1/auth/revoke-all-sessions
   ```

2. **Monitor System Status**
   - Watch for authentication failures
   - Monitor database performance
   - Check error rates

3. **Document Incident**
   - Record time of discovery
   - Document evidence of compromise
   - Log all actions taken

#### Recovery (1-4 hours)
1. **Complete Emergency Rotation**
   - Monitor rotation progress closely
   - Have rollback plan ready
   - Test system functionality

2. **Validate Security**
   - Perform security scans
   - Check for remaining vulnerabilities
   - Validate access controls

3. **Communicate Status**
   - Update stakeholders
   - Document lessons learned
   - Plan preventive measures

### Troubleshooting Procedures

#### Rotation Failure Recovery

1. **Check Service Status**
   ```bash
   curl -s https://api.lilymedia.com/api/v1/key-rotation/health
   ```

2. **Review Error Logs**
   ```bash
   grep -i "rotation" /var/log/lilymedia/app.log | tail -100
   ```

3. **Attempt Recovery**
   ```bash
   # Try to resume failed rotation
   curl -X POST https://api.lilymedia.com/api/v1/key-rotation/resume \
     -d '{"event_id": "failed_event_id"}'
   ```

4. **Rollback if Necessary**
   ```bash
   # Rollback to previous key if recovery fails
   curl -X POST https://api.lilymedia.com/api/v1/key-rotation/rollback \
     -d '{"event_id": "failed_event_id"}'
   ```

#### Database Migration Issues

1. **Check Database Connectivity**
   ```bash
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM user_credentials;"
   ```

2. **Verify Batch Processing**
   ```bash
   # Check for locked records
   psql $DATABASE_URL -c "SELECT * FROM pg_locks WHERE relation = 'user_credentials'::regclass;"
   ```

3. **Adjust Batch Size**
   ```bash
   # Reduce batch size if timeouts occur
   curl -X PATCH https://api.lilymedia.com/api/v1/key-rotation/config \
     -d '{"batch_size": 500}'
   ```

### Monitoring and Alerting Setup

#### Prometheus Metrics
```yaml
# Add to prometheus.yml
- job_name: 'key-rotation'
  static_configs:
    - targets: ['api.lilymedia.com:443']
  metrics_path: /api/v1/key-rotation/metrics
```

#### Alert Rules
```yaml
# key-rotation-alerts.yml
groups:
- name: key.rotation
  rules:
  - alert: KeyRotationOverdue
    expr: key_rotation_days_since_last > 90
    for: 24h
    labels:
      severity: warning
    annotations:
      summary: "Key rotation overdue for {{ $labels.key_type }}"
      
  - alert: KeyRotationFailed
    expr: key_rotation_failure_rate > 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Key rotation failed for {{ $labels.key_type }}"
```

## Contact Information

For key rotation emergencies or questions:

- **Security Team**: security@lilyai.com (24/7)
- **DevOps Team**: devops@lilyai.com (business hours)
- **Compliance Team**: compliance@lilyai.com
- **Emergency Hotline**: [INTERNAL_SECURITY_HOTLINE]

## Document Control

- **Version**: 1.0
- **Last Updated**: September 6, 2025
- **Next Review**: December 6, 2025
- **Approved By**: Security and Engineering Teams
- **Distribution**: Security team, senior engineering staff, compliance team

---

*This document contains sensitive security information and should be treated as confidential. Distribution is restricted to authorized personnel only.*