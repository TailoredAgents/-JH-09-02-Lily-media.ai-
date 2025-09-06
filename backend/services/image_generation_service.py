"""
Enhanced xAI Grok 2 Vision Image Generation Service

This service uses xAI Grok 2 Vision model through OpenAI-compatible API 
for superior social media content creation and multi-turn editing capabilities.

Implements Grok 4's recommendations:
- Enhanced post-processing with aspect ratio enforcement  
- Platform-specific image optimization
- Quality checking and retry logic
- Alt-text generation for accessibility
- Structured prompt templates with quality boosters
"""
import asyncio
import base64
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator, Union, Tuple
from datetime import datetime
from pathlib import Path
import uuid

from openai import OpenAI, AsyncOpenAI
from backend.core.config import get_settings
from backend.services.image_processing_service import image_processing_service
from backend.services.alt_text_service import alt_text_service

settings = get_settings()
logger = logging.getLogger(__name__)

class ImageGenerationService:
    """
    Enhanced image generation service using OpenAI's Responses API with image_generation tool
    for superior social media content creation with real-time streaming and multi-turn editing capabilities.
    """
    
    def __init__(self):
        # Check if xAI API key is configured
        if not settings.xai_api_key:
            logger.warning("xAI API key not configured. Image generation will be unavailable.")
            self.client = None
            self.async_client = None
        else:
            # Use xAI Grok for image generation
            try:
                self.client = OpenAI(
                    api_key=settings.xai_api_key,
                    base_url="https://api.x.ai/v1"
                )
                self.async_client = AsyncOpenAI(
                    api_key=settings.xai_api_key,
                    base_url="https://api.x.ai/v1"
                )
                logger.info("xAI image generation service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize xAI image generation service: {e}")
                self.client = None
                self.async_client = None
        
        # Model-to-API mapping for multi-model support
        self.model_mapping = {
            "grok2": "grok-2-image",
            "grok2_basic": "grok-2-image",
            "grok2_premium": "grok-2-image", 
            "gpt_image_1": "dall-e-3"  # This will use OpenAI client
        }
        
        # Initialize OpenAI client for GPT Image 1 model
        self.openai_client = None
        self.openai_async_client = None
        if settings.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=settings.openai_api_key)
                self.openai_async_client = AsyncOpenAI(api_key=settings.openai_api_key)
                logger.info("OpenAI client initialized for GPT Image 1 model")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        
        # Platform-specific optimization prompts
        self.platform_styles = {
            "twitter": "modern, clean, minimalist design suitable for Twitter posts, 16:9 or square aspect ratio",
            "instagram": "vibrant, visually stunning, Instagram-optimized design with excellent composition",
            "facebook": "engaging, social media friendly, Facebook-style design that captures attention",
            "tiktok": "trendy, youthful, dynamic design perfect for TikTok content with bold visuals",
            "youtube": "professional thumbnail design with bold text and engaging visuals"
        }
        
        # Quality presets (Note: xAI ignores size/quality, these are for metadata only)
        # xAI always generates 1024x768 images regardless of requested size
        self.quality_presets = {
            "draft": {"quality": "low", "size": "1024x1024"},
            "standard": {"quality": "medium", "size": "1024x1024"},
            "premium": {"quality": "high", "size": "1024x1536"},
            "story": {"quality": "high", "size": "1024x1792"},
            "banner": {"quality": "high", "size": "1536x1024"}
        }

    def _enhance_prompt_for_platform(self, prompt: str, platform: str, 
                                   content_context: Optional[str] = None,
                                   industry_context: Optional[str] = None,
                                   tone: str = "professional") -> str:
        """Enhance the prompt with platform-specific optimizations."""
        
        # Base enhancement
        enhanced_prompt = f"Create a high-quality image: {prompt}"
        
        # Add platform styling
        if platform in self.platform_styles:
            enhanced_prompt += f" Style: {self.platform_styles[platform]}"
        
        # Add content context
        if content_context:
            enhanced_prompt += f" Content context: {content_context[:200]}"
        
        # Add industry context
        if industry_context:
            enhanced_prompt += f" Industry: {industry_context[:100]}"
        
        # Add tone guidance
        tone_styles = {
            "professional": "polished, sophisticated, business-appropriate",
            "casual": "relaxed, approachable, friendly",
            "humorous": "fun, playful, engaging with subtle humor",
            "inspiring": "motivational, uplifting, empowering",
            "educational": "clear, informative, easy to understand"
        }
        
        if tone in tone_styles:
            enhanced_prompt += f" Tone: {tone_styles[tone]}"
        
        return enhanced_prompt
    
    def _enhance_prompt_with_quality_boosters(self, prompt: str, platform: str,
                                            content_context: Optional[str] = None,
                                            industry_context: Optional[str] = None,
                                            tone: str = "professional") -> str:
        """Enhance prompt with Grok 4's quality boosters and structured templates."""
        
        # Start with platform optimization
        enhanced_prompt = self._enhance_prompt_for_platform(
            prompt, platform, content_context, industry_context, tone
        )
        
        # Add Grok 4's quality boosters
        quality_boosters = [
            "professional photography quality",
            "sharp focus and crisp details",
            "optimal lighting and composition",
            "vibrant colors with perfect saturation",
            "high resolution commercial quality",
            "visually striking and engaging"
        ]
        
        # Platform-specific quality enhancements
        platform_quality = {
            "instagram": [
                "Instagram-worthy aesthetic",
                "perfect for social media engagement",
                "visually appealing thumbnail",
                "scroll-stopping visual impact"
            ],
            "twitter": [
                "Twitter timeline optimized",
                "clear and readable at small sizes",
                "eye-catching for quick consumption",
                "professional social media quality"
            ],
            "facebook": [
                "Facebook feed optimized",
                "engaging for social sharing",
                "clear call-to-action visual",
                "community-friendly design"
            ],
            "linkedin": [
                "LinkedIn professional standards",
                "corporate presentation quality",
                "business networking appropriate",
                "thought leadership visual"
            ],
            "tiktok": [
                "TikTok trending aesthetic",
                "mobile-first design",
                "Gen-Z appealing visuals",
                "viral content potential"
            ]
        }
        
        # Add general quality boosters
        enhanced_prompt += f". Quality requirements: {', '.join(quality_boosters[:3])}"
        
        # Add platform-specific quality boosters
        if platform in platform_quality:
            platform_boosters = platform_quality[platform][:2]
            enhanced_prompt += f". Platform optimization: {', '.join(platform_boosters)}"
        
        # Add technical specifications
        technical_specs = [
            "studio lighting setup",
            "professional camera angles",
            "color-corrected and post-processed",
            "marketing campaign quality"
        ]
        
        enhanced_prompt += f". Technical specs: {', '.join(technical_specs[:2])}"
        
        # Add final quality directive
        enhanced_prompt += ". Ensure maximum visual impact and professional presentation quality."
        
        return enhanced_prompt

    def build_prompt_with_user_settings(self, 
                                      base_prompt: str, 
                                      user_settings: Optional[Dict[str, Any]] = None,
                                      platform: str = "instagram") -> str:
        """
        Enhance a base prompt with user's industry presets and brand parameters.
        
        Args:
            base_prompt: The original prompt describing what to generate
            user_settings: User's settings from UserSetting model
            platform: Target social media platform
            
        Returns:
            Enhanced prompt incorporating user's style preferences
        """
        if not user_settings:
            return self._enhance_prompt_with_context(base_prompt, platform)
        
        enhanced_prompt = base_prompt
        
        # Add industry-specific styling
        industry_presets = {
            "restaurant": {
                "style": "warm, appetizing, professional food photography",
                "lighting": "golden hour, natural lighting",
                "composition": "appetizing close-up, rule of thirds",
                "mood": "inviting, delicious, mouth-watering"
            },
            "law_firm": {
                "style": "professional, authoritative, clean corporate design",
                "lighting": "bright, even office lighting",
                "composition": "structured, balanced, sophisticated",
                "mood": "trustworthy, professional, established"
            },
            "tech_startup": {
                "style": "modern, innovative, futuristic design",
                "lighting": "cool tones, gradient backgrounds, tech-inspired",
                "composition": "dynamic, cutting-edge, minimal",
                "mood": "innovative, forward-thinking, disruptive"
            },
            "healthcare": {
                "style": "clean, medical, trustworthy professional design",
                "lighting": "bright, clean, sterile white backgrounds",
                "composition": "organized, clear, medical-grade quality",
                "mood": "caring, professional, reliable"
            },
            "retail": {
                "style": "commercial product photography, lifestyle branding",
                "lighting": "bright, even product lighting, lifestyle ambiance",
                "composition": "product-focused, lifestyle context, commercial quality",
                "mood": "desirable, lifestyle-oriented, aspirational"
            },
            "fitness": {
                "style": "energetic, dynamic, motivational fitness imagery",
                "lighting": "dramatic gym lighting, natural outdoor light",
                "composition": "action-oriented, motivational, strength-focused",
                "mood": "energetic, motivational, powerful"
            }
        }
        
        industry_type = user_settings.get("industry_type", "general")
        if industry_type in industry_presets:
            preset = industry_presets[industry_type]
            enhanced_prompt += f" Style: {preset['style']}. {preset['lighting']}. {preset['composition']}. Mood: {preset['mood']}."
        
        # Add visual style preferences
        visual_style = user_settings.get("visual_style", "modern")
        style_descriptors = {
            "modern": "sleek, contemporary, minimalist, current design trends",
            "classic": "timeless, elegant, traditional, refined aesthetics",
            "minimalist": "clean, simple, uncluttered, essential elements only",
            "bold": "striking, vibrant, high-contrast, attention-grabbing",
            "playful": "fun, creative, colorful, engaging and lighthearted",
            "luxury": "premium, sophisticated, high-end, exclusive quality"
        }
        if visual_style in style_descriptors:
            enhanced_prompt += f" Visual style: {style_descriptors[visual_style]}."
        
        # Add brand colors
        primary_color = user_settings.get("primary_color", "#3b82f6")
        secondary_color = user_settings.get("secondary_color", "#10b981")
        if primary_color != "#3b82f6":  # Only add if user customized
            enhanced_prompt += f" Use brand color scheme with primary color {primary_color}"
            if secondary_color != "#10b981":
                enhanced_prompt += f" and secondary accent {secondary_color}"
            enhanced_prompt += "."
        
        # Add brand keywords to emphasize
        brand_keywords = user_settings.get("brand_keywords", [])
        if brand_keywords:
            keywords_str = ", ".join(brand_keywords[:3])  # Limit to 3 most important
            enhanced_prompt += f" Emphasize: {keywords_str}."
        
        # Add mood descriptors
        image_mood = user_settings.get("image_mood", ["professional", "clean"])
        if image_mood:
            mood_str = ", ".join(image_mood)
            enhanced_prompt += f" Overall mood: {mood_str}."
        
        # Add things to avoid
        avoid_list = user_settings.get("avoid_list", [])
        if avoid_list:
            avoid_str = ", ".join(avoid_list[:5])  # Limit to prevent prompt bloat
            enhanced_prompt += f" Avoid: {avoid_str}."
        
        # Add image quality and style preferences
        preferred_style = user_settings.get("preferred_image_style", {})
        if preferred_style:
            lighting = preferred_style.get("lighting", "natural")
            composition = preferred_style.get("composition", "rule_of_thirds")
            color_temp = preferred_style.get("color_temperature", "neutral")
            enhanced_prompt += f" Lighting: {lighting}. Composition: {composition}. Color temperature: {color_temp}."
        
        # Add quality specification
        quality = user_settings.get("image_quality", "high")
        quality_specs = {
            "low": "draft quality, quick generation",
            "medium": "good quality, balanced detail",
            "high": "high resolution, detailed, professional quality",
            "ultra": "ultra-high resolution, maximum detail, premium quality"
        }
        enhanced_prompt += f" Quality: {quality_specs.get(quality, 'high resolution, professional quality')}."
        
        return enhanced_prompt

    async def generate_image(self, 
                           prompt: str,
                           platform: str = "instagram",
                           quality_preset: str = "standard",
                           model: str = "grok2",
                           content_context: Optional[str] = None,
                           industry_context: Optional[str] = None,
                           tone: str = "professional",
                           custom_options: Optional[Dict[str, Any]] = None,
                           enable_post_processing: bool = True,
                           generate_alt_text: bool = True,
                           max_retries: int = 2) -> Dict[str, Any]:
        """
        Generate a single image with enhanced post-processing and accessibility features.
        
        Implements Grok 4's recommendations:
        - Enhanced prompt templates with quality boosters
        - Platform-specific post-processing and optimization
        - Quality validation and retry logic
        - Alt-text generation for accessibility compliance
        
        Args:
            prompt: Base image description
            platform: Target social media platform
            quality_preset: Quality/size preset (draft, standard, premium, story, banner)
            model: AI model to use (grok2, grok2_basic, grok2_premium, gpt_image_1)
            content_context: Additional context about the content
            industry_context: Industry-specific context
            tone: Desired tone for the image
            custom_options: Custom tool options (size, quality, format, etc.)
            enable_post_processing: Apply platform-specific post-processing
            generate_alt_text: Generate accessibility alt-text
            max_retries: Maximum retry attempts for quality validation
        
        Returns:
            Dict containing processed image data, alt-text, quality metrics, and metadata
        """
        # Check if service is available
        if not self.async_client:
            return {
                "status": "error",
                "error": "Image generation service is unavailable. Please check xAI API key configuration.",
                "image_data": None,
                "metadata": {
                    "platform": platform,
                    "quality_preset": quality_preset,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        try:
            # Enhance prompt with Grok 4's quality boosters
            enhanced_prompt = self._enhance_prompt_with_quality_boosters(
                prompt, platform, content_context, industry_context, tone
            )
            
            # Get quality preset settings
            preset_config = self.quality_presets.get(quality_preset, self.quality_presets["standard"])
            
            # Prepare Grok-2 Image parameters
            tool_options = {
                "type": "image_generation",
                "size": preset_config.get("size", "1024x1024"),
                "quality": preset_config.get("quality", "standard")
            }
            
            # Override with custom options if provided
            if custom_options:
                tool_options.update(custom_options)
            
            # Model routing: Select appropriate API client and model based on requested model
            selected_model, client_to_use = self._select_model_and_client(model)
            
            # Generate image using the selected model
            response = await client_to_use.images.generate(
                model=selected_model,
                prompt=enhanced_prompt,
                n=1,
                response_format="b64_json"  # Get base64 directly to avoid extra download step
            )
            
            # Extract image data from xAI response
            if not response.data or len(response.data) == 0:
                raise Exception("No image data returned from xAI Grok image generation")
            
            # Get the generated image
            image_data = response.data[0]
            
            # Check if we get a URL or base64 data
            if hasattr(image_data, 'b64_json') and image_data.b64_json:
                image_base64 = image_data.b64_json
            elif hasattr(image_data, 'url') and image_data.url:
                # Download image and convert to base64
                import httpx
                async with httpx.AsyncClient() as client:
                    img_response = await client.get(image_data.url)
                    if img_response.status_code == 200:
                        image_base64 = base64.b64encode(img_response.content).decode('utf-8')
                    else:
                        raise Exception(f"Failed to download generated image: {img_response.status_code}")
            else:
                raise Exception("No valid image data format returned from xAI")
            
            # Convert base64 to bytes for post-processing
            raw_image_bytes = base64.b64decode(image_base64)
            
            # Apply post-processing if enabled
            processed_image_bytes = raw_image_bytes
            processing_metadata = {}
            
            if enable_post_processing:
                try:
                    processed_image_bytes, processing_metadata = image_processing_service.resize_for_platform(
                        raw_image_bytes, platform, "default", quality_preset
                    )
                    logger.info(f"Post-processing completed for {platform} with preset {quality_preset}")
                except Exception as e:
                    logger.warning(f"Post-processing failed: {e}, using original image")
                    processing_metadata = {"error": str(e), "fallback": True}
            
            # Validate image quality
            quality_metrics = image_processing_service.validate_image_quality(processed_image_bytes)
            
            # Retry if quality is too low (score < 50) and retries available
            retry_count = 0
            while (quality_metrics.get("quality_score", 100) < 50 and 
                   retry_count < max_retries and 
                   "error" not in quality_metrics):
                
                logger.info(f"Image quality too low (score: {quality_metrics.get('quality_score')}), retrying... ({retry_count + 1}/{max_retries})")
                retry_count += 1
                
                # Add quality improvement to prompt
                retry_prompt = enhanced_prompt + ". Generate with higher resolution, better clarity, and professional quality."
                
                # Retry generation
                response = await self.async_client.images.generate(
                    model="grok-2-image",
                    prompt=retry_prompt,
                    n=1,
                    response_format="b64_json"
                )
                
                if response.data and len(response.data) > 0:
                    retry_image_data = response.data[0]
                    if hasattr(retry_image_data, 'b64_json') and retry_image_data.b64_json:
                        image_base64 = retry_image_data.b64_json
                        raw_image_bytes = base64.b64decode(image_base64)
                        
                        # Re-process and re-validate
                        if enable_post_processing:
                            try:
                                processed_image_bytes, processing_metadata = image_processing_service.resize_for_platform(
                                    raw_image_bytes, platform, "default", quality_preset
                                )
                            except Exception as e:
                                logger.warning(f"Retry post-processing failed: {e}")
                        
                        quality_metrics = image_processing_service.validate_image_quality(processed_image_bytes)
            
            # Convert processed image back to base64
            final_image_base64 = base64.b64encode(processed_image_bytes).decode('utf-8')
            
            # Generate alt-text if enabled
            alt_text_data = {}
            if generate_alt_text:
                try:
                    alt_text_data = await alt_text_service.generate_alt_text(
                        processed_image_bytes,
                        context=content_context or prompt,
                        platform=platform
                    )
                    logger.info(f"Alt-text generated: {alt_text_data.get('status')}")
                except Exception as e:
                    logger.warning(f"Alt-text generation failed: {e}")
                    alt_text_data = {
                        "alt_text": "Generated image",
                        "status": "error",
                        "error": str(e)
                    }
            
            # Generate unique filename and ID
            image_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{platform}_{timestamp}_{image_id[:8]}.png"
            
            return {
                "status": "success",
                "image_id": image_id,
                "response_id": image_id,
                "image_base64": final_image_base64,
                "image_data_url": f"data:image/png;base64,{final_image_base64}",
                "filename": filename,
                "prompt": {
                    "original": prompt,
                    "enhanced": enhanced_prompt,
                    "revised": enhanced_prompt
                },
                "alt_text": alt_text_data.get("alt_text", ""),
                "accessibility": {
                    "alt_text": alt_text_data.get("alt_text", ""),
                    "alt_text_status": alt_text_data.get("status", "not_generated"),
                    "alt_text_length": alt_text_data.get("length", 0),
                    "platform_optimized": alt_text_data.get("platform") == platform
                },
                "quality": {
                    "score": quality_metrics.get("quality_score", 0),
                    "issues": quality_metrics.get("issues", []),
                    "recommendations": quality_metrics.get("recommendations", []),
                    "retry_count": retry_count,
                    "final_attempt": retry_count >= max_retries
                },
                "processing": {
                    "post_processed": enable_post_processing,
                    "processing_metadata": processing_metadata,
                    "original_size": processing_metadata.get("original_size"),
                    "final_size": processing_metadata.get("processed_size"),
                    "compression_ratio": processing_metadata.get("compression_ratio", 1.0)
                },
                "metadata": {
                    "platform": platform,
                    "quality_preset": quality_preset,
                    "tool_options": tool_options,
                    "model": "grok-2-image",
                    "generated_at": datetime.now().isoformat(),
                    "actual_size": "1024x768",
                    "requested_size": tool_options.get("size", "1024x1024"),
                    "content_context": content_context,
                    "industry_context": industry_context,
                    "tone": tone,
                    "enhancements_applied": {
                        "post_processing": enable_post_processing,
                        "alt_text_generation": generate_alt_text,
                        "quality_validation": True,
                        "retry_logic": max_retries > 0
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Image generation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "prompt": prompt,
                "platform": platform
            }

    async def edit_image(self,
                        edit_prompt: str,
                        previous_response_id: Optional[str] = None,
                        previous_image_id: Optional[str] = None,
                        platform: str = "instagram",
                        quality_preset: str = "standard") -> Dict[str, Any]:
        """
        Edit an existing image using multi-turn capabilities.
        
        Args:
            edit_prompt: Description of how to edit the image
            previous_response_id: ID of previous response to continue from
            previous_image_id: ID of specific image to edit
            platform: Target platform
            quality_preset: Quality preset
        
        Returns:
            Dict containing edited image data and metadata
        """
        # Check if service is available
        if not self.async_client:
            return {
                "status": "error",
                "error": "Image editing service is unavailable. Please check xAI API key configuration.",
                "image_data": None,
                "metadata": {
                    "platform": platform,
                    "quality_preset": quality_preset,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        try:
            # Prepare tool options
            tool_options = self.quality_presets.get(quality_preset, self.quality_presets["standard"])
            
            if previous_response_id:
                # Continue from previous response
                response = await asyncio.to_thread(
                    self.client.responses.create,
                    model="grok-2-image",
                    previous_response_id=previous_response_id,
                    input=f"Edit the image: {edit_prompt}",
                    tools=[{
                        "type": "image_generation",
                        **tool_options
                    }]
                )
            elif previous_image_id:
                # Edit specific image by ID
                response = await asyncio.to_thread(
                    self.client.responses.create,
                    model="grok-2-image",
                    input=[
                        {
                            "role": "user",
                            "content": [{"type": "input_text", "text": f"Edit the image: {edit_prompt}"}]
                        },
                        {
                            "type": "image_generation_call",
                            "id": previous_image_id
                        }
                    ],
                    tools=[{
                        "type": "image_generation",
                        **tool_options
                    }]
                )
            else:
                raise ValueError("Either previous_response_id or previous_image_id must be provided")
            
            # Extract edited image
            image_calls = [
                output for output in response.output
                if output.type == "image_generation_call"
            ]
            
            if not image_calls:
                raise Exception("No edited image was generated")
            
            image_call = image_calls[0]
            
            # Generate unique filename for edited image
            image_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{platform}_edited_{timestamp}_{image_id[:8]}.png"
            
            return {
                "status": "success",
                "image_id": image_call.id,
                "response_id": response.id,
                "image_base64": image_call.result,
                "image_data_url": f"data:image/png;base64,{image_call.result}",
                "filename": filename,
                "edit_prompt": edit_prompt,
                "revised_prompt": getattr(image_call, 'revised_prompt', edit_prompt),
                "metadata": {
                    "platform": platform,
                    "quality_preset": quality_preset,
                    "tool_options": tool_options,
                    "model": "grok-2-image",
                    "edited_at": datetime.utcnow().isoformat(),
                    "previous_response_id": previous_response_id,
                    "previous_image_id": previous_image_id
                }
            }
            
        except Exception as e:
            logger.error(f"Image editing failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "edit_prompt": edit_prompt
            }

    async def generate_streaming_image(self,
                                     prompt: str,
                                     platform: str = "instagram",
                                     partial_images: int = 2,
                                     quality_preset: str = "standard") -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate image with streaming partial results for better UX.
        
        Args:
            prompt: Image description
            platform: Target platform
            partial_images: Number of partial images to stream (1-3)
            quality_preset: Quality preset
        
        Yields:
            Dict containing partial image data and progress info
        """
        try:
            enhanced_prompt = self._enhance_prompt_for_platform(prompt, platform)
            tool_options = self.quality_presets.get(quality_preset, self.quality_presets["standard"])
            
            # Use Responses API with streaming as per OpenAI documentation
            stream = await asyncio.to_thread(
                self.client.responses.create,
                model="grok-2-image",
                input=enhanced_prompt,
                tools=[{
                    "type": "image_generation",
                    "partial_images": partial_images,
                    **tool_options
                }],
                stream=True
            )
            
            for event in stream:
                if event.type == "image_generation.partial_image":
                    yield {
                        "status": "partial",
                        "partial_index": event.partial_image_index,
                        "total_partials": partial_images,
                        "image_base64": event.b64_json,
                        "image_data_url": f"data:image/png;base64,{event.b64_json}",
                        "progress": (event.partial_image_index + 1) / partial_images,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                elif event.type == "image_generation.done":
                    yield {
                        "status": "completed",
                        "final_image_base64": event.b64_json,
                        "final_image_data_url": f"data:image/png;base64,{event.b64_json}",
                        "prompt": enhanced_prompt,
                        "platform": platform,
                        "completed_at": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Streaming image generation failed: {str(e)}")
            yield {
                "status": "error",
                "error": str(e),
                "prompt": prompt,
                "platform": platform
            }

    async def generate_content_images(self,
                                    content_text: str,
                                    platforms: List[str],
                                    image_count: int = 1,
                                    industry_context: Optional[str] = None,
                                    enable_post_processing: bool = True,
                                    generate_alt_text: bool = True,
                                    quality_preset: str = "standard") -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate multiple images optimized for different platforms based on content.
        Includes Grok 4's enhancements: post-processing, alt-text, and quality validation.
        
        Args:
            content_text: The social media content text
            platforms: List of target platforms
            image_count: Number of images per platform
            industry_context: Industry context for styling
            enable_post_processing: Apply platform-specific post-processing
            generate_alt_text: Generate accessibility alt-text
            quality_preset: Quality preset for all images
        
        Returns:
            Dict with platform keys and lists of enhanced generated images
        """
        results = {}
        
        # Generate base prompt from content with quality enhancements
        base_prompt = f"Create a compelling visual representation for this social media content: {content_text[:200]}"
        
        for platform in platforms:
            platform_images = []
            logger.info(f"Generating {image_count} images for {platform} platform")
            
            for i in range(image_count):
                # Add variation to each image with enhanced prompts
                variation_prompt = base_prompt
                if i > 0:
                    variations = [
                        "with a different artistic composition and visual angle",
                        "from an alternative creative perspective with unique styling", 
                        "with a complementary color palette and mood",
                        "in a distinctive style with different visual emphasis",
                        "with varied lighting and atmospheric elements"
                    ]
                    variation_prompt += f" {variations[i % len(variations)]}"
                
                # Add image number context for variety
                if image_count > 1:
                    variation_prompt += f". Variation {i + 1} of {image_count} for maximum visual diversity."
                
                try:
                    result = await self.generate_image(
                        prompt=variation_prompt,
                        platform=platform,
                        quality_preset=quality_preset,
                        content_context=content_text,
                        industry_context=industry_context,
                        enable_post_processing=enable_post_processing,
                        generate_alt_text=generate_alt_text,
                        max_retries=1  # Reduced retries for batch generation
                    )
                    
                    # Add batch generation metadata
                    if "metadata" in result:
                        result["metadata"]["batch_info"] = {
                            "batch_index": i,
                            "batch_total": image_count,
                            "platform_batch": platform,
                            "content_source": content_text[:100]
                        }
                    
                    platform_images.append(result)
                    logger.info(f"Generated image {i + 1}/{image_count} for {platform} (quality: {result.get('quality', {}).get('score', 'N/A')})")
                    
                except Exception as e:
                    logger.error(f"Failed to generate image {i + 1} for {platform}: {e}")
                    # Add error placeholder
                    platform_images.append({
                        "status": "error",
                        "error": str(e),
                        "platform": platform,
                        "batch_index": i,
                        "prompt": variation_prompt
                    })
                
                # Brief delay to avoid rate limits and allow processing
                await asyncio.sleep(1.0)  # Increased delay for post-processing
            
            results[platform] = platform_images
            
            # Log platform completion with quality summary
            successful_images = [img for img in platform_images if img.get("status") == "success"]
            avg_quality = sum(img.get("quality", {}).get("score", 0) for img in successful_images) / max(len(successful_images), 1)
            logger.info(f"Completed {platform}: {len(successful_images)}/{image_count} successful, avg quality: {avg_quality:.1f}")
        
        return results

    async def add_watermark_to_image(self, 
                                   image_base64: str, 
                                   watermark_text: str,
                                   position: str = "bottom_right",
                                   opacity: float = 0.7) -> Dict[str, Any]:
        """
        Add watermark to generated image using post-processing service.
        
        Args:
            image_base64: Base64 encoded image
            watermark_text: Text to add as watermark
            position: Position for watermark (bottom_right, bottom_left, etc.)
            opacity: Watermark opacity (0.0 to 1.0)
            
        Returns:
            Dict with watermarked image data and metadata
        """
        try:
            # Convert base64 to bytes
            image_bytes = base64.b64decode(image_base64)
            
            # Add watermark using image processing service
            watermarked_bytes = image_processing_service.add_watermark(
                image_bytes, watermark_text, position, opacity
            )
            
            # Convert back to base64
            watermarked_base64 = base64.b64encode(watermarked_bytes).decode('utf-8')
            
            return {
                "status": "success",
                "image_base64": watermarked_base64,
                "image_data_url": f"data:image/png;base64,{watermarked_base64}",
                "watermark": {
                    "text": watermark_text,
                    "position": position,
                    "opacity": opacity,
                    "applied_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to add watermark: {e}")
            return {
                "status": "error", 
                "error": str(e),
                "image_base64": image_base64  # Return original on error
            }

    def get_platform_recommendations(self, platform: str) -> Dict[str, Any]:
        """
        Get comprehensive platform recommendations including Grok 4 enhancements.
        
        Args:
            platform: Target social media platform
            
        Returns:
            Dict with platform recommendations, quality presets, and best practices
        """
        # Get base recommendations from image processing service
        processing_recommendations = image_processing_service.get_platform_recommendations(platform)
        
        # Add image generation specific recommendations
        generation_recommendations = {
            "platform": platform,
            "optimal_quality_presets": self._get_platform_optimal_presets(platform),
            "prompt_enhancements": self._get_platform_prompt_tips(platform),
            "content_guidelines": self._get_platform_content_guidelines(platform),
            "accessibility_features": {
                "alt_text_required": True,
                "alt_text_max_length": 125 if platform == "twitter" else 125,
                "screen_reader_compatible": True
            },
            "post_processing_options": {
                "auto_resize": True,
                "quality_enhancement": True,
                "platform_optimization": True,
                "watermark_support": True
            }
        }
        
        # Merge recommendations
        return {**processing_recommendations, **generation_recommendations}
    
    def _get_platform_optimal_presets(self, platform: str) -> List[str]:
        """Get optimal quality presets for platform."""
        presets = {
            "instagram": ["standard", "premium", "story"],
            "twitter": ["standard", "premium"], 
            "facebook": ["standard", "premium"],
            "linkedin": ["premium", "banner"],
            "tiktok": ["story", "premium"],
            "youtube": ["banner", "premium"]
        }
        return presets.get(platform, ["standard", "premium"])
    
    def _get_platform_prompt_tips(self, platform: str) -> List[str]:
        """Get platform-specific prompt optimization tips."""
        tips = {
            "instagram": [
                "Include aesthetic and lifestyle elements",
                "Focus on visual appeal and engagement",
                "Use vibrant colors and clear composition",
                "Consider square or portrait orientations"
            ],
            "twitter": [
                "Keep visuals simple and clear",
                "Ensure readability at small sizes", 
                "Use high contrast for timeline visibility",
                "Optimize for horizontal viewing"
            ],
            "facebook": [
                "Create engaging, shareable content",
                "Use bright, attention-grabbing visuals",
                "Consider link preview optimization",
                "Balance text and visual elements"
            ],
            "linkedin": [
                "Maintain professional appearance",
                "Use business-appropriate imagery",
                "Focus on thought leadership visuals",
                "Ensure corporate presentation quality"
            ],
            "tiktok": [
                "Create trendy, youthful aesthetics",
                "Use bold, eye-catching visuals",
                "Optimize for mobile vertical viewing",
                "Consider viral content elements"
            ]
        }
        return tips.get(platform, [
            "Use high-quality, engaging visuals",
            "Maintain brand consistency",
            "Optimize for platform viewing experience"
        ])
    
    def _get_platform_content_guidelines(self, platform: str) -> Dict[str, Any]:
        """Get platform content guidelines and restrictions."""
        guidelines = {
            "instagram": {
                "text_overlay_limit": "20% of image area",
                "hashtag_support": True,
                "story_features": ["polls", "questions", "stickers"],
                "engagement_focus": "visual aesthetics"
            },
            "twitter": {
                "character_consideration": "visual should complement 280 char limit",
                "thread_support": True,
                "retweet_optimization": "clear, shareable content",
                "engagement_focus": "news and conversation"
            },
            "facebook": {
                "text_overlay_limit": "20% for ads",
                "link_preview_optimization": True,
                "sharing_features": "reactions, comments, shares",
                "engagement_focus": "community and sharing"
            },
            "linkedin": {
                "professional_standards": "business appropriate content only",
                "industry_focus": True,
                "networking_optimization": "thought leadership content",
                "engagement_focus": "professional networking"
            },
            "tiktok": {
                "vertical_requirement": "9:16 aspect ratio preferred",
                "trend_awareness": "align with current trends",
                "music_sync": "consider audio-visual sync",
                "engagement_focus": "entertainment and trends"
            }
        }
        return guidelines.get(platform, {
            "general_guidelines": "follow platform community standards",
            "quality_focus": "high-resolution, engaging content"
        })

    def _select_model_and_client(self, model: str) -> Tuple[str, Any]:
        """
        Select the appropriate API client and model name based on requested model
        
        Args:
            model: Requested model (grok2, grok2_basic, grok2_premium, gpt_image_1)
            
        Returns:
            Tuple of (actual_model_name, api_client_to_use)
        """
        # Map to actual model name
        actual_model = self.model_mapping.get(model, "grok-2-image")
        
        # Select client based on model
        if model == "gpt_image_1":
            if self.openai_async_client is None:
                logger.warning("OpenAI client not available, falling back to Grok-2")
                return "grok-2-image", self.async_client
            return actual_model, self.openai_async_client
        else:
            # Use xAI Grok client for all grok variants
            if self.async_client is None:
                raise Exception("xAI client not initialized. Image generation unavailable.")
            return actual_model, self.async_client

    def save_image_to_file(self, image_base64: str, filepath: str) -> bool:
        """Save base64 image data to file."""
        try:
            image_data = base64.b64decode(image_base64)
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, "wb") as f:
                f.write(image_data)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save image to {filepath}: {str(e)}")
            return False

# Global service instance
image_generation_service = ImageGenerationService()