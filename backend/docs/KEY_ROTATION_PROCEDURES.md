# Encryption Key Rotation Procedures

**Version**: 2.0  
**Last Updated**: December 2024  
**Responsible Team**: Security & Compliance (Agent 1)  
**Classification**: P1 High Priority Task (P1-2c)

## Overview

This document provides comprehensive procedures for encryption key rotation in the AI Social Media Content Agent platform. Key rotation is critical for maintaining security, compliance, and protecting sensitive data including user credentials, OAuth tokens, and encrypted communications.

## Key Types and Rotation Schedules

### Supported Key Types

| Key Type | Purpose | Rotation Interval | Grace Period | Priority |
|----------|---------|------------------|--------------|----------|
| `TOKEN_ENCRYPTION` | OAuth token encryption | 90 days | 30 days | Critical |
| `DATABASE_ENCRYPTION` | Database field encryption | 180 days | 90 days | High |
| `FILE_ENCRYPTION` | File/blob encryption | 365 days | 180 days | Medium |
| `SESSION_ENCRYPTION` | Session data encryption | 30 days | 7 days | High |
| `API_SIGNATURE` | API signature verification | 90 days | 30 days | High |

### Key Lifecycle States

1. **Active** - Currently used for new encryption operations
2. **Deprecated** - No longer used for new operations, still used for decryption
3. **Retired** - Completely removed from system (after grace period)

## Automated Key Rotation System

### Service Components

#### KeyRotationService
- **Location**: `backend/services/key_rotation_service.py`
- **Purpose**: Core key management and rotation logic
- **Key Features**:
  - Automated key generation
  - Gradual data migration
  - Key lifecycle management
  - Audit logging

#### AutomatedKeyRotationScheduler
- **Location**: `backend/services/automated_key_rotation_scheduler.py`
- **Purpose**: Automated scheduling and execution
- **Schedule**: Runs daily at 02:00 UTC

#### API Endpoints
- **Location**: `backend/api/key_rotation.py`
- **Purpose**: Administrative interface for key rotation
- **Authentication**: Admin users only

## Manual Key Rotation Procedures

### Prerequisites

1. **Access Requirements**:
   - Admin user privileges
   - Database access (for verification)
   - System monitoring access

2. **Pre-rotation Checklist**:
   - [ ] Verify system health
   - [ ] Check database connectivity
   - [ ] Ensure backup systems are operational
   - [ ] Schedule maintenance window if needed

### Emergency Key Rotation

When immediate key rotation is required (security breach, key compromise):

#### Step 1: Assess Impact
```bash
# Check key status
curl -X GET "https://api.domain.com/api/v1/key-rotation/status" \
  -H "Authorization: Bearer {admin_token}"

# Get affected records count
curl -X GET "https://api.domain.com/api/v1/key-rotation/impact/{key_type}" \
  -H "Authorization: Bearer {admin_token}"
```

#### Step 2: Initiate Emergency Rotation
```bash
# Force immediate rotation
curl -X POST "https://api.domain.com/api/v1/key-rotation/schedule" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "key_type": "TOKEN_ENCRYPTION",
    "force": true
  }'
```

#### Step 3: Monitor Progress
```bash
# Check rotation status
curl -X GET "https://api.domain.com/api/v1/key-rotation/events/{event_id}" \
  -H "Authorization: Bearer {admin_token}"
```

#### Step 4: Verify Completion
```bash
# Generate post-rotation report
curl -X GET "https://api.domain.com/api/v1/key-rotation/report" \
  -H "Authorization: Bearer {admin_token}"
```

### Scheduled Key Rotation

For regular, planned key rotations:

#### Step 1: Review Rotation Schedule
```bash
# Get rotation schedule
curl -X GET "https://api.domain.com/api/v1/key-rotation/schedule" \
  -H "Authorization: Bearer {admin_token}"
```

#### Step 2: Plan Maintenance Window
- Schedule during low-traffic periods
- Notify relevant teams
- Prepare rollback procedures

#### Step 3: Execute Rotation
```bash
# Schedule rotation for specific key type
curl -X POST "https://api.domain.com/api/v1/key-rotation/schedule" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "key_type": "TOKEN_ENCRYPTION",
    "force": false
  }'
```

#### Step 4: Monitor and Validate
- Monitor system metrics
- Verify application functionality
- Check error logs
- Validate data integrity

## Troubleshooting Guide

### Common Issues

#### 1. Rotation Stuck/Failed
**Symptoms**: Event status remains "in_progress" for extended period
**Diagnosis**:
```bash
# Check event details
curl -X GET "https://api.domain.com/api/v1/key-rotation/events/{event_id}" \
  -H "Authorization: Bearer {admin_token}"
```
**Resolution**:
```bash
# Retry failed rotation
curl -X POST "https://api.domain.com/api/v1/key-rotation/retry/{event_id}" \
  -H "Authorization: Bearer {admin_token}"
```

#### 2. High Migration Volume
**Symptoms**: Rotation taking longer than expected
**Diagnosis**: Check records count in event details
**Resolution**: Adjust batch size and implement throttling
```bash
# Execute with smaller batch size
curl -X POST "https://api.domain.com/api/v1/key-rotation/execute" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "{event_id}",
    "batch_size": 500
  }'
```

#### 3. Database Connection Issues
**Symptoms**: Migration fails with database errors
**Diagnosis**: Check database connectivity and locks
**Resolution**: 
1. Verify database health
2. Check for long-running transactions
3. Consider maintenance window

### Rollback Procedures

#### When to Rollback
- Data corruption detected
- Application functionality severely impacted
- Migration taking too long in production

#### Rollback Steps
```bash
# Rollback to previous key
curl -X POST "https://api.domain.com/api/v1/key-rotation/rollback/{event_id}" \
  -H "Authorization: Bearer {admin_token}"

# Verify rollback completion
curl -X GET "https://api.domain.com/api/v1/key-rotation/events/{event_id}" \
  -H "Authorization: Bearer {admin_token}"
```

## Security Considerations

### Key Generation
- Uses cryptographically secure random number generation
- Minimum key length: 256 bits
- Algorithm: AES-256-GCM (authenticated encryption)

### Key Storage
- Keys stored in environment variables (production)
- Future: Integrate with AWS KMS/Azure Key Vault
- No keys stored in source code or logs

### Access Control
- Admin privileges required for all key operations
- All operations logged to audit trail
- API endpoints protected with authentication

### Compliance Requirements
- SOX: Quarterly key rotation documentation
- PCI DSS: Key rotation for payment-related data
- GDPR: Key rotation for EU user data

## Monitoring and Alerting

### Key Metrics
- Key age (days since creation)
- Rotation success rate
- Migration performance (records/second)
- Error rates during rotation

### Alerts Configuration
- **Critical**: Key older than rotation schedule + grace period
- **Warning**: Key approaching rotation schedule
- **Info**: Successful rotation completion

### Dashboards
- Key rotation status dashboard
- Performance metrics
- Error rate monitoring

## Compliance and Audit

### Audit Requirements
All key rotation activities are logged with:
- Timestamp (UTC)
- User performing action
- Key type and ID
- Operation type
- Success/failure status
- Record counts processed

### Reporting
- Weekly: Key status summary
- Monthly: Rotation performance report
- Quarterly: Compliance audit report
- Ad-hoc: Security incident reports

### Documentation Updates
This document should be reviewed and updated:
- After each major system change
- Following any security incidents
- Quarterly as part of compliance review
- When new key types are added

## Contact Information

### Escalation Path
1. **Level 1**: Development Team
2. **Level 2**: Security Team Lead
3. **Level 3**: CTO/Security Officer

### Emergency Contacts
- **Security Incident**: security@company.com
- **System Administration**: sysadmin@company.com
- **Compliance**: compliance@company.com

## Appendix

### Environment Variables
```bash
# Required environment variables for key rotation
TOKEN_ENCRYPTION_KEY=<32-character-key>
DATABASE_ENCRYPTION_KEY=<32-character-key>
KEY_ROTATION_ENABLED=true
KEY_ROTATION_SCHEDULE_ENABLED=true
```

### API Reference
Full API documentation available at: `/docs#tag/key-rotation`

### Related Documentation
- [Security Architecture](./SECURITY_ARCHITECTURE.md)
- [Compliance Framework](./COMPLIANCE_FRAMEWORK.md)
- [Incident Response Procedures](./INCIDENT_RESPONSE.md)

---

**Document Status**: Active  
**Next Review Date**: March 2025  
**Approved By**: Security Team Lead  
**Classification**: Internal Use Only