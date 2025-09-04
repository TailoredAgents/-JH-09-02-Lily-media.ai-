# OAuth Platform Setup Guide

This guide provides step-by-step instructions for setting up OAuth integrations with social media platforms for the Lily Media AI autonomous social media management system.

## Overview

The system supports OAuth integration with the following platforms:
- ✅ **Meta (Facebook & Instagram)** - Production ready
- ✅ **X (Twitter)** - Production ready  
- ✅ **LinkedIn** - Production ready (requires Partnership Program for posting)
- ✅ **TikTok for Business** - Production ready (requires Business API approval)

## Architecture

All OAuth flows are implemented through:
- **Backend**: `backend/api/partner_oauth.py` - Unified OAuth handler for Meta, X, and TikTok
- **Backend**: `backend/api/linkedin_oauth.py` - Dedicated LinkedIn OAuth handler
- **Frontend**: Integration hooks for OAuth flow initiation and callback handling
- **Security**: PKCE for secure OAuth flows, encrypted token storage, audit logging

## Platform-Specific Setup Instructions

### 1. Meta (Facebook & Instagram)

#### Prerequisites
- Facebook Developer Account
- Business verification (required for production)
- Instagram Business Account (optional, for Instagram posting)

#### App Setup Steps

1. **Create Facebook App**
   ```
   Go to: https://developers.facebook.com/apps/
   Choose: Business → Create App
   ```

2. **Add Required Products**
   - Facebook Login for Business
   - Instagram Basic Display (if using Instagram)
   - Instagram Content Publishing (if posting to Instagram)

3. **Configure OAuth Settings**
   ```
   Valid OAuth Redirect URIs:
   - Development: http://localhost:8000/api/oauth/meta/callback
   - Production: https://your-domain.com/api/oauth/meta/callback
   ```

4. **Set Environment Variables**
   ```bash
   META_APP_ID=your_facebook_app_id
   META_APP_SECRET=your_facebook_app_secret
   META_GRAPH_VERSION=v18.0
   FEATURE_PARTNER_OAUTH=true
   ```

5. **Required Permissions & Review**
   - Basic permissions: `pages_show_list`, `pages_read_engagement`
   - Advanced permissions require app review:
     - `pages_manage_posts` (for posting)
     - `instagram_content_publish` (for Instagram posting)
     - `instagram_manage_insights` (for Instagram analytics)

#### Testing
```bash
# Start OAuth flow
curl -X GET "http://localhost:8000/api/oauth/meta/start" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 2. X (Twitter)

#### Prerequisites
- X Developer Account (v2)
- Approved for Essential access (minimum)

#### App Setup Steps

1. **Create X Developer App**
   ```
   Go to: https://developer.twitter.com/en/portal/dashboard
   Create Project → Create App
   ```

2. **Configure OAuth 2.0 Settings**
   ```
   OAuth 2.0 Settings:
   - Type: Web App, Automated App or Bot
   - Callback URLs:
     * Development: http://localhost:8000/api/oauth/x/callback
     * Production: https://your-domain.com/api/oauth/x/callback
   ```

3. **Set Environment Variables**
   ```bash
   X_CLIENT_ID=your_x_client_id
   X_CLIENT_SECRET=your_x_client_secret
   FEATURE_PARTNER_OAUTH=true
   ```

4. **Required Scopes**
   - `tweet.read` - Read tweets
   - `tweet.write` - Post tweets (requires approval for production)
   - `users.read` - Read user profile
   - `offline.access` - Refresh tokens

#### Testing
```bash
# Start OAuth flow
curl -X GET "http://localhost:8000/api/oauth/x/start" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. LinkedIn

#### Prerequisites
- LinkedIn Developer Account
- LinkedIn Partnership Program approval (for posting features)

#### App Setup Steps

1. **Create LinkedIn App**
   ```
   Go to: https://www.linkedin.com/developers/apps
   Create App → Fill required information
   ```

2. **Add Required Products**
   ```
   Required Products:
   - Sign In with LinkedIn using OpenID Connect ✅ (automatic)
   - Share on LinkedIn ⚠️ (requires Partnership Program approval)
   ```

3. **Configure OAuth Settings**
   ```
   OAuth Redirect URLs:
   - Development: http://localhost:8000/api/linkedin/callback
   - Production: https://your-domain.com/api/linkedin/callback
   ```

4. **Set Environment Variables**
   ```bash
   LINKEDIN_CLIENT_ID=your_linkedin_client_id
   LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
   LINKEDIN_REDIRECT_URI=http://localhost:8000/api/linkedin/callback
   ```

5. **Partnership Program Application**
   ```
   Apply at: https://docs.microsoft.com/en-us/linkedin/marketing/getting-started
   Required for:
   - Content posting (UGC API)
   - Post analytics  
   - Company page management
   - Advanced user data
   ```

#### Testing
```bash
# Check integration status
curl -X GET "http://localhost:8000/api/linkedin/status"

# Start OAuth flow (basic profile access)
curl -X GET "http://localhost:8000/api/linkedin/auth" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. TikTok for Business

#### Prerequisites
- TikTok for Business account
- TikTok Business API access approval
- Business verification

#### App Setup Steps

1. **Apply for TikTok Business API Access**
   ```
   Go to: https://developers.tiktok.com/
   Apply for: TikTok for Business API
   Wait for: Approval (can take 2-4 weeks)
   ```

2. **Create TikTok Developer App**
   ```
   After approval:
   - Access TikTok Developer Portal
   - Create new app
   - Configure OAuth settings
   ```

3. **Configure OAuth Settings**
   ```
   Redirect URIs:
   - Development: http://localhost:8000/api/oauth/tiktok/callback  
   - Production: https://your-domain.com/api/oauth/tiktok/callback
   ```

4. **Set Environment Variables**
   ```bash
   TIKTOK_CLIENT_ID=your_tiktok_client_key
   TIKTOK_CLIENT_SECRET=your_tiktok_client_secret
   FEATURE_PARTNER_OAUTH=true
   ```

5. **Required Scopes**
   - `user.info.basic` - User profile information
   - `video.list` - List user videos
   - `video.publish` - Post videos (requires additional approval)

#### Testing
```bash
# Start OAuth flow (after approval)
curl -X GET "http://localhost:8000/api/oauth/tiktok/start" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Environment Configuration

### Complete Environment Variables

```bash
# Backend URL
BACKEND_URL=http://localhost:8000

# Feature Flags
FEATURE_PARTNER_OAUTH=true

# Meta/Facebook
META_APP_ID=your_facebook_app_id
META_APP_SECRET=your_facebook_app_secret
META_GRAPH_VERSION=v18.0

# X/Twitter  
X_CLIENT_ID=your_x_client_id
X_CLIENT_SECRET=your_x_client_secret

# LinkedIn
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/api/linkedin/callback

# TikTok
TIKTOK_CLIENT_ID=your_tiktok_client_key
TIKTOK_CLIENT_SECRET=your_tiktok_client_secret

# Encryption (for token storage)
FERNET_KEY=your_32_byte_base64_encoded_key

# Database
DATABASE_URL=postgresql://user:password@localhost/dbname
```

## API Endpoints

### Partner OAuth (Meta, X, TikTok)

```bash
# Start OAuth flow
GET /api/oauth/{platform}/start
- Platforms: meta, x, tiktok
- Returns: authorization URL and state

# Handle OAuth callback  
GET /api/oauth/{platform}/callback?code=...&state=...
- Returns: success status and next step

# Get assets (Meta only)
GET /api/oauth/meta/assets?state=...
- Returns: Facebook Pages and Instagram accounts

# Connect account
POST /api/oauth/meta/connect
POST /api/oauth/x/connect  
POST /api/oauth/tiktok/connect
- Body: {state, page_id} (Meta) or {state} (X/TikTok)
- Returns: connection details

# List connections
GET /api/oauth/connections
- Returns: all active connections for user

# Disconnect account
DELETE /api/oauth/{connection_id}
- Body: {confirmation: true}
- Returns: disconnection confirmation

# Refresh tokens
POST /api/oauth/{connection_id}/refresh
- Returns: task information for refresh operation
```

### LinkedIn OAuth

```bash
# Get integration status
GET /api/linkedin/status

# Start OAuth flow
GET /api/linkedin/auth
- Returns: authorization URL and state

# Handle OAuth callback
GET /api/linkedin/callback?code=...&state=...
- Returns: profile and token information

# Get user profile
GET /api/linkedin/profile?access_token=...
- Returns: LinkedIn profile data

# Test posting (requires Partnership approval)
POST /api/linkedin/test-post?access_token=...&person_urn=...
- Body: {content, visibility}
- Returns: post result or partnership requirement notice
```

## Security Features

### Token Security
- **Encryption**: All tokens encrypted with Fernet before database storage
- **Expiration**: Automatic token expiration tracking and refresh
- **Audit Logging**: Complete audit trail for all OAuth operations

### OAuth Security
- **PKCE**: Code challenge/verifier for secure OAuth flows (X, TikTok)
- **State Validation**: CSRF protection through state parameter verification
- **Connection Limits**: Production limits on concurrent connections

### Error Handling
- **Graceful Degradation**: Fallback behavior when OAuth services unavailable
- **Rate Limiting**: Built-in rate limiting for OAuth endpoints
- **Monitoring**: Comprehensive error tracking and alerting

## Testing & Validation

### Local Development Testing

1. **Start Services**
   ```bash
   # Backend
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   
   # Frontend  
   cd frontend && npm run dev
   ```

2. **Test OAuth Flows**
   ```bash
   # Test each platform
   curl -X GET "http://localhost:8000/api/oauth/meta/start" -H "Authorization: Bearer $TOKEN"
   curl -X GET "http://localhost:8000/api/oauth/x/start" -H "Authorization: Bearer $TOKEN"  
   curl -X GET "http://localhost:8000/api/oauth/tiktok/start" -H "Authorization: Bearer $TOKEN"
   curl -X GET "http://localhost:8000/api/linkedin/auth" -H "Authorization: Bearer $TOKEN"
   ```

### Production Checklist

- [ ] All platform apps created and configured
- [ ] Environment variables set in production
- [ ] SSL certificates configured for HTTPS callbacks
- [ ] Rate limiting configured and tested
- [ ] Token encryption keys securely managed
- [ ] Audit logging enabled and monitored
- [ ] Error alerting configured
- [ ] Privacy policy and terms of service published (required by platforms)
- [ ] App review submissions completed (where required)

## Troubleshooting

### Common Issues

1. **OAuth Callback Failures**
   - Verify redirect URLs match exactly (including http/https)
   - Check environment variables are set correctly
   - Ensure feature flags are enabled

2. **Token Exchange Errors**
   - Verify client secrets are correct
   - Check platform-specific API requirements
   - Review scope permissions

3. **Connection Listing Issues**
   - Ensure database migrations are current
   - Verify organization_id mapping is correct
   - Check SocialConnection table structure

### Platform-Specific Issues

**Meta**:
- Instagram Business Account required for Instagram features
- App review required for publishing permissions
- Pages must be managed by the app user

**X**: 
- Essential access minimum requirement
- Posting requires elevated access approval
- Rate limits are strict in development

**LinkedIn**:
- Partnership Program required for posting
- Basic access only provides profile information
- Review process can take 4-6 weeks

**TikTok**:
- Business API approval required
- Long approval process (2-4 weeks)
- Limited developer documentation

## Support & Resources

### Platform Documentation
- [Meta Developer Docs](https://developers.facebook.com/docs/)
- [X API Documentation](https://developer.twitter.com/en/docs)
- [LinkedIn Developer Portal](https://docs.microsoft.com/en-us/linkedin/)
- [TikTok Business API](https://developers.tiktok.com/doc/business-api-overview)

### Internal Resources
- OAuth implementation: `backend/api/partner_oauth.py`
- LinkedIn implementation: `backend/api/linkedin_oauth.py`
- Database models: `backend/db/models.py`
- Frontend integration: `frontend/src/hooks/useOAuth.js`

---

*Last updated: September 2025*
*System version: Production v1.0*