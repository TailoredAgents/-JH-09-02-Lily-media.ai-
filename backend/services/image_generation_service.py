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
from prometheus_client import Counter, Histogram, Gauge
from backend.core.config import get_settings
from backend.services.image_processing_service import image_processing_service
from backend.services.alt_text_service import alt_text_service
from backend.services.advanced_quality_scorer import get_advanced_quality_scorer

settings = get_settings()
logger = logging.getLogger(__name__)

# Image quality and generation metrics
IMAGE_GENERATION_REQUESTS = Counter(
    'image_generation_requests_total',
    'Total image generation requests',
    ['model', 'platform', 'status', 'quality_preset']
)

IMAGE_GENERATION_LATENCY = Histogram(
    'image_generation_duration_seconds',
    'Image generation latency including post-processing',
    ['model', 'platform', 'quality_preset'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 30.0, 45.0, 60.0, float('inf')]
)

IMAGE_QUALITY_SCORES = Histogram(
    'image_quality_scores',
    'Distribution of image quality scores',
    ['model', 'platform', 'quality_preset'],
    buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
)

IMAGE_RETRIES = Counter(
    'image_generation_retries_total',
    'Total image generation retries due to quality issues',
    ['model', 'platform', 'retry_reason']
)

TEXT_FALLBACKS_GENERATED = Counter(
    'image_text_fallbacks_total',
    'Total text-only fallbacks generated due to poor image quality',
    ['platform', 'reason']
)

PROCESSING_FAILURES = Counter(
    'image_processing_failures_total',
    'Total image post-processing failures',
    ['platform', 'failure_type']
)

ALT_TEXT_GENERATION = Counter(
    'alt_text_generation_total',
    'Alt-text generation attempts and results',
    ['platform', 'status']
)

CURRENT_QUALITY_DISTRIBUTION = Gauge(
    'current_image_quality_average',
    'Current average image quality score',
    ['model', 'platform']
)

class ImageGenerationService:
    """
    Enhanced image generation service using xAI Grok-2 Vision for policy-compliant
    social media content creation with real-time streaming and multi-turn editing capabilities.
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
        
        # Model-to-API mapping for multi-model support - Policy compliant models only
        self.model_mapping = {
            "grok2": "grok-2-image",
            "grok2_basic": "grok-2-image",
            "grok2_premium": "grok-2-image", 
            "gpt_image_1": "grok-2-image"  # Policy compliant: use Grok-2 for all requests
        }
        
        # Policy compliant: Only xAI Grok-2 Vision model is used - OpenAI integration removed
        
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
        # Step 1: Content moderation - validate prompt before generation
        try:
            from backend.services.content_moderation_service import moderate_content, ContentType, ModerationResult
            
            moderation_result = await moderate_content(
                content=prompt,
                content_type=ContentType.TEXT,
                user_id=None,  # User context not available at this service level
                organization_id=None,
                context={
                    'type': 'image_generation_prompt',
                    'platform': platform,
                    'model': model,
                    'quality': quality_preset
                }
            )
            
            # Block generation if content is rejected
            if moderation_result['result'] == ModerationResult.REJECTED.value:
                return {
                    "status": "moderation_rejected",
                    "error": f"Content rejected by moderation: {moderation_result['message']}",
                    "moderation": {
                        "result": moderation_result['result'],
                        "confidence": moderation_result['confidence'],
                        "categories": moderation_result['categories'],
                        "processing_time_ms": moderation_result['processing_time_ms']
                    }
                }
            
            # Log flagged content but allow generation with warning
            if moderation_result['result'] == ModerationResult.FLAGGED.value:
                logger.warning(
                    f"Flagged content approved for generation: "
                    f"confidence={moderation_result['confidence']:.2f}, "
                    f"categories={moderation_result['categories']}"
                )
                
        except ImportError:
            logger.warning("Content moderation service not available - proceeding without moderation")
        except Exception as e:
            logger.error(f"Content moderation error: {e} - proceeding with generation")
        
        # Start timing for metrics
        generation_start_time = datetime.utcnow()
        
        # Track request initiation
        IMAGE_GENERATION_REQUESTS.labels(
            model=model,
            platform=platform, 
            status='initiated',
            quality_preset=quality_preset
        ).inc()
        
        # Check if service is available
        if not self.async_client:
            # Track service unavailable
            IMAGE_GENERATION_REQUESTS.labels(
                model=model,
                platform=platform,
                status='failed_service_unavailable',
                quality_preset=quality_preset
            ).inc()
            
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
            
            # Model routing: Route to appropriate generation function based on effective_model
            response = await self._route_to_generation_function(
                model=model,
                enhanced_prompt=enhanced_prompt,
                tool_options=tool_options,
                platform=platform,
                quality_preset=quality_preset
            )
            
            # Extract image data from API response
            if not response.data or len(response.data) == 0:
                raise Exception(f"No image data returned from {model} image generation")
            
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
                raise Exception(f"No valid image data format returned from {model}")
            
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
                    
                    # Track post-processing failure
                    PROCESSING_FAILURES.labels(
                        platform=platform,
                        failure_type='post_processing_failed'
                    ).inc()
                    
                    processing_metadata = {"error": str(e), "fallback": True}
            
            # Advanced image quality assessment with CLIP/LAION integration
            advanced_scorer = get_advanced_quality_scorer()
            quality_metrics = await advanced_scorer.score_image_quality(
                image_base64=base64.b64encode(processed_image_bytes).decode('utf-8'),
                original_prompt=enhanced_prompt,
                platform=platform,
                brand_context=None,  # TODO: Pass brand context from user settings
                fallback_to_basic=True
            )
            
            # Convert to legacy format for compatibility
            legacy_quality_score = quality_metrics.get("overall_score", 50)
            legacy_quality_metrics = {
                "quality_score": legacy_quality_score,
                "issues": quality_metrics.get("recommendations", []),
                "recommendations": quality_metrics.get("recommendations", []),
                "advanced_assessment": quality_metrics
            }
            
            # Retry if quality is too low (score < 50) and retries available
            retry_count = 0
            while (legacy_quality_score < 50 and 
                   retry_count < max_retries and 
                   "error" not in legacy_quality_metrics):
                
                logger.info(f"Image quality too low (score: {legacy_quality_score}), retrying... ({retry_count + 1}/{max_retries})")
                retry_count += 1
                
                # Track retry
                IMAGE_RETRIES.labels(
                    model=model,
                    platform=platform,
                    retry_reason='quality_too_low'
                ).inc()
                
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
                        
                        # Re-assess quality with advanced scoring
                        retry_quality_assessment = await advanced_scorer.score_image_quality(
                            image_base64=base64.b64encode(processed_image_bytes).decode('utf-8'),
                            original_prompt=enhanced_prompt,
                            platform=platform,
                            brand_context=None,
                            fallback_to_basic=True
                        )
                        legacy_quality_score = retry_quality_assessment.get("overall_score", 50)
                        legacy_quality_metrics = {
                            "quality_score": legacy_quality_score,
                            "issues": retry_quality_assessment.get("recommendations", []),
                            "recommendations": retry_quality_assessment.get("recommendations", []),
                            "advanced_assessment": retry_quality_assessment
                        }
            
            # Check if text-only fallback should be offered due to poor quality
            text_only_fallback = None
            final_quality_score = legacy_quality_score
            
            if final_quality_score < 35 and retry_count >= max_retries:
                # Generate text-only content as fallback option
                logger.warning(f"Image quality critically low (score: {final_quality_score}) after {retry_count} retries. Generating text-only fallback.")
                
                # Track text fallback generation
                TEXT_FALLBACKS_GENERATED.labels(
                    platform=platform,
                    reason='quality_threshold_failed'
                ).inc()
                
                text_only_fallback = await self._generate_text_only_content(
                    prompt, platform, content_context, industry_context, tone
                )
            
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
                    
                    # Track alt-text generation success
                    ALT_TEXT_GENERATION.labels(
                        platform=platform,
                        status=alt_text_data.get('status', 'success')
                    ).inc()
                    
                except Exception as e:
                    logger.warning(f"Alt-text generation failed: {e}")
                    
                    # Track alt-text generation failure
                    ALT_TEXT_GENERATION.labels(
                        platform=platform,
                        status='failed'
                    ).inc()
                    
                    alt_text_data = {
                        "alt_text": "Generated image",
                        "status": "error",
                        "error": str(e)
                    }
            
            # Generate unique filename and ID
            image_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{platform}_{timestamp}_{image_id[:8]}.png"
            
            # Calculate generation time and track metrics
            generation_end_time = datetime.utcnow()
            generation_duration = (generation_end_time - generation_start_time).total_seconds()
            
            # Track successful generation
            IMAGE_GENERATION_REQUESTS.labels(
                model=model,
                platform=platform,
                status='success',
                quality_preset=quality_preset
            ).inc()
            
            # Track latency
            IMAGE_GENERATION_LATENCY.labels(
                model=model,
                platform=platform,
                quality_preset=quality_preset
            ).observe(generation_duration)
            
            # Track quality score
            IMAGE_QUALITY_SCORES.labels(
                model=model,
                platform=platform,
                quality_preset=quality_preset
            ).observe(final_quality_score)
            
            # Update current quality average
            CURRENT_QUALITY_DISTRIBUTION.labels(
                model=model,
                platform=platform
            ).set(final_quality_score)
            
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
                    "score": legacy_quality_metrics.get("quality_score", 0),
                    "issues": legacy_quality_metrics.get("issues", []),
                    "recommendations": legacy_quality_metrics.get("recommendations", []),
                    "retry_count": retry_count,
                    "final_attempt": retry_count >= max_retries,
                    "quality_acceptable": final_quality_score >= 35,
                    "advanced_assessment": legacy_quality_metrics.get("advanced_assessment", {})
                },
                "text_only_fallback": text_only_fallback,
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
            
            # Track generation failure
            IMAGE_GENERATION_REQUESTS.labels(
                model=model,
                platform=platform,
                status='failed_exception',
                quality_preset=quality_preset
            ).inc()
            
            # Track processing failure
            PROCESSING_FAILURES.labels(
                platform=platform,
                failure_type='generation_exception'
            ).inc()
            
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

    async def _route_to_generation_function(self, model: str, enhanced_prompt: str, 
                                          tool_options: Dict[str, Any], platform: str, 
                                          quality_preset: str) -> Any:
        """
        Route to appropriate generation function based on effective_model parameter.
        
        This implements proper model routing to dispatch to different generation
        functions based on the model's capabilities and API requirements.
        
        Args:
            model: Effective model to use (grok2, grok2_basic, grok2_premium, gpt_image_1)
            enhanced_prompt: Enhanced prompt for image generation
            tool_options: Tool configuration options
            platform: Target platform
            quality_preset: Quality preset
            
        Returns:
            API response from the appropriate generation function
        """
        logger.info(f"Routing image generation to model: {model}")
        
        # Route based on model family - Policy compliant: all models use Grok-2 Vision
        if model in ["grok2", "grok2_basic", "grok2_premium", "gpt_image_1"]:
            return await self._generate_with_grok_vision(
                "grok2", enhanced_prompt, tool_options, platform, quality_preset
            )
        else:
            # Default fallback to Grok-2
            logger.warning(f"Unknown model '{model}', falling back to Grok-2")
            return await self._generate_with_grok_vision(
                "grok2", enhanced_prompt, tool_options, platform, quality_preset
            )

    # Policy compliant: Legacy generation method removed - all requests use Grok-2 Vision

    async def _generate_with_grok_vision(self, model: str, enhanced_prompt: str, 
                                       tool_options: Dict[str, Any], platform: str, 
                                       quality_preset: str) -> Any:
        """
        Generate image using xAI Grok-2 Vision model with Grok-specific optimizations.
        
        Args:
            model: Specific Grok model variant (grok2, grok2_basic, grok2_premium)
            enhanced_prompt: Enhanced prompt for image generation
            tool_options: Tool configuration options
            platform: Target platform
            quality_preset: Quality preset
            
        Returns:
            xAI API response
        """
        if not self.async_client:
            logger.error("xAI Grok client not available")
            raise Exception("xAI Grok image generation service unavailable")
        
        logger.info(f"Generating image with xAI Grok-2 Vision model: {model}")
        
        # Grok-specific prompt enhancement based on model variant
        grok_enhanced_prompt = self._enhance_prompt_for_grok_variant(
            enhanced_prompt, model, platform, quality_preset
        )
        
        try:
            response = await self.async_client.images.generate(
                model="grok-2-image",
                prompt=grok_enhanced_prompt,
                n=1,
                response_format="b64_json"
            )
            
            logger.info(f"Grok-2 generation successful with model variant: {model}")
            return response
            
        except Exception as e:
            logger.error(f"Grok-2 generation failed: {e}")
            raise Exception(f"Grok-2 image generation failed: {str(e)}")

    def _enhance_prompt_for_grok_variant(self, prompt: str, model: str, 
                                       platform: str, quality_preset: str) -> str:
        """
        Enhance prompt specifically for different Grok model variants.
        
        Args:
            prompt: Base enhanced prompt
            model: Grok model variant
            platform: Target platform
            quality_preset: Quality preset
            
        Returns:
            Grok variant-specific enhanced prompt
        """
        # Base Grok enhancements
        enhanced = prompt
        
        # Model variant specific enhancements
        if model == "grok2_premium":
            # Premium variant: more detailed, artistic prompts
            enhanced += " Ultra-high quality, premium artistic rendering, maximum detail and refinement, professional photography quality."
        elif model == "grok2_basic":
            # Basic variant: simple, clean prompts
            enhanced += " Clean, simple design, good quality rendering, efficient generation."
        else:  # grok2 default
            # Standard variant: balanced quality and performance
            enhanced += " High quality rendering, detailed and professional, optimal balance of speed and quality."
        
        # Platform-specific Grok optimizations
        if platform in ["instagram", "tiktok"]:
            enhanced += " Optimized for mobile viewing, vibrant colors, high visual impact."
        elif platform in ["twitter", "facebook"]:
            enhanced += " Optimized for social media engagement, clear and readable design."
        
        return enhanced

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

    async def _generate_text_only_content(self,
                                        original_prompt: str,
                                        platform: str,
                                        content_context: Optional[str] = None,
                                        industry_context: Optional[str] = None,
                                        tone: str = "professional") -> Dict[str, Any]:
        """
        Generate text-only content as fallback when image quality is poor
        
        Args:
            original_prompt: Original image generation prompt
            platform: Target social media platform
            content_context: Context about the content
            industry_context: Industry-specific context
            tone: Desired tone for the content
            
        Returns:
            Dict containing text-only content alternatives
        """
        try:
            # Use OpenAI for text generation if available, otherwise xAI
            client = self.openai_async_client if self.openai_async_client else self.async_client
            if not client:
                raise ValueError("No text generation client available")
                
            # Adapt image prompt to text content prompt
            text_prompt = self._adapt_image_prompt_to_text(original_prompt, platform, content_context, industry_context, tone)
            
            # Generate multiple text alternatives
            response = await client.chat.completions.create(
                model="gpt-4o" if self.openai_async_client else "grok-beta",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a social media content expert creating engaging {platform} posts. Generate professional, high-quality text content that would work well without images."
                    },
                    {
                        "role": "user", 
                        "content": text_prompt
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            generated_content = response.choices[0].message.content.strip()
            
            # Generate additional text-based alternatives
            alternatives = await self._generate_text_alternatives(generated_content, platform, tone)
            
            # Create formatted text content suitable for the platform
            formatted_content = self._format_text_for_platform(generated_content, platform)
            
            return {
                "reason": "image_quality_fallback",
                "original_image_prompt": original_prompt,
                "quality_threshold_failed": True,
                "text_content": {
                    "primary": formatted_content,
                    "alternatives": alternatives,
                    "platform": platform,
                    "tone": tone,
                    "word_count": len(formatted_content.split()),
                    "character_count": len(formatted_content),
                    "platform_optimized": True
                },
                "suggestions": {
                    "use_case": f"High-quality text post for {platform}",
                    "benefits": [
                        "Guaranteed readability and engagement",
                        "Fast loading and accessible content", 
                        "Professional appearance without image dependency",
                        "Better performance than poor quality images"
                    ],
                    "call_to_action": "Consider using this text-only version for better user experience"
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate text-only fallback: {e}")
            return {
                "reason": "text_generation_failed",
                "error": str(e),
                "fallback_content": "Content creation in progress. Please check back shortly.",
                "generated_at": datetime.utcnow().isoformat()
            }
    
    def _adapt_image_prompt_to_text(self,
                                  image_prompt: str,
                                  platform: str,
                                  content_context: Optional[str] = None,
                                  industry_context: Optional[str] = None,
                                  tone: str = "professional") -> str:
        """Convert image generation prompt to text content prompt"""
        
        # Extract key concepts from image prompt
        concepts = image_prompt.replace("Generate an image of", "").replace("Create a visual", "").strip()
        
        # Platform-specific text content guidance
        platform_guidance = {
            "twitter": "Create a concise, engaging tweet (280 characters max) with relevant hashtags",
            "instagram": "Write an engaging Instagram caption with storytelling elements and relevant hashtags",
            "facebook": "Create a conversational Facebook post that encourages engagement", 
            "linkedin": "Write a professional LinkedIn post with industry insights",
            "tiktok": "Create energetic, trend-aware content suitable for video captions"
        }
        
        guidance = platform_guidance.get(platform, "Create engaging social media content")
        
        text_prompt = f"""
        {guidance} based on this concept: {concepts}
        
        Content context: {content_context or "General social media content"}
        Industry context: {industry_context or "General business"}
        Tone: {tone}
        Platform: {platform}
        
        Requirements:
        - Make it engaging and platform-appropriate
        - Include relevant hashtags if suitable for the platform
        - Focus on the core message from the original visual concept
        - Ensure it works well as standalone text content
        - Make it actionable and valuable to the audience
        
        Generate professional, high-quality text content:
        """
        
        return text_prompt.strip()
    
    async def _generate_text_alternatives(self, primary_content: str, platform: str, tone: str) -> List[str]:
        """Generate alternative text versions"""
        try:
            client = self.openai_async_client if self.openai_async_client else self.async_client
            if not client:
                return ["Alternative version not available"]
            
            alt_prompt = f"""
            Based on this {platform} content: "{primary_content}"
            
            Create 2 alternative versions with the same {tone} tone but different approaches:
            1. A more conversational version
            2. A more concise version
            
            Keep the core message but vary the style. Return just the alternatives, one per line.
            """
            
            response = await client.chat.completions.create(
                model="gpt-4o" if self.openai_async_client else "grok-beta",
                messages=[{"role": "user", "content": alt_prompt}],
                max_tokens=300,
                temperature=0.8
            )
            
            alternatives = response.choices[0].message.content.strip().split('\n')
            return [alt.strip() for alt in alternatives if alt.strip()][:2]
            
        except Exception as e:
            logger.error(f"Failed to generate text alternatives: {e}")
            return ["Alternative version not available"]
    
    def _format_text_for_platform(self, content: str, platform: str) -> str:
        """Format text content for specific platform requirements"""
        
        # Platform-specific formatting
        if platform == "twitter":
            # Ensure under 280 characters
            if len(content) > 280:
                content = content[:276] + "..."
                
        elif platform == "instagram":
            # Add line breaks for better readability
            if '\n' not in content:
                sentences = content.split('. ')
                if len(sentences) > 2:
                    mid_point = len(sentences) // 2
                    content = '. '.join(sentences[:mid_point]) + '.\n\n' + '. '.join(sentences[mid_point:])
                    
        elif platform == "linkedin":
            # Add professional formatting
            if not content.startswith(('Excited to', 'Proud to', 'Thrilled to')):
                content = content
            
        return content.strip()

# Global service instance
image_generation_service = ImageGenerationService()