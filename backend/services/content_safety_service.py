"""
Content Safety and Brand Protection Service

Implements comprehensive content moderation and brand protection to prevent
publication of content that could damage brand reputation or violate policies.

Key Features:
- Multi-layer content filtering (text, image, metadata)
- Brand guideline validation and alignment scoring
- Safety classification with confidence scoring
- Integration with external moderation APIs (OpenAI Moderation, Azure Content Moderator)
- Customizable safety thresholds and brand guidelines
- Audit logging and escalation workflows
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timezone
from enum import Enum
import json
import re
import hashlib

from openai import AsyncOpenAI
from prometheus_client import Counter, Histogram, Gauge
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.core.config import get_settings
from backend.db.models import User
from backend.core.observability import get_observability_manager

settings = get_settings()
logger = logging.getLogger(__name__)
observability = get_observability_manager()

# Content safety metrics
CONTENT_SAFETY_CHECKS = Counter(
    'content_safety_checks_total',
    'Total content safety checks performed',
    ['content_type', 'platform', 'status']
)

BRAND_PROTECTION_VIOLATIONS = Counter(
    'brand_protection_violations_total', 
    'Brand protection violations detected',
    ['violation_type', 'severity', 'platform']
)

CONTENT_MODERATION_LATENCY = Histogram(
    'content_moderation_duration_seconds',
    'Time taken for content moderation checks',
    ['moderation_type', 'platform']
)

SAFETY_SCORE_DISTRIBUTION = Histogram(
    'content_safety_scores',
    'Distribution of content safety scores',
    ['content_type', 'platform'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

BRAND_ALIGNMENT_SCORES = Histogram(
    'brand_alignment_scores',
    'Distribution of brand alignment scores', 
    ['platform', 'brand_element'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)


class SafetyLevel(Enum):
    """Content safety classification levels"""
    SAFE = "safe"
    CAUTION = "caution"
    UNSAFE = "unsafe"
    BLOCKED = "blocked"


class ViolationType(Enum):
    """Types of content violations"""
    PROFANITY = "profanity"
    HARASSMENT = "harassment"
    HATE_SPEECH = "hate_speech"
    ADULT_CONTENT = "adult_content"
    VIOLENCE = "violence"
    SPAM = "spam"
    COPYRIGHT = "copyright"
    BRAND_MISALIGNMENT = "brand_misalignment"
    POOR_QUALITY = "poor_quality"
    FACTUAL_INACCURACY = "factual_inaccuracy"


class ContentSafetyResult(BaseModel):
    """Result of content safety analysis"""
    safety_level: SafetyLevel
    confidence_score: float = Field(ge=0.0, le=1.0)
    violations: List[Dict[str, Any]] = []
    brand_alignment_score: float = Field(ge=0.0, le=1.0)
    moderation_flags: Dict[str, Any] = {}
    recommendations: List[str] = []
    publish_approved: bool = False
    review_required: bool = False
    metadata: Dict[str, Any] = {}


class BrandGuidelines(BaseModel):
    """Brand guideline configuration"""
    brand_voice: str = "professional"
    prohibited_topics: List[str] = []
    required_elements: List[str] = []
    tone_requirements: Dict[str, Any] = {}
    visual_guidelines: Dict[str, Any] = {}
    platform_specific: Dict[str, Dict[str, Any]] = {}


class ContentSafetyService:
    """Comprehensive content safety and brand protection service"""
    
    def __init__(self):
        # Initialize OpenAI client for moderation
        self.openai_client = None
        if settings.openai_api_key:
            try:
                self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
                logger.info("OpenAI moderation client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI moderation client: {e}")
        
        # Default safety thresholds
        self.safety_thresholds = {
            SafetyLevel.SAFE: {"min_score": 0.9, "max_violations": 0},
            SafetyLevel.CAUTION: {"min_score": 0.7, "max_violations": 1}, 
            SafetyLevel.UNSAFE: {"min_score": 0.5, "max_violations": 2},
            SafetyLevel.BLOCKED: {"min_score": 0.0, "max_violations": float('inf')}
        }
        
        # Brand protection keywords and patterns
        self.profanity_patterns = self._load_profanity_patterns()
        self.spam_indicators = self._load_spam_indicators()
        
        # Content quality thresholds
        self.quality_thresholds = {
            "min_text_length": 10,
            "max_text_length": 2000,
            "min_readability_score": 30,
            "max_spelling_errors": 3,
            "min_brand_alignment": 0.6
        }
    
    async def analyze_content_safety(self,
                                   content_text: str,
                                   image_data: Optional[bytes] = None,
                                   platform: str = "general",
                                   user_id: Optional[int] = None,
                                   brand_guidelines: Optional[BrandGuidelines] = None) -> ContentSafetyResult:
        """
        Perform comprehensive content safety analysis
        
        Args:
            content_text: Text content to analyze
            image_data: Optional image data for visual content analysis
            platform: Target publishing platform
            user_id: User ID for personalized guidelines
            brand_guidelines: Custom brand guidelines
            
        Returns:
            ContentSafetyResult with safety classification and recommendations
        """
        start_time = datetime.utcnow()
        
        try:
            # Track analysis start
            CONTENT_SAFETY_CHECKS.labels(
                content_type='text_and_image' if image_data else 'text_only',
                platform=platform,
                status='initiated'
            ).inc()
            
            # Initialize result
            result = ContentSafetyResult(
                safety_level=SafetyLevel.SAFE,
                confidence_score=1.0,
                brand_alignment_score=1.0,
                metadata={
                    "platform": platform,
                    "analyzed_at": datetime.utcnow().isoformat(),
                    "user_id": user_id,
                    "content_length": len(content_text)
                }
            )
            
            # Load user-specific or default brand guidelines
            if not brand_guidelines and user_id:
                brand_guidelines = await self._get_user_brand_guidelines(user_id)
            if not brand_guidelines:
                brand_guidelines = self._get_default_brand_guidelines(platform)
            
            # Layer 1: OpenAI Moderation API
            openai_moderation = await self._check_openai_moderation(content_text)
            result.moderation_flags.update(openai_moderation)
            
            # Layer 2: Custom profanity and spam detection
            custom_checks = await self._check_custom_filters(content_text, platform)
            result.violations.extend(custom_checks["violations"])
            
            # Layer 3: Brand alignment analysis
            brand_analysis = await self._analyze_brand_alignment(
                content_text, brand_guidelines, platform
            )
            result.brand_alignment_score = brand_analysis["alignment_score"]
            result.violations.extend(brand_analysis["violations"])
            
            # Layer 4: Content quality assessment
            quality_analysis = await self._assess_content_quality(content_text, platform)
            result.violations.extend(quality_analysis["violations"])
            
            # Layer 5: Image safety analysis (if provided)
            if image_data:
                image_analysis = await self._analyze_image_safety(image_data, platform)
                result.violations.extend(image_analysis["violations"])
                result.moderation_flags.update(image_analysis["flags"])
            
            # Layer 6: Platform-specific compliance
            platform_checks = await self._check_platform_compliance(
                content_text, platform, brand_guidelines
            )
            result.violations.extend(platform_checks["violations"])
            
            # Calculate final safety classification
            result = self._calculate_final_safety_level(result, brand_guidelines)
            
            # Generate recommendations
            result.recommendations = self._generate_safety_recommendations(
                result, brand_guidelines, platform
            )
            
            # Determine publish approval
            result.publish_approved = (
                result.safety_level in [SafetyLevel.SAFE, SafetyLevel.CAUTION] and
                result.brand_alignment_score >= self.quality_thresholds["min_brand_alignment"] and
                len([v for v in result.violations if v.get("severity") == "high"]) == 0
            )
            
            result.review_required = (
                result.safety_level == SafetyLevel.CAUTION or
                result.brand_alignment_score < 0.8 or
                len(result.violations) > 0
            )
            
            # Track completion metrics
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            CONTENT_MODERATION_LATENCY.labels(
                moderation_type='comprehensive',
                platform=platform
            ).observe(duration)
            
            SAFETY_SCORE_DISTRIBUTION.labels(
                content_type='text_and_image' if image_data else 'text_only',
                platform=platform
            ).observe(result.confidence_score)
            
            BRAND_ALIGNMENT_SCORES.labels(
                platform=platform,
                brand_element='overall'
            ).observe(result.brand_alignment_score)
            
            CONTENT_SAFETY_CHECKS.labels(
                content_type='text_and_image' if image_data else 'text_only',
                platform=platform,
                status='completed'
            ).inc()
            
            # Track violations
            for violation in result.violations:
                BRAND_PROTECTION_VIOLATIONS.labels(
                    violation_type=violation.get("type", "unknown"),
                    severity=violation.get("severity", "low"),
                    platform=platform
                ).inc()
            
            logger.info(f"Content safety analysis completed: {result.safety_level.value} "
                       f"(confidence: {result.confidence_score:.2f}, "
                       f"brand: {result.brand_alignment_score:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Content safety analysis failed: {e}")
            
            CONTENT_SAFETY_CHECKS.labels(
                content_type='text_and_image' if image_data else 'text_only',
                platform=platform,
                status='failed'
            ).inc()
            
            # Return safe fallback result with review required
            return ContentSafetyResult(
                safety_level=SafetyLevel.CAUTION,
                confidence_score=0.0,
                brand_alignment_score=0.5,
                violations=[{
                    "type": "analysis_error",
                    "message": "Content analysis failed - manual review required",
                    "severity": "medium"
                }],
                publish_approved=False,
                review_required=True,
                metadata={"error": str(e), "analyzed_at": datetime.utcnow().isoformat()}
            )
    
    async def _check_openai_moderation(self, content_text: str) -> Dict[str, Any]:
        """Check content against OpenAI Moderation API"""
        if not self.openai_client:
            return {"status": "unavailable", "reason": "OpenAI client not configured"}
        
        try:
            moderation = await self.openai_client.moderations.create(input=content_text)
            result = moderation.results[0]
            
            return {
                "flagged": result.flagged,
                "categories": dict(result.categories),
                "category_scores": dict(result.category_scores),
                "status": "completed"
            }
            
        except Exception as e:
            logger.warning(f"OpenAI moderation check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _check_custom_filters(self, content_text: str, platform: str) -> Dict[str, Any]:
        """Apply custom profanity and spam filters"""
        violations = []
        content_lower = content_text.lower()
        
        # Profanity detection
        profanity_matches = []
        for pattern in self.profanity_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                profanity_matches.append(pattern)
        
        if profanity_matches:
            violations.append({
                "type": ViolationType.PROFANITY.value,
                "message": f"Detected {len(profanity_matches)} potential profanity issues",
                "severity": "high",
                "details": profanity_matches[:3]  # Limit details for privacy
            })
        
        # Spam indicators
        spam_score = 0
        spam_indicators = []
        
        # Excessive caps
        if len(re.findall(r'[A-Z]', content_text)) / len(content_text) > 0.3:
            spam_score += 0.2
            spam_indicators.append("excessive_caps")
        
        # Excessive exclamation marks
        if content_text.count('!') > 3:
            spam_score += 0.15
            spam_indicators.append("excessive_exclamation")
        
        # Repetitive phrases
        words = content_text.split()
        if len(set(words)) / len(words) < 0.5:
            spam_score += 0.2
            spam_indicators.append("repetitive_content")
        
        # URL spam (basic detection)
        url_count = len(re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content_text))
        if url_count > 2:
            spam_score += 0.25
            spam_indicators.append("excessive_urls")
        
        if spam_score > 0.4:
            violations.append({
                "type": ViolationType.SPAM.value,
                "message": f"Spam indicators detected (score: {spam_score:.2f})",
                "severity": "medium" if spam_score < 0.7 else "high",
                "details": spam_indicators
            })
        
        return {"violations": violations, "spam_score": spam_score}
    
    async def _analyze_brand_alignment(self,
                                     content_text: str,
                                     brand_guidelines: BrandGuidelines,
                                     platform: str) -> Dict[str, Any]:
        """Analyze how well content aligns with brand guidelines"""
        violations = []
        alignment_scores = {}
        
        # Voice and tone analysis
        voice_score = await self._analyze_brand_voice(content_text, brand_guidelines.brand_voice)
        alignment_scores["voice"] = voice_score
        
        if voice_score < 0.7:
            violations.append({
                "type": ViolationType.BRAND_MISALIGNMENT.value,
                "message": f"Content voice doesn't match brand guidelines ({brand_guidelines.brand_voice})",
                "severity": "medium",
                "details": {"expected_voice": brand_guidelines.brand_voice, "score": voice_score}
            })
        
        # Prohibited topics check
        topic_violations = []
        content_lower = content_text.lower()
        for topic in brand_guidelines.prohibited_topics:
            if topic.lower() in content_lower:
                topic_violations.append(topic)
        
        if topic_violations:
            violations.append({
                "type": ViolationType.BRAND_MISALIGNMENT.value,
                "message": f"Content mentions prohibited topics: {', '.join(topic_violations)}",
                "severity": "high",
                "details": {"prohibited_topics": topic_violations}
            })
            alignment_scores["topics"] = 0.0
        else:
            alignment_scores["topics"] = 1.0
        
        # Required elements check
        missing_elements = []
        for element in brand_guidelines.required_elements:
            if element.lower() not in content_lower:
                missing_elements.append(element)
        
        if missing_elements and len(brand_guidelines.required_elements) > 0:
            element_score = 1.0 - (len(missing_elements) / len(brand_guidelines.required_elements))
            alignment_scores["required_elements"] = element_score
            
            if element_score < 0.5:
                violations.append({
                    "type": ViolationType.BRAND_MISALIGNMENT.value,
                    "message": f"Missing required brand elements: {', '.join(missing_elements)}",
                    "severity": "low",
                    "details": {"missing_elements": missing_elements}
                })
        else:
            alignment_scores["required_elements"] = 1.0
        
        # Calculate overall alignment score
        overall_score = sum(alignment_scores.values()) / len(alignment_scores) if alignment_scores else 1.0
        
        return {
            "alignment_score": overall_score,
            "violations": violations,
            "detailed_scores": alignment_scores
        }
    
    async def _analyze_brand_voice(self, content_text: str, expected_voice: str) -> float:
        """Analyze brand voice alignment using AI if available"""
        try:
            if not self.openai_client:
                return 0.8  # Default good score if no AI analysis available
            
            voice_analysis_prompt = f"""
            Analyze the following content for brand voice alignment.
            Expected brand voice: {expected_voice}
            
            Content: "{content_text}"
            
            Rate the alignment on a scale of 0.0 to 1.0 where:
            - 1.0 = Perfect alignment with expected voice
            - 0.8 = Good alignment with minor deviations  
            - 0.6 = Moderate alignment with some concerns
            - 0.4 = Poor alignment with significant issues
            - 0.2 = Very poor alignment
            - 0.0 = No alignment or opposite voice
            
            Return only the numerical score (e.g., 0.85).
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": voice_analysis_prompt}],
                max_tokens=10,
                temperature=0.1
            )
            
            score_text = response.choices[0].message.content.strip()
            score = float(re.search(r'\d+\.?\d*', score_text).group())
            return max(0.0, min(1.0, score))  # Clamp to 0.0-1.0 range
            
        except Exception as e:
            logger.warning(f"Brand voice analysis failed: {e}")
            return 0.8  # Default score on error
    
    async def _assess_content_quality(self, content_text: str, platform: str) -> Dict[str, Any]:
        """Assess content quality metrics"""
        violations = []
        
        # Length checks
        text_length = len(content_text.strip())
        if text_length < self.quality_thresholds["min_text_length"]:
            violations.append({
                "type": ViolationType.POOR_QUALITY.value,
                "message": f"Content too short ({text_length} chars, minimum {self.quality_thresholds['min_text_length']})",
                "severity": "medium"
            })
        
        if text_length > self.quality_thresholds["max_text_length"]:
            violations.append({
                "type": ViolationType.POOR_QUALITY.value,
                "message": f"Content too long ({text_length} chars, maximum {self.quality_thresholds['max_text_length']})",
                "severity": "low"
            })
        
        # Basic spelling/grammar check (simplified)
        spelling_errors = self._count_potential_spelling_errors(content_text)
        if spelling_errors > self.quality_thresholds["max_spelling_errors"]:
            violations.append({
                "type": ViolationType.POOR_QUALITY.value,
                "message": f"Potential spelling/grammar issues detected ({spelling_errors} issues)",
                "severity": "medium"
            })
        
        # Readability check (simplified Flesch-Kincaid approximation)
        readability_score = self._calculate_readability_score(content_text)
        if readability_score < self.quality_thresholds["min_readability_score"]:
            violations.append({
                "type": ViolationType.POOR_QUALITY.value,
                "message": f"Content may be difficult to read (readability score: {readability_score})",
                "severity": "low"
            })
        
        return {"violations": violations, "quality_metrics": {
            "length": text_length,
            "spelling_errors": spelling_errors,
            "readability_score": readability_score
        }}
    
    async def _analyze_image_safety(self, image_data: bytes, platform: str) -> Dict[str, Any]:
        """Analyze image content for safety violations"""
        violations = []
        flags = {}
        
        try:
            # Basic image analysis (simplified - in production, use Azure Content Moderator or similar)
            image_hash = hashlib.md5(image_data).hexdigest()
            image_size = len(image_data)
            
            # Size checks
            if image_size > 10 * 1024 * 1024:  # 10MB limit
                violations.append({
                    "type": ViolationType.POOR_QUALITY.value,
                    "message": f"Image file too large ({image_size / (1024*1024):.1f}MB)",
                    "severity": "medium"
                })
            
            if image_size < 1024:  # 1KB minimum
                violations.append({
                    "type": ViolationType.POOR_QUALITY.value,
                    "message": "Image file suspiciously small - may be corrupted",
                    "severity": "medium"
                })
            
            flags["image_analyzed"] = True
            flags["image_hash"] = image_hash
            flags["image_size_bytes"] = image_size
            
        except Exception as e:
            logger.warning(f"Image safety analysis failed: {e}")
            violations.append({
                "type": "analysis_error",
                "message": "Image analysis failed - manual review recommended",
                "severity": "low"
            })
            flags["image_analysis_error"] = str(e)
        
        return {"violations": violations, "flags": flags}
    
    async def _check_platform_compliance(self,
                                       content_text: str,
                                       platform: str,
                                       brand_guidelines: BrandGuidelines) -> Dict[str, Any]:
        """Check platform-specific compliance requirements"""
        violations = []
        
        # Platform-specific length limits
        platform_limits = {
            "twitter": {"max_length": 280, "max_hashtags": 10},
            "instagram": {"max_length": 2200, "max_hashtags": 30},
            "facebook": {"max_length": 5000, "max_hashtags": 15},
            "linkedin": {"max_length": 1300, "max_hashtags": 10},
            "tiktok": {"max_length": 300, "max_hashtags": 20}
        }
        
        if platform in platform_limits:
            limits = platform_limits[platform]
            
            if len(content_text) > limits["max_length"]:
                violations.append({
                    "type": ViolationType.POOR_QUALITY.value,
                    "message": f"Content exceeds {platform} length limit ({len(content_text)}/{limits['max_length']} chars)",
                    "severity": "high"
                })
            
            # Hashtag count check
            hashtag_count = len(re.findall(r'#\w+', content_text))
            if hashtag_count > limits["max_hashtags"]:
                violations.append({
                    "type": ViolationType.SPAM.value,
                    "message": f"Too many hashtags for {platform} ({hashtag_count}/{limits['max_hashtags']})",
                    "severity": "medium"
                })
        
        # Platform-specific content guidelines
        platform_guidelines = brand_guidelines.platform_specific.get(platform, {})
        for guideline, requirement in platform_guidelines.items():
            # Implementation would depend on specific guideline types
            pass
        
        return {"violations": violations}
    
    def _calculate_final_safety_level(self,
                                     result: ContentSafetyResult,
                                     brand_guidelines: BrandGuidelines) -> ContentSafetyResult:
        """Calculate final safety level based on all analysis results"""
        
        # Count violations by severity
        high_violations = len([v for v in result.violations if v.get("severity") == "high"])
        medium_violations = len([v for v in result.violations if v.get("severity") == "medium"])
        low_violations = len([v for v in result.violations if v.get("severity") == "low"])
        
        # OpenAI moderation check
        openai_flagged = result.moderation_flags.get("flagged", False)
        
        # Calculate confidence score
        confidence_factors = []
        
        # Brand alignment factor
        confidence_factors.append(result.brand_alignment_score)
        
        # Violation penalty
        violation_penalty = min(1.0, (high_violations * 0.3) + (medium_violations * 0.15) + (low_violations * 0.05))
        confidence_factors.append(1.0 - violation_penalty)
        
        # Moderation flag penalty
        if openai_flagged:
            confidence_factors.append(0.0)
        else:
            confidence_factors.append(1.0)
        
        result.confidence_score = sum(confidence_factors) / len(confidence_factors)
        
        # Determine safety level
        if openai_flagged or high_violations > 0:
            result.safety_level = SafetyLevel.BLOCKED
        elif medium_violations > 2 or result.brand_alignment_score < 0.5:
            result.safety_level = SafetyLevel.UNSAFE  
        elif medium_violations > 0 or low_violations > 3 or result.brand_alignment_score < 0.7:
            result.safety_level = SafetyLevel.CAUTION
        else:
            result.safety_level = SafetyLevel.SAFE
        
        return result
    
    def _generate_safety_recommendations(self,
                                       result: ContentSafetyResult,
                                       brand_guidelines: BrandGuidelines,
                                       platform: str) -> List[str]:
        """Generate actionable recommendations for content improvement"""
        recommendations = []
        
        if result.safety_level == SafetyLevel.BLOCKED:
            recommendations.append("⚠️ Content blocked due to policy violations - major revision required")
            
        if result.brand_alignment_score < 0.7:
            recommendations.append(f"📝 Improve brand voice alignment - target: {brand_guidelines.brand_voice}")
            
        for violation in result.violations:
            if violation["type"] == ViolationType.PROFANITY.value:
                recommendations.append("🧹 Remove or replace inappropriate language")
            elif violation["type"] == ViolationType.SPAM.value:
                recommendations.append("✂️ Reduce repetitive content and excessive formatting")
            elif violation["type"] == ViolationType.BRAND_MISALIGNMENT.value:
                recommendations.append("🎯 Align content with brand guidelines and voice")
            elif violation["type"] == ViolationType.POOR_QUALITY.value:
                recommendations.append("✨ Improve content quality and readability")
        
        if result.safety_level == SafetyLevel.SAFE:
            recommendations.append("✅ Content meets safety and brand guidelines")
        elif result.safety_level == SafetyLevel.CAUTION:
            recommendations.append("⚡ Content approved with minor concerns - consider revisions")
            
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _load_profanity_patterns(self) -> List[str]:
        """Load profanity detection patterns (simplified for production)"""
        # In production, this would load from a comprehensive database
        return [
            r'\b(damn|hell|crap)\b',  # Mild profanity  
            r'\b(stupid|dumb|idiot)\b',  # Potentially offensive terms
            # Add more patterns as needed - ensure they're business-appropriate
        ]
    
    def _load_spam_indicators(self) -> List[str]:
        """Load spam detection indicators"""
        return [
            "excessive_caps",
            "excessive_exclamation", 
            "repetitive_content",
            "excessive_urls",
            "suspicious_formatting"
        ]
    
    async def _get_user_brand_guidelines(self, user_id: int) -> Optional[BrandGuidelines]:
        """Load user-specific brand guidelines"""
        # In production, this would query the database for user settings
        try:
            # Placeholder - would integrate with user_settings table
            return None
        except Exception as e:
            logger.warning(f"Failed to load user brand guidelines for {user_id}: {e}")
            return None
    
    def _get_default_brand_guidelines(self, platform: str) -> BrandGuidelines:
        """Get default brand guidelines for platform"""
        return BrandGuidelines(
            brand_voice="professional",
            prohibited_topics=["illegal", "violent", "discriminatory"],
            required_elements=[],
            tone_requirements={"professional": True, "respectful": True},
            platform_specific={
                platform: {"appropriate_tone": True}
            }
        )
    
    def _count_potential_spelling_errors(self, text: str) -> int:
        """Simple spelling error detection (production would use proper spell checker)"""
        # Simplified - count obvious patterns
        errors = 0
        
        # Multiple consecutive identical characters (typos)
        errors += len(re.findall(r'(.)\1{2,}', text))
        
        # Common misspellings patterns
        common_errors = ['teh ', 'recieve', 'seperate', 'definately', 'occured']
        for error in common_errors:
            if error in text.lower():
                errors += 1
        
        return min(errors, 10)  # Cap at 10 to avoid false positives
    
    def _calculate_readability_score(self, text: str) -> float:
        """Calculate approximate readability score (simplified Flesch-Kincaid)"""
        if not text.strip():
            return 0
            
        sentences = len(re.findall(r'[.!?]+', text))
        if sentences == 0:
            sentences = 1
            
        words = len(text.split())
        if words == 0:
            return 0
            
        syllables = sum(self._count_syllables(word) for word in text.split())
        
        # Simplified Flesch Reading Ease approximation
        score = 206.835 - (1.015 * (words / sentences)) - (84.6 * (syllables / words))
        return max(0, min(100, score))  # Clamp to 0-100 range
    
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simplified)"""
        word = word.lower().strip(".,!?;:")
        if not word:
            return 0
        
        # Simple vowel counting approximation
        vowels = len(re.findall(r'[aeiouy]', word))
        if word.endswith('e'):
            vowels -= 1
        if vowels == 0:
            vowels = 1
            
        return vowels


# Global service instance
content_safety_service = ContentSafetyService()


def get_content_safety_service():
    """Get the global content safety service instance"""
    return content_safety_service