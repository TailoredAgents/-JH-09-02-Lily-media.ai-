# SDKs and Libraries

Official and community-maintained SDKs and libraries for the Lily Media AI API.

## 🏗️ Overview

While the Lily Media AI API is REST-based and can be used with any HTTP client, we provide official SDKs and support community libraries to make integration easier and more robust.

## 📋 Table of Contents

- [Official SDKs](#official-sdks)
- [Community Libraries](#community-libraries)
- [Language-Specific Examples](#language-specific-examples)
- [SDK Features](#sdk-features)
- [Installation Guides](#installation-guides)
- [Quick Start Examples](#quick-start-examples)
- [Advanced Usage](#advanced-usage)
- [Contributing](#contributing)

## 🔧 Official SDKs

### Python SDK (lily-media-python)

**Status**: ✅ Official | **Version**: v2.0.0 | **Maintenance**: Active

```bash
pip install lily-media-python
```

**Features**:
- ✅ Full API coverage
- ✅ Async/await support
- ✅ Built-in retry logic
- ✅ Type hints
- ✅ Rate limit handling
- ✅ Webhook verification
- ✅ File upload support

**Quick Example**:
```python
from lily_media import LilyMediaClient

client = LilyMediaClient(api_key="your_api_key")

# Generate content
content = client.content.generate(
    prompt="Create a Monday motivation post",
    platform="instagram",
    tone="professional"
)

# Generate image
image = client.images.generate(
    prompt="Professional office workspace",
    style="photographic",
    aspect_ratio="1:1"
)

# Schedule post
post = client.posts.create(
    content=content.content,
    platforms=["instagram", "twitter"],
    media={"images": [image.image_id]},
    schedule={"publish_at": "2024-09-08T09:00:00Z"}
)
```

### Node.js SDK (lily-media-node)

**Status**: ✅ Official | **Version**: v2.0.0 | **Maintenance**: Active

```bash
npm install lily-media-node
```

**Features**:
- ✅ Full API coverage
- ✅ Promise-based & async/await
- ✅ TypeScript definitions
- ✅ Automatic retries
- ✅ Rate limit handling
- ✅ Webhook middleware
- ✅ Stream support

**Quick Example**:
```javascript
const { LilyMediaClient } = require('lily-media-node');

const client = new LilyMediaClient({
  apiKey: 'your_api_key'
});

async function createPost() {
  // Generate content
  const content = await client.content.generate({
    prompt: "Create a Monday motivation post",
    platform: "instagram",
    tone: "professional"
  });

  // Generate image
  const image = await client.images.generate({
    prompt: "Professional office workspace",
    style: "photographic",
    aspectRatio: "1:1"
  });

  // Schedule post
  const post = await client.posts.create({
    content: content.content,
    platforms: ["instagram", "twitter"],
    media: { images: [image.imageId] },
    schedule: { publishAt: "2024-09-08T09:00:00Z" }
  });

  return post;
}
```

### PHP SDK (lily-media-php)

**Status**: ✅ Official | **Version**: v2.0.0 | **Maintenance**: Active

```bash
composer require lily-media/lily-media-php
```

**Features**:
- ✅ Full API coverage
- ✅ PSR-7 HTTP message support
- ✅ Guzzle HTTP client
- ✅ Laravel integration
- ✅ WordPress plugin support
- ✅ Built-in caching

**Quick Example**:
```php
<?php
use LilyMedia\Client;

$client = new Client([
    'api_key' => 'your_api_key'
]);

// Generate content
$content = $client->content()->generate([
    'prompt' => 'Create a Monday motivation post',
    'platform' => 'instagram',
    'tone' => 'professional'
]);

// Generate image
$image = $client->images()->generate([
    'prompt' => 'Professional office workspace',
    'style' => 'photographic',
    'aspect_ratio' => '1:1'
]);

// Schedule post
$post = $client->posts()->create([
    'content' => $content->content,
    'platforms' => ['instagram', 'twitter'],
    'media' => ['images' => [$image->image_id]],
    'schedule' => ['publish_at' => '2024-09-08T09:00:00Z']
]);
```

### Go SDK (lily-media-go)

**Status**: ✅ Official | **Version**: v2.0.0 | **Maintenance**: Active

```bash
go get github.com/lily-media/lily-media-go
```

**Features**:
- ✅ Full API coverage
- ✅ Context support
- ✅ Structured error handling
- ✅ HTTP/2 support
- ✅ Concurrent request handling
- ✅ Built-in JSON marshaling

**Quick Example**:
```go
package main

import (
    "context"
    "fmt"
    "time"

    "github.com/lily-media/lily-media-go"
)

func main() {
    client := lilymedia.NewClient("your_api_key")
    ctx := context.Background()

    // Generate content
    content, err := client.Content.Generate(ctx, &lilymedia.ContentGenerateRequest{
        Prompt:   "Create a Monday motivation post",
        Platform: "instagram",
        Tone:     "professional",
    })
    if err != nil {
        panic(err)
    }

    // Generate image
    image, err := client.Images.Generate(ctx, &lilymedia.ImageGenerateRequest{
        Prompt:      "Professional office workspace",
        Style:       "photographic",
        AspectRatio: "1:1",
    })
    if err != nil {
        panic(err)
    }

    // Schedule post
    publishTime := time.Now().Add(1 * time.Hour)
    post, err := client.Posts.Create(ctx, &lilymedia.PostCreateRequest{
        Content:   content.Content,
        Platforms: []string{"instagram", "twitter"},
        Media: &lilymedia.PostMedia{
            Images: []string{image.ImageID},
        },
        Schedule: &lilymedia.PostSchedule{
            PublishAt: &publishTime,
        },
    })
    if err != nil {
        panic(err)
    }

    fmt.Printf("Post scheduled: %s\n", post.PostID)
}
```

### Ruby SDK (lily-media-ruby)

**Status**: ✅ Official | **Version**: v2.0.0 | **Maintenance**: Active

```bash
gem install lily-media-ruby
```

**Features**:
- ✅ Full API coverage
- ✅ ActiveRecord-style interface
- ✅ Rails integration
- ✅ Built-in pagination
- ✅ Automatic retries
- ✅ Thread-safe

**Quick Example**:
```ruby
require 'lily_media'

client = LilyMedia::Client.new(api_key: 'your_api_key')

# Generate content
content = client.content.generate(
  prompt: 'Create a Monday motivation post',
  platform: 'instagram',
  tone: 'professional'
)

# Generate image
image = client.images.generate(
  prompt: 'Professional office workspace',
  style: 'photographic',
  aspect_ratio: '1:1'
)

# Schedule post
post = client.posts.create(
  content: content.content,
  platforms: %w[instagram twitter],
  media: { images: [image.image_id] },
  schedule: { publish_at: 1.hour.from_now.iso8601 }
)

puts "Post scheduled: #{post.post_id}"
```

## 🌍 Community Libraries

### Java SDK (community-maintained)

**Repository**: [github.com/community/lily-media-java](https://github.com/community/lily-media-java)  
**Maintainer**: [@java-dev-community](https://github.com/java-dev-community)  
**Status**: 🟡 Community | **Version**: v1.5.0

```xml
<dependency>
    <groupId>com.lilymedia</groupId>
    <artifactId>lily-media-java</artifactId>
    <version>1.5.0</version>
</dependency>
```

### C# SDK (community-maintained)

**Repository**: [github.com/community/lily-media-csharp](https://github.com/community/lily-media-csharp)  
**Maintainer**: [@dotnet-devs](https://github.com/dotnet-devs)  
**Status**: 🟡 Community | **Version**: v1.3.0

```bash
dotnet add package LilyMedia.SDK
```

### Rust SDK (community-maintained)

**Repository**: [github.com/community/lily-media-rust](https://github.com/community/lily-media-rust)  
**Maintainer**: [@rust-community](https://github.com/rust-community)  
**Status**: 🟡 Community | **Version**: v0.8.0

```bash
cargo add lily-media
```

### Swift SDK (community-maintained)

**Repository**: [github.com/community/lily-media-swift](https://github.com/community/lily-media-swift)  
**Maintainer**: [@ios-devs](https://github.com/ios-devs)  
**Status**: 🟡 Community | **Version**: v1.2.0

```swift
// Package.swift
dependencies: [
    .package(url: "https://github.com/community/lily-media-swift", from: "1.2.0")
]
```

## 🔥 Framework Integrations

### Laravel Package

```bash
composer require lily-media/laravel-lily-media
php artisan vendor:publish --provider="LilyMedia\Laravel\ServiceProvider"
```

**Configuration**:
```php
// config/lily-media.php
return [
    'api_key' => env('LILY_MEDIA_API_KEY'),
    'base_url' => env('LILY_MEDIA_BASE_URL', 'https://api.lily-media.ai/api'),
    'timeout' => 30,
    'retry_attempts' => 3,
];
```

**Usage**:
```php
// In your controller
use LilyMedia\Laravel\Facades\LilyMedia;

class ContentController extends Controller
{
    public function generateContent(Request $request)
    {
        $content = LilyMedia::content()->generate([
            'prompt' => $request->prompt,
            'platform' => $request->platform,
            'tone' => 'professional'
        ]);

        return response()->json($content);
    }
}
```

### Django Package

```bash
pip install django-lily-media
```

**Settings**:
```python
# settings.py
INSTALLED_APPS = [
    # ... other apps
    'django_lily_media',
]

LILY_MEDIA_API_KEY = 'your_api_key'
LILY_MEDIA_BASE_URL = 'https://api.lily-media.ai/api'
```

**Usage**:
```python
# views.py
from django_lily_media import LilyMediaClient
from django.http import JsonResponse

def generate_content(request):
    client = LilyMediaClient()
    
    content = client.content.generate(
        prompt=request.POST.get('prompt'),
        platform=request.POST.get('platform'),
        tone='professional'
    )
    
    return JsonResponse(content.to_dict())
```

### Next.js Plugin

```bash
npm install @lily-media/nextjs-plugin
```

**Configuration**:
```javascript
// next.config.js
const { withLilyMedia } = require('@lily-media/nextjs-plugin');

module.exports = withLilyMedia({
  lilyMedia: {
    apiKey: process.env.LILY_MEDIA_API_KEY,
  },
});
```

**Usage**:
```javascript
// pages/api/generate-content.js
import { LilyMediaClient } from '@lily-media/nextjs-plugin';

export default async function handler(req, res) {
  const client = new LilyMediaClient();
  
  try {
    const content = await client.content.generate({
      prompt: req.body.prompt,
      platform: req.body.platform,
      tone: 'professional'
    });
    
    res.status(200).json(content);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}
```

### WordPress Plugin

**Installation**:
```bash
wp plugin install lily-media-wp --activate
```

**Configuration**:
```php
// In your theme's functions.php or plugin
add_action('lily_media_init', function() {
    lily_media_configure([
        'api_key' => get_option('lily_media_api_key'),
    ]);
});

// Generate content in your theme
$content = lily_media_generate_content([
    'prompt' => 'Create a blog post about WordPress tips',
    'platform' => 'wordpress',
    'tone' => 'helpful'
]);
```

## 🚀 SDK Features Comparison

| Feature | Python | Node.js | PHP | Go | Ruby |
|---------|--------|---------|-----|----|----- |
| **Full API Coverage** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Async Support** | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Type Safety** | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Rate Limiting** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Auto Retry** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Webhook Support** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **File Upload** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Pagination** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Error Handling** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Caching** | ✅ | ✅ | ✅ | ❌ | ✅ |

## 📚 Installation Guides

### Python SDK - Detailed Setup

```bash
# Install from PyPI
pip install lily-media-python

# Or install with async support
pip install lily-media-python[async]

# Or install development version
pip install git+https://github.com/lily-media/lily-media-python.git
```

**Environment Setup**:
```python
import os
from lily_media import LilyMediaClient

# From environment variable
client = LilyMediaClient(api_key=os.getenv('LILY_MEDIA_API_KEY'))

# Or with configuration file
client = LilyMediaClient.from_config_file('lily_media_config.json')

# Or with custom configuration
client = LilyMediaClient(
    api_key='your_api_key',
    base_url='https://api.lily-media.ai/api',
    timeout=30,
    max_retries=3,
    retry_delay=1.0
)
```

### Node.js SDK - Detailed Setup

```bash
# Install from npm
npm install lily-media-node

# Or with yarn
yarn add lily-media-node

# Or install TypeScript definitions separately
npm install @types/lily-media-node
```

**Configuration**:
```javascript
const { LilyMediaClient } = require('lily-media-node');

// Basic configuration
const client = new LilyMediaClient({
  apiKey: process.env.LILY_MEDIA_API_KEY
});

// Advanced configuration
const client = new LilyMediaClient({
  apiKey: process.env.LILY_MEDIA_API_KEY,
  baseURL: 'https://api.lily-media.ai/api',
  timeout: 30000,
  maxRetries: 3,
  retryDelay: 1000,
  userAgent: 'MyApp/1.0.0'
});
```

## 🎯 Quick Start Examples

### Content Generation Workflow

#### Python
```python
from lily_media import LilyMediaClient
import asyncio

async def content_workflow():
    client = LilyMediaClient(api_key="your_api_key")
    
    # Generate content
    content = await client.content.generate_async(
        prompt="Create a post about productivity tips",
        platform="linkedin",
        tone="professional",
        length="medium"
    )
    
    # Generate matching image
    image = await client.images.generate_async(
        prompt=f"Visual representation of: {content.content[:100]}",
        style="professional",
        aspect_ratio="1:1"
    )
    
    # Schedule post
    post = await client.posts.create_async(
        content=content.content,
        platforms=["linkedin", "twitter"],
        media={"images": [image.image_id]},
        schedule={"publish_at": "2024-09-08T15:00:00Z"}
    )
    
    return post

# Run the workflow
asyncio.run(content_workflow())
```

#### Node.js
```javascript
const { LilyMediaClient } = require('lily-media-node');

async function contentWorkflow() {
  const client = new LilyMediaClient({
    apiKey: process.env.LILY_MEDIA_API_KEY
  });
  
  // Generate content
  const content = await client.content.generate({
    prompt: "Create a post about productivity tips",
    platform: "linkedin",
    tone: "professional",
    length: "medium"
  });
  
  // Generate matching image
  const image = await client.images.generate({
    prompt: `Visual representation of: ${content.content.substring(0, 100)}`,
    style: "professional",
    aspectRatio: "1:1"
  });
  
  // Schedule post
  const post = await client.posts.create({
    content: content.content,
    platforms: ["linkedin", "twitter"],
    media: { images: [image.imageId] },
    schedule: { publishAt: "2024-09-08T15:00:00Z" }
  });
  
  return post;
}

contentWorkflow().then(console.log).catch(console.error);
```

### Webhook Handler Implementation

#### Python (Flask)
```python
from flask import Flask, request, jsonify
from lily_media import LilyMediaClient, verify_webhook_signature

app = Flask(__name__)
client = LilyMediaClient(api_key="your_api_key")

@app.route('/webhooks/lily-media', methods=['POST'])
def handle_webhook():
    # Verify signature
    signature = request.headers.get('X-Lily-Signature')
    payload = request.get_data()
    
    if not verify_webhook_signature(payload, signature, 'your_webhook_secret'):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Process event
    event_data = request.get_json()
    event_type = event_data.get('type')
    
    if event_type == 'post.published':
        # Update your database
        update_post_status(event_data['data']['post_id'], 'published')
    
    elif event_type == 'post.failed':
        # Handle failed post
        handle_post_failure(event_data['data'])
    
    return jsonify({'status': 'processed'})

def update_post_status(post_id, status):
    # Your database update logic
    pass

def handle_post_failure(post_data):
    # Your error handling logic
    pass
```

#### Node.js (Express)
```javascript
const express = require('express');
const { LilyMediaClient, verifyWebhookSignature } = require('lily-media-node');

const app = express();
const client = new LilyMediaClient({ apiKey: process.env.LILY_MEDIA_API_KEY });

app.use('/webhooks', express.raw({ type: 'application/json' }));

app.post('/webhooks/lily-media', (req, res) => {
  const signature = req.get('X-Lily-Signature');
  const payload = req.body;
  
  // Verify signature
  if (!verifyWebhookSignature(payload, signature, process.env.WEBHOOK_SECRET)) {
    return res.status(401).json({ error: 'Invalid signature' });
  }
  
  // Process event
  const eventData = JSON.parse(payload);
  const eventType = eventData.type;
  
  switch (eventType) {
    case 'post.published':
      updatePostStatus(eventData.data.post_id, 'published');
      break;
      
    case 'post.failed':
      handlePostFailure(eventData.data);
      break;
  }
  
  res.json({ status: 'processed' });
});

function updatePostStatus(postId, status) {
  // Your database update logic
}

function handlePostFailure(postData) {
  // Your error handling logic
}

app.listen(3000, () => {
  console.log('Webhook server running on port 3000');
});
```

## 🔧 Advanced Usage

### Custom HTTP Client Configuration

#### Python
```python
import httpx
from lily_media import LilyMediaClient

# Custom HTTP client with specific settings
http_client = httpx.AsyncClient(
    timeout=60.0,
    limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
    headers={"User-Agent": "MyApp/2.0.0"}
)

client = LilyMediaClient(
    api_key="your_api_key",
    http_client=http_client
)
```

#### Node.js
```javascript
const axios = require('axios');
const { LilyMediaClient } = require('lily-media-node');

// Custom axios instance
const httpClient = axios.create({
  timeout: 60000,
  maxRedirects: 3,
  headers: {
    'User-Agent': 'MyApp/2.0.0'
  }
});

const client = new LilyMediaClient({
  apiKey: process.env.LILY_MEDIA_API_KEY,
  httpClient: httpClient
});
```

### Error Handling Patterns

#### Python
```python
from lily_media import LilyMediaClient, LilyMediaError, RateLimitError, QuotaExceededError

client = LilyMediaClient(api_key="your_api_key")

try:
    content = client.content.generate(
        prompt="Create a post about AI",
        platform="instagram"
    )
except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after: {e.retry_after} seconds")
    # Implement backoff strategy
    
except QuotaExceededError as e:
    print(f"Quota exceeded: {e.quota_type}. Resets on: {e.reset_date}")
    # Handle quota limit
    
except LilyMediaError as e:
    print(f"API error: {e.code} - {e.message}")
    # Handle other API errors
    
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle unexpected errors
```

### Pagination Handling

#### Python
```python
# Get all posts with automatic pagination
all_posts = []
for post_batch in client.posts.list_paginated(limit=50):
    all_posts.extend(post_batch.data)
    
    # Optional: Add delay between requests
    time.sleep(0.1)

print(f"Retrieved {len(all_posts)} posts")

# Or use async pagination
async for post_batch in client.posts.list_paginated_async(limit=50):
    process_posts(post_batch.data)
```

#### Node.js
```javascript
// Manual pagination
let page = 1;
const allPosts = [];

while (true) {
  const response = await client.posts.list({
    page: page,
    per_page: 50
  });
  
  allPosts.push(...response.data);
  
  if (!response.pagination.has_more) {
    break;
  }
  
  page++;
}

console.log(`Retrieved ${allPosts.length} posts`);

// Or use async iterator (if supported)
for await (const postBatch of client.posts.listPaginated({ limit: 50 })) {
  processPosts(postBatch.data);
}
```

### Caching Implementation

#### Python with Redis
```python
import redis
import json
from lily_media import LilyMediaClient

redis_client = redis.Redis(host='localhost', port=6379, db=0)

class CachedLilyMediaClient:
    def __init__(self, api_key, cache_ttl=3600):
        self.client = LilyMediaClient(api_key=api_key)
        self.cache_ttl = cache_ttl
    
    def generate_content_cached(self, **kwargs):
        # Create cache key from parameters
        cache_key = f"content:{hash(str(kwargs))}"
        
        # Try to get from cache
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Generate new content
        content = self.client.content.generate(**kwargs)
        
        # Cache the result
        redis_client.setex(
            cache_key, 
            self.cache_ttl, 
            json.dumps(content.to_dict())
        )
        
        return content

# Usage
cached_client = CachedLilyMediaClient(api_key="your_api_key")
content = cached_client.generate_content_cached(
    prompt="Create a post about productivity",
    platform="instagram"
)
```

## 🤝 Contributing

We welcome contributions to our SDKs! Here's how you can help:

### Reporting Issues

1. **Check existing issues** first
2. **Provide detailed information**:
   - SDK version
   - Programming language/runtime version
   - Operating system
   - Code snippet that reproduces the issue
   - Expected vs actual behavior

### Contributing Code

1. **Fork the repository**
2. **Create a feature branch**
3. **Write tests** for your changes
4. **Follow the coding standards**
5. **Submit a pull request**

### SDK Development Guidelines

#### Code Style
- Follow language-specific conventions
- Use meaningful variable names
- Add comprehensive docstrings/comments
- Include type hints where applicable

#### Testing
- Unit tests for all public methods
- Integration tests for API interactions
- Mock external dependencies
- Test error conditions

#### Documentation
- Update README files
- Add code examples
- Document breaking changes
- Update changelog

### Community SDK Support

If you maintain a community SDK:

1. **Submit a PR** to add it to this documentation
2. **Include these details**:
   - Repository URL
   - Current version
   - Maintenance status
   - Brief feature list
   - Installation instructions

3. **Maintain compatibility** with API v2.0
4. **Follow security best practices**
5. **Provide documentation and examples**

## 📋 SDK Checklist

When evaluating or creating an SDK, ensure it includes:

### Core Features ✅
- [ ] All API endpoints covered
- [ ] Authentication handling
- [ ] Error handling with specific exceptions
- [ ] Rate limit handling
- [ ] Request/response serialization
- [ ] Pagination support

### Advanced Features ✅
- [ ] Retry logic with exponential backoff
- [ ] Webhook signature verification
- [ ] File upload support
- [ ] Async/concurrent request support
- [ ] Configuration management
- [ ] Logging integration

### Developer Experience ✅
- [ ] Clear documentation
- [ ] Code examples
- [ ] Type definitions/hints
- [ ] IDE autocomplete support
- [ ] Comprehensive test suite
- [ ] Semantic versioning

### Production Ready ✅
- [ ] Security best practices
- [ ] Performance optimization
- [ ] Memory efficiency
- [ ] Thread safety (if applicable)
- [ ] Connection pooling
- [ ] Monitoring/metrics support

---

## 🔗 Related Documentation

- **[API Reference](./api-reference.md)** - Complete endpoint documentation
- **[Authentication](./authentication.md)** - API authentication guide
- **[Examples](./examples/)** - Practical integration examples
- **[Webhooks](./webhooks.md)** - Event-driven integrations

## 💡 Need Help?

- **SDK Documentation**: Each SDK has detailed docs in its repository
- **API Documentation**: [docs.lily-media.ai](https://docs.lily-media.ai)
- **Community Forum**: [community.lily-media.ai](https://community.lily-media.ai)
- **Discord**: [discord.gg/lily-media-ai](https://discord.gg/lily-media-ai)
- **GitHub Issues**: Report SDK-specific issues in respective repositories
- **Support Email**: sdk-support@lily-media.ai