"""Add performance indexes for high-traffic queries

Revision ID: 025_add_performance_indexes
Revises: 024_partner_oauth_connections_audit
Create Date: 2025-09-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '025_add_performance_indexes'
down_revision = '024_partner_oauth'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes for commonly queried columns"""
    
    # Content-related indexes
    op.create_index('idx_content_logs_platform_status', 'content_logs', ['platform', 'status'])
    op.create_index('idx_content_logs_user_created', 'content_logs', ['user_id', 'created_at'])
    
    # Metrics indexes for analytics queries
    op.create_index('idx_metrics_user_type_date', 'metrics', ['user_id', 'metric_type', 'date_recorded'])
    op.create_index('idx_metrics_platform_date', 'metrics', ['platform', 'date_recorded'])
    
    # User settings for brand voice queries
    op.create_index('idx_user_settings_voice_industry', 'user_settings', ['brand_voice', 'industry_type'])
    op.create_index('idx_user_settings_user_id', 'user_settings', ['user_id'])
    
    # Note: Indexes for content scheduling, drafts, and partner OAuth are handled
    # in their respective migrations to match actual table/column names.


def downgrade():
    """Remove performance indexes"""
    
    # Drop all indexes in reverse order
    op.drop_index('idx_audit_log_timestamp', 'partner_oauth_audit_log')
    op.drop_index('idx_audit_log_org_action', 'partner_oauth_audit_log')
    op.drop_index('idx_content_draft_verified', 'content_draft')
    op.drop_index('idx_content_draft_org_status', 'content_draft')
    op.drop_index('idx_partner_oauth_status', 'partner_oauth_connections')
    op.drop_index('idx_partner_oauth_org_provider', 'partner_oauth_connections')
    op.drop_index('idx_content_schedule_user_platform', 'content_schedule')
    op.drop_index('idx_content_schedule_status_time', 'content_schedule')
    op.drop_index('idx_user_settings_user_id', 'user_settings')
    op.drop_index('idx_user_settings_voice_industry', 'user_settings')
    op.drop_index('idx_metrics_platform_date', 'metrics')
    op.drop_index('idx_metrics_user_type_date', 'metrics')
    op.drop_index('idx_content_logs_user_created', 'content_logs')
    op.drop_index('idx_content_logs_platform_status', 'content_logs')
