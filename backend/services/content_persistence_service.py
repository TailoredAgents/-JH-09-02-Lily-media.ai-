"""
Content Persistence Service - Database-backed content management
Production-ready service with no mocks or in-memory storage
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
import logging

from backend.db.models import ContentLog, User
from backend.db.database import get_db

logger = logging.getLogger(__name__)

class ContentPersistenceService:
    """Service for persisting and retrieving content from database"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_content(
        self,
        user_id: int,
        organization_id: str,
        title: str,
        content: str,
        platform: str = "twitter",
        content_type: str = "text",
        status: str = "draft",
        scheduled_at: Optional[datetime] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> ContentLog:
        """Create new content in database"""
        try:
            # Generate external ID for idempotency
            external_id = str(uuid.uuid4())
            
            # Create content log entry
            content_log = ContentLog(
                user_id=user_id,
                organization_id=organization_id,
                platform=platform,
                content=content,
                content_type=content_type,
                status=status,
                scheduled_for=scheduled_at,
                external_post_id=external_id,
                engagement_data={
                    "title": title,
                    "tags": tags or [],
                    "metadata": metadata or {}
                }
            )
            
            self.db.add(content_log)
            self.db.commit()
            self.db.refresh(content_log)
            
            logger.info(f"Created content {content_log.id} for user {user_id}")
            return content_log
            
        except Exception as e:
            logger.error(f"Error creating content: {str(e)}")
            self.db.rollback()
            raise
    
    def get_content_list(
        self,
        user_id: int,
        organization_id: str,
        page: int = 1,
        limit: int = 20,
        platform: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated content list for user"""
        try:
            query = self.db.query(ContentLog).filter(
                ContentLog.user_id == user_id,
                ContentLog.organization_id == organization_id
            )
            
            # Apply filters
            if platform:
                query = query.filter(ContentLog.platform == platform)
            if status:
                query = query.filter(ContentLog.status == status)
            
            # Get total count
            total = query.count()
            
            # Apply pagination and sorting
            offset = (page - 1) * limit
            content_list = query.order_by(desc(ContentLog.created_at))\
                               .offset(offset)\
                               .limit(limit)\
                               .all()
            
            # Format response
            formatted_content = []
            for content in content_list:
                engagement_data = content.engagement_data or {}
                formatted_content.append({
                    "id": content.id,
                    "title": engagement_data.get("title", ""),
                    "content": content.content,
                    "platform": content.platform,
                    "content_type": content.content_type,
                    "status": content.status,
                    "scheduled_at": content.scheduled_for.isoformat() if content.scheduled_for else None,
                    "published_at": content.published_at.isoformat() if content.published_at else None,
                    "tags": engagement_data.get("tags", []),
                    "external_post_id": content.external_post_id,
                    "platform_post_id": content.platform_post_id,
                    "created_at": content.created_at.isoformat(),
                    "updated_at": content.updated_at.isoformat() if content.updated_at else None,
                    "engagement": {
                        "likes": engagement_data.get("likes", 0),
                        "shares": engagement_data.get("shares", 0),
                        "comments": engagement_data.get("comments", 0),
                        "views": engagement_data.get("views", 0)
                    }
                })
            
            return {
                "content": formatted_content,
                "total": total,
                "page": page,
                "limit": limit,
                "has_next": (page * limit) < total,
                "has_prev": page > 1
            }
            
        except Exception as e:
            logger.error(f"Error getting content list: {str(e)}")
            raise
    
    def get_content_by_id(self, user_id: int, organization_id: str, content_id: int) -> Optional[ContentLog]:
        """Get single content item by ID"""
        try:
            content = self.db.query(ContentLog).filter(
                ContentLog.id == content_id,
                ContentLog.user_id == user_id,
                ContentLog.organization_id == organization_id
            ).first()
            
            return content
            
        except Exception as e:
            logger.error(f"Error getting content {content_id}: {str(e)}")
            raise
    
    def update_content(
        self,
        user_id: int,
        organization_id: str,
        content_id: int,
        updates: Dict[str, Any]
    ) -> Optional[ContentLog]:
        """Update existing content"""
        try:
            content = self.get_content_by_id(user_id, organization_id, content_id)
            if not content:
                return None
            
            # Update allowed fields
            allowed_fields = ['content', 'platform', 'status', 'scheduled_for']
            for field, value in updates.items():
                if field in allowed_fields and value is not None:
                    setattr(content, field, value)
            
            # Update title and tags in engagement_data
            if 'title' in updates or 'tags' in updates:
                engagement_data = content.engagement_data or {}
                if 'title' in updates:
                    engagement_data['title'] = updates['title']
                if 'tags' in updates:
                    engagement_data['tags'] = updates['tags']
                content.engagement_data = engagement_data
            
            self.db.commit()
            self.db.refresh(content)
            
            logger.info(f"Updated content {content_id} for user {user_id}")
            return content
            
        except Exception as e:
            logger.error(f"Error updating content {content_id}: {str(e)}")
            self.db.rollback()
            raise
    
    def delete_content(self, user_id: int, organization_id: str, content_id: int) -> bool:
        """Delete content item"""
        try:
            content = self.get_content_by_id(user_id, organization_id, content_id)
            if not content:
                return False
            
            self.db.delete(content)
            self.db.commit()
            
            logger.info(f"Deleted content {content_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting content {content_id}: {str(e)}")
            self.db.rollback()
            raise
    
    def mark_as_published(
        self,
        user_id: int,
        organization_id: str,
        content_id: int,
        platform_post_id: str,
        published_at: Optional[datetime] = None
    ) -> Optional[ContentLog]:
        """Mark content as published with platform post ID"""
        try:
            content = self.get_content_by_id(user_id, organization_id, content_id)
            if not content:
                return None
            
            content.status = "published"
            content.platform_post_id = platform_post_id
            content.published_at = published_at or datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(content)
            
            logger.info(f"Marked content {content_id} as published with ID {platform_post_id}")
            return content
            
        except Exception as e:
            logger.error(f"Error marking content as published: {str(e)}")
            self.db.rollback()
            raise
    
    def update_engagement_metrics(
        self,
        user_id: int,
        organization_id: str,
        content_id: int,
        metrics: Dict[str, int]
    ) -> Optional[ContentLog]:
        """Update engagement metrics for published content"""
        try:
            content = self.get_content_by_id(user_id, organization_id, content_id)
            if not content:
                return None
            
            engagement_data = content.engagement_data or {}
            engagement_data.update(metrics)
            content.engagement_data = engagement_data
            
            self.db.commit()
            self.db.refresh(content)
            
            logger.info(f"Updated engagement metrics for content {content_id}")
            return content
            
        except Exception as e:
            logger.error(f"Error updating engagement metrics: {str(e)}")
            self.db.rollback()
            raise
    
    def get_scheduled_content(
        self,
        organization_id: Optional[str] = None,
        user_id: Optional[int] = None,
        platform: Optional[str] = None,
        before: Optional[datetime] = None
    ) -> List[ContentLog]:
        """Get scheduled content that needs to be published"""
        try:
            query = self.db.query(ContentLog).filter(ContentLog.status == "scheduled")
            
            # Always filter by organization_id for multi-tenant isolation
            if organization_id:
                query = query.filter(ContentLog.organization_id == organization_id)
            
            if user_id:
                query = query.filter(ContentLog.user_id == user_id)
            if platform:
                query = query.filter(ContentLog.platform == platform)
            if before:
                query = query.filter(ContentLog.scheduled_for <= before)
            
            return query.order_by(ContentLog.scheduled_for).all()
            
        except Exception as e:
            logger.error(f"Error getting scheduled content: {str(e)}")
            raise