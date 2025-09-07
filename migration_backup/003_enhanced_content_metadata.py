"""Enhanced content metadata schema with performance tracking

Revision ID: 003_enhanced_content_metadata
Revises: 002_add_auth_fields
Create Date: 2025-07-23 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_enhanced_content_metadata'
down_revision = '002_add_auth_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create content_categories table
    op.create_table('content_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('color', sa.String(), nullable=True),
        sa.Column('icon', sa.String(), nullable=True),
        sa.Column('avg_engagement_rate', sa.Float(), nullable=True),
        sa.Column('total_content_count', sa.Integer(), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('training_samples', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['content_categories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_content_categories_id'), 'content_categories', ['id'], unique=False)
    op.create_index(op.f('ix_content_categories_slug'), 'content_categories', ['slug'], unique=False)

    # Create content_items table
    op.create_table('content_items',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=True),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('content_format', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True),
        sa.Column('platform_post_id', sa.String(), nullable=True),
        sa.Column('platform_url', sa.String(), nullable=True),
        sa.Column('embedding_id', sa.String(), nullable=True),
        sa.Column('embedding_model', sa.String(), nullable=True),
        sa.Column('likes_count', sa.Integer(), nullable=True),
        sa.Column('shares_count', sa.Integer(), nullable=True),
        sa.Column('comments_count', sa.Integer(), nullable=True),
        sa.Column('reach_count', sa.Integer(), nullable=True),
        sa.Column('click_count', sa.Integer(), nullable=True),
        sa.Column('engagement_rate', sa.Float(), nullable=True),
        sa.Column('performance_tier', sa.String(), nullable=True),
        sa.Column('viral_score', sa.Float(), nullable=True),
        sa.Column('topic_category', sa.String(), nullable=True),
        sa.Column('sentiment', sa.String(), nullable=True),
        sa.Column('tone', sa.String(), nullable=True),
        sa.Column('reading_level', sa.String(), nullable=True),
        sa.Column('ai_generated', sa.Boolean(), nullable=True),
        sa.Column('ai_model', sa.String(), nullable=True),
        sa.Column('generation_prompt', sa.Text(), nullable=True),
        sa.Column('generation_params', sa.JSON(), nullable=True),
        sa.Column('hashtags', sa.JSON(), nullable=True),
        sa.Column('mentions', sa.JSON(), nullable=True),
        sa.Column('links', sa.JSON(), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('optimal_posting_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_zone', sa.String(), nullable=True),
        sa.Column('day_of_week', sa.Integer(), nullable=True),
        sa.Column('hour_of_day', sa.Integer(), nullable=True),
        sa.Column('parent_content_id', sa.String(), nullable=True),
        sa.Column('template_id', sa.String(), nullable=True),
        sa.Column('campaign_id', sa.String(), nullable=True),
        sa.Column('ab_test_group', sa.String(), nullable=True),
        sa.Column('ab_test_id', sa.String(), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), nullable=True),
        sa.Column('approved_by', sa.String(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('content_quality_score', sa.Float(), nullable=True),
        sa.Column('brand_voice_alignment', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_performance_update', sa.DateTime(timezone=True), nullable=True),
        sa.Column('content_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['parent_content_id'], ['content_items.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for content_items
    op.create_index('idx_content_ab_test', 'content_items', ['ab_test_id', 'ab_test_group'], unique=False)
    op.create_index('idx_content_created_platform', 'content_items', ['created_at', 'platform'], unique=False)
    op.create_index('idx_content_performance', 'content_items', ['performance_tier', 'engagement_rate'], unique=False)
    op.create_index('idx_content_topic_sentiment', 'content_items', ['topic_category', 'sentiment'], unique=False)
    op.create_index('idx_content_user_platform', 'content_items', ['user_id', 'platform'], unique=False)
    op.create_index(op.f('ix_content_items_ab_test_id'), 'content_items', ['ab_test_id'], unique=False)
    op.create_index(op.f('ix_content_items_content_hash'), 'content_items', ['content_hash'], unique=False)
    op.create_index(op.f('ix_content_items_content_type'), 'content_items', ['content_type'], unique=False)
    op.create_index(op.f('ix_content_items_created_at'), 'content_items', ['created_at'], unique=False)
    op.create_index(op.f('ix_content_items_embedding_id'), 'content_items', ['embedding_id'], unique=False)
    op.create_index(op.f('ix_content_items_performance_tier'), 'content_items', ['performance_tier'], unique=False)
    op.create_index(op.f('ix_content_items_platform'), 'content_items', ['platform'], unique=False)
    op.create_index(op.f('ix_content_items_platform_post_id'), 'content_items', ['platform_post_id'], unique=False)
    op.create_index(op.f('ix_content_items_published_at'), 'content_items', ['published_at'], unique=False)
    op.create_index(op.f('ix_content_items_scheduled_for'), 'content_items', ['scheduled_for'], unique=False)
    op.create_index(op.f('ix_content_items_sentiment'), 'content_items', ['sentiment'], unique=False)
    op.create_index(op.f('ix_content_items_status'), 'content_items', ['status'], unique=False)
    op.create_index(op.f('ix_content_items_topic_category'), 'content_items', ['topic_category'], unique=False)

    # Create content_performance_snapshots table
    op.create_table('content_performance_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content_item_id', sa.String(), nullable=False),
        sa.Column('snapshot_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('likes_count', sa.Integer(), nullable=True),
        sa.Column('shares_count', sa.Integer(), nullable=True),
        sa.Column('comments_count', sa.Integer(), nullable=True),
        sa.Column('reach_count', sa.Integer(), nullable=True),
        sa.Column('click_count', sa.Integer(), nullable=True),
        sa.Column('engagement_rate', sa.Float(), nullable=True),
        sa.Column('likes_growth', sa.Integer(), nullable=True),
        sa.Column('shares_growth', sa.Integer(), nullable=True),
        sa.Column('comments_growth', sa.Integer(), nullable=True),
        sa.Column('reach_growth', sa.Integer(), nullable=True),
        sa.Column('engagement_velocity', sa.Float(), nullable=True),
        sa.Column('viral_coefficient', sa.Float(), nullable=True),
        sa.Column('platform_metrics', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_snapshot_content_time', 'content_performance_snapshots', ['content_item_id', 'snapshot_time'], unique=False)
    op.create_index(op.f('ix_content_performance_snapshots_id'), 'content_performance_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_content_performance_snapshots_snapshot_time'), 'content_performance_snapshots', ['snapshot_time'], unique=False)

    # Create content_templates table
    op.create_table('content_templates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('template_content', sa.Text(), nullable=False),
        sa.Column('prompt_template', sa.Text(), nullable=True),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=True),
        sa.Column('avg_performance', sa.Float(), nullable=True),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('constraints', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['content_categories.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_content_templates_platform'), 'content_templates', ['platform'], unique=False)

    # Insert default content categories
    op.execute("""
        INSERT INTO content_categories (name, slug, description, color, keywords) VALUES
        ('Technology', 'technology', 'Technology trends, AI, software development', '#3B82F6', 
         '["AI", "machine learning", "software", "development", "tech", "innovation"]'),
        ('Marketing', 'marketing', 'Marketing strategies, social media, advertising', '#10B981', 
         '["marketing", "social media", "advertising", "branding", "campaigns"]'),
        ('Business', 'business', 'Business insights, entrepreneurship, strategy', '#F59E0B', 
         '["business", "entrepreneurship", "strategy", "leadership", "growth"]'),
        ('Industry News', 'industry-news', 'Latest industry news and updates', '#EF4444', 
         '["news", "industry", "updates", "trends", "announcements"]'),
        ('Educational', 'educational', 'How-to guides, tutorials, educational content', '#8B5CF6', 
         '["tutorial", "how-to", "education", "guide", "learning"]'),
        ('Personal', 'personal', 'Personal insights, behind-the-scenes, company culture', '#F97316', 
         '["personal", "culture", "team", "behind-the-scenes", "insights"]')
    """)


def downgrade() -> None:
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('content_templates')
    op.drop_table('content_performance_snapshots')
    op.drop_table('content_items')
    op.drop_table('content_categories')