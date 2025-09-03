"""
Goals API endpoints with real database operations
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime, date
import uuid
import logging

from backend.db.database import get_db
from backend.db.models import Goal, GoalProgress, User, Notification, Milestone
from backend.auth.dependencies import get_current_active_user
from backend.services.notification_service import notification_service
from backend.services.goals_progress_service import GoalsProgressService
from backend.tasks.goals_tasks import sync_platform_metrics, update_all_goals_progress
from backend.core.api_version import create_versioned_router

router = create_versioned_router(prefix="/goals", tags=["goals"])
logger = logging.getLogger(__name__)

# Pydantic models
class CreateGoalRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    goal_type: str = Field(..., pattern="^(follower_growth|engagement_rate|reach_increase|content_volume|custom)$")
    target_value: float = Field(..., gt=0)
    target_date: date
    platform: Optional[str] = Field(None, pattern="^(twitter|linkedin|instagram|facebook|tiktok|all)$")
    
    @field_validator('target_date')
    @classmethod
    def target_date_must_be_future(cls, v):
        if v <= date.today():
            raise ValueError('Target date must be in the future')
        return v

class UpdateGoalRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    target_value: Optional[float] = Field(None, gt=0)
    target_date: Optional[date] = None
    platform: Optional[str] = Field(None, pattern="^(twitter|linkedin|instagram|facebook|tiktok|all)$")
    
    @field_validator('target_date')
    @classmethod
    def target_date_must_be_future(cls, v):
        if v and v <= date.today():
            raise ValueError('Target date must be in the future')
        return v

class UpdateProgressRequest(BaseModel):
    current_value: float = Field(..., ge=0)
    notes: Optional[str] = Field(None, max_length=500)

class GoalResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    goal_type: str
    target_value: float
    current_value: float
    target_date: date
    status: str
    platform: Optional[str]
    progress_percentage: float
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class GoalProgressResponse(BaseModel):
    id: int
    old_value: float
    new_value: float
    change_amount: float
    recorded_at: datetime
    source: Optional[str]
    notes: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)

class CreateMilestoneRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    target_value: float = Field(..., gt=0)
    target_date: Optional[date] = None

class MilestoneResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    target_value: float
    target_date: Optional[date]
    achieved: bool
    achieved_at: Optional[datetime]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

@router.post("/", response_model=GoalResponse)
async def create_goal(
    request: CreateGoalRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new goal"""
    
    # Create new goal
    goal = Goal(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        title=request.title,
        description=request.description,
        goal_type=request.goal_type,
        target_value=request.target_value,
        current_value=0.0,
        target_date=datetime.combine(request.target_date, datetime.min.time()),
        status="active",
        platform=request.platform,
        metadata={}
    )
    
    db.add(goal)
    db.commit()
    db.refresh(goal)
    
    # Calculate progress percentage
    goal.progress_percentage = (goal.current_value / goal.target_value) * 100
    
    return goal

@router.get("/", response_model=List[GoalResponse])
async def get_user_goals(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, pattern="^(active|paused|completed|failed)$"),
    goal_type: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    """Get user's goals with optional filtering"""
    
    query = db.query(Goal).filter(Goal.user_id == current_user.id)
    
    if status:
        query = query.filter(Goal.status == status)
    if goal_type:
        query = query.filter(Goal.goal_type == goal_type)
    if platform:
        query = query.filter(Goal.platform == platform)
    
    goals = query.order_by(Goal.created_at.desc()).limit(limit).all()
    
    # Calculate progress percentages
    for goal in goals:
        goal.progress_percentage = (goal.current_value / goal.target_value) * 100 if goal.target_value > 0 else 0
    
    return goals

@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific goal by ID"""
    
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Calculate progress percentage
    goal.progress_percentage = (goal.current_value / goal.target_value) * 100 if goal.target_value > 0 else 0
    
    return goal

@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    request: UpdateGoalRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update goal details"""
    
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    if goal.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot update completed goal")
    
    # Update fields
    update_data = request.dict(exclude_unset=True)
    if 'target_date' in update_data:
        update_data['target_date'] = datetime.combine(update_data['target_date'], datetime.min.time())
    
    for field, value in update_data.items():
        setattr(goal, field, value)
    
    goal.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(goal)
    
    # Calculate progress percentage
    goal.progress_percentage = (goal.current_value / goal.target_value) * 100 if goal.target_value > 0 else 0
    
    return goal

@router.put("/{goal_id}/progress", response_model=GoalResponse)
async def update_goal_progress(
    goal_id: str,
    request: UpdateProgressRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update goal progress"""
    
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    if goal.status in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Cannot update progress for completed/failed goal")
    
    # Create progress log
    old_value = goal.current_value
    new_value = request.current_value
    change_amount = new_value - old_value
    
    progress_log = GoalProgress(
        goal_id=goal.id,
        old_value=old_value,
        new_value=new_value,
        change_amount=change_amount,
        source="manual",
        notes=request.notes
    )
    
    # Update goal
    goal.current_value = new_value
    goal.updated_at = datetime.utcnow()
    
    # Check if goal is completed
    if new_value >= goal.target_value:
        goal.status = "completed"
        goal.completed_at = datetime.utcnow()
    
    db.add(progress_log)
    db.commit()
    db.refresh(goal)
    
    # Calculate progress percentage
    goal.progress_percentage = (goal.current_value / goal.target_value) * 100 if goal.target_value > 0 else 0
    
    # Generate milestone notifications
    try:
        notifications = await notification_service.process_goal_progress_update(
            db, goal, old_value, new_value
        )
        
        # Save notifications to database
        for notification_msg in notifications:
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
        
        db.commit()
        
        if notifications:
            logger.info(f"Generated {len(notifications)} milestone notifications for goal {goal.id}")
    
    except Exception as e:
        logger.error(f"Failed to generate milestone notifications: {e}")
        # Don't fail the progress update if notifications fail
        pass
    
    return goal

@router.put("/{goal_id}/pause")
async def pause_goal(
    goal_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Pause a goal"""
    
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    if goal.status != "active":
        raise HTTPException(status_code=400, detail="Can only pause active goals")
    
    goal.status = "paused"
    goal.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Goal paused successfully"}

@router.put("/{goal_id}/resume")
async def resume_goal(
    goal_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Resume a paused goal"""
    
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    if goal.status != "paused":
        raise HTTPException(status_code=400, detail="Can only resume paused goals")
    
    goal.status = "active"
    goal.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Goal resumed successfully"}

@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a goal and its progress logs"""
    
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Delete progress logs first
    db.query(GoalProgress).filter(GoalProgress.goal_id == goal_id).delete()
    
    # Delete goal
    db.delete(goal)
    db.commit()
    
    return {"message": "Goal deleted successfully"}

@router.get("/{goal_id}/progress", response_model=List[GoalProgressResponse])
async def get_goal_progress(
    goal_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100)
):
    """Get goal progress history"""
    
    # Verify goal exists and belongs to user
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    progress_logs = db.query(GoalProgress).filter(
        GoalProgress.goal_id == goal_id
    ).order_by(GoalProgress.recorded_at.desc()).limit(limit).all()
    
    return progress_logs

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get goals dashboard summary"""
    
    # Get all user goals
    goals = db.query(Goal).filter(Goal.user_id == current_user.id).all()
    
    # Calculate summary stats
    total_goals = len(goals)
    active_goals = len([g for g in goals if g.status == "active"])
    completed_goals = len([g for g in goals if g.status == "completed"])
    paused_goals = len([g for g in goals if g.status == "paused"])
    
    # Calculate average progress
    active_goal_progress = []
    for goal in goals:
        if goal.status == "active" and goal.target_value > 0:
            progress = (goal.current_value / goal.target_value) * 100
            active_goal_progress.append(min(progress, 100))
    
    avg_progress = sum(active_goal_progress) / len(active_goal_progress) if active_goal_progress else 0
    
    # Get goals by type
    goals_by_type = {}
    for goal in goals:
        if goal.goal_type not in goals_by_type:
            goals_by_type[goal.goal_type] = 0
        goals_by_type[goal.goal_type] += 1
    
    return {
        "total_goals": total_goals,
        "active_goals": active_goals,
        "completed_goals": completed_goals,
        "paused_goals": paused_goals,
        "average_progress": round(avg_progress, 1),
        "goals_by_type": goals_by_type,
        "recent_goals": [
            {
                "id": goal.id,
                "title": goal.title,
                "progress": min((goal.current_value / goal.target_value) * 100, 100) if goal.target_value > 0 else 0,
                "status": goal.status
            }
            for goal in sorted(goals, key=lambda x: x.created_at, reverse=True)[:5]
        ]
    }


@router.post("/sync/all")
async def sync_all_goals_progress(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Manually trigger progress sync for all user goals"""
    
    progress_service = GoalsProgressService()
    
    try:
        result = await progress_service.update_all_user_goals(db, current_user.id)
        
        logger.info(f"Manual sync completed for user {current_user.id}: {result}")
        
        return {
            "message": "Goals progress sync completed",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error syncing goals progress: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to sync goals progress")


@router.post("/sync/platform/{platform}")
async def sync_platform_goals_progress(
    platform: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Manually trigger progress sync for specific platform goals"""
    
    valid_platforms = ['twitter', 'linkedin', 'instagram', 'facebook', 'tiktok']
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}"
        )
    
    progress_service = GoalsProgressService()
    
    try:
        result = await progress_service.sync_platform_metrics(db, current_user.id, platform)
        
        logger.info(f"Platform sync completed for user {current_user.id}, platform {platform}: {result}")
        
        return {
            "message": f"Platform {platform} goals sync completed",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error syncing platform goals: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to sync {platform} goals progress")


@router.get("/analytics/progress-trends")
async def get_progress_trends(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze")
):
    """Get progress trends and analytics for all user goals"""
    
    from datetime import timedelta
    from sqlalchemy import func
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get progress history for time series
    progress_data = db.query(
        GoalProgress.recorded_at,
        GoalProgress.new_value,
        Goal.title,
        Goal.id,
        Goal.goal_type,
        Goal.target_value
    ).join(Goal).filter(
        Goal.user_id == current_user.id,
        GoalProgress.recorded_at >= start_date
    ).order_by(GoalProgress.recorded_at).all()
    
    # Get current goals status
    current_goals = db.query(Goal).filter(Goal.user_id == current_user.id).all()
    
    # Calculate trends
    goal_trends = {}
    for entry in progress_data:
        goal_id = entry.id
        if goal_id not in goal_trends:
            goal_trends[goal_id] = {
                "title": entry.title,
                "goal_type": entry.goal_type,
                "target_value": entry.target_value,
                "data_points": []
            }
        
        goal_trends[goal_id]["data_points"].append({
            "date": entry.recorded_at.isoformat(),
            "value": entry.new_value,
            "progress_percentage": (entry.new_value / entry.target_value * 100) if entry.target_value else 0
        })
    
    # Calculate velocity (progress per day) for active goals
    goal_velocities = {}
    for goal in current_goals:
        if goal.status == 'active' and goal.id in goal_trends:
            data_points = goal_trends[goal.id]["data_points"]
            if len(data_points) >= 2:
                # Calculate average daily progress
                first_point = data_points[0]
                last_point = data_points[-1]
                
                days_elapsed = (datetime.fromisoformat(last_point["date"].replace('Z', '+00:00')) - 
                              datetime.fromisoformat(first_point["date"].replace('Z', '+00:00'))).days
                
                if days_elapsed > 0:
                    progress_change = last_point["value"] - first_point["value"]
                    velocity = progress_change / days_elapsed
                    goal_velocities[goal.id] = velocity
    
    return {
        "period_days": days,
        "total_goals_tracked": len(goal_trends),
        "goal_trends": goal_trends,
        "goal_velocities": goal_velocities,
        "summary": {
            "active_goals": len([g for g in current_goals if g.status == 'active']),
            "completed_goals": len([g for g in current_goals if g.status == 'completed']),
            "at_risk_goals": len([g for g in current_goals if g.status == 'at_risk']),
            "average_velocity": sum(goal_velocities.values()) / len(goal_velocities) if goal_velocities else 0
        }
    }


@router.get("/analytics/performance")
async def get_goals_performance_analytics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed performance analytics for goals"""
    
    goals = db.query(Goal).filter(Goal.user_id == current_user.id).all()
    
    # Performance metrics
    total_goals = len(goals)
    completed_goals = [g for g in goals if g.status == 'completed']
    active_goals = [g for g in goals if g.status == 'active']
    at_risk_goals = [g for g in goals if g.status == 'at_risk']
    
    # Success rate
    success_rate = (len(completed_goals) / total_goals * 100) if total_goals > 0 else 0
    
    # Average time to completion
    completion_times = []
    for goal in completed_goals:
        if goal.completed_at and goal.created_at:
            completion_time = (goal.completed_at - goal.created_at).days
            completion_times.append(completion_time)
    
    avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
    
    # Goal type performance
    type_performance = {}
    for goal in goals:
        goal_type = goal.goal_type
        if goal_type not in type_performance:
            type_performance[goal_type] = {
                "total": 0,
                "completed": 0,
                "active": 0,
                "at_risk": 0,
                "success_rate": 0
            }
        
        type_performance[goal_type]["total"] += 1
        
        if goal.status == 'completed':
            type_performance[goal_type]["completed"] += 1
        elif goal.status == 'active':
            type_performance[goal_type]["active"] += 1
        elif goal.status == 'at_risk':
            type_performance[goal_type]["at_risk"] += 1
    
    # Calculate success rates for each type
    for goal_type in type_performance:
        total = type_performance[goal_type]["total"]
        completed = type_performance[goal_type]["completed"]
        type_performance[goal_type]["success_rate"] = (completed / total * 100) if total > 0 else 0
    
    return {
        "overview": {
            "total_goals": total_goals,
            "success_rate": round(success_rate, 1),
            "average_completion_time_days": round(avg_completion_time, 1),
            "goals_by_status": {
                "completed": len(completed_goals),
                "active": len(active_goals),
                "at_risk": len(at_risk_goals),
                "paused": len([g for g in goals if g.status == 'paused'])
            }
        },
        "type_performance": type_performance,
        "recommendations": [
            "Focus on goal types with highest success rates" if type_performance else "Create your first goal to get started",
            f"Review at-risk goals ({len(at_risk_goals)} goals need attention)" if at_risk_goals else "Great! No goals at risk",
            f"Average completion time is {avg_completion_time:.1f} days" if avg_completion_time > 0 else "Set realistic deadlines for better tracking"
        ]
    }


# Milestone Management Endpoints

@router.post("/{goal_id}/milestones", response_model=MilestoneResponse)
async def create_milestone(
    goal_id: str,
    request: CreateMilestoneRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a milestone for a goal"""
    
    # Verify goal exists and belongs to user
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Validate that milestone target is less than or equal to goal target
    if request.target_value > goal.target_value:
        raise HTTPException(
            status_code=400, 
            detail="Milestone target cannot exceed goal target value"
        )
    
    # Create milestone
    milestone = Milestone(
        goal_id=goal_id,
        title=request.title,
        description=request.description,
        target_value=request.target_value,
        target_date=datetime.combine(request.target_date, datetime.min.time()) if request.target_date else None
    )
    
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    
    return milestone


@router.get("/{goal_id}/milestones", response_model=List[MilestoneResponse])
async def get_goal_milestones(
    goal_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all milestones for a goal"""
    
    # Verify goal exists and belongs to user
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    milestones = db.query(Milestone).filter(
        Milestone.goal_id == goal_id
    ).order_by(Milestone.target_value).all()
    
    return milestones


@router.put("/{goal_id}/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    goal_id: str,
    milestone_id: int,
    request: CreateMilestoneRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a milestone"""
    
    # Verify goal exists and belongs to user
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Get milestone
    milestone = db.query(Milestone).filter(
        Milestone.id == milestone_id,
        Milestone.goal_id == goal_id
    ).first()
    
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    # Validate target value
    if request.target_value > goal.target_value:
        raise HTTPException(
            status_code=400, 
            detail="Milestone target cannot exceed goal target value"
        )
    
    # Update milestone
    milestone.title = request.title
    milestone.description = request.description
    milestone.target_value = request.target_value
    if request.target_date:
        milestone.target_date = datetime.combine(request.target_date, datetime.min.time())
    
    db.commit()
    db.refresh(milestone)
    
    return milestone


@router.put("/{goal_id}/milestones/{milestone_id}/achieve")
async def achieve_milestone(
    goal_id: str,
    milestone_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark a milestone as achieved"""
    
    # Verify goal exists and belongs to user
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Get milestone
    milestone = db.query(Milestone).filter(
        Milestone.id == milestone_id,
        Milestone.goal_id == goal_id
    ).first()
    
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    # Check if milestone can be achieved (current progress meets target)
    if goal.current_value < milestone.target_value:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot achieve milestone. Current progress ({goal.current_value}) is below milestone target ({milestone.target_value})"
        )
    
    # Mark as achieved
    milestone.achieved = True
    milestone.achieved_at = datetime.utcnow()
    
    db.commit()
    
    # Create achievement notification
    try:
        achievement_notification = notification_service.create_notification(
            db=db,
            user_id=current_user.id,
            notification_type='milestone_achieved',
            title=f"🎉 Milestone Achieved: {milestone.title}",
            message=f"Congratulations! You've achieved the milestone '{milestone.title}' for your goal '{goal.title}'.",
            metadata={
                "goal_id": goal.id,
                "milestone_id": milestone.id,
                "milestone_value": milestone.target_value,
                "current_progress": goal.current_value
            }
        )
        
        if achievement_notification:
            db_notification = Notification(
                id=achievement_notification.id,
                user_id=achievement_notification.user_id,
                goal_id=goal.id,
                title=achievement_notification.title,
                message=achievement_notification.message,
                notification_type=achievement_notification.notification_type.value,
                priority=achievement_notification.priority,
                action_url=achievement_notification.action_url,
                metadata=achievement_notification.metadata,
                created_at=achievement_notification.created_at
            )
            db.add(db_notification)
            db.commit()
    
    except Exception as e:
        logger.error(f"Failed to create milestone achievement notification: {e}")
    
    return {"message": "Milestone achieved successfully", "milestone": milestone}


@router.delete("/{goal_id}/milestones/{milestone_id}")
async def delete_milestone(
    goal_id: str,
    milestone_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a milestone"""
    
    # Verify goal exists and belongs to user
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Get milestone
    milestone = db.query(Milestone).filter(
        Milestone.id == milestone_id,
        Milestone.goal_id == goal_id
    ).first()
    
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    db.delete(milestone)
    db.commit()
    
    return {"message": "Milestone deleted successfully"}


# Dashboard Widget Endpoints

@router.get("/dashboard/widgets/upcoming-deadlines")
async def get_upcoming_deadlines(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    days_ahead: int = Query(7, ge=1, le=30, description="Number of days to look ahead")
):
    """Get goals and milestones with upcoming deadlines"""
    
    from datetime import timedelta
    
    deadline_date = datetime.utcnow() + timedelta(days=days_ahead)
    
    # Get goals with upcoming deadlines
    upcoming_goals = db.query(Goal).filter(
        Goal.user_id == current_user.id,
        Goal.status == 'active',
        Goal.target_date <= deadline_date,
        Goal.target_date > datetime.utcnow()
    ).order_by(Goal.target_date).all()
    
    # Get milestones with upcoming deadlines
    upcoming_milestones = db.query(Milestone).join(Goal).filter(
        Goal.user_id == current_user.id,
        Goal.status == 'active',
        Milestone.target_date.isnot(None),
        Milestone.target_date <= deadline_date,
        Milestone.target_date > datetime.utcnow(),
        Milestone.achieved == False
    ).order_by(Milestone.target_date).all()
    
    return {
        "upcoming_goals": [
            {
                "id": goal.id,
                "title": goal.title,
                "target_date": goal.target_date.isoformat(),
                "days_remaining": (goal.target_date - datetime.utcnow()).days,
                "progress_percentage": (goal.current_value / goal.target_value * 100) if goal.target_value else 0,
                "is_at_risk": goal.status == 'at_risk'
            }
            for goal in upcoming_goals
        ],
        "upcoming_milestones": [
            {
                "id": milestone.id,
                "goal_id": milestone.goal_id,
                "title": milestone.title,
                "goal_title": milestone.goal.title,
                "target_date": milestone.target_date.isoformat(),
                "days_remaining": (milestone.target_date - datetime.utcnow()).days,
                "target_value": milestone.target_value,
                "current_progress": milestone.goal.current_value
            }
            for milestone in upcoming_milestones
        ]
    }


@router.get("/dashboard/widgets/recent-achievements")
async def get_recent_achievements(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    days_back: int = Query(30, ge=1, le=90, description="Number of days to look back")
):
    """Get recently completed goals and achieved milestones"""
    
    from datetime import timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    
    # Get recently completed goals
    completed_goals = db.query(Goal).filter(
        Goal.user_id == current_user.id,
        Goal.status == 'completed',
        Goal.completed_at >= cutoff_date
    ).order_by(Goal.completed_at.desc()).all()
    
    # Get recently achieved milestones
    achieved_milestones = db.query(Milestone).join(Goal).filter(
        Goal.user_id == current_user.id,
        Milestone.achieved == True,
        Milestone.achieved_at >= cutoff_date
    ).order_by(Milestone.achieved_at.desc()).all()
    
    return {
        "completed_goals": [
            {
                "id": goal.id,
                "title": goal.title,
                "goal_type": goal.goal_type,
                "target_value": goal.target_value,
                "completed_at": goal.completed_at.isoformat(),
                "days_to_complete": (goal.completed_at - goal.created_at).days,
                "platform": goal.platform
            }
            for goal in completed_goals
        ],
        "achieved_milestones": [
            {
                "id": milestone.id,
                "title": milestone.title,
                "goal_title": milestone.goal.title,
                "target_value": milestone.target_value,
                "achieved_at": milestone.achieved_at.isoformat(),
                "goal_id": milestone.goal_id
            }
            for milestone in achieved_milestones
        ]
    }


@router.get("/dashboard/widgets/progress-alerts")
async def get_progress_alerts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get goals that need attention (at risk, stagnant, etc.)"""
    
    from datetime import timedelta
    
    # Get at-risk goals
    at_risk_goals = db.query(Goal).filter(
        Goal.user_id == current_user.id,
        Goal.status == 'at_risk'
    ).all()
    
    # Get stagnant goals (no progress in last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    stagnant_goals = db.query(Goal).filter(
        Goal.user_id == current_user.id,
        Goal.status == 'active',
        Goal.updated_at <= seven_days_ago
    ).all()
    
    # Get overdue goals
    overdue_goals = db.query(Goal).filter(
        Goal.user_id == current_user.id,
        Goal.status == 'active',
        Goal.target_date < datetime.utcnow()
    ).all()
    
    return {
        "at_risk_goals": [
            {
                "id": goal.id,
                "title": goal.title,
                "progress_percentage": (goal.current_value / goal.target_value * 100) if goal.target_value else 0,
                "target_date": goal.target_date.isoformat(),
                "days_remaining": (goal.target_date - datetime.utcnow()).days
            }
            for goal in at_risk_goals
        ],
        "stagnant_goals": [
            {
                "id": goal.id,
                "title": goal.title,
                "days_without_progress": (datetime.utcnow() - goal.updated_at).days,
                "progress_percentage": (goal.current_value / goal.target_value * 100) if goal.target_value else 0
            }
            for goal in stagnant_goals
        ],
        "overdue_goals": [
            {
                "id": goal.id,
                "title": goal.title,
                "days_overdue": (datetime.utcnow() - goal.target_date).days,
                "progress_percentage": (goal.current_value / goal.target_value * 100) if goal.target_value else 0
            }
            for goal in overdue_goals
        ]
    }