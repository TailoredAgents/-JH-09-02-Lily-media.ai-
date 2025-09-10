# Key Rotation Quick Reference

## Emergency Commands

### Immediate Key Rotation (Security Breach)
```bash
# Rotate all keys immediately
python -c "
from backend.services.key_rotation_service import get_key_rotation_service, KeyType
service = get_key_rotation_service()
for key_type in KeyType:
    result = service.rotate_key(key_type, force=True, reason='Emergency')
    print(f'{key_type.value}: {result}')
"
```

### Check Key Status
```bash
# Quick health check
python -c "
from backend.services.key_rotation_service import get_key_rotation_service
status = get_key_rotation_service().get_rotation_status()
print('Status:', status)
"
```

### Validate Environment
```bash
# Validate all keys
python backend/core/secrets_validator.py
```

## Monitoring Commands

### Celery Task Status
```bash
# Check running tasks
celery -A backend.tasks.celery_app inspect active

# Check task history
celery -A backend.tasks.celery_app events
```

### Generate Compliance Report
```bash
python -c "
from backend.tasks.key_rotation_tasks import key_rotation_compliance_report
result = key_rotation_compliance_report.delay().get()
print(result)
"
```

## Key Rotation Schedule

| Key Type | Interval | Next Action |
|----------|----------|-------------|
| TOKEN_ENCRYPTION_KEY | 90 days | Check quarterly |
| JWT_SECRET_KEY | 365 days | Check annually |
| WEBHOOK_SIGNING_KEY | 180 days | Check bi-annually |

## Troubleshooting

### Task Failures
1. Check Celery worker: `celery -A backend.tasks.celery_app worker --loglevel=info`
2. Check Redis: `redis-cli ping`
3. Check database: Test connection in application

### Validation Failures
1. Generate new key: `python -c "from backend.core.secrets_validator import generate_secure_secret; print(generate_secure_secret(32))"`
2. Update environment variable
3. Restart services

## Emergency Contacts

- **Development Team**: Check logs and restart services
- **Security Team**: Document incidents
- **Operations Team**: Execute procedures

## Health Check Endpoint

```
GET /health
Response: { "key_rotation": "healthy" }
```