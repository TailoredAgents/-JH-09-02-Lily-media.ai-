"""
Celery tasks for comprehensive automation workflows
Supports all integration services: Instagram, Facebook, research automation, content generation
"""
# Ensure warnings are suppressed in worker processes
from backend.core.suppress_warnings import suppress_third_party_warnings
suppress_third_party_warnings()

from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncio
import json

from backend.db.database import SessionLocal
from backend.db.models import User, ContentItem, ResearchData, WorkflowExecution
from backend.services.research_automation import research_service, ResearchQuery, ResearchSource
from backend.services.content_automation import content_automation_service
from backend.services.workflow_orchestration import workflow_orchestrator
from backend.services.metrics_collection import metrics_collector
from backend.integrations.instagram_client import instagram_client
from backend.integrations.facebook_client import facebook_client
from backend.integrations.twitter_client import twitter_client
from backend.integrations.client import client

logger = get_task_logger(__name__)

# Research Automation Tasks

@shared_task(name="execute_research_pipeline")
def execute_research_pipeline(user_id: int, research_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute comprehensive research pipeline across all platforms
    """
    db = SessionLocal()
    
    try:
        # Convert config to ResearchQuery
        research_query = ResearchQuery(
            keywords=research_config["keywords"],
            platforms=[ResearchSource(p) for p in research_config["platforms"]],
            content_types=research_config.get("content_types", ["text", "image", "video"]),
            time_range=research_config.get("time_range", "24h"),
            location=research_config.get("location"),
            max_results=research_config.get("max_results", 100),
            include_sentiment=research_config.get("include_sentiment", True),
            include_engagement=research_config.get("include_engagement", True)
        )
        
        # Execute research in async context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(
            research_service.execute_research_pipeline(
                query=research_query,
                user_id=user_id,
                db=db
            )
        )
        
        logger.info(f"Research pipeline completed for user {user_id}: {len(results)} results")
        
        return {
            "success": True,
            "user_id": user_id,
            "results_count": len(results),
            "platforms_searched": research_config["platforms"],
            "keywords": research_config["keywords"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Research pipeline failed for user {user_id}: {str(e)}")
        return {
            "success": False,
            "user_id": user_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
    finally:
        if 'loop' in locals():
            loop.close()
        db.close()

@shared_task(name="daily_trend_analysis")
def daily_trend_analysis(user_id: int) -> Dict[str, Any]:
    """
    Daily automated trend analysis across all platforms
    """
    db = SessionLocal()
    
    try:
        # Get trending topics from each platform
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        trends = loop.run_until_complete(
            research_service.analyze_daily_trends(user_id, db)
        )
        
        # Store trend analysis results
        trend_summary = {
            "total_trends": len(trends),
            "top_hashtags": trends.get("top_hashtags", [])[:10],
            "emerging_topics": trends.get("emerging_topics", [])[:5],
            "engagement_leaders": trends.get("engagement_leaders", [])[:5],
            "sentiment_analysis": trends.get("sentiment_analysis", {}),
            "platform_breakdown": trends.get("platform_breakdown", {})
        }
        
        logger.info(f"Daily trend analysis completed for user {user_id}: {trend_summary['total_trends']} trends")
        
        return {
            "success": True,
            "user_id": user_id,
            "trend_summary": trend_summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Daily trend analysis failed for user {user_id}: {str(e)}")
        return {"success": False, "user_id": user_id, "error": str(e)}
    finally:
        if 'loop' in locals():
            loop.close()
        db.close()

# Content Generation and Publishing Tasks

@shared_task(name="generate_and_schedule_content")
def generate_and_schedule_content(user_id: int, content_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate AI content and schedule across multiple platforms
    """
    db = SessionLocal()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Generate content for platforms with bounded concurrency
        platforms = content_config.get("platforms", ["twitter"])
        max_concurrent = min(len(platforms), 4)  # Limit concurrent operations
        
        async def generate_platform_content(platform):
            return await content_automation_service.generate_content(
                topic=content_config["topic"],
                platform=platform,
                content_type=content_config.get("content_type", "post"),
                tone=content_config.get("tone", "professional"),
                target_audience=content_config.get("target_audience"),
                include_hashtags=content_config.get("include_hashtags", True),
                include_cta=content_config.get("include_cta", True),
                user_id=user_id
            )
        
        # Use semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_generate(platform):
            async with semaphore:
                return platform, await generate_platform_content(platform)
        
        # Execute all platforms concurrently with bounds
        platform_results = loop.run_until_complete(
            asyncio.gather(*[bounded_generate(p) for p in platforms], return_exceptions=True)
        )
        
        generated_content = {}
        scheduled_posts = []
        
        for result in platform_results:
            if isinstance(result, Exception):
                logger.error(f"Platform content generation failed: {result}")
                continue
                
            platform, content_result = result
            
            generated_content[platform] = content_result
            
            # Store in database
            content_item = ContentItem(
                user_id=user_id,
                content=content_result["content"],
                platform=platform,
                content_type=content_config.get("content_type", "post"),
                status="scheduled" if content_config.get("auto_schedule") else "draft",
                ai_model=content_result.get("model", "openai-gpt"),
                prompt_used=content_result.get("prompt"),
                generation_params=content_config,
                scheduled_for=content_config.get("schedule_time")
            )
            db.add(content_item)
            
            # Schedule post if enabled
            if content_config.get("auto_schedule"):
                schedule_result = loop.run_until_complete(
                    _schedule_platform_post(platform, content_result, user_id, content_config)
                )
                scheduled_posts.append({
                    "platform": platform,
                    "content_id": content_item.id,
                    "scheduled_for": content_config.get("schedule_time"),
                    "status": schedule_result.get("status", "scheduled")
                })
        
        db.commit()
        
        logger.info(f"Content generation completed for user {user_id}: {len(generated_content)} pieces generated")
        
        return {
            "success": True,
            "user_id": user_id,
            "generated_content": len(generated_content),
            "scheduled_posts": len(scheduled_posts),
            "platforms": list(generated_content.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Content generation failed for user {user_id}: {str(e)}")
        db.rollback()
        return {"success": False, "user_id": user_id, "error": str(e)}
    finally:
        if 'loop' in locals():
            loop.close()
        db.close()

async def _schedule_platform_post(platform: str, content_result: Dict[str, Any], user_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to schedule posts on specific platforms"""
    try:
        if platform == "instagram":
            # For Instagram, we need media URLs
            if not config.get("media_urls"):
                return {"status": "skipped", "reason": "No media URLs provided for Instagram"}
            
            result = await instagram_client.create_post(
                access_token=await instagram_client.get_user_token(user_id),
                caption=content_result["content"],
                media_urls=config["media_urls"],
                hashtags=content_result.get("hashtags", [])
            )
            return {"status": "scheduled", "platform_id": result.get("id")}
            
        elif platform == "facebook":
            result = await facebook_client.create_post(
                access_token=await facebook_client.get_user_token(user_id),
                message=content_result["content"],
                scheduled_publish_time=config.get("schedule_time")
            )
            return {"status": "scheduled", "platform_id": result.get("id")}
            
        elif platform == "twitter":
            result = await twitter_client.create_tweet(
                access_token=await twitter_client.get_user_token(user_id),
                text=content_result["content"]
            )
            return {"status": "published", "platform_id": result.get("id")}
            
        else:
            # Unsupported or not yet integrated platforms
            return {"status": "unsupported_platform"}
        
    except Exception as e:
        logger.error(f"Failed to schedule {platform} post: {str(e)}")
        return {"status": "failed", "error": str(e)}

# Workflow Orchestration Tasks

@shared_task(name="execute_daily_workflow")
def execute_daily_workflow(user_id: int, workflow_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute comprehensive daily workflow: research → content generation → scheduling → analysis
    """
    db = SessionLocal()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Default daily workflow configuration
        if not workflow_config:
            workflow_config = {
                "research_topics": ["industry trends", "competitor analysis"],
                "content_count": 3,
                "platforms": ["twitter", ],
                "tone": "professional",
                "auto_schedule": True
            }
        
        workflow_results = loop.run_until_complete(
            workflow_orchestrator.execute_workflow(
                workflow_type="daily_content",
                user_id=user_id,
                parameters=workflow_config
            )
        )
        
        logger.info(f"Daily workflow completed for user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "workflow_id": workflow_results.get("id"),
            "stages_completed": workflow_results.get("stages_completed", []),
            "content_generated": workflow_results.get("content_generated", 0),
            "posts_scheduled": workflow_results.get("posts_scheduled", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Daily workflow failed for user {user_id}: {str(e)}")
        return {"success": False, "user_id": user_id, "error": str(e)}
    finally:
        if 'loop' in locals():
            loop.close()
        db.close()

@shared_task(name="execute_engagement_optimization")
def execute_engagement_optimization(user_id: int) -> Dict[str, Any]:
    """
    Analyze recent content performance and optimize future strategies
    """
    db = SessionLocal()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Collect recent metrics
        metrics_result = loop.run_until_complete(
            metrics_collector.collect_all_metrics(user_id, days=7)
        )
        
        # Execute optimization workflow
        optimization_result = loop.run_until_complete(
            workflow_orchestrator.execute_workflow(
                workflow_type="engagement_optimization",
                user_id=user_id,
                parameters={"metrics": metrics_result}
            )
        )
        
        logger.info(f"Engagement optimization completed for user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "metrics_analyzed": len(metrics_result.get("content_items", [])),
            "optimizations_identified": len(optimization_result.get("recommendations", [])),
            "top_performing_content": optimization_result.get("top_performers", [])[:3],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Engagement optimization failed for user {user_id}: {str(e)}")
        return {"success": False, "user_id": user_id, "error": str(e)}
    finally:
        if 'loop' in locals():
            loop.close()
        db.close()

# Metrics Collection Tasks

@shared_task(name="collect_all_platform_metrics")
def collect_all_platform_metrics(user_id: int) -> Dict[str, Any]:
    """
    Collect metrics from all connected social media platforms
    """
    db = SessionLocal()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Collect metrics from all platforms
        metrics_result = loop.run_until_complete(
            metrics_collector.collect_all_metrics(user_id)
        )
        
        # Store metrics in database
        metrics_summary = {
            "total_posts_analyzed": metrics_result.get("total_posts", 0),
            "platforms_collected": list(metrics_result.get("platforms", {}).keys()),
            "avg_engagement_rate": metrics_result.get("avg_engagement_rate", 0),
            "total_impressions": metrics_result.get("total_impressions", 0),
            "total_engagement": metrics_result.get("total_engagement", 0),
            "top_performing_posts": metrics_result.get("top_performers", [])[:5]
        }
        
        logger.info(f"Metrics collection completed for user {user_id}: {metrics_summary['total_posts_analyzed']} posts analyzed")
        
        return {
            "success": True,
            "user_id": user_id,
            "metrics_summary": metrics_summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Metrics collection failed for user {user_id}: {str(e)}")
        return {"success": False, "user_id": user_id, "error": str(e)}
    finally:
        if 'loop' in locals():
            loop.close()
        db.close()

# Scheduled Tasks for Automation

@shared_task(name="hourly_metrics_sync")
def hourly_metrics_sync() -> Dict[str, Any]:
    """
    Hourly task to sync metrics for all active users
    """
    db = SessionLocal()
    
    try:
        # Batch over active users to avoid loading all into memory
        batch_size = 500
        offset = 0
        total_processed = 0
        results = {
            "total_users": None,  # unknown up front
            "successful_syncs": 0,
            "failed_syncs": 0,
            "errors": []
        }
        
        while True:
            batch = (
                db.query(User)
                .filter(User.is_active == True)
                .order_by(User.id)
                .offset(offset)
                .limit(batch_size)
                .all()
            )
            if not batch:
                break
                
            for user in batch:
                total_processed += 1
                try:
                    # Trigger metrics collection for each user
                    collect_all_platform_metrics.delay(user.id)
                    results["successful_syncs"] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to trigger metrics sync for user {user.id}: {str(e)}")
                    results["failed_syncs"] += 1
                    results["errors"].append({"user_id": user.id, "error": str(e)})
            
            offset += batch_size
        
        results["total_users"] = total_processed
        
        logger.info(f"Hourly metrics sync triggered for {results['successful_syncs']} users")
        return results
        
    except Exception as e:
        logger.error(f"Hourly metrics sync failed: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@shared_task(name="daily_workflow_automation")
def daily_workflow_automation() -> Dict[str, Any]:
    """
    Daily task to execute automated workflows for all users
    """
    db = SessionLocal()
    
    try:
        # Batch users with automation enabled
        batch_size = 500
        offset = 0
        total_processed = 0
        results = {
            "total_users": None,  # unknown up front
            "workflows_triggered": 0,
            "errors": []
        }
        
        while True:
            users = (
                db.query(User)
                .filter(
                    User.is_active == True,
                    User.automation_enabled == True
                )
                .order_by(User.id)
                .offset(offset)
                .limit(batch_size)
                .all()
            )
            if not users:
                break
                
            for user in users:
                total_processed += 1
                try:
                    # Trigger daily workflow for each user
                    execute_daily_workflow.delay(user.id)
                    results["workflows_triggered"] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to trigger daily workflow for user {user.id}: {str(e)}")
                    results["errors"].append({"user_id": user.id, "error": str(e)})
            
            offset += batch_size
        
        results["total_users"] = total_processed
        
        logger.info(f"Daily workflow automation triggered for {results['workflows_triggered']} users")
        return results
        
    except Exception as e:
        logger.error(f"Daily workflow automation failed: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()
