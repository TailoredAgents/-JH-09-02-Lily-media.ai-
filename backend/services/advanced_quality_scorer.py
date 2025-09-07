"""
Advanced Image Quality Scoring Service

Integrates CLIP and LAION-based models for semantic quality assessment
beyond basic technical quality metrics. Provides comprehensive scoring
for content relevance, aesthetic quality, and brand alignment.
"""

import logging
import base64
import io
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from PIL import Image
import numpy as np

from backend.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class AdvancedQualityScorer:
    """
    Advanced image quality scoring using CLIP and LAION-based models.
    
    Provides multi-dimensional quality assessment including:
    - Technical quality (resolution, composition, clarity)
    - Semantic alignment (prompt-image matching)
    - Aesthetic quality (visual appeal, artistic merit)
    - Brand consistency (alignment with brand guidelines)
    - Platform suitability (optimization for target platform)
    """
    
    def __init__(self):
        self.models_loaded = False
        self.clip_model = None
        self.clip_processor = None
        self.laion_aesthetic_model = None
        
        # Quality scoring thresholds
        self.quality_thresholds = {
            'excellent': 85,
            'good': 70,
            'acceptable': 55,
            'poor': 35,
            'unacceptable': 0
        }
        
        # Platform-specific quality weights
        self.platform_weights = {
            'instagram': {
                'aesthetic': 0.35,
                'semantic': 0.25,
                'technical': 0.20,
                'brand': 0.15,
                'platform_fit': 0.05
            },
            'twitter': {
                'semantic': 0.30,
                'technical': 0.25,
                'brand': 0.20,
                'aesthetic': 0.15,
                'platform_fit': 0.10
            },
            'facebook': {
                'semantic': 0.25,
                'brand': 0.25,
                'aesthetic': 0.20,
                'technical': 0.20,
                'platform_fit': 0.10
            },
            'tiktok': {
                'aesthetic': 0.30,
                'platform_fit': 0.25,
                'semantic': 0.20,
                'technical': 0.15,
                'brand': 0.10
            },
            'default': {
                'semantic': 0.25,
                'technical': 0.25,
                'aesthetic': 0.20,
                'brand': 0.20,
                'platform_fit': 0.10
            }
        }
        
        # Initialize models (lazy loading)
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize CLIP and LAION models for quality scoring."""
        try:
            # Try to import and load CLIP
            try:
                import clip
                import torch
                
                # Load CLIP model
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self.clip_model, self.clip_processor = clip.load("ViT-B/32", device=device)
                logger.info(f"CLIP model loaded successfully on {device}")
                
            except ImportError:
                logger.warning("CLIP not available. Install with: pip install git+https://github.com/openai/CLIP.git")
                
            # Try to load LAION aesthetic predictor
            try:
                import transformers
                from transformers import pipeline
                
                # Use a LAION-based aesthetic quality model
                # This is a placeholder - in practice, you'd use a specific aesthetic model
                self.laion_aesthetic_model = pipeline(
                    "image-classification",
                    model="cafeai/cafe_aesthetic",  # Example model
                    device=0 if torch.cuda.is_available() else -1
                )
                logger.info("LAION aesthetic model loaded successfully")
                
            except (ImportError, Exception) as e:
                logger.warning(f"LAION aesthetic model not available: {e}")
                
            self.models_loaded = True if self.clip_model or self.laion_aesthetic_model else False
            
        except Exception as e:
            logger.error(f"Failed to initialize advanced quality scoring models: {e}")
            self.models_loaded = False
    
    async def score_image_quality(self, 
                                image_base64: str, 
                                original_prompt: str,
                                platform: str = "instagram",
                                brand_context: Optional[Dict[str, Any]] = None,
                                fallback_to_basic: bool = True) -> Dict[str, Any]:
        """
        Comprehensive image quality scoring using advanced ML models.
        
        Args:
            image_base64: Base64 encoded image data
            original_prompt: Original prompt used to generate the image
            platform: Target social media platform
            brand_context: Brand guidelines and context
            fallback_to_basic: Whether to fall back to basic scoring if models unavailable
            
        Returns:
            Comprehensive quality assessment with scores and recommendations
        """
        try:
            # Load and validate image
            image_pil = self._decode_image(image_base64)
            if not image_pil:
                return self._create_error_response("Failed to decode image")
            
            # Get platform-specific weights
            weights = self.platform_weights.get(platform, self.platform_weights['default'])
            
            # Initialize scores
            quality_scores = {}
            total_score = 0
            
            # 1. Technical Quality Assessment
            technical_score = await self._assess_technical_quality(image_pil)
            quality_scores['technical'] = technical_score
            total_score += technical_score * weights['technical']
            
            # 2. Semantic Alignment Assessment (CLIP-based)
            semantic_score = await self._assess_semantic_alignment(image_pil, original_prompt)
            quality_scores['semantic'] = semantic_score
            total_score += semantic_score * weights['semantic']
            
            # 3. Aesthetic Quality Assessment (LAION-based)
            aesthetic_score = await self._assess_aesthetic_quality(image_pil)
            quality_scores['aesthetic'] = aesthetic_score
            total_score += aesthetic_score * weights['aesthetic']
            
            # 4. Brand Consistency Assessment
            brand_score = await self._assess_brand_consistency(image_pil, brand_context)
            quality_scores['brand'] = brand_score
            total_score += brand_score * weights['brand']
            
            # 5. Platform Suitability Assessment
            platform_score = await self._assess_platform_suitability(image_pil, platform)
            quality_scores['platform_fit'] = platform_score
            total_score += platform_score * weights['platform_fit']
            
            # Calculate overall score
            overall_score = min(100, max(0, total_score))
            
            # Generate quality assessment and recommendations
            quality_level = self._determine_quality_level(overall_score)
            recommendations = self._generate_recommendations(quality_scores, weights, platform)
            
            return {
                "overall_score": round(overall_score, 1),
                "quality_level": quality_level,
                "dimension_scores": {
                    "technical": round(quality_scores['technical'], 1),
                    "semantic": round(quality_scores['semantic'], 1),
                    "aesthetic": round(quality_scores['aesthetic'], 1),
                    "brand": round(quality_scores['brand'], 1),
                    "platform_fit": round(quality_scores['platform_fit'], 1)
                },
                "weights_used": weights,
                "recommendations": recommendations,
                "quality_acceptable": overall_score >= self.quality_thresholds['acceptable'],
                "models_used": {
                    "clip_available": self.clip_model is not None,
                    "laion_available": self.laion_aesthetic_model is not None,
                    "advanced_scoring": self.models_loaded
                },
                "platform": platform,
                "assessed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Advanced quality scoring failed: {e}")
            
            if fallback_to_basic:
                # Fall back to basic quality scoring
                return await self._basic_quality_fallback(image_base64, original_prompt, platform)
            else:
                return self._create_error_response(f"Quality assessment failed: {str(e)}")
    
    def _decode_image(self, image_base64: str) -> Optional[Image.Image]:
        """Decode base64 image to PIL Image."""
        try:
            image_data = base64.b64decode(image_base64)
            image_pil = Image.open(io.BytesIO(image_data))
            return image_pil
        except Exception as e:
            logger.error(f"Failed to decode image: {e}")
            return None
    
    async def _assess_technical_quality(self, image: Image.Image) -> float:
        """Assess technical image quality (resolution, composition, clarity)."""
        try:
            width, height = image.size
            total_pixels = width * height
            
            # Resolution score (higher is better, up to a point)
            if total_pixels >= 1024 * 1024:  # 1MP+
                resolution_score = 100
            elif total_pixels >= 512 * 512:  # 0.25MP+
                resolution_score = 80
            elif total_pixels >= 256 * 256:  # 64K+
                resolution_score = 60
            else:
                resolution_score = 40
            
            # Aspect ratio score (prefer common social media ratios)
            aspect_ratio = width / height
            if 0.8 <= aspect_ratio <= 1.25:  # Square-ish (Instagram)
                aspect_score = 100
            elif 1.77 <= aspect_ratio <= 1.78:  # 16:9 (Twitter, YouTube)
                aspect_score = 90
            elif 0.56 <= aspect_ratio <= 0.57:  # 9:16 (TikTok, Stories)
                aspect_score = 85
            else:
                aspect_score = 70
            
            # Basic quality checks
            # Convert to array for analysis
            image_array = np.array(image)
            
            # Check for completely blank or uniform images
            if len(np.unique(image_array)) < 10:
                uniformity_penalty = 50
            else:
                uniformity_penalty = 0
            
            # Combine technical metrics
            technical_score = (resolution_score * 0.4 + aspect_score * 0.3 + 
                             (100 - uniformity_penalty) * 0.3)
            
            return max(0, min(100, technical_score))
            
        except Exception as e:
            logger.error(f"Technical quality assessment failed: {e}")
            return 50.0  # Neutral score on error
    
    async def _assess_semantic_alignment(self, image: Image.Image, prompt: str) -> float:
        """Assess semantic alignment between image and prompt using CLIP."""
        try:
            if not self.clip_model or not self.clip_processor:
                # Fallback: basic keyword matching
                return self._basic_semantic_assessment(image, prompt)
            
            import torch
            
            # Preprocess image and text
            image_input = self.clip_processor(image).unsqueeze(0)
            text_input = self.clip_processor.tokenize([prompt]).to(self.clip_model.device)
            
            with torch.no_grad():
                # Get embeddings
                image_features = self.clip_model.encode_image(image_input)
                text_features = self.clip_model.encode_text(text_input)
                
                # Calculate cosine similarity
                similarity = torch.cosine_similarity(image_features, text_features).item()
                
                # Convert to 0-100 score
                # CLIP similarity ranges roughly from -1 to 1, but typically 0.2 to 0.4 for good matches
                semantic_score = max(0, min(100, (similarity + 1) * 50))
                
                # Boost score for very high similarity
                if similarity > 0.3:
                    semantic_score = min(100, semantic_score * 1.2)
                
                return semantic_score
                
        except Exception as e:
            logger.error(f"CLIP semantic assessment failed: {e}")
            return self._basic_semantic_assessment(image, prompt)
    
    def _basic_semantic_assessment(self, image: Image.Image, prompt: str) -> float:
        """Basic semantic assessment fallback."""
        # This is a very basic fallback - in practice, you might use other methods
        # For now, just return a neutral score
        return 65.0
    
    async def _assess_aesthetic_quality(self, image: Image.Image) -> float:
        """Assess aesthetic quality using LAION-based models."""
        try:
            if not self.laion_aesthetic_model:
                # Fallback to basic aesthetic assessment
                return self._basic_aesthetic_assessment(image)
            
            # Use the aesthetic model
            result = self.laion_aesthetic_model(image)
            
            # Extract aesthetic score (depends on specific model)
            # This is a placeholder - adjust based on actual model output
            if isinstance(result, list) and len(result) > 0:
                score_info = result[0]
                if 'score' in score_info:
                    aesthetic_score = score_info['score'] * 100
                elif 'label' in score_info and 'score' in score_info:
                    # Convert classification to score
                    aesthetic_score = score_info['score'] * 100 if 'beautiful' in score_info['label'].lower() else 50
                else:
                    aesthetic_score = 70
            else:
                aesthetic_score = 70
                
            return max(0, min(100, aesthetic_score))
            
        except Exception as e:
            logger.error(f"LAION aesthetic assessment failed: {e}")
            return self._basic_aesthetic_assessment(image)
    
    def _basic_aesthetic_assessment(self, image: Image.Image) -> float:
        """Basic aesthetic assessment fallback."""
        try:
            # Basic heuristics for aesthetic quality
            width, height = image.size
            
            # Color variety
            image_array = np.array(image)
            unique_colors = len(np.unique(image_array.reshape(-1, image_array.shape[-1]), axis=0))
            
            # More color variety generally indicates more interesting images
            color_score = min(100, (unique_colors / 1000) * 100)
            
            # Aspect ratio aesthetics
            aspect_ratio = width / height
            if 0.8 <= aspect_ratio <= 1.25:  # Golden ratio vicinity
                ratio_score = 100
            else:
                ratio_score = 80
            
            aesthetic_score = (color_score * 0.6 + ratio_score * 0.4)
            return max(40, min(100, aesthetic_score))
            
        except Exception as e:
            logger.error(f"Basic aesthetic assessment failed: {e}")
            return 60.0
    
    async def _assess_brand_consistency(self, image: Image.Image, brand_context: Optional[Dict[str, Any]]) -> float:
        """Assess brand consistency and alignment."""
        try:
            if not brand_context:
                return 75.0  # Neutral score if no brand context
            
            brand_score = 75.0  # Start with neutral
            
            # Check color alignment if brand colors specified
            if 'primary_color' in brand_context or 'secondary_color' in brand_context:
                # This would need color analysis of the image
                # Placeholder for color consistency check
                brand_score += 10
            
            # Check style alignment
            if 'visual_style' in brand_context:
                # This would need style classification
                # Placeholder for style consistency check  
                brand_score += 5
            
            # Check industry appropriateness
            if 'industry_type' in brand_context:
                # Industry-appropriate imagery assessment
                brand_score += 10
            
            return min(100, brand_score)
            
        except Exception as e:
            logger.error(f"Brand consistency assessment failed: {e}")
            return 70.0
    
    async def _assess_platform_suitability(self, image: Image.Image, platform: str) -> float:
        """Assess suitability for specific social media platform."""
        try:
            width, height = image.size
            aspect_ratio = width / height
            
            platform_preferences = {
                'instagram': {
                    'preferred_ratios': [(1.0, 0.1), (0.8, 0.1), (1.91, 0.1)],  # Square, portrait, landscape
                    'min_resolution': 1080,
                    'style_preference': 'aesthetic'
                },
                'twitter': {
                    'preferred_ratios': [(1.91, 0.1), (1.0, 0.1)],  # Landscape, square
                    'min_resolution': 1024,
                    'style_preference': 'clear'
                },
                'facebook': {
                    'preferred_ratios': [(1.91, 0.1), (1.0, 0.1)],  # Landscape, square  
                    'min_resolution': 1200,
                    'style_preference': 'engaging'
                },
                'tiktok': {
                    'preferred_ratios': [(0.56, 0.05)],  # Vertical 9:16
                    'min_resolution': 1080,
                    'style_preference': 'dynamic'
                }
            }
            
            prefs = platform_preferences.get(platform, platform_preferences['instagram'])
            
            # Aspect ratio score
            ratio_score = 0
            for pref_ratio, tolerance in prefs['preferred_ratios']:
                if abs(aspect_ratio - pref_ratio) <= tolerance:
                    ratio_score = 100
                    break
            if ratio_score == 0:
                # Find closest match
                closest = min(prefs['preferred_ratios'], 
                            key=lambda x: abs(aspect_ratio - x[0]))
                ratio_score = max(30, 100 - abs(aspect_ratio - closest[0]) * 100)
            
            # Resolution score for platform
            min_res = prefs['min_resolution']
            if min(width, height) >= min_res:
                res_score = 100
            else:
                res_score = (min(width, height) / min_res) * 100
            
            platform_score = (ratio_score * 0.7 + res_score * 0.3)
            return max(0, min(100, platform_score))
            
        except Exception as e:
            logger.error(f"Platform suitability assessment failed: {e}")
            return 70.0
    
    def _determine_quality_level(self, score: float) -> str:
        """Determine quality level from numerical score."""
        for level, threshold in self.quality_thresholds.items():
            if score >= threshold:
                return level
        return 'unacceptable'
    
    def _generate_recommendations(self, scores: Dict[str, float], weights: Dict[str, float], platform: str) -> List[str]:
        """Generate actionable quality improvement recommendations."""
        recommendations = []
        
        # Check each dimension for improvement opportunities
        if scores['technical'] < 60:
            recommendations.append("Consider increasing image resolution for better technical quality")
            
        if scores['semantic'] < 50:
            recommendations.append("Image content doesn't match prompt well - try refining the prompt")
            
        if scores['aesthetic'] < 60:
            recommendations.append("Enhance visual appeal with better composition or color balance")
            
        if scores['brand'] < 70:
            recommendations.append("Improve brand consistency by incorporating brand colors and style")
            
        if scores['platform_fit'] < 70:
            platform_tips = {
                'instagram': "Optimize for Instagram: use square or portrait aspect ratio",
                'twitter': "Optimize for Twitter: use landscape or square format with clear, readable content",
                'tiktok': "Optimize for TikTok: use vertical 9:16 aspect ratio with dynamic visuals",
                'facebook': "Optimize for Facebook: use landscape format with engaging, social content"
            }
            tip = platform_tips.get(platform, "Optimize aspect ratio and resolution for target platform")
            recommendations.append(tip)
        
        # Add specific improvement suggestions based on weights
        highest_weight = max(weights.items(), key=lambda x: x[1])
        if scores[highest_weight[0]] < 75:
            recommendations.insert(0, f"Focus on improving {highest_weight[0]} quality - it's weighted highest for {platform}")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    async def _basic_quality_fallback(self, image_base64: str, prompt: str, platform: str) -> Dict[str, Any]:
        """Fallback to basic quality scoring when advanced models unavailable."""
        try:
            # Basic quality assessment without ML models
            image_pil = self._decode_image(image_base64)
            if not image_pil:
                return self._create_error_response("Failed to decode image for basic assessment")
            
            technical_score = await self._assess_technical_quality(image_pil)
            
            # Simplified scoring
            fallback_score = technical_score * 0.6 + 40  # Add base score for other dimensions
            
            return {
                "overall_score": round(fallback_score, 1),
                "quality_level": self._determine_quality_level(fallback_score),
                "dimension_scores": {
                    "technical": round(technical_score, 1),
                    "semantic": 65.0,  # Neutral
                    "aesthetic": 60.0,  # Neutral
                    "brand": 70.0,  # Neutral
                    "platform_fit": 65.0  # Neutral
                },
                "recommendations": ["Advanced quality models unavailable - consider upgrading for better assessment"],
                "quality_acceptable": fallback_score >= self.quality_thresholds['acceptable'],
                "models_used": {
                    "clip_available": False,
                    "laion_available": False,
                    "advanced_scoring": False,
                    "fallback_mode": True
                },
                "platform": platform,
                "assessed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Basic quality fallback failed: {e}")
            return self._create_error_response(f"All quality assessment methods failed: {str(e)}")
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response for quality assessment."""
        return {
            "overall_score": 0,
            "quality_level": "error",
            "error": error_message,
            "quality_acceptable": False,
            "models_used": {
                "clip_available": False,
                "laion_available": False,
                "advanced_scoring": False,
                "error": True
            },
            "assessed_at": datetime.utcnow().isoformat()
        }


# Global instance for service usage
_advanced_quality_scorer = None

def get_advanced_quality_scorer() -> AdvancedQualityScorer:
    """Get the global advanced quality scorer instance."""
    global _advanced_quality_scorer
    if _advanced_quality_scorer is None:
        _advanced_quality_scorer = AdvancedQualityScorer()
    return _advanced_quality_scorer