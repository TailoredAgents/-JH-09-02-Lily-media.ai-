"""Add FastAPI Users columns

Revision ID: 008
Revises: 007
Create Date: 2025-01-18

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '008'
down_revision = '007_add_external_post_id'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to users table for FastAPI Users compatibility
    with op.batch_alter_table('users') as batch_op:
        # Add is_superuser column if it doesn't exist
        try:
            batch_op.add_column(sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'))
        except:
            pass  # Column might already exist
        
        # Add is_verified column if it doesn't exist
        try:
            batch_op.add_column(sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))
        except:
            pass  # Column might already exist

def downgrade():
    # Remove the columns
    with op.batch_alter_table('users') as batch_op:
        try:
            batch_op.drop_column('is_superuser')
        except:
            pass
        try:
            batch_op.drop_column('is_verified')
        except:
            pass