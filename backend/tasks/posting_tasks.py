# Ensure warnings are suppressed in worker processes
from backend.core.suppress_warnings import suppress_third_party_warnings
suppress_third_party_warnings()

from backend.tasks.celery_app import celery_app
from backend.agents.tools import twitter_tool
from backend.db.database import get_db
from backend.db.models import ContentLog
from backend.core.feature_flags import ff
from backend.core.dlq import handle_task_failure, TaskFailureReason
import logging
import hashlib
import traceback
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=2,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
    reject_on_worker_lost=True
)
def schedule_post(self, content, platform, scheduled_time=None, user_id=None, organization_id=None, idempotency_key=None):
    """Schedule a post for a specific platform with idempotency"""
    try:
        # CRITICAL: Validate tenant isolation
        if not user_id:
            raise ValueError("user_id is required for tenant isolation")
        if not organization_id:
            raise ValueError("organization_id is required for tenant isolation")
            
        if scheduled_time is None:
            scheduled_time = datetime.utcnow() + timedelta(hours=1)
        
        # Create idempotency key if not provided
        if not idempotency_key:
            content_hash = hashlib.sha256(f"{user_id}_{platform}_{content}_{scheduled_time}".encode()).hexdigest()[:16]
            idempotency_key = f"schedule_{content_hash}"
        
        # Check for existing post with same idempotency key
        db = next(get_db())
        try:
            # SECURITY: Validate user belongs to organization before proceeding
            from backend.db.models import UserOrganizationRole
            membership = db.query(UserOrganizationRole).filter(
                UserOrganizationRole.user_id == user_id,
                UserOrganizationRole.organization_id == organization_id
            ).first()
            
            if not membership:
                logger.error(f"SECURITY VIOLATION: User {user_id} attempted to schedule post for org {organization_id} without membership")
                raise ValueError(f"User {user_id} does not belong to organization {organization_id}")
            
            # Check for existing post with same idempotency key AND user
            existing = db.query(ContentLog).filter(
                ContentLog.external_post_id == idempotency_key,
                ContentLog.user_id == user_id  # Additional security: scope to user
            ).first()
            
            if existing:
                logger.info(f"Post already scheduled with key {idempotency_key}")
                return {
                    'status': 'already_scheduled',
                    'content': existing.content,
                    'platform': existing.platform,
                    'scheduled_for': existing.scheduled_for.isoformat(),
                    'post_id': str(existing.id)
                }
            
            # Create new content log entry
            content_log = ContentLog(
                user_id=user_id,
                platform=platform,
                content=content,
                status="scheduled",
                scheduled_for=scheduled_time,
                external_post_id=idempotency_key,
                content_type="text"
            )
            db.add(content_log)
            db.commit()
            db.refresh(content_log)
            
            result = {
                'status': 'scheduled',
                'content': content,
                'platform': platform,
                'scheduled_for': scheduled_time.isoformat(),
                'post_id': str(content_log.id),
                'idempotency_key': idempotency_key
            }
            
            logger.info(f"Post scheduled for {platform} at {scheduled_time} with key {idempotency_key}")
            
            return result
            
        finally:
            db.close()
        
    except Exception as exc:
        logger.error(f"Post scheduling failed: {str(exc)}")
        
        # Record failure in DLQ if max retries exceeded
        if self.request.retries >= self.max_retries:
            handle_task_failure(
                task_id=self.request.id,
                task_name="schedule_post",
                queue_name=getattr(self.request, 'delivery_info', {}).get('routing_key', 'posting'),
                error=exc,
                traceback_str=traceback.format_exc(),
                retry_count=self.request.retries,
                organization_id=organization_id,
                user_id=user_id,
                task_args=(content, platform, scheduled_time),
                task_kwargs={
                    'user_id': user_id,
                    'organization_id': organization_id,
                    'idempotency_key': idempotency_key
                }
            )
        
        raise

@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=2,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
    reject_on_worker_lost=True
)
def publish_post(self, content, platform, post_id=None, user_id=None, organization_id=None, idempotency_key=None):
    """Publish a post immediately to the specified platform with idempotency"""
    try:
        # CRITICAL: Validate tenant isolation
        if not user_id:
            raise ValueError("user_id is required for tenant isolation")
        if not organization_id:
            raise ValueError("organization_id is required for tenant isolation")
            
        # Create idempotency key if not provided
        if not idempotency_key:
            content_hash = hashlib.sha256(f"{user_id}_{platform}_{content}".encode()).hexdigest()[:16]
            idempotency_key = f"publish_{content_hash}"
        
        # Check for existing published post with same idempotency key
        db = next(get_db())
        try:
            existing = db.query(ContentLog).filter(
                ContentLog.external_post_id == idempotency_key,
                ContentLog.status == "published"
            ).first()
            
            if existing:
                logger.info(f"Post already published with key {idempotency_key}")
                return {
                    'status': 'already_published',
                    'platform': existing.platform,
                    'content': existing.content,
                    'platform_post_id': existing.platform_post_id,
                    'published_at': existing.published_at.isoformat() if existing.published_at else None
                }
            
            # Use stub integrations if feature flag is enabled
            if ff("USE_STUB_INTEGRATIONS"):
                # Simulate successful publishing
                platform_post_id = f"{platform}_{int(datetime.utcnow().timestamp())}"
                result = {
                    'status': 'published',
                    'platform': platform,
                    'content': content,
                    'platform_post_id': platform_post_id,
                    'published_at': datetime.utcnow().isoformat(),
                    'note': 'Published via stub integration'
                }
            else:
                # Real platform integrations
                if platform.lower() == 'twitter':
                    result = twitter_tool.post_tweet(content)
                    
                    if result['status'] != 'success':
                        raise Exception(f"Twitter API error: {result.get('error', 'Unknown error')}")
                        
                    result = {
                        'status': 'published',
                        'platform': platform,
                        'content': content,
                        'platform_post_id': result['tweet_id'],
                        'published_at': datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f'Platform {platform} not yet supported')
            
            # Update or create content log entry
            if post_id:
                # Update existing scheduled post
                content_log = db.query(ContentLog).filter(ContentLog.id == int(post_id)).first()
                if content_log:
                    content_log.status = "published"
                    content_log.published_at = datetime.utcnow()
                    content_log.platform_post_id = result['platform_post_id']
                    content_log.external_post_id = idempotency_key
                else:
                    raise Exception(f"Content log {post_id} not found")
            else:
                # Create new content log entry
                content_log = ContentLog(
                    user_id=user_id,
                    platform=platform,
                    content=content,
                    status="published",
                    published_at=datetime.utcnow(),
                    platform_post_id=result['platform_post_id'],
                    external_post_id=idempotency_key,
                    content_type="text"
                )
                db.add(content_log)
            
            db.commit()
            logger.info(f"Post published successfully to {platform} with key {idempotency_key}")
            
            return result
            
        finally:
            db.close()
            
    except Exception as exc:
        logger.error(f"Post publishing failed: {str(exc)}")
        
        # Record failure in DLQ if max retries exceeded
        if self.request.retries >= self.max_retries:
            handle_task_failure(
                task_id=self.request.id,
                task_name="publish_post",
                queue_name=getattr(self.request, 'delivery_info', {}).get('routing_key', 'posting'),
                error=exc,
                traceback_str=traceback.format_exc(),
                retry_count=self.request.retries,
                organization_id=organization_id,
                user_id=user_id,
                task_args=(content, platform),
                task_kwargs={
                    'post_id': post_id,
                    'user_id': user_id,
                    'organization_id': organization_id,
                    'idempotency_key': idempotency_key
                }
            )
        
        raise

@celery_app.task(bind=True, acks_late=True)
def batch_publish_posts(self, posts):
    """Publish multiple posts across different platforms"""
    try:
        results = []
        
        for post in posts:
            result = publish_post.apply_async(
                args=[post['content'], post['platform']],
                kwargs={'post_id': post.get('id')}
            )
            
            results.append({
                'original_post': post,
                'task_id': result.id,
                'status': 'queued'
            })
        
        return {
            'status': 'success',
            'message': f'Batch publishing initiated for {len(posts)} posts',
            'results': results
        }
        
    except Exception as exc:
        logger.error(f"Batch publishing failed: {str(exc)}")
        return {
            'status': 'error',
            'message': f'Batch publishing failed: {str(exc)}'
        }

@celery_app.task(bind=True, acks_late=True)
def validate_post_content(self, content, platform):
    """Validate post content against platform requirements"""
    try:
        issues = []
        
        # Platform-specific validation
        if platform.lower() == 'twitter':
            if len(content) > 280:
                issues.append(f"Content too long: {len(content)} characters (max: 280)")
        
        elif platform.lower() == 'linkedin':
            if len(content) > 3000:
                issues.append(f"Content too long: {len(content)} characters (max: 3000)")
        
        elif platform.lower() == 'instagram':
            if len(content) > 2200:
                issues.append(f"Content too long: {len(content)} characters (max: 2200)")
        
        # General validation
        if not content.strip():
            issues.append("Content is empty")
        
        # Check for excessive hashtags
        hashtag_count = content.count('#')
        if hashtag_count > 10:
            issues.append(f"Too many hashtags: {hashtag_count} (recommended: 5-10)")
        
        # Check for URLs (basic validation)
        if 'http://' in content or 'https://' in content:
            url_count = content.count('http://') + content.count('https://')
            if url_count > 2:
                issues.append(f"Too many URLs: {url_count} (recommended: 1-2)")
        
        return {
            'status': 'success',
            'valid': len(issues) == 0,
            'issues': issues,
            'content_length': len(content),
            'platform': platform
        }
        
    except Exception as exc:
        logger.error(f"Content validation failed: {str(exc)}")
        return {
            'status': 'error',
            'message': f'Content validation failed: {str(exc)}'
        }

@celery_app.task(bind=True, acks_late=True)
def get_optimal_posting_time(self, platform, timezone='UTC'):
    """Get optimal posting time for a platform"""
    try:
        # Default optimal times (these would ideally come from analytics)
        optimal_times = {
            'twitter': {
                'weekdays': ['09:00', '12:00', '15:00', '17:00'],
                'weekends': ['10:00', '14:00', '16:00']
            },
            'linkedin': {
                'weekdays': ['08:00', '10:00', '12:00', '17:00'],
                'weekends': ['09:00', '11:00']
            },
            'instagram': {
                'weekdays': ['11:00', '13:00', '17:00', '19:00'],
                'weekends': ['10:00', '12:00', '15:00']
            }
        }
        
        current_time = datetime.utcnow()
        is_weekend = current_time.weekday() >= 5  # Saturday = 5, Sunday = 6
        
        platform_times = optimal_times.get(platform.lower(), optimal_times['twitter'])
        times = platform_times['weekends'] if is_weekend else platform_times['weekdays']
        
        # Find next optimal time
        next_optimal = None
        for time_str in times:
            hour, minute = map(int, time_str.split(':'))
            optimal_datetime = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if optimal_datetime > current_time:
                next_optimal = optimal_datetime
                break
        
        # If no time today, use first time tomorrow
        if next_optimal is None:
            tomorrow = current_time + timedelta(days=1)
            hour, minute = map(int, times[0].split(':'))
            next_optimal = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return {
            'status': 'success',
            'platform': platform,
            'next_optimal_time': next_optimal.isoformat(),
            'all_optimal_times': times,
            'timezone': timezone,
            'is_weekend': is_weekend
        }
        
    except Exception as exc:
        logger.error(f"Optimal time calculation failed: {str(exc)}")
        return {
            'status': 'error',
            'message': f'Optimal time calculation failed: {str(exc)}'
        }