# Key Rotation Procedures Documentation

## Overview

This document provides comprehensive procedures for encryption key rotation in the Lily Media AI platform. The system implements automated key rotation for security compliance, including SOC 2 Type II requirements, and provides both automated and manual key management capabilities.

## Architecture

### Key Types

The system manages several types of encryption keys:

1. **TOKEN_ENCRYPTION_KEY** - OAuth partner token encryption (32 characters)
2. **JWT_SECRET_KEY** - JWT signing and verification
3. **WEBHOOK_SIGNING_KEY** - Webhook signature validation  
4. **ENCRYPTION_KEY** - General purpose data encryption
5. **API_SIGNING_KEY** - API request signing

### Components

- **KeyRotationService** (`backend/services/key_rotation_service.py`) - Core key rotation logic
- **AutomatedKeyRotationScheduler** (`backend/services/automated_key_rotation_scheduler.py`) - Scheduling engine
- **Key Rotation Tasks** (`backend/tasks/key_rotation_tasks.py`) - Celery background tasks
- **Secrets Validator** (`backend/core/secrets_validator.py`) - Key validation and security checks

## Automated Key Rotation

### Rotation Schedule

| Key Type | Rotation Interval | Compliance Requirement |
|----------|-------------------|------------------------|
| TOKEN_ENCRYPTION_KEY | 90 days | SOC 2 Type II |
| JWT_SECRET_KEY | 365 days | Industry Standard |
| WEBHOOK_SIGNING_KEY | 180 days | Security Best Practice |
| ENCRYPTION_KEY | 90 days | SOC 2 Type II |
| API_SIGNING_KEY | 180 days | Security Best Practice |

### Celery Tasks

#### 1. Health Check Task
**Task**: `key_rotation_health_check`  
**Schedule**: Every 4 hours  
**Purpose**: Monitor key rotation system health

```python
# Execute health check
celery -A backend.tasks.celery_app worker --loglevel=info
```

#### 2. Rotation Check Task
**Task**: `automated_key_rotation_check`  
**Schedule**: Daily at 2:00 AM UTC  
**Purpose**: Check for keys due for rotation

#### 3. Execute Rotations Task
**Task**: `execute_scheduled_key_rotations`  
**Schedule**: On-demand (triggered by rotation check)  
**Purpose**: Perform actual key rotations

#### 4. Compliance Reporting Task
**Task**: `key_rotation_compliance_report`  
**Schedule**: Weekly on Sundays  
**Purpose**: Generate compliance reports

## Manual Key Rotation Procedures

### Emergency Key Rotation

When immediate key rotation is required (security breach, compliance requirement):

#### Step 1: Assess the Situation
```bash
# Check current key status
python -c "
from backend.services.key_rotation_service import get_key_rotation_service
service = get_key_rotation_service()
status = service.get_rotation_status()
print('Key Rotation Status:', status)
"
```

#### Step 2: Initiate Emergency Rotation
```bash
# Rotate specific key type immediately
python -c "
from backend.services.key_rotation_service import get_key_rotation_service, KeyType
service = get_key_rotation_service()
result = service.rotate_key(KeyType.TOKEN_ENCRYPTION_KEY, force=True, reason='Emergency rotation')
print('Rotation Result:', result)
"
```

#### Step 3: Verify Rotation
```bash
# Verify the rotation completed successfully
python -c "
from backend.services.key_rotation_service import get_key_rotation_service
from backend.core.secrets_validator import validate_secrets_on_startup
import os

service = get_key_rotation_service()
status = service.get_rotation_status()
print('Post-rotation Status:', status)

# Validate new secrets
secrets_valid, errors = validate_secrets_on_startup(os.getenv('ENVIRONMENT', 'production'))
print('Secrets Valid:', secrets_valid)
if errors:
    print('Validation Errors:', errors)
"
```

### Planned Key Rotation

For scheduled maintenance rotations:

#### Step 1: Schedule Rotation Window
- Coordinate with operations team
- Schedule during low-traffic periods
- Prepare rollback procedures

#### Step 2: Pre-rotation Validation
```bash
# Validate current environment
python backend/core/secrets_validator.py

# Check key rotation service health
python -c "
from backend.tasks.key_rotation_tasks import key_rotation_health_check
result = key_rotation_health_check.delay()
print('Health Check Result:', result.get())
"
```

#### Step 3: Execute Planned Rotation
```bash
# Trigger automated rotation check
python -c "
from backend.tasks.key_rotation_tasks import automated_key_rotation_check
result = automated_key_rotation_check.delay()
print('Rotation Check Result:', result.get())
"

# If rotations are scheduled, execute them
python -c "
from backend.tasks.key_rotation_tasks import execute_scheduled_key_rotations
result = execute_scheduled_key_rotations.delay(max_rotations=5)
print('Execution Result:', result.get())
"
```

#### Step 4: Post-rotation Verification
```bash
# Generate compliance report
python -c "
from backend.tasks.key_rotation_tasks import key_rotation_compliance_report
result = key_rotation_compliance_report.delay()
print('Compliance Report:', result.get())
"
```

## Key Storage and Security

### Environment Variables

Keys are stored as environment variables and validated on startup:

```bash
# Required keys for production
TOKEN_ENCRYPTION_KEY=<32-character-key>
JWT_SECRET_KEY=<secure-jwt-secret>
WEBHOOK_SIGNING_KEY=<webhook-signing-key>
```

### Key Generation

Secure key generation follows cryptographic standards:

```python
from backend.core.secrets_validator import generate_secure_secret

# Generate 32-character encryption key
encryption_key = generate_secure_secret(32)

# Generate 64-character JWT secret
jwt_secret = generate_secure_secret(64)
```

### Key Validation

All keys are validated for security compliance:

- **Minimum Length**: Based on key type and security requirements
- **Entropy Check**: Ensure sufficient randomness
- **Pattern Validation**: Avoid predictable patterns
- **Expiry Tracking**: Monitor key age and rotation schedules

## Compliance and Audit

### SOC 2 Type II Compliance

The key rotation system meets SOC 2 Type II requirements:

1. **Automated Rotation**: Keys rotate automatically per security policy
2. **Audit Logging**: All rotations are logged for audit trails
3. **Access Controls**: Key rotation requires administrative privileges
4. **Monitoring**: Continuous monitoring of key health and compliance
5. **Incident Response**: Emergency rotation procedures for security incidents

### Audit Trail

All key rotation activities are logged:

```json
{
  "timestamp": "2025-09-08T10:30:00Z",
  "event_type": "key_rotation",
  "key_type": "TOKEN_ENCRYPTION_KEY",
  "action": "rotated",
  "reason": "scheduled_rotation",
  "user_id": "system",
  "compliance_status": "compliant",
  "next_rotation_due": "2025-12-07T10:30:00Z"
}
```

### Compliance Reporting

Weekly compliance reports track:

- Key rotation schedule adherence
- Overdue rotations (critical alerts)
- Security policy compliance
- Audit log integrity
- System health metrics

## Troubleshooting

### Common Issues

#### 1. Key Rotation Task Failures

**Symptoms**: Celery tasks failing, rotation not completing
**Diagnosis**:
```bash
# Check Celery worker logs
celery -A backend.tasks.celery_app events

# Check task status
python -c "
from backend.tasks.key_rotation_tasks import key_rotation_health_check
result = key_rotation_health_check.delay()
print('Status:', result.status)
print('Result:', result.result if result.ready() else 'Pending')
"
```

**Resolution**:
1. Restart Celery workers
2. Check database connectivity
3. Verify environment variable access
4. Check Redis/broker connectivity

#### 2. Key Validation Failures

**Symptoms**: Startup validation errors, key length warnings
**Diagnosis**:
```bash
# Run secrets validation
python backend/core/secrets_validator.py

# Check specific key
python -c "
from backend.core.secrets_validator import SecretsValidator
import os
validator = SecretsValidator()
result = validator.validate_secret('TOKEN_ENCRYPTION_KEY', os.getenv('TOKEN_ENCRYPTION_KEY'))
print('Validation Result:', result)
"
```

**Resolution**:
1. Generate new compliant keys
2. Update environment variables
3. Restart application services

#### 3. Database Connection Issues

**Symptoms**: Key rotation service cannot update database
**Diagnosis**:
```bash
# Test database connection
python -c "
from backend.db.database import get_db
try:
    db = next(get_db())
    print('Database connection: OK')
except Exception as e:
    print('Database connection failed:', e)
"
```

**Resolution**:
1. Check DATABASE_URL environment variable
2. Verify database server availability
3. Check connection pool settings

### Emergency Procedures

#### Security Breach Response

1. **Immediate Actions**:
   ```bash
   # Rotate all keys immediately
   python -c "
   from backend.services.key_rotation_service import get_key_rotation_service
   from backend.services.key_rotation_service import KeyType
   service = get_key_rotation_service()
   
   # Rotate all key types
   for key_type in KeyType:
       result = service.rotate_key(key_type, force=True, reason='Security breach response')
       print(f'Rotated {key_type.value}: {result}')
   "
   ```

2. **Verification**:
   ```bash
   # Verify all services restart successfully
   python backend/core/secrets_validator.py
   ```

3. **Audit Trail**:
   - Document the incident
   - Generate compliance report
   - Notify security team
   - Update incident response log

#### Service Recovery

If key rotation causes service interruption:

1. **Rollback Procedure**:
   - Restore previous environment variables from backup
   - Restart affected services
   - Verify service functionality

2. **Investigation**:
   - Check rotation logs
   - Identify root cause
   - Update procedures to prevent recurrence

## Monitoring and Alerting

### Health Checks

Monitor key rotation system health:

```bash
# System health endpoint
curl -X GET "https://your-api/health" | jq '.key_rotation'

# Direct health check
python -c "
from backend.tasks.key_rotation_tasks import key_rotation_health_check
result = key_rotation_health_check()
print('Health Status:', result)
"
```

### Alerts Configuration

Configure monitoring alerts for:

1. **Overdue Rotations**: Keys past rotation schedule
2. **Task Failures**: Celery task execution failures
3. **Validation Errors**: Key security compliance failures
4. **Service Unavailability**: Key rotation service health issues

### Metrics

Track key rotation metrics:

- Rotation success rate
- Average rotation duration  
- Keys approaching expiry
- Compliance score
- System availability

## Security Considerations

### Access Control

- Key rotation requires administrative privileges
- Production key access is restricted
- All rotation activities are audited
- Emergency procedures have approval processes

### Key Lifecycle

1. **Generation**: Cryptographically secure random generation
2. **Storage**: Environment variables, never in code
3. **Rotation**: Automated based on security policy
4. **Archival**: Secure disposal of old keys
5. **Recovery**: Emergency procedures for key restoration

### Best Practices

- Never commit keys to version control
- Use secure key generation methods
- Implement proper key validation
- Monitor key rotation health continuously
- Document all procedures thoroughly
- Test emergency procedures regularly

## Related Documentation

- [Security Hardening Guide](../SECURITY.md)
- [Environment Variables Guide](../ENVIRONMENT_VARIABLES.md)
- [Compliance Documentation](../docs/compliance/)
- [Incident Response Procedures](../docs/incident-response/)

## Support

For key rotation support and emergencies:

1. **Development Team**: Check troubleshooting section
2. **Operations Team**: Follow emergency procedures
3. **Security Team**: Document incidents and compliance
4. **Compliance Team**: Review audit trails and reports

---

**Document Version**: 1.0  
**Last Updated**: September 8, 2025  
**Next Review**: December 8, 2025  
**Owner**: Security & Compliance Team