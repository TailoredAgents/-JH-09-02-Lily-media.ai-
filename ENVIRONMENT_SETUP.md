# Environment Setup Guide

Complete environment configuration guide for Lily Media AI Platform.

## 🚀 Quick Start

```bash
# Interactive setup wizard (recommended)
python scripts/setup_wizard.py

# Manual setup
cp .env.example .env
cp frontend/.env.example frontend/.env
# Edit configuration files as needed
```

## 📋 Environment Variables Reference

### Core Application Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | Yes | `development` | Environment type: `development`, `production`, `testing` |
| `SECRET_KEY` | Yes | Generated | Application secret key (32+ characters) |
| `JWT_SECRET_KEY` | Yes | Generated | JWT token signing key (32+ characters) |
| `DEBUG` | No | `true` | Enable debug mode (development only) |
| `API_VERSION` | No | `v1` | API version prefix |

### Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection for caching and tasks |

**PostgreSQL URL Format:**
```
postgresql://username:password@hostname:port/database_name
```

**Example Configurations:**
```bash
# Local PostgreSQL
DATABASE_URL=postgresql://postgres:password@localhost:5432/lily_media_ai

# Render.com PostgreSQL
DATABASE_URL=postgresql://user:pass@hostname.oregon-postgres.render.com/dbname

# AWS RDS PostgreSQL
DATABASE_URL=postgresql://user:pass@instance.region.rds.amazonaws.com:5432/dbname
```

### AI Services Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for content generation |
| `OPENAI_MODEL` | No | `gpt-4o` | Primary OpenAI model |
| `OPENAI_RESEARCH_MODEL` | No | `gpt-4o-mini` | Model for research tasks |
| `OPENAI_EMBEDDING_MODEL` | No | `text-embedding-3-large` | Embedding model |
| `XAI_API_KEY` | No | - | xAI API key for image generation |
| `XAI_MODEL` | No | `grok-2-image` | xAI image generation model |
| `XAI_BASE_URL` | No | `https://api.x.ai/v1` | xAI API base URL |

**Getting AI API Keys:**
- **OpenAI**: https://platform.openai.com/api-keys
- **xAI**: https://x.ai/ (for Grok-2 image generation)

### Social Platform OAuth Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `META_APP_ID` | No | - | Meta (Facebook/Instagram) App ID |
| `META_APP_SECRET` | No | - | Meta (Facebook/Instagram) App Secret |
| `X_CLIENT_ID` | No | - | X (Twitter) OAuth 2.0 Client ID |
| `X_CLIENT_SECRET` | No | - | X (Twitter) OAuth 2.0 Client Secret |
| `LINKEDIN_CLIENT_ID` | No | - | LinkedIn OAuth Client ID |
| `LINKEDIN_CLIENT_SECRET` | No | - | LinkedIn OAuth Client Secret |

**OAuth Setup Guides:**
- **Meta**: https://developers.facebook.com/
- **X (Twitter)**: https://developer.twitter.com/
- **LinkedIn**: https://www.linkedin.com/developers/

### Email Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SMTP_HOST` | No | - | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `SMTP_USERNAME` | No | - | SMTP username |
| `SMTP_PASSWORD` | No | - | SMTP password |
| `EMAIL_FROM` | No | - | From email address |
| `EMAIL_VERIFICATION_ENABLED` | No | `false` | Enable email verification |

**Gmail App Password Setup:**
1. Enable 2-factor authentication
2. Go to Google Account settings
3. Security → App passwords
4. Generate app password for "Mail"

### Monitoring and Observability

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | No | - | Sentry error tracking DSN |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `PROMETHEUS_PORT` | No | `9090` | Prometheus metrics port |

### Performance Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CACHE_TTL` | No | `300` | Default cache TTL in seconds |
| `MAX_CACHE_SIZE` | No | `1000` | Maximum cache entries |
| `CONNECTION_POOL_SIZE` | No | `100` | Database connection pool size |
| `RATE_LIMIT_REQUESTS` | No | `100` | Rate limit requests per window |
| `RATE_LIMIT_WINDOW` | No | `3600` | Rate limit window in seconds |

### Frontend Configuration

Create `frontend/.env`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | Yes | `http://localhost:8000` | Backend API URL |
| `VITE_ENVIRONMENT` | No | `development` | Frontend environment |
| `VITE_FEATURE_PARTNER_OAUTH` | No | `false` | Enable OAuth integrations |
| `VITE_APP_NAME` | No | `Lily Media AI` | Application name |

### Feature Flags

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_FEATURE_PARTNER_OAUTH` | No | `false` | Enable partner OAuth flows |
| `VITE_FEATURE_AUTONOMOUS_POSTING` | No | `true` | Enable autonomous posting |
| `VITE_FEATURE_DEEP_RESEARCH` | No | `true` | Enable deep research features |
| `VITE_FEATURE_BILLING` | No | `true` | Enable billing integration |

## 🔒 Security Best Practices

### Secret Key Generation

```bash
# Generate secure secret keys
python -c "import secrets; print(secrets.token_urlsafe(32))"
python -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*') for _ in range(32)))"
```

### Environment Security

1. **Never commit `.env` files to version control**
2. **Use different keys for different environments**
3. **Rotate keys regularly in production**
4. **Use environment-specific configurations**
5. **Enable HTTPS in production**

### Database Security

```bash
# Strong database passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Connection SSL
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

## 🌍 Environment-Specific Configurations

### Development Environment

```bash
# .env
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=postgresql://postgres:password@localhost:5432/lily_media_ai_dev
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=DEBUG

# frontend/.env
VITE_API_URL=http://localhost:8000
VITE_ENVIRONMENT=development
```

### Production Environment

```bash
# .env
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://user:strongpass@prod-host:5432/lily_media_ai?sslmode=require
REDIS_URL=redis://prod-redis:6379/0?ssl=true
LOG_LEVEL=INFO
SENTRY_DSN=https://your-dsn@sentry.io/project

# frontend/.env
VITE_API_URL=https://api.yourdomain.com
VITE_ENVIRONMENT=production
```

### Testing Environment

```bash
# .env.test
ENVIRONMENT=testing
DEBUG=false
DATABASE_URL=postgresql://postgres:password@localhost:5432/lily_media_ai_test
REDIS_URL=redis://localhost:6379/1
LOG_LEVEL=WARNING
```

## 🐳 Docker Environment

```yaml
# docker-compose.yml environment section
environment:
  - ENVIRONMENT=production
  - SECRET_KEY=${SECRET_KEY}
  - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/lily_media_ai
  - REDIS_URL=redis://redis:6379/0
  - OPENAI_API_KEY=${OPENAI_API_KEY}
```

## ☁️ Cloud Provider Configurations

### Render.com

Environment variables in Render dashboard:

```
ENVIRONMENT=production
SECRET_KEY=[auto-generated]
DATABASE_URL=[from database service]
REDIS_URL=[from redis service]
OPENAI_API_KEY=[your-key]
```

### Railway

```bash
# Using Railway CLI
railway variables set ENVIRONMENT=production
railway variables set SECRET_KEY=$(openssl rand -base64 32)
railway variables set OPENAI_API_KEY=your-key
```

### Heroku

```bash
# Using Heroku CLI
heroku config:set ENVIRONMENT=production
heroku config:set SECRET_KEY=$(openssl rand -base64 32)
heroku config:set OPENAI_API_KEY=your-key
```

### AWS/Azure/GCP

Use their respective secret management services:
- **AWS**: Parameter Store or Secrets Manager
- **Azure**: Key Vault
- **GCP**: Secret Manager

## 🔧 Validation and Testing

### Environment Validation

```bash
# Test environment loading
python -c "
from backend.core.config import settings
print(f'Environment: {settings.ENVIRONMENT}')
print(f'Database: {settings.DATABASE_URL[:50]}...')
print('✅ Environment loaded successfully')
"
```

### Connection Testing

```bash
# Test database connection
python scripts/test_database.py

# Test Redis connection
python scripts/test_redis.py

# Test AI services
python scripts/test_ai_services.py
```

### Configuration Checklist

- [ ] All required environment variables set
- [ ] Database connection successful
- [ ] Redis connection successful (if used)
- [ ] OpenAI API key valid
- [ ] Social platform OAuth configured (if needed)
- [ ] Email configuration working (if needed)
- [ ] Monitoring configured (production)
- [ ] SSL certificates configured (production)

## 🆘 Troubleshooting

### Common Issues

**Environment not loading:**
```bash
# Check file exists and permissions
ls -la .env
cat .env | head -5

# Check for syntax errors
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ Environment loaded')"
```

**Database connection fails:**
```bash
# Test PostgreSQL connection
psql $DATABASE_URL -c "SELECT version();"

# Check if database exists
psql $DATABASE_URL -c "\l"
```

**Redis connection fails:**
```bash
# Test Redis connection
redis-cli -u $REDIS_URL ping
```

**AI API errors:**
```bash
# Test OpenAI API
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models | jq '.data[0].id'
```

### Environment File Templates

Complete templates available in:
- `.env.example` - Backend configuration
- `frontend/.env.example` - Frontend configuration
- `docker-compose.env.example` - Docker environment

### Getting Help

1. Run the setup wizard: `python scripts/setup_wizard.py`
2. Check the troubleshooting section in README.md
3. Validate your configuration with test scripts
4. Check application logs for specific errors