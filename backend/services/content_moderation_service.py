"""
NSFW Content Moderation Service
Comprehensive content moderation pipeline for text and image content before generation
"""

import logging
import asyncio
import base64
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
import re

from openai import AsyncOpenAI
from backend.core.config import get_settings
from backend.services.usage_tracking_service import UsageTrackingService

logger = logging.getLogger(__name__)

class ModerationResult(Enum):
    """Moderation result types"""
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"  # Requires review
    ERROR = "error"

class ContentType(Enum):
    """Content types for moderation"""
    TEXT = "text"
    IMAGE = "image"
    COMBINED = "combined"

class ModerationCategories:
    """Moderation categories and their thresholds"""
    
    # OpenAI Moderation categories
    OPENAI_CATEGORIES = {
        'sexual': {'threshold': 0.7, 'description': 'Sexual content'},
        'hate': {'threshold': 0.8, 'description': 'Hate speech'},
        'harassment': {'threshold': 0.8, 'description': 'Harassment'},
        'self-harm': {'threshold': 0.9, 'description': 'Self-harm content'},
        'sexual/minors': {'threshold': 0.1, 'description': 'Sexual content involving minors'},
        'hate/threatening': {'threshold': 0.5, 'description': 'Threatening hate speech'},
        'violence/graphic': {'threshold': 0.8, 'description': 'Graphic violence'},
        'self-harm/intent': {'threshold': 0.9, 'description': 'Intent to self-harm'},
        'self-harm/instructions': {'threshold': 0.9, 'description': 'Self-harm instructions'},
        'harassment/threatening': {'threshold': 0.7, 'description': 'Threatening harassment'},
        'violence': {'threshold': 0.8, 'description': 'Violence content'}
    }
    
    # Custom categories for social media content
    CUSTOM_CATEGORIES = {
        'spam': {'threshold': 0.8, 'description': 'Spam content'},
        'misinformation': {'threshold': 0.7, 'description': 'Potential misinformation'},
        'brand_safety': {'threshold': 0.6, 'description': 'Brand safety concerns'},
        'copyright': {'threshold': 0.8, 'description': 'Potential copyright infringement'}
    }

class ContentModerationService:
    """
    Comprehensive content moderation service with multiple layers of protection
    """
    
    def __init__(self):
        """Initialize the content moderation service"""
        self.settings = get_settings()
        
        # Initialize OpenAI client for moderation
        if self.settings.openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        else:
            self.openai_client = None
            logger.warning("OpenAI API key not configured - moderation will be limited")
        
        # Enable/disable moderation based on settings
        self.moderation_enabled = getattr(self.settings, 'content_moderation_enabled', True)
        
        # Initialize usage tracking (optional, requires database session)
        self.usage_tracker = None
        
        logger.info(f"Content moderation service initialized (enabled: {self.moderation_enabled})")
    
    async def moderate_content(
        self,
        content: str,
        content_type: ContentType = ContentType.TEXT,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Moderate content with comprehensive analysis
        
        Args:
            content: Content to moderate
            content_type: Type of content (text, image, combined)
            user_id: User ID for tracking
            organization_id: Organization ID for tracking
            context: Additional context for moderation
            
        Returns:
            Moderation result with detailed analysis
        """
        
        if not self.moderation_enabled:
            return {
                'result': ModerationResult.APPROVED.value,
                'confidence': 1.0,
                'categories': {},
                'message': 'Content moderation disabled',
                'processing_time_ms': 0
            }
        
        start_time = datetime.utcnow()
        
        try:
            # Layer 1: Basic content validation
            basic_validation = await self._basic_validation(content, content_type)
            if basic_validation['result'] != ModerationResult.APPROVED.value:
                return basic_validation
            
            # Layer 2: OpenAI moderation (if available)
            openai_result = None
            if self.openai_client and content_type in [ContentType.TEXT, ContentType.COMBINED]:
                openai_result = await self._openai_moderation(content)
            
            # Layer 3: Custom pattern matching
            pattern_result = await self._pattern_matching(content, content_type)
            
            # Layer 4: NSFW text detection
            nsfw_result = await self._nsfw_text_detection(content)
            
            # Combine results and make final decision
            final_result = await self._combine_results(
                basic_validation,
                openai_result,
                pattern_result,
                nsfw_result,
                context
            )
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            final_result['processing_time_ms'] = round(processing_time, 2)
            
            # Track usage if user/org provided and tracker available
            if user_id and organization_id and self.usage_tracker:
                await self._track_moderation_usage(
                    user_id, organization_id, content_type, final_result
                )
            
            # Log moderation results
            await self._log_moderation_result(content, final_result, context)
            
            return final_result
            
        except Exception as e:
            logger.error(f"Content moderation error: {e}")
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return {
                'result': ModerationResult.ERROR.value,
                'confidence': 0.0,
                'categories': {},
                'message': f'Moderation service error: {str(e)}',
                'processing_time_ms': round(processing_time, 2)
            }
    
    async def moderate_image_prompt(
        self,
        prompt: str,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Moderate image generation prompts before sending to AI models
        
        Args:
            prompt: Image generation prompt
            user_id: User ID for tracking
            organization_id: Organization ID for tracking
            
        Returns:
            Moderation result
        """
        
        return await self.moderate_content(
            content=prompt,
            content_type=ContentType.TEXT,
            user_id=user_id,
            organization_id=organization_id,
            context={'type': 'image_prompt', 'purpose': 'generation'}
        )
    
    async def _basic_validation(self, content: str, content_type: ContentType) -> Dict[str, Any]:
        """Basic content validation checks"""
        
        # Check content length
        max_length = getattr(self.settings, 'max_content_length', 10000)
        if len(content) > max_length:
            return {
                'result': ModerationResult.REJECTED.value,
                'confidence': 1.0,
                'categories': {'length': 1.0},
                'message': f'Content too long ({len(content)} > {max_length} characters)'
            }
        
        # Check for empty content
        if not content or not content.strip():
            return {
                'result': ModerationResult.REJECTED.value,
                'confidence': 1.0,
                'categories': {'empty': 1.0},
                'message': 'Empty or whitespace-only content'
            }
        
        return {
            'result': ModerationResult.APPROVED.value,
            'confidence': 1.0,
            'categories': {},
            'message': 'Basic validation passed'
        }
    
    async def _openai_moderation(self, content: str) -> Optional[Dict[str, Any]]:
        """Use OpenAI's moderation API"""
        
        if not self.openai_client:
            return None
        
        try:
            response = await self.openai_client.moderations.create(
                input=content,
                model="text-moderation-latest"
            )
            
            result = response.results[0]
            categories = result.categories
            category_scores = result.category_scores
            
            # Check if any category exceeds threshold
            flagged_categories = {}
            max_score = 0
            
            for category, flagged in categories:
                score = getattr(category_scores, category, 0)
                max_score = max(max_score, score)
                
                # Check against our custom thresholds
                threshold = ModerationCategories.OPENAI_CATEGORIES.get(category, {}).get('threshold', 0.5)
                
                if score > threshold:
                    flagged_categories[category] = score
            
            if flagged_categories:
                return {
                    'result': ModerationResult.REJECTED.value,
                    'confidence': max_score,
                    'categories': flagged_categories,
                    'message': f'Content flagged by OpenAI moderation: {", ".join(flagged_categories.keys())}'
                }
            else:
                return {
                    'result': ModerationResult.APPROVED.value,
                    'confidence': 1.0 - max_score,
                    'categories': {},
                    'message': 'OpenAI moderation passed'
                }
                
        except Exception as e:
            logger.error(f"OpenAI moderation error: {e}")
            return {
                'result': ModerationResult.ERROR.value,
                'confidence': 0.0,
                'categories': {'api_error': 1.0},
                'message': f'OpenAI moderation API error: {str(e)}'
            }
    
    async def _pattern_matching(self, content: str, content_type: ContentType) -> Dict[str, Any]:
        """Pattern-based content detection"""
        
        flagged_patterns = {}
        content_lower = content.lower()
        
        # NSFW keywords (comprehensive list)
        nsfw_patterns = [
            r'\b(porn|pornography|xxx|adult|nsfw)\b',
            r'\b(nude|naked|nudity|topless|bottomless)\b',
            r'\b(sex|sexual|sexy|erotic|intimate)\b',
            r'\b(breast|nipple|genital|penis|vagina)\b',
            r'\b(fetish|kink|bdsm|dominatrix)\b',
            r'\b(masturbate|masturbation|orgasm|climax)\b',
            r'\b(revealing|provocative|seductive|sensual)\b',
            r'\b(undressed|unclothed|scantily)\b',
            r'\b(explicit|graphic).*\b(content|material|imagery)\b',
        ]
        
        # Violence patterns
        violence_patterns = [
            r'\b(kill|murder|death|blood|gore|violent)\b',
            r'\b(gun|weapon|knife|bomb|explosive)\b',
            r'\b(fight|attack|assault|violence)\b',
            r'\b(shoot|shooting|stabbing|killing)\b',
            r'\b(war|battlefield|combat|destruction)\b',
            r'\b(torture|abuse|brutality|carnage)\b',
        ]
        
        # Hate speech patterns
        hate_patterns = [
            r'\b(hate|racist|discrimination|prejudice)\b',
            r'\b(nazi|hitler|holocaust)\b',
            r'\b(terrorist|terrorism|extremist)\b',
        ]
        
        # Drug-related patterns
        drug_patterns = [
            r'\b(drug|cocaine|heroin|marijuana|cannabis)\b',
            r'\b(alcohol|beer|wine|drunk|intoxicated)\b',
            r'\b(smoke|smoking|cigarette|tobacco)\b',
        ]
        
        # Check all patterns
        all_patterns = {
            'nsfw': nsfw_patterns,
            'violence': violence_patterns,
            'hate': hate_patterns,
            'drugs': drug_patterns
        }
        
        for category, patterns in all_patterns.items():
            category_score = 0
            for pattern in patterns:
                matches = re.findall(pattern, content_lower)
                if matches:
                    # Higher score for NSFW and violence to be more sensitive
                    multiplier = 0.8 if category in ['nsfw', 'violence'] else 0.3
                    score = min(1.0, len(matches) * multiplier + 0.4)  # Base score of 0.4
                    category_score = max(category_score, score)
            
            # Different thresholds for different categories
            thresholds = {
                'nsfw': 0.3,      # Lower threshold for NSFW (more sensitive)
                'violence': 0.4,   # Moderate threshold for violence
                'hate': 0.5,      # Higher threshold for hate speech
                'drugs': 0.6      # Highest threshold for drugs (least sensitive)
            }
            
            threshold = thresholds.get(category, 0.5)
            if category_score > threshold:
                flagged_patterns[category] = category_score
        
        if flagged_patterns:
            max_score = max(flagged_patterns.values())
            return {
                'result': ModerationResult.FLAGGED.value if max_score < 0.8 else ModerationResult.REJECTED.value,
                'confidence': max_score,
                'categories': flagged_patterns,
                'message': f'Content flagged by pattern matching: {", ".join(flagged_patterns.keys())}'
            }
        
        return {
            'result': ModerationResult.APPROVED.value,
            'confidence': 1.0,
            'categories': {},
            'message': 'Pattern matching passed'
        }
    
    async def _nsfw_text_detection(self, content: str) -> Dict[str, Any]:
        """Specialized NSFW text detection"""
        
        # Enhanced NSFW detection using multiple approaches
        nsfw_score = 0
        
        # Check for explicit sexual terms
        explicit_terms = [
            'explicit', 'graphic', 'sexual content', 'adult material',
            'mature content', 'not safe for work', 'nsfw'
        ]
        
        content_lower = content.lower()
        for term in explicit_terms:
            if term in content_lower:
                nsfw_score += 0.4
        
        # Check for suggestive context
        suggestive_combinations = [
            (r'\b(hot|sexy|attractive)\b.*\b(woman|man|person)\b', 0.3),
            (r'\b(revealing|tight|skimpy)\b.*\b(clothing|outfit|dress)\b', 0.4),
            (r'\b(bedroom|bed|intimate)\b.*\b(scene|moment|setting)\b', 0.5),
        ]
        
        for pattern, score in suggestive_combinations:
            if re.search(pattern, content_lower):
                nsfw_score += score
        
        # Cap the score at 1.0
        nsfw_score = min(1.0, nsfw_score)
        
        if nsfw_score > 0.6:
            return {
                'result': ModerationResult.REJECTED.value,
                'confidence': nsfw_score,
                'categories': {'nsfw_content': nsfw_score},
                'message': 'Content detected as NSFW'
            }
        elif nsfw_score > 0.3:
            return {
                'result': ModerationResult.FLAGGED.value,
                'confidence': nsfw_score,
                'categories': {'nsfw_content': nsfw_score},
                'message': 'Content flagged for potential NSFW content'
            }
        
        return {
            'result': ModerationResult.APPROVED.value,
            'confidence': 1.0 - nsfw_score,
            'categories': {},
            'message': 'NSFW detection passed'
        }
    
    async def _combine_results(
        self,
        basic_result: Dict[str, Any],
        openai_result: Optional[Dict[str, Any]],
        pattern_result: Dict[str, Any],
        nsfw_result: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Combine all moderation results into final decision"""
        
        # Collect all results
        results = [basic_result, pattern_result, nsfw_result]
        if openai_result:
            results.append(openai_result)
        
        # Find the most restrictive result
        result_priority = {
            ModerationResult.REJECTED.value: 3,
            ModerationResult.FLAGGED.value: 2,
            ModerationResult.APPROVED.value: 1,
            ModerationResult.ERROR.value: 0
        }
        
        final_result = ModerationResult.APPROVED.value
        max_confidence = 0
        all_categories = {}
        all_messages = []
        
        for result in results:
            result_value = result['result']
            confidence = result['confidence']
            categories = result['categories']
            message = result['message']
            
            # Update final result based on priority
            if result_priority[result_value] > result_priority[final_result]:
                final_result = result_value
                max_confidence = confidence
            elif result_value == final_result:
                max_confidence = max(max_confidence, confidence)
            
            # Combine categories
            all_categories.update(categories)
            
            # Collect messages
            if message and 'passed' not in message.lower():
                all_messages.append(message)
        
        # Format final message
        if all_messages:
            final_message = '; '.join(all_messages)
        else:
            final_message = 'Content moderation passed all checks'
        
        return {
            'result': final_result,
            'confidence': max_confidence,
            'categories': all_categories,
            'message': final_message,
            'context': context or {}
        }
    
    async def _track_moderation_usage(
        self,
        user_id: int,
        organization_id: int,
        content_type: ContentType,
        result: Dict[str, Any]
    ):
        """Track moderation usage for billing and analytics"""
        
        if not self.usage_tracker:
            logger.debug("Usage tracking not available - skipping moderation usage tracking")
            return
            
        try:
            await self.usage_tracker.track_usage(
                user_id=user_id,
                organization_id=organization_id,
                usage_type='content_moderation',
                resource=content_type.value,
                quantity=1,
                cost_credits=0.01,  # Small credit cost for moderation
                cost_usd=0.001,    # Minimal USD cost
                metadata={
                    'result': result['result'],
                    'confidence': result['confidence'],
                    'categories': list(result['categories'].keys()),
                    'processing_time_ms': result.get('processing_time_ms', 0)
                }
            )
        except Exception as e:
            logger.error(f"Failed to track moderation usage: {e}")
    
    async def _log_moderation_result(
        self,
        content: str,
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ):
        """Log moderation results for audit and improvement"""
        
        # Only log rejected/flagged content for review
        if result['result'] in [ModerationResult.REJECTED.value, ModerationResult.FLAGGED.value]:
            logger.warning(
                f"Content moderation alert: {result['result']} "
                f"(confidence: {result['confidence']:.2f}) "
                f"Categories: {result['categories']} "
                f"Content preview: {content[:100]}..."
                f"Context: {context}"
            )
        else:
            logger.debug(f"Content moderation passed: {result['message']}")

# Global service instance
_moderation_service: Optional[ContentModerationService] = None

def get_moderation_service() -> ContentModerationService:
    """Get or create the global content moderation service instance"""
    global _moderation_service
    
    if _moderation_service is None:
        _moderation_service = ContentModerationService()
    
    return _moderation_service

async def moderate_content(
    content: str,
    content_type: ContentType = ContentType.TEXT,
    user_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function for content moderation
    
    Args:
        content: Content to moderate
        content_type: Type of content
        user_id: User ID for tracking
        organization_id: Organization ID for tracking
        context: Additional context
        
    Returns:
        Moderation result
    """
    service = get_moderation_service()
    return await service.moderate_content(content, content_type, user_id, organization_id, context)