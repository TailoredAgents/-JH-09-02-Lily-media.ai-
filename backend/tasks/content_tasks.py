"""
Content Generation and Management Tasks.

This module provides Celery tasks for generating social media content using CrewAI agents.
Tasks handle daily content generation, brand voice customization, and content optimization
for different social media platforms.

Functions:
    generate_daily_content: Generate daily content using CrewAI agents with specified topics and brand voice
"""

# Ensure warnings are suppressed in worker processes
from backend.core.suppress_warnings import suppress_third_party_warnings
suppress_third_party_warnings()

from celery import current_task
from backend.tasks.celery_app import celery_app
from backend.agents.crew_config import create_daily_crew
from backend.agents.tools import memory_tool, openai_tool
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def generate_daily_content(self, topic="social media trends", brand_voice="professional"):
    """Generate daily content using CrewAI agents"""
    try:
        current_task.update_state(
            state='PROGRESS',
            meta={'current': 1, 'total': 4, 'status': 'Starting content generation...'}
        )
        
        # Create and run the daily crew
        crew = create_daily_crew(topic=topic, brand_voice=brand_voice)
        
        current_task.update_state(
            state='PROGRESS',
            meta={'current': 2, 'total': 4, 'status': 'Running research agent...'}
        )
        
        result = crew.kickoff()
        
        current_task.update_state(
            state='PROGRESS',
            meta={'current': 3, 'total': 4, 'status': 'Processing results...'}
        )
        
        # Store results in memory
        if result:
            memory_tool.store_content(
                content=str(result),
                metadata={
                    'type': 'daily_content',
                    'topic': topic,
                    'brand_voice': brand_voice,
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }
            )
        
        current_task.update_state(
            state='PROGRESS',
            meta={'current': 4, 'total': 4, 'status': 'Content generation completed!'}
        )
        
        return {
            'status': 'success',
            'message': 'Daily content generated successfully',
            'content': str(result) if result else 'No content generated',
            'topic': topic,
            'brand_voice': brand_voice
        }
        
    except Exception as exc:
        logger.error(f"Content generation failed: {str(exc)}")
        return {
            'status': 'error',
            'message': f'Content generation failed: {str(exc)}',
            'topic': topic
        }

@celery_app.task
def generate_single_post(platform="linkedin", topic="AI trends", style="professional"):
    """Generate a single post for specified platform"""
    try:
        prompt = f"""Create a {style} social media post for {platform} about {topic}.
        
        Requirements:
        - Platform: {platform}
        - Topic: {topic}
        - Style: {style}
        - Include relevant hashtags
        - Optimize for engagement
        - Keep within platform limits
        
        Return only the post content, ready to publish."""
        
        content = openai_tool.generate_text(prompt, max_tokens=300)
        
        # Store in memory
        memory_tool.store_content(
            content=content,
            metadata={
                'type': 'single_post',
                'platform': platform,
                'topic': topic,
                'style': style
            }
        )
        
        return {
            'status': 'success',
            'content': content,
            'platform': platform,
            'topic': topic
        }
        
    except Exception as exc:
        logger.error(f"Single post generation failed: {str(exc)}")
        return {
            'status': 'error',
            'message': f'Post generation failed: {str(exc)}'
        }

@celery_app.task
def generate_content_series(topic="AI in Marketing", num_posts=5, platforms=None):
    """Generate a series of related posts across platforms"""
    if platforms is None:
        platforms = ["twitter", "linkedin", "instagram"]
    
    try:
        results = []
        
        for i in range(num_posts):
            for platform in platforms:
                post_prompt = f"""Create post {i+1} of {num_posts} in a series about {topic} for {platform}.
                
                This is part of a content series, so:
                - Reference that this is part {i+1} of {num_posts}
                - Build on previous posts conceptually
                - Include platform-specific optimization
                - Add relevant hashtags
                - Maintain consistency in tone and messaging
                
                Return only the post content."""
                
                content = openai_tool.generate_text(post_prompt, max_tokens=250)
                
                post_result = {
                    'part': i+1,
                    'platform': platform,
                    'content': content,
                    'topic': topic
                }
                
                results.append(post_result)
                
                # Store in memory
                memory_tool.store_content(
                    content=content,
                    metadata={
                        'type': 'content_series',
                        'series_topic': topic,
                        'part': i+1,
                        'total_parts': num_posts,
                        'platform': platform
                    }
                )
        
        return {
            'status': 'success',
            'message': f'Generated {len(results)} posts for content series',
            'series_topic': topic,
            'total_posts': len(results),
            'results': results
        }
        
    except Exception as exc:
        logger.error(f"Content series generation failed: {str(exc)}")
        return {
            'status': 'error',
            'message': f'Content series generation failed: {str(exc)}'
        }

@celery_app.task
def repurpose_content(original_content, target_platforms=None):
    """Repurpose existing content for different platforms"""
    if target_platforms is None:
        target_platforms = ["twitter", "linkedin", "instagram"]
    
    try:
        results = []
        
        for platform in target_platforms:
            repurpose_prompt = f"""Repurpose this content for {platform}:

Original content: {original_content}

Requirements for {platform}:
- Adapt tone and format for the platform
- Optimize length for platform limits
- Add platform-appropriate hashtags
- Maintain core message while adapting style
- Make it engaging for {platform} audience

Return only the repurposed content."""
            
            repurposed = openai_tool.generate_text(repurpose_prompt, max_tokens=300)
            
            result = {
                'platform': platform,
                'content': repurposed,
                'original': original_content[:100] + "..."
            }
            
            results.append(result)
            
            # Store in memory
            memory_tool.store_content(
                content=repurposed,
                metadata={
                    'type': 'repurposed_content',
                    'platform': platform,
                    'original_content': original_content
                }
            )
        
        return {
            'status': 'success',
            'message': f'Content repurposed for {len(results)} platforms',
            'results': results
        }
        
    except Exception as exc:
        logger.error(f"Content repurposing failed: {str(exc)}")
        return {
            'status': 'error',
            'message': f'Content repurposing failed: {str(exc)}'
        }