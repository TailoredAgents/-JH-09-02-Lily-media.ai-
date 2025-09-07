"""Add partner OAuth connections and audit tables

Revision ID: 024_partner_oauth
Revises: 023_add_user_id_to_memory_content_tables
Create Date: 2024-01-29 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '024_partner_oauth'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade():
    # Create social_connections table
    op.create_table('social_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('connection_name', sa.String(255), nullable=True),
        sa.Column('platform_account_id', sa.String(255), nullable=True),
        sa.Column('platform_username', sa.String(255), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),  # encrypted
        sa.Column('refresh_token', sa.Text(), nullable=True),  # encrypted
        sa.Column('page_access_token', sa.Text(), nullable=True),  # encrypted, Meta Pages only
        sa.Column('enc_version', sa.SmallInteger(), nullable=False, default=1),
        sa.Column('enc_kid', sa.String(50), nullable=False, default='default'),
        sa.Column('token_expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('scopes', postgresql.JSONB(), nullable=True),
        sa.Column('platform_metadata', postgresql.JSONB(), nullable=True),  # page_id, ig_business_id, since_id
        sa.Column('webhook_subscribed', sa.Boolean(), default=False),
        sa.Column('webhook_secret', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_checked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('organization_id', 'platform', 'platform_account_id', name='uq_org_platform_account')
    )
    
    # Create social_audit table
    op.create_table('social_audit',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),  # connect, disconnect, refresh, publish, webhook_verify
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('audit_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['connection_id'], ['social_connections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL')
    )
    
    # Create indexes
    op.create_index('idx_social_connections_org', 'social_connections', ['organization_id'])
    op.create_index('idx_social_connections_expires', 'social_connections', ['token_expires_at'])
    op.create_index(
        'idx_social_connections_active',
        'social_connections',
        ['organization_id', 'platform'],
        postgresql_where=sa.text('is_active = TRUE AND revoked_at IS NULL')
    )
    op.create_index('idx_social_audit_org', 'social_audit', ['organization_id'])
    op.create_index('idx_social_audit_connection', 'social_audit', ['connection_id'])
    op.create_index('idx_social_audit_created', 'social_audit', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_social_audit_created', 'social_audit')
    op.drop_index('idx_social_audit_connection', 'social_audit')
    op.drop_index('idx_social_audit_org', 'social_audit')
    op.drop_index('idx_social_connections_active', 'social_connections')
    op.drop_index('idx_social_connections_expires', 'social_connections')
    op.drop_index('idx_social_connections_org', 'social_connections')
    
    # Drop tables
    op.drop_table('social_audit')
    op.drop_table('social_connections')