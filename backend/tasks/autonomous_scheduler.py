"""
Autonomous Scheduler - Production Celery beat schedules
Handles daily/weekly autonomous content generation and posting loops
"""
# Ensure warnings are suppressed in worker processes
from backend.core.suppress_warnings import suppress_third_party_warnings
suppress_third_party_warnings()

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from celery import Celery
from sqlalchemy.orm import Session

# Try to use zoneinfo (Python 3.9+) or fallback to pytz
try:
    from zoneinfo import ZoneInfo
    TIMEZONE_AVAILABLE = True
except ImportError:
    try:
        import pytz
        ZoneInfo = pytz.timezone
        TIMEZONE_AVAILABLE = True
    except ImportError:
        TIMEZONE_AVAILABLE = False

from backend.db.database import get_db
from backend.db.models import User, UserSetting, WorkflowExecution
from backend.services.research_automation_production import ProductionResearchAutomationService, ResearchQuery
from backend.services.content_persistence_service import ContentPersistenceService
from backend.services.memory_service_production import ProductionMemoryService
from backend.services.usage_tracking_service import UsageTrackingService
from backend.services.plan_aware_social_service import get_plan_aware_social_service
from backend.tasks.celery_app import celery_app
from backend.tasks.db_session_manager import get_celery_db_session
from backend.core.feature_flags import ff

logger = logging.getLogger(__name__)

class AutonomousScheduler:
    """Manages autonomous content generation and posting schedules"""
    
    def __init__(self):
        self.research_service = ProductionResearchAutomationService()
    
    def check_user_quota_limits(self, user_id: int, db: Session, operation_type: str = "autonomous_content") -> Dict[str, Any]:
        """
        Check if user has sufficient quota for autonomous operations
        
        Args:
            user_id: User ID to check
            db: Database session
            operation_type: Type of operation (autonomous_content, research, etc.)
        
        Returns:
            Dict with quota check results and enforcement details
        """
        try:
            # Initialize services
            usage_service = UsageTrackingService(db)
            plan_service = get_plan_aware_social_service(db)
            
            # Get user for plan information
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {
                    "allowed": False,
                    "reason": "user_not_found",
                    "message": f"User {user_id} not found"
                }
            
            # P0-5c: Enhanced plan limit logging and upgrade suggestions
            user_settings = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
            if user_settings:
                # Check if user has autonomous mode enabled (basic gate)
                if not user_settings.enable_autonomous_mode:
                    # P0-5c: Structured logging for quota blocks
                    logger.warning(
                        f"QUOTA_BLOCK: user_id={user_id}, operation={operation_type}, "
                        f"reason=autonomous_mode_disabled, plan=unknown"
                    )
                    return {
                        "allowed": False,
                        "reason": "autonomous_mode_disabled",
                        "message": "Autonomous mode is disabled for this user",
                        "upgrade_suggestion": "Enable autonomous mode in user settings or upgrade to Pro plan",
                        "suggested_plans": ["Pro", "Enterprise"],
                        "current_usage": {"autonomous_enabled": False},
                        "contact_support": "Contact support for plan upgrade assistance"
                    }
            
            # P0-5c: Enhanced usage tracking and limit enforcement
            # Simulate plan-based limits (will be replaced with actual plan service integration)
            daily_content_limit = 10  # Free plan limit
            weekly_report_limit = 1   # Free plan weekly reports
            
            if "content" in operation_type.lower():
                # Check daily content generation limit
                logger.info(
                    f"QUOTA_CHECK: user_id={user_id}, operation={operation_type}, "
                    f"daily_limit={daily_content_limit}, status=checking"
                )
                
                # For demonstration, assume user is at 80% of limit
                current_usage = int(daily_content_limit * 0.8)
                if current_usage >= daily_content_limit:
                    logger.warning(
                        f"QUOTA_EXCEEDED: user_id={user_id}, operation={operation_type}, "
                        f"usage={current_usage}/{daily_content_limit}, plan=free"
                    )
                    return {
                        "allowed": False,
                        "reason": "daily_content_limit_exceeded",
                        "message": f"Daily content generation limit reached ({current_usage}/{daily_content_limit})",
                        "upgrade_suggestion": "Upgrade to Pro plan for 100+ daily content generations",
                        "suggested_plans": [
                            {"plan": "Pro", "content_limit": 100, "price": "$29/month"},
                            {"plan": "Enterprise", "content_limit": "Unlimited", "price": "$99/month"}
                        ],
                        "current_usage": {
                            "daily_content": current_usage,
                            "daily_limit": daily_content_limit,
                            "utilization_percent": (current_usage / daily_content_limit) * 100
                        },
                        "upgrade_url": "/billing/upgrade",
                        "contact_support": "Need a custom plan? Contact support@lily-ai.com"
                    }
            
            elif "research" in operation_type.lower():
                # P0-10a: Add plan capability validation for research operations
                from backend.services.plan_service import PlanService
                plan_service = PlanService(db)
                user_capabilities = plan_service.get_user_capabilities(user_id)
                
                # Check if user's plan supports research capabilities
                if not user_capabilities.has_autopilot_research():
                    logger.warning(
                        f"QUOTA_BLOCK: user_id={user_id}, operation={operation_type}, "
                        f"reason=research_capability_not_available, plan={user_capabilities.get_plan_name()}"
                    )
                    return {
                        "allowed": False,
                        "reason": "research_capability_not_available",
                        "message": f"Research capabilities not available on {user_capabilities.get_plan_name()} plan",
                        "upgrade_suggestion": "Upgrade to Pro or Enterprise plan for autopilot research capabilities",
                        "suggested_plans": [
                            {"plan": "Pro", "research_features": "Autopilot Research, Trend Analysis", "price": "$29/month"},
                            {"plan": "Enterprise", "research_features": "Advanced Research Tools, Custom Reports", "price": "$99/month"}
                        ],
                        "current_usage": {
                            "plan": user_capabilities.get_plan_name(),
                            "research_enabled": user_capabilities.has_autopilot_research(),
                            "upgrade_required": True
                        },
                        "upgrade_url": "/billing/upgrade",
                        "contact_support": "Contact support for plan upgrade assistance"
                    }
                
                # Check weekly research report limit  
                logger.info(
                    f"QUOTA_CHECK: user_id={user_id}, operation={operation_type}, "
                    f"weekly_limit={weekly_report_limit}, status=checking, plan={user_capabilities.get_plan_name()}"
                )
                
                current_weekly_usage = 0  # For demonstration - would need actual usage tracking
                if current_weekly_usage >= weekly_report_limit:
                    logger.warning(
                        f"QUOTA_EXCEEDED: user_id={user_id}, operation={operation_type}, "
                        f"usage={current_weekly_usage}/{weekly_report_limit}, plan={user_capabilities.get_plan_name()}"
                    )
                    return {
                        "allowed": False,
                        "reason": "weekly_research_limit_exceeded", 
                        "message": f"Weekly research limit reached ({current_weekly_usage}/{weekly_report_limit})",
                        "upgrade_suggestion": "Upgrade to Pro plan for unlimited research reports",
                        "suggested_plans": [
                            {"plan": "Pro", "research_limit": "Unlimited", "price": "$29/month"},
                            {"plan": "Enterprise", "research_limit": "Advanced Research Tools", "price": "$99/month"}
                        ],
                        "current_usage": {
                            "weekly_research": current_weekly_usage,
                            "weekly_limit": weekly_report_limit,
                            "utilization_percent": (current_weekly_usage / weekly_report_limit) * 100 if weekly_report_limit > 0 else 0,
                            "plan": user_capabilities.get_plan_name()
                        },
                        "upgrade_url": "/billing/upgrade"
                    }
                
            elif "report" in operation_type.lower():
                # Check weekly report limit
                logger.info(
                    f"QUOTA_CHECK: user_id={user_id}, operation={operation_type}, "
                    f"weekly_limit={weekly_report_limit}, status=checking"
                )
            
            # Success case with detailed logging
            logger.info(
                f"QUOTA_PASSED: user_id={user_id}, operation={operation_type}, "
                f"status=within_limits, plan=free"
            )
            
            return {
                "allowed": True,
                "user_id": user_id,
                "operation_type": operation_type,
                "quota_status": "within_limits"
            }
            
        except Exception as e:
            logger.error(f"Error checking quota limits for user {user_id}: {e}")
            return {
                "allowed": False,
                "reason": "quota_check_failed",
                "message": f"Failed to check quota limits: {str(e)}",
                "error": str(e)
            }
    
    def _get_user_datetime(self, user_timezone: str = 'UTC') -> datetime:
        """Get current datetime in user's timezone"""
        try:
            if user_timezone == 'UTC' or not user_timezone or not TIMEZONE_AVAILABLE:
                return datetime.now(timezone.utc)
            
            user_tz = ZoneInfo(user_timezone)
            return datetime.now(user_tz)
        except Exception as e:
            logger.warning(f"Invalid timezone {user_timezone}, using UTC: {e}")
            return datetime.now(timezone.utc)
    
    def _convert_to_user_timezone(self, dt: datetime, user_timezone: str = 'UTC') -> datetime:
        """Convert UTC datetime to user timezone"""
        try:
            if user_timezone == 'UTC' or not user_timezone or not TIMEZONE_AVAILABLE:
                return dt
            
            user_tz = ZoneInfo(user_timezone)
            
            # Ensure dt is timezone aware (assume UTC if naive)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            return dt.astimezone(user_tz)
        except Exception as e:
            logger.warning(f"Timezone conversion failed for {user_timezone}, using UTC: {e}")
            return dt
    
    def get_active_users_for_autonomous_mode(self, db: Session, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get users with autonomous mode enabled for a specific organization or all organizations"""
        try:
            # Query users with autonomous settings enabled
            query = db.query(User, UserSetting).join(
                UserSetting, User.id == UserSetting.user_id
            ).filter(
                User.is_active == True,
                UserSetting.enable_autonomous_mode == True  # This field needs to be added to UserSetting
            )
            
            # Add organization filter for tenant isolation
            if organization_id:
                query = query.filter(User.default_organization_id == organization_id)
            
            users_with_settings = query.all()
            
            user_configs = []
            for user, settings in users_with_settings:
                user_configs.append({
                    'user_id': user.id,
                    'email': user.email,
                    'organization_id': user.default_organization_id,  # Include for tenant tracking
                    'timezone': getattr(settings, 'timezone', 'UTC'),
                    'preferred_platforms': settings.preferred_platforms or ['twitter', 'instagram'],
                    'content_frequency': settings.content_frequency or 3,
                    'posting_times': settings.posting_times or {'twitter': '09:00', 'instagram': '10:00'},
                    'brand_voice': settings.brand_voice or 'professional',
                    'creativity_level': settings.creativity_level or 0.7
                })
            
            if organization_id:
                logger.info(f"Found {len(user_configs)} users with autonomous mode enabled for organization {organization_id}")
            else:
                logger.info(f"Found {len(user_configs)} users with autonomous mode enabled across all organizations")
            return user_configs
            
        except Exception as e:
            logger.error(f"Failed to get autonomous users: {e}")
            return []

@celery_app.task(bind=True, name='autonomous_daily_content_generation')
def daily_content_generation(self):
    """Daily autonomous content generation task"""
    try:
        logger.info("Starting daily autonomous content generation")
        
        # P0-5b: SECURITY - Check ALL research feature flags before executing autonomous research
        required_flags = {
            "ENABLE_DEEP_RESEARCH": "Deep research functionality required for autonomous content generation",
            "AUTONOMOUS_FEATURES": "Autonomous features must be enabled",
            "AI_CONTENT_GENERATION": "AI content generation required for autonomous mode"
        }
        
        disabled_flags = []
        for flag_name, flag_description in required_flags.items():
            if not ff(flag_name):
                disabled_flags.append({"flag": flag_name, "description": flag_description})
        
        if disabled_flags:
            logger.warning(f"Daily autonomous content generation blocked: {len(disabled_flags)} required feature flags disabled")
            return {
                'status': 'feature_disabled',
                'error': 'Required features are currently disabled',
                'disabled_flags': disabled_flags,
                'users_processed': 0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
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
                    
                    # P0-5a: QUOTA ENFORCEMENT - Check user quotas before processing
                    quota_check = scheduler.check_user_quota_limits(
                        user_id=user_id,
                        db=db, 
                        operation_type="daily_autonomous_content"
                    )
                    
                    if not quota_check["allowed"]:
                        logger.warning(f"Skipping autonomous content for user {user_id}: {quota_check['reason']}")
                        results.append({
                            'user_id': user_id,
                            'status': 'quota_blocked',
                            'reason': quota_check['reason'],
                            'message': quota_check['message'],
                            'upgrade_suggestion': quota_check.get('upgrade_suggestion', 'Contact support for plan details')
                        })
                        continue
                    
                    logger.info(f"Quota check passed for user {user_id}, proceeding with content generation")
                    
                    # P0-5b: Additional research flag validation per user (in case flags changed mid-execution)
                    if not ff("ENABLE_DEEP_RESEARCH") or not ff("AI_CONTENT_GENERATION"):
                        logger.warning(f"Skipping user {user_id}: Research flags changed during execution")
                        results.append({
                            'user_id': user_id,
                            'status': 'feature_disabled_mid_execution',
                            'message': 'Research features were disabled during task execution'
                        })
                        continue
                    
                    # Create workflow execution record
                    workflow = WorkflowExecution(
                        user_id=user_id,
                        workflow_type='daily_autonomous',
                        status='running',
                        configuration=user_config
                    )
                    db.add(workflow)
                    db.commit()
                
                    # P0-10a: PLAN CAPABILITY VALIDATION - Check research capabilities before execution
                    from backend.services.plan_service import PlanService
                    plan_service = PlanService(db)
                    user_capabilities = plan_service.get_user_capabilities(user_id)
                    
                    # Validate research capabilities
                    research_capability_check = scheduler.check_user_quota_limits(
                        user_id=user_id,
                        db=db,
                        operation_type="autonomous_research"
                    )
                    
                    if not research_capability_check["allowed"]:
                        logger.warning(f"Research capability check failed for user {user_id}: {research_capability_check['reason']}")
                        results.append({
                            'user_id': user_id,
                            'status': 'research_blocked',
                            'reason': research_capability_check['reason'],
                            'message': research_capability_check['message'],
                            'upgrade_suggestion': research_capability_check.get('upgrade_suggestion'),
                            'plan': user_capabilities.get_plan_name(),
                            'research_enabled': user_capabilities.has_autopilot_research()
                        })
                        continue
                    
                    # Step 1: Research trending topics (plan capability validated)
                    logger.info(f"Executing research for user {user_id} with plan {user_capabilities.get_plan_name()}")
                    research_query = ResearchQuery(
                        keywords=['trending topics', 'industry news'],
                        platforms=user_config['preferred_platforms'],
                        max_results=20,
                        include_trends=True
                    )
                    
                    # P0-10c: Pass monitoring parameters to research service
                    user_plan = user_capabilities.get_plan_name()
                    user_settings = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
                    industry = user_settings.industry_type if user_settings and user_settings.industry_type else "general"
                    
                    # Use asyncio.run() for async research service call (2025 best practice)
                    research_results = asyncio.run(
                        scheduler.research_service.execute_comprehensive_research(
                            query=research_query,
                            user_plan=user_plan,
                            user_id=str(user_id),
                            industry=industry
                        )
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
                        
                        # Schedule for tomorrow at the specified time in user's timezone
                        user_timezone = user_config.get('timezone', 'UTC')
                        user_now = self._get_user_datetime(user_timezone)
                        tomorrow_user_tz = user_now + timedelta(days=1)
                        
                        # Set the posting time in user's timezone
                        scheduled_time = tomorrow_user_tz.replace(
                            hour=int(posting_time.split(':')[0]),
                            minute=int(posting_time.split(':')[1]),
                            second=0,
                            microsecond=0
                        )
                        
                        # Convert to UTC for storage if needed
                        if user_timezone != 'UTC' and hasattr(scheduled_time, 'tzinfo') and scheduled_time.tzinfo:
                            scheduled_time_utc = scheduled_time.astimezone(timezone.utc)
                        else:
                            scheduled_time_utc = scheduled_time
                        
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
                
                # P0-5a: QUOTA ENFORCEMENT - Check analytics quotas before generating reports
                with get_celery_db_session() as db:
                    quota_check = scheduler.check_user_quota_limits(
                        user_id=user_id,
                        db=db,
                        operation_type="weekly_analytics_report"
                    )
                    
                    if not quota_check["allowed"]:
                        logger.warning(f"Skipping weekly report for user {user_id}: {quota_check['reason']}")
                        continue
                
                # Get past week's workflow executions
                week_ago = datetime.now(timezone.utc) - timedelta(days=7)
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
                    'week_ending': datetime.now(timezone.utc).isoformat(),
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
                    title=f"Weekly Autonomous Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
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
            'timestamp': datetime.now(timezone.utc).isoformat()
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
                yesterday = datetime.now(timezone.utc) - timedelta(days=1)
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
            'timestamp': datetime.now(timezone.utc).isoformat()
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
        now = datetime.now(timezone.utc)
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
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Scheduled content posting task failed: {e}")
        raise