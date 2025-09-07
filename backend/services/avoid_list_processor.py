"""
Avoid List Processor

Centralized service for processing and managing content safety avoid lists
across all AI model templates. Implements negative prompt support and
content filtering for Agent 1 compliance requirements.
"""

import logging
import re
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class ContentCategory(Enum):
    """Categories of content to avoid"""
    NSFW = "nsfw"
    VIOLENCE = "violence"
    HATE_SPEECH = "hate_speech"
    COPYRIGHTED = "copyrighted"
    MISINFORMATION = "misinformation"
    ILLEGAL = "illegal"
    SPAM = "spam"
    QUALITY_ISSUES = "quality_issues"
    PLATFORM_VIOLATIONS = "platform_violations"

class ProcessingMode(Enum):
    """Modes for processing avoid list content"""
    FILTER_OUT = "filter_out"  # Remove/replace content
    NEGATIVE_PROMPT = "negative_prompt"  # Add to negative prompt
    POSITIVE_GUIDANCE = "positive_guidance"  # Convert to positive guidance
    BLOCK_REQUEST = "block_request"  # Block the entire request

@dataclass
class AvoidListRule:
    """Rule for avoiding specific content"""
    pattern: str
    category: ContentCategory
    severity: str  # "low", "medium", "high", "critical"
    processing_mode: ProcessingMode
    replacement_text: Optional[str] = None
    description: Optional[str] = None
    platforms: Optional[List[str]] = None  # Specific platforms this applies to
    
class AvoidListProcessor:
    """Service for processing content safety avoid lists"""
    
    def __init__(self):
        self.rules = self._initialize_default_rules()
        self.platform_specific_rules = self._initialize_platform_rules()
        self.quality_rules = self._initialize_quality_rules()
        
        # Compile regex patterns for performance
        self.compiled_patterns = {}
        self._compile_patterns()
    
    def _initialize_default_rules(self) -> List[AvoidListRule]:
        """Initialize default content safety rules"""
        return [
            # NSFW Content
            AvoidListRule(
                pattern=r'\b(?:nsfw|explicit|adult|sexual|nude|naked|xxx|porn)\b',
                category=ContentCategory.NSFW,
                severity="critical",
                processing_mode=ProcessingMode.BLOCK_REQUEST,
                description="Explicit adult content"
            ),
            AvoidListRule(
                pattern=r'\b(?:sexy|provocative|sensual|erotic)\b',
                category=ContentCategory.NSFW,
                severity="medium",
                processing_mode=ProcessingMode.FILTER_OUT,
                replacement_text="elegant and artistic",
                description="Suggestive content"
            ),
            
            # Violence and Harm
            AvoidListRule(
                pattern=r'\b(?:violence|violent|kill|murder|death|blood|gore|weapon|gun|knife|sword)\b',
                category=ContentCategory.VIOLENCE,
                severity="high",
                processing_mode=ProcessingMode.FILTER_OUT,
                replacement_text="peaceful scene",
                description="Violence and weapons"
            ),
            AvoidListRule(
                pattern=r'\b(?:injury|hurt|harm|pain|suffering|torture|abuse)\b',
                category=ContentCategory.VIOLENCE,
                severity="medium",
                processing_mode=ProcessingMode.FILTER_OUT,
                replacement_text="comfort and care",
                description="Harm and suffering"
            ),
            
            # Hate Speech and Discrimination
            AvoidListRule(
                pattern=r'\b(?:hate|racist|sexist|homophobic|discriminatory|offensive)\b',
                category=ContentCategory.HATE_SPEECH,
                severity="critical",
                processing_mode=ProcessingMode.BLOCK_REQUEST,
                description="Hate speech and discrimination"
            ),
            
            # Copyrighted Content
            AvoidListRule(
                pattern=r'\b(?:disney|marvel|dc\s+comics|nintendo|pokemon|star\s+wars|harry\s+potter)\b',
                category=ContentCategory.COPYRIGHTED,
                severity="high",
                processing_mode=ProcessingMode.FILTER_OUT,
                replacement_text="original character",
                description="Copyrighted characters and franchises"
            ),
            AvoidListRule(
                pattern=r'\b(?:coca\s*cola|pepsi|nike|adidas|apple|microsoft|google|facebook)\b',
                category=ContentCategory.COPYRIGHTED,
                severity="medium",
                processing_mode=ProcessingMode.FILTER_OUT,
                replacement_text="generic brand",
                description="Trademarked brands"
            ),
            
            # Misinformation
            AvoidListRule(
                pattern=r'\b(?:fake\s+news|conspiracy|hoax|propaganda|misleading)\b',
                category=ContentCategory.MISINFORMATION,
                severity="medium",
                processing_mode=ProcessingMode.NEGATIVE_PROMPT,
                description="Misinformation and fake content"
            ),
            
            # Illegal Activities
            AvoidListRule(
                pattern=r'\b(?:illegal|drug|narcotic|criminal|fraud|theft|piracy)\b',
                category=ContentCategory.ILLEGAL,
                severity="critical",
                processing_mode=ProcessingMode.BLOCK_REQUEST,
                description="Illegal activities"
            ),
            
            # Quality Issues
            AvoidListRule(
                pattern=r'\b(?:low\s+quality|blurry|pixelated|distorted|amateur|poor)\b',
                category=ContentCategory.QUALITY_ISSUES,
                severity="low",
                processing_mode=ProcessingMode.NEGATIVE_PROMPT,
                description="Quality issues"
            ),
            AvoidListRule(
                pattern=r'\b(?:watermark|signature|logo|brand|copyright\s+symbol)\b',
                category=ContentCategory.QUALITY_ISSUES,
                severity="medium",
                processing_mode=ProcessingMode.NEGATIVE_PROMPT,
                description="Unwanted overlays and marks"
            )
        ]
    
    def _initialize_platform_rules(self) -> Dict[str, List[AvoidListRule]]:
        """Initialize platform-specific rules"""
        return {
            "instagram": [
                AvoidListRule(
                    pattern=r'\b(?:copyright\s+violation|brand\s+infringement|low\s+engagement)\b',
                    category=ContentCategory.PLATFORM_VIOLATIONS,
                    severity="medium",
                    processing_mode=ProcessingMode.NEGATIVE_PROMPT,
                    description="Instagram policy violations",
                    platforms=["instagram"]
                ),
                AvoidListRule(
                    pattern=r'\b(?:boring|uninteresting|static|dull)\b',
                    category=ContentCategory.QUALITY_ISSUES,
                    severity="low",
                    processing_mode=ProcessingMode.FILTER_OUT,
                    replacement_text="vibrant and engaging",
                    platforms=["instagram"]
                )
            ],
            
            "twitter": [
                AvoidListRule(
                    pattern=r'\b(?:misinformation|political\s+bias|controversial\s+imagery)\b',
                    category=ContentCategory.MISINFORMATION,
                    severity="high",
                    processing_mode=ProcessingMode.NEGATIVE_PROMPT,
                    description="Twitter content policy",
                    platforms=["twitter"]
                )
            ],
            
            "facebook": [
                AvoidListRule(
                    pattern=r'\b(?:fake|misleading|clickbait)\b',
                    category=ContentCategory.MISINFORMATION,
                    severity="medium",
                    processing_mode=ProcessingMode.NEGATIVE_PROMPT,
                    description="Facebook community standards",
                    platforms=["facebook"]
                )
            ],
            
            "linkedin": [
                AvoidListRule(
                    pattern=r'\b(?:unprofessional|casual\s+inappropriate|personal\s+life)\b',
                    category=ContentCategory.PLATFORM_VIOLATIONS,
                    severity="medium",
                    processing_mode=ProcessingMode.FILTER_OUT,
                    replacement_text="professional and business-appropriate",
                    description="LinkedIn professional standards",
                    platforms=["linkedin"]
                )
            ],
            
            "tiktok": [
                AvoidListRule(
                    pattern=r'\b(?:static|boring|outdated|old\s+trend)\b',
                    category=ContentCategory.QUALITY_ISSUES,
                    severity="low",
                    processing_mode=ProcessingMode.FILTER_OUT,
                    replacement_text="dynamic and trending",
                    description="TikTok engagement optimization",
                    platforms=["tiktok"]
                )
            ],
            
            "youtube": [
                AvoidListRule(
                    pattern=r'\b(?:clickbait|misleading\s+thumbnail|fake\s+content)\b',
                    category=ContentCategory.MISINFORMATION,
                    severity="medium",
                    processing_mode=ProcessingMode.NEGATIVE_PROMPT,
                    description="YouTube content policies",
                    platforms=["youtube"]
                )
            ]
        }
    
    def _initialize_quality_rules(self) -> Dict[str, List[AvoidListRule]]:
        """Initialize quality-based rules"""
        return {
            "basic": [],
            "standard": [
                AvoidListRule(
                    pattern=r'\b(?:low\s+resolution|compressed|artifact)\b',
                    category=ContentCategory.QUALITY_ISSUES,
                    severity="low",
                    processing_mode=ProcessingMode.NEGATIVE_PROMPT,
                    description="Standard quality requirements"
                )
            ],
            "premium": [
                AvoidListRule(
                    pattern=r'\b(?:amateur|unprofessional|poor\s+composition)\b',
                    category=ContentCategory.QUALITY_ISSUES,
                    severity="medium",
                    processing_mode=ProcessingMode.NEGATIVE_PROMPT,
                    description="Premium quality requirements"
                )
            ],
            "ultra": [
                AvoidListRule(
                    pattern=r'\b(?:noise|grain|blur|overexposed|underexposed|color\s+banding)\b',
                    category=ContentCategory.QUALITY_ISSUES,
                    severity="high",
                    processing_mode=ProcessingMode.NEGATIVE_PROMPT,
                    description="Ultra quality requirements"
                )
            ]
        }
    
    def _compile_patterns(self):
        """Compile regex patterns for better performance"""
        all_rules = self.rules.copy()
        
        # Add platform-specific rules
        for platform_rules in self.platform_specific_rules.values():
            all_rules.extend(platform_rules)
        
        # Add quality rules
        for quality_rules in self.quality_rules.values():
            all_rules.extend(quality_rules)
        
        for rule in all_rules:
            try:
                self.compiled_patterns[rule.pattern] = re.compile(rule.pattern, re.IGNORECASE | re.MULTILINE)
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{rule.pattern}': {e}")
    
    def process_content(self, content: str, platform: Optional[str] = None, 
                       quality_level: Optional[str] = None, 
                       strict_mode: bool = True) -> Dict[str, Any]:
        """Process content through avoid list filters"""
        
        result = {
            "original_content": content,
            "processed_content": content,
            "blocked": False,
            "violations": [],
            "replacements": [],
            "negative_prompts": [],
            "warnings": []
        }
        
        # Get applicable rules
        applicable_rules = self._get_applicable_rules(platform, quality_level)
        
        processed_content = content
        
        for rule in applicable_rules:
            pattern = self.compiled_patterns.get(rule.pattern)
            if not pattern:
                continue
            
            matches = pattern.findall(processed_content)
            if matches:
                violation = {
                    "category": rule.category.value,
                    "severity": rule.severity,
                    "description": rule.description,
                    "matches": matches,
                    "processing_mode": rule.processing_mode.value
                }
                result["violations"].append(violation)
                
                # Apply processing based on mode
                if rule.processing_mode == ProcessingMode.BLOCK_REQUEST:
                    if strict_mode or rule.severity == "critical":
                        result["blocked"] = True
                        result["warnings"].append(f"Content blocked due to {rule.category.value}: {rule.description}")
                        break
                
                elif rule.processing_mode == ProcessingMode.FILTER_OUT:
                    if rule.replacement_text:
                        old_content = processed_content
                        processed_content = pattern.sub(rule.replacement_text, processed_content)
                        result["replacements"].append({
                            "original": matches,
                            "replacement": rule.replacement_text,
                            "category": rule.category.value
                        })
                        logger.info(f"Content filtered: {rule.category.value} - {len(matches)} matches replaced")
                
                elif rule.processing_mode == ProcessingMode.NEGATIVE_PROMPT:
                    negative_items = [match for match in matches if match not in result["negative_prompts"]]
                    result["negative_prompts"].extend(negative_items)
                
                elif rule.processing_mode == ProcessingMode.POSITIVE_GUIDANCE:
                    # Convert negative to positive guidance
                    if rule.replacement_text:
                        guidance = f"ensure {rule.replacement_text} instead of {', '.join(matches)}"
                        result["negative_prompts"].append(guidance)
        
        result["processed_content"] = processed_content
        
        # Log processing summary
        if result["violations"]:
            logger.info(f"Content processing: {len(result['violations'])} violations found, "
                       f"{len(result['replacements'])} replacements made, "
                       f"blocked: {result['blocked']}")
        
        return result
    
    def _get_applicable_rules(self, platform: Optional[str], quality_level: Optional[str]) -> List[AvoidListRule]:
        """Get rules applicable to the given platform and quality level"""
        applicable_rules = self.rules.copy()
        
        # Add platform-specific rules
        if platform and platform in self.platform_specific_rules:
            applicable_rules.extend(self.platform_specific_rules[platform])
        
        # Add quality-specific rules
        if quality_level and quality_level in self.quality_rules:
            applicable_rules.extend(self.quality_rules[quality_level])
        
        return applicable_rules
    
    def get_negative_prompts_for_platform(self, platform: str, quality_level: Optional[str] = None) -> List[str]:
        """Get standard negative prompts for a specific platform"""
        negative_prompts = []
        
        # Default negative prompts
        default_negatives = [
            "nsfw", "explicit content", "violence", "gore", "hate speech",
            "copyrighted characters", "trademarked content", "low quality",
            "blurry", "pixelated", "watermarks", "signatures"
        ]
        negative_prompts.extend(default_negatives)
        
        # Platform-specific negatives
        platform_negatives = {
            "instagram": ["copyright violation", "brand infringement", "boring composition"],
            "twitter": ["misinformation", "political bias", "controversial imagery"],
            "facebook": ["fake news", "misleading content", "clickbait"],
            "linkedin": ["unprofessional content", "casual inappropriate"],
            "tiktok": ["static image", "outdated trends", "boring content"],
            "youtube": ["misleading thumbnail", "clickbait visuals"]
        }
        
        if platform in platform_negatives:
            negative_prompts.extend(platform_negatives[platform])
        
        # Quality-level negatives
        if quality_level:
            quality_negatives = {
                "premium": ["amateur composition", "poor lighting", "unprofessional"],
                "ultra": ["noise", "grain", "artifacts", "compression", "color banding"]
            }
            if quality_level in quality_negatives:
                negative_prompts.extend(quality_negatives[quality_level])
        
        return list(set(negative_prompts))  # Remove duplicates
    
    def validate_content_safety(self, content: str, platform: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Quick validation of content safety"""
        result = self.process_content(content, platform, strict_mode=True)
        
        is_safe = not result["blocked"] and len([v for v in result["violations"] if v["severity"] in ["critical", "high"]]) == 0
        
        warnings = result["warnings"].copy()
        for violation in result["violations"]:
            if violation["severity"] in ["critical", "high"]:
                warnings.append(f"{violation['category']}: {violation['description']}")
        
        return is_safe, warnings
    
    def get_content_safety_score(self, content: str, platform: Optional[str] = None) -> Dict[str, Any]:
        """Get a content safety score (0-100, higher is safer)"""
        result = self.process_content(content, platform, strict_mode=False)
        
        if result["blocked"]:
            return {"score": 0, "level": "blocked", "issues": len(result["violations"])}
        
        # Calculate score based on violations
        violation_weights = {"critical": -50, "high": -25, "medium": -10, "low": -5}
        score_penalty = 0
        
        for violation in result["violations"]:
            score_penalty += violation_weights.get(violation["severity"], -5)
        
        safety_score = max(0, min(100, 100 + score_penalty))
        
        if safety_score >= 90:
            safety_level = "excellent"
        elif safety_score >= 75:
            safety_level = "good"
        elif safety_score >= 50:
            safety_level = "moderate"
        elif safety_score >= 25:
            safety_level = "poor"
        else:
            safety_level = "critical"
        
        return {
            "score": safety_score,
            "level": safety_level,
            "issues": len(result["violations"]),
            "categories": list(set(v["category"] for v in result["violations"])),
            "replacements_made": len(result["replacements"])
        }
    
    def add_custom_rule(self, rule: AvoidListRule) -> bool:
        """Add a custom avoid list rule"""
        try:
            # Validate pattern
            re.compile(rule.pattern, re.IGNORECASE | re.MULTILINE)
            
            # Add rule
            self.rules.append(rule)
            self.compiled_patterns[rule.pattern] = re.compile(rule.pattern, re.IGNORECASE | re.MULTILINE)
            
            logger.info(f"Custom rule added: {rule.category.value} - {rule.description}")
            return True
            
        except re.error as e:
            logger.error(f"Invalid custom rule pattern '{rule.pattern}': {e}")
            return False
    
    def export_rules_config(self) -> Dict[str, Any]:
        """Export current rules configuration"""
        return {
            "default_rules": [
                {
                    "pattern": rule.pattern,
                    "category": rule.category.value,
                    "severity": rule.severity,
                    "processing_mode": rule.processing_mode.value,
                    "replacement_text": rule.replacement_text,
                    "description": rule.description
                }
                for rule in self.rules
            ],
            "platform_rules": {
                platform: [
                    {
                        "pattern": rule.pattern,
                        "category": rule.category.value,
                        "severity": rule.severity,
                        "processing_mode": rule.processing_mode.value,
                        "replacement_text": rule.replacement_text,
                        "description": rule.description
                    }
                    for rule in rules
                ]
                for platform, rules in self.platform_specific_rules.items()
            },
            "quality_rules": {
                quality: [
                    {
                        "pattern": rule.pattern,
                        "category": rule.category.value,
                        "severity": rule.severity,
                        "processing_mode": rule.processing_mode.value,
                        "replacement_text": rule.replacement_text,
                        "description": rule.description
                    }
                    for rule in rules
                ]
                for quality, rules in self.quality_rules.items()
            }
        }

# Global service instance
avoid_list_processor = AvoidListProcessor()

def get_avoid_list_processor() -> AvoidListProcessor:
    """Get the global avoid list processor instance"""
    return avoid_list_processor