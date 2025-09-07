"""Add two-factor authentication fields to users table

Revision ID: f42f94c7a129
Revises: 014
Create Date: 2025-08-20 14:20:38.303210

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f42f94c7a129'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 2FA columns to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('two_factor_enabled', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('two_factor_secret', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('two_factor_backup_codes', sa.JSON(), nullable=True))
    
    # Set default values for existing users
    op.execute("UPDATE users SET two_factor_enabled = 0 WHERE two_factor_enabled IS NULL")
    
    # Make two_factor_enabled non-nullable with default False
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('two_factor_enabled', nullable=False, server_default='0')


def downgrade() -> None:
    # Remove 2FA columns from users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('two_factor_backup_codes')
        batch_op.drop_column('two_factor_secret')
        batch_op.drop_column('two_factor_enabled')