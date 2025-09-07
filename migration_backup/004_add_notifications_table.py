"""Add notifications table for milestone tracking

Revision ID: 004_add_notifications
Revises: 003_enhanced_content_metadata
Create Date: 2025-07-23 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_notifications'
down_revision = '003_enhanced_content_metadata'
branch_labels = None
depends_on = None


def upgrade():
    """Add notifications table"""
    op.create_table('notifications',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(), nullable=False),
        sa.Column('priority', sa.String(), nullable=True),
        sa.Column('goal_id', sa.String(), nullable=True),
        sa.Column('content_id', sa.String(), nullable=True),
        sa.Column('workflow_id', sa.String(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('is_dismissed', sa.Boolean(), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('action_url', sa.String(), nullable=True),
        sa.Column('action_label', sa.String(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('idx_notification_user_read', 'notifications', ['user_id', 'is_read'])
    op.create_index('idx_notification_user_type', 'notifications', ['user_id', 'notification_type'])
    op.create_index('idx_notification_created', 'notifications', [sa.text('created_at DESC')])
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'])
    op.create_index(op.f('ix_notifications_notification_type'), 'notifications', ['notification_type'])
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'])
    op.create_index(op.f('ix_notifications_created_at'), 'notifications', ['created_at'])


def downgrade():
    """Remove notifications table"""
    op.drop_index(op.f('ix_notifications_created_at'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_is_read'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_notification_type'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index('idx_notification_created', table_name='notifications')
    op.drop_index('idx_notification_user_type', table_name='notifications')
    op.drop_index('idx_notification_user_read', table_name='notifications')
    op.drop_table('notifications')