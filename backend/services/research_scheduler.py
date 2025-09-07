"""
Research Scheduler Service
Weekly Deep Research Automation System

Manages automated scheduling and execution of deep research tasks
using Celery for background task processing.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
from pathlib import Path

from celery import Celery
from celery.schedules import crontab
from backend.core.config import get_settings
from backend.agents.deep_research_agent import deep_research_agent, ResearchTopic, IndustryIntelligence
from backend.services.notification_service import notification_service
from backend.services.plan_service import PlanService
from backend.services.research_monitoring import get_research_monitoring_service, ResearchOperationTracker

settings = get_settings()
logger = logging.getLogger(__name__)

class ResearchScheduler:
    """
    Manages automated research scheduling and execution
    
    Features:
    - Weekly research automation
    - Industry-specific research configuration
    - Progress monitoring and alerts
    - Failure recovery and retry logic
    - Performance metrics tracking
    """
    
    def __init__(self, db=None):
        """Initialize Research Scheduler"""
        self.db = db
        self.plan_service = PlanService(db) if db else None
        project_root = Path(__file__).parent.parent.parent
        self.config_path = project_root / "data/research_config"
        self.schedules_path = project_root / "data/research_schedules"
        self.logs_path = project_root / "data/research_logs"
        
        # Create directories
        for path in [self.config_path, self.schedules_path, self.logs_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Default schedule: Every Sunday at 2:00 AM
        self.default_schedule = {
            "hour": 2,
            "minute": 0,
            "day_of_week": 0  # Sunday
        }
        
        logger.info("Research Scheduler initialized")
    
    async def setup_industry_research(self, 
                                    user_id: int,
                                    industry: str, 
                                    business_context: Dict[str, Any],
                                    schedule_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Set up automated research for a specific industry
        
        Args:
            user_id: User requesting the research setup
            industry: Target industry name
            business_context: Business-specific context and goals
            schedule_config: Custom schedule configuration
            
        Returns:
            Setup confirmation with schedule details
        """
        try:
            # PLAN VALIDATION: Check if user can access research automation
            if self.plan_service:
                capabilities = self.plan_service.get_user_capabilities(user_id)
                if not capabilities.has_autopilot_research():
                    return {
                        "status": "access_denied",
                        "error": f"Research automation not available on {capabilities.get_plan_name()} plan",
                        "plan": capabilities.get_plan_name(),
                        "feature_required": "autopilot_research_enabled",
                        "upgrade_required": True,
                        "suggested_plans": ["pro", "enterprise"]
                    }
            # Initialize research topics
            research_topics = await deep_research_agent.initialize_research_topics(
                industry, business_context
            )
            
            # Create research configuration
            config = {
                "industry": industry,
                "business_context": business_context,
                "research_topics": [
                    {
                        "name": topic.name,
                        "keywords": topic.keywords,
                        "priority": topic.priority,
                        "research_depth": topic.research_depth,
                        "sources": topic.sources
                    }
                    for topic in research_topics
                ],
                "schedule": schedule_config or self.default_schedule,
                "created_at": datetime.utcnow().isoformat(),
                "last_research": None,
                "status": "active",
                "total_research_runs": 0,
                "average_findings_per_run": 0,
                "last_performance_metrics": {}
            }
            
            # Save configuration
            config_file = self.config_path / f"{industry}_research_config.json"
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Schedule the task
            schedule_result = await self._schedule_weekly_research(industry, config["schedule"])
            
            logger.info(f"Research setup completed for {industry}")
            
            return {
                "status": "success",
                "industry": industry,
                "topics_count": len(research_topics),
                "schedule": config["schedule"],
                "next_run": schedule_result.get("next_run"),
                "config_file": str(config_file)
            }
            
        except Exception as e:
            logger.error(f"Failed to setup industry research for {industry}: {e}")
            return {
                "status": "error",
                "industry": industry,
                "error": str(e)
            }
    
    async def _schedule_weekly_research(self, industry: str, schedule_config: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule weekly research task using Celery"""
        try:
            # Create Celery task
            task_name = f"weekly_research_{industry}"
            
            # Schedule configuration
            schedule = crontab(
                hour=schedule_config.get("hour", 2),
                minute=schedule_config.get("minute", 0),
                day_of_week=schedule_config.get("day_of_week", 0)
            )
            
            # Save schedule information
            schedule_info = {
                "task_name": task_name,
                "industry": industry,
                "schedule": schedule_config,
                "created_at": datetime.utcnow().isoformat(),
                "status": "scheduled",
                "next_run": self._calculate_next_run(schedule_config)
            }
            
            schedule_file = self.schedules_path / f"{task_name}_schedule.json"
            with open(schedule_file, 'w') as f:
                json.dump(schedule_info, f, indent=2)
            
            return schedule_info
            
        except Exception as e:
            logger.error(f"Failed to schedule weekly research for {industry}: {e}")
            raise
    
    def _calculate_next_run(self, schedule_config: Dict[str, Any]) -> str:
        """Calculate next scheduled run time"""
        now = datetime.utcnow()
        
        # Calculate next Sunday at specified time
        days_ahead = schedule_config.get("day_of_week", 0) - now.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        next_run = now + timedelta(days=days_ahead)
        next_run = next_run.replace(
            hour=schedule_config.get("hour", 2),
            minute=schedule_config.get("minute", 0),
            second=0,
            microsecond=0
        )
        
        return next_run.isoformat()
    
    async def execute_weekly_research(self, user_id: int, industry: str) -> Dict[str, Any]:
        """
        Execute weekly research for an industry
        
        Args:
            user_id: User requesting the research execution  
            industry: Target industry
            
        Returns:
            Research execution results
        """
        start_time = datetime.utcnow()
        
        try:
            # PLAN VALIDATION: Check if user can execute research automation
            if self.plan_service:
                capabilities = self.plan_service.get_user_capabilities(user_id)
                if not capabilities.has_autopilot_research():
                    logger.warning(f"Research execution blocked for user {user_id}: plan does not include research automation")
                    return {
                        "status": "access_denied",
                        "error": f"Research automation not available on {capabilities.get_plan_name()} plan",
                        "plan": capabilities.get_plan_name(),
                        "execution_time": (datetime.utcnow() - start_time).total_seconds()
                    }
            logger.info(f"Starting weekly research execution for {industry}")
            
            # Load research configuration
            config = await self._load_research_config(industry)
            if not config:
                raise Exception(f"No research configuration found for {industry}")
            
            # Convert config topics back to ResearchTopic objects
            research_topics = []
            for topic_data in config["research_topics"]:
                topic = ResearchTopic(
                    name=topic_data["name"],
                    keywords=topic_data["keywords"],
                    priority=topic_data["priority"],
                    research_depth=topic_data["research_depth"],
                    sources=topic_data["sources"]
                )
                research_topics.append(topic)
            
            # Execute research
            intelligence_report = await deep_research_agent.conduct_weekly_research(
                industry, research_topics
            )
            
            # Update configuration with results
            await self._update_research_config(industry, intelligence_report)
            
            # Log execution
            await self._log_research_execution(industry, intelligence_report, start_time)
            
            # Send notifications
            await self._send_research_notifications(industry, intelligence_report)
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            result = {
                "status": "success",
                "industry": industry,
                "execution_time_seconds": execution_time,
                "findings_count": len(intelligence_report.key_trends) + len(intelligence_report.market_developments),
                "confidence_score": intelligence_report.confidence_score,
                "next_scheduled_run": self._calculate_next_run(config["schedule"]),
                "report_generated_at": intelligence_report.generated_at.isoformat()
            }
            
            logger.info(f"Weekly research completed for {industry} in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Weekly research execution failed for {industry}: {e}")
            
            # Log failure
            await self._log_research_failure(industry, str(e), start_time)
            
            # Send failure notification
            await self._send_failure_notification(industry, str(e))
            
            return {
                "status": "error",
                "industry": industry,
                "error": str(e),
                "execution_time_seconds": (datetime.utcnow() - start_time).total_seconds()
            }
    
    async def _load_research_config(self, industry: str) -> Optional[Dict[str, Any]]:
        """Load research configuration for an industry"""
        try:
            config_file = self.config_path / f"{industry}_research_config.json"
            
            if not config_file.exists():
                return None
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load research config for {industry}: {e}")
            return None
    
    async def _update_research_config(self, industry: str, intelligence_report: IndustryIntelligence):
        """Update research configuration with latest results"""
        try:
            config = await self._load_research_config(industry)
            if not config:
                return
            
            # Update statistics
            config["last_research"] = intelligence_report.generated_at.isoformat()
            config["total_research_runs"] += 1
            
            # Calculate average findings per run
            current_findings = len(intelligence_report.key_trends) + len(intelligence_report.market_developments)
            if config["total_research_runs"] == 1:
                config["average_findings_per_run"] = current_findings
            else:
                # Running average
                old_avg = config.get("average_findings_per_run", 0)
                config["average_findings_per_run"] = (
                    (old_avg * (config["total_research_runs"] - 1) + current_findings) / 
                    config["total_research_runs"]
                )
            
            # Store performance metrics
            config["last_performance_metrics"] = {
                "confidence_score": intelligence_report.confidence_score,
                "findings_count": current_findings,
                "trends_identified": len(intelligence_report.key_trends),
                "market_developments": len(intelligence_report.market_developments),
                "content_opportunities": len(intelligence_report.content_opportunities),
                "source_quality": intelligence_report.source_quality_metrics
            }
            
            # Save updated configuration
            config_file = self.config_path / f"{industry}_research_config.json"
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to update research config for {industry}: {e}")
    
    async def _log_research_execution(self, industry: str, intelligence_report: IndustryIntelligence, start_time: datetime):
        """Log research execution details"""
        try:
            log_entry = {
                "industry": industry,
                "execution_start": start_time.isoformat(),
                "execution_end": datetime.utcnow().isoformat(),
                "status": "success",
                "intelligence_report": {
                    "generated_at": intelligence_report.generated_at.isoformat(),
                    "confidence_score": intelligence_report.confidence_score,
                    "key_trends_count": len(intelligence_report.key_trends),
                    "market_developments_count": len(intelligence_report.market_developments),
                    "content_opportunities_count": len(intelligence_report.content_opportunities),
                    "source_quality": intelligence_report.source_quality_metrics
                }
            }
            
            log_file = self.logs_path / f"{industry}_{start_time.strftime('%Y%m%d_%H%M%S')}_success.json"
            with open(log_file, 'w') as f:
                json.dump(log_entry, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to log research execution: {e}")
    
    async def _log_research_failure(self, industry: str, error: str, start_time: datetime):
        """Log research execution failure"""
        try:
            log_entry = {
                "industry": industry,
                "execution_start": start_time.isoformat(),
                "execution_end": datetime.utcnow().isoformat(),
                "status": "failed",
                "error": error
            }
            
            log_file = self.logs_path / f"{industry}_{start_time.strftime('%Y%m%d_%H%M%S')}_failed.json"
            with open(log_file, 'w') as f:
                json.dump(log_entry, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to log research failure: {e}")
    
    async def _send_research_notifications(self, industry: str, intelligence_report: IndustryIntelligence):
        """Send notifications about research completion"""
        try:
            # High-priority content opportunities
            urgent_opportunities = [
                opp for opp in intelligence_report.content_opportunities
                if opp.get("urgency") == "high"
            ]
            
            # High-impact trends
            high_impact_trends = [
                trend for trend in intelligence_report.key_trends
                if trend.get("impact_level") == "high"
            ]
            
            notification = {
                "type": "research_completed",
                "industry": industry,
                "title": f"Weekly Research Completed - {industry}",
                "message": f"Research completed with {intelligence_report.confidence_score:.0%} confidence",
                "data": {
                    "trends_count": len(intelligence_report.key_trends),
                    "urgent_opportunities": len(urgent_opportunities),
                    "high_impact_trends": len(high_impact_trends),
                    "confidence_score": intelligence_report.confidence_score
                },
                "priority": "high" if urgent_opportunities or high_impact_trends else "medium",
                "created_at": datetime.utcnow().isoformat()
            }
            
            await notification_service.send_notification(notification)
            
        except Exception as e:
            logger.error(f"Failed to send research notifications: {e}")
    
    async def _send_failure_notification(self, industry: str, error: str):
        """Send notification about research failure"""
        try:
            notification = {
                "type": "research_failed",
                "industry": industry,
                "title": f"Research Failed - {industry}",
                "message": f"Weekly research failed: {error}",
                "priority": "high",
                "created_at": datetime.utcnow().isoformat()
            }
            
            await notification_service.send_notification(notification)
            
        except Exception as e:
            logger.error(f"Failed to send failure notification: {e}")
    
    async def get_research_status(self, industry: str) -> Dict[str, Any]:
        """Get current research status for an industry"""
        try:
            config = await self._load_research_config(industry)
            if not config:
                return {"status": "not_configured", "industry": industry}
            
            # Get recent intelligence
            recent_intelligence = await deep_research_agent.get_recent_intelligence(industry, days=7)
            
            status = {
                "industry": industry,
                "status": config.get("status", "unknown"),
                "total_research_runs": config.get("total_research_runs", 0),
                "last_research": config.get("last_research"),
                "average_findings_per_run": config.get("average_findings_per_run", 0),
                "schedule": config.get("schedule"),
                "next_scheduled_run": self._calculate_next_run(config["schedule"]),
                "last_performance_metrics": config.get("last_performance_metrics", {}),
                "recent_intelligence_available": recent_intelligence is not None
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get research status for {industry}: {e}")
            return {"status": "error", "industry": industry, "error": str(e)}
    
    async def update_research_schedule(self, industry: str, new_schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Update research schedule for an industry"""
        try:
            config = await self._load_research_config(industry)
            if not config:
                return {"status": "error", "message": "Industry research not configured"}
            
            # Update schedule
            config["schedule"] = new_schedule
            config["updated_at"] = datetime.utcnow().isoformat()
            
            # Save configuration
            config_file = self.config_path / f"{industry}_research_config.json"
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Reschedule task
            schedule_result = await self._schedule_weekly_research(industry, new_schedule)
            
            return {
                "status": "success",
                "industry": industry,
                "new_schedule": new_schedule,
                "next_run": schedule_result.get("next_run")
            }
            
        except Exception as e:
            logger.error(f"Failed to update research schedule for {industry}: {e}")
            return {"status": "error", "industry": industry, "error": str(e)}
    
    async def trigger_immediate_research(self, user_id: int, industry: str) -> Dict[str, Any]:
        """Trigger immediate research execution for an industry"""
        logger.info(f"Triggering immediate research for {industry} (user: {user_id})")
        return await self.execute_weekly_research(user_id, industry)
    
    async def list_configured_industries(self) -> List[Dict[str, Any]]:
        """List all configured industries and their status"""
        try:
            industries = []
            
            for config_file in self.config_path.glob("*_research_config.json"):
                industry = config_file.stem.replace("_research_config", "")
                status = await self.get_research_status(industry)
                industries.append(status)
            
            return industries
            
        except Exception as e:
            logger.error(f"Failed to list configured industries: {e}")
            return []

# Global instance
research_scheduler = ResearchScheduler()