"""
Notifications API Endpoints with Real-time WebSocket Support
Provides notification management, retrieval, and real-time delivery functionality
"""
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
import logging
import json

from backend.db.database import get_db
from backend.core.datetime_utils import utc_now_iso
from backend.db.models import Notification, User
from backend.auth.dependencies import get_current_active_user
from backend.services.notification_service import (
    notification_service, 
    websocket_manager, 
    NotificationType, 
    NotificationPriority
)
from backend.core.api_version import create_versioned_router

router = create_versioned_router(prefix="/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)

# Pydantic response models
class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    notification_type: str
    priority: str
    goal_id: Optional[str]
    content_id: Optional[str]
    workflow_id: Optional[str]
    is_read: bool
    is_dismissed: bool
    action_url: Optional[str]
    action_label: Optional[str]
    metadata: dict
    created_at: datetime
    read_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class CreateNotificationRequest(BaseModel):
    title: str
    message: str
    notification_type: str
    priority: str = "medium"
    goal_id: Optional[str] = None
    content_id: Optional[str] = None
    workflow_id: Optional[str] = None
    metadata: Optional[dict] = None

class WebSocketStats(BaseModel):
    total_connections: int
    connected_users: int
    connections_per_user: dict

class NotificationSummary(BaseModel):
    total_notifications: int
    unread_count: int
    high_priority_count: int
    recent_notifications: List[NotificationResponse]

# WebSocket endpoint for real-time notifications
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: int = Query(...)):
    """WebSocket endpoint for real-time notifications"""
    try:
        # In a real app, you'd validate the user_id through authentication
        # For now, we'll trust the provided user_id
        await websocket_manager.connect(websocket, user_id)
        
        logger.info(f"WebSocket connection established for user {user_id}")
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Listen for client messages (like ping/pong)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": utc_now_iso()
                    }))
                elif message.get("type") == "mark_read":
                    # Handle marking notifications as read via WebSocket
                    notification_id = message.get("notification_id")
                    if notification_id:
                        await notification_service.mark_as_read(notification_id, user_id)
                        await websocket.send_text(json.dumps({
                            "type": "marked_read",
                            "notification_id": notification_id,
                            "timestamp": utc_now_iso()
                        }))
                        
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                # Invalid JSON, send error
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error", 
                    "message": "Server error"
                }))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        await websocket_manager.disconnect(websocket)

# Admin endpoint to get WebSocket connection stats
@router.get("/ws/stats", response_model=WebSocketStats)
async def get_websocket_stats(
    current_user: User = Depends(get_current_active_user)
):
    """Get WebSocket connection statistics (admin only for now)"""
    # In production, you'd check for admin permissions here
    stats = websocket_manager.get_connection_stats()
    return WebSocketStats(**stats)

# Enhanced notification creation endpoint
@router.post("/create", response_model=NotificationResponse)
async def create_notification(
    request: CreateNotificationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new notification (admin/system use)"""
    try:
        # Validate notification type
        try:
            notification_type = NotificationType(request.notification_type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid notification type: {request.notification_type}"
            )
        
        # Validate priority
        try:
            priority = NotificationPriority(request.priority)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid priority: {request.priority}"
            )
        
        # Create notification
        notification = await notification_service.create_notification(
            user_id=current_user.id,
            title=request.title,
            message=request.message,
            notification_type=notification_type,
            priority=priority,
            goal_id=request.goal_id,
            content_id=request.content_id,
            workflow_id=request.workflow_id,
            metadata=request.metadata or {}
        )
        
        return notification
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to create notification")

# Broadcast system notification endpoint
@router.post("/broadcast")
async def broadcast_system_notification(
    request: CreateNotificationRequest,
    current_user: User = Depends(get_current_active_user),
    exclude_users: Optional[List[int]] = None
):
    """Broadcast a system notification to all connected users (admin only)"""
    # In production, you'd check for admin permissions here
    
    try:
        notification_data = {
            "title": request.title,
            "message": request.message,
            "type": request.notification_type,
            "priority": request.priority,
            "metadata": request.metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        await websocket_manager.broadcast_system_notification(
            notification_data, 
            exclude_users or []
        )
        
        return {"message": "System notification broadcasted successfully"}
        
    except Exception as e:
        logger.error(f"Error broadcasting system notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast notification")

@router.get("/", response_model=List[NotificationResponse])
async def get_user_notifications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    unread_only: bool = Query(False, description="Show only unread notifications"),
    notification_type: Optional[str] = Query(None, description="Filter by notification type"),
    priority: Optional[str] = Query(None, description="Filter by priority (high, medium, low)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum notifications to return"),
    offset: int = Query(0, ge=0, description="Number of notifications to skip")
):
    """Get user's notifications with optional filtering"""
    
    try:
        query = db.query(Notification).filter(Notification.user_id == current_user.id)
        
        # Apply filters
        if unread_only:
            query = query.filter(Notification.is_read.is_(False))
        
        if notification_type:
            query = query.filter(Notification.notification_type == notification_type)
        
        if priority:
            query = query.filter(Notification.priority == priority)
        
        # Order by creation date (newest first)
        query = query.order_by(desc(Notification.created_at))
        
        # Apply pagination
        notifications = query.offset(offset).limit(limit).all()
        
        logger.info(f"Retrieved {len(notifications)} notifications for user {current_user.id}")
        return notifications
        
    except Exception as e:
        logger.error(f"Error retrieving notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notifications")

@router.get("/summary", response_model=NotificationSummary)
async def get_notifications_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get summary of user's notifications"""
    
    try:
        # Get all notifications count
        total_count = db.query(Notification).filter(
            Notification.user_id == current_user.id
        ).count()
        
        # Get unread count
        unread_count = db.query(Notification).filter(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read.is_(False)
            )
        ).count()
        
        # Get high priority unread count
        high_priority_count = db.query(Notification).filter(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read.is_(False),
                Notification.priority == "high"
            )
        ).count()
        
        # Get recent notifications (last 5)
        recent_notifications = db.query(Notification).filter(
            Notification.user_id == current_user.id
        ).order_by(desc(Notification.created_at)).limit(5).all()
        
        return NotificationSummary(
            total_notifications=total_count,
            unread_count=unread_count,
            high_priority_count=high_priority_count,
            recent_notifications=recent_notifications
        )
        
    except Exception as e:
        logger.error(f"Error getting notifications summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notifications summary")

@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""
    
    try:
        notification = db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id
            )
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Marked notification {notification_id} as read for user {current_user.id}")
        
        return {"message": "Notification marked as read"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")

@router.put("/{notification_id}/dismiss")
async def dismiss_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Dismiss a notification"""
    
    try:
        notification = db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id
            )
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        notification.is_dismissed = True
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Dismissed notification {notification_id} for user {current_user.id}")
        return {"message": "Notification dismissed"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dismissing notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to dismiss notification")

@router.put("/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark all user notifications as read"""
    
    try:
        updated_count = db.query(Notification).filter(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read.is_(False)
            )
        ).update({
            "is_read": True,
            "read_at": datetime.utcnow()
        })
        
        db.commit()
        
        logger.info(f"Marked {updated_count} notifications as read for user {current_user.id}")
        return {"message": f"Marked {updated_count} notifications as read"}
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark all notifications as read")

@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a notification"""
    
    try:
        notification = db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id
            )
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        db.delete(notification)
        db.commit()
        
        logger.info(f"Deleted notification {notification_id} for user {current_user.id}")
        return {"message": "Notification deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete notification")

@router.post("/check-goals")
async def check_user_goals_for_notifications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Manually trigger goal notification check for the current user"""
    
    try:
        # Check for at-risk, stagnant, and overdue goals
        notifications = await notification_service.check_all_user_goals(db, current_user.id)
        
        # Save notifications to database
        saved_count = 0
        for notification_msg in notifications:
            # Check if similar notification already exists (avoid spam)
            existing = db.query(Notification).filter(
                and_(
                    Notification.user_id == current_user.id,
                    Notification.goal_id == notification_msg.goal_id,
                    Notification.notification_type == notification_msg.notification_type.value,
                    Notification.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)  # Today
                )
            ).first()
            
            if not existing:
                db_notification = Notification(
                    id=notification_msg.id,
                    user_id=notification_msg.user_id,
                    goal_id=notification_msg.goal_id,
                    title=notification_msg.title,
                    message=notification_msg.message,
                    notification_type=notification_msg.notification_type.value,
                    priority=notification_msg.priority,
                    action_url=notification_msg.action_url,
                    metadata=notification_msg.metadata,
                    created_at=notification_msg.created_at
                )
                db.add(db_notification)
                saved_count += 1
        
        db.commit()
        
        logger.info(f"Goal check generated {len(notifications)} notifications, saved {saved_count} new ones for user {current_user.id}")
        
        return {
            "message": f"Goal check complete. Generated {saved_count} new notifications.",
            "total_generated": len(notifications),
            "new_notifications": saved_count
        }
        
    except Exception as e:
        logger.error(f"Error checking goals for notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to check goals for notifications")

@router.get("/types")
async def get_notification_types():
    """Get available notification types and priorities"""
    
    return {
        "notification_types": [
            # Goal tracking notifications
            {"type": "milestone_25", "description": "25% progress milestone", "category": "goals"},
            {"type": "milestone_50", "description": "50% progress milestone", "category": "goals"},
            {"type": "milestone_75", "description": "75% progress milestone", "category": "goals"},
            {"type": "milestone_90", "description": "90% progress milestone", "category": "goals"},
            {"type": "goal_completed", "description": "Goal completed", "category": "goals"},
            {"type": "goal_overdue", "description": "Goal is overdue", "category": "goals"},
            {"type": "goal_at_risk", "description": "Goal at risk of not being completed", "category": "goals"},
            {"type": "progress_stagnant", "description": "No recent progress on goal", "category": "goals"},
            {"type": "exceptional_progress", "description": "Exceptional progress made", "category": "goals"},
            
            # Social media notifications
            {"type": "post_published", "description": "Post successfully published", "category": "social"},
            {"type": "post_failed", "description": "Post failed to publish", "category": "social"},
            {"type": "engagement_milestone", "description": "Engagement milestone reached", "category": "social"},
            {"type": "platform_connected", "description": "Social platform connected", "category": "social"},
            {"type": "platform_disconnected", "description": "Social platform disconnected", "category": "social"},
            {"type": "oauth_expired", "description": "OAuth token expired", "category": "social"},
            
            # System notifications
            {"type": "system_maintenance", "description": "System maintenance notification", "category": "system"},
            {"type": "system_error", "description": "System error occurred", "category": "system"},
            {"type": "feature_announcement", "description": "New feature announcement", "category": "system"},
            {"type": "security_alert", "description": "Security alert", "category": "system"},
            
            # Content notifications
            {"type": "content_generated", "description": "Content generated successfully", "category": "content"},
            {"type": "content_scheduled", "description": "Content scheduled for posting", "category": "content"},
            {"type": "workflow_completed", "description": "Workflow completed", "category": "content"},
            {"type": "workflow_failed", "description": "Workflow failed", "category": "content"}
        ],
        "priorities": [
            {"priority": "urgent", "description": "Requires immediate attention"},
            {"priority": "high", "description": "High priority"},
            {"priority": "medium", "description": "Medium priority"},
            {"priority": "low", "description": "Low priority"}
        ],
        "categories": ["goals", "social", "system", "content"]
    }