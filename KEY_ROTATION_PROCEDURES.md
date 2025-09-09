# Encryption Key Rotation Procedures

**Document Version:** 1.0  
**Last Updated:** September 8, 2025  
**Classification:** Confidential - Security Operations  
**Compliance:** SOC 2 Type II, ISO 27001, NIST Cybersecurity Framework

## Executive Summary

This document defines comprehensive encryption key rotation procedures for Lily AI Social Media platform. The system implements automated key lifecycle management to ensure cryptographic security, regulatory compliance, and protection against key compromise scenarios.

## Key Types and Rotation Schedules

### 1. Token Encryption Keys (90 Days)
- **Purpose:** OAuth tokens, API keys, session tokens encryption
- **Rotation Interval:** 90 days
- **Grace Period:** 30 days
- **Priority:** High (affects user authentication)
- **Database Tables:** `social_connections`, `user_credentials`, `refresh_token_blacklist`

### 2. Database Encryption Keys (180 Days)  
- **Purpose:** Sensitive database field encryption
- **Rotation Interval:** 180 days
- **Grace Period:** 90 days
- **Priority:** Critical (affects data integrity)
- **Database Tables:** `user_settings`, `payment_methods`, `social_audit`

### 3. File Encryption Keys (365 Days)
- **Purpose:** Uploaded files, exports, backups encryption
- **Rotation Interval:** 365 days
- **Grace Period:** 180 days
- **Priority:** Medium (affects file access)
- **Storage:** Encrypted file storage, export archives

### 4. Session Encryption Keys (30 Days)
- **Purpose:** User session data encryption
- **Rotation Interval:** 30 days
- **Grace Period:** 7 days
- **Priority:** High (affects user experience)
- **Storage:** Redis cache, session storage

### 5. API Signature Keys (90 Days)
- **Purpose:** API request signing and verification
- **Rotation Interval:** 90 days
- **Grace Period:** 30 days
- **Priority:** High (affects API security)
- **Usage:** Webhook signatures, internal API calls

## Automated Rotation Schedule

### Continuous Monitoring (Every 6 Hours)
- **Task:** `key_rotation_health_check`
- **Purpose:** Monitor key ages, detect overdue keys, generate alerts
- **Queue:** `key_rotation` (priority: 9)
- **Alerts:** Keys >150% of rotation interval trigger critical alerts

### Daily Rotation Check (1:00 AM UTC)
- **Task:** `automated_key_rotation_check`
- **Purpose:** Schedule rotations for keys due according to policy
- **Queue:** `key_rotation` (priority: 9)
- **Actions:** Creates rotation events for due keys

### Rotation Execution (Every 4 Hours)
- **Task:** `execute_scheduled_key_rotations`
- **Purpose:** Execute pending rotation events
- **Queue:** `key_rotation` (priority: 9)
- **Batch Size:** 1,000 records per execution (configurable)

### Weekly Cleanup (Sunday 6:00 AM UTC)
- **Task:** `key_rotation_cleanup`
- **Purpose:** Remove expired keys past grace period
- **Queue:** `key_rotation` (priority: 9)
- **Security:** Ensures old keys cannot be misused

### Usage Monitoring (Every 8 Hours)
- **Task:** `key_usage_monitoring`
- **Purpose:** Detect usage anomalies and unused keys
- **Queue:** `key_rotation` (priority: 9)
- **Anomaly Detection:** High usage patterns, unused keys

### Compliance Reporting (Monthly)
- **Task:** `generate_key_rotation_compliance_report`
- **Purpose:** Generate comprehensive compliance report
- **Queue:** `key_rotation` (priority: 9)
- **Output:** Policy adherence, security recommendations

## API Endpoints for Key Management

### Administrative Endpoints (Admin Access Required)

#### POST `/v1/key-rotation/schedule`
Schedule key rotation for specific key type.
```json
{
  "key_type": "token_encryption",
  "force": false
}
```

#### POST `/v1/key-rotation/execute`
Execute scheduled key rotation.
```json
{
  "event_id": "kr_event_12345",
  "batch_size": 1000
}
```

#### GET `/v1/key-rotation/schedule`
Get current rotation schedule and key status.

#### GET `/v1/key-rotation/keys/{key_type}`
Get active keys for specific type (metadata only).

#### POST `/v1/key-rotation/cleanup`
Clean up expired and deprecated keys.

#### GET `/v1/key-rotation/report`
Generate comprehensive rotation compliance report.

#### POST `/v1/key-rotation/emergency-rotation`
Emergency rotation for security incidents.
```json
{
  "key_type": "token_encryption",
  "reason": "suspected_compromise"
}
```

### Scheduler Control Endpoints

#### GET `/v1/key-rotation/scheduler/status`
Get automated scheduler status and statistics.

#### POST `/v1/key-rotation/scheduler/pause`
Pause automated rotation scheduling.

#### POST `/v1/key-rotation/scheduler/resume`
Resume automated rotation scheduling.

## Emergency Procedures

### Key Compromise Response

#### Immediate Actions (0-15 minutes)
1. **Identify Affected Key Type**
   - Determine which key type is compromised
   - Assess scope of potential data exposure

2. **Initiate Emergency Rotation**
   ```bash
   # Via API
   curl -X POST /v1/key-rotation/emergency-rotation \
     -H "Authorization: Bearer {admin_token}" \
     -d '{"key_type": "token_encryption", "reason": "key_compromise"}'
   
   # Via Celery task
   emergency_key_rotation_task.delay("token_encryption", "suspected_compromise")
   ```

3. **Alert Security Team**
   - Notify on-call security personnel
   - Escalate to incident response team
   - Begin incident documentation

#### Short Term Actions (15 minutes - 2 hours)
1. **Monitor Rotation Progress**
   - Track rotation execution status
   - Verify successful data migration
   - Monitor for any failures or errors

2. **Assess Impact**
   - Review audit logs for suspicious activity
   - Identify potentially affected users/sessions
   - Evaluate need for user notification

3. **Verify Security**
   - Confirm old keys are deprecated
   - Test that new keys are functioning
   - Validate encryption/decryption operations

#### Recovery Actions (2-24 hours)
1. **Complete Data Migration**
   - Ensure all encrypted data uses new keys
   - Verify no data remains encrypted with compromised keys
   - Run data integrity checks

2. **Security Review**
   - Analyze how compromise occurred
   - Review access logs and permissions
   - Update security controls if needed

3. **Documentation**
   - Complete incident report
   - Update procedures based on lessons learned
   - Notify stakeholders and regulators if required

### System Recovery Procedures

#### Database Backup Restoration
If key rotation causes data corruption:

1. **Immediate Response**
   ```bash
   # Stop key rotation scheduler
   curl -X POST /v1/key-rotation/scheduler/pause
   
   # Assess extent of corruption
   python manage.py check_data_integrity
   ```

2. **Recovery Process**
   - Restore from most recent clean backup
   - Identify point of failure in rotation process
   - Re-run rotation with corrected procedures
   - Verify data integrity post-recovery

#### Key Store Recovery
If key storage is corrupted or unavailable:

1. **Emergency Key Generation**
   - Generate new keys for critical operations
   - Implement temporary encryption solutions
   - Document emergency key usage

2. **Systematic Recovery**
   - Restore key store from encrypted backups
   - Verify key integrity and metadata
   - Resume normal rotation schedules

## Monitoring and Alerting

### Health Monitoring Metrics
- **Key Age Distribution:** Track age of all active keys
- **Rotation Success Rate:** Percentage of successful rotations
- **Migration Performance:** Time and records processed per rotation
- **Error Rates:** Failed rotations and reasons
- **Usage Patterns:** Key usage anomalies and trends

### Alert Thresholds

#### Critical Alerts (Immediate Response Required)
- Key age >150% of rotation interval
- Failed rotation affecting critical systems
- Key store unavailable or corrupted
- Suspected key compromise indicators
- Emergency rotation triggered

#### Warning Alerts (Response Within 24 Hours)
- Key age >125% of rotation interval
- Rotation execution delays
- High key usage anomalies
- Unused keys beyond retention period
- Performance degradation during rotation

#### Information Alerts (Weekly Review)
- Successful rotation completions
- Expired key cleanup results
- Usage pattern changes
- Schedule adherence reports

### Compliance Monitoring

#### SOC 2 Type II Requirements
- **CC6.1:** Logical access controls documented and tested
- **CC6.7:** Data transmission and disposal controls verified
- **CC6.8:** Key management procedures implemented and audited

#### ISO 27001 Requirements  
- **A.10.1.2:** Key management procedures documented
- **A.12.3.1:** Regular backup and restoration testing
- **A.16.1.5:** Response to information security incidents

#### NIST Framework Alignment
- **PR.DS-1:** Data-at-rest protection through encryption
- **PR.DS-2:** Data-in-transit protection verification
- **DE.CM-1:** Network and system monitoring for key events
- **RS.RP-1:** Response plans tested and updated

## Administrative Procedures

### Planned Maintenance Windows

#### Pre-Maintenance (24 Hours Before)
1. **System Health Check**
   - Verify all key rotation services are operational
   - Check database connectivity and performance
   - Confirm backup systems are current
   - Validate monitoring and alerting systems

2. **Stakeholder Notification**
   - Notify operations team of maintenance window
   - Alert security team to increased monitoring
   - Prepare incident response team for standby

#### During Maintenance
1. **Enhanced Monitoring**
   - Monitor rotation execution closely
   - Track performance metrics in real-time
   - Maintain communication channels open
   - Document any anomalies or issues

2. **Quality Assurance**
   - Verify successful data migration
   - Test encryption/decryption operations
   - Confirm system performance impact
   - Validate security controls

#### Post-Maintenance (6 Hours After)
1. **System Verification**
   - Comprehensive health check of all systems
   - Verify normal operation resumed
   - Check for any delayed issues or errors
   - Update documentation with any changes

### Quarterly Security Review

#### Key Management Assessment
1. **Policy Review**
   - Evaluate rotation schedules against security requirements
   - Review and update emergency procedures
   - Assess compliance with regulatory requirements
   - Update risk assessments

2. **Technical Assessment**
   - Review key storage security mechanisms
   - Evaluate encryption algorithm strength
   - Test disaster recovery procedures
   - Assess monitoring and alerting effectiveness

3. **Process Improvement**
   - Analyze rotation performance metrics
   - Identify automation opportunities
   - Update procedures based on incidents
   - Plan security enhancements

## Training and Documentation

### Role-Based Training Requirements

#### Security Administrators
- **Initial Certification:** 8-hour key management training
- **Annual Recertification:** 4-hour update training
- **Emergency Response:** Quarterly drill participation
- **Documentation:** Maintain current procedure knowledge

#### Operations Team
- **Basic Training:** 2-hour overview of key rotation impact
- **Incident Response:** Understanding of escalation procedures
- **Monitoring:** Key rotation alert interpretation
- **Documentation:** Access to current procedures

#### Development Team
- **Integration Training:** Key rotation API and testing procedures
- **Security Awareness:** Impact of key rotation on applications
- **Code Review:** Key rotation impact assessment
- **Documentation:** Technical implementation guidelines

### Documentation Maintenance

#### Procedure Updates
- **Quarterly Review:** Update procedures based on operational experience
- **Incident-Based Updates:** Revise procedures after security incidents
- **Compliance Reviews:** Update for regulatory requirement changes
- **Version Control:** Maintain change history and approval records

#### Access Control
- **Classification:** Confidential - restricted to security and operations teams
- **Distribution:** Controlled access through secure document management
- **Updates:** Automatic notification to stakeholders for changes
- **Retention:** Maintain historical versions for audit purposes

## Contact Information

### Emergency Contacts
- **Primary Security Contact:** security@lilymedia.ai
- **Incident Response Team:** incident-response@lilymedia.ai
- **Operations Manager:** ops-manager@lilymedia.ai
- **CTO/Security Officer:** cto@lilymedia.ai

### Escalation Matrix
1. **Level 1:** Operations Team (immediate response)
2. **Level 2:** Security Team (15 minutes)
3. **Level 3:** Incident Response Team (30 minutes)
4. **Level 4:** Executive Team (1 hour)

### External Contacts
- **Cloud Provider Security:** [Provider-specific contact]
- **Key Management Service:** [KMS provider contact]
- **Legal Counsel:** [Legal team contact]
- **Regulatory Liaison:** [Compliance contact]

---

**Document Approval:**
- Security Review: ✅ Procedures align with security best practices
- Operations Review: ✅ Procedures are operationally feasible  
- Compliance Review: ✅ Meets SOC 2, ISO 27001, and NIST requirements
- Legal Review: ✅ Incident response procedures meet legal obligations

**Change History:**
- v1.0 (2025-09-08): Initial version - comprehensive key rotation procedures
- Next Review: 2025-12-08 (Quarterly review cycle)

*This document contains sensitive security information and should be protected accordingly. Distribution is restricted to authorized personnel only.*