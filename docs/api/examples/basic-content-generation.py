#!/usr/bin/env python3
"""
Basic Content Generation Example

Demonstrates how to use the Lily Media AI API for simple content generation.
This example shows the fundamental workflow of creating AI-powered social media content.

Prerequisites:
    pip install requests python-dotenv

Usage:
    python basic-content-generation.py
"""

import os
import requests
import json
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LilyMediaClient:
    """Basic client for Lily Media AI API."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.lily-media.ai/api"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "LilyMedia-BasicExample/1.0"
        })
    
    def generate_content(
        self, 
        prompt: str, 
        platform: str = "instagram",
        tone: str = "professional",
        length: str = "medium",
        include_hashtags: bool = True,
        include_cta: bool = False
    ) -> Dict[str, Any]:
        """
        Generate AI-powered content.
        
        Args:
            prompt: Description of content to generate
            platform: Target platform (instagram, twitter, linkedin, facebook)
            tone: Content tone (professional, casual, enthusiastic, informative)
            length: Content length (short, medium, long)
            include_hashtags: Whether to include hashtags
            include_cta: Whether to include call-to-action
            
        Returns:
            Dict containing generated content and metadata
        """
        
        payload = {
            "prompt": prompt,
            "platform": platform,
            "tone": tone,
            "length": length,
            "include_hashtags": include_hashtags,
            "include_cta": include_cta
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/content/generate",
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                print("Rate limit exceeded. Waiting before retry...")
                time.sleep(60)
                return self.generate_content(prompt, platform, tone, length, include_hashtags, include_cta)
            else:
                print(f"API Error: {e}")
                print(f"Response: {response.text}")
                raise
        
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            raise
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get current account information and quotas."""
        
        try:
            response = self.session.get(f"{self.base_url}/auth/me")
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to get account info: {e}")
            raise

def main():
    """Main example workflow."""
    
    # Get API key from environment
    api_key = os.getenv("LILY_API_KEY")
    if not api_key:
        print("❌ LILY_API_KEY environment variable not set")
        print("Please set your API key: export LILY_API_KEY='your_api_key_here'")
        return
    
    # Initialize client
    client = LilyMediaClient(api_key)
    
    print("🚀 Lily Media AI - Basic Content Generation Example")
    print("=" * 60)
    
    try:
        # Check account status
        print("📊 Checking account status...")
        account_info = client.get_account_info()
        
        print(f"✅ Connected as: {account_info.get('email', 'Unknown')}")
        print(f"📋 Plan: {account_info.get('plan', 'Unknown')}")
        
        quota = account_info.get('quota', {})
        print(f"📈 Content generations remaining: {quota.get('content_generations_remaining', 'Unknown')}")
        print()
        
        # Example 1: Basic content generation
        print("📝 Example 1: Basic Content Generation")
        print("-" * 40)
        
        basic_content = client.generate_content(
            prompt="Create a motivational Monday morning post about productivity",
            platform="instagram",
            tone="professional",
            length="medium"
        )
        
        print("Generated content:")
        print(f"📄 Content: {basic_content['content']}")
        print(f"📊 Character count: {basic_content.get('character_count', 'Unknown')}")
        print(f"🏷️ Hashtags: {basic_content.get('hashtags', [])}")
        print()
        
        # Example 2: Platform-specific content
        print("📝 Example 2: Platform-Specific Content")
        print("-" * 40)
        
        platforms = ["instagram", "twitter", "linkedin"]
        
        for platform in platforms:
            print(f"Generating content for {platform}...")
            
            content = client.generate_content(
                prompt="Share a tip about remote work productivity",
                platform=platform,
                tone="friendly",
                length="short" if platform == "twitter" else "medium"
            )
            
            print(f"✅ {platform.capitalize()}:")
            print(f"   Content: {content['content'][:100]}...")
            print(f"   Characters: {content.get('character_count', 'Unknown')}")
            print()
        
        # Example 3: Content with call-to-action
        print("📝 Example 3: Content with Call-to-Action")
        print("-" * 40)
        
        cta_content = client.generate_content(
            prompt="Announce a new product launch for eco-friendly water bottles",
            platform="instagram",
            tone="enthusiastic",
            length="medium",
            include_cta=True
        )
        
        print("Generated content with CTA:")
        print(f"📄 Content: {cta_content['content']}")
        print()
        
        # Example 4: Different tones comparison
        print("📝 Example 4: Tone Comparison")
        print("-" * 40)
        
        tones = ["professional", "casual", "enthusiastic", "informative"]
        base_prompt = "Explain the benefits of using social media scheduling tools"
        
        for tone in tones:
            content = client.generate_content(
                prompt=base_prompt,
                platform="linkedin",
                tone=tone,
                length="short"
            )
            
            print(f"🎭 {tone.capitalize()} tone:")
            print(f"   {content['content'][:150]}...")
            print()
        
        # Example 5: Content analysis
        print("📝 Example 5: Content Analysis")
        print("-" * 40)
        
        analysis_content = client.generate_content(
            prompt="Create a post about the importance of work-life balance",
            platform="instagram",
            tone="professional",
            length="long"
        )
        
        content_text = analysis_content['content']
        
        print("Content Analysis:")
        print(f"📊 Character count: {len(content_text)}")
        print(f"📝 Word count: {len(content_text.split())}")
        print(f"📱 Emoji count: {sum(1 for c in content_text if ord(c) > 127)}")
        print(f"🔤 Hashtag count: {content_text.count('#')}")
        print(f"🔗 Mention count: {content_text.count('@')}")
        
        # Check platform limits
        platform_limits = {
            "instagram": 2200,
            "twitter": 280,
            "linkedin": 3000,
            "facebook": 63206
        }
        
        print(f"📏 Platform compatibility:")
        for platform, limit in platform_limits.items():
            status = "✅" if len(content_text) <= limit else "❌"
            print(f"   {platform}: {status} ({len(content_text)}/{limit} chars)")
        
        print()
        print("🎉 Content generation examples completed successfully!")
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        raise

def demonstrate_error_handling():
    """Demonstrate proper error handling."""
    
    print("🔧 Error Handling Examples")
    print("=" * 40)
    
    # Example with invalid API key
    try:
        invalid_client = LilyMediaClient("invalid_key")
        invalid_client.generate_content("test prompt")
    except requests.exceptions.HTTPError as e:
        print(f"✅ Caught authentication error: {e}")
    
    # Example with invalid parameters
    try:
        client = LilyMediaClient(os.getenv("LILY_API_KEY"))
        client.generate_content(
            prompt="",  # Empty prompt should fail
            platform="invalid_platform"  # Invalid platform
        )
    except requests.exceptions.HTTPError as e:
        print(f"✅ Caught validation error: {e}")
    
    print("Error handling examples completed.")

if __name__ == "__main__":
    try:
        main()
        print("\n" + "=" * 60)
        demonstrate_error_handling()
        
    except KeyboardInterrupt:
        print("\n⏹️ Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()