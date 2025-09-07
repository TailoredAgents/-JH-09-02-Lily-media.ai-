#!/usr/bin/env python3
"""
Image Generation Example

Demonstrates how to use the Lily Media AI API for AI-powered image generation.
This example covers creating images, handling different styles and formats.

Prerequisites:
    pip install requests python-dotenv pillow

Usage:
    python image-generation.py
"""

import os
import requests
import json
import time
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import tempfile
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

class LilyImageClient:
    """Client for Lily Media AI image generation."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.lily-media.ai/api"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "LilyMedia-ImageExample/1.0"
        })
    
    def generate_image(
        self, 
        prompt: str,
        style: str = "photographic",
        aspect_ratio: str = "1:1",
        quality: str = "standard",
        size: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate AI-powered image.
        
        Args:
            prompt: Description of image to generate
            style: Image style (photographic, digital-art, cinematic, anime, 3d-model, etc.)
            aspect_ratio: Image aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            quality: Image quality (standard, high, ultra)
            size: Specific size override (e.g., "1024x1024")
            
        Returns:
            Dict containing image URL, metadata, and generation info
        """
        
        payload = {
            "prompt": prompt,
            "style": style,
            "aspect_ratio": aspect_ratio,
            "quality": quality
        }
        
        if size:
            payload["size"] = size
        
        try:
            response = self.session.post(
                f"{self.base_url}/images/generate",
                json=payload,
                timeout=60  # Image generation can take longer
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                print("Rate limit exceeded. Waiting before retry...")
                time.sleep(60)
                return self.generate_image(prompt, style, aspect_ratio, quality, size)
            elif response.status_code == 400:
                error_data = response.json()
                if 'content_policy_violation' in error_data.get('error', {}).get('code', ''):
                    print(f"Content policy violation: {error_data['error']['message']}")
                    return None
                else:
                    print(f"Validation error: {response.text}")
                    raise
            else:
                print(f"API Error: {e}")
                print(f"Response: {response.text}")
                raise
        
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            raise
    
    def download_image(self, image_url: str, filename: Optional[str] = None) -> str:
        """
        Download generated image to local file.
        
        Args:
            image_url: URL of the generated image
            filename: Local filename (auto-generated if None)
            
        Returns:
            Path to downloaded file
        """
        
        if not filename:
            # Generate filename from URL
            parsed_url = urlparse(image_url)
            filename = os.path.basename(parsed_url.path)
            if not filename:
                filename = f"generated_image_{int(time.time())}.jpg"
        
        try:
            response = self.session.get(image_url, timeout=30)
            response.raise_for_status()
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            return filename
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to download image: {e}")
            raise
    
    def get_image_info(self, image_id: str) -> Dict[str, Any]:
        """Get information about a generated image."""
        
        try:
            response = self.session.get(f"{self.base_url}/images/{image_id}")
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to get image info: {e}")
            raise
    
    def get_quota_info(self) -> Dict[str, Any]:
        """Get image generation quota information."""
        
        try:
            response = self.session.get(f"{self.base_url}/auth/me")
            response.raise_for_status()
            data = response.json()
            return data.get('quota', {})
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to get quota info: {e}")
            raise

def display_image_info(image_data: Dict[str, Any]):
    """Display information about generated image."""
    
    print(f"🖼️ Image Generated Successfully!")
    print(f"   URL: {image_data.get('image_url', 'N/A')}")
    print(f"   Alt Text: {image_data.get('alt_text', 'N/A')}")
    
    dimensions = image_data.get('dimensions', {})
    if dimensions:
        print(f"   Dimensions: {dimensions.get('width')}x{dimensions.get('height')}")
    
    print(f"   Image ID: {image_data.get('image_id', 'N/A')}")
    
    generation_time = image_data.get('generation_time_ms')
    if generation_time:
        print(f"   Generation Time: {generation_time}ms")

def main():
    """Main image generation workflow."""
    
    # Get API key from environment
    api_key = os.getenv("LILY_API_KEY")
    if not api_key:
        print("❌ LILY_API_KEY environment variable not set")
        print("Please set your API key: export LILY_API_KEY='your_api_key_here'")
        return
    
    # Initialize client
    client = LilyImageClient(api_key)
    
    print("🎨 Lily Media AI - Image Generation Examples")
    print("=" * 60)
    
    try:
        # Check quota status
        print("📊 Checking image generation quota...")
        quota = client.get_quota_info()
        remaining = quota.get('image_generations_remaining', 'Unknown')
        print(f"✅ Images remaining this month: {remaining}")
        print()
        
        # Example 1: Basic image generation
        print("🖼️ Example 1: Basic Image Generation")
        print("-" * 40)
        
        basic_image = client.generate_image(
            prompt="A serene mountain landscape at sunset with a lake reflection",
            style="photographic",
            aspect_ratio="16:9",
            quality="high"
        )
        
        if basic_image:
            display_image_info(basic_image)
            
            # Download the image
            filename = client.download_image(basic_image['image_url'], "mountain_sunset.jpg")
            print(f"✅ Image downloaded as: {filename}")
        print()
        
        # Example 2: Different styles comparison
        print("🎨 Example 2: Style Comparison")
        print("-" * 40)
        
        styles = [
            ("photographic", "Professional photography style"),
            ("digital-art", "Digital artwork style"),
            ("cinematic", "Movie-like cinematic style"),
            ("minimalist", "Clean minimalist style")
        ]
        
        base_prompt = "A modern office workspace with laptop and coffee cup"
        
        for style, description in styles:
            print(f"Generating {style} style...")
            
            image_data = client.generate_image(
                prompt=base_prompt,
                style=style,
                aspect_ratio="1:1",
                quality="standard"
            )
            
            if image_data:
                print(f"✅ {description}")
                print(f"   URL: {image_data['image_url']}")
                filename = client.download_image(image_data['image_url'], f"workspace_{style}.jpg")
                print(f"   Downloaded: {filename}")
            else:
                print(f"❌ Failed to generate {style} image")
            print()
        
        # Example 3: Different aspect ratios
        print("📐 Example 3: Aspect Ratio Examples")
        print("-" * 40)
        
        aspect_ratios = [
            ("1:1", "Square - Perfect for Instagram posts"),
            ("16:9", "Landscape - Great for YouTube thumbnails"),
            ("9:16", "Portrait - Ideal for Instagram Stories"),
            ("4:3", "Classic - Traditional photo format")
        ]
        
        for ratio, description in aspect_ratios:
            print(f"Generating {ratio} aspect ratio...")
            
            image_data = client.generate_image(
                prompt="A vibrant tropical beach scene with palm trees",
                style="photographic",
                aspect_ratio=ratio,
                quality="high"
            )
            
            if image_data:
                dimensions = image_data.get('dimensions', {})
                print(f"✅ {description}")
                print(f"   Dimensions: {dimensions.get('width')}x{dimensions.get('height')}")
                filename = client.download_image(image_data['image_url'], f"beach_{ratio.replace(':', 'x')}.jpg")
                print(f"   Downloaded: {filename}")
            print()
        
        # Example 4: Social media optimized images
        print("📱 Example 4: Social Media Optimized Images")
        print("-" * 40)
        
        social_prompts = [
            {
                "platform": "Instagram Post",
                "prompt": "Flat lay of healthy breakfast with avocado toast, coffee, and fruits",
                "aspect_ratio": "1:1",
                "style": "photographic"
            },
            {
                "platform": "Instagram Story",
                "prompt": "Behind-the-scenes office workspace with motivational quote overlay space",
                "aspect_ratio": "9:16", 
                "style": "minimalist"
            },
            {
                "platform": "LinkedIn Banner",
                "prompt": "Professional team collaboration in modern office environment",
                "aspect_ratio": "16:9",
                "style": "cinematic"
            },
            {
                "platform": "Twitter Header",
                "prompt": "Abstract technology network connections with blue and purple gradient",
                "aspect_ratio": "16:9",
                "style": "digital-art"
            }
        ]
        
        for config in social_prompts:
            print(f"Creating image for {config['platform']}...")
            
            image_data = client.generate_image(
                prompt=config['prompt'],
                style=config['style'],
                aspect_ratio=config['aspect_ratio'],
                quality="high"
            )
            
            if image_data:
                platform_name = config['platform'].lower().replace(' ', '_')
                filename = client.download_image(image_data['image_url'], f"{platform_name}.jpg")
                
                print(f"✅ {config['platform']} image created")
                print(f"   Style: {config['style']}")
                print(f"   Aspect Ratio: {config['aspect_ratio']}")
                print(f"   Downloaded: {filename}")
            print()
        
        # Example 5: Batch image generation
        print("🔄 Example 5: Batch Image Generation")
        print("-" * 40)
        
        batch_prompts = [
            "Product photography of eco-friendly water bottle on white background",
            "Cozy coffee shop interior with warm lighting and wooden furniture",
            "Team of diverse professionals in business meeting",
            "Modern smartphone displaying social media app interface",
            "Fresh ingredients for healthy cooking laid out on marble counter"
        ]
        
        print(f"Generating {len(batch_prompts)} images in batch...")
        batch_results = []
        
        for i, prompt in enumerate(batch_prompts, 1):
            print(f"Generating image {i}/{len(batch_prompts)}...")
            
            image_data = client.generate_image(
                prompt=prompt,
                style="photographic",
                aspect_ratio="4:3",
                quality="standard"
            )
            
            if image_data:
                filename = client.download_image(image_data['image_url'], f"batch_image_{i}.jpg")
                batch_results.append({
                    'prompt': prompt,
                    'filename': filename,
                    'url': image_data['image_url']
                })
                print(f"✅ Downloaded: {filename}")
            
            # Add delay to respect rate limits
            time.sleep(2)
        
        print(f"\n📊 Batch generation completed: {len(batch_results)}/{len(batch_prompts)} successful")
        
        # Example 6: Image analysis and metadata
        print("\n🔍 Example 6: Image Analysis")
        print("-" * 40)
        
        analysis_image = client.generate_image(
            prompt="Professional headshot of confident businesswoman in modern office",
            style="photographic",
            aspect_ratio="1:1",
            quality="ultra"
        )
        
        if analysis_image:
            print("Generated image for analysis:")
            display_image_info(analysis_image)
            
            # Download and analyze
            filename = client.download_image(analysis_image['image_url'], "analysis_image.jpg")
            
            # Check file size
            file_size = os.path.getsize(filename)
            print(f"📁 File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
            
            # Platform suitability
            print("📱 Platform suitability:")
            platforms = {
                "Instagram": {"max_size": 30 * 1024 * 1024, "recommended_ratio": "1:1"},
                "Twitter": {"max_size": 5 * 1024 * 1024, "recommended_ratio": "16:9"},
                "LinkedIn": {"max_size": 4 * 1024 * 1024, "recommended_ratio": "1.91:1"},
                "Facebook": {"max_size": 10 * 1024 * 1024, "recommended_ratio": "1.91:1"}
            }
            
            dimensions = analysis_image.get('dimensions', {})
            current_ratio = dimensions.get('width', 0) / dimensions.get('height', 1) if dimensions else 1
            
            for platform, specs in platforms.items():
                size_ok = file_size <= specs['max_size']
                size_status = "✅" if size_ok else "❌"
                print(f"   {platform}: {size_status} Size: {file_size/1024/1024:.1f}MB/{specs['max_size']/1024/1024:.0f}MB")
        
        print("\n🎉 Image generation examples completed successfully!")
        print(f"📁 All images saved in current directory")
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        raise

def demonstrate_advanced_features():
    """Demonstrate advanced image generation features."""
    
    api_key = os.getenv("LILY_API_KEY")
    if not api_key:
        return
    
    client = LilyImageClient(api_key)
    
    print("\n🚀 Advanced Features Demo")
    print("=" * 40)
    
    try:
        # Advanced prompt engineering
        print("🔧 Advanced Prompt Engineering:")
        
        advanced_prompts = [
            {
                "name": "Detailed Style Specification",
                "prompt": "Professional product photography, studio lighting, white background, Canon 5D Mark IV, 85mm lens, f/2.8, commercial photography style, high-end luxury watch"
            },
            {
                "name": "Mood and Atmosphere",
                "prompt": "Cozy autumn coffee shop, warm golden hour lighting, steam rising from coffee cup, soft focus background, hygge aesthetic, Danish interior design"
            },
            {
                "name": "Artistic Direction",
                "prompt": "Minimalist workspace, Scandinavian design, natural wood textures, soft shadows, architectural photography, Kinfolk magazine style"
            }
        ]
        
        for config in advanced_prompts:
            print(f"\n{config['name']}:")
            print(f"Prompt: {config['prompt'][:60]}...")
            
            image_data = client.generate_image(
                prompt=config['prompt'],
                style="photographic",
                aspect_ratio="4:3",
                quality="ultra"
            )
            
            if image_data:
                filename = client.download_image(image_data['image_url'], 
                                               f"advanced_{config['name'].lower().replace(' ', '_')}.jpg")
                print(f"✅ Generated: {filename}")
        
        print("\n🔍 Quality Comparison:")
        
        # Generate same image in different qualities
        base_prompt = "Modern minimalist living room with natural light"
        qualities = ["standard", "high", "ultra"]
        
        for quality in qualities:
            print(f"Generating {quality} quality...")
            
            image_data = client.generate_image(
                prompt=base_prompt,
                style="photographic",
                aspect_ratio="16:9",
                quality=quality
            )
            
            if image_data:
                filename = client.download_image(image_data['image_url'], f"quality_{quality}.jpg")
                file_size = os.path.getsize(filename)
                
                print(f"✅ {quality.capitalize()} quality:")
                print(f"   File size: {file_size:,} bytes")
                print(f"   Generation time: {image_data.get('generation_time_ms', 'N/A')}ms")
        
    except Exception as e:
        print(f"❌ Advanced features demo failed: {e}")

if __name__ == "__main__":
    try:
        main()
        demonstrate_advanced_features()
        
    except KeyboardInterrupt:
        print("\n⏹️ Image generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()