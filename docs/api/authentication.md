# Authentication Guide

Complete guide to authentication and security for the Lily Media AI API.

## 🔐 Authentication Overview

The Lily Media AI API uses a hybrid authentication system combining:
- **API Keys** for service-to-service authentication
- **OAuth 2.0** for user authorization and social platform connections
- **JWT Tokens** for session management

## 📋 Table of Contents

- [Getting Your API Key](#getting-your-api-key)
- [API Key Authentication](#api-key-authentication)
- [OAuth 2.0 Flow](#oauth-20-flow)
- [JWT Token Management](#jwt-token-management)
- [Social Platform OAuth](#social-platform-oauth)
- [Security Best Practices](#security-best-practices)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

## 🔑 Getting Your API Key

### Step 1: Create Your Account

```bash
curl -X POST "https://api.lily-media.ai/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "secure-password",
    "first_name": "Your",
    "last_name": "Name"
  }'
```

### Step 2: Verify Your Email (if enabled)

```bash
curl -X POST "https://api.lily-media.ai/api/auth/verify-email" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "verification-token-from-email"
  }'
```

### Step 3: Login and Get JWT Token

```bash
curl -X POST "https://api.lily-media.ai/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "secure-password"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user_123",
    "email": "your-email@example.com",
    "plan": "free"
  }
}
```

### Step 4: Generate API Key

```bash
curl -X POST "https://api.lily-media.ai/api/auth/api-keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Application Key",
    "scopes": ["content:write", "images:generate", "posts:publish"]
  }'
```

## 🔐 API Key Authentication

### Basic Usage

Include your API key in the `Authorization` header:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://api.lily-media.ai/api/health"
```

### Python Example

```python
import requests

headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}

response = requests.get(
    "https://api.lily-media.ai/api/auth/me", 
    headers=headers
)
```

### Node.js Example

```javascript
const axios = require('axios');

const apiClient = axios.create({
  baseURL: 'https://api.lily-media.ai/api',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
  }
});

const user = await apiClient.get('/auth/me');
```

### API Key Scopes

| Scope | Description | Endpoints |
|-------|-------------|-----------|
| `content:read` | Read content | GET `/content/*` |
| `content:write` | Create/edit content | POST/PUT `/content/*` |
| `images:generate` | Generate images | POST `/images/generate` |
| `posts:publish` | Publish posts | POST `/posts`, PUT `/posts/*/publish` |
| `analytics:read` | Read analytics | GET `/analytics/*` |
| `integrations:manage` | Manage connections | All `/integrations/*` |
| `admin:all` | Full access | All endpoints |

## 🔄 OAuth 2.0 Flow

### Authorization Code Flow

Perfect for web applications with a backend.

#### Step 1: Authorization URL

```bash
curl -X POST "https://api.lily-media.ai/api/auth/oauth/authorize" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "your_client_id",
    "response_type": "code",
    "redirect_uri": "https://yourapp.com/callback",
    "scope": "content:write images:generate",
    "state": "random_state_string"
  }'
```

Response:
```json
{
  "authorization_url": "https://api.lily-media.ai/oauth/authorize?client_id=...",
  "state": "random_state_string"
}
```

#### Step 2: Exchange Code for Token

```bash
curl -X POST "https://api.lily-media.ai/api/auth/oauth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "authorization_code",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "code": "authorization_code_from_callback",
    "redirect_uri": "https://yourapp.com/callback"
  }'
```

### Client Credentials Flow

For server-to-server authentication.

```bash
curl -X POST "https://api.lily-media.ai/api/auth/oauth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "scope": "content:write images:generate"
  }'
```

### Refresh Token Flow

```bash
curl -X POST "https://api.lily-media.ai/api/auth/oauth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "refresh_token",
    "refresh_token": "your_refresh_token",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret"
  }'
```

## 🎫 JWT Token Management

### Token Structure

JWT tokens contain three parts:
- **Header**: Token type and algorithm
- **Payload**: User claims and metadata
- **Signature**: Verification signature

### Token Validation

```python
import jwt
import requests

def validate_token(token):
    try:
        # Get public key from API
        jwks_response = requests.get("https://api.lily-media.ai/.well-known/jwks.json")
        jwks = jwks_response.json()
        
        # Decode and validate
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience="api.lily-media.ai"
        )
        
        return payload
    except jwt.InvalidTokenError:
        return None
```

### Token Refresh

```python
def refresh_access_token(refresh_token):
    response = requests.post(
        "https://api.lily-media.ai/api/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    
    if response.status_code == 200:
        data = response.json()
        return data["access_token"]
    
    return None
```

## 🔗 Social Platform OAuth

### Meta (Facebook/Instagram) Connection

```python
def connect_meta_account():
    # Step 1: Get authorization URL
    response = requests.post(
        "https://api.lily-media.ai/api/integrations/connect",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "platform": "meta",
            "redirect_uri": "https://yourapp.com/oauth/meta/callback"
        }
    )
    
    auth_url = response.json()["authorization_url"]
    
    # Redirect user to auth_url
    # After callback, exchange code for connection
    
    # Step 2: Complete connection
    connection_response = requests.post(
        "https://api.lily-media.ai/api/integrations/callback",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "platform": "meta",
            "code": "authorization_code",
            "state": "state_from_callback"
        }
    )
    
    return connection_response.json()
```

### X (Twitter) Connection

```python
def connect_x_account():
    # OAuth 2.0 PKCE flow for X
    response = requests.post(
        "https://api.lily-media.ai/api/integrations/connect",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "platform": "x",
            "redirect_uri": "https://yourapp.com/oauth/x/callback",
            "code_challenge": "generated_pkce_challenge",
            "code_challenge_method": "S256"
        }
    )
    
    return response.json()
```

### LinkedIn Connection

```python
def connect_linkedin_account():
    response = requests.post(
        "https://api.lily-media.ai/api/integrations/connect",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "platform": "linkedin",
            "redirect_uri": "https://yourapp.com/oauth/linkedin/callback",
            "scope": "w_member_social,r_basicprofile"
        }
    )
    
    return response.json()
```

## 🔒 Security Best Practices

### 1. API Key Security

```bash
# ❌ Never expose in client-side code
const API_KEY = "lily_api_key_123"; // DON'T DO THIS

# ✅ Use environment variables
export LILY_API_KEY="lily_api_key_123"
```

```python
# ✅ Load from environment
import os
api_key = os.getenv("LILY_API_KEY")

# ✅ Use secrets management
import boto3
session = boto3.Session()
secrets = session.client('secretsmanager')
api_key = secrets.get_secret_value(SecretId="lily-api-key")["SecretString"]
```

### 2. Token Rotation

```python
class TokenManager:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
    
    def get_valid_token(self):
        if self.access_token and time.time() < self.expires_at:
            return self.access_token
        
        # Token expired, refresh
        new_token = self.refresh_access_token()
        return new_token
    
    def refresh_access_token(self):
        response = requests.post(
            "https://api.lily-media.ai/api/auth/refresh",
            json={"refresh_token": self.refresh_token}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.expires_at = time.time() + data["expires_in"]
            return self.access_token
        
        raise AuthenticationError("Failed to refresh token")
```

### 3. Secure Storage

```python
# ✅ Encrypt sensitive tokens
from cryptography.fernet import Fernet

class SecureTokenStorage:
    def __init__(self, encryption_key):
        self.cipher = Fernet(encryption_key)
    
    def store_token(self, user_id, token):
        encrypted_token = self.cipher.encrypt(token.encode())
        # Store encrypted_token in database
        
    def retrieve_token(self, user_id):
        encrypted_token = get_from_database(user_id)
        return self.cipher.decrypt(encrypted_token).decode()
```

### 4. Request Signing

```python
import hmac
import hashlib
import time

def sign_request(method, path, body, secret):
    timestamp = str(int(time.time()))
    string_to_sign = f"{method}\n{path}\n{body}\n{timestamp}"
    
    signature = hmac.new(
        secret.encode(),
        string_to_sign.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return {
        "X-Timestamp": timestamp,
        "X-Signature": signature
    }

# Usage
headers = sign_request("POST", "/api/posts", json_body, secret_key)
headers["Authorization"] = f"Bearer {api_key}"
```

## ⚠️ Error Handling

### Authentication Errors

| Status Code | Error Code | Description | Action |
|-------------|------------|-------------|---------|
| 401 | `invalid_token` | Token expired/invalid | Refresh token |
| 401 | `token_expired` | Access token expired | Use refresh token |
| 401 | `insufficient_scope` | Missing required scope | Request proper scopes |
| 403 | `rate_limit_exceeded` | Too many requests | Implement backoff |
| 403 | `quota_exceeded` | Usage quota exceeded | Upgrade plan |

### Error Response Format

```json
{
  "error": {
    "code": "invalid_token",
    "message": "The provided access token is invalid or expired",
    "details": {
      "timestamp": "2024-09-07T14:30:00Z",
      "request_id": "req_abc123",
      "documentation_url": "https://docs.lily-media.ai/errors#invalid_token"
    }
  }
}
```

### Retry Logic Example

```python
import time
import random

def api_request_with_retry(url, headers, data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 401:
                # Try to refresh token
                new_token = refresh_access_token()
                headers["Authorization"] = f"Bearer {new_token}"
                continue
                
            elif response.status_code == 429:
                # Rate limited, exponential backoff
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
                continue
                
            else:
                # Other error, don't retry
                raise APIError(response.json())
                
        except requests.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
```

## 📊 Rate Limiting

### Rate Limit Headers

Every API response includes rate limit information:

```http
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4999
X-RateLimit-Reset: 1694096400
X-RateLimit-Retry-After: 60
```

### Handling Rate Limits

```python
def make_api_request(url, headers, data):
    response = requests.post(url, headers=headers, json=data)
    
    # Check rate limit headers
    remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
    
    if remaining < 10:
        # Approaching limit, slow down
        time.sleep(1)
    
    if response.status_code == 429:
        # Rate limited
        retry_after = int(response.headers.get("X-RateLimit-Retry-After", 60))
        print(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after)
        
        # Retry the request
        return make_api_request(url, headers, data)
    
    return response
```

### Rate Limiting by Plan

| Plan | Requests/Hour | Burst Limit | Content Gen/Day | Image Gen/Day |
|------|---------------|-------------|-----------------|---------------|
| Free | 1,000 | 50 | 10 | 5 |
| Basic | 5,000 | 100 | 100 | 50 |
| Pro | 20,000 | 500 | 1,000 | 500 |
| Enterprise | Custom | Custom | Custom | Custom |

## 🔧 Advanced Authentication

### Webhook Signature Verification

```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)

# Usage in Flask
@app.route('/webhooks/lily-media', methods=['POST'])
def handle_webhook():
    signature = request.headers.get('X-Lily-Signature')
    payload = request.get_data(as_text=True)
    
    if not verify_webhook_signature(payload, signature, webhook_secret):
        return jsonify({"error": "Invalid signature"}), 401
    
    # Process webhook
    data = request.get_json()
    process_webhook_event(data)
    
    return jsonify({"status": "success"})
```

### Multi-tenant Authentication

```python
class MultiTenantAuth:
    def __init__(self):
        self.tenant_keys = {}
    
    def authenticate_request(self, api_key, tenant_id=None):
        # Validate API key
        key_info = self.validate_api_key(api_key)
        
        if not key_info:
            raise AuthenticationError("Invalid API key")
        
        # Check tenant access
        if tenant_id and not self.has_tenant_access(key_info, tenant_id):
            raise AuthorizationError("Access denied to tenant")
        
        return key_info
    
    def has_tenant_access(self, key_info, tenant_id):
        allowed_tenants = key_info.get("tenants", [])
        return tenant_id in allowed_tenants or key_info.get("admin", False)
```

## 📚 Quick Reference

### Common Headers

```bash
# Required for all requests
Authorization: Bearer YOUR_API_KEY

# Content type for JSON requests
Content-Type: application/json

# Optional: Request ID for tracking
X-Request-ID: unique-request-id

# Optional: Tenant context
X-Tenant-ID: your-tenant-id
```

### Health Check Endpoint

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://api.lily-media.ai/api/health"
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2024-09-07T14:30:00Z",
  "user": {
    "id": "user_123",
    "plan": "professional",
    "quota_remaining": 850
  }
}
```

---

## 🔗 Next Steps

- **[Getting Started](./getting-started.md)** - Your first API calls
- **[API Reference](./api-reference.md)** - Complete endpoint documentation
- **[Error Handling](./error-handling.md)** - Comprehensive error reference
- **[Webhooks](./webhooks.md)** - Event-driven integrations

## 💡 Need Help?

- **Documentation**: [docs.lily-media.ai](https://docs.lily-media.ai)
- **API Status**: [status.lily-media.ai](https://status.lily-media.ai)
- **Support**: api-support@lily-media.ai
- **Community**: [Discord](https://discord.gg/lily-media-ai)