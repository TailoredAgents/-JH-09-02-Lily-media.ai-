# Integration Examples

Practical code examples and tutorials for integrating with the Lily Media AI API.

## 🗂️ Examples Directory

### Quick Start Examples

- **[Basic Content Generation](./basic-content-generation.py)** - Simple content creation workflow
- **[Image Generation](./image-generation.py)** - AI-powered image creation
- **[Social Media Publishing](./social-media-publishing.py)** - Multi-platform post publishing
- **[Webhook Integration](./webhook-integration.py)** - Real-time event handling

### Advanced Workflows

- **[Automated Content Pipeline](./automated-content-pipeline.py)** - Complete automation workflow
- **[Bulk Content Creation](./bulk-content-creation.py)** - Batch processing content
- **[Analytics Dashboard](./analytics-dashboard.py)** - Performance tracking integration
- **[Multi-tenant SaaS](./multi-tenant-saas.py)** - Building SaaS applications

### Framework Integrations

- **[Flask Integration](./flask-integration/)** - Complete Flask web app
- **[Django Integration](./django-integration/)** - Django REST API integration
- **[Express.js Integration](./express-integration/)** - Node.js/Express example
- **[Next.js Integration](./nextjs-integration/)** - Full-stack React application

### Platform-Specific Examples

- **[Instagram Automation](./instagram-automation.py)** - Instagram-focused workflow
- **[Twitter/X Publishing](./twitter-publishing.py)** - Twitter/X integration
- **[LinkedIn Professional](./linkedin-professional.py)** - LinkedIn business content
- **[Multi-Platform Campaign](./multi-platform-campaign.py)** - Cross-platform campaigns

### Enterprise Examples

- **[Rate Limit Handling](./rate-limit-handling.py)** - Robust rate limit management
- **[Error Recovery](./error-recovery.py)** - Comprehensive error handling
- **[Security Best Practices](./security-examples.py)** - Production security patterns
- **[Monitoring & Observability](./monitoring-setup.py)** - Application monitoring

## 🏗️ Architecture Patterns

### Microservices Integration

Example of integrating Lily Media AI into a microservices architecture:

```python
# Content Service
class ContentService:
    def __init__(self, lily_api_key):
        self.lily_client = LilyMediaClient(lily_api_key)
    
    def generate_content(self, prompt, platform):
        return self.lily_client.content.generate(
            prompt=prompt,
            platform=platform
        )

# Publishing Service  
class PublishingService:
    def __init__(self, lily_api_key):
        self.lily_client = LilyMediaClient(lily_api_key)
    
    def publish_post(self, content, platforms):
        return self.lily_client.posts.create(
            content=content,
            platforms=platforms
        )

# Analytics Service
class AnalyticsService:
    def __init__(self, lily_api_key):
        self.lily_client = LilyMediaClient(lily_api_key)
    
    def get_performance_data(self, post_id):
        return self.lily_client.analytics.get_post_performance(post_id)
```

### Event-Driven Architecture

```python
# Event Publisher
class LilyWebhookHandler:
    def __init__(self, event_bus):
        self.event_bus = event_bus
    
    def handle_webhook(self, event_data):
        event_type = event_data['type']
        
        if event_type == 'post.published':
            self.event_bus.publish('content.published', event_data)
        elif event_type == 'content.generated':
            self.event_bus.publish('content.ready', event_data)

# Event Consumers
class NotificationService:
    def handle_content_published(self, event_data):
        # Send notification to user
        pass

class AnalyticsCollector:
    def handle_content_published(self, event_data):
        # Update analytics database
        pass
```

## 🔧 Common Use Cases

### 1. Content Calendar Automation

```python
from datetime import datetime, timedelta
import schedule
import time

class ContentCalendarAutomation:
    def __init__(self, lily_api_key):
        self.client = LilyMediaClient(lily_api_key)
        self.content_themes = {
            'monday': 'motivation',
            'wednesday': 'tips',
            'friday': 'celebration'
        }
    
    def generate_weekly_content(self):
        """Generate a week's worth of content."""
        base_date = datetime.now()
        
        for i in range(7):
            date = base_date + timedelta(days=i)
            day_name = date.strftime('%A').lower()
            
            if day_name in self.content_themes:
                theme = self.content_themes[day_name]
                
                # Generate content
                content = self.client.content.generate(
                    prompt=f"Create a {theme} post for {day_name}",
                    platform='instagram',
                    tone='professional'
                )
                
                # Schedule post
                self.client.posts.create(
                    content=content['content'],
                    platforms=['instagram', 'twitter'],
                    schedule={'publish_at': date.isoformat()}
                )

# Schedule automation
automation = ContentCalendarAutomation('your_api_key')
schedule.every().sunday.at("10:00").do(automation.generate_weekly_content)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 2. Brand-Consistent Content Generation

```python
class BrandContentGenerator:
    def __init__(self, lily_api_key, brand_guidelines):
        self.client = LilyMediaClient(lily_api_key)
        self.brand_guidelines = brand_guidelines
    
    def generate_branded_content(self, topic):
        """Generate content following brand guidelines."""
        
        # Create brand-specific prompt
        prompt = f"""
        Create content about {topic} following these brand guidelines:
        - Tone: {self.brand_guidelines['tone']}
        - Voice: {self.brand_guidelines['voice']}
        - Key messages: {', '.join(self.brand_guidelines['key_messages'])}
        - Hashtags: {', '.join(self.brand_guidelines['hashtags'])}
        - Call-to-action: {self.brand_guidelines['cta']}
        """
        
        content = self.client.content.generate(
            prompt=prompt,
            platform='instagram',
            include_cta=True
        )
        
        # Validate brand compliance
        if self.validate_brand_compliance(content['content']):
            return content
        else:
            # Regenerate with stricter guidelines
            return self.generate_branded_content_strict(topic)
    
    def validate_brand_compliance(self, content):
        """Validate content meets brand guidelines."""
        # Check for required elements
        required_elements = self.brand_guidelines.get('required_elements', [])
        for element in required_elements:
            if element.lower() not in content.lower():
                return False
        
        # Check for forbidden words
        forbidden_words = self.brand_guidelines.get('forbidden_words', [])
        for word in forbidden_words:
            if word.lower() in content.lower():
                return False
        
        return True

# Usage
brand_guidelines = {
    'tone': 'professional yet approachable',
    'voice': 'expert but friendly',
    'key_messages': ['innovation', 'quality', 'customer-first'],
    'hashtags': ['#YourBrand', '#Innovation', '#Quality'],
    'cta': 'Visit our website to learn more',
    'required_elements': ['quality', 'innovation'],
    'forbidden_words': ['cheap', 'basic', 'simple']
}

generator = BrandContentGenerator('your_api_key', brand_guidelines)
content = generator.generate_branded_content('new product launch')
```

### 3. A/B Testing Content

```python
import random
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ContentVariant:
    id: str
    content: str
    tone: str
    length: str
    cta_type: str

class ContentABTester:
    def __init__(self, lily_api_key):
        self.client = LilyMediaClient(lily_api_key)
        self.active_tests = {}
    
    def create_ab_test(self, topic: str, variants: int = 2) -> List[ContentVariant]:
        """Create multiple content variants for A/B testing."""
        
        tones = ['professional', 'casual', 'enthusiastic', 'informative']
        lengths = ['short', 'medium']
        cta_types = ['learn_more', 'shop_now', 'sign_up', 'download']
        
        variants_list = []
        
        for i in range(variants):
            # Randomize parameters
            tone = random.choice(tones)
            length = random.choice(lengths)
            cta_type = random.choice(cta_types)
            
            # Generate content variant
            content_result = self.client.content.generate(
                prompt=f"Create content about {topic}",
                platform='instagram',
                tone=tone,
                length=length,
                cta_type=cta_type
            )
            
            variant = ContentVariant(
                id=f"variant_{i+1}",
                content=content_result['content'],
                tone=tone,
                length=length,
                cta_type=cta_type
            )
            
            variants_list.append(variant)
        
        return variants_list
    
    def launch_ab_test(self, test_id: str, variants: List[ContentVariant], audience_split: float = 0.5):
        """Launch A/B test with audience splitting."""
        
        for i, variant in enumerate(variants):
            # Calculate schedule offset for staggered posting
            schedule_offset = i * 30  # 30 minutes apart
            
            post_result = self.client.posts.create(
                content=variant.content,
                platforms=['instagram'],
                schedule={
                    'publish_at': (datetime.now() + timedelta(minutes=schedule_offset)).isoformat()
                },
                metadata={
                    'ab_test_id': test_id,
                    'variant_id': variant.id,
                    'audience_split': audience_split / len(variants)
                }
            )
            
            # Track test
            self.active_tests[test_id] = {
                'variants': variants,
                'posts': [post_result['post_id']],
                'start_time': datetime.now()
            }
    
    def analyze_ab_test(self, test_id: str) -> Dict:
        """Analyze A/B test results."""
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        test_data = self.active_tests[test_id]
        results = {}
        
        for post_id in test_data['posts']:
            analytics = self.client.analytics.get_post_performance(post_id)
            
            results[post_id] = {
                'engagement_rate': analytics.get('engagement_rate', 0),
                'reach': analytics.get('reach', 0),
                'clicks': analytics.get('clicks', 0),
                'conversions': analytics.get('conversions', 0)
            }
        
        # Determine winner
        best_post = max(results.keys(), key=lambda x: results[x]['engagement_rate'])
        
        return {
            'test_id': test_id,
            'results': results,
            'winner': best_post,
            'confidence_level': self.calculate_confidence(results)
        }
    
    def calculate_confidence(self, results: Dict) -> float:
        """Calculate statistical confidence of A/B test results."""
        # Simplified confidence calculation
        # In production, use proper statistical testing
        values = [r['engagement_rate'] for r in results.values()]
        if len(values) < 2:
            return 0.0
        
        max_val = max(values)
        min_val = min(values)
        
        if min_val == 0:
            return 100.0
        
        difference_ratio = (max_val - min_val) / min_val
        return min(95.0, difference_ratio * 100)

# Usage
ab_tester = ContentABTester('your_api_key')

# Create variants
variants = ab_tester.create_ab_test("summer product collection", variants=3)

# Launch test
ab_tester.launch_ab_test("summer_collection_test", variants)

# Analyze after sufficient time
results = ab_tester.analyze_ab_test("summer_collection_test")
print(f"Winning variant: {results['winner']} with {results['confidence_level']:.1f}% confidence")
```

## 🎯 Best Practices Examples

Each example includes:
- ✅ Error handling and retry logic
- ✅ Rate limit management
- ✅ Security best practices
- ✅ Monitoring and logging
- ✅ Production-ready code patterns

## 📚 Getting Started

1. **Choose your use case** from the examples above
2. **Review the code** and understand the implementation
3. **Set up your environment** with required dependencies
4. **Configure your API credentials** securely
5. **Run the example** and customize for your needs

## 🔧 Prerequisites

Most examples require:

```bash
pip install requests python-dotenv schedule redis celery
```

Or for Node.js examples:
```bash
npm install axios dotenv node-schedule redis bull
```

## 🎨 Customization

All examples are designed to be:
- **Modular** - Use individual components
- **Extensible** - Add your own features
- **Configurable** - Adapt to your requirements
- **Production-ready** - Include proper error handling

---

## 🔗 Navigation

- **[Back to API Documentation](../README.md)**
- **[Authentication Guide](../authentication.md)**
- **[API Reference](../api-reference.md)**
- **[Webhooks Guide](../webhooks.md)**

## 💡 Need Help?

- **Documentation**: [docs.lily-media.ai](https://docs.lily-media.ai)
- **Example Repository**: [github.com/lily-media/api-examples](https://github.com/lily-media/api-examples)
- **Community**: [Discord](https://discord.gg/lily-media-ai)
- **Support**: api-support@lily-media.ai