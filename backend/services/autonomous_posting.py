"""
Autonomous Social Media Posting Service

This service handles automated posting to connected social media platforms
"""
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from backend.db.models import ContentLog, User, SocialConnection
from backend.services.research_automation_service import AutomatedResearchService
from backend.services.connection_publisher_service import get_connection_publisher_service
from backend.services.ai_insights_service import ai_insights_service
from backend.services.web_research_service import web_research_service
from backend.services.industry_classification_service import industry_classification_service
from backend.agents.tools import openai_tool
from backend.core.config import get_settings
from backend.core.observability import get_observability_manager

logger = logging.getLogger(__name__)
settings = get_settings()

class AutonomousPostingService:
    """Service for autonomous social media posting"""
    
    def __init__(self):
        self.research_service = AutomatedResearchService()
        self.publisher_service = get_connection_publisher_service()
        self.observability = get_observability_manager()
    
    async def execute_autonomous_cycle(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Execute a complete autonomous posting cycle"""
        
        cycle_start_time = time.time()
        
        try:
            logger.info(f"Starting autonomous posting cycle for user {user_id}")
            
            # Add Sentry breadcrumb for debugging
            self.observability.add_sentry_breadcrumb(
                f"Starting autonomous cycle for user {user_id}",
                category="autonomous_posting",
                data={"user_id": user_id}
            )
            
            # Step 1: Conduct real industry research using AI insights
            research_start_time = time.time()
            
            # Get user's organization and industry context
            user_obj = db.query(User).filter(User.id == user_id).first()
            if not user_obj:
                raise ValueError(f"User {user_id} not found")
            
            # Step 1.5: Determine user's industry dynamically
            user_industry = await industry_classification_service.auto_classify_user_industry(user_id, db)
            if not user_industry:
                user_industry = "general"  # Fallback
                
            industry_display_name = industry_classification_service.get_industry_display_name(user_industry)
            research_topics = industry_classification_service.get_industry_research_topics(user_industry)
            
            logger.info(f"Autonomous posting for user {user_id}: Industry={industry_display_name}, Topics={research_topics}")
            
            # Generate weekly insights using AI service
            research_results = await ai_insights_service.generate_weekly_insights()
            
            if research_results.get("status") != "success":
                # Fallback to web research with user's actual industry
                research_results = await web_research_service.research_industry_trends(
                    industry=industry_display_name,
                    topics=research_topics
                )
            
            # Track research performance
            research_duration = time.time() - research_start_time
            self.observability.track_ai_generation("research", "multi_platform", "success", research_duration)
            
            # Step 2: Generate content ideas based on research and user's industry
            content_ideas = await self._generate_content_ideas(research_results, user_industry)
            
            # Step 3: Create and post content to connected platforms
            posting_results = []
            connected_platforms = await self._get_connected_platforms(user_id, db)
            
            for platform in connected_platforms:
                if len(content_ideas) > 0:
                    idea = content_ideas.pop(0)  # Take next idea
                    result = await self._create_and_post_content(
                        user_id=user_id,
                        platform=platform,
                        content_idea=idea,
                        research_context=research_results,
                        db=db
                    )
                    posting_results.append(result)
            
            # Step 4: Schedule future posts
            await self._schedule_future_posts(user_id, content_ideas, db)
            
            logger.info(f"Autonomous posting cycle completed for user {user_id}")
            
            # Track successful cycle
            cycle_duration = time.time() - cycle_start_time
            self.observability.track_autonomous_cycle("success")
            self.observability.add_sentry_breadcrumb(
                f"Autonomous cycle completed successfully for user {user_id}",
                category="autonomous_posting",
                data={
                    "user_id": user_id,
                    "posts_created": len(posting_results),
                    "duration_seconds": cycle_duration
                }
            )
            
            return {
                "status": "success",
                "user_id": user_id,
                "research_insights": len(research_results.get("insights", [])),
                "content_ideas_generated": len(content_ideas) + len(posting_results),
                "posts_created": len(posting_results),
                "platforms_posted": [r["platform"] for r in posting_results if r["status"] == "success"],
                "cycle_completed_at": datetime.now(timezone.utc),
                "duration_seconds": cycle_duration
            }
            
        except Exception as e:
            logger.error(f"Autonomous posting cycle failed for user {user_id}: {e}")
            
            # Track failed cycle
            self.observability.track_autonomous_cycle("failed")
            self.observability.capture_exception(e, {
                "user_id": user_id,
                "cycle_step": "autonomous_posting_cycle",
                "duration_seconds": time.time() - cycle_start_time
            })
            
            return {
                "status": "error",
                "user_id": user_id,
                "error": str(e),
                "cycle_attempted_at": datetime.now(timezone.utc)
            }
    
    async def _generate_content_ideas(self, research_results: Dict, user_industry: str = "general") -> List[Dict]:
        """Generate content ideas based on research results using real AI"""
        
        generation_start_time = time.time()
        
        try:
            # Extract insights from AI research results
            insights = research_results.get("insights", {})
            if isinstance(insights, dict):
                trending_topics = insights.get("trending_topics", [])
                market_insights = insights.get("market_insights", [])
                content_opportunities = insights.get("content_opportunities", [])
            else:
                # Handle legacy format
                trending_topics = research_results.get("trends", [])
                market_insights = research_results.get("insights", [])
                content_opportunities = research_results.get("content_opportunities", [])
            
            # Get industry-specific context
            industry_display_name = industry_classification_service.get_industry_display_name(user_industry)
            
            # Create sophisticated prompt based on real research data and user's industry
            prompt = f"""You are a social media strategist specializing in {industry_display_name}. Based on this REAL market research data, create 3 high-value social media content ideas that will drive engagement and showcase expertise in {industry_display_name}.

TRENDING TOPICS:
{chr(10).join(trending_topics[:5]) if trending_topics else "AI automation and productivity tools are highly relevant"}

MARKET INSIGHTS:
{chr(10).join(market_insights[:3]) if market_insights else "Businesses are seeking automation solutions to improve efficiency"}

CONTENT OPPORTUNITIES:
{chr(10).join(content_opportunities[:3]) if content_opportunities else "Showcase AI automation benefits and case studies"}

REQUIREMENTS:
- Each idea must provide genuine value to professionals in {industry_display_name}
- Focus on industry-specific trends, challenges, and opportunities
- Include specific, actionable insights rather than generic content
- Vary platforms (LinkedIn for B2B, Twitter for quick insights, Instagram for visual content)
- Tailor content tone and topics specifically for {industry_display_name} audience

FORMAT: Return a JSON array where each object contains:
- "hook": Attention-grabbing opening line
- "content": Main message (200-300 words)
- "hashtags": Array of 3-5 relevant hashtags
- "platform": Best platform (twitter, linkedin, instagram)
- "content_type": Type (text, image+text, video_concept)
- "value_proposition": Why this content provides value

Generate content that demonstrates real expertise and actionable insights."""

            response = await openai_tool.generate_text(prompt, max_tokens=1500)
            
            # Parse the AI response into structured content ideas
            content_ideas = []
            
            if response and len(response) > 50:
                try:
                    # Parse JSON response from AI
                    import json
                    
                    # Clean the response to extract JSON
                    response = response.strip()
                    if response.startswith('```json'):
                        response = response[7:]
                    if response.endswith('```'):
                        response = response[:-3]
                    response = response.strip()
                    
                    if response.startswith('['):
                        # Direct array
                        content_ideas = json.loads(response)
                    elif response.startswith('{'):
                        # Object wrapper
                        parsed = json.loads(response)
                        if 'content_ideas' in parsed:
                            content_ideas = parsed['content_ideas']
                        elif isinstance(parsed, list):
                            content_ideas = parsed
                        else:
                            content_ideas = [parsed]  # Single idea object
                    else:
                        # Plain text response - create a single content idea
                        content_ideas = [{
                            "hook": "AI-Generated Insight",
                            "content": response[:800],  # Reasonable length
                            "hashtags": ["#AIInsights", "#Automation", "#Productivity"],
                            "platform": "linkedin",
                            "content_type": "text",
                            "value_proposition": "AI-generated content based on current market research"
                        }]
                        
                    # Validate and clean the content ideas
                    validated_ideas = []
                    for idea in content_ideas[:5]:  # Limit to 5 ideas
                        if isinstance(idea, dict) and 'content' in idea:
                            # Ensure required fields
                            validated_idea = {
                                "hook": idea.get("hook", "AI-Generated Content"),
                                "content": idea.get("content", "")[:800],  # Limit length
                                "hashtags": idea.get("hashtags", ["#AIAutomation"])[:5],  # Limit hashtags
                                "platform": idea.get("platform", "linkedin").lower(),
                                "content_type": idea.get("content_type", "text"),
                                "value_proposition": idea.get("value_proposition", "AI-generated content")
                            }
                            validated_ideas.append(validated_idea)
                    
                    content_ideas = validated_ideas if validated_ideas else []
                    
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.error(f"Failed to parse AI content generation response: {e}")
                    content_ideas = []
                    
            if not content_ideas:
                logger.error("AI content generation failed - no valid content ideas generated")
                raise ValueError("Content generation failed: AI service did not produce valid content ideas")
            
            # Track content generation success
            generation_duration = time.time() - generation_start_time
            self.observability.track_ai_generation("content_ideas", "multi_platform", "success", generation_duration)
            
            return content_ideas
            
        except Exception as e:
            logger.error(f"Content idea generation failed: {e}")
            
            # Track content generation failure
            generation_duration = time.time() - generation_start_time
            self.observability.track_ai_generation("content_ideas", "multi_platform", "failed", generation_duration)
            self.observability.capture_exception(e, {"step": "content_idea_generation"})
            
            # Re-raise the exception - no fallback to dummy content
            raise
    
    async def _get_connected_platforms(self, user_id: int, db: Session) -> List[str]:
        """Get list of connected social media platforms for user"""
        
        try:
            # Get user's organization ID
            user_obj = db.query(User).filter(User.id == user_id).first()
            if not user_obj or not user_obj.default_organization_id:
                logger.warning(f"User {user_id} has no organization")
                return []
            
            # Query for active social connections
            connections = db.query(SocialConnection).filter(
                SocialConnection.organization_id == user_obj.default_organization_id,
                SocialConnection.is_active == True,
                SocialConnection.connection_status == "active"
            ).all()
            
            platforms = []
            for conn in connections:
                if conn.platform and conn.platform not in platforms:
                    platforms.append(conn.platform)
            
            logger.info(f"Found {len(platforms)} connected platforms for user {user_id}: {platforms}")
            return platforms
            
        except Exception as e:
            logger.error(f"Error getting connected platforms for user {user_id}: {e}")
            return []
    
    async def _create_and_post_content(
        self, 
        user_id: int, 
        platform: str, 
        content_idea: Dict, 
        research_context: Dict,
        db: Session
    ) -> Dict[str, Any]:
        """Create and post content to a specific platform"""
        
        try:
            # Create content record in database
            content_record = ContentLog(
                user_id=user_id,
                platform=platform,
                content=content_idea["content"],
                content_type=content_idea.get("content_type", "text"),
                status="draft",
                engagement_data={"hashtags": content_idea.get("hashtags", [])},
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(content_record)
            db.flush()  # Get the ID
            
            # Generate image if needed
            image_url = None
            if content_idea.get("content_type") == "image+text":
                image_result = openai_tool.create_image(
                    f"Professional social media image for: {content_idea['hook']} - AI automation and social media management theme"
                )
                if image_result.get("status") == "success":
                    image_url = image_result.get("image_url")
            
            # Format content for platform
            formatted_content = self._format_content_for_platform(
                platform, content_idea, image_url
            )
            
            # Use real connection publisher service to post content
            post_result = await self.publisher_service.publish_content(
                user_id=user_id,
                platform=platform,
                content=formatted_content,
                content_type=content_idea.get("content_type", "text"),
                image_url=image_url
            )
                
            if post_result.get("success"):
                # Update content record as published
                content_record.status = "published"
                content_record.published_at = datetime.now(timezone.utc)
                content_record.engagement_data["platform_post_id"] = post_result.get("post_id")
                
                db.commit()
                
                # Track successful post
                self.observability.track_social_post(platform, "success")
                
                return {
                    "status": "success",
                    "platform": platform,
                    "content_id": content_record.id,
                    "post_id": post_result.get("post_id"),
                    "content_preview": content_idea["content"][:100] + "..."
                }
            else:
                content_record.status = "failed"
                db.commit()
                
                # Track failed post
                self.observability.track_social_post(platform, "failed")
                
                return {
                    "status": "failed",
                    "platform": platform,
                    "error": post_result.get("error"),
                    "content_id": content_record.id
                }
                
        except Exception as e:
            logger.error(f"Failed to create and post content for {platform}: {e}")
            return {
                "status": "error",
                "platform": platform,
                "error": str(e)
            }
    
    def _format_content_for_platform(self, platform: str, content_idea: Dict, image_url: str = None) -> str:
        """Format content appropriately for each platform"""
        
        base_content = f"{content_idea['hook']}\n\n{content_idea['content']}"
        hashtags = " ".join(content_idea.get("hashtags", []))
        
        if platform == "twitter":
            # Twitter has character limits
            max_length = 280 - len(hashtags) - 10  # Leave space for hashtags
            if len(base_content) > max_length:
                base_content = base_content[:max_length-3] + "..."
            return f"{base_content}\n\n{hashtags}"
        
        elif platform == "linkedin":
            # LinkedIn allows longer content
            return f"{base_content}\n\n{hashtags}"
        
        elif platform == "instagram":
            # Instagram is visual-first
            return f"{base_content}\n\n{hashtags}"
        
        elif platform == "facebook":
            return f"{base_content}\n\n{hashtags}"
        
        return f"{base_content}\n\n{hashtags}"
    
    
    async def _schedule_future_posts(self, user_id: int, remaining_ideas: List[Dict], db: Session):
        """Schedule remaining content ideas for future posting"""
        
        if not remaining_ideas:
            return
        
        # Schedule posts for the next few days
        base_time = datetime.now(timezone.utc) + timedelta(hours=4)  # Start 4 hours from now
        
        for i, idea in enumerate(remaining_ideas[:3]):  # Schedule up to 3 more
            scheduled_time = base_time + timedelta(hours=i * 8)  # 8 hours apart
            
            content_record = ContentLog(
                user_id=user_id,
                platform=idea.get("platform", "twitter"),
                content=idea["content"],
                content_type=idea.get("content_type", "text"),
                status="scheduled",
                scheduled_for=scheduled_time,
                engagement_data={"hashtags": idea.get("hashtags", [])},
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(content_record)
        
        db.commit()
        logger.info(f"Scheduled {len(remaining_ideas[:3])} future posts for user {user_id}")

# Create singleton instance
autonomous_posting_service = AutonomousPostingService()