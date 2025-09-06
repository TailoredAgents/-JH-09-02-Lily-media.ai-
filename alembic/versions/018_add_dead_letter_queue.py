"""Add Dead Letter Queue table for failed task tracking

Revision ID: 018_add_dead_letter_queue
Revises: 017_add_public_uuid_columns
Create Date: 2025-09-06 00:00:00.000000

P0.5 AUDIT FIX: Adds Dead Letter Queue (DLQ) table for comprehensive 
task failure tracking and recovery as required for production resilience.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '018_add_dead_letter_queue'
down_revision = '017_add_public_uuid_columns'
branch_labels = None
depends_on = None


def upgrade():
    """Add Dead Letter Queue table for failed task management"""
    
    # Create dead_letter_tasks table
    op.create_table('dead_letter_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('task_name', sa.String(), nullable=False),
        sa.Column('queue_name', sa.String(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('original_args', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('original_kwargs', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('failure_reason', sa.String(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('original_eta', sa.DateTime(), nullable=True),
        sa.Column('first_failure_at', sa.DateTime(), nullable=False),
        sa.Column('last_retry_at', sa.DateTime(), nullable=True),
        sa.Column('moved_to_dlq_at', sa.DateTime(), nullable=False),
        sa.Column('is_requeued', sa.Boolean(), nullable=True),
        sa.Column('requeued_at', sa.DateTime(), nullable=True),
        sa.Column('requires_manual_review', sa.Boolean(), nullable=True),
        sa.Column('task_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient querying
    op.create_index('ix_dead_letter_tasks_id', 'dead_letter_tasks', ['id'])
    op.create_index('ix_dead_letter_tasks_task_id', 'dead_letter_tasks', ['task_id'], unique=True)
    op.create_index('ix_dead_letter_tasks_task_name', 'dead_letter_tasks', ['task_name'])
    op.create_index('ix_dead_letter_tasks_queue_name', 'dead_letter_tasks', ['queue_name'])
    op.create_index('ix_dead_letter_tasks_organization_id', 'dead_letter_tasks', ['organization_id'])
    op.create_index('ix_dead_letter_tasks_user_id', 'dead_letter_tasks', ['user_id'])
    op.create_index('ix_dead_letter_tasks_failure_reason', 'dead_letter_tasks', ['failure_reason'])
    
    # Composite indexes for common query patterns
    op.create_index('ix_dead_letter_tasks_org_queue', 'dead_letter_tasks', ['organization_id', 'queue_name'])
    op.create_index('ix_dead_letter_tasks_reason_date', 'dead_letter_tasks', ['failure_reason', 'moved_to_dlq_at'])
    op.create_index('ix_dead_letter_tasks_manual_review', 'dead_letter_tasks', ['requires_manual_review', 'is_requeued'])
    
    print("✅ Dead Letter Queue table created with indexes for production resilience")


def downgrade():
    """Remove Dead Letter Queue table"""
    
    # Drop indexes first
    op.drop_index('ix_dead_letter_tasks_manual_review', table_name='dead_letter_tasks')
    op.drop_index('ix_dead_letter_tasks_reason_date', table_name='dead_letter_tasks')
    op.drop_index('ix_dead_letter_tasks_org_queue', table_name='dead_letter_tasks')
    op.drop_index('ix_dead_letter_tasks_failure_reason', table_name='dead_letter_tasks')
    op.drop_index('ix_dead_letter_tasks_user_id', table_name='dead_letter_tasks')
    op.drop_index('ix_dead_letter_tasks_organization_id', table_name='dead_letter_tasks')
    op.drop_index('ix_dead_letter_tasks_queue_name', table_name='dead_letter_tasks')
    op.drop_index('ix_dead_letter_tasks_task_name', table_name='dead_letter_tasks')
    op.drop_index('ix_dead_letter_tasks_task_id', table_name='dead_letter_tasks')
    op.drop_index('ix_dead_letter_tasks_id', table_name='dead_letter_tasks')
    
    # Drop the table
    op.drop_table('dead_letter_tasks')