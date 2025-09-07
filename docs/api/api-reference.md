# API Reference

Complete reference documentation for all Lily Media AI API endpoints. This documentation is automatically generated from our OpenAPI specification and is always up-to-date.

## 📋 Overview

The Lily Media AI API is organized around REST principles. It uses predictable resource-oriented URLs, accepts form-encoded request bodies, returns JSON-encoded responses, and uses standard HTTP response codes, authentication, and verbs.

### Base URL
```
https://api.lily-media.ai/api
```

### Authentication
All API requests require authentication using Bearer tokens:

```http
Authorization: Bearer your-api-key-here
```

### Content Type
All requests should use JSON:

```http
Content-Type: application/json
```

## 🔑 Authentication Endpoints

### POST /auth/login
Authenticate a user and receive access tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### POST /auth/refresh
Refresh an access token using a refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 3600
}
```

### GET /auth/me
Get current user information.

**Response:**
```json
{
  "id": "user_123",
  "email": "user@example.com",
  "name": "John Doe",
  "plan": "professional",
  "quota": {
    "content_generations_remaining": 850,
    "image_generations_remaining": 425,
    "requests_per_hour_remaining": 18500
  },
  "organization": {
    "id": "org_456",
    "name": "Acme Corp",
    "role": "admin"
  }
}
```

## 🎨 Content Generation Endpoints

### POST /content/generate
Generate AI-powered text content optimized for social media platforms.

**Parameters:**
- `prompt` (required): Description of the content to generate
- `platform` (required): Target platform (`instagram`, `twitter`, `linkedin`, `facebook`, `tiktok`)
- `tone` (optional): Content tone (`professional`, `friendly`, `casual`, `formal`, `humorous`)
- `length` (optional): Content length (`short`, `medium`, `long`)
- `include_hashtags` (optional): Whether to include hashtags (boolean)
- `include_cta` (optional): Whether to include call-to-action (boolean)
- `brand_voice` (optional): Brand voice identifier from Style Vault

**Request:**
```json
{
  "prompt": "Create a motivational post about productivity",
  "platform": "instagram", 
  "tone": "friendly",
  "length": "medium",
  "include_hashtags": true,
  "include_cta": true,
  "brand_voice": "brand_voice_123"
}
```

**Response:**
```json
{
  "content": "🌟 Monday Motivation Alert! 🌟\n\nFeeling overwhelmed by your to-do list? Here's the secret: Start small, think big! 💪\n\n✨ Break big tasks into bite-sized pieces\n🎯 Focus on one thing at a time\n⏰ Use the 2-minute rule: if it takes less than 2 minutes, do it now!\n💡 Celebrate every small win\n\nRemember, productivity isn't about doing more—it's about doing what matters most. What's your #1 productivity tip? Share below! 👇",
  "hashtags": ["#MondayMotivation", "#ProductivityTips", "#WorkSuccess", "#MindfulMonday"],
  "platform_optimized": true,
  "character_count": 387,
  "word_count": 67,
  "content_id": "content_abc123",
  "estimated_engagement": {
    "likes": 125,
    "comments": 18,
    "shares": 23
  }
}
```

### POST /content/optimize
Optimize existing content for a specific platform.

**Parameters:**
- `content` (required): Original content to optimize
- `source_platform` (required): Original platform
- `target_platform` (required): Target platform for optimization
- `preserve_hashtags` (optional): Keep original hashtags (boolean)

**Request:**
```json
{
  "content": "Great meeting today! Excited about the new project launch.",
  "source_platform": "twitter",
  "target_platform": "linkedin",
  "preserve_hashtags": false
}
```

**Response:**
```json
{
  "optimized_content": "I'm thrilled to share insights from today's strategic planning session. Our team has made significant progress on an exciting new project that will launch next quarter.\n\nKey highlights from today:\n• Confirmed project timeline and deliverables\n• Aligned cross-functional teams on objectives  \n• Established clear success metrics\n\nLooking forward to sharing more details as we progress. What strategies has your team found most effective for project launches?",
  "changes_made": [
    "Expanded content for LinkedIn's longer format",
    "Added professional tone and structure", 
    "Included conversation starter question",
    "Removed casual language"
  ],
  "character_count": 542,
  "platform_optimized": true
}
```

## 🖼️ Image Generation Endpoints

### POST /images/generate
Generate AI-powered images using xAI Grok-2 Vision.

**Parameters:**
- `prompt` (required): Description of the image to generate
- `style` (optional): Image style (`photorealistic`, `illustration`, `modern`, `vintage`, `minimal`)
- `aspect_ratio` (optional): Image dimensions (`1:1`, `16:9`, `9:16`, `4:3`, `3:4`)
- `quality` (optional): Image quality (`standard`, `high`, `ultra`)
- `brand_style` (optional): Brand style identifier from Style Vault

**Request:**
```json
{
  "prompt": "Modern workspace with laptop, coffee, and plants, natural lighting",
  "style": "photorealistic", 
  "aspect_ratio": "16:9",
  "quality": "high",
  "brand_style": "brand_style_456"
}
```

**Response:**
```json
{
  "image_url": "https://cdn.lily-media.ai/images/img_xyz789.jpg",
  "thumbnail_url": "https://cdn.lily-media.ai/images/thumbs/img_xyz789.jpg",
  "alt_text": "Modern workspace featuring an open laptop, steaming coffee cup, green plants, and natural lighting streaming through a window",
  "dimensions": {
    "width": 1920,
    "height": 1080
  },
  "file_size": 245760,
  "format": "JPEG",
  "image_id": "img_xyz789",
  "generation_time": 3.2,
  "quality_score": 0.92
}
```

### GET /images/{image_id}
Get information about a generated image.

**Response:**
```json
{
  "image_id": "img_xyz789",
  "image_url": "https://cdn.lily-media.ai/images/img_xyz789.jpg",
  "alt_text": "Modern workspace featuring an open laptop...",
  "created_at": "2024-09-07T14:30:00Z",
  "prompt": "Modern workspace with laptop, coffee, and plants",
  "style": "photorealistic",
  "dimensions": {"width": 1920, "height": 1080},
  "usage_count": 3,
  "posts_used_in": ["post_def456", "post_ghi789"]
}
```

## 📱 Social Integration Endpoints

### GET /integrations/platforms
List all supported social media platforms.

**Response:**
```json
{
  "platforms": [
    {
      "id": "instagram",
      "name": "Instagram",
      "supports": ["posts", "stories", "reels"],
      "max_image_size": 8388608,
      "max_video_size": 104857600,
      "character_limits": {
        "caption": 2200,
        "hashtags": 30
      }
    },
    {
      "id": "twitter",
      "name": "Twitter/X", 
      "supports": ["tweets", "threads"],
      "max_image_size": 5242880,
      "character_limits": {
        "tweet": 280,
        "thread": 25
      }
    }
  ]
}
```

### POST /integrations/connect
Initiate OAuth connection to a social platform.

**Parameters:**
- `platform` (required): Platform identifier
- `redirect_uri` (required): OAuth callback URL
- `scopes` (optional): Requested permissions

**Request:**
```json
{
  "platform": "instagram",
  "redirect_uri": "https://your-app.com/callback",
  "scopes": ["pages_manage_posts", "pages_read_engagement"]
}
```

**Response:**
```json
{
  "authorization_url": "https://www.facebook.com/v18.0/dialog/oauth?client_id=...",
  "state": "secure_random_string_123",
  "expires_in": 600,
  "connection_id": "conn_abc123"
}
```

### GET /integrations/connections
List all connected social accounts.

**Response:**
```json
{
  "connections": [
    {
      "id": "conn_abc123",
      "platform": "instagram",
      "account_name": "@mybrand",
      "account_id": "17841402441234567",
      "status": "active",
      "permissions": ["pages_manage_posts", "pages_read_engagement"],
      "connected_at": "2024-09-01T10:00:00Z",
      "last_used": "2024-09-07T09:15:00Z"
    }
  ]
}
```

## 📝 Posts Endpoints

### POST /posts
Create and optionally schedule a social media post.

**Parameters:**
- `content` (required): Post content text
- `platforms` (required): Array of platform identifiers
- `media` (optional): Media attachments
- `schedule` (optional): Scheduling information
- `options` (optional): Additional posting options

**Request:**
```json
{
  "content": "Exciting news! We're launching our new feature next week 🚀",
  "platforms": ["twitter", "instagram", "linkedin"],
  "media": {
    "images": ["img_xyz789"],
    "videos": []
  },
  "schedule": {
    "publish_at": "2024-09-08T15:00:00Z",
    "timezone": "America/New_York"
  },
  "options": {
    "auto_hashtag": true,
    "cross_post": true,
    "optimize_timing": true
  }
}
```

**Response:**
```json
{
  "post_id": "post_def456",
  "status": "scheduled",
  "scheduled_for": "2024-09-08T15:00:00Z",
  "platforms": {
    "twitter": {
      "status": "scheduled",
      "connection_id": "conn_twitter_123",
      "estimated_reach": 850
    },
    "instagram": {
      "status": "scheduled", 
      "connection_id": "conn_instagram_456",
      "estimated_reach": 1250
    },
    "linkedin": {
      "status": "scheduled",
      "connection_id": "conn_linkedin_789", 
      "estimated_reach": 420
    }
  },
  "preview_urls": {
    "twitter": "https://api.lily-media.ai/preview/post_def456/twitter",
    "instagram": "https://api.lily-media.ai/preview/post_def456/instagram",
    "linkedin": "https://api.lily-media.ai/preview/post_def456/linkedin"
  },
  "created_at": "2024-09-07T14:30:00Z"
}
```

### GET /posts
List posts with filtering and pagination.

**Query Parameters:**
- `status` (optional): Filter by status (`draft`, `scheduled`, `published`, `failed`)
- `platform` (optional): Filter by platform
- `limit` (optional): Number of results (default: 20, max: 100)
- `offset` (optional): Pagination offset
- `start_date` (optional): Filter posts from date
- `end_date` (optional): Filter posts until date

**Response:**
```json
{
  "posts": [
    {
      "post_id": "post_def456",
      "content": "Exciting news! We're launching our new feature...",
      "status": "published",
      "platforms": ["twitter", "instagram"],
      "created_at": "2024-09-07T14:30:00Z",
      "published_at": "2024-09-08T15:00:00Z",
      "performance": {
        "total_reach": 2100,
        "total_engagement": 184,
        "engagement_rate": 0.088
      }
    }
  ],
  "pagination": {
    "total": 156,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

### GET /posts/{post_id}
Get detailed information about a specific post.

**Response:**
```json
{
  "post_id": "post_def456",
  "content": "Exciting news! We're launching our new feature next week 🚀",
  "status": "published",
  "platforms": {
    "twitter": {
      "platform_post_id": "1234567890123456789",
      "status": "published",
      "url": "https://twitter.com/username/status/1234567890123456789",
      "metrics": {
        "likes": 42,
        "retweets": 18,
        "replies": 7,
        "reach": 850
      }
    },
    "instagram": {
      "platform_post_id": "18123456789012345",
      "status": "published", 
      "url": "https://instagram.com/p/ABC123def45/",
      "metrics": {
        "likes": 156,
        "comments": 23,
        "shares": 12,
        "reach": 1250
      }
    }
  },
  "media": [
    {
      "image_id": "img_xyz789",
      "url": "https://cdn.lily-media.ai/images/img_xyz789.jpg",
      "alt_text": "Modern workspace featuring..."
    }
  ],
  "created_at": "2024-09-07T14:30:00Z",
  "scheduled_for": "2024-09-08T15:00:00Z",
  "published_at": "2024-09-08T15:00:15Z"
}
```

## 📊 Analytics Endpoints

### GET /analytics/overview
Get account-wide analytics overview.

**Query Parameters:**
- `period` (optional): Time period (`1d`, `7d`, `30d`, `90d`, `1y`)
- `platforms` (optional): Comma-separated platform list
- `metrics` (optional): Comma-separated metrics list

**Response:**
```json
{
  "period": "30d",
  "summary": {
    "total_posts": 47,
    "total_reach": 125750,
    "total_engagement": 8924,
    "engagement_rate": 0.071,
    "follower_growth": 342,
    "top_performing_platform": "instagram"
  },
  "platforms": {
    "instagram": {
      "posts": 18,
      "reach": 67200,
      "engagement": 5280,
      "engagement_rate": 0.079
    },
    "twitter": {
      "posts": 23,
      "reach": 42300,
      "engagement": 2890,
      "engagement_rate": 0.068
    },
    "linkedin": {
      "posts": 6,
      "reach": 16250,
      "engagement": 754,
      "engagement_rate": 0.046
    }
  },
  "trends": {
    "reach_change": "+15.2%",
    "engagement_change": "+8.7%",
    "post_frequency_change": "+12.3%"
  }
}
```

### GET /analytics/posts/{post_id}
Get detailed analytics for a specific post.

**Response:**
```json
{
  "post_id": "post_def456",
  "analytics_period": "7d",
  "total_metrics": {
    "reach": 2100,
    "impressions": 3240,
    "engagement": 184,
    "engagement_rate": 0.088,
    "clicks": 23,
    "saves": 15,
    "shares": 31
  },
  "platform_breakdown": {
    "twitter": {
      "reach": 850,
      "likes": 42,
      "retweets": 18,
      "replies": 7,
      "clicks": 12
    },
    "instagram": {
      "reach": 1250,
      "likes": 156,
      "comments": 23,
      "shares": 12,
      "saves": 15,
      "profile_visits": 8
    }
  },
  "demographics": {
    "age_groups": {
      "18-24": 0.23,
      "25-34": 0.41,
      "35-44": 0.28,
      "45+": 0.08
    },
    "locations": {
      "US": 0.52,
      "UK": 0.18,
      "CA": 0.12,
      "AU": 0.08,
      "other": 0.10
    }
  }
}
```

## 🎯 Automation Endpoints

### POST /automation/workflows
Create an automated posting workflow.

**Parameters:**
- `name` (required): Workflow name
- `trigger` (required): Automation trigger configuration
- `actions` (required): Actions to perform
- `schedule` (optional): Scheduling configuration

**Request:**
```json
{
  "name": "Daily Motivation Posts",
  "description": "Generate and post daily motivational content",
  "trigger": {
    "type": "schedule",
    "schedule": {
      "frequency": "daily",
      "time": "09:00:00",
      "timezone": "America/New_York",
      "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
    }
  },
  "actions": [
    {
      "type": "generate_content",
      "config": {
        "prompt_template": "Create a motivational post for {{day_of_week}}",
        "platform": "instagram",
        "tone": "inspiring"
      }
    },
    {
      "type": "generate_image", 
      "config": {
        "prompt_template": "Motivational image for {{generated_content}}",
        "style": "modern"
      }
    },
    {
      "type": "publish_post",
      "config": {
        "platforms": ["instagram", "twitter"],
        "delay_minutes": 5
      }
    }
  ]
}
```

**Response:**
```json
{
  "workflow_id": "workflow_abc123",
  "name": "Daily Motivation Posts",
  "status": "active",
  "next_execution": "2024-09-08T09:00:00Z",
  "created_at": "2024-09-07T14:30:00Z",
  "executions_count": 0,
  "success_rate": null
}
```

### GET /automation/workflows
List automation workflows.

**Response:**
```json
{
  "workflows": [
    {
      "workflow_id": "workflow_abc123",
      "name": "Daily Motivation Posts",
      "status": "active",
      "next_execution": "2024-09-08T09:00:00Z",
      "last_execution": "2024-09-07T09:00:00Z",
      "executions_count": 5,
      "success_rate": 1.0
    }
  ]
}
```

## 🔔 Webhook Endpoints

### POST /webhooks
Register a new webhook endpoint.

**Request:**
```json
{
  "url": "https://your-app.com/webhooks/lily-media",
  "events": ["post.published", "post.failed", "analytics.updated"],
  "secret": "your_webhook_secret"
}
```

**Response:**
```json
{
  "webhook_id": "webhook_xyz789",
  "url": "https://your-app.com/webhooks/lily-media",
  "events": ["post.published", "post.failed", "analytics.updated"],
  "status": "active",
  "created_at": "2024-09-07T14:30:00Z"
}
```

### GET /webhooks
List registered webhooks.

**Response:**
```json
{
  "webhooks": [
    {
      "webhook_id": "webhook_xyz789",
      "url": "https://your-app.com/webhooks/lily-media",
      "events": ["post.published", "post.failed", "analytics.updated"],
      "status": "active",
      "last_delivery": "2024-09-07T13:45:00Z",
      "success_rate": 0.98
    }
  ]
}
```

## ⚠️ Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "type": "validation_error",
    "message": "The request contains invalid parameters",
    "details": [
      {
        "field": "platform",
        "code": "invalid_choice",
        "message": "Platform 'myspace' is not supported"
      }
    ],
    "request_id": "req_abc123",
    "timestamp": "2024-09-07T14:30:00Z"
  }
}
```

### Common Error Codes

| HTTP Code | Error Type | Description |
|-----------|------------|-------------|
| 400 | `validation_error` | Invalid request parameters |
| 401 | `authentication_error` | Invalid or missing API key |
| 403 | `authorization_error` | Insufficient permissions |
| 404 | `resource_not_found` | Resource doesn't exist |
| 429 | `rate_limit_error` | Rate limit exceeded |
| 500 | `server_error` | Internal server error |

## 📊 Rate Limits

Rate limits are enforced per API key and vary by plan:

| Plan | Requests/Hour | Burst Limit | Content Gen/Day |
|------|---------------|-------------|-----------------|
| Free | 1,000 | 50 | 10 |
| Basic | 5,000 | 100 | 100 |
| Pro | 20,000 | 500 | 1,000 |
| Enterprise | Custom | Custom | Custom |

### Rate Limit Headers

```http
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4850  
X-RateLimit-Reset: 1694097600
X-RateLimit-Burst-Remaining: 95
```

---

## 🔗 Additional Resources

- **[Interactive API Explorer](https://api.lily-media.ai/docs)** - Test endpoints in your browser
- **[OpenAPI Specification](https://api.lily-media.ai/openapi.json)** - Machine-readable API spec
- **[Postman Collection](https://docs.lily-media.ai/postman)** - Import our collection
- **[SDKs & Libraries](./sdks.md)** - Official and community libraries

**Need help?** Contact our API support team at api-support@lily-media.ai