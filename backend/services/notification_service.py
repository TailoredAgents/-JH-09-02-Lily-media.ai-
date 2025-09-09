"""
Real-time Notification Service with WebSocket Support
Handles notifications, real-time delivery, and event triggers for goals and social media
"""
import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.db.database import get_db
from backend.db.models import Notification, User, SocialPost, SocialPlatformConnection, Goal, GoalProgress
from backend.core.audit_logger import log_content_event, AuditEventType

logger = logging.getLogger(__name__)

class NotificationType(str, Enum):
    """Notification types for the system"""
    # Goal tracking notifications (existing)
    MILESTONE_25 = "milestone_25"
    MILESTONE_50 = "milestone_50" 
    MILESTONE_75 = "milestone_75"
    MILESTONE_90 = "milestone_90"
    GOAL_COMPLETED = "goal_completed"
    GOAL_OVERDUE = "goal_overdue"
    GOAL_AT_RISK = "goal_at_risk"
    PROGRESS_STAGNANT = "progress_stagnant"
    EXCEPTIONAL_PROGRESS = "exceptional_progress"
    
    # Social media events (new)
    POST_PUBLISHED = "post_published"
    POST_FAILED = "post_failed"
    ENGAGEMENT_MILESTONE = "engagement_milestone"
    PLATFORM_CONNECTED = "platform_connected"
    PLATFORM_DISCONNECTED = "platform_disconnected"
    OAUTH_EXPIRED = "oauth_expired"
    
    # System events (new)
    SYSTEM_MAINTENANCE = "system_maintenance"
    SYSTEM_ERROR = "system_error"
    FEATURE_ANNOUNCEMENT = "feature_announcement"
    SECURITY_ALERT = "security_alert"
    
    # Content events (new)
    CONTENT_GENERATED = "content_generated"
    CONTENT_SCHEDULED = "content_scheduled"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    
    # Lead management events (PW-DM-ADD-002)
    LEAD_MEDIA_RECEIVED = "lead_media_received"
    LEAD_CREATED_FROM_DM = "lead_created_from_dm"
    LEAD_QUOTE_GENERATED = "lead_quote_generated"

class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class NotificationMessage:
    """Notification message structure"""
    id: str
    user_id: int
    goal_id: Optional[str]
    notification_type: NotificationType
    title: str
    message: str
    priority: str  # high, medium, low
    action_url: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

class WebSocketManager:
    """Manages WebSocket connections for real-time notifications"""
    
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int, client_info: Optional[Dict] = None):
        """Accept WebSocket connection and register user"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.now(timezone.utc),
            "client_info": client_info or {}
        }
        
        logger.info(f"User {user_id} connected via WebSocket. Total connections: {self._get_total_connections()}")
        
        # Send welcome message with current notification count
        await self._send_welcome_message(websocket, user_id)
    
    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.connection_metadata:
            user_id = self.connection_metadata[websocket]["user_id"]
            
            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove metadata
            del self.connection_metadata[websocket]
            
            logger.info(f"User {user_id} disconnected from WebSocket. Total connections: {self._get_total_connections()}")
    
    async def send_notification_to_user(self, user_id: int, notification_data: Dict[str, Any]):
        """Send notification to all connections for a specific user"""
        if user_id not in self.active_connections:
            logger.debug(f"No active connections for user {user_id}")
            return
        
        # Prepare notification message
        message = {
            "type": "notification",
            "data": notification_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Send to all user connections
        disconnected_connections = set()
        for websocket in self.active_connections[user_id].copy():
            try:
                await websocket.send_text(json.dumps(message))
                logger.debug(f"Sent notification to user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to send notification to user {user_id}: {e}")
                disconnected_connections.add(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected_connections:
            await self.disconnect(websocket)
    
    async def broadcast_system_notification(self, notification_data: Dict[str, Any], exclude_users: Optional[List[int]] = None):
        """Broadcast notification to all connected users"""
        exclude_users = exclude_users or []
        
        message = {
            "type": "system_notification",
            "data": notification_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        for user_id, connections in self.active_connections.items():
            if user_id in exclude_users:
                continue
            
            disconnected_connections = set()
            for websocket in connections.copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to broadcast to user {user_id}: {e}")
                    disconnected_connections.add(websocket)
            
            # Clean up disconnected connections
            for websocket in disconnected_connections:
                await self.disconnect(websocket)
    
    async def _send_welcome_message(self, websocket: WebSocket, user_id: int):
        """Send welcome message with unread notification count"""
        try:
            db = next(get_db())
            unread_count = db.query(Notification).filter(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            ).count()
            
            welcome_message = {
                "type": "welcome",
                "data": {
                    "user_id": user_id,
                    "unread_notifications": unread_count,
                    "connection_status": "connected"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send_text(json.dumps(welcome_message))
            
        except Exception as e:
            logger.error(f"Failed to send welcome message to user {user_id}: {e}")
        finally:
            db.close()
    
    def _get_total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            "total_connections": self._get_total_connections(),
            "connected_users": len(self.active_connections),
            "connections_per_user": {
                user_id: len(connections) 
                for user_id, connections in self.active_connections.items()
            }
        }

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

class NotificationService:
    """Enhanced service for creating, managing, and delivering notifications"""
    
    def __init__(self):
        self.websocket_manager = websocket_manager
        self.milestone_thresholds = [25, 50, 75, 90, 100]
        self.notification_cooldown = timedelta(hours=6)  # Minimum time between similar notifications
        self.at_risk_days_threshold = 7  # Days before deadline to warn about slow progress
        self.stagnant_days_threshold = 14  # Days without progress to consider stagnant
    
    async def create_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        goal_id: Optional[str] = None,
        content_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_send: bool = True
    ) -> Notification:
        """Create a new notification and optionally send it in real-time"""
        
        db = next(get_db())
        try:
            # Create notification record
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type.value,
                priority=priority.value,
                goal_id=goal_id,
                content_id=content_id,
                workflow_id=workflow_id,
                notification_metadata=metadata or {}
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            logger.info(f"Created notification {notification.id} for user {user_id}: {title}")
            
            # Log audit event
            log_content_event(
                AuditEventType.SYSTEM_ACCESS,
                user_id=user_id,
                resource="notification",
                action="create",
                additional_data={
                    "notification_id": notification.id,
                    "type": notification_type.value,
                    "priority": priority.value,
                    "title": title
                }
            )
            
            # Send real-time notification if requested
            if auto_send:
                await self._send_real_time_notification(notification)
            
            return notification
            
        except Exception as e:
            logger.error(f"Failed to create notification for user {user_id}: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    async def _send_real_time_notification(self, notification: Notification):
        """Send notification via WebSocket"""
        try:
            notification_data = {
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "type": notification.notification_type,
                "priority": notification.priority,
                "goal_id": notification.goal_id,
                "content_id": notification.content_id,
                "workflow_id": notification.workflow_id,
                "metadata": notification.notification_metadata,
                "created_at": notification.created_at.isoformat(),
                "is_read": notification.is_read
            }
            
            await self.websocket_manager.send_notification_to_user(
                notification.user_id,
                notification_data
            )
            
        except Exception as e:
            logger.error(f"Failed to send real-time notification {notification.id}: {e}")
    
    async def mark_as_read(self, notification_id: str, user_id: int) -> bool:
        """Mark notification as read"""
        db = next(get_db())
        try:
            notification = db.query(Notification).filter(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            ).first()
            
            if not notification:
                return False
            
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            db.commit()
            
            logger.info(f"Marked notification {notification_id} as read for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark notification {notification_id} as read: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all unread notifications as read for a user"""
        db = next(get_db())
        try:
            updated_count = db.query(Notification).filter(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            ).update({
                "is_read": True,
                "read_at": datetime.now(timezone.utc)
            })
            
            db.commit()
            
            logger.info(f"Marked {updated_count} notifications as read for user {user_id}")
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to mark all notifications as read for user {user_id}: {e}")
            db.rollback()
            return 0
        finally:
            db.close()
    
    def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        notification_types: Optional[List[NotificationType]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """Get user notifications with filtering"""
        db = next(get_db())
        try:
            query = db.query(Notification).filter(Notification.user_id == user_id)
            
            if unread_only:
                query = query.filter(Notification.is_read == False)
            
            if notification_types:
                type_values = [nt.value for nt in notification_types]
                query = query.filter(Notification.notification_type.in_(type_values))
            
            notifications = query.order_by(
                Notification.created_at.desc()
            ).offset(offset).limit(limit).all()
            
            return notifications
            
        finally:
            db.close()
    
    def get_notification_stats(self, user_id: int) -> Dict[str, Any]:
        """Get notification statistics for a user"""
        db = next(get_db())
        try:
            total_notifications = db.query(Notification).filter(
                Notification.user_id == user_id
            ).count()
            
            unread_notifications = db.query(Notification).filter(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            ).count()
            
            # Count by type
            type_counts = {}
            for notification_type in NotificationType:
                count = db.query(Notification).filter(
                    and_(
                        Notification.user_id == user_id,
                        Notification.notification_type == notification_type.value
                    )
                ).count()
                type_counts[notification_type.value] = count
            
            return {
                "total_notifications": total_notifications,
                "unread_notifications": unread_notifications,
                "read_notifications": total_notifications - unread_notifications,
                "notifications_by_type": type_counts
            }
            
        finally:
            db.close()
    
    # Goal notification methods (preserved from original implementation)
    
    def detect_milestone_achievements(
        self, 
        goal: Goal, 
        old_progress: float, 
        new_progress: float
    ) -> List[NotificationType]:
        """Detect which milestones were achieved with this progress update"""
        achieved_milestones = []
        
        for threshold in self.milestone_thresholds:
            # Check if we crossed a milestone threshold
            if old_progress < threshold <= new_progress:
                if threshold == 25:
                    achieved_milestones.append(NotificationType.MILESTONE_25)
                elif threshold == 50:
                    achieved_milestones.append(NotificationType.MILESTONE_50)
                elif threshold == 75:
                    achieved_milestones.append(NotificationType.MILESTONE_75)
                elif threshold == 90:
                    achieved_milestones.append(NotificationType.MILESTONE_90)
                elif threshold >= 100:
                    achieved_milestones.append(NotificationType.GOAL_COMPLETED)
        
        return achieved_milestones
    
    async def process_goal_progress_update(
        self, 
        db: Session, 
        goal: Goal, 
        old_value: float, 
        new_value: float
    ) -> List[NotificationMessage]:
        """Process a goal progress update and generate appropriate notifications"""
        notifications = []
        
        if goal.target_value <= 0:
            return notifications
        
        # Calculate progress percentages
        old_progress = (old_value / goal.target_value) * 100
        new_progress = (new_value / goal.target_value) * 100
        
        # Detect milestone achievements
        achieved_milestones = self.detect_milestone_achievements(goal, old_progress, new_progress)
        
        for milestone_type in achieved_milestones:
            # Generate and create notification
            notification_content = self._get_milestone_content(goal, milestone_type, new_progress)
            
            notification = await self.create_notification(
                user_id=goal.user_id,
                title=notification_content["title"],
                message=notification_content["message"],
                notification_type=milestone_type,
                priority=NotificationPriority(notification_content["priority"]),
                goal_id=goal.id,
                metadata={
                    "goal_title": goal.title,
                    "progress_percentage": new_progress,
                    "target_value": goal.target_value,
                    "current_value": goal.current_value,
                    "goal_type": goal.goal_type,
                    "platform": goal.platform
                }
            )
            
            # Convert to NotificationMessage for compatibility
            notifications.append(NotificationMessage(
                id=notification.id,
                user_id=notification.user_id,
                goal_id=notification.goal_id,
                notification_type=milestone_type,
                title=notification.title,
                message=notification.message,
                priority=notification.priority,
                action_url=f"/goals/{goal.id}",
                metadata=notification.notification_metadata,
                created_at=notification.created_at
            ))
        
        logger.info(f"Generated {len(notifications)} notifications for goal {goal.id} progress update")
        return notifications
    
    def _get_milestone_content(
        self, 
        goal: Goal, 
        milestone_type: NotificationType, 
        progress_percentage: float
    ) -> Dict[str, str]:
        """Generate milestone-specific notification content"""
        
        content_templates = {
            NotificationType.MILESTONE_25: {
                "title": "🎯 25% Progress Milestone!",
                "message": f"Great start! You've achieved 25% progress on '{goal.title}'. Keep up the momentum!",
                "priority": "medium"
            },
            NotificationType.MILESTONE_50: {
                "title": "🚀 Halfway There!",
                "message": f"Amazing progress! You're 50% complete on '{goal.title}'. You're doing great!",
                "priority": "medium"
            },
            NotificationType.MILESTONE_75: {
                "title": "⭐ 75% Complete!",
                "message": f"Outstanding work! You've reached 75% progress on '{goal.title}'. The finish line is in sight!",
                "priority": "high"
            },
            NotificationType.MILESTONE_90: {
                "title": "🔥 90% Complete!",
                "message": f"So close! You've achieved 90% progress on '{goal.title}'. One final push to victory!",
                "priority": "high"
            },
            NotificationType.GOAL_COMPLETED: {
                "title": "🏆 Goal Achieved!",
                "message": f"Congratulations! You've successfully completed '{goal.title}'! Time to celebrate and set new goals!",
                "priority": "high"
            },
            NotificationType.GOAL_OVERDUE: {
                "title": "⏰ Goal Overdue",
                "message": f"Your goal '{goal.title}' is past its target date. Consider updating the timeline or adjusting the target.",
                "priority": "high"
            },
            NotificationType.GOAL_AT_RISK: {
                "title": "⚠️ Goal At Risk",
                "message": f"Your goal '{goal.title}' may be at risk. Current progress might not meet the target date. Consider adjusting your strategy.",
                "priority": "high"
            },
            NotificationType.PROGRESS_STAGNANT: {
                "title": "📈 Progress Update Needed",
                "message": f"No recent progress recorded for '{goal.title}'. Time to take action and move forward!",
                "priority": "medium"
            },
            NotificationType.EXCEPTIONAL_PROGRESS: {
                "title": "🌟 Exceptional Progress!",
                "message": f"Wow! Your progress on '{goal.title}' is exceptional. You're ahead of schedule - keep it up!",
                "priority": "high"
            }
        }
        
        return content_templates.get(milestone_type, {
            "title": "Goal Update",
            "message": f"Update on your goal '{goal.title}'",
            "priority": "medium"
        })
    
    # PW-DM-ADD-002: Lead media notification methods
    
    async def send_lead_media_notification(
        self,
        lead_id: str,
        media_asset_id: str,
        organization_id: str,
        user_id: int
    ) -> None:
        """
        Send internal notification about lead media received
        
        Args:
            lead_id: Lead ID that received media
            media_asset_id: Media asset ID that was attached
            organization_id: Organization ID for context
            user_id: User ID who processed the attachment
        """
        try:
            # Get lead information to create meaningful notification
            db = next(get_db())
            try:
                from backend.db.models import Lead, MediaAsset
                
                lead = db.query(Lead).filter(
                    Lead.id == lead_id,
                    Lead.organization_id == organization_id
                ).first()
                
                media_asset = db.query(MediaAsset).filter(
                    MediaAsset.id == media_asset_id,
                    MediaAsset.organization_id == organization_id
                ).first()
                
                if not lead or not media_asset:
                    logger.warning(f"Could not find lead {lead_id} or media {media_asset_id} for notification")
                    return
                
                # Create notification for the user/team
                contact_name = lead.contact_name or "Customer"
                platform = lead.source_platform or "social media"
                
                await self.create_notification(
                    user_id=user_id,
                    title=f"📸 New Media from {contact_name}",
                    message=f"{contact_name} has uploaded photos for their {platform} inquiry. Lead ID: {lead_id[:8]}... Review and update quote if needed.",
                    notification_type=NotificationType.LEAD_MEDIA_RECEIVED,
                    priority=NotificationPriority.HIGH,
                    metadata={
                        "lead_id": lead_id,
                        "media_asset_id": media_asset_id,
                        "contact_name": contact_name,
                        "source_platform": lead.source_platform,
                        "filename": media_asset.filename,
                        "file_size": media_asset.file_size,
                        "priority_score": lead.priority_score,
                        "pricing_intent": lead.pricing_intent,
                        "action_url": f"/leads/{lead_id}"
                    }
                )
                
                logger.info(f"Sent lead media notification for lead {lead_id} to user {user_id}")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to send lead media notification: {e}")
            # Don't raise exception as this is auxiliary functionality

# Global notification service instance
notification_service = NotificationService()

def get_notification_service() -> NotificationService:
    """Factory function to get notification service instance"""
    return notification_service

# Social media notification trigger functions

async def trigger_post_published_notification(user_id: int, platform: str, post_id: str, content: str):
    """Trigger notification when a post is successfully published"""
    await notification_service.create_notification(
        user_id=user_id,
        title=f"Post Published on {platform.title()}!",
        message=f"Your post has been successfully published to {platform}. Content: {content[:100]}{'...' if len(content) > 100 else ''}",
        notification_type=NotificationType.POST_PUBLISHED,
        priority=NotificationPriority.MEDIUM,
        content_id=post_id,
        metadata={
            "platform": platform,
            "post_id": post_id,
            "content_preview": content[:200]
        }
    )

async def trigger_post_failed_notification(user_id: int, platform: str, content: str, error: str):
    """Trigger notification when a post fails to publish"""
    await notification_service.create_notification(
        user_id=user_id,
        title=f"Post Failed on {platform.title()}",
        message=f"Failed to publish your post to {platform}. Error: {error}",
        notification_type=NotificationType.POST_FAILED,
        priority=NotificationPriority.HIGH,
        metadata={
            "platform": platform,
            "error": error,
            "content_preview": content[:200]
        }
    )

async def trigger_platform_connected_notification(user_id: int, platform: str, username: str):
    """Trigger notification when a social platform is connected"""
    await notification_service.create_notification(
        user_id=user_id,
        title=f"{platform.title()} Connected!",
        message=f"Successfully connected your {platform} account (@{username}). You can now start posting!",
        notification_type=NotificationType.PLATFORM_CONNECTED,
        priority=NotificationPriority.MEDIUM,
        metadata={
            "platform": platform,
            "username": username
        }
    )

async def trigger_oauth_expired_notification(user_id: int, platform: str):
    """Trigger notification when OAuth token expires"""
    await notification_service.create_notification(
        user_id=user_id,
        title=f"{platform.title()} Connection Expired",
        message=f"Your {platform} connection has expired. Please reconnect to continue posting.",
        notification_type=NotificationType.OAUTH_EXPIRED,
        priority=NotificationPriority.HIGH,
        metadata={
            "platform": platform,
            "action_required": "reconnect"
        }
    )

async def trigger_goal_progress_notification(user_id: int, goal_id: str, progress: float, milestone: str):
    """Trigger notification for goal progress milestones"""
    await notification_service.create_notification(
        user_id=user_id,
        title=f"Goal Progress: {milestone}",
        message=f"Great progress! You've reached {progress:.1f}% of your goal.",
        notification_type=NotificationType.GOAL_PROGRESS,
        priority=NotificationPriority.MEDIUM,
        goal_id=goal_id,
        metadata={
            "progress_percentage": progress,
            "milestone": milestone
        }
    )

async def trigger_goal_completed_notification(user_id: int, goal_id: str, goal_title: str):
    """Trigger notification when a goal is completed"""
    await notification_service.create_notification(
        user_id=user_id,
        title="🎉 Goal Completed!",
        message=f"Congratulations! You've completed your goal: {goal_title}",
        notification_type=NotificationType.GOAL_COMPLETED,
        priority=NotificationPriority.HIGH,
        goal_id=goal_id,
        metadata={
            "goal_title": goal_title,
            "celebration": True
        }
    )

# Legacy compatibility - GoalNotificationService alias
GoalNotificationService = NotificationService

# Export the main components
__all__ = [
    "NotificationService",
    "GoalNotificationService",  # Legacy compatibility
    "WebSocketManager", 
    "NotificationType",
    "NotificationPriority",
    "NotificationMessage",
    "notification_service",
    "get_notification_service",
    "websocket_manager",
    "trigger_post_published_notification",
    "trigger_post_failed_notification",
    "trigger_platform_connected_notification",
    "trigger_oauth_expired_notification",
    "trigger_goal_progress_notification",
    "trigger_goal_completed_notification"
]