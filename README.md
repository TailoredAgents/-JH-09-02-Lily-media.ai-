# Lily Media AI - Social Media Management Platform 🤖

**Enterprise-Grade Multi-Tenant AI-Powered Social Media Management Platform**

*Transform your social media presence with intelligent automation and advanced analytics*

![Version](https://img.shields.io/badge/version-2.1-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![React](https://img.shields.io/badge/react-18.x-blue)
![License](https://img.shields.io/badge/license-Proprietary-red)
![Production Ready](https://img.shields.io/badge/production-ready-brightgreen)
![Multi-Tenant](https://img.shields.io/badge/multi--tenant-RBAC-purple)

## 🚦 CI/CD Status

[![Backend Tests](https://github.com/ai-social-media-agent/ai-social-media-agent/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/ai-social-media-agent/ai-social-media-agent/actions/workflows/backend-tests.yml)
[![Frontend CI](https://github.com/ai-social-media-agent/ai-social-media-agent/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/ai-social-media-agent/ai-social-media-agent/actions/workflows/frontend-ci.yml)
[![Security Scan](https://github.com/ai-social-media-agent/ai-social-media-agent/actions/workflows/security-scan.yml/badge.svg)](https://github.com/ai-social-media-agent/ai-social-media-agent/actions/workflows/security-scan.yml)
[![Code Quality](https://github.com/ai-social-media-agent/ai-social-media-agent/actions/workflows/code-quality.yml/badge.svg)](https://github.com/ai-social-media-agent/ai-social-media-agent/actions/workflows/code-quality.yml)
[![Deploy Production](https://github.com/ai-social-media-agent/ai-social-media-agent/actions/workflows/deploy-production.yml/badge.svg)](https://github.com/ai-social-media-agent/ai-social-media-agent/actions/workflows/deploy-production.yml)

[![codecov](https://codecov.io/gh/ai-social-media-agent/ai-social-media-agent/branch/main/graph/badge.svg)](https://codecov.io/gh/ai-social-media-agent/ai-social-media-agent)
[![Maintainability](https://api.codeclimate.com/v1/badges/maintainability)](https://codeclimate.com/github/ai-social-media-agent/ai-social-media-agent/maintainability)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=ai-social-media-agent&metric=security_rating)](https://sonarcloud.io/dashboard?id=ai-social-media-agent)

## 🌟 Overview

AI Social Media Manager is a sophisticated, enterprise-grade platform that leverages artificial intelligence to automate social media content creation, publishing, and analytics across multiple platforms. Built with modern technologies and designed for scalability, it provides comprehensive social media management capabilities for businesses, marketers, and content creators.

**Current Status (August 2025)**: Recently converted from closed registration-key system to open SaaS authentication with custom JWT implementation. Users can now register freely without registration keys. Complete OAuth partner integration system with connection management, rate limiting, and resilient publishing pipeline is now live.

## 🌐 Production Deployment

### Live Instance (Render.com)
- **Main API**: https://socialmedia-api-wxip.onrender.com (FastAPI backend)
- **Frontend**: https://socialmedia-frontend-pycc.onrender.com (React app)
- **Database**: PostgreSQL with pgvector extension
- **Redis**: Configured for caching and rate limiting
- **Status**: Production-ready with OAuth partner integrations

### 🚀 Key Features

- **🤖 AI-Powered Content Generation**: OpenAI GPT-4o and GPT-4o-mini with built-in web search and enhanced reasoning
- **🎨 AI Image Generation**: xAI Grok-2 Vision model with streaming generation and platform optimization
- **📱 Multi-Platform Support**: X/Twitter, Instagram, Facebook via OAuth Partner Integration
- **🔗 Connection Management**: OAuth-based social media account connections with health monitoring
- **⚡ Resilient Publishing**: Per-tenant rate limiting, circuit breakers, and connection-based publishing
- **📊 Advanced Analytics**: Real-time performance tracking and insights
- **🔍 Enhanced Semantic Memory**: text-embedding-3-large with 3072-dimensional vectors for superior search accuracy
- **⚡ Automated Workflows**: Intelligent content scheduling with draft verification gates
- **🎯 Goal Tracking**: Comprehensive goal management with progress monitoring
- **🛡️ Custom JWT Security**: Open SaaS authentication with email verification and password reset
- **📈 Performance Optimization**: Multi-tenant isolation, Redis caching, connection pooling
- **🚩 Feature Flag System**: Controlled rollout of new features with environment-based configuration

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React 18)                      │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │  Dashboard  │  Analytics  │   Content   │    Goals    │  │
│  │   Overview  │ Insights    │ Management  │  Tracking   │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
                          ┌────▼────┐
                          │   API   │
                          │ Gateway │
                          └────┬────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                  Backend Services (FastAPI)                 │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │Integration  │   Content   │  Research   │  Workflow   │  │
│  │  Services   │ Generation  │ Automation  │Orchestration│  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │  Analytics  │   Memory    │    Auth     │ Performance │  │
│  │  Engine     │   System    │  Security   │ Optimizer   │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       │                       │                       │
   ┌───▼────┐            ┌────▼────┐            ┌────▼────┐
   │        │            │         │            │         │
   │ PostgreSQL         │  Redis   │            │  FAISS  │
   │Database│            │  Cache   │            │ Vector  │
   │        │            │         │            │  Store  │
   └────────┘            └─────────┘            └─────────┘
```

---

## 🤖 Autonomous Social Inbox System

The platform features a comprehensive **AI-powered social interaction management system** that automatically handles comments and messages across social media platforms:

### 🔥 Core Capabilities

- **Intelligent Response Generation**: GPT-5 powered responses using company knowledge base and personality profiles
- **Real-Time WebSocket Updates**: Live monitoring and instant notifications for new interactions
- **Multi-Platform Support**: Handles comments and direct messages on Facebook, Instagram, and X/Twitter
- **Smart Escalation**: Automatically escalates complex issues or sensitive topics to human oversight

### 🎯 Response Automation

- **Personality-Driven Replies**: Configurable response personalities (professional, friendly, casual, etc.)
- **Template Management**: Dynamic response templates with variable substitution
- **Business Hours Integration**: Respects configured business hours and auto-response schedules
- **Confidence Thresholds**: Only auto-responds when AI confidence exceeds configured thresholds
- **Keyword Filtering**: Automatic escalation for predefined keywords (complaints, legal terms, etc.)

### 🚀 Technical Implementation

- **Production Webhooks**: Secure webhook endpoints for Facebook, Instagram, and X/Twitter APIs
- **Signature Verification**: HMAC-based webhook security validation
- **Database Integration**: Comprehensive interaction tracking and response history
- **WebSocket Manager**: Real-time connection management with heartbeat and reconnection logic
- **Content Library Integration**: Leverages uploaded images and brand assets in responses

### 📊 Management Interface

- **Live Social Inbox**: Real-time dashboard showing all incoming interactions
- **Response History**: Complete audit trail of AI-generated and manual responses  
- **Template Editor**: Visual template management with variable placeholders
- **Settings Panel**: Granular control over auto-response behavior and escalation rules
- **Analytics Dashboard**: Response performance metrics and engagement tracking

---

## 📋 Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS (10.15+), or Windows 10+ with WSL2
- **Python**: 3.11 or higher
- **Node.js**: 20.x or higher
- **Memory**: Minimum 8GB RAM (16GB recommended for production)
- **Storage**: 20GB free space (SSD recommended)
- **Network**: Stable internet connection for API integrations

### Required Accounts & Services

Before setting up the project, you'll need accounts and API access for the following services:

#### 🔐 Authentication Services
- **Custom JWT System** (Built-in)
  - No external authentication service required
  - Open SaaS registration and login
  - Email verification support (optional)
  - Secure token-based authentication

#### 🤖 AI Services
- **OpenAI API** 
  - GPT-4o and GPT-4o-mini access required for content generation
  - API key with sufficient credits
  - Pay-as-you-go pricing (see pricing section for details)
  - Source: https://openai.com/pricing
- **xAI API**
  - Grok-2 Vision model for advanced image generation
  - API key required for image creation features
  - Streaming image generation capabilities
  - Source: https://x.ai/

#### 📱 Social Media Platform APIs

##### Twitter/X API
- **Cost**: 
  - Free tier: $0/month (100 reads, 500 writes per month)
  - Basic tier: $200/month (15K reads, 50K writes per month)
  - Pro tier: $5,000/month (1M reads, 300K writes per month)
  - Enterprise tier: Custom pricing
  - Source: https://docs.x.com/x-api
- **Requirements**: 
  - X Developer Account
  - App creation and API v2 access
  - Bearer Token, API Key, API Secret, Access Token, Access Secret
- **Limitations**: 
  - Free tier: Very limited for production use
  - Basic tier: Suitable for small to medium applications
  - Pro tier: Full archive search and filtered stream access

##### Partner OAuth Integration
- **Meta (Facebook/Instagram)**:
  - Facebook Developer Account required
  - Business verification for advanced features
  - OAuth 2.0 with PKCE for secure connections
  - Page and Instagram account selection via Asset Picker
- **X (Twitter)**:
  - X Developer Account with OAuth 2.0 enabled
  - Client ID and Client Secret required
  - Rate limits: Basic tier $200/month for posting
- **Connection Management**:
  - Health monitoring with expiry tracking
  - Secure token storage with encryption
  - Automatic reconnection prompts

##### Instagram Business API
- **Cost**: 
  - API Access: Free
  - Requires Facebook Business account (free)
  - Source: https://developers.facebook.com/docs/instagram-api
- **Requirements**:
  - Facebook Developer Account
  - Instagram Business Account (converted from personal)
  - Facebook Page connected to Instagram Business Account
  - App review for publishing permissions (can take weeks)
- **Limitations**:
  - Rate limits: 25 API calls per hour for content publishing
  - 200 calls per hour for other endpoints
  - Business verification required for advanced features
  - Source: https://developers.facebook.com/docs/graph-api/overview/rate-limiting

##### Facebook Graph API
- **Cost**: 
  - API Access: Free
  - Business verification may be required for certain features
  - Advanced features may require Facebook Business account
  - Source: https://developers.facebook.com/docs/graph-api
- **Requirements**:
  - Facebook Developer Account
  - Facebook App with required permissions
  - Business verification for advanced features (can take weeks)
  - App review process for publishing permissions
- **Limitations**:
  - Rate limiting varies by endpoint and user type
  - Stricter limits for newer apps
  - Some features require business verification
  - Source: https://developers.facebook.com/docs/graph-api

##### TikTok for Developers API
- **Cost**: 
  - Pricing not publicly disclosed
  - Enterprise partnerships and custom agreements only
  - Contact TikTok directly for pricing information
  - Source: https://developers.tiktok.com/
- **Requirements**:
  - TikTok for Business account
  - Developer application approval (invite-only)
  - Business verification required
  - Partnership agreement for most APIs
- **Critical Note**: TikTok API access is extremely restricted
- **Access**: Limited to approved partners and enterprise clients
- **Available APIs**: Login Kit, Share Kit, Content Posting API (restricted)
- **Alternatives**: 
  - TikTok Business Creative Center for analytics
  - Manual posting via TikTok Business Suite
  - Third-party scheduling tools (very limited functionality)
- **Limitations**:
  - Not available for general developer access
  - Most APIs require special partnership agreements

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/lily-ai-socialmedia.git
cd lily-ai-socialmedia
```

### 2. Backend Setup

#### Install Python Dependencies

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Database Setup

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Install PostgreSQL (macOS with Homebrew)
brew install postgresql
brew services start postgresql

# Create database
sudo -u postgres createdb lily_ai_socialmedia

# Install Redis (Ubuntu/Debian)
sudo apt install redis-server

# Install Redis (macOS with Homebrew)
brew install redis
brew services start redis
```

#### Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (see detailed configuration section below)
nano .env
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Run the Application

```bash
# Terminal 1: Start backend
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start frontend (if not already running)
cd frontend
npm run dev

# Terminal 3: Start background workers
cd backend
celery -A tasks.celery_app worker --loglevel=info
```

---

## ⚙️ Detailed Configuration

### Environment Variables (.env file)

Create a `.env` file in the project root with the following configuration:

```bash
# ================================
# CORE APPLICATION SETTINGS
# ================================
ENVIRONMENT=development
SECRET_KEY=your-super-secret-key-min-32-chars
DEBUG=true
API_VERSION=v1

# ================================
# DATABASE CONFIGURATION
# ================================
DATABASE_URL=postgresql://username:password@localhost:5432/lily_ai_socialmedia
REDIS_URL=redis://localhost:6379/0

# ================================
# AUTHENTICATION (Custom JWT)
# ================================
JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440
# Email verification (optional)
EMAIL_VERIFICATION_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# ================================
# AI SERVICES
# ================================
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4o
OPENAI_RESEARCH_MODEL=gpt-4o-mini
OPENAI_DEEP_RESEARCH_MODEL=gpt-4o
OPENAI_CATEGORIZATION_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
OPENAI_MAX_TOKENS=4000

# xAI Services (for image generation)
XAI_API_KEY=your-xai-api-key
XAI_MODEL=grok-2-image
XAI_BASE_URL=https://api.x.ai/v1

# ================================
# TWITTER/X API CONFIGURATION
# ================================
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_SECRET=your_twitter_access_secret

# ================================
# PARTNER OAUTH CONFIGURATION
# ================================
# Meta (Facebook/Instagram)
META_APP_ID=your_meta_app_id
META_APP_SECRET=your_meta_app_secret
META_REDIRECT_URI=http://localhost:3000/oauth/meta/callback

# X (Twitter) OAuth 2.0
X_CLIENT_ID=your_x_client_id
X_CLIENT_SECRET=your_x_client_secret
X_REDIRECT_URI=http://localhost:3000/oauth/x/callback

# Feature Flags
VITE_FEATURE_PARTNER_OAUTH=true

# ================================
# FACEBOOK/INSTAGRAM API CONFIGURATION
# ================================
FACEBOOK_APP_ID=your_facebook_app_id
FACEBOOK_APP_SECRET=your_facebook_app_secret
FACEBOOK_ACCESS_TOKEN=your_long_lived_access_token
INSTAGRAM_BUSINESS_ID=your_instagram_business_account_id

# ================================
# TIKTOK API CONFIGURATION (Optional - Paid)
# ================================
TIKTOK_CLIENT_KEY=your_tiktok_client_key
TIKTOK_CLIENT_SECRET=your_tiktok_client_secret
TIKTOK_REDIRECT_URI=http://localhost:3000/callback/tiktok

# ================================
# PERFORMANCE & CACHING
# ================================
CACHE_TTL=300
MAX_CACHE_SIZE=1000
CONNECTION_POOL_SIZE=100
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# ================================
# EMAIL & NOTIFICATIONS (Optional)
# ================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourdomain.com

# ================================
# MONITORING & LOGGING
# ================================
LOG_LEVEL=INFO
SENTRY_DSN=your_sentry_dsn_url (optional)
PROMETHEUS_PORT=9090

# ================================
# FRONTEND CONFIGURATION
# ================================
VITE_API_URL=http://localhost:8000
VITE_FEATURE_PARTNER_OAUTH=true
VITE_ENVIRONMENT=development
```

---

## 🔧 Detailed Setup Instructions

### Partner OAuth Configuration

1. **Meta (Facebook/Instagram) Setup**
   ```bash
   # Visit developers.facebook.com
   # Create new app for "Business" use case
   # Add Facebook Login and Instagram products
   # Set redirect URI: http://localhost:3000/oauth/meta/callback
   # Get App ID and App Secret
   ```

2. **X (Twitter) OAuth 2.0 Setup**
   ```bash
   # Visit developer.twitter.com
   # Create new app with OAuth 2.0 enabled
   # Set redirect URI: http://localhost:3000/oauth/x/callback
   # Get Client ID and Client Secret
   # Enable read/write permissions
   ```

3. **Feature Flag Configuration**
   ```bash
   # Enable partner OAuth features
   VITE_FEATURE_PARTNER_OAUTH=true
   # This gates the Integrations page and OAuth flows
   ```

### Social Media API Setup

#### Twitter/X API Setup (Required for Twitter Integration)

1. **Apply for Developer Account**
   ```bash
   # Visit https://developer.twitter.com/
   # Apply for developer account (1-3 day approval)
   # Describe your use case: "AI-powered social media management tool"
   ```

2. **Create Twitter App**
   ```bash
   # In Twitter Developer Portal:
   # - Create new app
   # - Enable OAuth 1.0a and OAuth 2.0
   # - Set callback URL: http://localhost:3000/callback/twitter
   # - Generate API keys and tokens
   ```

3. **Upgrade to Paid Plan** (Required for posting)
   ```bash
   # Basic Tier: $100/month
   # - 10,000 tweets per month
   # - Read and write access
   # - Essential for posting functionality
   ```

####  API Setup

1. **Create  App**
   ```bash
   # Visit https://www..com/developers/
   # Create new app with company page
   # Request permissions: r_liteprofile, r_emailaddress, w_member_social
   ```

2. **Verification Process**
   ```bash
   #  requires app review for posting capabilities
   # Provide detailed use case and demo video
   # Approval typically takes 5-10 business days
   ```

#### Instagram Business API Setup

1. **Convert to Business Account**
   ```bash
   # Convert Instagram personal account to Business Account
   # Connect to a Facebook Page (create one if needed)
   # This connection is required for API access
   ```

2. **Facebook App Configuration**
   ```bash
   # In Facebook Developers (developers.facebook.com):
   # - Create new app
   # - Add Instagram Basic Display product
   # - Add Facebook Login product
   # - Add Pages API product
   ```

3. **Business Verification**
   ```bash
   # For advanced features, complete Facebook Business Verification
   # Upload business documents
   # Process takes 3-5 business days
   ```

#### Facebook Graph API Setup

1. **Create Facebook App**
   ```bash
   # Visit developers.facebook.com
   # Create app for "Business" use case
   # Add Facebook Login and Pages API products
   ```

2. **Generate Long-lived Access Token**
   ```bash
   # Use Graph API Explorer to generate user access token
   # Exchange for long-lived token (60 days)
   # Set up token refresh in your application
   ```

#### TikTok API Setup (Optional - Limited Availability)

⚠️ **Important**: TikTok API access is highly restricted and currently invite-only

1. **Business Account Required**
   ```bash
   # Create TikTok for Business account
   # Complete business verification with official documents
   # Pricing is not publicly available - contact TikTok directly
   ```

2. **Developer Application**
   ```bash
   # Visit developers.tiktok.com
   # Submit detailed application with business use case
   # Requires approval from TikTok (invite-only basis)
   # Approval process: 2-4 weeks minimum, often longer
   ```

3. **Alternative Approach (Recommended)**
   ```bash
   # For most users:
   # - Use TikTok Business Creative Center for insights
   # - Manual posting workflow
   # - Focus on other platforms with available APIs
   # - Consider TikTok integration as future enhancement
   ```

---

## 🚀 Running the Application

### Development Mode

```bash
# Start all services for development
make dev

# Or manually:

# Terminal 1: Backend API
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Background Workers
cd backend
celery -A tasks.celery_app worker --loglevel=info

# Terminal 4: Redis (if not running as service)
redis-server

# Terminal 5: PostgreSQL (if not running as service)
pg_ctl -D /usr/local/var/postgres start
```

### Production Mode

```bash
# Build frontend
cd frontend
npm run build

# Start production services
cd backend
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Start background workers
celery -A tasks.celery_app worker --loglevel=info -c 4

# Start scheduler
celery -A tasks.celery_app beat --loglevel=info
```

### Docker Deployment (Recommended for Production)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale workers
docker-compose up -d --scale worker=4
```

---

## 📖 Usage Guide

### First-Time Setup

1. **Create Admin User**
   ```bash
   # Navigate to http://localhost:3000
   # Click "Sign Up" and create your account
   # First user is automatically assigned admin role
   # Email verification is optional (configurable)
   ```

2. **Connect Social Media Accounts**
   ```bash
   # Navigate to Integrations page (feature flag required)
   # Click "Connect" for Meta (Facebook/Instagram)
   # Click "Connect" for X (Twitter)
   # View connection health and manage existing connections
   # Test connections with draft content publishing
   ```

3. **Configure AI Settings**
   ```bash
   # Navigate to Settings > AI Configuration
   # Verify OpenAI API key is working
   # Set content generation preferences
   # Configure brand voice and guidelines
   ```

### Basic Operations

#### Creating Content
```bash
# Method 1: AI Generation
1. Go to Content > Generate
2. Enter topic, platform, and preferences
3. Review and edit generated content
4. Schedule or publish immediately

# Method 2: Manual Creation
1. Go to Content > Create
2. Select platform and content type
3. Write content with AI assistance
4. Add media, hashtags, and scheduling
```

#### Setting Up Workflows
```bash
# Navigate to Workflows > Create
1. Choose workflow type (daily, trending, goal-driven)
2. Configure platforms and posting schedule
3. Set content parameters and goals
4. Enable automation and monitoring
```

#### Analytics and Monitoring
```bash
# Dashboard provides real-time overview
# Analytics > Detailed Reports for deep insights
# Performance > Platform Metrics for optimization
# Goals > Progress Tracking for business objectives
```

---

## 🔍 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Restart PostgreSQL
sudo systemctl restart postgresql

# Check database exists
psql -U postgres -l

# Create database if missing
createdb -U postgres ai_social_media
```

#### Redis Connection Issues
```bash
# Check Redis status
redis-cli ping

# Restart Redis
sudo systemctl restart redis-server

# Clear Redis cache if needed
redis-cli FLUSHALL
```

#### Social Media API Issues
```bash
# Check API credentials in logs
tail -f backend/logs/api.log

# Test API connections
python backend/scripts/test_integrations.py

# Common fixes:
# - Verify API keys are correct
# - Check rate limits haven't been exceeded
# - Ensure OAuth tokens haven't expired
```

#### Frontend Build Issues
```bash
# Clear Node modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# Clear browser cache
# Restart development server
npm run dev
```

### API Rate Limits

Each platform has specific rate limits:

- **Twitter**: 300 requests per 15 minutes (Basic tier)
- ****: 100 requests per hour per user
- **Instagram**: 200 requests per hour per user
- **Facebook**: 600 requests per 10 minutes per user
- **TikTok**: Very strict limits (varies by plan)

The application automatically handles rate limiting with intelligent retry mechanisms.

### Performance Optimization

```bash
# Monitor performance
curl http://localhost:8000/health
curl http://localhost:8000/metrics

# Check cache statistics
curl http://localhost:8000/api/performance/stats

# Monitor database performance
psql -U postgres -d ai_social_media -c "SELECT * FROM pg_stat_activity;"
```

---

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m performance   # Performance tests only

# Run with coverage
pytest --cov=backend --cov-report=html

# Run frontend tests
cd frontend
npm test
```

### Test Configuration

The project includes comprehensive test suites:
- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing
- **Performance Tests**: Load and benchmark testing
- **Security Tests**: Vulnerability scanning
- **End-to-End Tests**: Complete workflow testing

---

## 📊 Monitoring & Analytics

### Application Monitoring

The application includes built-in monitoring:

```bash
# Health checks
curl http://localhost:8000/health

# Performance metrics
curl http://localhost:8000/metrics

# Integration status
curl http://localhost:8000/api/integrations/metrics/collection
```

### Log Management

```bash
# Application logs location
backend/logs/
├── api.log              # API request logs
├── integrations.log     # Social media API logs
├── workflows.log        # Automation workflow logs
└── errors.log          # Error and exception logs

# View real-time logs
tail -f backend/logs/api.log

# Search logs
grep "ERROR" backend/logs/*.log
```

### Performance Metrics

Key metrics to monitor:
- **API Response Times**: < 200ms average
- **Cache Hit Rate**: > 80%
- **Database Query Performance**: < 50ms average
- **Background Job Processing**: < 30s average
- **Error Rate**: < 1%

---

## 🔒 Security

### Security Features

- **Multi-layer Authentication**: Auth0 + JWT
- **API Security**: Rate limiting, input validation, HTTPS
- **Data Protection**: Encryption at rest and in transit
- **Social Media Token Security**: Encrypted token storage
- **GDPR Compliance**: Data privacy and user rights

### Security Best Practices

```bash
# Regular security updates
pip-review --local --interactive

# Check for vulnerabilities
safety check
bandit -r backend/

# Monitor security logs
grep "SECURITY" backend/logs/*.log
```

---

## 🔄 Updates & Maintenance

### Regular Maintenance Tasks

```bash
# Weekly tasks
1. Update dependencies: pip-review --local --interactive
2. Clean up logs: find backend/logs -name "*.log" -mtime +30 -delete
3. Database optimization: VACUUM ANALYZE in PostgreSQL
4. Cache cleanup: Redis FLUSHDB if needed

# Monthly tasks
1. Security audit: Run security scans
2. Performance review: Analyze metrics and optimize
3. Backup verification: Test backup and restore procedures
4. API credential rotation: Update social media tokens
```

### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Update backend dependencies
pip install -r requirements.txt

# Update frontend dependencies
cd frontend
npm install

# Run database migrations
alembic upgrade head

# Restart services
systemctl restart ai-social-media
```

---

## 💰 Cost Estimation

### Monthly Operating Costs

| Service | Free Tier | Basic Paid | Production | Source |
|---------|-----------|------------|------------|--------|
| **X/Twitter API** | $0 (100 reads, 500 writes/mo) | $200/month (15K reads, 50K writes/mo) | $5,000/month (1M reads, 300K writes/mo) | [X API Pricing](https://docs.x.com/x-api) |
| **OpenAI API** | Pay-as-you-go | ~$20-100/month* | ~$100-1000/month* | [OpenAI Pricing](https://platform.openai.com/pricing) |
| **xAI API** | Pay-as-you-go | ~$10-50/month* | ~$50-500/month* | [xAI Pricing](https://x.ai/pricing) |
| **Auth0** | Free (25K external users) | $0.10/user/month (B2C Essentials) | $0.24+/user/month (Professional) | [Auth0 Pricing](https://auth0.com/pricing) |
| ** API** | Free (basic personal) | Contact  | Contact  | [ Developers](https://developers..com/) |
| **Facebook/Instagram API** | Free | Free | Free (with business verification) | [Meta for Developers](https://developers.facebook.com/docs/graph-api) |
| **TikTok API** | Not available publicly | Enterprise partnerships only | Custom pricing | [TikTok Developers](https://developers.tiktok.com/) |
| **Hosting (ex: DigitalOcean)** | $0 (local development) | $24/month (Basic Droplet) | $200+/month (Production) | [DigitalOcean Pricing](https://www.digitalocean.com/pricing) |
| **Database (PostgreSQL)** | $0 (local development) | $15/month (managed DB) | $100+/month (Production DB) | [DigitalOcean DB](https://www.digitalocean.com/pricing/managed-databases) |
| **Redis Cache** | $0 (local development) | $15/month (managed Redis) | $50+/month (Production Redis) | [DigitalOcean Redis](https://www.digitalocean.com/pricing/managed-databases) |
| **Total Estimated** | ~$0-20/month | ~$274-374/month** | ~$1,395+/month | |

*AI API costs are usage-based and can vary significantly:
- GPT-4o: $0.005-0.015 per 1K tokens (input/output)
- GPT-4o-mini: $0.0001-0.0006 per 1K tokens
- xAI Grok-2 Vision: $0.01-0.03 per image generation
- Text embeddings: $0.00013 per 1K tokens
- Costs depend heavily on usage volume and model selection

**Budget-Friendly Setup**: 
- Start with X Free tier + OpenAI GPT-4o-mini + local development = ~$20-50/month
- Basic production setup with X Basic tier = ~$250-350/month

**Note: X API pricing increased significantly in 2024. The Basic tier now costs $200/month (previously $100).

---

## 🤝 Contributing

### Development Workflow

```bash
# 1. Fork the repository
# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes and test
pytest
npm test

# 4. Commit with conventional format
git commit -m "feat: add new social media integration"

# 5. Push and create pull request
git push origin feature/your-feature-name
```

### Code Standards

- **Python**: Black formatter, flake8 linting, type hints
- **JavaScript**: Prettier formatter, ESLint, React best practices
- **Documentation**: Comprehensive docstrings and comments
- **Testing**: Minimum 80% test coverage required

---

## 📞 Support

### Getting Help

1. **Documentation**: Check this README and API documentation
2. **Issues**: Create GitHub issue with detailed description
3. **Discussions**: Use GitHub Discussions for questions
4. **Community**: Join our Discord server for real-time help

### Common Support Requests

- **API Setup Issues**: Most common - follow platform-specific guides
- **Authentication Problems**: Verify Auth0 configuration
- **Performance Issues**: Check system requirements and optimize
- **Integration Failures**: Verify API credentials and rate limits

---

## 💼 Commercial Licensing & Enterprise Solutions

### **ENTERPRISE-READY AI SOCIAL MEDIA PLATFORM**

**Copyright (c) 2025 Tailored Agents LLC. All Rights Reserved.**

This AI Social Media Content Agent is a **commercial software solution** designed for businesses, enterprises, and individuals seeking professional social media management capabilities.

### 🏢 **LICENSING TIERS AVAILABLE**

| License Tier | Price | Use Case | Features |
|--------------|-------|----------|----------|
| **Personal** | **FREE** | Individual, non-commercial | 3 accounts, basic features |
| **Small Business** | **$49/month** | Single business entity | 10 accounts, email support, 5 users |
| **Enterprise** | **$199/month** | Large organizations | 50 accounts, priority support, unlimited users |
| **Commercial Services** | **$499/month** | Service providers/agencies | 200 client accounts, white-label, revenue sharing |
| **Enterprise Unlimited** | **$999/month** | Enterprise-scale operations | Unlimited accounts, custom development |

### ✅ **AUTHORIZED USES**

With proper licensing, you may use this software for:

- ✅ **Business Operations**: Internal social media management for your company
- ✅ **Client Services**: Providing social media management to clients (Commercial Services License)
- ✅ **Personal Use**: Individual social media management (Personal License)
- ✅ **Enterprise Integration**: Custom integrations and enterprise deployments
- ✅ **White-Label Solutions**: Branded solutions for service providers

### 🚫 **USAGE RESTRICTIONS**

Without proper licensing, the following are prohibited:

- ❌ **Unlicensed Commercial Use**: Using beyond your licensing tier limits
- ❌ **Reverse Engineering**: Extracting proprietary algorithms or architecture  
- ❌ **Unauthorized Distribution**: Sharing, copying, or redistributing the software
- ❌ **Competing Products**: Creating competing platforms using our IP
- ❌ **License Violations**: Exceeding account limits or usage parameters

### 💰 **ENTERPRISE BENEFITS**

**Why Choose Our Commercial License:**

- 🔒 **Legal Compliance**: Fully licensed for commercial use
- 🛠️ **Enterprise Support**: Dedicated technical and account management
- 📊 **SLA Guarantees**: 99.5% uptime with professional support tiers
- 🔧 **Custom Development**: Tailored features and integrations available
- 📈 **Scalable Architecture**: Handles enterprise-scale social media operations
- 🏷️ **White-Label Options**: Brand the platform as your own solution

### 📞 **Get Licensed Today**

**Ready to get started with proper licensing?**

**Tailored Agents LLC**  
📧 **Sales**: sales@tailoredagents.com  
📞 **Phone**: 1-800-TAILORED (1-800-824-5673)  
🌐 **Website**: https://tailoredagents.com  
📋 **Legal**: legal@tailoredagents.com

### 🛡️ **Legal Framework**

This software is protected under:
- **Commercial Software License Agreement** (See [LICENSE](LICENSE) file)
- **United States Copyright Law** (17 U.S.C. § 101 et seq.)
- **Delaware State Contract Law**
- **Trade Secret Protection** (Uniform Trade Secrets Act)

**📋 Complete licensing terms and conditions available in our [LICENSE](LICENSE) file.**

---

## 🚀 **Get Started with Enterprise Licensing**

1. **Choose Your Tier**: Select the licensing tier that fits your business needs
2. **Contact Sales**: Reach out to discuss your requirements and get pricing
3. **Deploy Quickly**: Get up and running with professional onboarding support
4. **Scale Confidently**: Grow your social media operations with enterprise-grade infrastructure

**Ready to transform your social media management? [Contact our sales team today!](mailto:sales@tailoredagents.com)**

---

## 🙏 Acknowledgments

- **OpenAI** for GPT-4o and GPT-4o-mini API and AI capabilities
- **xAI** for Grok-2 Vision image generation capabilities
- **Custom JWT System** for secure authentication
- **FastAPI** for the high-performance backend framework
- **React** for the modern frontend framework
- **All social media platforms** for providing developer APIs
- **Open source community** for amazing tools and libraries

---

## 🗺️ Roadmap

### Version 2.1 (Next Quarter)
- [ ] Advanced video content generation
- [ ] Multi-language content support
- [ ] Enhanced analytics dashboard
- [ ] Mobile app development

### Version 2.2 (Next Half)
- [ ] AI-powered image generation
- [ ] Advanced workflow automation
- [ ] Enterprise team collaboration
- [ ] White-label solutions

### Version 3.0 (Next Year)
- [ ] Machine learning content optimization
- [ ] Voice-to-content conversion
- [ ] Advanced competitor analysis
- [ ] Global expansion features

---

**🚀 Ready to revolutionize your social media management with AI? Follow the setup guide above and start creating engaging content across all platforms!**

*For technical support or business inquiries, please contact our team or create an issue in the GitHub repository.*