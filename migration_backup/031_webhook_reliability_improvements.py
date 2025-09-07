"""webhook reliability improvements

Revision ID: 031_webhook_reliability_improvements
Revises: 030
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '031_webhook_reliability_improvements'
down_revision = '030'
branch_labels = None
depends_on = None


def upgrade():
    """Add webhook reliability improvements: idempotency tracking and delivery monitoring"""
    
    # Create webhook_idempotency_records table
    op.create_table('webhook_idempotency_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('idempotency_key', sa.String(length=64), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('webhook_id', sa.String(length=255), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('processing_result', sa.String(length=50), nullable=False),
        sa.Column('processed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('event_summary', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for webhook_idempotency_records
    op.create_index('idx_webhook_idempotency_key', 'webhook_idempotency_records', ['idempotency_key'], unique=True)
    op.create_index('idx_webhook_idempotency_platform', 'webhook_idempotency_records', ['platform'])
    op.create_index('idx_webhook_idempotency_platform_event', 'webhook_idempotency_records', ['platform', 'event_type'])
    op.create_index('idx_webhook_idempotency_expires', 'webhook_idempotency_records', ['expires_at'])
    op.create_index('idx_webhook_idempotency_organization', 'webhook_idempotency_records', ['organization_id'])
    
    # Create webhook_delivery_tracking table
    op.create_table('webhook_delivery_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('webhook_id', sa.String(length=255), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('delivery_status', sa.String(length=50), nullable=False),
        sa.Column('attempt_count', sa.Integer(), default=0, nullable=False),
        sa.Column('max_retries', sa.Integer(), default=5, nullable=False),
        sa.Column('first_attempted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_attempted_at', sa.DateTime(), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('failure_reason', sa.String(length=100), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), default=0, nullable=False),
        sa.Column('total_processing_time_ms', sa.Integer(), default=0, nullable=False),
        sa.Column('avg_response_time_ms', sa.Integer(), nullable=True),
        sa.Column('event_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for webhook_delivery_tracking
    op.create_index('idx_webhook_delivery_webhook_id', 'webhook_delivery_tracking', ['webhook_id'])
    op.create_index('idx_webhook_delivery_status', 'webhook_delivery_tracking', ['delivery_status'])
    op.create_index('idx_webhook_delivery_next_retry', 'webhook_delivery_tracking', ['next_retry_at'])
    op.create_index('idx_webhook_delivery_platform_event', 'webhook_delivery_tracking', ['platform', 'event_type'])
    op.create_index('idx_webhook_delivery_organization', 'webhook_delivery_tracking', ['organization_id'])
    
    print("✅ Created webhook reliability tables: webhook_idempotency_records, webhook_delivery_tracking")


def downgrade():
    """Remove webhook reliability improvements"""
    
    # Drop webhook_delivery_tracking table and indexes
    op.drop_index('idx_webhook_delivery_organization', table_name='webhook_delivery_tracking')
    op.drop_index('idx_webhook_delivery_platform_event', table_name='webhook_delivery_tracking')
    op.drop_index('idx_webhook_delivery_next_retry', table_name='webhook_delivery_tracking')
    op.drop_index('idx_webhook_delivery_status', table_name='webhook_delivery_tracking')
    op.drop_index('idx_webhook_delivery_webhook_id', table_name='webhook_delivery_tracking')
    op.drop_table('webhook_delivery_tracking')
    
    # Drop webhook_idempotency_records table and indexes
    op.drop_index('idx_webhook_idempotency_organization', table_name='webhook_idempotency_records')
    op.drop_index('idx_webhook_idempotency_expires', table_name='webhook_idempotency_records')
    op.drop_index('idx_webhook_idempotency_platform_event', table_name='webhook_idempotency_records')
    op.drop_index('idx_webhook_idempotency_platform', table_name='webhook_idempotency_records')
    op.drop_index('idx_webhook_idempotency_key', table_name='webhook_idempotency_records')
    op.drop_table('webhook_idempotency_records')
    
    print("✅ Removed webhook reliability tables")