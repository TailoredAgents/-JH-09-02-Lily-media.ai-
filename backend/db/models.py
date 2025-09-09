from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, JSON, ForeignKey, Index, UniqueConstraint, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from backend.db.database import Base
from typing import Dict, Any
import uuid

# Import multi-tenant models to ensure all relationships are properly established
from backend.db.multi_tenant_models import (
    Organization, Team, Role, Permission, OrganizationInvitation, 
    UserOrganizationRole, user_teams, role_permissions
)
from backend.db.admin_models import RegistrationKey
from backend.db.user_credentials import UserCredentials

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    hashed_password = Column(String)  # For local authentication
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)  # For FastAPI Users
    is_verified = Column(Boolean, default=False)  # For FastAPI Users
    tier = Column(String, default="base")  # base, pro, enterprise - DEPRECATED, use plan_id
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)  # Reference to Plan model
    auth_provider = Column(String, default="local")  # Authentication provider
    
    # Two-Factor Authentication
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String, nullable=True)  # Base32 secret for TOTP
    two_factor_backup_codes = Column(JSON, nullable=True)  # Recovery codes
    
    # Email Verification & Password Reset
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True, index=True)
    email_verification_sent_at = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String(255), nullable=True, index=True)
    password_reset_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Subscription Management
    subscription_status = Column(String(50), default="free")  # free, active, cancelled, past_due
    subscription_end_date = Column(DateTime(timezone=True), nullable=True)
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    
    # Multi-tenancy: Default organization for personal accounts
    default_organization_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships with explicit foreign keys
    content_logs = relationship("ContentLog", back_populates="user", foreign_keys="ContentLog.user_id")
    metrics = relationship("Metric", back_populates="user", foreign_keys="Metric.user_id")
    user_settings = relationship("UserSetting", back_populates="user", uselist=False, foreign_keys="UserSetting.user_id")
    goals = relationship("Goal", back_populates="user", foreign_keys="Goal.user_id")
    workflow_executions = relationship("WorkflowExecution", back_populates="user", foreign_keys="WorkflowExecution.user_id")
    notifications = relationship("Notification", back_populates="user", foreign_keys="Notification.user_id")
    
    # Multi-tenancy relationships
    default_organization = relationship("Organization", foreign_keys=[default_organization_id])
    teams = relationship("Team", secondary="user_teams", back_populates="members")
    organization_roles = relationship("UserOrganizationRole", foreign_keys="UserOrganizationRole.user_id", back_populates="user")
    
    # Organization ownership and invitations  
    owned_organizations = relationship("Organization", foreign_keys="Organization.owner_id", overlaps="default_organization")
    sent_invitations = relationship("OrganizationInvitation", foreign_keys="OrganizationInvitation.invited_by_id", overlaps="received_invitations")
    received_invitations = relationship("OrganizationInvitation", foreign_keys="OrganizationInvitation.invited_user_id", overlaps="sent_invitations")
    
    
    # User credentials for social media platforms
    credentials = relationship("UserCredentials", back_populates="user", cascade="all, delete-orphan")
    
    # Plan relationship
    plan = relationship("Plan", foreign_keys="User.plan_id", back_populates="users")
    
    # Content and memory relationships (NEW - for AI suggestions performance)
    memories = relationship("Memory", back_populates="user", foreign_keys="Memory.user_id")
    content = relationship("Content", back_populates="user", foreign_keys="Content.user_id")


class Plan(Base):
    """Subscription plan model for Starter, Pro, Enterprise tiers"""
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # Starter, Pro, Enterprise
    display_name = Column(String, nullable=False)  # Display name for UI
    description = Column(Text)  # Plan description
    
    # Pricing
    monthly_price = Column(Numeric(10, 2), nullable=False)  # Monthly price in USD
    annual_price = Column(Numeric(10, 2), nullable=True)  # Annual price (optional)
    trial_days = Column(Integer, default=14)  # Trial period days
    
    # Core limits
    max_social_profiles = Column(Integer, nullable=False)  # Max connected social accounts
    max_users = Column(Integer, default=1)  # Max team members
    max_workspaces = Column(Integer, default=1)  # Max workspaces/organizations
    max_posts_per_day = Column(Integer, nullable=False)  # Daily posting limit
    max_posts_per_week = Column(Integer, nullable=False)  # Weekly posting limit
    
    # Feature flags (stored as JSON for flexibility)
    features = Column(JSON, default={})  # Feature permissions and limits
    
    # Deprecated: old feature flags (for backward compatibility)
    full_ai = Column(Boolean, default=False)
    enhanced_autopilot = Column(Boolean, default=False)
    ai_inbox = Column(Boolean, default=False)
    crm_integration = Column(Boolean, default=False)
    advanced_analytics = Column(Boolean, default=False)
    predictive_analytics = Column(Boolean, default=False)
    white_label = Column(Boolean, default=False)
    
    # AI model access
    basic_ai_only = Column(Boolean, default=True)  # Restrict to basic AI models
    premium_ai_models = Column(Boolean, default=False)  # Access to GPT-4o, GPT Image 1
    image_generation_limit = Column(Integer, default=10)  # Images per day
    
    # Autopilot capabilities
    autopilot_posts_per_day = Column(Integer, default=1)
    autopilot_research_enabled = Column(Boolean, default=False)
    autopilot_ad_campaigns = Column(Boolean, default=False)
    
    # Plan metadata
    is_active = Column(Boolean, default=True)
    is_popular = Column(Boolean, default=False)  # Mark as "Most Popular"
    sort_order = Column(Integer, default=0)  # Display order
    
    # Stripe integration
    stripe_product_id = Column(String)  # Stripe Product ID
    stripe_monthly_price_id = Column(String)  # Stripe Price ID for monthly
    stripe_annual_price_id = Column(String)  # Stripe Price ID for annual
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="plan")
    
    def __repr__(self):
        return f"<Plan(name={self.name}, price=${self.monthly_price}/month)>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "monthly_price": float(self.monthly_price) if self.monthly_price else None,
            "annual_price": float(self.annual_price) if self.annual_price else None,
            "trial_days": self.trial_days,
            "max_social_profiles": self.max_social_profiles,
            "max_users": self.max_users,
            "max_workspaces": self.max_workspaces,
            "max_posts_per_day": self.max_posts_per_day,
            "max_posts_per_week": self.max_posts_per_week,
            "features": self.features,
            "is_popular": self.is_popular
        }


class ContentLog(Base):
    __tablename__ = "content_logs"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)  # P1-1b: Multi-tenancy support
    platform = Column(String, nullable=False)  # twitter, instagram, facebook
    content = Column(Text, nullable=False)
    content_type = Column(String, nullable=False)  # text, image, video
    status = Column(String, default="draft")  # draft, scheduled, published, failed
    engagement_data = Column(JSON, default={})
    scheduled_for = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # External IDs
    platform_post_id = Column(String)  # ID from social platform
    external_post_id = Column(String, index=True)  # For idempotency tracking
    
    # Relationships
    user = relationship("User", back_populates="content_logs")
    organization = relationship("Organization", backref="content_logs")
    
    # Indexes for multi-tenant query optimization
    __table_args__ = (
        Index('ix_content_logs_org_user', 'organization_id', 'user_id'),
        Index('ix_content_logs_org_status', 'organization_id', 'status'),
        Index('ix_content_logs_org_platform', 'organization_id', 'platform'),
    )


class ContentDraft(Base):
    """Phase 7: Content drafts for connection verification"""
    __tablename__ = "content_drafts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("social_connections.id", ondelete="CASCADE"), nullable=False)
    
    # Draft content
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)  # SHA256 of content for idempotency
    media_urls = Column(JSON, default=[])  # List of media URLs
    
    # Status
    status = Column(String(50), default="created", nullable=False)  # created, verified, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    verified_at = Column(DateTime(timezone=True))
    
    # Error tracking
    error_message = Column(Text)
    
    # Relationships
    organization = relationship("Organization")
    connection = relationship("SocialConnection")
    
    __table_args__ = (
        Index('idx_content_drafts_org_connection', organization_id, connection_id),
        Index('idx_content_drafts_hash', content_hash),
    )


class ContentSchedule(Base):
    """Phase 7: Content scheduling with connection-based publishing"""
    __tablename__ = "content_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("social_connections.id", ondelete="CASCADE"), nullable=False)
    
    # Content
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)  # SHA256 for idempotency
    media_urls = Column(JSON, default=[])  # List of media URLs
    
    # Scheduling
    scheduled_for = Column(DateTime(timezone=True))  # NULL for immediate publish
    status = Column(String(50), default="scheduled", nullable=False)  # scheduled, publishing, published, failed
    
    # Publishing results
    published_at = Column(DateTime(timezone=True))
    platform_post_id = Column(String(255))  # ID returned by platform
    error_message = Column(Text)
    
    # Idempotency
    idempotency_key = Column(String(255), unique=True)  # Redis key: org:conn:hash:time
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization")
    connection = relationship("SocialConnection")
    
    __table_args__ = (
        Index('idx_content_schedules_org_connection', organization_id, connection_id),
        Index('idx_content_schedules_scheduled', scheduled_for),
        Index('idx_content_schedules_status', status),
        Index('idx_content_schedules_idempotency', idempotency_key),
        Index('idx_content_schedules_content_hash_connection', content_hash, connection_id),
        UniqueConstraint('content_hash', 'connection_id', name='uq_content_schedule_hash_connection'),
    )


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    metric_type = Column(String, nullable=False)  # engagement, reach, followers, etc.
    platform = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    date_recorded = Column(DateTime(timezone=True), server_default=func.now())
    metric_metadata = Column(JSON, default={})
    
    # Relationships
    user = relationship("User", back_populates="metrics")

class UserSetting(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Brand settings
    brand_name = Column(String)
    brand_voice = Column(String, default="professional")
    primary_color = Column(String, default="#3b82f6")
    secondary_color = Column(String, default="#10b981")  # For accents/gradients
    logo_url = Column(String)
    
    # Industry & Visual Style Settings
    industry_type = Column(String, default="general")  # restaurant, law_firm, tech_startup, healthcare, retail, etc.
    visual_style = Column(String, default="modern")  # modern, classic, minimalist, bold, playful, luxury
    image_mood = Column(JSON, default=["professional", "clean"])  # List of mood keywords
    brand_keywords = Column(JSON, default=[])  # Keywords to emphasize in image generation
    avoid_list = Column(JSON, default=[])  # Things to never include in images
    
    # Image Generation Preferences
    enable_auto_image_generation = Column(Boolean, default=True)
    default_image_model = Column(String, default="grok2")  # grok2, gpt_image_1, etc. (OpenAI image models removed per policy)
    preferred_image_style = Column(JSON, default={
        "lighting": "natural",
        "composition": "rule_of_thirds",
        "color_temperature": "neutral"
    })
    custom_image_prompts = Column(JSON, default={})  # User-defined prompt templates
    image_quality = Column(String, default="high")  # low, medium, high, ultra
    image_aspect_ratio = Column(String, default="1:1")  # 1:1, 16:9, 9:16, 4:5
    style_vault = Column(JSON, default={})  # Brand consistency vault
    
    # Content preferences
    content_frequency = Column(Integer, default=3)  # posts per week
    preferred_platforms = Column(JSON, default=["twitter", "instagram"])
    posting_times = Column(JSON, default={"twitter": "09:00", "instagram": "10:00"})
    
    # AI settings
    creativity_level = Column(Float, default=0.7)  # 0-1 scale
    enable_images = Column(Boolean, default=True)
    enable_repurposing = Column(Boolean, default=True)
    enable_autonomous_mode = Column(Boolean, default=False)  # For autonomous scheduling
    timezone = Column(String, default="UTC")  # User timezone for scheduling
    
    # Integrations
    connected_accounts = Column(JSON, default={})
    
    # Social Inbox Settings
    default_response_personality = Column(String, default="professional")  # professional, friendly, casual, technical
    auto_response_enabled = Column(Boolean, default=False)
    auto_response_confidence_threshold = Column(Float, default=0.8)  # Only auto-respond if AI confidence >= 80%
    auto_response_business_hours_only = Column(Boolean, default=True)
    auto_response_delay_minutes = Column(Integer, default=5)  # Delay before auto-responding
    business_hours_start = Column(String, default="09:00")  # 24h format
    business_hours_end = Column(String, default="17:00")  # 24h format
    business_days = Column(JSON, default=["monday", "tuesday", "wednesday", "thursday", "friday"])
    escalation_keywords = Column(JSON, default=["complaint", "lawsuit", "refund", "angry", "terrible"])
    excluded_response_keywords = Column(JSON, default=["spam", "bot", "fake"])  # Don't respond to these
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_settings")

class ResearchData(Base):
    __tablename__ = "research_data"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    source_url = Column(String)
    platform_source = Column(String)  # twitter, web, etc.
    relevance_score = Column(Float, default=0.0)
    embedding_id = Column(String)  # FAISS vector ID
    tags = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Content categorization
    sentiment = Column(String)  # positive, negative, neutral
    topic_category = Column(String)
    trending_score = Column(Float, default=0.0)


class Goal(Base):
    __tablename__ = "goals"

    id = Column(String, primary_key=True)  # UUID string
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    goal_type = Column(String, nullable=False)  # follower_growth, engagement_rate, etc.
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0.0)
    target_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="active")  # active, paused, completed, failed
    platform = Column(String)  # optional platform-specific goal
    
    # Progress tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Metadata
    goal_metadata = Column(JSON, default={})
    
    # Relationships
    user = relationship("User", back_populates="goals")
    progress_logs = relationship("GoalProgress", back_populates="goal")
    milestones = relationship("Milestone", back_populates="goal")


class GoalProgress(Base):
    __tablename__ = "goal_progress"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(String, ForeignKey("goals.id"), nullable=False)
    old_value = Column(Float, nullable=False)
    new_value = Column(Float, nullable=False)
    change_amount = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(String)  # manual, automatic, import
    notes = Column(Text)
    
    # Relationships
    goal = relationship("Goal", back_populates="progress_logs")


class Milestone(Base):
    __tablename__ = "milestones"
    
    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(String, ForeignKey("goals.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    target_value = Column(Float, nullable=False)
    target_date = Column(DateTime(timezone=True))
    achieved = Column(Boolean, default=False)
    achieved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    goal = relationship("Goal", back_populates="milestones")


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    memory_type = Column(String, nullable=False)  # content, research, template, trend, insight
    vector_id = Column(String, index=True)  # FAISS vector ID
    relevance_score = Column(Float, default=1.0)
    
    # Metadata
    memory_metadata = Column(JSON, default={})
    tags = Column(JSON, default=[])
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Performance tracking
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="memories")


class Content(Base):
    __tablename__ = "content"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String)
    content = Column(Text, nullable=False)
    platform = Column(String, nullable=False)
    status = Column(String, default="draft")  # draft, scheduled, published
    scheduled_at = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))
    
    # Engagement metrics
    engagement_data = Column(JSON, default={})
    performance_score = Column(Float, default=0.0)
    
    # AI generation metadata
    ai_model = Column(String)
    prompt_used = Column(Text)
    generation_params = Column(JSON, default={})
    
    # Vector reference
    memory_id = Column(Integer, ForeignKey("memories.id"))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="content")
    memory = relationship("Memory")


class ContentItem(Base):
    """Enhanced content model with comprehensive metadata and performance tracking"""
    __tablename__ = "content_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String, index=True)  # SHA256 hash for deduplication
    
    # Platform and type information
    platform = Column(String, nullable=False, index=True)  # twitter, instagram, facebook
    content_type = Column(String, nullable=False, index=True)  # text, image, video, carousel, story
    content_format = Column(String)  # post, thread, article, etc.
    
    # Status tracking
    status = Column(String, default="draft", index=True)  # draft, scheduled, published, failed, archived
    published_at = Column(DateTime(timezone=True), index=True)
    scheduled_for = Column(DateTime(timezone=True), index=True)
    
    # External platform references
    platform_post_id = Column(String, index=True)  # ID from social media platform
    platform_url = Column(String)  # Direct URL to the post
    
    # FAISS vector integration
    embedding_id = Column(String, index=True)  # Reference to FAISS vector store
    embedding_model = Column(String, default="text-embedding-3-large")
    
    # Performance metrics (updated by background tasks)
    likes_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)  # retweets, reposts, etc.
    comments_count = Column(Integer, default=0)
    reach_count = Column(Integer, default=0)  # impressions, views
    click_count = Column(Integer, default=0)  # link clicks
    engagement_rate = Column(Float, default=0.0)  # calculated metric
    
    # Performance categorization
    performance_tier = Column(String, default="unknown", index=True)  # viral, high, medium, low, poor
    viral_score = Column(Float, default=0.0)  # 0-1 score for viral potential
    
    # Content categorization and analysis
    topic_category = Column(String, index=True)  # AI-determined topic
    sentiment = Column(String, index=True)  # positive, negative, neutral
    tone = Column(String)  # professional, casual, humorous, etc.
    reading_level = Column(String)  # beginner, intermediate, advanced
    
    # AI generation metadata
    ai_generated = Column(Boolean, default=False)
    ai_model = Column(String)  # gpt-5, gpt-5-mini, etc.
    generation_prompt = Column(Text)
    generation_params = Column(JSON, default={})
    
    # Content optimization
    hashtags = Column(JSON, default=[])  # extracted hashtags
    mentions = Column(JSON, default=[])  # @mentions
    links = Column(JSON, default=[])  # URLs in content
    keywords = Column(JSON, default=[])  # SEO keywords
    
    # Timing and scheduling optimization
    optimal_posting_time = Column(DateTime(timezone=True))
    time_zone = Column(String, default="UTC")
    day_of_week = Column(Integer)  # 0=Monday, 6=Sunday
    hour_of_day = Column(Integer)  # 0-23
    
    # Content relationships
    parent_content_id = Column(String, ForeignKey("content_items.id"))  # For repurposed content
    template_id = Column(String)  # Template used for generation
    campaign_id = Column(String)  # Marketing campaign association
    
    # A/B testing
    ab_test_group = Column(String)  # A, B, C, etc.
    ab_test_id = Column(String, index=True)  # Test identifier
    
    # Approval workflow
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(String)  # User ID who approved
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    
    # Quality metrics
    content_quality_score = Column(Float, default=0.0)  # AI-calculated quality
    brand_voice_alignment = Column(Float, default=0.0)  # Brand consistency score
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_performance_update = Column(DateTime(timezone=True))
    
    # Additional metadata
    content_metadata = Column(JSON, default={})
    
    # Relationships
    user = relationship("User")
    parent_content = relationship("ContentItem", remote_side=[id])
    performance_snapshots = relationship("ContentPerformanceSnapshot", back_populates="content_item")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_content_user_platform', user_id, platform),
        Index('idx_content_performance', performance_tier, engagement_rate),
        Index('idx_content_topic_sentiment', topic_category, sentiment),
        Index('idx_content_created_platform', created_at, platform),
        Index('idx_content_ab_test', ab_test_id, ab_test_group),
    )


class ContentPerformanceSnapshot(Base):
    """Time-series performance data for content items"""
    __tablename__ = "content_performance_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    content_item_id = Column(String, ForeignKey("content_items.id"), nullable=False)
    snapshot_time = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Performance metrics at this point in time
    likes_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    reach_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    
    # Growth metrics (since last snapshot)
    likes_growth = Column(Integer, default=0)
    shares_growth = Column(Integer, default=0)
    comments_growth = Column(Integer, default=0)
    reach_growth = Column(Integer, default=0)
    
    # Velocity metrics (per hour/day)
    engagement_velocity = Column(Float, default=0.0)
    viral_coefficient = Column(Float, default=0.0)
    
    # Platform-specific metrics
    platform_metrics = Column(JSON, default={})
    
    # Relationships
    content_item = relationship("ContentItem", back_populates="performance_snapshots")
    
    __table_args__ = (
        Index('idx_snapshot_content_time', content_item_id, snapshot_time),
    )


class ContentCategory(Base):
    """Hierarchical content categorization system"""
    __tablename__ = "content_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey("content_categories.id"))
    
    # Category metadata
    color = Column(String, default="#6B7280")  # Hex color for UI
    icon = Column(String)  # Icon identifier
    
    # Performance tracking at category level
    avg_engagement_rate = Column(Float, default=0.0)
    total_content_count = Column(Integer, default=0)
    
    # AI training data
    keywords = Column(JSON, default=[])  # Keywords associated with category
    training_samples = Column(JSON, default=[])  # Sample content for AI classification
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    parent = relationship("ContentCategory", remote_side=[id], overlaps="children")
    children = relationship("ContentCategory", overlaps="parent")


class ContentTemplate(Base):
    """Reusable content templates for consistent generation"""
    __tablename__ = "content_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Template content
    template_content = Column(Text, nullable=False)  # With placeholders like {topic}, {insight}
    prompt_template = Column(Text)  # AI prompt template
    
    # Template metadata
    platform = Column(String, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("content_categories.id"))
    content_type = Column(String, nullable=False)  # text, image, video
    
    # Usage statistics
    usage_count = Column(Integer, default=0)
    avg_performance = Column(Float, default=0.0)  # Average engagement of content using this template
    
    # Template configuration
    variables = Column(JSON, default=[])  # List of template variables
    constraints = Column(JSON, default={})  # Length limits, required elements, etc.
    
    # Status
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)  # Shareable templates
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    category = relationship("ContentCategory")


class MemoryContent(Base):
    """Legacy table - keeping for backward compatibility"""
    __tablename__ = "memory_content"

    id = Column(String, primary_key=True)  # UUID string
    content = Column(Text, nullable=False)
    content_type = Column(String, nullable=False)  # research, post, insight, trend
    source = Column(String)  # twitter, web, manual, generated
    platform = Column(String)  # platform this content relates to
    
    # Vector storage
    embedding_id = Column(String)  # Reference to FAISS vector
    similarity_cluster = Column(String)  # Cluster for similar content
    
    # Performance data
    engagement_score = Column(Float, default=0.0)
    performance_tier = Column(String, default="unknown")  # high, medium, low
    
    # Categorization
    tags = Column(JSON, default=[])
    sentiment = Column(String)  # positive, negative, neutral
    topic_category = Column(String)
    relevance_score = Column(Float, default=0.5)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata
    content_metadata = Column(JSON, default={})


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(String, primary_key=True)  # UUID string
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    workflow_type = Column(String, nullable=False)  # daily, optimization, manual
    status = Column(String, default="running")  # running, completed, failed, cancelled
    
    # Execution details
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    
    # Workflow stages
    current_stage = Column(String)
    completed_stages = Column(JSON, default=[])
    failed_stages = Column(JSON, default=[])
    
    # Results
    content_generated = Column(Integer, default=0)
    posts_scheduled = Column(Integer, default=0)
    research_items = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Metadata
    execution_params = Column(JSON, default={})
    results_summary = Column(JSON, default={})
    
    # Relationships
    user = relationship("User", back_populates="workflow_executions")


class Notification(Base):
    """User notifications for goals and system events"""
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Notification content
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, nullable=False, index=True)  # milestone_25, goal_completed, etc.
    priority = Column(String, default="medium")  # high, medium, low
    
    # Related entities
    goal_id = Column(String, ForeignKey("goals.id"), nullable=True)
    content_id = Column(String, nullable=True)  # For content-related notifications
    workflow_id = Column(String, nullable=True)  # For workflow notifications
    
    # Notification state
    is_read = Column(Boolean, default=False, index=True)
    is_dismissed = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True))
    
    # Action data
    action_url = Column(String)  # URL to navigate to when clicked
    action_label = Column(String)  # Button text for action
    
    # Metadata
    notification_metadata = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True))  # Optional expiration
    
    # Relationships
    user = relationship("User")
    goal = relationship("Goal")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_notification_user_read', user_id, is_read),
        Index('idx_notification_user_type', user_id, notification_type),
        Index('idx_notification_created', created_at.desc()),
    )


class RefreshTokenBlacklist(Base):
    """Store revoked/blacklisted refresh tokens"""
    __tablename__ = "refresh_token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    token_jti = Column(String, unique=True, index=True, nullable=False)  # JWT ID claim
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    revoked_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Original token expiration
    
    # Relationships
    user = relationship("User")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_blacklist_token_user', token_jti, user_id),
        Index('idx_blacklist_expires', expires_at),
    )


# Social Platform Connection Models

class SocialPlatformConnection(Base):
    """Stores OAuth tokens and connection details for social platforms"""
    __tablename__ = "social_platform_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String, nullable=False, index=True)  # twitter, instagram, facebook
    
    # Platform account details
    platform_user_id = Column(String, nullable=False, index=True)  # ID from the platform
    platform_username = Column(String, nullable=False)  # @username or handle
    platform_display_name = Column(String)  # Full name or display name
    profile_image_url = Column(String)
    profile_url = Column(String)
    
    # OAuth tokens (encrypted at rest)
    access_token = Column(Text, nullable=False)  # Encrypted OAuth access token
    refresh_token = Column(Text)  # Encrypted OAuth refresh token (if available)
    token_expires_at = Column(DateTime(timezone=True))  # Token expiration
    
    # Token metadata
    token_type = Column(String, default="Bearer")  # Token type (Bearer, etc.)
    scope = Column(String)  # OAuth scopes granted
    
    # Connection status
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)  # Platform verification status
    connection_status = Column(String, default="connected")  # connected, expired, revoked, error
    
    # Platform-specific metadata
    platform_metadata = Column(JSON, default={})  # Follower count, verified status, etc.
    
    # Rate limiting info
    rate_limit_remaining = Column(Integer)
    rate_limit_reset = Column(DateTime(timezone=True))
    daily_post_count = Column(Integer, default=0)
    daily_post_limit = Column(Integer)  # Platform-specific limits
    
    # Error tracking
    last_error = Column(Text)
    error_count = Column(Integer, default=0)
    last_error_at = Column(DateTime(timezone=True))
    
    # Posting preferences for this connection
    auto_post_enabled = Column(Boolean, default=True)
    preferred_posting_times = Column(JSON, default={})  # {"weekdays": "09:00", "weekends": "10:00"}
    content_filters = Column(JSON, default={})  # Content type preferences, hashtag rules, etc.
    
    # Timestamps
    connected_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True))
    last_refreshed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    organization = relationship("Organization")
    posts = relationship("SocialPost", back_populates="connection")
    
    # Unique constraint: one connection per platform per user per organization
    __table_args__ = (
        Index('idx_social_platform_conn_org_user_platform', organization_id, user_id, platform, unique=True),
        Index('idx_social_conn_platform_user', platform, platform_user_id),
        Index('idx_social_platform_conn_org_id', organization_id),
    )


class SocialPost(Base):
    """Tracks posts made to social platforms with detailed metadata"""
    __tablename__ = "social_posts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    connection_id = Column(Integer, ForeignKey("social_platform_connections.id"), nullable=False)
    content_item_id = Column(String, ForeignKey("content_items.id"), nullable=True)  # Link to original content
    
    # Platform details
    platform = Column(String, nullable=False, index=True)
    platform_post_id = Column(String, nullable=False, index=True)  # ID from the platform
    platform_url = Column(String)  # Direct URL to the post
    
    # Post content
    content_text = Column(Text)
    media_urls = Column(JSON, default=[])  # Images, videos attached
    hashtags = Column(JSON, default=[])
    mentions = Column(JSON, default=[])
    
    # Post type and format
    post_type = Column(String, default="text")  # text, image, video, carousel, story, reel
    post_format = Column(String)  # single, thread, article
    
    # Scheduling and timing
    scheduled_for = Column(DateTime(timezone=True))
    posted_at = Column(DateTime(timezone=True), index=True)
    
    # Status tracking
    status = Column(String, default="draft", index=True)  # draft, scheduled, posted, failed, deleted
    failure_reason = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Performance metrics (updated by background jobs)
    likes_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)  # retweets, reposts, etc.
    comments_count = Column(Integer, default=0)
    reach_count = Column(Integer, default=0)  # impressions, views
    click_count = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    
    # Performance tracking
    last_metrics_update = Column(DateTime(timezone=True))
    metrics_update_count = Column(Integer, default=0)
    peak_engagement_time = Column(DateTime(timezone=True))
    
    # Platform-specific metrics
    platform_metrics = Column(JSON, default={})  # Platform-specific engagement data
    
    # Content analysis
    sentiment = Column(String)  # positive, negative, neutral
    topics = Column(JSON, default=[])  # AI-extracted topics
    keywords = Column(JSON, default=[])
    
    # Campaign and tracking
    campaign_id = Column(String, index=True)
    utm_parameters = Column(JSON, default={})  # UTM tracking for links
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    connection = relationship("SocialPlatformConnection", back_populates="posts")
    content_item = relationship("ContentItem")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_social_post_user_platform', user_id, platform),
        Index('idx_social_post_connection_status', connection_id, status),
        Index('idx_social_post_posted_engagement', posted_at, engagement_rate),
        Index('idx_social_post_campaign', campaign_id),
    )


class PlatformMetricsSnapshot(Base):
    """Time-series snapshots of account metrics across platforms"""
    __tablename__ = "platform_metrics_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("social_platform_connections.id"), nullable=False)
    snapshot_time = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Account metrics
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)
    
    # Engagement metrics
    avg_likes_per_post = Column(Float, default=0.0)
    avg_comments_per_post = Column(Float, default=0.0)
    avg_shares_per_post = Column(Float, default=0.0)
    overall_engagement_rate = Column(Float, default=0.0)
    
    # Growth metrics (calculated)
    followers_growth = Column(Integer, default=0)  # Since last snapshot
    posts_growth = Column(Integer, default=0)
    engagement_growth = Column(Float, default=0.0)
    
    # Platform-specific metrics
    platform_specific_metrics = Column(JSON, default={})
    
    # Relationships
    connection = relationship("SocialPlatformConnection")
    
    __table_args__ = (
        Index('idx_metrics_snapshot_conn_time', connection_id, snapshot_time),
    )


class SocialPostTemplate(Base):
    """Platform-specific post templates with formatting rules"""
    __tablename__ = "social_post_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Platform and formatting
    platform = Column(String, nullable=False, index=True)
    post_type = Column(String, nullable=False)  # text, image, video, thread
    
    # Template content
    template_text = Column(Text, nullable=False)  # With variables like {topic}, {insight}
    hashtag_template = Column(String)  # Hashtag pattern
    
    # Platform-specific formatting
    max_length = Column(Integer)  # Character limit
    thread_split_rules = Column(JSON, default={})  # For Twitter threads
    formatting_rules = Column(JSON, default={})  # Bold, italic, links, etc.
    
    # Usage and performance
    usage_count = Column(Integer, default=0)
    avg_engagement_rate = Column(Float, default=0.0)
    
    # Template metadata
    variables = Column(JSON, default=[])  # List of template variables
    required_media = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    
    __table_args__ = (
        Index('idx_social_template_user_platform', user_id, platform),
    )


# Phase 3A: Social Inbox Models

class SocialInteraction(Base):
    """Stores incoming social media interactions (comments, mentions, DMs)"""
    __tablename__ = "social_interactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    connection_id = Column(Integer, ForeignKey("social_platform_connections.id"), nullable=True)
    
    # Platform and interaction details
    platform = Column(String, nullable=False, index=True)  # facebook, instagram, twitter
    interaction_type = Column(String, nullable=False, index=True)  # comment, mention, dm, reply
    external_id = Column(String, nullable=False, index=True)  # Platform's ID for this interaction
    parent_external_id = Column(String, nullable=True)  # For replies/nested comments
    
    # Author information
    author_platform_id = Column(String, nullable=False)
    author_username = Column(String, nullable=False)
    author_display_name = Column(String)
    author_profile_url = Column(String)
    author_profile_image = Column(String)
    author_verified = Column(Boolean, default=False)
    
    # Interaction content
    content = Column(Text, nullable=False)
    media_urls = Column(JSON, default=[])  # Images/videos in the interaction
    hashtags = Column(JSON, default=[])
    mentions = Column(JSON, default=[])
    
    # Analysis and categorization
    sentiment = Column(String, default="neutral")  # positive, negative, neutral
    intent = Column(String)  # question, complaint, praise, lead, spam
    priority_score = Column(Float, default=0.0)  # 0-100 priority ranking
    
    # Response handling
    status = Column(String, default="unread", index=True)  # unread, read, responded, archived, escalated
    response_strategy = Column(String, default="auto")  # auto, manual, escalate, ignore
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)  # For manual assignment
    
    # Platform metadata
    platform_metadata = Column(JSON, default={})  # Platform-specific data
    
    # Timestamps
    platform_created_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    connection = relationship("SocialPlatformConnection")
    assigned_user = relationship("User", foreign_keys=[assigned_to])
    responses = relationship("InteractionResponse", back_populates="interaction")
    
    __table_args__ = (
        Index('idx_social_interaction_platform_type', platform, interaction_type),
        Index('idx_social_interaction_status_priority', status, priority_score),
        Index('idx_social_interaction_user_received', user_id, received_at),
        Index('idx_social_interaction_external', platform, external_id),
    )


class InteractionResponse(Base):
    """Stores responses sent to social media interactions"""
    __tablename__ = "interaction_responses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    interaction_id = Column(String, ForeignKey("social_interactions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Response content
    response_text = Column(Text, nullable=False)
    media_urls = Column(JSON, default=[])
    
    # Response metadata
    response_type = Column(String, default="manual")  # auto, manual, template
    template_id = Column(String, ForeignKey("response_templates.id"), nullable=True)
    ai_confidence_score = Column(Float, default=0.0)  # How confident AI was in this response
    
    # Platform posting details
    platform = Column(String, nullable=False)
    platform_response_id = Column(String)  # ID from platform after posting
    platform_url = Column(String)  # Direct URL to the response
    
    # Status and timing
    status = Column(String, default="pending")  # pending, sent, failed, deleted
    failure_reason = Column(Text)
    retry_count = Column(Integer, default=0)
    
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    interaction = relationship("SocialInteraction", back_populates="responses")
    user = relationship("User")
    template = relationship("ResponseTemplate")
    
    __table_args__ = (
        Index('idx_interaction_response_interaction', interaction_id),
        Index('idx_interaction_response_status', status),
        Index('idx_interaction_response_user_sent', user_id, sent_at),
    )


class ResponseTemplate(Base):
    """AI response templates with personality and trigger conditions"""
    __tablename__ = "response_templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Template identification
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Trigger conditions
    trigger_type = Column(String, nullable=False)  # intent, keyword, platform, sentiment
    trigger_conditions = Column(JSON, default={})  # Specific conditions for activation
    keywords = Column(JSON, default=[])  # Keywords that trigger this template
    platforms = Column(JSON, default=[])  # Platforms where this template applies
    
    # Response content
    response_text = Column(Text, nullable=False)
    variables = Column(JSON, default=[])  # {company_name}, {customer_name}, etc.
    
    # Personality settings
    personality_style = Column(String, default="professional")  # professional, friendly, casual, technical
    tone = Column(String, default="helpful")  # helpful, apologetic, enthusiastic, informative
    formality_level = Column(Integer, default=5)  # 1-10 scale
    
    # Platform-specific adaptations
    platform_adaptations = Column(JSON, default={})  # Platform-specific variations
    
    # Usage and performance
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)  # Based on customer satisfaction
    avg_response_time = Column(Float, default=0.0)
    
    # Status and settings
    is_active = Column(Boolean, default=True)
    auto_approve = Column(Boolean, default=False)  # Auto-send without human review
    priority = Column(Integer, default=50)  # Template selection priority
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    responses = relationship("InteractionResponse", back_populates="template")
    
    __table_args__ = (
        Index('idx_response_template_user_active', user_id, is_active),
        Index('idx_response_template_trigger', trigger_type),
    )


class CompanyKnowledge(Base):
    """Company knowledge base for AI-powered responses"""
    __tablename__ = "company_knowledge"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Content identification
    title = Column(String, nullable=False)
    topic = Column(String, nullable=False)  # faq, policy, product_info, contact_info, etc.
    
    # Knowledge content
    content = Column(Text, nullable=False)
    summary = Column(String)  # Brief summary for quick reference
    
    # Searchability
    keywords = Column(JSON, default=[])
    tags = Column(JSON, default=[])
    embedding_vector = Column(JSON, nullable=True)  # For semantic search
    
    # Context and usage
    context_type = Column(String, default="general")  # customer_service, sales, technical, etc.
    platforms = Column(JSON, default=["facebook", "instagram", "twitter"])  # Where to use this knowledge
    
    # Content metadata
    source = Column(String)  # manual, imported, auto_generated
    confidence_score = Column(Float, default=1.0)  # How confident we are in this info
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    effectiveness_score = Column(Float, default=0.0)  # Based on response success
    
    # Status
    is_active = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=False)  # For sensitive information
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    
    __table_args__ = (
        Index('idx_company_knowledge_user_topic', user_id, topic),
        Index('idx_company_knowledge_active', is_active),
        Index('idx_company_knowledge_usage', usage_count, last_used_at),
    )


class SocialConnection(Base):
    """Tenant-scoped social media connections for partner OAuth"""
    __tablename__ = "social_connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(50), nullable=False)  # meta, x, etc.
    connection_name = Column(String(255))  # User-friendly name
    platform_account_id = Column(String(255))  # Platform's account ID
    platform_username = Column(String(255))  # @handle or page name
    
    # Encrypted tokens (versioned envelope JSON)
    access_token = Column(Text)  # Encrypted with versioned envelope
    refresh_token = Column(Text)  # Encrypted with versioned envelope
    page_access_token = Column(Text)  # Encrypted, Meta Pages only
    
    # Encryption metadata
    enc_version = Column(Integer, nullable=False, default=1)
    enc_kid = Column(String(50), nullable=False, default='default')  # Key ID for rotation
    
    # Token lifecycle
    token_expires_at = Column(DateTime(timezone=True))
    scopes = Column(JSON)  # List of granted scopes
    
    # Platform-specific metadata
    platform_metadata = Column(JSON, default={})  # page_id, ig_business_id, since_id for X
    
    # Webhook configuration
    webhook_subscribed = Column(Boolean, default=False)
    webhook_secret = Column(String(255))
    
    # Status tracking
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime(timezone=True))
    last_checked_at = Column(DateTime(timezone=True))
    verified_for_posting = Column(Boolean, default=False)  # Phase 7: First-run draft gate
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="social_connections")
    audit_logs = relationship("SocialAudit", back_populates="connection", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_social_connections_org', organization_id),
        Index('idx_social_connections_expires', token_expires_at),
        Index('idx_social_connections_active', organization_id, platform, 
              postgresql_where='is_active = TRUE AND revoked_at IS NULL'),
        {'extend_existing': True}
    )


class SocialAudit(Base):
    """Audit log for all social connection operations"""
    __tablename__ = "social_audit"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    connection_id = Column(UUID(as_uuid=True), ForeignKey("social_connections.id", ondelete="CASCADE"))
    
    # Action details
    action = Column(String(50), nullable=False)  # connect, disconnect, refresh, publish, webhook_verify
    platform = Column(String(50))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    
    # Operation metadata
    audit_metadata = Column(JSON)  # Additional context for the action
    status = Column(String(50))  # success, failure, pending
    error_message = Column(Text)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization")
    connection = relationship("SocialConnection", back_populates="audit_logs")
    user = relationship("User")
    
    __table_args__ = (
        Index('idx_social_audit_org', organization_id),
        Index('idx_social_audit_connection', connection_id),
        Index('idx_social_audit_created', created_at),
        {'extend_existing': True}
    )


class UsageRecord(Base):
    """Track usage for subscription enforcement"""
    __tablename__ = "usage_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Usage details
    usage_type = Column(String(50), nullable=False)  # image_generation, posts, api_calls, etc.
    resource = Column(String(50))  # specific resource used (grok2, gpt_image_1, twitter_post, etc.)
    quantity = Column(Integer, default=1)  # amount used
    
    # Cost and billing information
    cost_credits = Column(Numeric(10, 4), default=0.0)  # Cost in internal credits
    cost_usd = Column(Numeric(10, 4), default=0.0)  # Cost in USD
    
    # Additional context  
    usage_metadata = Column(JSON)  # Additional context (prompt, platform, quality, etc.)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    billing_period = Column(String(7), nullable=False, index=True)  # YYYY-MM for monthly aggregation
    
    # Relationships
    user = relationship("User")
    organization = relationship("Organization")
    
    __table_args__ = (
        Index('idx_usage_user_period', user_id, billing_period),
        Index('idx_usage_org_period', organization_id, billing_period),
        Index('idx_usage_type_period', usage_type, billing_period),
        Index('idx_usage_created', created_at.desc()),
    )


# Pressure Washing Pricing Models

class PricingRule(Base):
    """
    PW-PRICING-ADD-001: Organization-scoped pricing rules for pressure washing services
    
    Stores pricing configuration including base rates, bundles, seasonal modifiers,
    and minimum job totals for computing ballpark quotes.
    """
    __tablename__ = "pricing_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Pricing metadata
    name = Column(String(255), nullable=False, default="Default Pricing")
    description = Column(Text)
    currency = Column(String(3), nullable=False, default="USD")  # ISO 4217 currency code
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Core pricing configuration
    min_job_total = Column(Numeric(10, 2), nullable=False, default=150.00)  # Minimum job charge
    
    # Base rates per surface type (per square foot)
    base_rates = Column(JSON, nullable=False, default={
        "concrete": 0.15,
        "brick": 0.18,
        "vinyl_siding": 0.20,
        "wood_deck": 0.25,
        "roof": 0.30,
        "driveway": 0.12,
        "patio": 0.15,
        "fence": 0.22
    })
    
    # Service bundles with discount percentages
    bundles = Column(JSON, nullable=False, default=[
        {
            "name": "House + Driveway Package",
            "services": ["vinyl_siding", "driveway"],
            "discount_pct": 0.15,
            "description": "Save 15% when bundling house and driveway cleaning"
        },
        {
            "name": "Complete Property Package", 
            "services": ["vinyl_siding", "driveway", "patio", "fence"],
            "discount_pct": 0.20,
            "description": "Save 20% on full property cleaning"
        }
    ])
    
    # Seasonal pricing modifiers by month
    seasonal_modifiers = Column(JSON, nullable=False, default={
        "1": 0.8,   # January - Winter discount
        "2": 0.8,   # February - Winter discount
        "3": 1.2,   # March - Spring premium
        "4": 1.2,   # April - Spring premium
        "5": 1.1,   # May - Spring moderate
        "6": 1.0,   # June - Standard
        "7": 1.0,   # July - Standard
        "8": 1.0,   # August - Standard
        "9": 1.1,   # September - Fall moderate
        "10": 1.1,  # October - Fall moderate
        "11": 0.9,  # November - Fall discount
        "12": 0.8   # December - Winter discount
    })
    
    # Additional service rates (optional)
    additional_services = Column(JSON, default={
        "gutter_cleaning_per_linear_foot": 1.50,
        "soft_wash_multiplier": 1.3,
        "pressure_wash_multiplier": 1.0,
        "stain_removal_multiplier": 1.5,
        "sealant_application_multiplier": 2.0
    })
    
    # Travel and logistics
    travel_settings = Column(JSON, default={
        "free_radius_miles": 15.0,
        "rate_per_mile": 2.00,
        "minimum_travel_charge": 25.00,
        "maximum_travel_distance": 50.0
    })
    
    # Pricing rule metadata
    version = Column(Integer, nullable=False, default=1)  # For versioning pricing rules
    effective_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expiry_date = Column(DateTime(timezone=True))  # Optional expiration
    
    # Audit fields
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization", backref="pricing_rules")
    created_by = relationship("User")
    
    # Indexes for performance and multi-tenancy
    __table_args__ = (
        Index('ix_pricing_rules_org_active', organization_id, is_active),
        Index('ix_pricing_rules_org_effective', organization_id, effective_date),
        UniqueConstraint('organization_id', 'name', name='uq_pricing_rule_org_name'),
    )
    
    def __repr__(self):
        return f"<PricingRule(org={self.organization_id}, name='{self.name}', active={self.is_active})>"
    
    def to_dict(self):
        """Convert pricing rule to dictionary for API responses"""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "description": self.description,
            "currency": self.currency,
            "is_active": self.is_active,
            "min_job_total": float(self.min_job_total) if self.min_job_total else None,
            "base_rates": self.base_rates,
            "bundles": self.bundles,
            "seasonal_modifiers": self.seasonal_modifiers,
            "additional_services": self.additional_services,
            "travel_settings": self.travel_settings,
            "version": self.version,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Quote(Base):
    """
    PW-PRICING-ADD-002: Organization-scoped quotes with status lifecycle
    
    Converts pricing computations into customer quotes that can be accepted/declined
    to track lead conversion from DM inquiries to booked jobs.
    """
    __tablename__ = "quotes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Lead relationship (optional - for quotes created from leads)
    lead_id = Column(String, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Customer information (can be populated from lead or directly)
    customer_email = Column(String, nullable=False, index=True)
    customer_name = Column(String)
    customer_phone = Column(String)
    customer_address = Column(Text)
    
    # Quote content and pricing
    line_items = Column(JSON, nullable=False, default=[])  # Detailed breakdown from pricing engine
    subtotal = Column(Numeric(10, 2), nullable=False)
    discounts = Column(Numeric(10, 2), nullable=False, default=0.00)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    total = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    
    # Quote lifecycle status
    status = Column(String(20), nullable=False, default="draft", index=True)
    # Status values: draft, sent, accepted, declined, expired
    
    # Status transitions tracking
    sent_at = Column(DateTime(timezone=True))
    accepted_at = Column(DateTime(timezone=True))
    declined_at = Column(DateTime(timezone=True))
    expired_at = Column(DateTime(timezone=True))
    
    # Quote metadata
    quote_number = Column(String(50), unique=True, index=True)  # Human-readable quote number
    valid_until = Column(DateTime(timezone=True))  # Quote expiration
    notes = Column(Text)  # Internal notes
    customer_notes = Column(Text)  # Notes visible to customer
    
    # Source tracking
    source = Column(String(50), default="manual")  # manual, dm_inquiry, website, phone
    source_metadata = Column(JSON, default={})  # Additional source context
    
    # Related pricing data
    pricing_rule_id = Column(Integer, ForeignKey("pricing_rules.id"), nullable=True)
    pricing_snapshot = Column(JSON)  # Snapshot of pricing computation for audit
    
    # Audit fields
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", backref="quotes")
    pricing_rule = relationship("PricingRule", backref="quotes")
    lead = relationship("Lead", back_populates="quotes")
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    
    # Indexes for performance and multi-tenancy
    __table_args__ = (
        Index('ix_quotes_org_status', organization_id, status),
        Index('ix_quotes_org_customer', organization_id, customer_email),
        Index('ix_quotes_org_created', organization_id, created_at),
        Index('ix_quotes_valid_until', valid_until),
    )
    
    def __repr__(self):
        return f"<Quote(id={self.id}, org={self.organization_id}, status={self.status}, total={self.total})>"


class MediaAsset(Base):
    """
    PW-SEC-ADD-001: Secure media storage for quote photos and PII assets
    
    Stores encrypted media assets with organization isolation and audit trail.
    Supports signed URLs for secure upload/download with TTL enforcement.
    """
    __tablename__ = "media_assets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Optional relationship to lead (for quote photos)
    lead_id = Column(String, ForeignKey("leads.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Storage metadata
    storage_key = Column(String, nullable=False, unique=True, index=True)  # S3 key or file path
    filename = Column(String, nullable=False)  # Original filename
    mime_type = Column(String, nullable=False, index=True)
    file_size = Column(Integer, nullable=False)
    
    # Security and integrity
    sha256_hash = Column(String(64), nullable=False, index=True)  # File integrity hash
    encryption_key = Column(Text, nullable=True)  # Encrypted storage key (for additional encryption)
    
    # Asset status and lifecycle
    status = Column(String(20), nullable=False, default="active", index=True)  # active, deleted, expired
    upload_completed = Column(Boolean, default=False, index=True)
    
    # TTL and access control
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Asset expiration
    access_count = Column(Integer, default=0)  # Track download count for audit
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Asset metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    asset_metadata = Column(JSON, default={})  # Width, height, EXIF data, etc.
    tags = Column(JSON, default=[])  # Categorization tags
    
    # Audit fields
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization")
    lead = relationship("Lead", back_populates="media_assets")
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    
    # Indexes for performance and multi-tenancy
    __table_args__ = (
        Index('ix_media_assets_org_status', organization_id, status),
        Index('ix_media_assets_org_lead', organization_id, lead_id),
        Index('ix_media_assets_org_created', organization_id, created_at),
        Index('ix_media_assets_upload_status', upload_completed, status),
        Index('ix_media_assets_expires', expires_at),
    )
    
    def __repr__(self):
        return f"<MediaAsset(id={self.id}, org={self.organization_id}, filename={self.filename}, size={self.file_size})>"
    
    def to_dict(self):
        """Convert media asset to dictionary for API responses (redacts sensitive data)"""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "lead_id": self.lead_id,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "sha256_hash": self.sha256_hash,
            "status": self.status,
            "upload_completed": self.upload_completed,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "asset_metadata": self.asset_metadata,
            "tags": self.tags,
            "created_by_id": self.created_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def is_expired(self) -> bool:
        """Check if asset has expired"""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def can_access(self, user_org_id: str) -> bool:
        """Check if user's organization can access this asset"""
        return self.organization_id == user_org_id and self.status == "active" and not self.is_expired()
    
    def to_dict(self):
        """Convert quote to dictionary for API responses"""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "quote_number": self.quote_number,
            "customer_email": self.customer_email,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "customer_address": self.customer_address,
            "line_items": self.line_items,
            "subtotal": float(self.subtotal) if self.subtotal else 0.0,
            "discounts": float(self.discounts) if self.discounts else 0.0,
            "tax_amount": float(self.tax_amount) if self.tax_amount else 0.0,
            "total": float(self.total) if self.total else 0.0,
            "currency": self.currency,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "declined_at": self.declined_at.isoformat() if self.declined_at else None,
            "expired_at": self.expired_at.isoformat() if self.expired_at else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "notes": self.notes,
            "customer_notes": self.customer_notes,
            "source": self.source,
            "source_metadata": self.source_metadata,
            "pricing_rule_id": self.pricing_rule_id,
            "created_by_id": self.created_by_id,
            "updated_by_id": self.updated_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def is_expired(self):
        """Check if quote has expired"""
        from datetime import datetime, timezone
        if not self.valid_until:
            return False
        return datetime.now(timezone.utc) > self.valid_until
    
    def can_transition_to(self, new_status: str) -> bool:
        """Check if status transition is allowed"""
        valid_transitions = {
            "draft": ["sent", "declined"],
            "sent": ["accepted", "declined", "expired"],
            "accepted": [],  # Terminal state
            "declined": [],  # Terminal state  
            "expired": []    # Terminal state
        }
        return new_status in valid_transitions.get(self.status, [])


# P1-5b: Webhook Event Idempotency Store Models

class WebhookIdempotencyRecord(Base):
    """
    P1-5b: Idempotency tracking for webhook events to prevent duplicate processing
    """
    __tablename__ = "webhook_idempotency_records"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Idempotency key (hash of event signature + payload content)
    idempotency_key = Column(String(64), unique=True, nullable=False, index=True)
    
    # Webhook identification
    platform = Column(String(50), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    webhook_id = Column(String(255), nullable=True, index=True)  # Platform-provided ID
    
    # Tenant isolation
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Processing tracking
    processing_result = Column(String(50), nullable=False)  # WebhookProcessingResult
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processing_time_ms = Column(Integer, nullable=True)
    
    # Event data summary (no sensitive info)
    event_summary = Column(JSON, nullable=True)
    
    # Expiration for cleanup
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_webhook_idempotency_platform_event', 'platform', 'event_type'),
        Index('idx_webhook_idempotency_expires', 'expires_at'),
        Index('idx_webhook_idempotency_org', 'organization_id'),
    )


class WebhookDeliveryTracker(Base):
    """
    P1-5b: Enhanced webhook delivery tracking with retry logic and reliability monitoring
    """
    __tablename__ = "webhook_delivery_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Webhook identification
    webhook_id = Column(String(255), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    
    # Tenant isolation
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Delivery status
    delivery_status = Column(String(50), nullable=False, index=True)  # WebhookDeliveryStatus
    attempt_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=5, nullable=False)
    
    # Timing
    first_attempted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_attempted_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Failure tracking
    failure_reason = Column(String(100), nullable=True)
    last_error_message = Column(Text, nullable=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    
    # Performance metrics
    total_processing_time_ms = Column(Integer, default=0, nullable=False)
    avg_response_time_ms = Column(Integer, nullable=True)
    
    # Event payload metadata (no sensitive data)
    event_metadata = Column(JSON, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_webhook_delivery_status', 'delivery_status'),
        Index('idx_webhook_delivery_next_retry', 'next_retry_at'),
        Index('idx_webhook_delivery_platform_event', 'platform', 'event_type'),
        Index('idx_webhook_delivery_org', 'organization_id'),
    )


# PW-DM-REPLACE-001: Lead management for pressure washing DM pipeline
class Lead(Base):
    """
    Lead model for tracking potential customers from social media DMs
    Converts social interactions with pricing intent into actionable sales objects
    """
    __tablename__ = "leads"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Source tracking - linked to SocialInteraction
    interaction_id = Column(String, ForeignKey("social_interactions.id", ondelete="SET NULL"), nullable=True, index=True)
    source_platform = Column(String, nullable=False, index=True)  # facebook, instagram, twitter
    
    # Contact information (optional - extracted from DM content or profile)
    contact_name = Column(String, nullable=True)
    contact_email = Column(String, nullable=True, index=True)
    contact_phone = Column(String, nullable=True)
    contact_address = Column(Text, nullable=True)  # Physical address for service location
    
    # Lead details
    requested_services = Column(JSON, nullable=False, default=[])  # List of service types requested
    pricing_intent = Column(String, nullable=True)  # Detected intent: "quote_request", "price_inquiry", "service_interest"
    extracted_surfaces = Column(JSON, nullable=True)  # Surface data if detected: {"driveway": {"area": 1000}, ...}
    extracted_details = Column(JSON, nullable=True)  # Other extracted details from DM
    
    # Lead management
    status = Column(String(20), nullable=False, default="new", index=True)  # new, contacted, qualified, closed
    priority_score = Column(Float, default=0.0)  # 0-100 priority based on intent strength and details
    notes = Column(Text, nullable=True)  # Internal notes for lead management
    
    # Audit and tracking
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="leads")
    interaction = relationship("SocialInteraction")
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    quotes = relationship("Quote", back_populates="lead")
    media_assets = relationship("MediaAsset", back_populates="lead", cascade="all, delete-orphan")
    
    # Multi-tenant indexes for performance
    __table_args__ = (
        Index('idx_lead_org_status', 'organization_id', 'status'),
        Index('idx_lead_org_created', 'organization_id', 'created_at'),
        Index('idx_lead_platform_org', 'source_platform', 'organization_id'),
        Index('idx_lead_contact_email', 'contact_email'),
        Index('idx_lead_priority', 'priority_score'),
    )
    
    def can_transition_to(self, new_status: str) -> bool:
        """Validate status transitions for lead lifecycle"""
        valid_transitions = {
            "new": ["contacted", "qualified", "closed"],
            "contacted": ["qualified", "closed"],
            "qualified": ["closed"],
            "closed": []  # Terminal state
        }
        return new_status in valid_transitions.get(self.status, [])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Lead to dictionary for API responses"""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "interaction_id": self.interaction_id,
            "source_platform": self.source_platform,
            "contact_name": self.contact_name,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "contact_address": self.contact_address,
            "requested_services": self.requested_services,
            "pricing_intent": self.pricing_intent,
            "extracted_surfaces": self.extracted_surfaces,
            "extracted_details": self.extracted_details,
            "status": self.status,
            "priority_score": self.priority_score,
            "notes": self.notes,
            "created_by_id": self.created_by_id,
            "updated_by_id": self.updated_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }