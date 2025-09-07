"""Add autonomous mode fields to user settings

Revision ID: 010
Revises: 009
Create Date: 2025-01-18

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None

def upgrade():
    # Add autonomous mode fields to user_settings table
    with op.batch_alter_table('user_settings') as batch_op:
        # Add enable_autonomous_mode column
        batch_op.add_column(sa.Column('enable_autonomous_mode', sa.Boolean(), nullable=False, server_default='false'))
        
        # Add timezone column for scheduling
        batch_op.add_column(sa.Column('timezone', sa.String(), nullable=False, server_default='UTC'))

def downgrade():
    # Remove the autonomous mode fields
    with op.batch_alter_table('user_settings') as batch_op:
        batch_op.drop_column('enable_autonomous_mode')
        batch_op.drop_column('timezone')