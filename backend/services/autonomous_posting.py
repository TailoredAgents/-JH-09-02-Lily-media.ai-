"""
Autonomous Social Media Posting Service

This service handles automated posting to connected social media platforms
"""
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from backend.db.models import ContentLog, User
from backend.integrations.twitter_client import TwitterAPIClient as TwitterClient
from backend.integrations.linkedin_client import linkedin_client as LinkedInClient
from backend.integrations.instagram_client import InstagramAPIClient as InstagramClient
from backend.integrations.facebook_client import FacebookAPIClient as FacebookClient
from backend.services.research_automation_service import ResearchAutomationService
from backend.agents.tools import openai_tool
from backend.core.config import get_settings
from backend.core.observability import get_observability_manager

logger = logging.getLogger(__name__)
settings = get_settings()

class AutonomousPostingService:
    """Service for autonomous social media posting"""
    
    def __init__(self):
        self.research_service = ResearchAutomationService()
        self.platform_clients = {
            'twitter': TwitterClient(),
            'linkedin': LinkedInClient, 
            'instagram': InstagramClient(),
            'facebook': FacebookClient()
        }
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
            
            # Step 1: Conduct industry research
            research_start_time = time.time()
            research_results = await self.research_service.conduct_research(
                industry="AI Agent Products",
                focus_areas=[
                    "artificial intelligence trends",
                    "automation software",
                    "social media management",
                    "business productivity tools"
                ]
            )
            
            # Track research performance
            research_duration = time.time() - research_start_time
            self.observability.track_ai_generation("research", "multi_platform", "success", research_duration)
            
            # Step 2: Generate content ideas based on research
            content_ideas = await self._generate_content_ideas(research_results)
            
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
    
    async def _generate_content_ideas(self, research_results: Dict) -> List[Dict]:
        """Generate content ideas based on research results"""
        
        generation_start_time = time.time()
        
        try:
            insights = research_results.get("insights", [])
            trends = research_results.get("trends", [])
            
            # Create prompt for content generation
            prompt = f"""Based on the following industry research, generate 5 engaging social media content ideas for AI Agent products:

Research Insights:
{chr(10).join(insights[:5])}

Current Trends:
{chr(10).join(trends[:3])}

For each content idea, provide:
1. A compelling hook/opening
2. Main content body (keep platform-appropriate lengths in mind)
3. Relevant hashtags
4. Best platform recommendation (Twitter, LinkedIn, Instagram, Facebook)
5. Content type (text, image+text, video concept)

Focus on providing value, showcasing AI automation benefits, and engaging with the target audience of business owners and marketing professionals."""

            response = openai_tool.generate_text(prompt, max_tokens=1000)
            
            # Parse the response into structured content ideas
            # This is a simplified version - in production, you'd parse more carefully
            content_ideas = []
            
            # Create some default content ideas in case AI generation fails
            default_ideas = [
                {
                    "hook": "🤖 AI is revolutionizing social media management",
                    "content": "Discover how autonomous AI agents can manage your entire social media strategy, from research to posting, saving you 10+ hours per week while improving engagement rates by 300%.",
                    "hashtags": ["#AIAutomation", "#SocialMediaManagement", "#ProductivityHack", "#AIAgent"],
                    "platform": "linkedin",
                    "content_type": "text"
                },
                {
                    "hook": "💡 Pro tip for busy entrepreneurs",
                    "content": "Stop manually researching content ideas. AI agents can analyze industry trends, competitor content, and audience preferences to generate perfectly timed posts that drive real engagement.",
                    "hashtags": ["#EntrepreneurTips", "#AIProductivity", "#AutomationTools"],
                    "platform": "twitter",
                    "content_type": "text"
                },
                {
                    "hook": "🚀 The future of content creation is here",
                    "content": "From trend analysis to image generation to post scheduling - see how AI agents are transforming how businesses approach social media marketing.",
                    "hashtags": ["#FutureOfWork", "#AIContent", "#MarketingAutomation", "#SocialMediaStrategy"],
                    "platform": "instagram",
                    "content_type": "image+text"
                }
            ]
            
            # Try to extract ideas from AI response using 2025 best practices
            if response and len(response) > 100:
                try:
                    # Attempt to parse JSON response (OpenAI structured output format)
                    import json
                    if response.strip().startswith('{') or response.strip().startswith('['):
                        parsed_response = json.loads(response)
                        if isinstance(parsed_response, list):
                            content_ideas = parsed_response
                        elif isinstance(parsed_response, dict) and 'content_ideas' in parsed_response:
                            content_ideas = parsed_response['content_ideas']
                        else:
                            # Fallback to defaults only if parsing completely fails
                            content_ideas = default_ideas
                    else:
                        # If response is plain text, create structured content from it
                        content_ideas = [{
                            "hook": "AI-Generated Content",
                            "content": response[:500],  # Truncate if needed
                            "hashtags": ["#AIGenerated", "#SocialMedia"],
                            "platform": preferred_platforms[0] if preferred_platforms else "twitter",
                            "content_type": "text"
                        }]
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse AI response as JSON: {e}, using defaults")
                    content_ideas = default_ideas
                except Exception as e:
                    logger.warning(f"Error processing AI response: {e}, using defaults") 
                    content_ideas = default_ideas
            else:
                content_ideas = default_ideas
            
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
            
            # Return basic default ideas
            return [
                {
                    "hook": "🤖 AI automation is changing the game",
                    "content": "Experience the power of autonomous social media management with AI agents that work 24/7 to grow your online presence.",
                    "hashtags": ["#AIAutomation", "#SocialMedia"],
                    "platform": "twitter",
                    "content_type": "text"
                }
            ]
    
    async def _get_connected_platforms(self, user_id: int, db: Session) -> List[str]:
        """Get list of connected social media platforms for user"""
        
        # In a real implementation, this would check user's connected accounts
        # For now, return all available platforms
        return ["twitter", "linkedin"]  # Start with these two
    
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
            
            # Post to platform
            platform_client = self.platform_clients.get(platform)
            if platform_client:
                # Format content for platform
                formatted_content = self._format_content_for_platform(
                    platform, content_idea, image_url
                )
                
                # Attempt to post (this would use real API in production)
                post_result = await self._simulate_platform_post(
                    platform, formatted_content, image_url
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
            else:
                return {
                    "status": "failed",
                    "platform": platform,
                    "error": f"Platform client not available for {platform}"
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
    
    async def _simulate_platform_post(self, platform: str, content: str, image_url: str = None) -> Dict:
        """Simulate posting to platform (replace with real API calls in production)"""
        
        # Simulate successful posting
        import random
        import uuid
        
        if random.random() > 0.1:  # 90% success rate
            return {
                "success": True,
                "post_id": f"{platform}_{uuid.uuid4().hex[:8]}",
                "posted_at": datetime.now(timezone.utc)
            }
        else:
            return {
                "success": False,
                "error": f"Platform API error for {platform}"
            }
    
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