"""Create content_drafts and content_schedules tables if missing

Revision ID: 027_create_content_drafts_and_schedules
Revises: 025_add_performance_indexes
Create Date: 2025-09-02 00:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '027_create_content_drafts_and_schedules'
down_revision = '026_add_content_schedule_idempotency'
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    inspector = Inspector.from_engine(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()

    # Create content_drafts
    if not _table_exists(bind, 'content_drafts'):
        op.create_table(
            'content_drafts',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('connection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('social_connections.id', ondelete='CASCADE'), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('content_hash', sa.String(length=64), nullable=False),
            sa.Column('media_urls', postgresql.JSONB(), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='created'),
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
            sa.Column('verified_at', sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
        )
        op.create_index('idx_content_drafts_org_connection', 'content_drafts', ['organization_id', 'connection_id'])
        op.create_index('idx_content_drafts_hash', 'content_drafts', ['content_hash'])

    # Create content_schedules
    if not _table_exists(bind, 'content_schedules'):
        op.create_table(
            'content_schedules',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('connection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('social_connections.id', ondelete='CASCADE'), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('content_hash', sa.String(length=64), nullable=False),
            sa.Column('media_urls', postgresql.JSONB(), nullable=True),
            sa.Column('scheduled_for', sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='scheduled'),
            sa.Column('published_at', sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column('platform_post_id', sa.String(length=255), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('idempotency_key', sa.String(length=255), unique=True, nullable=True),
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
            sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        )
        op.create_index('idx_content_schedules_org_connection', 'content_schedules', ['organization_id', 'connection_id'])
        op.create_index('idx_content_schedules_scheduled', 'content_schedules', ['scheduled_for'])
        op.create_index('idx_content_schedules_status', 'content_schedules', ['status'])
        op.create_index('idx_content_schedules_idempotency', 'content_schedules', ['idempotency_key'])


def downgrade() -> None:
    # Drop in reverse order to satisfy dependencies
    bind = op.get_bind()
    if _table_exists(bind, 'content_schedules'):
        op.drop_index('idx_content_schedules_idempotency', table_name='content_schedules')
        op.drop_index('idx_content_schedules_status', table_name='content_schedules')
        op.drop_index('idx_content_schedules_scheduled', table_name='content_schedules')
        op.drop_index('idx_content_schedules_org_connection', table_name='content_schedules')
        op.drop_table('content_schedules')

    if _table_exists(bind, 'content_drafts'):
        op.drop_index('idx_content_drafts_hash', table_name='content_drafts')
        op.drop_index('idx_content_drafts_org_connection', table_name='content_drafts')
        op.drop_table('content_drafts')

