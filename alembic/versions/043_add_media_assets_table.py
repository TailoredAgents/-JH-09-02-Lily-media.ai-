"""PW-SEC-ADD-001: Add secure media assets table with encryption support

Revision ID: 043_add_media_assets_table
Revises: 042_quotes_table
Create Date: 2025-09-09 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '043_add_media_assets_table'
down_revision: Union[str, None] = '042_quotes_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create media_assets table
    op.create_table('media_assets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('lead_id', sa.String(), nullable=True),
        sa.Column('storage_key', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('mime_type', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('sha256_hash', sa.String(64), nullable=False),
        sa.Column('encryption_key', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('upload_completed', sa.Boolean(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('asset_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('updated_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('storage_key')
    )
    
    # Create indexes for performance and multi-tenancy
    op.create_index('ix_media_assets_org_status', 'media_assets', ['organization_id', 'status'])
    op.create_index('ix_media_assets_org_lead', 'media_assets', ['organization_id', 'lead_id'])
    op.create_index('ix_media_assets_org_created', 'media_assets', ['organization_id', 'created_at'])
    op.create_index('ix_media_assets_upload_status', 'media_assets', ['upload_completed', 'status'])
    op.create_index('ix_media_assets_expires', 'media_assets', ['expires_at'])
    op.create_index('ix_media_assets_organization_id', 'media_assets', ['organization_id'])
    op.create_index('ix_media_assets_lead_id', 'media_assets', ['lead_id'])
    op.create_index('ix_media_assets_mime_type', 'media_assets', ['mime_type'])
    op.create_index('ix_media_assets_sha256_hash', 'media_assets', ['sha256_hash'])
    op.create_index('ix_media_assets_status', 'media_assets', ['status'])
    op.create_index('ix_media_assets_upload_completed', 'media_assets', ['upload_completed'])
    op.create_index('ix_media_assets_storage_key', 'media_assets', ['storage_key'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_media_assets_storage_key', table_name='media_assets')
    op.drop_index('ix_media_assets_upload_completed', table_name='media_assets')
    op.drop_index('ix_media_assets_status', table_name='media_assets')
    op.drop_index('ix_media_assets_sha256_hash', table_name='media_assets')
    op.drop_index('ix_media_assets_mime_type', table_name='media_assets')
    op.drop_index('ix_media_assets_lead_id', table_name='media_assets')
    op.drop_index('ix_media_assets_organization_id', table_name='media_assets')
    op.drop_index('ix_media_assets_expires', table_name='media_assets')
    op.drop_index('ix_media_assets_upload_status', table_name='media_assets')
    op.drop_index('ix_media_assets_org_created', table_name='media_assets')
    op.drop_index('ix_media_assets_org_lead', table_name='media_assets')
    op.drop_index('ix_media_assets_org_status', table_name='media_assets')
    
    # Drop table
    op.drop_table('media_assets')