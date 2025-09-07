"""Add Phase 3A social inbox models

Revision ID: 019_phase3a_social_inbox
Revises: 2025_08_20_1420-f42f94c7a129
Create Date: 2025-08-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '023_phase3a_social_inbox'
down_revision = '022_add_user_id_to_memory_content_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create social_interactions table
    op.create_table(
        'social_interactions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('connection_id', sa.Integer(), nullable=True),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('interaction_type', sa.String(), nullable=False),
        sa.Column('external_id', sa.String(), nullable=False),
        sa.Column('parent_external_id', sa.String(), nullable=True),
        sa.Column('author_platform_id', sa.String(), nullable=False),
        sa.Column('author_username', sa.String(), nullable=False),
        sa.Column('author_display_name', sa.String(), nullable=True),
        sa.Column('author_profile_url', sa.String(), nullable=True),
        sa.Column('author_profile_image', sa.String(), nullable=True),
        sa.Column('author_verified', sa.Boolean(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('media_urls', sa.JSON(), nullable=True),
        sa.Column('hashtags', sa.JSON(), nullable=True),
        sa.Column('mentions', sa.JSON(), nullable=True),
        sa.Column('sentiment', sa.String(), nullable=True),
        sa.Column('intent', sa.String(), nullable=True),
        sa.Column('priority_score', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('response_strategy', sa.String(), nullable=True),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('platform_metadata', sa.JSON(), nullable=True),
        sa.Column('platform_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['connection_id'], ['social_platform_connections.id'], ),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_social_interaction_platform_type', 'social_interactions', ['platform', 'interaction_type'])
    op.create_index('idx_social_interaction_status_priority', 'social_interactions', ['status', 'priority_score'])
    op.create_index('idx_social_interaction_user_received', 'social_interactions', ['user_id', 'received_at'])
    op.create_index('idx_social_interaction_external', 'social_interactions', ['platform', 'external_id'])
    op.create_index(op.f('ix_social_interactions_user_id'), 'social_interactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_social_interactions_platform'), 'social_interactions', ['platform'], unique=False)
    op.create_index(op.f('ix_social_interactions_interaction_type'), 'social_interactions', ['interaction_type'], unique=False)
    op.create_index(op.f('ix_social_interactions_external_id'), 'social_interactions', ['external_id'], unique=False)
    op.create_index(op.f('ix_social_interactions_status'), 'social_interactions', ['status'], unique=False)

    # Create response_templates table
    op.create_table(
        'response_templates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('trigger_type', sa.String(), nullable=False),
        sa.Column('trigger_conditions', sa.JSON(), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('platforms', sa.JSON(), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('personality_style', sa.String(), nullable=True),
        sa.Column('tone', sa.String(), nullable=True),
        sa.Column('formality_level', sa.Integer(), nullable=True),
        sa.Column('platform_adaptations', sa.JSON(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('avg_response_time', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('auto_approve', sa.Boolean(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_response_template_user_active', 'response_templates', ['user_id', 'is_active'])
    op.create_index('idx_response_template_trigger', 'response_templates', ['trigger_type'])

    # Create interaction_responses table
    op.create_table(
        'interaction_responses',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('interaction_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('media_urls', sa.JSON(), nullable=True),
        sa.Column('response_type', sa.String(), nullable=True),
        sa.Column('template_id', sa.String(), nullable=True),
        sa.Column('ai_confidence_score', sa.Float(), nullable=True),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('platform_response_id', sa.String(), nullable=True),
        sa.Column('platform_url', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['interaction_id'], ['social_interactions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['response_templates.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_interaction_response_interaction', 'interaction_responses', ['interaction_id'])
    op.create_index('idx_interaction_response_status', 'interaction_responses', ['status'])
    op.create_index('idx_interaction_response_user_sent', 'interaction_responses', ['user_id', 'sent_at'])

    # Create company_knowledge table
    op.create_table(
        'company_knowledge',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('topic', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('summary', sa.String(), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('embedding_vector', sa.JSON(), nullable=True),
        sa.Column('context_type', sa.String(), nullable=True),
        sa.Column('platforms', sa.JSON(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effectiveness_score', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_company_knowledge_user_topic', 'company_knowledge', ['user_id', 'topic'])
    op.create_index('idx_company_knowledge_active', 'company_knowledge', ['is_active'])
    op.create_index('idx_company_knowledge_usage', 'company_knowledge', ['usage_count', 'last_used_at'])

    # Set default values for JSON columns
    op.execute("ALTER TABLE social_interactions ALTER COLUMN media_urls SET DEFAULT '[]'")
    op.execute("ALTER TABLE social_interactions ALTER COLUMN hashtags SET DEFAULT '[]'")
    op.execute("ALTER TABLE social_interactions ALTER COLUMN mentions SET DEFAULT '[]'")
    op.execute("ALTER TABLE social_interactions ALTER COLUMN platform_metadata SET DEFAULT '{}'")
    op.execute("ALTER TABLE social_interactions ALTER COLUMN sentiment SET DEFAULT 'neutral'")
    op.execute("ALTER TABLE social_interactions ALTER COLUMN priority_score SET DEFAULT 0.0")
    op.execute("ALTER TABLE social_interactions ALTER COLUMN status SET DEFAULT 'unread'")
    op.execute("ALTER TABLE social_interactions ALTER COLUMN response_strategy SET DEFAULT 'auto'")
    op.execute("ALTER TABLE social_interactions ALTER COLUMN author_verified SET DEFAULT false")

    op.execute("ALTER TABLE response_templates ALTER COLUMN trigger_conditions SET DEFAULT '{}'")
    op.execute("ALTER TABLE response_templates ALTER COLUMN keywords SET DEFAULT '[]'")
    op.execute("ALTER TABLE response_templates ALTER COLUMN platforms SET DEFAULT '[]'")
    op.execute("ALTER TABLE response_templates ALTER COLUMN variables SET DEFAULT '[]'")
    op.execute("ALTER TABLE response_templates ALTER COLUMN platform_adaptations SET DEFAULT '{}'")
    op.execute("ALTER TABLE response_templates ALTER COLUMN personality_style SET DEFAULT 'professional'")
    op.execute("ALTER TABLE response_templates ALTER COLUMN tone SET DEFAULT 'helpful'")
    op.execute("ALTER TABLE response_templates ALTER COLUMN formality_level SET DEFAULT 5")
    op.execute("ALTER TABLE response_templates ALTER COLUMN usage_count SET DEFAULT 0")
    op.execute("ALTER TABLE response_templates ALTER COLUMN success_rate SET DEFAULT 0.0")
    op.execute("ALTER TABLE response_templates ALTER COLUMN avg_response_time SET DEFAULT 0.0")
    op.execute("ALTER TABLE response_templates ALTER COLUMN is_active SET DEFAULT true")
    op.execute("ALTER TABLE response_templates ALTER COLUMN auto_approve SET DEFAULT false")
    op.execute("ALTER TABLE response_templates ALTER COLUMN priority SET DEFAULT 50")

    op.execute("ALTER TABLE interaction_responses ALTER COLUMN media_urls SET DEFAULT '[]'")
    op.execute("ALTER TABLE interaction_responses ALTER COLUMN response_type SET DEFAULT 'manual'")
    op.execute("ALTER TABLE interaction_responses ALTER COLUMN ai_confidence_score SET DEFAULT 0.0")
    op.execute("ALTER TABLE interaction_responses ALTER COLUMN status SET DEFAULT 'pending'")
    op.execute("ALTER TABLE interaction_responses ALTER COLUMN retry_count SET DEFAULT 0")

    op.execute("ALTER TABLE company_knowledge ALTER COLUMN keywords SET DEFAULT '[]'")
    op.execute("ALTER TABLE company_knowledge ALTER COLUMN tags SET DEFAULT '[]'")
    op.execute("ALTER TABLE company_knowledge ALTER COLUMN platforms SET DEFAULT '[\"facebook\", \"instagram\", \"twitter\"]'")
    op.execute("ALTER TABLE company_knowledge ALTER COLUMN context_type SET DEFAULT 'general'")
    op.execute("ALTER TABLE company_knowledge ALTER COLUMN confidence_score SET DEFAULT 1.0")
    op.execute("ALTER TABLE company_knowledge ALTER COLUMN usage_count SET DEFAULT 0")
    op.execute("ALTER TABLE company_knowledge ALTER COLUMN effectiveness_score SET DEFAULT 0.0")
    op.execute("ALTER TABLE company_knowledge ALTER COLUMN is_active SET DEFAULT true")
    op.execute("ALTER TABLE company_knowledge ALTER COLUMN requires_approval SET DEFAULT false")


def downgrade():
    op.drop_table('company_knowledge')
    op.drop_table('interaction_responses')
    op.drop_table('response_templates')
    op.drop_table('social_interactions')