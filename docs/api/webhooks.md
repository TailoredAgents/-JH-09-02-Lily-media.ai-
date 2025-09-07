# Webhooks Guide

Complete guide to using webhooks for real-time event notifications from the Lily Media AI platform.

## 🔗 Overview

Webhooks allow your application to receive real-time notifications when events occur in your Lily Media AI account. Instead of polling our API for changes, we'll send HTTP POST requests to your specified endpoints when relevant events happen.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Webhook Events](#webhook-events)
- [Webhook Payload](#webhook-payload)
- [Signature Verification](#signature-verification)
- [Endpoint Requirements](#endpoint-requirements)
- [Error Handling & Retries](#error-handling--retries)
- [Testing Webhooks](#testing-webhooks)
- [Best Practices](#best-practices)
- [Code Examples](#code-examples)

## 🚀 Getting Started

### Step 1: Configure Webhook Endpoint

```bash
curl -X POST "https://api.lily-media.ai/api/webhooks" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/webhooks/lily-media",
    "events": [
      "post.published",
      "post.failed",
      "content.generated",
      "connection.health_changed"
    ],
    "secret": "your_webhook_secret"
  }'
```

Response:
```json
{
  "id": "webhook_abc123",
  "url": "https://your-app.com/webhooks/lily-media",
  "events": [
    "post.published",
    "post.failed", 
    "content.generated",
    "connection.health_changed"
  ],
  "secret": "wh_secret_***_def456",
  "created_at": "2024-09-07T14:30:00Z",
  "status": "active"
}
```

### Step 2: Implement Webhook Handler

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)
WEBHOOK_SECRET = "your_webhook_secret"

@app.route('/webhooks/lily-media', methods=['POST'])
def handle_webhook():
    # Verify signature
    signature = request.headers.get('X-Lily-Signature')
    if not verify_signature(request.get_data(), signature, WEBHOOK_SECRET):
        return jsonify({"error": "Invalid signature"}), 401
    
    # Process event
    event_data = request.get_json()
    event_type = event_data.get('type')
    
    if event_type == 'post.published':
        handle_post_published(event_data)
    elif event_type == 'post.failed':
        handle_post_failed(event_data)
    elif event_type == 'content.generated':
        handle_content_generated(event_data)
    
    return jsonify({"status": "success"}), 200

def verify_signature(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)
```

### Step 3: Test Your Webhook

```bash
curl -X POST "https://api.lily-media.ai/api/webhooks/webhook_abc123/test" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## 📡 Webhook Events

### Post Events

#### `post.published`
Triggered when a post is successfully published to a social platform.

```json
{
  "id": "evt_abc123",
  "type": "post.published",
  "created_at": "2024-09-07T14:30:00Z",
  "data": {
    "post_id": "post_def456",
    "platform": "instagram",
    "platform_post_id": "18234567890123456",
    "published_at": "2024-09-07T14:30:00Z",
    "engagement": {
      "likes": 0,
      "comments": 0,
      "shares": 0
    },
    "post_url": "https://instagram.com/p/ABC123DEF456"
  },
  "organization_id": "org_789xyz"
}
```

#### `post.failed`
Triggered when a post publication fails.

```json
{
  "id": "evt_def456",
  "type": "post.failed",
  "created_at": "2024-09-07T14:30:00Z",
  "data": {
    "post_id": "post_ghi789",
    "platform": "twitter",
    "error_code": "media_upload_failed",
    "error_message": "Image file too large",
    "retry_count": 3,
    "will_retry": false,
    "next_retry_at": null
  },
  "organization_id": "org_789xyz"
}
```

#### `post.scheduled`
Triggered when a post is scheduled for future publishing.

```json
{
  "id": "evt_ghi789",
  "type": "post.scheduled",
  "created_at": "2024-09-07T14:30:00Z",
  "data": {
    "post_id": "post_jkl012",
    "platforms": ["instagram", "twitter"],
    "scheduled_for": "2024-09-08T09:00:00Z",
    "content_preview": "Monday Motivation: Start your week with...",
    "media_count": 1
  },
  "organization_id": "org_789xyz"
}
```

### Content Generation Events

#### `content.generated`
Triggered when AI content generation completes.

```json
{
  "id": "evt_jkl012",
  "type": "content.generated",
  "created_at": "2024-09-07T14:30:00Z",
  "data": {
    "generation_id": "gen_mno345",
    "prompt": "Create a motivational Monday post",
    "platform": "instagram",
    "content": "Monday Motivation 💪\n\nStart your week with intention!...",
    "metadata": {
      "character_count": 187,
      "hashtag_count": 3,
      "emoji_count": 2,
      "tone": "professional",
      "estimated_engagement": 125
    }
  },
  "organization_id": "org_789xyz"
}
```

#### `content.generation_failed`
Triggered when content generation fails.

```json
{
  "id": "evt_mno345",
  "type": "content.generation_failed",
  "created_at": "2024-09-07T14:30:00Z",
  "data": {
    "generation_id": "gen_pqr678",
    "prompt": "Create inappropriate content...",
    "error_code": "content_policy_violation",
    "error_message": "Content violates usage policy",
    "policy_violation_type": "inappropriate_content"
  },
  "organization_id": "org_789xyz"
}
```

### Image Generation Events

#### `image.generated`
Triggered when AI image generation completes.

```json
{
  "id": "evt_pqr678",
  "type": "image.generated",
  "created_at": "2024-09-07T14:30:00Z",
  "data": {
    "generation_id": "img_stu901",
    "prompt": "Professional workspace with laptop and coffee",
    "image_url": "https://cdn.lily-media.ai/images/stu901.jpg",
    "alt_text": "Modern workspace with open laptop and coffee cup",
    "dimensions": {
      "width": 1024,
      "height": 1024
    },
    "style": "professional",
    "generation_time_ms": 3500
  },
  "organization_id": "org_789xyz"
}
```

### Connection Events

#### `connection.health_changed`
Triggered when a social platform connection's health status changes.

```json
{
  "id": "evt_stu901",
  "type": "connection.health_changed",
  "created_at": "2024-09-07T14:30:00Z",
  "data": {
    "connection_id": "conn_vwx234",
    "platform": "instagram",
    "previous_status": "healthy",
    "current_status": "degraded",
    "error_count": 5,
    "last_error": "rate_limit_exceeded",
    "last_successful_request": "2024-09-07T12:15:00Z",
    "suggested_action": "wait_and_retry"
  },
  "organization_id": "org_789xyz"
}
```

#### `connection.disconnected`
Triggered when a social platform connection is revoked or expires.

```json
{
  "id": "evt_vwx234",
  "type": "connection.disconnected",
  "created_at": "2024-09-07T14:30:00Z",
  "data": {
    "connection_id": "conn_yza567",
    "platform": "twitter", 
    "reason": "token_revoked",
    "disconnected_at": "2024-09-07T14:30:00Z",
    "reconnect_url": "https://api.lily-media.ai/api/integrations/connect?platform=twitter"
  },
  "organization_id": "org_789xyz"
}
```

### Analytics Events

#### `analytics.report_ready`
Triggered when scheduled analytics reports are ready.

```json
{
  "id": "evt_yza567",
  "type": "analytics.report_ready",
  "created_at": "2024-09-07T14:30:00Z",
  "data": {
    "report_id": "rpt_bcd890",
    "report_type": "monthly_summary",
    "period": {
      "start": "2024-08-01T00:00:00Z",
      "end": "2024-08-31T23:59:59Z"
    },
    "download_url": "https://api.lily-media.ai/api/analytics/reports/rpt_bcd890/download",
    "expires_at": "2024-09-14T14:30:00Z"
  },
  "organization_id": "org_789xyz"
}
```

### Account Events

#### `account.quota_warning`
Triggered when account approaches usage quotas.

```json
{
  "id": "evt_bcd890",
  "type": "account.quota_warning",
  "created_at": "2024-09-07T14:30:00Z",
  "data": {
    "quota_type": "content_generations",
    "limit": 1000,
    "used": 850,
    "remaining": 150,
    "percentage_used": 85,
    "reset_date": "2024-10-01T00:00:00Z",
    "upgrade_url": "https://lily-media.ai/upgrade"
  },
  "organization_id": "org_789xyz"
}
```

## 📦 Webhook Payload

### Standard Payload Structure

All webhooks follow this structure:

```json
{
  "id": "evt_unique_id",
  "type": "event.type",
  "created_at": "2024-09-07T14:30:00Z",
  "data": {
    // Event-specific data
  },
  "organization_id": "org_id",
  "api_version": "2024-09-01",
  "environment": "live"
}
```

### Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique event identifier |
| `type` | string | Event type (see events above) |
| `created_at` | string | ISO 8601 timestamp when event occurred |
| `data` | object | Event-specific payload data |
| `organization_id` | string | Your organization ID |
| `api_version` | string | API version when event was created |
| `environment` | string | Environment: `live` or `test` |

## 🔐 Signature Verification

### How Signatures Work

Lily Media AI signs webhook payloads using HMAC-SHA256 with your webhook secret. The signature is sent in the `X-Lily-Signature` header as `sha256={signature}`.

### Verification Implementation

#### Python (Flask/Django)

```python
import hmac
import hashlib
import time

def verify_webhook_signature(payload, signature_header, secret):
    """Verify webhook signature."""
    if not signature_header:
        return False
    
    try:
        # Extract signature from header
        signature = signature_header.split('=')[1]
    except (IndexError, ValueError):
        return False
    
    # Calculate expected signature
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Use constant-time comparison
    return hmac.compare_digest(expected_signature, signature)

# Usage
@app.route('/webhooks/lily-media', methods=['POST'])
def webhook_handler():
    payload = request.get_data()
    signature = request.headers.get('X-Lily-Signature')
    
    if not verify_webhook_signature(payload, signature, WEBHOOK_SECRET):
        abort(401)
    
    # Process webhook
    event_data = request.get_json()
    process_webhook_event(event_data)
    
    return '', 200
```

#### Node.js (Express)

```javascript
const crypto = require('crypto');
const express = require('express');

const app = express();
app.use(express.raw({type: 'application/json'}));

function verifyWebhookSignature(payload, signature, secret) {
    if (!signature) return false;
    
    const expectedSignature = crypto
        .createHmac('sha256', secret)
        .update(payload)
        .digest('hex');
    
    const providedSignature = signature.split('=')[1];
    
    return crypto.timingSafeEqual(
        Buffer.from(expectedSignature, 'hex'),
        Buffer.from(providedSignature, 'hex')
    );
}

app.post('/webhooks/lily-media', (req, res) => {
    const signature = req.get('X-Lily-Signature');
    
    if (!verifyWebhookSignature(req.body, signature, process.env.WEBHOOK_SECRET)) {
        return res.status(401).send('Invalid signature');
    }
    
    const eventData = JSON.parse(req.body);
    processWebhookEvent(eventData);
    
    res.status(200).send('OK');
});
```

#### Ruby (Rails)

```ruby
require 'openssl'

class WebhooksController < ApplicationController
  skip_before_action :verify_authenticity_token
  
  def lily_media
    payload = request.raw_post
    signature = request.headers['X-Lily-Signature']
    
    unless verify_signature(payload, signature)
      head :unauthorized
      return
    end
    
    event_data = JSON.parse(payload)
    process_webhook_event(event_data)
    
    head :ok
  end
  
  private
  
  def verify_signature(payload, signature_header)
    return false unless signature_header
    
    signature = signature_header.split('=')[1]
    expected_signature = OpenSSL::HMAC.hexdigest(
      'sha256', 
      ENV['WEBHOOK_SECRET'], 
      payload
    )
    
    Rack::Utils.secure_compare(expected_signature, signature)
  end
end
```

## 🔧 Endpoint Requirements

### Required Response

Your webhook endpoint must:
- Return HTTP 200 status code for successful processing
- Respond within 30 seconds
- Accept POST requests with `application/json` content type

### Headers Sent

Every webhook request includes these headers:

```http
Content-Type: application/json
User-Agent: Lily-Media-Webhooks/2.0
X-Lily-Signature: sha256=abc123def456...
X-Lily-Event-Type: post.published
X-Lily-Event-ID: evt_abc123
X-Lily-Delivery-ID: delivery_def456
X-Lily-Timestamp: 1694096400
```

### Response Handling

```python
@app.route('/webhooks/lily-media', methods=['POST'])
def webhook_handler():
    try:
        # Verify signature (shown above)
        # Process event
        event_data = request.get_json()
        result = process_webhook_event(event_data)
        
        # Return success
        return jsonify({"status": "success", "processed": True}), 200
        
    except ValueError as e:
        # Invalid JSON
        return jsonify({"error": "Invalid JSON"}), 400
        
    except Exception as e:
        # Log error
        logger.error(f"Webhook processing failed: {e}")
        
        # Return 5xx to trigger retry
        return jsonify({"error": "Processing failed"}), 500
```

## 🔄 Error Handling & Retries

### Retry Policy

If your endpoint returns a non-2xx status code or times out, we'll retry the webhook with exponential backoff:

- **Attempt 1**: Immediate
- **Attempt 2**: 30 seconds later
- **Attempt 3**: 5 minutes later
- **Attempt 4**: 30 minutes later
- **Attempt 5**: 2 hours later
- **Attempt 6**: 6 hours later (final attempt)

### Retry Headers

Retry attempts include additional headers:

```http
X-Lily-Retry-Count: 3
X-Lily-Max-Retries: 6
X-Lily-First-Attempt: 2024-09-07T14:30:00Z
```

### Handling Failures

```python
def process_webhook_event(event_data):
    """Process webhook event with error handling."""
    
    event_type = event_data.get('type')
    event_id = event_data.get('id')
    
    try:
        # Check for duplicate events
        if is_duplicate_event(event_id):
            logger.info(f"Duplicate event ignored: {event_id}")
            return {"status": "duplicate"}
        
        # Mark event as processing
        mark_event_processing(event_id)
        
        # Route to specific handlers
        if event_type == 'post.published':
            result = handle_post_published(event_data['data'])
        elif event_type == 'post.failed':
            result = handle_post_failed(event_data['data'])
        else:
            logger.warning(f"Unknown event type: {event_type}")
            return {"status": "ignored"}
        
        # Mark event as processed
        mark_event_completed(event_id, result)
        return result
        
    except Exception as e:
        # Mark event as failed
        mark_event_failed(event_id, str(e))
        raise  # Re-raise to return 5xx and trigger retry

def is_duplicate_event(event_id):
    """Check if event was already processed."""
    # Implement your deduplication logic
    return False  # Placeholder

def mark_event_processing(event_id):
    """Mark event as currently processing."""
    # Store in database/cache
    pass

def mark_event_completed(event_id, result):
    """Mark event as successfully processed."""
    # Store completion status
    pass

def mark_event_failed(event_id, error):
    """Mark event as failed with error details."""
    # Store failure details
    pass
```

## 🧪 Testing Webhooks

### Local Testing with ngrok

```bash
# Install ngrok
npm install -g ngrok

# Start your local server
python app.py &

# Expose local server
ngrok http 5000
```

Use the ngrok URL for webhook configuration:
```bash
curl -X POST "https://api.lily-media.ai/api/webhooks" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "url": "https://abc123.ngrok.io/webhooks/lily-media",
    "events": ["post.published"]
  }'
```

### Test Event Endpoint

Send test events to verify your webhook:

```bash
curl -X POST "https://api.lily-media.ai/api/webhooks/webhook_abc123/test" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "event_type": "post.published"
  }'
```

### Webhook Logs

View webhook delivery logs:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://api.lily-media.ai/api/webhooks/webhook_abc123/deliveries"
```

Response:
```json
{
  "deliveries": [
    {
      "id": "delivery_def456",
      "event_id": "evt_abc123",
      "event_type": "post.published",
      "attempted_at": "2024-09-07T14:30:00Z",
      "response_status": 200,
      "response_time_ms": 150,
      "success": true,
      "retry_count": 0
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 1
  }
}
```

## 💡 Best Practices

### 1. Idempotency

Handle duplicate events gracefully:

```python
import redis
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def is_event_processed(event_id):
    """Check if event was already processed."""
    return redis_client.exists(f"processed:{event_id}")

def mark_event_processed(event_id):
    """Mark event as processed with TTL."""
    redis_client.setex(
        f"processed:{event_id}", 
        timedelta(days=7),  # Keep for 7 days
        "processed"
    )

@app.route('/webhooks/lily-media', methods=['POST'])
def webhook_handler():
    event_data = request.get_json()
    event_id = event_data.get('id')
    
    # Check for duplicate
    if is_event_processed(event_id):
        return jsonify({"status": "already_processed"}), 200
    
    # Process event
    try:
        result = process_webhook_event(event_data)
        mark_event_processed(event_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Failed to process event {event_id}: {e}")
        return jsonify({"error": str(e)}), 500
```

### 2. Asynchronous Processing

Process webhooks asynchronously for better performance:

```python
from celery import Celery
from flask import Flask, request, jsonify

app = Flask(__name__)
celery = Celery('webhook_processor')

@celery.task(bind=True, max_retries=3)
def process_webhook_async(self, event_data):
    """Process webhook asynchronously."""
    try:
        return process_webhook_event(event_data)
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@app.route('/webhooks/lily-media', methods=['POST'])
def webhook_handler():
    # Verify signature
    if not verify_signature(request.get_data(), request.headers.get('X-Lily-Signature')):
        return jsonify({"error": "Invalid signature"}), 401
    
    # Queue for async processing
    event_data = request.get_json()
    process_webhook_async.delay(event_data)
    
    # Return immediately
    return jsonify({"status": "queued"}), 200
```

### 3. Monitoring and Alerting

Monitor webhook health:

```python
import time
from collections import defaultdict

webhook_metrics = defaultdict(int)

def track_webhook_metrics(event_type, success, processing_time):
    """Track webhook processing metrics."""
    webhook_metrics[f"{event_type}_total"] += 1
    
    if success:
        webhook_metrics[f"{event_type}_success"] += 1
    else:
        webhook_metrics[f"{event_type}_failures"] += 1
    
    webhook_metrics[f"{event_type}_processing_time"] += processing_time

@app.route('/webhooks/lily-media', methods=['POST'])
def webhook_handler():
    start_time = time.time()
    event_data = request.get_json()
    event_type = event_data.get('type', 'unknown')
    
    try:
        result = process_webhook_event(event_data)
        processing_time = time.time() - start_time
        track_webhook_metrics(event_type, True, processing_time)
        return jsonify(result), 200
        
    except Exception as e:
        processing_time = time.time() - start_time
        track_webhook_metrics(event_type, False, processing_time)
        logger.error(f"Webhook processing failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/webhook-metrics')
def webhook_metrics_endpoint():
    """Endpoint for monitoring system to check webhook health."""
    return jsonify(dict(webhook_metrics))
```

### 4. Security Best Practices

```python
import hmac
import time
from functools import wraps

def validate_timestamp(timestamp_header, tolerance=300):
    """Validate request timestamp to prevent replay attacks."""
    try:
        timestamp = int(timestamp_header)
        current_time = int(time.time())
        return abs(current_time - timestamp) <= tolerance
    except (ValueError, TypeError):
        return False

def webhook_security(f):
    """Security decorator for webhook endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check timestamp
        timestamp = request.headers.get('X-Lily-Timestamp')
        if not validate_timestamp(timestamp):
            return jsonify({"error": "Invalid timestamp"}), 401
        
        # Verify signature
        payload = request.get_data()
        signature = request.headers.get('X-Lily-Signature')
        if not verify_webhook_signature(payload, signature, WEBHOOK_SECRET):
            return jsonify({"error": "Invalid signature"}), 401
        
        # Check content type
        if request.headers.get('Content-Type') != 'application/json':
            return jsonify({"error": "Invalid content type"}), 400
        
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/webhooks/lily-media', methods=['POST'])
@webhook_security
def webhook_handler():
    # Your secure webhook handler
    pass
```

## 📝 Code Examples

### Complete Flask Handler

```python
from flask import Flask, request, jsonify
import hmac
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEBHOOK_SECRET = "your_webhook_secret"

class WebhookProcessor:
    def __init__(self):
        self.processed_events = {}  # In production, use Redis or database
    
    def verify_signature(self, payload, signature, secret):
        """Verify HMAC signature."""
        if not signature:
            return False
        
        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        provided_signature = signature.split('=')[1]
        return hmac.compare_digest(expected_signature, provided_signature)
    
    def is_duplicate_event(self, event_id):
        """Check if event was already processed."""
        return event_id in self.processed_events
    
    def mark_processed(self, event_id):
        """Mark event as processed."""
        self.processed_events[event_id] = {
            'processed_at': datetime.utcnow(),
            'status': 'processed'
        }
    
    def handle_post_published(self, event_data):
        """Handle post.published event."""
        post_data = event_data['data']
        post_id = post_data['post_id']
        platform = post_data['platform']
        
        logger.info(f"Post {post_id} published to {platform}")
        
        # Update your database
        # Send notifications
        # Update analytics
        
        return {"status": "processed", "action": "post_published"}
    
    def handle_post_failed(self, event_data):
        """Handle post.failed event."""
        post_data = event_data['data']
        post_id = post_data['post_id']
        error_message = post_data['error_message']
        
        logger.error(f"Post {post_id} failed: {error_message}")
        
        # Alert administrators
        # Update post status
        # Schedule retry if appropriate
        
        return {"status": "processed", "action": "post_failed"}
    
    def handle_content_generated(self, event_data):
        """Handle content.generated event."""
        content_data = event_data['data']
        generation_id = content_data['generation_id']
        content = content_data['content']
        
        logger.info(f"Content generated: {generation_id}")
        
        # Save generated content
        # Notify user
        # Update generation history
        
        return {"status": "processed", "action": "content_generated"}
    
    def process_event(self, event_data):
        """Route event to appropriate handler."""
        event_type = event_data.get('type')
        event_id = event_data.get('id')
        
        # Check for duplicates
        if self.is_duplicate_event(event_id):
            logger.info(f"Duplicate event ignored: {event_id}")
            return {"status": "duplicate"}
        
        # Route to handlers
        handlers = {
            'post.published': self.handle_post_published,
            'post.failed': self.handle_post_failed,
            'content.generated': self.handle_content_generated,
        }
        
        handler = handlers.get(event_type)
        if not handler:
            logger.warning(f"No handler for event type: {event_type}")
            return {"status": "ignored"}
        
        try:
            result = handler(event_data)
            self.mark_processed(event_id)
            return result
        except Exception as e:
            logger.error(f"Handler failed for {event_type}: {e}")
            raise

processor = WebhookProcessor()

@app.route('/webhooks/lily-media', methods=['POST'])
def webhook_handler():
    """Main webhook handler endpoint."""
    
    # Verify signature
    payload = request.get_data()
    signature = request.headers.get('X-Lily-Signature')
    
    if not processor.verify_signature(payload, signature, WEBHOOK_SECRET):
        logger.warning("Invalid webhook signature")
        return jsonify({"error": "Invalid signature"}), 401
    
    # Parse event data
    try:
        event_data = request.get_json()
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        return jsonify({"error": "Invalid JSON"}), 400
    
    # Process event
    try:
        result = processor.process_event(event_data)
        logger.info(f"Webhook processed: {event_data.get('id')} -> {result}")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        return jsonify({"error": "Processing failed"}), 500

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "processed_events": len(processor.processed_events)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### Express.js Handler

```javascript
const express = require('express');
const crypto = require('crypto');
const { body, validationResult } = require('express-validator');

const app = express();

// Middleware to capture raw body for signature verification
app.use('/webhooks', express.raw({type: 'application/json'}));

const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET;
const processedEvents = new Map();

class WebhookProcessor {
    verifySignature(payload, signature, secret) {
        if (!signature) return false;
        
        const expectedSignature = crypto
            .createHmac('sha256', secret)
            .update(payload)
            .digest('hex');
        
        const providedSignature = signature.split('=')[1];
        
        return crypto.timingSafeEqual(
            Buffer.from(expectedSignature, 'hex'),
            Buffer.from(providedSignature, 'hex')
        );
    }
    
    isDuplicateEvent(eventId) {
        return processedEvents.has(eventId);
    }
    
    markProcessed(eventId) {
        processedEvents.set(eventId, {
            processedAt: new Date(),
            status: 'processed'
        });
        
        // Clean up old entries (keep for 24 hours)
        setTimeout(() => {
            processedEvents.delete(eventId);
        }, 24 * 60 * 60 * 1000);
    }
    
    async handlePostPublished(eventData) {
        const { post_id, platform, platform_post_id } = eventData.data;
        
        console.log(`Post ${post_id} published to ${platform}: ${platform_post_id}`);
        
        // Update database
        // Send notifications
        // Track analytics
        
        return { status: 'processed', action: 'post_published' };
    }
    
    async handleContentGenerated(eventData) {
        const { generation_id, content, metadata } = eventData.data;
        
        console.log(`Content generated: ${generation_id}`);
        
        // Save to database
        // Notify user
        
        return { status: 'processed', action: 'content_generated' };
    }
    
    async processEvent(eventData) {
        const { type: eventType, id: eventId } = eventData;
        
        if (this.isDuplicateEvent(eventId)) {
            console.log(`Duplicate event ignored: ${eventId}`);
            return { status: 'duplicate' };
        }
        
        const handlers = {
            'post.published': this.handlePostPublished.bind(this),
            'content.generated': this.handleContentGenerated.bind(this),
        };
        
        const handler = handlers[eventType];
        if (!handler) {
            console.warn(`No handler for event type: ${eventType}`);
            return { status: 'ignored' };
        }
        
        try {
            const result = await handler(eventData);
            this.markProcessed(eventId);
            return result;
        } catch (error) {
            console.error(`Handler failed for ${eventType}:`, error);
            throw error;
        }
    }
}

const processor = new WebhookProcessor();

app.post('/webhooks/lily-media', async (req, res) => {
    try {
        // Verify signature
        const signature = req.get('X-Lily-Signature');
        if (!processor.verifySignature(req.body, signature, WEBHOOK_SECRET)) {
            console.warn('Invalid webhook signature');
            return res.status(401).json({ error: 'Invalid signature' });
        }
        
        // Parse JSON
        const eventData = JSON.parse(req.body);
        
        // Process event
        const result = await processor.processEvent(eventData);
        
        console.log(`Webhook processed: ${eventData.id} ->`, result);
        res.json(result);
        
    } catch (error) {
        console.error('Webhook processing failed:', error);
        res.status(500).json({ error: 'Processing failed' });
    }
});

app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        processedEvents: processedEvents.size
    });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Webhook server listening on port ${PORT}`);
});
```

## 📊 Webhook Management

### List Webhooks

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://api.lily-media.ai/api/webhooks"
```

### Update Webhook

```bash
curl -X PUT "https://api.lily-media.ai/api/webhooks/webhook_abc123" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "events": ["post.published", "post.failed", "content.generated"],
    "url": "https://your-new-endpoint.com/webhooks"
  }'
```

### Delete Webhook

```bash
curl -X DELETE "https://api.lily-media.ai/api/webhooks/webhook_abc123" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Webhook Status

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://api.lily-media.ai/api/webhooks/webhook_abc123/status"
```

---

## 🔗 Related Documentation

- **[API Reference](./api-reference.md)** - Complete endpoint documentation
- **[Authentication](./authentication.md)** - API authentication guide
- **[Error Handling](./error-handling.md)** - Error handling patterns
- **[Getting Started](./getting-started.md)** - Quick start guide

## 💡 Need Help?

- **Documentation**: [docs.lily-media.ai](https://docs.lily-media.ai)
- **Webhook Tester**: [webhook.lily-media.ai](https://webhook.lily-media.ai)
- **Support**: api-support@lily-media.ai
- **Community**: [Discord](https://discord.gg/lily-media-ai)