# Error Handling Guide

Comprehensive guide to handling errors and exceptions in the Lily Media AI API.

## 🚨 Overview

The Lily Media AI API uses conventional HTTP response codes to indicate the success or failure of an API request. In general:
- **2xx** codes indicate success
- **4xx** codes indicate client errors
- **5xx** codes indicate server errors

All error responses follow a consistent JSON format with detailed information to help you debug and handle errors gracefully.

## 📋 Table of Contents

- [Error Response Format](#error-response-format)
- [HTTP Status Codes](#http-status-codes)
- [Error Categories](#error-categories)
- [Authentication Errors](#authentication-errors)
- [Validation Errors](#validation-errors)
- [Rate Limiting Errors](#rate-limiting-errors)
- [Integration Errors](#integration-errors)
- [Server Errors](#server-errors)
- [Retry Strategies](#retry-strategies)
- [Error Monitoring](#error-monitoring)
- [Code Examples](#code-examples)

## 🔧 Error Response Format

All errors return a consistent JSON structure:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Request validation failed",
    "details": {
      "field": "content",
      "issue": "Content exceeds maximum length of 2000 characters",
      "provided_length": 2547,
      "max_length": 2000
    },
    "timestamp": "2024-09-07T14:30:00Z",
    "request_id": "req_abc123def456",
    "documentation_url": "https://docs.lily-media.ai/errors#validation_failed",
    "support_reference": "ERR-2024-0907-001"
  }
}
```

### Error Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Machine-readable error code |
| `message` | string | Human-readable error message |
| `details` | object | Additional context and debugging information |
| `timestamp` | string | ISO 8601 timestamp when error occurred |
| `request_id` | string | Unique identifier for the request |
| `documentation_url` | string | Link to relevant documentation |
| `support_reference` | string | Reference code for support inquiries |

## 📊 HTTP Status Codes

### 2xx Success Codes

| Code | Name | Description |
|------|------|-------------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 202 | Accepted | Request accepted for processing |
| 204 | No Content | Request succeeded, no content returned |

### 4xx Client Error Codes

| Code | Name | Common Causes |
|------|------|---------------|
| 400 | Bad Request | Invalid JSON, missing required fields |
| 401 | Unauthorized | Invalid/expired API key or token |
| 403 | Forbidden | Insufficient permissions, quota exceeded |
| 404 | Not Found | Resource doesn't exist |
| 405 | Method Not Allowed | HTTP method not supported |
| 409 | Conflict | Resource conflict, duplicate creation |
| 422 | Unprocessable Entity | Validation errors |
| 429 | Too Many Requests | Rate limit exceeded |

### 5xx Server Error Codes

| Code | Name | Description |
|------|------|-------------|
| 500 | Internal Server Error | Unexpected server error |
| 502 | Bad Gateway | Upstream service error |
| 503 | Service Unavailable | Service temporarily unavailable |
| 504 | Gateway Timeout | Request timeout |

## 🏷️ Error Categories

### Authentication & Authorization Errors

```json
{
  "error": {
    "code": "invalid_api_key",
    "message": "The provided API key is invalid or has been revoked",
    "details": {
      "api_key_prefix": "lily_***_456",
      "revoked_at": "2024-09-06T10:15:00Z",
      "reason": "User requested revocation"
    }
  }
}
```

**Common Authentication Error Codes:**
- `invalid_api_key` - API key is invalid or revoked
- `token_expired` - JWT token has expired
- `insufficient_scope` - Token lacks required permissions
- `account_suspended` - User account is suspended

### Validation Errors

```json
{
  "error": {
    "code": "validation_failed",
    "message": "One or more fields failed validation",
    "details": {
      "errors": [
        {
          "field": "content",
          "code": "length_exceeded",
          "message": "Content exceeds maximum length",
          "max_length": 2000,
          "actual_length": 2547
        },
        {
          "field": "platforms",
          "code": "invalid_platform",
          "message": "Unsupported platform specified",
          "invalid_platforms": ["myspace", "friendster"],
          "supported_platforms": ["instagram", "twitter", "linkedin", "facebook"]
        }
      ]
    }
  }
}
```

### Rate Limiting Errors

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "API rate limit exceeded",
    "details": {
      "limit": 5000,
      "remaining": 0,
      "reset_time": 1694096400,
      "retry_after": 3600,
      "plan": "basic",
      "upgrade_url": "https://lily-media.ai/upgrade"
    }
  }
}
```

### Quota Errors

```json
{
  "error": {
    "code": "quota_exceeded",
    "message": "Monthly content generation quota exceeded",
    "details": {
      "quota_type": "content_generations",
      "limit": 100,
      "used": 100,
      "reset_date": "2024-10-01T00:00:00Z",
      "plan": "basic",
      "upgrade_url": "https://lily-media.ai/upgrade"
    }
  }
}
```

## 🔐 Authentication Errors

### Invalid API Key

```bash
curl -H "Authorization: Bearer invalid_key" \
     "https://api.lily-media.ai/api/auth/me"
```

Response (401):
```json
{
  "error": {
    "code": "invalid_api_key",
    "message": "The provided API key is invalid",
    "details": {
      "api_key_format": "Expected format: lily_live_* or lily_test_*",
      "provided_format": "invalid_key"
    },
    "documentation_url": "https://docs.lily-media.ai/authentication#api-keys"
  }
}
```

### Expired Token

Response (401):
```json
{
  "error": {
    "code": "token_expired",
    "message": "JWT token has expired",
    "details": {
      "expired_at": "2024-09-07T13:30:00Z",
      "current_time": "2024-09-07T14:30:00Z",
      "refresh_token_available": true
    },
    "documentation_url": "https://docs.lily-media.ai/authentication#token-refresh"
  }
}
```

### Insufficient Permissions

Response (403):
```json
{
  "error": {
    "code": "insufficient_scope",
    "message": "Token lacks required permissions for this operation",
    "details": {
      "required_scopes": ["content:write", "images:generate"],
      "provided_scopes": ["content:read"],
      "missing_scopes": ["content:write", "images:generate"]
    },
    "documentation_url": "https://docs.lily-media.ai/authentication#scopes"
  }
}
```

## ✅ Validation Errors

### Content Validation

Request:
```bash
curl -X POST "https://api.lily-media.ai/api/content/generate" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "prompt": "",
    "platform": "invalid_platform",
    "length": "super_long"
  }'
```

Response (422):
```json
{
  "error": {
    "code": "validation_failed",
    "message": "Request validation failed",
    "details": {
      "errors": [
        {
          "field": "prompt",
          "code": "required",
          "message": "Prompt is required and cannot be empty"
        },
        {
          "field": "platform",
          "code": "invalid_choice",
          "message": "Platform must be one of: instagram, twitter, linkedin, facebook",
          "provided": "invalid_platform"
        },
        {
          "field": "length",
          "code": "invalid_choice",
          "message": "Length must be one of: short, medium, long",
          "provided": "super_long"
        }
      ]
    }
  }
}
```

### Image Generation Validation

Response (422):
```json
{
  "error": {
    "code": "validation_failed",
    "message": "Image generation request validation failed",
    "details": {
      "errors": [
        {
          "field": "prompt",
          "code": "content_policy_violation",
          "message": "Prompt violates content policy",
          "violation_type": "inappropriate_content",
          "policy_url": "https://docs.lily-media.ai/content-policy"
        },
        {
          "field": "dimensions",
          "code": "invalid_dimensions",
          "message": "Dimensions must be between 256x256 and 2048x2048",
          "provided": "4096x4096",
          "max_dimensions": "2048x2048"
        }
      ]
    }
  }
}
```

## 🚫 Rate Limiting Errors

### Request Rate Limit

Response (429):
```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Request rate limit exceeded",
    "details": {
      "limit_type": "requests_per_hour",
      "limit": 5000,
      "remaining": 0,
      "reset_time": 1694096400,
      "retry_after": 300,
      "plan": "basic"
    }
  }
}
```

Headers:
```http
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1694096400
Retry-After: 300
```

### Burst Limit

Response (429):
```json
{
  "error": {
    "code": "burst_limit_exceeded",
    "message": "Too many requests in short time period",
    "details": {
      "burst_limit": 100,
      "window_seconds": 60,
      "requests_in_window": 150,
      "retry_after": 45
    }
  }
}
```

## 🔗 Integration Errors

### Social Platform Connection Errors

```json
{
  "error": {
    "code": "platform_connection_failed",
    "message": "Failed to connect to Instagram account",
    "details": {
      "platform": "instagram",
      "oauth_error": "access_denied",
      "platform_message": "User denied authorization",
      "retry_url": "https://api.lily-media.ai/api/integrations/connect?platform=instagram"
    }
  }
}
```

### Publishing Errors

```json
{
  "error": {
    "code": "publishing_failed",
    "message": "Failed to publish post to Instagram",
    "details": {
      "platform": "instagram",
      "platform_error": "media_type_not_supported",
      "platform_message": "Video format not supported for carousel posts",
      "supported_formats": ["jpg", "png", "gif"],
      "provided_format": "mp4"
    }
  }
}
```

### Connection Health Errors

```json
{
  "error": {
    "code": "connection_unhealthy",
    "message": "Social platform connection is not healthy",
    "details": {
      "platform": "twitter",
      "connection_id": "conn_abc123",
      "health_status": "degraded",
      "last_successful_request": "2024-09-06T10:30:00Z",
      "error_count_24h": 15,
      "suggested_action": "reconnect"
    }
  }
}
```

## 🔥 Server Errors

### Internal Server Error

Response (500):
```json
{
  "error": {
    "code": "internal_server_error",
    "message": "An unexpected error occurred",
    "details": {
      "incident_id": "inc_def456ghi789",
      "timestamp": "2024-09-07T14:30:00Z",
      "service": "content-generation",
      "status_page": "https://status.lily-media.ai"
    },
    "documentation_url": "https://docs.lily-media.ai/errors#internal_server_error",
    "support_reference": "ERR-2024-0907-002"
  }
}
```

### Service Unavailable

Response (503):
```json
{
  "error": {
    "code": "service_unavailable",
    "message": "Content generation service is temporarily unavailable",
    "details": {
      "service": "ai-content-generation",
      "estimated_recovery": "2024-09-07T15:00:00Z",
      "status_page": "https://status.lily-media.ai",
      "alternative_endpoints": ["/api/content/templates"]
    }
  }
}
```

## 🔄 Retry Strategies

### Exponential Backoff Implementation

```python
import time
import random
import requests
from typing import Optional, Dict, Any

class APIClient:
    def __init__(self, api_key: str, base_url: str = "https://api.lily-media.ai/api"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def request_with_retry(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        backoff_factor: float = 1.0
    ):
        """Make API request with exponential backoff retry logic."""
        
        for attempt in range(max_retries + 1):
            try:
                response = self.session.request(
                    method, 
                    f"{self.base_url}/{endpoint.lstrip('/')}", 
                    json=data
                )
                
                # Success
                if 200 <= response.status_code < 300:
                    return response.json()
                
                # Client errors (4xx) - don't retry most
                if 400 <= response.status_code < 500:
                    error_data = response.json()
                    error_code = error_data.get("error", {}).get("code", "")
                    
                    # Retry on rate limiting and some auth errors
                    if error_code in ["rate_limit_exceeded", "token_expired"]:
                        if attempt < max_retries:
                            wait_time = self._calculate_wait_time(
                                response, attempt, backoff_factor
                            )
                            print(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}")
                            time.sleep(wait_time)
                            
                            # Try to refresh token if expired
                            if error_code == "token_expired":
                                self._refresh_token()
                            
                            continue
                    
                    # Don't retry other 4xx errors
                    raise APIError(response.status_code, error_data)
                
                # Server errors (5xx) - retry with backoff
                if 500 <= response.status_code < 600:
                    if attempt < max_retries:
                        wait_time = backoff_factor * (2 ** attempt) + random.uniform(0, 1)
                        print(f"Server error {response.status_code}. Retrying in {wait_time:.1f}s")
                        time.sleep(wait_time)
                        continue
                    
                    # Max retries reached
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    raise APIError(response.status_code, error_data)
                    
            except requests.RequestException as e:
                if attempt < max_retries:
                    wait_time = backoff_factor * (2 ** attempt)
                    print(f"Request failed: {e}. Retrying in {wait_time:.1f}s")
                    time.sleep(wait_time)
                    continue
                
                raise NetworkError(f"Request failed after {max_retries} retries: {e}")
        
        raise APIError(500, {"error": {"code": "max_retries_exceeded"}})
    
    def _calculate_wait_time(self, response, attempt, backoff_factor):
        """Calculate wait time based on response headers and attempt number."""
        
        # Check for Retry-After header
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                pass
        
        # Check for rate limit reset
        rate_limit_reset = response.headers.get('X-RateLimit-Reset')
        if rate_limit_reset:
            try:
                reset_time = int(rate_limit_reset)
                current_time = int(time.time())
                wait_time = max(0, reset_time - current_time)
                if wait_time > 0 and wait_time < 3600:  # Max 1 hour wait
                    return wait_time
            except ValueError:
                pass
        
        # Default exponential backoff
        return backoff_factor * (2 ** attempt) + random.uniform(0, 1)
    
    def _refresh_token(self):
        """Refresh the authentication token if possible."""
        # Implementation depends on your auth flow
        # This is a placeholder
        pass

class APIError(Exception):
    def __init__(self, status_code: int, error_data: Dict[str, Any]):
        self.status_code = status_code
        self.error_data = error_data
        self.error_code = error_data.get("error", {}).get("code", "unknown")
        self.message = error_data.get("error", {}).get("message", "Unknown error")
        super().__init__(f"{status_code}: {self.message}")

class NetworkError(Exception):
    pass
```

### Usage Example

```python
# Initialize client
client = APIClient("your_api_key")

try:
    # Make request with automatic retry
    result = client.request_with_retry(
        "POST", 
        "/content/generate",
        data={
            "prompt": "Create a motivational Monday post",
            "platform": "instagram",
            "tone": "professional"
        },
        max_retries=5,
        backoff_factor=2.0
    )
    
    print("Content generated successfully:", result)
    
except APIError as e:
    print(f"API Error {e.status_code}: {e.message}")
    print(f"Error code: {e.error_code}")
    
    # Handle specific error types
    if e.error_code == "quota_exceeded":
        print("Consider upgrading your plan")
    elif e.error_code == "validation_failed":
        print("Fix validation errors:", e.error_data.get("error", {}).get("details"))
        
except NetworkError as e:
    print(f"Network error: {e}")
```

## 🔍 Error Monitoring

### Logging Errors

```python
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_api_error(error: APIError, context: Dict[str, Any]):
    """Log API errors with structured data."""
    
    log_data = {
        "timestamp": time.time(),
        "status_code": error.status_code,
        "error_code": error.error_code,
        "message": error.message,
        "request_id": error.error_data.get("error", {}).get("request_id"),
        "context": context
    }
    
    if error.status_code >= 500:
        logger.error("API Server Error", extra=log_data)
    elif error.status_code >= 400:
        logger.warning("API Client Error", extra=log_data)
    else:
        logger.info("API Response", extra=log_data)

# Usage
try:
    result = client.request_with_retry("POST", "/posts", data=post_data)
except APIError as e:
    log_api_error(e, {
        "endpoint": "/posts",
        "method": "POST",
        "user_id": "user_123",
        "post_data_length": len(json.dumps(post_data))
    })
    raise
```

### Error Metrics

```python
from collections import defaultdict, Counter
import time

class ErrorTracker:
    def __init__(self):
        self.error_counts = Counter()
        self.error_times = defaultdict(list)
        self.start_time = time.time()
    
    def record_error(self, error_code: str, endpoint: str):
        """Record an error occurrence."""
        key = f"{endpoint}:{error_code}"
        self.error_counts[key] += 1
        self.error_times[key].append(time.time())
    
    def get_error_rate(self, error_code: str, endpoint: str, window_seconds: int = 3600):
        """Get error rate for specific error and endpoint."""
        key = f"{endpoint}:{error_code}"
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        recent_errors = [
            t for t in self.error_times[key] 
            if t >= cutoff_time
        ]
        
        return len(recent_errors) / (window_seconds / 3600)  # Errors per hour
    
    def should_circuit_break(self, endpoint: str, error_threshold: int = 10):
        """Determine if circuit breaker should trigger."""
        endpoint_errors = sum(
            count for key, count in self.error_counts.items()
            if key.startswith(f"{endpoint}:")
        )
        
        return endpoint_errors >= error_threshold

# Global error tracker
error_tracker = ErrorTracker()

# Integration with API client
def make_monitored_request(client, method, endpoint, data=None):
    try:
        return client.request_with_retry(method, endpoint, data)
    except APIError as e:
        error_tracker.record_error(e.error_code, endpoint)
        
        # Check if we should stop making requests to this endpoint
        if error_tracker.should_circuit_break(endpoint):
            logger.warning(f"Circuit breaker activated for {endpoint}")
            raise CircuitBreakerError(f"Too many errors for {endpoint}")
        
        raise

class CircuitBreakerError(Exception):
    pass
```

## 📊 Error Analytics

### Error Dashboard Data

```python
def generate_error_report(start_time: float, end_time: float):
    """Generate error analytics report."""
    
    report = {
        "time_range": {
            "start": start_time,
            "end": end_time,
            "duration_hours": (end_time - start_time) / 3600
        },
        "error_summary": {
            "total_errors": sum(error_tracker.error_counts.values()),
            "unique_error_types": len(set(
                key.split(":")[1] for key in error_tracker.error_counts.keys()
            )),
            "affected_endpoints": len(set(
                key.split(":")[0] for key in error_tracker.error_counts.keys()
            ))
        },
        "top_errors": error_tracker.error_counts.most_common(10),
        "error_rates": {},
        "recommendations": []
    }
    
    # Calculate error rates
    for key, count in error_tracker.error_counts.items():
        endpoint, error_code = key.split(":", 1)
        rate = error_tracker.get_error_rate(error_code, endpoint)
        report["error_rates"][key] = rate
    
    # Generate recommendations
    if "rate_limit_exceeded" in str(report["top_errors"]):
        report["recommendations"].append("Consider implementing more aggressive rate limiting in your application")
    
    if "validation_failed" in str(report["top_errors"]):
        report["recommendations"].append("Review input validation on client side")
    
    return report
```

## 🎯 Best Practices

### 1. Graceful Error Handling

```python
def handle_api_response(response_data, operation_name="API operation"):
    """Handle API response with graceful error handling."""
    
    try:
        if "error" in response_data:
            error = response_data["error"]
            error_code = error.get("code", "unknown")
            
            # Handle different error types gracefully
            if error_code == "quota_exceeded":
                return {
                    "success": False,
                    "error": "quota_exceeded",
                    "message": "You've reached your usage limit. Please upgrade your plan.",
                    "user_action": "upgrade_plan"
                }
            
            elif error_code == "validation_failed":
                return {
                    "success": False,
                    "error": "validation_error",
                    "message": "Please check your input and try again.",
                    "details": error.get("details", {}),
                    "user_action": "fix_input"
                }
            
            elif error_code == "rate_limit_exceeded":
                retry_after = error.get("details", {}).get("retry_after", 60)
                return {
                    "success": False,
                    "error": "rate_limited",
                    "message": f"Too many requests. Please wait {retry_after} seconds.",
                    "retry_after": retry_after,
                    "user_action": "wait_and_retry"
                }
            
            else:
                return {
                    "success": False,
                    "error": "api_error",
                    "message": f"{operation_name} failed: {error.get('message', 'Unknown error')}",
                    "user_action": "contact_support"
                }
        
        # Success case
        return {
            "success": True,
            "data": response_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "processing_error",
            "message": f"Error processing {operation_name} response: {str(e)}",
            "user_action": "contact_support"
        }
```

### 2. User-Friendly Error Messages

```python
ERROR_MESSAGES = {
    "invalid_api_key": "Your API key appears to be invalid. Please check your key in the dashboard.",
    "quota_exceeded": "You've reached your usage limit for this month. Consider upgrading your plan.",
    "rate_limit_exceeded": "You're making requests too quickly. Please slow down and try again.",
    "validation_failed": "There's an issue with your request format. Please check the required fields.",
    "service_unavailable": "Our service is temporarily unavailable. Please try again in a few minutes.",
    "connection_unhealthy": "There's an issue with your social media connection. Please reconnect your account.",
    "publishing_failed": "We couldn't publish your post. Please check your content and try again."
}

def get_user_friendly_message(error_code: str, default_message: str = None):
    """Get user-friendly error message."""
    return ERROR_MESSAGES.get(error_code, default_message or "Something went wrong. Please try again.")
```

### 3. Error Recovery

```python
class RecoveryStrategies:
    @staticmethod
    def handle_token_expired(api_client):
        """Recover from expired token."""
        try:
            new_token = api_client.refresh_token()
            api_client.update_token(new_token)
            return True
        except Exception:
            return False
    
    @staticmethod
    def handle_connection_unhealthy(platform: str, connection_id: str):
        """Recover from unhealthy connection."""
        # Trigger reconnection flow
        reconnect_url = f"https://api.lily-media.ai/api/integrations/reconnect/{connection_id}"
        return {"action": "reconnect", "url": reconnect_url}
    
    @staticmethod
    def handle_quota_exceeded(error_details):
        """Handle quota exceeded."""
        return {
            "action": "upgrade_or_wait",
            "reset_date": error_details.get("reset_date"),
            "upgrade_url": error_details.get("upgrade_url")
        }
```

---

## 🔗 Related Documentation

- **[Authentication Guide](./authentication.md)** - Complete authentication setup
- **[API Reference](./api-reference.md)** - All endpoint documentation
- **[Rate Limits](./rate-limits.md)** - Rate limiting details
- **[Getting Started](./getting-started.md)** - Quick start guide

## 💡 Need Help?

- **Documentation**: [docs.lily-media.ai](https://docs.lily-media.ai)
- **API Status**: [status.lily-media.ai](https://status.lily-media.ai)
- **Support**: api-support@lily-media.ai
- **Community**: [Discord](https://discord.gg/lily-media-ai)

When contacting support, please include:
- The `request_id` from the error response
- The `support_reference` code if available
- Your API key prefix (first and last 4 characters only)
- The exact request you were making when the error occurred