# Getting Started with Lily Media AI API

Get up and running with the Lily Media AI API in just 5 minutes. This guide will walk you through your first API calls and show you how to create, schedule, and publish AI-generated content.

## 🚀 Quick Start

### Step 1: Get Your API Key

1. Sign up at [lily-media.ai](https://lily-media.ai)
2. Navigate to **Settings** > **API Keys**
3. Click **Generate New API Key**
4. Copy your API key (keep it secure!)

### Step 2: Make Your First Request

Test your connection with a simple health check:

```bash
curl -H "Authorization: Bearer your-api-key-here" \
     https://api.lily-media.ai/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2024-09-07T14:30:00Z"
}
```

### Step 3: Check Your Account

Get your account information and current plan:

```bash
curl -H "Authorization: Bearer your-api-key-here" \
     https://api.lily-media.ai/api/auth/me
```

Expected response:
```json
{
  "id": "user_123",
  "email": "you@example.com",
  "plan": "professional",
  "quota": {
    "content_generations_remaining": 850,
    "image_generations_remaining": 425,
    "requests_per_hour_remaining": 18500
  }
}
```

## 🎯 Your First AI Content Generation

### Generate Text Content

```bash
curl -X POST "https://api.lily-media.ai/api/content/generate" \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a motivational post about Monday morning productivity",
    "platform": "instagram",
    "tone": "professional",
    "length": "short"
  }'
```

Response:
```json
{
  "content": "Monday Motivation 💪\n\nStart your week with intention! Here are 3 simple ways to boost your Monday productivity:\n\n✨ Plan your top 3 priorities\n⏰ Time-block your most important tasks\n🎯 Celebrate small wins throughout the day\n\nWhat's your Monday productivity tip? Share below! 👇\n\n#MondayMotivation #ProductivityTips #WorkSuccess",
  "hashtags": ["#MondayMotivation", "#ProductivityTips", "#WorkSuccess"],
  "platform_optimized": true,
  "character_count": 187,
  "content_id": "content_abc123"
}
```

### Generate an Image

```bash
curl -X POST "https://api.lily-media.ai/api/images/generate" \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Professional workspace with laptop, coffee, and motivational quote",
    "style": "modern",
    "aspect_ratio": "1:1",
    "quality": "high"
  }'
```

Response:
```json
{
  "image_url": "https://cdn.lily-media.ai/images/abc123.jpg",
  "alt_text": "Modern workspace featuring an open laptop, steaming coffee cup, and inspirational quote on a clean desk",
  "dimensions": {
    "width": 1024,
    "height": 1024
  },
  "image_id": "img_xyz789"
}
```

## 📱 Connect Your Social Accounts

### List Available Platforms

```bash
curl -H "Authorization: Bearer your-api-key-here" \
     https://api.lily-media.ai/api/integrations/platforms
```

### Start OAuth Connection

```bash
curl -X POST "https://api.lily-media.ai/api/integrations/connect" \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "instagram",
    "redirect_uri": "https://your-app.com/callback"
  }'
```

Response:
```json
{
  "authorization_url": "https://api.instagram.com/oauth/authorize?client_id=...",
  "state": "secure_random_string",
  "expires_in": 600
}
```

## 📝 Create and Schedule a Post

### Create a Complete Post

```bash
curl -X POST "https://api.lily-media.ai/api/posts" \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Monday Motivation 💪\n\nStart your week with intention!...",
    "platforms": ["instagram", "twitter"],
    "media": {
      "images": ["img_xyz789"]
    },
    "schedule": {
      "publish_at": "2024-09-08T09:00:00Z",
      "timezone": "America/New_York"
    },
    "options": {
      "auto_hashtag": true,
      "cross_post": true
    }
  }'
```

Response:
```json
{
  "post_id": "post_def456",
  "status": "scheduled",
  "scheduled_for": "2024-09-08T09:00:00Z",
  "platforms": {
    "instagram": {
      "status": "scheduled",
      "estimated_reach": 1250
    },
    "twitter": {
      "status": "scheduled",
      "estimated_engagement": 85
    }
  },
  "preview_urls": {
    "instagram": "https://api.lily-media.ai/preview/post_def456/instagram",
    "twitter": "https://api.lily-media.ai/preview/post_def456/twitter"
  }
}
```

## 📊 Check Your Analytics

### Get Post Performance

```bash
curl -H "Authorization: Bearer your-api-key-here" \
     "https://api.lily-media.ai/api/analytics/posts/post_def456"
```

### Get Account Overview

```bash
curl -H "Authorization: Bearer your-api-key-here" \
     "https://api.lily-media.ai/api/analytics/overview?period=7d"
```

## 🔄 Common Workflows

### 1. AI Content Creation Workflow

```python
import requests

# Configuration
API_BASE = "https://api.lily-media.ai/api"
headers = {"Authorization": "Bearer your-api-key-here"}

# Step 1: Generate content
content_response = requests.post(f"{API_BASE}/content/generate", 
    headers=headers,
    json={
        "prompt": "Create a post about sustainable living tips",
        "platform": "instagram",
        "tone": "friendly",
        "include_cta": True
    }
)
content = content_response.json()

# Step 2: Generate matching image
image_response = requests.post(f"{API_BASE}/images/generate",
    headers=headers, 
    json={
        "prompt": f"Visual representation of: {content['content'][:100]}",
        "style": "eco-friendly",
        "aspect_ratio": "1:1"
    }
)
image = image_response.json()

# Step 3: Schedule the post
post_response = requests.post(f"{API_BASE}/posts",
    headers=headers,
    json={
        "content": content["content"],
        "platforms": ["instagram", "twitter"],
        "media": {"images": [image["image_id"]]},
        "schedule": {"publish_at": "2024-09-08T15:00:00Z"}
    }
)

print(f"Post scheduled: {post_response.json()['post_id']}")
```

### 2. Bulk Content Generation

```python
import requests
import time

API_BASE = "https://api.lily-media.ai/api"
headers = {"Authorization": "Bearer your-api-key-here"}

topics = [
    "Monday motivation for entrepreneurs",
    "Tuesday tips for productivity", 
    "Wednesday wellness and self-care",
    "Thursday thoughts on leadership",
    "Friday features and celebrations"
]

posts = []
for topic in topics:
    # Respect rate limits
    time.sleep(1)
    
    response = requests.post(f"{API_BASE}/content/generate",
        headers=headers,
        json={
            "prompt": topic,
            "platform": "linkedin",
            "tone": "professional"
        }
    )
    
    if response.status_code == 200:
        posts.append(response.json())
    else:
        print(f"Failed to generate content for: {topic}")

print(f"Generated {len(posts)} posts")
```

## ⚠️ Important Considerations

### Rate Limits
- Monitor the `X-RateLimit-Remaining` header
- Implement exponential backoff for 429 responses
- Use webhooks to avoid polling

### Error Handling
- Always check status codes
- Parse error responses for details
- Implement retry logic for transient errors

### Security
- Never expose API keys in client-side code
- Use environment variables for API keys
- Rotate keys regularly

### Best Practices
- Cache responses when appropriate
- Use batch operations when available
- Monitor quota usage

## 🔗 Next Steps

Now that you've made your first API calls, explore these guides:

- **[Authentication Guide](./authentication.md)** - Secure OAuth flows
- **[API Reference](./api-reference.md)** - Complete endpoint documentation  
- **[Error Handling](./error-handling.md)** - Robust error management
- **[Integration Examples](./examples/)** - Real-world use cases
- **[Webhooks](./webhooks.md)** - Event-driven development

## 💡 Need Help?

- **Documentation**: [docs.lily-media.ai](https://docs.lily-media.ai)
- **API Status**: [status.lily-media.ai](https://status.lily-media.ai)  
- **Support**: api-support@lily-media.ai
- **Community**: [Discord](https://discord.gg/lily-media-ai)

---

**Ready for more advanced features?** Check out our [Integration Examples](./examples/) for complete application workflows.