"""
Data Retention Service

Comprehensive data retention policy management and automated cleanup system.
Implements GDPR/CCPA compliance requirements with configurable retention windows
for all data types in the platform.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, func

from backend.db.models import (
    User, UserSetting, Metric, ContentLog, Goal, WorkflowExecution,
    Notification, Memory, Content, ContentDraft, ContentSchedule,
    SocialConnection, SocialAudit, UsageRecord, ResearchData,
    ContentItem, ContentPerformanceSnapshot, SocialPost,
    PlatformMetricsSnapshot, SocialInteraction, InteractionResponse,
    RefreshTokenBlacklist
)
from backend.db.database import get_db
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class DataCategory(Enum):
    """Data categories with different retention requirements"""
    USER_PROFILE = "user_profile"
    USER_CONTENT = "user_content"
    METRICS_DATA = "metrics_data"
    AUDIT_LOGS = "audit_logs"
    SYSTEM_LOGS = "system_logs"
    SOCIAL_CONNECTIONS = "social_connections"
    AI_GENERATED = "ai_generated"
    SECURITY_DATA = "security_data"
    WORKFLOW_DATA = "workflow_data"
    NOTIFICATIONS = "notifications"
    CACHE_DATA = "cache_data"
    RESEARCH_DATA = "research_data"
    PERFORMANCE_DATA = "performance_data"

@dataclass
class RetentionPolicy:
    """Data retention policy configuration"""
    category: DataCategory
    retention_days: int
    description: str
    automatic_cleanup: bool = True
    legal_hold_exempt: bool = False  # If true, legal holds don't override retention
    gdpr_category: Optional[str] = None  # GDPR data category
    ccpa_category: Optional[str] = None  # CCPA data category

class DataRetentionService:
    """Service for managing data retention policies and automated cleanup"""
    
    def __init__(self):
        self.retention_policies = self._initialize_retention_policies()
        
    def _initialize_retention_policies(self) -> Dict[DataCategory, RetentionPolicy]:
        """Initialize retention policies based on legal and business requirements"""
        policies = {
            # User profile data - keep indefinitely while user is active
            DataCategory.USER_PROFILE: RetentionPolicy(
                category=DataCategory.USER_PROFILE,
                retention_days=3650,  # 10 years after account deletion
                description="User profile information, settings, and authentication data",
                automatic_cleanup=False,  # Manual review required
                gdpr_category="Identity data",
                ccpa_category="Personal information"
            ),
            
            # User-generated content - long retention for business value
            DataCategory.USER_CONTENT: RetentionPolicy(
                category=DataCategory.USER_CONTENT,
                retention_days=2555,  # 7 years
                description="User-created content, posts, drafts, and scheduled content",
                automatic_cleanup=True,
                gdpr_category="Content data",
                ccpa_category="Personal information"
            ),
            
            # Metrics and analytics - medium retention for insights
            DataCategory.METRICS_DATA: RetentionPolicy(
                category=DataCategory.METRICS_DATA,
                retention_days=1095,  # 3 years
                description="Performance metrics, analytics, and engagement data",
                automatic_cleanup=True,
                gdpr_category="Usage data",
                ccpa_category="Commercial information"
            ),
            
            # Audit logs - long retention for compliance
            DataCategory.AUDIT_LOGS: RetentionPolicy(
                category=DataCategory.AUDIT_LOGS,
                retention_days=2555,  # 7 years
                description="Security audit logs, access logs, and compliance records",
                automatic_cleanup=False,  # Compliance requirements
                legal_hold_exempt=True,
                gdpr_category="Security data",
                ccpa_category="Security information"
            ),
            
            # System logs - shorter retention for operational needs
            DataCategory.SYSTEM_LOGS: RetentionPolicy(
                category=DataCategory.SYSTEM_LOGS,
                retention_days=90,  # 3 months
                description="System errors, performance logs, and operational data",
                automatic_cleanup=True,
                gdpr_category="Technical data",
                ccpa_category="System information"
            ),
            
            # Social connections - keep while active, cleanup after disconnection
            DataCategory.SOCIAL_CONNECTIONS: RetentionPolicy(
                category=DataCategory.SOCIAL_CONNECTIONS,
                retention_days=365,  # 1 year after disconnection
                description="OAuth tokens, social platform connections, and credentials",
                automatic_cleanup=True,
                gdpr_category="Connection data",
                ccpa_category="Personal information"
            ),
            
            # AI-generated content - medium retention for model improvement
            DataCategory.AI_GENERATED: RetentionPolicy(
                category=DataCategory.AI_GENERATED,
                retention_days=730,  # 2 years
                description="AI-generated content, suggestions, and model outputs",
                automatic_cleanup=True,
                gdpr_category="Derived data",
                ccpa_category="Inferences"
            ),
            
            # Security data - long retention for security analysis
            DataCategory.SECURITY_DATA: RetentionPolicy(
                category=DataCategory.SECURITY_DATA,
                retention_days=1095,  # 3 years
                description="Security events, authentication logs, and threat data",
                automatic_cleanup=False,
                legal_hold_exempt=True,
                gdpr_category="Security data",
                ccpa_category="Security information"
            ),
            
            # Workflow data - medium retention for process improvement
            DataCategory.WORKFLOW_DATA: RetentionPolicy(
                category=DataCategory.WORKFLOW_DATA,
                retention_days=730,  # 2 years
                description="Workflow executions, automation logs, and process data",
                automatic_cleanup=True,
                gdpr_category="Process data",
                ccpa_category="Commercial information"
            ),
            
            # Notifications - short retention for user experience
            DataCategory.NOTIFICATIONS: RetentionPolicy(
                category=DataCategory.NOTIFICATIONS,
                retention_days=90,  # 3 months
                description="User notifications, alerts, and messages",
                automatic_cleanup=True,
                gdpr_category="Communication data",
                ccpa_category="Personal information"
            ),
            
            # Cache data - very short retention for performance
            DataCategory.CACHE_DATA: RetentionPolicy(
                category=DataCategory.CACHE_DATA,
                retention_days=30,  # 1 month
                description="Cached responses, temporary data, and performance optimizations",
                automatic_cleanup=True,
                gdpr_category="Technical data",
                ccpa_category="System information"
            ),
            
            # Research data - long retention for insights
            DataCategory.RESEARCH_DATA: RetentionPolicy(
                category=DataCategory.RESEARCH_DATA,
                retention_days=1095,  # 3 years
                description="Market research, trend analysis, and competitive intelligence",
                automatic_cleanup=True,
                gdpr_category="Research data",
                ccpa_category="Commercial information"
            ),
            
            # Performance data - medium retention for optimization
            DataCategory.PERFORMANCE_DATA: RetentionPolicy(
                category=DataCategory.PERFORMANCE_DATA,
                retention_days=365,  # 1 year
                description="Performance metrics, monitoring data, and system health",
                automatic_cleanup=True,
                gdpr_category="Technical data",
                ccpa_category="System information"
            ),
        }
        
        return policies
    
    def get_retention_policy(self, category: DataCategory) -> RetentionPolicy:
        """Get retention policy for a specific data category"""
        return self.retention_policies.get(category)
    
    def get_all_retention_policies(self) -> Dict[DataCategory, RetentionPolicy]:
        """Get all retention policies"""
        return self.retention_policies.copy()
    
    def calculate_retention_date(self, category: DataCategory, 
                                created_date: datetime) -> datetime:
        """Calculate retention expiration date for data"""
        policy = self.get_retention_policy(category)
        if not policy:
            # Default to 7 years if no policy found
            return created_date + timedelta(days=2555)
        
        return created_date + timedelta(days=policy.retention_days)
    
    def is_data_expired(self, category: DataCategory, created_date: datetime) -> bool:
        """Check if data has exceeded its retention period"""
        if not created_date:
            return False
            
        # Ensure created_date is timezone aware
        if created_date.tzinfo is None:
            created_date = created_date.replace(tzinfo=timezone.utc)
            
        retention_date = self.calculate_retention_date(category, created_date)
        return datetime.now(timezone.utc) > retention_date
    
    def get_expired_data_count(self, db: Session, category: DataCategory) -> Dict[str, int]:
        """Get count of expired data by model type"""
        expired_counts = {}
        
        # Map categories to database models
        model_mappings = {
            DataCategory.USER_CONTENT: [
                (ContentLog, "created_at"),
                (ContentDraft, "created_at"),
                (ContentSchedule, "created_at"),
                (Content, "created_at"),
                (ContentItem, "created_at"),
            ],
            DataCategory.METRICS_DATA: [
                (Metric, "date_recorded"),
                (ContentPerformanceSnapshot, "snapshot_time"),
                (PlatformMetricsSnapshot, "snapshot_time"),
            ],
            DataCategory.AI_GENERATED: [
                (Memory, "created_at"),
                (Content, "created_at"),  # AI-generated content
            ],
            DataCategory.SOCIAL_CONNECTIONS: [
                (SocialConnection, "created_at"),
                (SocialPost, "created_at"),
                (SocialInteraction, "created_at"),
            ],
            DataCategory.AUDIT_LOGS: [
                (SocialAudit, "created_at"),
                (UsageRecord, "created_at"),
            ],
            DataCategory.WORKFLOW_DATA: [
                (WorkflowExecution, "created_at"),
            ],
            DataCategory.NOTIFICATIONS: [
                (Notification, "created_at"),
            ],
            DataCategory.RESEARCH_DATA: [
                (ResearchData, "created_at"),
            ],
            DataCategory.SECURITY_DATA: [
                (RefreshTokenBlacklist, "revoked_at"),
            ],
        }
        
        policy = self.get_retention_policy(category)
        if not policy:
            return expired_counts
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        models = model_mappings.get(category, [])
        
        for model_class, date_field in models:
            try:
                count = db.query(model_class).filter(
                    getattr(model_class, date_field) < cutoff_date
                ).count()
                expired_counts[model_class.__name__] = count
            except Exception as e:
                logger.error(f"Error counting expired {model_class.__name__}: {e}")
                expired_counts[model_class.__name__] = 0
        
        return expired_counts
    
    def cleanup_expired_data(self, db: Session, category: DataCategory, 
                           dry_run: bool = True) -> Dict[str, Any]:
        """Clean up expired data for a specific category"""
        cleanup_results = {
            "category": category.value,
            "dry_run": dry_run,
            "deleted_counts": {},
            "errors": [],
            "total_deleted": 0,
            "cleanup_date": datetime.now(timezone.utc).isoformat()
        }
        
        policy = self.get_retention_policy(category)
        if not policy:
            cleanup_results["errors"].append(f"No retention policy found for {category.value}")
            return cleanup_results
        
        if not policy.automatic_cleanup:
            cleanup_results["errors"].append(f"Automatic cleanup disabled for {category.value}")
            return cleanup_results
        
        # Get expired data counts first
        expired_counts = self.get_expired_data_count(db, category)
        cleanup_results["expired_counts"] = expired_counts
        
        if not any(expired_counts.values()):
            cleanup_results["message"] = "No expired data found"
            return cleanup_results
        
        # Perform cleanup if not dry run
        if not dry_run:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
            
            # Map categories to cleanup functions
            cleanup_functions = {
                DataCategory.USER_CONTENT: self._cleanup_user_content,
                DataCategory.METRICS_DATA: self._cleanup_metrics_data,
                DataCategory.AI_GENERATED: self._cleanup_ai_generated,
                DataCategory.SOCIAL_CONNECTIONS: self._cleanup_social_connections,
                DataCategory.WORKFLOW_DATA: self._cleanup_workflow_data,
                DataCategory.NOTIFICATIONS: self._cleanup_notifications,
                DataCategory.RESEARCH_DATA: self._cleanup_research_data,
                DataCategory.SECURITY_DATA: self._cleanup_security_data,
            }
            
            cleanup_function = cleanup_functions.get(category)
            if cleanup_function:
                try:
                    deleted_counts = cleanup_function(db, cutoff_date)
                    cleanup_results["deleted_counts"] = deleted_counts
                    cleanup_results["total_deleted"] = sum(deleted_counts.values())
                    
                    # Commit changes
                    db.commit()
                    logger.info(f"Successfully cleaned up {category.value}: {deleted_counts}")
                    
                except Exception as e:
                    db.rollback()
                    error_msg = f"Error cleaning up {category.value}: {str(e)}"
                    cleanup_results["errors"].append(error_msg)
                    logger.error(error_msg)
            else:
                cleanup_results["errors"].append(f"No cleanup function for {category.value}")
        
        return cleanup_results
    
    def _cleanup_user_content(self, db: Session, cutoff_date: datetime) -> Dict[str, int]:
        """Clean up expired user content"""
        deleted_counts = {}
        
        # Content logs
        content_logs = db.query(ContentLog).filter(ContentLog.created_at < cutoff_date)
        deleted_counts["ContentLog"] = content_logs.count()
        if deleted_counts["ContentLog"] > 0:
            content_logs.delete(synchronize_session=False)
        
        # Content drafts
        drafts = db.query(ContentDraft).filter(ContentDraft.created_at < cutoff_date)
        deleted_counts["ContentDraft"] = drafts.count()
        if deleted_counts["ContentDraft"] > 0:
            drafts.delete(synchronize_session=False)
        
        # Content schedules (only completed/failed ones)
        schedules = db.query(ContentSchedule).filter(
            and_(
                ContentSchedule.created_at < cutoff_date,
                ContentSchedule.status.in_(["published", "failed"])
            )
        )
        deleted_counts["ContentSchedule"] = schedules.count()
        if deleted_counts["ContentSchedule"] > 0:
            schedules.delete(synchronize_session=False)
        
        # Content items
        content_items = db.query(ContentItem).filter(ContentItem.created_at < cutoff_date)
        deleted_counts["ContentItem"] = content_items.count()
        if deleted_counts["ContentItem"] > 0:
            content_items.delete(synchronize_session=False)
        
        return deleted_counts
    
    def _cleanup_metrics_data(self, db: Session, cutoff_date: datetime) -> Dict[str, int]:
        """Clean up expired metrics data"""
        deleted_counts = {}
        
        # Metrics
        metrics = db.query(Metric).filter(Metric.date_recorded < cutoff_date)
        deleted_counts["Metric"] = metrics.count()
        if deleted_counts["Metric"] > 0:
            metrics.delete(synchronize_session=False)
        
        # Performance snapshots
        perf_snapshots = db.query(ContentPerformanceSnapshot).filter(
            ContentPerformanceSnapshot.snapshot_time < cutoff_date
        )
        deleted_counts["ContentPerformanceSnapshot"] = perf_snapshots.count()
        if deleted_counts["ContentPerformanceSnapshot"] > 0:
            perf_snapshots.delete(synchronize_session=False)
        
        # Platform metrics snapshots
        platform_snapshots = db.query(PlatformMetricsSnapshot).filter(
            PlatformMetricsSnapshot.snapshot_time < cutoff_date
        )
        deleted_counts["PlatformMetricsSnapshot"] = platform_snapshots.count()
        if deleted_counts["PlatformMetricsSnapshot"] > 0:
            platform_snapshots.delete(synchronize_session=False)
        
        return deleted_counts
    
    def _cleanup_ai_generated(self, db: Session, cutoff_date: datetime) -> Dict[str, int]:
        """Clean up expired AI-generated content"""
        deleted_counts = {}
        
        # AI memories
        memories = db.query(Memory).filter(Memory.created_at < cutoff_date)
        deleted_counts["Memory"] = memories.count()
        if deleted_counts["Memory"] > 0:
            memories.delete(synchronize_session=False)
        
        # AI-generated content (where ai_model is not null)
        ai_content = db.query(Content).filter(
            and_(
                Content.created_at < cutoff_date,
                Content.ai_model.isnot(None)
            )
        )
        deleted_counts["AIContent"] = ai_content.count()
        if deleted_counts["AIContent"] > 0:
            ai_content.delete(synchronize_session=False)
        
        return deleted_counts
    
    def _cleanup_social_connections(self, db: Session, cutoff_date: datetime) -> Dict[str, int]:
        """Clean up expired social connection data"""
        deleted_counts = {}
        
        # Social posts (old ones)
        old_posts = db.query(SocialPost).filter(SocialPost.created_at < cutoff_date)
        deleted_counts["SocialPost"] = old_posts.count()
        if deleted_counts["SocialPost"] > 0:
            old_posts.delete(synchronize_session=False)
        
        # Social interactions
        old_interactions = db.query(SocialInteraction).filter(
            SocialInteraction.created_at < cutoff_date
        )
        deleted_counts["SocialInteraction"] = old_interactions.count()
        if deleted_counts["SocialInteraction"] > 0:
            old_interactions.delete(synchronize_session=False)
        
        # Inactive social connections (connections not used in retention period)
        inactive_connections = db.query(SocialConnection).filter(
            and_(
                SocialConnection.created_at < cutoff_date,
                SocialConnection.is_active == False
            )
        )
        deleted_counts["SocialConnection"] = inactive_connections.count()
        if deleted_counts["SocialConnection"] > 0:
            inactive_connections.delete(synchronize_session=False)
        
        return deleted_counts
    
    def _cleanup_workflow_data(self, db: Session, cutoff_date: datetime) -> Dict[str, int]:
        """Clean up expired workflow execution data"""
        deleted_counts = {}
        
        workflow_executions = db.query(WorkflowExecution).filter(
            WorkflowExecution.created_at < cutoff_date
        )
        deleted_counts["WorkflowExecution"] = workflow_executions.count()
        if deleted_counts["WorkflowExecution"] > 0:
            workflow_executions.delete(synchronize_session=False)
        
        return deleted_counts
    
    def _cleanup_notifications(self, db: Session, cutoff_date: datetime) -> Dict[str, int]:
        """Clean up expired notifications"""
        deleted_counts = {}
        
        notifications = db.query(Notification).filter(
            Notification.created_at < cutoff_date
        )
        deleted_counts["Notification"] = notifications.count()
        if deleted_counts["Notification"] > 0:
            notifications.delete(synchronize_session=False)
        
        return deleted_counts
    
    def _cleanup_research_data(self, db: Session, cutoff_date: datetime) -> Dict[str, int]:
        """Clean up expired research data"""
        deleted_counts = {}
        
        research_data = db.query(ResearchData).filter(
            ResearchData.created_at < cutoff_date
        )
        deleted_counts["ResearchData"] = research_data.count()
        if deleted_counts["ResearchData"] > 0:
            research_data.delete(synchronize_session=False)
        
        return deleted_counts
    
    def _cleanup_security_data(self, db: Session, cutoff_date: datetime) -> Dict[str, int]:
        """Clean up expired security data"""
        deleted_counts = {}
        
        # Blacklisted refresh tokens
        blacklisted_tokens = db.query(RefreshTokenBlacklist).filter(
            RefreshTokenBlacklist.revoked_at < cutoff_date
        )
        deleted_counts["RefreshTokenBlacklist"] = blacklisted_tokens.count()
        if deleted_counts["RefreshTokenBlacklist"] > 0:
            blacklisted_tokens.delete(synchronize_session=False)
        
        return deleted_counts
    
    def generate_retention_report(self, db: Session) -> Dict[str, Any]:
        """Generate comprehensive data retention report"""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "policies": {},
            "expired_data_summary": {},
            "total_expired_records": 0,
            "recommendations": []
        }
        
        # Add policy information
        for category, policy in self.retention_policies.items():
            report["policies"][category.value] = {
                "retention_days": policy.retention_days,
                "description": policy.description,
                "automatic_cleanup": policy.automatic_cleanup,
                "gdpr_category": policy.gdpr_category,
                "ccpa_category": policy.ccpa_category,
            }
        
        # Add expired data counts
        total_expired = 0
        for category in DataCategory:
            expired_counts = self.get_expired_data_count(db, category)
            if any(expired_counts.values()):
                report["expired_data_summary"][category.value] = expired_counts
                total_expired += sum(expired_counts.values())
        
        report["total_expired_records"] = total_expired
        
        # Generate recommendations
        if total_expired > 1000:
            report["recommendations"].append(
                "High volume of expired data detected. Consider running cleanup operations."
            )
        
        if total_expired > 10000:
            report["recommendations"].append(
                "Critical: Very high volume of expired data. Immediate cleanup recommended."
            )
        
        # Check for policies that need attention
        for category, policy in self.retention_policies.items():
            if not policy.automatic_cleanup:
                expired_counts = self.get_expired_data_count(db, category)
                if any(expired_counts.values()):
                    report["recommendations"].append(
                        f"Manual review needed for {category.value}: automatic cleanup disabled"
                    )
        
        return report

# Global instance
retention_service = DataRetentionService()

def get_data_retention_service() -> DataRetentionService:
    """Get the global data retention service instance"""
    return retention_service