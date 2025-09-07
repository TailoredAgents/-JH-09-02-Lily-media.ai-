"""Add idempotency unique constraint to content_schedules

Revision ID: 026_add_content_schedule_idempotency
Revises: 025_add_performance_indexes
Create Date: 2025-09-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '026_add_content_schedule_idempotency'
down_revision = '025_add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add supporting index for lookups
    op.create_index(
        'idx_content_schedules_content_hash_connection',
        'content_schedules',
        ['content_hash', 'connection_id'],
        unique=False
    )

    # Enforce idempotency at DB level
    op.create_unique_constraint(
        'uq_content_schedule_hash_connection',
        'content_schedules',
        ['content_hash', 'connection_id']
    )


def downgrade() -> None:
    # Remove unique constraint and index
    op.drop_constraint('uq_content_schedule_hash_connection', 'content_schedules', type_='unique')
    op.drop_index('idx_content_schedules_content_hash_connection', table_name='content_schedules')
