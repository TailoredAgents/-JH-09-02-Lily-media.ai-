"""
Workflow execution API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid

from backend.db.database import get_db
from backend.db.models import WorkflowExecution, User
from backend.auth.dependencies import get_current_active_user
from backend.middleware.feature_flag_enforcement import require_flag

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

# Pydantic models
class ExecuteWorkflowRequest(BaseModel):
    workflow_type: str = Field(..., pattern="^(daily|optimization|manual|research|content_generation)$")
    execution_params: Optional[Dict[str, Any]] = Field(default_factory=dict)

class WorkflowExecutionResponse(BaseModel):
    id: str
    workflow_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    current_stage: Optional[str]
    completed_stages: List[str]
    failed_stages: List[str]
    content_generated: int
    posts_scheduled: int
    research_items: int
    error_message: Optional[str]
    execution_params: Dict[str, Any]
    results_summary: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)

@router.post("/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    request: ExecuteWorkflowRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_flag("WORKFLOW_V2"))
):
    """Execute a workflow in the background"""
    
    # Create workflow execution record
    execution = WorkflowExecution(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        workflow_type=request.workflow_type,
        status="running",
        current_stage="initializing",
        completed_stages=[],
        failed_stages=[],
        content_generated=0,
        posts_scheduled=0,
        research_items=0,
        execution_params=request.execution_params or {},
        results_summary={}
    )
    
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    # Add to background tasks - don't pass db session to background task
    background_tasks.add_task(run_workflow, execution.id, request.workflow_type)
    
    return execution

@router.get("/", response_model=List[WorkflowExecutionResponse])
async def get_workflow_executions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    workflow_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """Get workflow execution history"""
    
    query = db.query(WorkflowExecution).filter(WorkflowExecution.user_id == current_user.id)
    
    if workflow_type:
        query = query.filter(WorkflowExecution.workflow_type == workflow_type)
    if status:
        query = query.filter(WorkflowExecution.status == status)
    
    executions = query.order_by(WorkflowExecution.started_at.desc()).limit(limit).all()
    
    return executions

@router.get("/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_workflow_execution(
    execution_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific workflow execution"""
    
    execution = db.query(WorkflowExecution).filter(
        WorkflowExecution.id == execution_id,
        WorkflowExecution.user_id == current_user.id
    ).first()
    
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    
    return execution

@router.post("/{execution_id}/cancel")
async def cancel_workflow_execution(
    execution_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel a running workflow execution"""
    
    execution = db.query(WorkflowExecution).filter(
        WorkflowExecution.id == execution_id,
        WorkflowExecution.user_id == current_user.id
    ).first()
    
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    
    if execution.status not in ["running", "pending"]:
        raise HTTPException(status_code=400, detail="Can only cancel running or pending workflows")
    
    execution.status = "cancelled"
    execution.completed_at = datetime.utcnow()
    
    if execution.started_at:
        duration = (execution.completed_at - execution.started_at).total_seconds()
        execution.duration_seconds = int(duration)
    
    db.commit()
    
    return {"message": "Workflow execution cancelled successfully"}

@router.get("/status/summary")
async def get_workflow_status_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get workflow execution status summary"""
    
    # Get recent executions (last 30 days)
    from datetime import timedelta
    start_date = datetime.utcnow() - timedelta(days=30)
    
    executions = db.query(WorkflowExecution).filter(
        WorkflowExecution.user_id == current_user.id,
        WorkflowExecution.started_at >= start_date
    ).all()
    
    # Calculate statistics
    total_executions = len(executions)
    
    status_counts = {}
    type_counts = {}
    total_content_generated = 0
    total_posts_scheduled = 0
    total_research_items = 0
    
    for execution in executions:
        # Status counts
        status = execution.status
        status_counts[status] = status_counts.get(status, 0) + 1
        
        # Type counts
        workflow_type = execution.workflow_type
        type_counts[workflow_type] = type_counts.get(workflow_type, 0) + 1
        
        # Aggregate results
        total_content_generated += execution.content_generated or 0
        total_posts_scheduled += execution.posts_scheduled or 0
        total_research_items += execution.research_items or 0
    
    # Get currently running executions
    running_executions = db.query(WorkflowExecution).filter(
        WorkflowExecution.user_id == current_user.id,
        WorkflowExecution.status == "running"
    ).all()
    
    # Get recent completed executions
    recent_completed = db.query(WorkflowExecution).filter(
        WorkflowExecution.user_id == current_user.id,
        WorkflowExecution.status == "completed"
    ).order_by(WorkflowExecution.completed_at.desc()).limit(5).all()
    
    return {
        "total_executions": total_executions,
        "status_counts": status_counts,
        "type_counts": type_counts,
        "currently_running": len(running_executions),
        "total_results": {
            "content_generated": total_content_generated,
            "posts_scheduled": total_posts_scheduled,
            "research_items": total_research_items
        },
        "running_workflows": [
            {
                "id": exec.id,
                "workflow_type": exec.workflow_type,
                "current_stage": exec.current_stage,
                "started_at": exec.started_at,
                "duration_minutes": int((datetime.utcnow() - exec.started_at).total_seconds() / 60)
            }
            for exec in running_executions
        ],
        "recent_completed": [
            {
                "id": exec.id,
                "workflow_type": exec.workflow_type,
                "completed_at": exec.completed_at,
                "duration_minutes": int(exec.duration_seconds / 60) if exec.duration_seconds else 0,
                "content_generated": exec.content_generated,
                "posts_scheduled": exec.posts_scheduled
            }
            for exec in recent_completed
        ]
    }

@router.post("/templates/daily")
async def create_daily_workflow_template(
    current_user: User = Depends(get_current_active_user)
):
    """Get daily workflow template parameters"""
    
    # This would typically be customized based on user settings
    template = {
        "workflow_type": "daily",
        "execution_params": {
            "research_topics": ["industry trends", "competitor analysis"],
            "content_count": 3,
            "platforms": ["twitter", "linkedin"],
            "tone": "professional",
            "include_images": True,
            "schedule_posts": True,
            "optimization_enabled": True
        },
        "estimated_duration_minutes": 15,
        "stages": [
            "research_trends",
            "generate_content",
            "optimize_content",
            "schedule_posts",
            "update_memory"
        ]
    }
    
    return template

@router.post("/templates/optimization")
async def create_optimization_workflow_template(
    current_user: User = Depends(get_current_active_user)
):
    """Get optimization workflow template parameters"""
    
    template = {
        "workflow_type": "optimization",
        "execution_params": {
            "analyze_period_days": 7,
            "min_engagement_threshold": 10,
            "optimization_focus": ["engagement", "reach", "timing"],
            "generate_recommendations": True,
            "update_strategy": True
        },
        "estimated_duration_minutes": 10,
        "stages": [
            "collect_metrics",
            "analyze_performance",
            "identify_patterns",
            "generate_recommendations",
            "update_memory"
        ]
    }
    
    return template

# Background task function
async def run_workflow(execution_id: str, workflow_type: str):
    """Background task to run workflow execution"""
    
    # Create new database session for background task
    from backend.db.database import get_db
    db = next(get_db())
    
    try:
        # Get execution record
        execution = db.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()
        
        if not execution:
            return
        
        # Simulate workflow execution stages
        stages = get_workflow_stages(workflow_type)
        
        for stage in stages:
            # Update current stage
            execution.current_stage = stage
            execution.completed_stages = execution.completed_stages + [stage]
            db.commit()
            
            # Simulate stage processing time
            import time
            await asyncio.sleep(2)  # Non-blocking sleep in async function
            
            # Simulate stage results
            if stage == "generate_content":
                execution.content_generated += 2
            elif stage == "schedule_posts":
                execution.posts_scheduled += 2
            elif stage == "research_trends":
                execution.research_items += 5
        
        # Mark as completed
        execution.status = "completed"
        execution.completed_at = datetime.utcnow()
        execution.current_stage = None
        
        if execution.started_at:
            duration = (execution.completed_at - execution.started_at).total_seconds()
            execution.duration_seconds = int(duration)
        
        execution.results_summary = {
            "success": True,
            "stages_completed": len(stages),
            "total_content_generated": execution.content_generated,
            "total_posts_scheduled": execution.posts_scheduled,
            "total_research_items": execution.research_items
        }
        
        db.commit()
        
    except Exception as e:
        # Mark as failed on error
        try:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            
            if execution.started_at:
                duration = (execution.completed_at - execution.started_at).total_seconds()
                execution.duration_seconds = int(duration)
            
            db.commit()
        except Exception as commit_error:
            logger.error(f"Failed to commit error state for workflow {execution_id}: {commit_error}")
            db.rollback()
    finally:
        # Always close the database session
        db.close()

def get_workflow_stages(workflow_type: str) -> List[str]:
    """Get stages for different workflow types"""
    
    stage_mapping = {
        "daily": ["research_trends", "generate_content", "optimize_content", "schedule_posts", "update_memory"],
        "optimization": ["collect_metrics", "analyze_performance", "identify_patterns", "generate_recommendations", "update_memory"],
        "research": ["gather_sources", "analyze_trends", "extract_insights", "categorize_content", "store_results"],
        "content_generation": ["analyze_context", "generate_ideas", "create_content", "optimize_content", "save_drafts"],
        "manual": ["custom_processing"]
    }
    
    return stage_mapping.get(workflow_type, ["processing"])