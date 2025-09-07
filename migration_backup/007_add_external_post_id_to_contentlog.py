"""Add external_post_id to ContentLog for idempotency

Revision ID: 007_add_external_post_id
Revises: 006_fix_metadata_column_names
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_add_external_post_id'
down_revision = '006_fix_metadata_columns'
branch_labels = None
depends_on = None

def upgrade():
    # Add external_post_id column to content_logs table
    op.add_column('content_logs', sa.Column('external_post_id', sa.String(), nullable=True))
    
    # Add index for external_post_id
    op.create_index('ix_content_logs_external_post_id', 'content_logs', ['external_post_id'])

def downgrade():
    # Remove index and column
    op.drop_index('ix_content_logs_external_post_id', table_name='content_logs')
    op.drop_column('content_logs', 'external_post_id')