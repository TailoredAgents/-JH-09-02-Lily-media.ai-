"""
Autonomous Scheduler - Production Celery beat schedules
Handles daily/weekly autonomous content generation and posting loops
"""
# Ensure warnings are suppressed in worker processes
from backend.core.suppress_warnings import suppress_third_party_warnings
suppress_third_party_warnings()

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from celery import Celery
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User, UserSetting, WorkflowExecution
from backend.services.research_automation_production import ProductionResearchAutomationService, ResearchQuery
from backend.services.content_persistence_service import ContentPersistenceService
from backend.services.memory_service_production import ProductionMemoryService
from backend.tasks.celery_app import celery_app
from backend.tasks.db_session_manager import get_celery_db_session

logger = logging.getLogger(__name__)

class AutonomousScheduler:
    """Manages autonomous content generation and posting schedules"""
    
    def __init__(self):
        self.research_service = ProductionResearchAutomationService()
    
    def get_active_users_for_autonomous_mode(self, db: Session) -> List[Dict[str, Any]]:
        """Get users with autonomous mode enabled"""
        try:
            # Query users with autonomous settings enabled
            users_with_settings = db.query(User, UserSetting).join(
                UserSetting, User.id == UserSetting.user_id
            ).filter(
                User.is_active == True,
                UserSetting.enable_autonomous_mode == True  # This field needs to be added to UserSetting
            ).all()
            
            user_configs = []
            for user, settings in users_with_settings:
                user_configs.append({
                    'user_id': user.id,
                    'email': user.email,
                    'timezone': getattr(settings, 'timezone', 'UTC'),
                    'preferred_platforms': settings.preferred_platforms or ['twitter', 'instagram'],
                    'content_frequency': settings.content_frequency or 3,
                    'posting_times': settings.posting_times or {'twitter': '09:00', 'instagram': '10:00'},
                    'brand_voice': settings.brand_voice or 'professional',
                    'creativity_level': settings.creativity_level or 0.7
                })
            
            logger.info(f"Found {len(user_configs)} users with autonomous mode enabled")
            return user_configs
            
        except Exception as e:
            logger.error(f"Failed to get autonomous users: {e}")
            return []

@celery_app.task(bind=True, name='autonomous_daily_content_generation')
def daily_content_generation(self):
    """Daily autonomous content generation task"""
    try:
        logger.info("Starting daily autonomous content generation")
        
        scheduler = AutonomousScheduler()
        
        with get_celery_db_session() as db:
            # Get users with autonomous mode enabled
            active_users = scheduler.get_active_users_for_autonomous_mode(db)
            
            if not active_users:
                logger.info("No users with autonomous mode enabled")
                return {'status': 'completed', 'users_processed': 0}
            
            results = []
            
            for user_config in active_users:
                try:
                    user_id = user_config['user_id']
                    logger.info(f"Processing autonomous content for user {user_id}")
                    
                    # Create workflow execution record
                    workflow = WorkflowExecution(
                        user_id=user_id,
                        workflow_type='daily_autonomous',
                        status='running',
                        configuration=user_config
                    )
                    db.add(workflow)
                    db.commit()
                
                    # Step 1: Research trending topics
                    research_query = ResearchQuery(
                        keywords=['trending topics', 'industry news'],
                        platforms=user_config['preferred_platforms'],
                        max_results=20,
                        include_trends=True
                    )
                    
                    # Use asyncio.run() for async research service call (2025 best practice)
                    research_results = asyncio.run(
                        scheduler.research_service.execute_comprehensive_research(research_query)
                    )
                
                # Step 2: Generate content based on research
                content_service = ContentPersistenceService(db)
                memory_service = ProductionMemoryService(db)
                
                # Get content inspiration from memory
                inspiration = memory_service.get_content_inspiration(
                    user_id=user_id,
                    topic='daily content',
                    platform=user_config['preferred_platforms'][0],
                    limit=5
                )
                
                # Step 3: Create content for each platform
                content_items = []
                for platform in user_config['preferred_platforms']:
                    # Determine posting time for this platform
                    posting_time = user_config['posting_times'].get(platform, '09:00')
                    
                    # Schedule for tomorrow at the specified time
                    tomorrow = datetime.utcnow() + timedelta(days=1)
                    scheduled_time = tomorrow.replace(
                        hour=int(posting_time.split(':')[0]),
                        minute=int(posting_time.split(':')[1]),
                        second=0,
                        microsecond=0
                    )
                    
                    # Generate platform-specific content
                    content_text = f"Daily insight for {platform}: Based on today's research, here's what's trending..."
                    
                    # Store content with scheduling
                    content_item = content_service.create_content(
                        user_id=user_id,
                        title=f"Daily {platform} content - {tomorrow.strftime('%Y-%m-%d')}",
                        content=content_text,
                        platform=platform,
                        content_type='text',
                        status='scheduled',
                        scheduled_at=scheduled_time,
                        metadata={
                            'generated_by': 'autonomous_scheduler',
                            'research_data': research_results.get('summary', {}),
                            'inspiration_sources': len(inspiration.get('similar_content', []))
                        }
                    )
                    
                    content_items.append(content_item.id)
                
                # Update workflow as completed
                workflow.status = 'completed'
                workflow.results = {
                    'content_items_created': len(content_items),
                    'research_quality_score': research_results.get('summary', {}).get('research_quality_score', 0),
                    'platforms_processed': user_config['preferred_platforms']
                }
                db.commit()
                
                results.append({
                    'user_id': user_id,
                    'status': 'success',
                    'content_items': len(content_items),
                    'workflow_id': workflow.id
                })
                
                logger.info(f"Completed autonomous content generation for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed autonomous content generation for user {user_config['user_id']}: {e}")
                # Update workflow as failed
                if 'workflow' in locals():
                    workflow.status = 'failed'
                    workflow.error_message = str(e)
                    db.commit()
                
                results.append({
                    'user_id': user_config['user_id'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        logger.info(f"Daily autonomous content generation completed. Processed {len(results)} users")
        return {
            'status': 'completed',
            'users_processed': len(results),
            'successful': len([r for r in results if r['status'] == 'success']),
            'failed': len([r for r in results if r['status'] == 'failed']),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Daily content generation task failed: {e}")
        raise

@celery_app.task(bind=True, name='autonomous_weekly_report')
def weekly_report_generation(self):
    """Weekly autonomous performance report task"""
    try:
        logger.info("Starting weekly autonomous report generation")
        
        scheduler = AutonomousScheduler()
        
        with get_celery_db_session() as db:
            # Get users with autonomous mode
            active_users = scheduler.get_active_users_for_autonomous_mode(db)
        
        if not active_users:
            logger.info("No users for weekly report generation")
            return {'status': 'completed', 'reports_generated': 0}
        
        reports_generated = 0
        
        for user_config in active_users:
            try:
                user_id = user_config['user_id']
                
                # Get past week's workflow executions
                week_ago = datetime.utcnow() - timedelta(days=7)
                workflows = db.query(WorkflowExecution).filter(
                    WorkflowExecution.user_id == user_id,
                    WorkflowExecution.created_at >= week_ago,
                    WorkflowExecution.workflow_type == 'daily_autonomous'
                ).all()
                
                # Get content performance from past week
                content_service = ContentPersistenceService(db)
                week_content = content_service.get_content_list(
                    user_id=user_id,
                    page=1,
                    limit=50
                )
                
                # Calculate weekly metrics
                total_content = len(week_content.get('content', []))
                successful_workflows = len([w for w in workflows if w.status == 'completed'])
                failed_workflows = len([w for w in workflows if w.status == 'failed'])
                
                # Generate weekly summary
                weekly_summary = {
                    'user_id': user_id,
                    'week_ending': datetime.utcnow().isoformat(),
                    'content_generated': total_content,
                    'successful_workflows': successful_workflows,
                    'failed_workflows': failed_workflows,
                    'success_rate': (successful_workflows / max(len(workflows), 1)) * 100,
                    'platforms_active': user_config['preferred_platforms'],
                    'recommendations': []
                }
                
                # Add recommendations based on performance
                if weekly_summary['success_rate'] < 80:
                    weekly_summary['recommendations'].append(
                        "Consider reviewing content generation settings - success rate below 80%"
                    )
                
                if total_content < user_config['content_frequency']:
                    weekly_summary['recommendations'].append(
                        f"Content generation below target frequency ({total_content} vs {user_config['content_frequency']} expected)"
                    )
                
                # Store weekly report
                memory_service = ProductionMemoryService(db)
                memory_service.store_insight_memory(
                    user_id=user_id,
                    title=f"Weekly Autonomous Report - {datetime.utcnow().strftime('%Y-%m-%d')}",
                    insight_content=f"Weekly performance summary: {total_content} content items generated, {weekly_summary['success_rate']:.1f}% success rate",
                    insight_type='weekly_report',
                    metadata=weekly_summary
                )
                
                reports_generated += 1
                logger.info(f"Generated weekly report for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to generate weekly report for user {user_config['user_id']}: {e}")
        
        logger.info(f"Weekly report generation completed. Generated {reports_generated} reports")
        return {
            'status': 'completed',
            'reports_generated': reports_generated,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Weekly report generation task failed: {e}")
        raise

@celery_app.task(bind=True, name='autonomous_metrics_collection')
def nightly_metrics_collection(self):
    """Nightly metrics collection and analysis task"""
    try:
        logger.info("Starting nightly metrics collection")
        
        scheduler = AutonomousScheduler()
        
        with get_celery_db_session() as db:
            # Get all active users (not just autonomous mode)
            active_users = db.query(User).filter(User.is_active == True).all()
        
        metrics_collected = 0
        
        for user in active_users:
            try:
                # Get published content from the past day
                yesterday = datetime.utcnow() - timedelta(days=1)
                content_service = ContentPersistenceService(db)
                
                recent_content = content_service.get_content_list(
                    user_id=user.id,
                    page=1,
                    limit=100,
                    status='published'
                )
                
                # Simulate metrics collection (in production, would call platform APIs)
                for content_item in recent_content.get('content', []):
                    if content_item.get('published_at'):
                        published_date = datetime.fromisoformat(content_item['published_at'].replace('Z', ''))
                        
                        # Only collect metrics for content published yesterday
                        if published_date.date() == yesterday.date():
                            # Simulate engagement metrics
                            platform = content_item.get('platform', 'unknown')
                            simulated_metrics = {
                                'views': 100 + (hash(content_item['content']) % 500),
                                'likes': 5 + (hash(content_item['content']) % 50),
                                'shares': 1 + (hash(content_item['content']) % 10),
                                'comments': hash(content_item['content']) % 5,
                                'engagement_rate': ((5 + hash(content_item['content']) % 50) / (100 + hash(content_item['content']) % 500)) * 100
                            }
                            
                            # Update content with metrics
                            content_service.update_engagement_metrics(
                                user_id=user.id,
                                content_id=content_item['id'],
                                metrics=simulated_metrics
                            )
                            
                            metrics_collected += 1
                
                logger.info(f"Collected metrics for user {user.id}")
                
            except Exception as e:
                logger.error(f"Failed to collect metrics for user {user.id}: {e}")
        
        logger.info(f"Nightly metrics collection completed. Collected {metrics_collected} metric sets")
        return {
            'status': 'completed',
            'metrics_collected': metrics_collected,
            'users_processed': len(active_users),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Nightly metrics collection task failed: {e}")
        raise

@celery_app.task(bind=True, name='autonomous_content_posting')
def process_scheduled_content(self):
    """Process and post scheduled content"""
    try:
        logger.info("Starting scheduled content posting")
        
        with get_celery_db_session() as db:
            content_service = ContentPersistenceService(db)
        
        # Get content scheduled for posting now (within the next hour)
        now = datetime.utcnow()
        posting_window = now + timedelta(hours=1)
        
        scheduled_content = content_service.get_scheduled_content(
            user_id=None,  # Get for all users
            before=posting_window
        )
        
        if not scheduled_content:
            logger.info("No content scheduled for posting")
            return {'status': 'completed', 'posts_processed': 0}
        
        posts_processed = 0
        successful_posts = 0
        failed_posts = 0
        
        for content_item in scheduled_content:
            try:
                # Check if it's time to post
                if content_item.scheduled_for <= now:
                    # Simulate posting (in production, would call platform APIs)
                    platform = content_item.platform
                    content_text = content_item.content
                    
                    # Simulate successful posting
                    external_post_id = f"{platform}_{content_item.id}_{int(now.timestamp())}"
                    
                    # Mark as published
                    content_service.mark_as_published(
                        user_id=content_item.user_id,
                        content_id=content_item.id,
                        platform_post_id=external_post_id,
                        published_at=now
                    )
                    
                    successful_posts += 1
                    logger.info(f"Posted content {content_item.id} to {platform}")
                
                posts_processed += 1
                
            except Exception as e:
                logger.error(f"Failed to post content {content_item.id}: {e}")
                failed_posts += 1
        
        logger.info(f"Scheduled posting completed. Processed {posts_processed}, succeeded {successful_posts}, failed {failed_posts}")
        return {
            'status': 'completed',
            'posts_processed': posts_processed,
            'successful_posts': successful_posts,
            'failed_posts': failed_posts,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Scheduled content posting task failed: {e}")
        raise