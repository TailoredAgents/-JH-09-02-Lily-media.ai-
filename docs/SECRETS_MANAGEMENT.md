# Secrets Management Guide

Comprehensive guide for secure secrets management in the Lily Media AI platform.

## 🔒 Overview

This project implements enterprise-grade secrets management with multiple layers of protection:
- Environment variable based configuration
- SecretStr encryption for sensitive fields
- Production validation and enforcement
- Comprehensive .gitignore protection
- Automated secrets scanning and validation

## 📋 Secrets Management Principles

### 1. Zero Hard-Coded Secrets
✅ **ENFORCED**: No API keys, passwords, or tokens are hard-coded in the source code  
✅ **VALIDATION**: Pre-commit hooks scan for and block hard-coded secrets  
✅ **MONITORING**: Automated secrets detection in CI/CD pipeline  

### 2. Environment-Based Configuration
All sensitive configuration uses environment variables with secure defaults:

```python
# ✅ CORRECT: Environment variable with SecretStr
openai_api_key: SecretStr = Field(default=SecretStr(""), env="OPENAI_API_KEY")

# ❌ WRONG: Hard-coded secret
openai_api_key = "sk-1234567890abcdef"  # NEVER DO THIS
```

### 3. Production Validation
The system automatically validates that production environments have proper secrets:

```python
def validate_production_config(self) -> List[str]:
    """Validate production configuration and return missing required fields"""
    missing_fields = []
    
    if self.environment == "production":
        # Critical security fields
        if not self.SECRET_KEY or self.SECRET_KEY == "your-secret-key-change-this-in-production":
            missing_fields.append("SECRET_KEY")
        
        if not self.encryption_key or self.encryption_key == "your-32-byte-encryption-key-change-this":
            missing_fields.append("ENCRYPTION_KEY")
```

## 🔑 Required Secrets for Production

### Core Security Secrets (CRITICAL)
```bash
# Application secret key (256-bit minimum)
SECRET_KEY=your-ultra-secure-secret-key-here-256-bits-minimum

# JWT signing secret (can be same as SECRET_KEY)
JWT_SECRET=your-jwt-signing-secret-here

# Token encryption key (32 characters exactly)
TOKEN_ENCRYPTION_KEY=your-32-character-encryption-key12
```

### Database Configuration (CRITICAL)
```bash
# PostgreSQL database URL (production)
DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require

# Redis for caching and rate limiting (optional but recommended)
REDIS_URL=redis://username:password@host:port/database
```

### AI Service API Keys (REQUIRED)
```bash
# OpenAI for text generation and moderation
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# xAI for image generation (optional)
XAI_API_KEY=xai-your-xai-api-key-here

# Serper for web research (optional)
SERPER_API_KEY=your-serper-api-key-here
```

### Social Media Platform Secrets (OPTIONAL)
```bash
# Meta (Facebook/Instagram) OAuth
META_APP_ID=your-meta-app-id
META_APP_SECRET=your-meta-app-secret

# Twitter/X OAuth 2.0
TWITTER_CLIENT_ID=your-twitter-client-id
TWITTER_CLIENT_SECRET=your-twitter-client-secret

# LinkedIn OAuth (Partnership Program required)
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
```

### Email Service Configuration (OPTIONAL)
```bash
# SMTP Configuration
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password

# Alternative: SendGrid
SENDGRID_API_KEY=your-sendgrid-api-key

# Alternative: AWS SES
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_REGION=us-east-1

# Alternative: Resend
RESEND_API_KEY=your-resend-api-key
```

## 🛡️ Security Implementation Details

### SecretStr Protection
All sensitive fields use Pydantic's `SecretStr` for automatic masking:

```python
from pydantic import SecretStr

class Settings(BaseSettings):
    # ✅ Secure: Automatically masked in logs and representations
    openai_api_key: SecretStr = Field(default=SecretStr(""), env="OPENAI_API_KEY")
    
    def get_openai_api_key(self) -> str:
        """Safe accessor method for API key value"""
        return self.openai_api_key.get_secret_value()
```

### Production Validation
Critical secrets are validated at startup in production:

```python
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if self.environment == "production":
        secret_key_value = self.SECRET_KEY.get_secret_value()
        if not secret_key_value or secret_key_value == "your-secret-key-change-this-in-production":
            logger.error("🚨 CRITICAL: SECRET_KEY must be set in production environment")
            raise ValueError("CRITICAL: SECRET_KEY must be set in production environment")
```

### Automated Key Generation
For missing encryption keys, the system can generate temporary keys with warnings:

```python
if not encryption_key_value or len(encryption_key_value) < 32:
    logger.warning("⚠️  ENCRYPTION_KEY not set in production - generating temporary key")
    logger.warning("   This is NOT secure for production! Set environment variable:")
    logger.warning("   ENCRYPTION_KEY=your-32-character-encryption-key")
    import secrets
    import string
    temp_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    self.encryption_key = SecretStr(temp_key)
    logger.warning(f"   Generated temporary key: {temp_key}")
```

## 🔍 Secrets Scanning and Prevention

### Pre-Commit Hooks
The `.pre-commit-config.yaml` includes comprehensive secrets detection:

```yaml
# Secrets detection
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.4.0
  hooks:
    - id: detect-secrets
      args: ['--baseline', '.secrets.baseline']
      exclude: \.lock$|package-lock\.json$
```

### Prevent Mock/Placeholder Code
Custom pre-commit hook prevents committing placeholder secrets:

```yaml
- id: no-mock-code
  name: Prevent Mock/Placeholder Code
  entry: python -c "
  import sys, re
  mock_patterns = [
      r'mock[_\s]*data',
      r'placeholder[_\s]*\w+',
      r'your-api-key-here',
      r'your-secret-key-here',
      r'change-this-in-production'
  ]
  # Scan code and reject if patterns found
  "
```

### .gitignore Protection
Comprehensive .gitignore ensures secrets are never committed:

```bash
# SECURITY: Never commit secrets or credentials
.env
.env.local
.env.production
.env.staging
.env.development
.secrets
secrets.txt
credentials.txt
keys.txt
config.ini
*.pem
*.key
*.p12
*.pfx
*.jks

# Database credentials and URLs
database_url.txt
db_credentials.txt

# API Keys and tokens
api_keys.txt
tokens.txt
*.token
```

## 📝 Environment File Management

### Development Environment (.env)
```bash
# Local development settings
ENVIRONMENT=development
SECRET_KEY=development-secret-key-not-for-production
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/socialmedia_dev
OPENAI_API_KEY=sk-proj-your-dev-key-here
```

### Production Environment Template (.env.production.template)
```bash
# Production environment template - COPY and RENAME to .env
# DO NOT commit the actual .env file!

# CRITICAL: Set these in production
SECRET_KEY=CHANGE_THIS_TO_SECURE_SECRET_KEY
JWT_SECRET=CHANGE_THIS_TO_SECURE_JWT_SECRET
TOKEN_ENCRYPTION_KEY=CHANGE_THIS_32_CHARACTER_KEY_123456
DATABASE_URL=postgresql://username:password@host:port/database

# REQUIRED: OpenAI API key for core functionality
OPENAI_API_KEY=sk-proj-your-production-openai-key

# OPTIONAL: Additional services
XAI_API_KEY=xai-your-production-xai-key
REDIS_URL=redis://username:password@host:port/database
```

## 🔐 Key Generation and Rotation

### Generate Secure Keys
Use these methods to generate cryptographically secure keys:

```bash
# Generate 256-bit secret key
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Generate 32-character encryption key  
python -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))"

# Generate UUID-based key
python -c "import uuid; print(str(uuid.uuid4()).replace('-', ''))"
```

### Key Rotation Schedule
Recommended rotation schedule for production:

- **SECRET_KEY**: Rotate every 90 days
- **JWT_SECRET**: Rotate every 90 days  
- **TOKEN_ENCRYPTION_KEY**: Rotate every 180 days
- **API Keys**: Rotate according to provider recommendations
- **Database Passwords**: Rotate every 180 days

### Automated Key Rotation (P0-4c Implementation)
```python
import secrets
import string
from datetime import datetime, timedelta

class KeyRotationManager:
    def __init__(self):
        self.rotation_schedule = {
            'SECRET_KEY': timedelta(days=90),
            'JWT_SECRET': timedelta(days=90),
            'TOKEN_ENCRYPTION_KEY': timedelta(days=180),
        }
    
    def generate_new_key(self, key_type: str) -> str:
        """Generate new cryptographically secure key"""
        if key_type == 'TOKEN_ENCRYPTION_KEY':
            # Exactly 32 characters for encryption key
            return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        else:
            # 64-character URL-safe key for secrets and JWT
            return secrets.token_urlsafe(64)
    
    def should_rotate(self, key_type: str, last_rotation: datetime) -> bool:
        """Check if key should be rotated based on schedule"""
        rotation_interval = self.rotation_schedule.get(key_type, timedelta(days=90))
        return datetime.utcnow() - last_rotation > rotation_interval
```

## 🚨 Security Incidents

### Suspected Key Compromise
If you suspect a key has been compromised:

1. **Immediately rotate the compromised key**
2. **Revoke API access for the old key** 
3. **Update all deployment environments**
4. **Monitor for unauthorized usage**
5. **Review access logs for the time period**
6. **Document the incident for security review**

### Emergency Key Rotation Script
```bash
#!/bin/bash
# emergency_key_rotation.sh - Emergency key rotation script

echo "🚨 EMERGENCY KEY ROTATION"
echo "Generating new secure keys..."

echo "New SECRET_KEY:"
python -c "import secrets; print(secrets.token_urlsafe(64))"

echo "New JWT_SECRET:"  
python -c "import secrets; print(secrets.token_urlsafe(64))"

echo "New TOKEN_ENCRYPTION_KEY:"
python -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))"

echo "⚠️  Update these in your deployment environment immediately!"
echo "⚠️  Restart all application instances after updating keys!"
```

## ✅ Security Checklist

### Pre-Production Checklist
- [ ] All secrets are environment variables (no hard-coded values)
- [ ] Production secrets are unique and secure (not development values)
- [ ] .env files are in .gitignore and never committed
- [ ] SecretStr is used for all sensitive configuration fields
- [ ] Production validation passes without errors
- [ ] API keys have appropriate scopes/permissions
- [ ] Database uses SSL/TLS in production
- [ ] Key rotation schedule is documented and implemented

### Regular Security Review
- [ ] Review .gitignore for completeness
- [ ] Scan codebase for hard-coded secrets
- [ ] Audit API key permissions and usage
- [ ] Check for unused or expired keys
- [ ] Verify encryption key strength
- [ ] Test key rotation procedures
- [ ] Review access logs for anomalies

## 📚 References

- [Pydantic SecretStr Documentation](https://docs.pydantic.dev/latest/usage/types/#secret-types)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [NIST Cryptographic Key Management](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)
- [Pre-commit Secrets Detection](https://github.com/Yelp/detect-secrets)

---

## 🔗 Related Documentation

- **[Authentication Guide](./api/authentication.md)** - API authentication patterns
- **[Deployment Guide](./DEPLOYMENT.md)** - Production deployment security
- **[Security Best Practices](./SECURITY.md)** - Comprehensive security guide
- **[Environment Configuration](./ENVIRONMENT.md)** - Environment setup guide