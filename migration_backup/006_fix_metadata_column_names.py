"""Fix metadata column names to match model definitions

Revision ID: 006_fix_metadata_columns
Revises: 005_add_milestones
Create Date: 2025-07-24 13:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006_fix_metadata_columns'
down_revision = '005_add_milestones'
branch_labels = None
depends_on = None


def upgrade():
    """Rename metadata columns to match model definitions"""
    
    # Rename metadata column in metrics table
    with op.batch_alter_table('metrics') as batch_op:
        batch_op.alter_column('metadata', new_column_name='metric_metadata')
    
    # Rename metadata column in goals table  
    with op.batch_alter_table('goals') as batch_op:
        batch_op.alter_column('metadata', new_column_name='goal_metadata')
    
    # Rename metadata column in memory_content table
    with op.batch_alter_table('memory_content') as batch_op:
        batch_op.alter_column('metadata', new_column_name='content_metadata')


def downgrade():
    """Revert metadata column names to original"""
    
    # Revert metadata column in memory_content table
    with op.batch_alter_table('memory_content') as batch_op:
        batch_op.alter_column('content_metadata', new_column_name='metadata')
    
    # Revert metadata column in goals table
    with op.batch_alter_table('goals') as batch_op:
        batch_op.alter_column('goal_metadata', new_column_name='metadata')
    
    # Revert metadata column in metrics table
    with op.batch_alter_table('metrics') as batch_op:
        batch_op.alter_column('metric_metadata', new_column_name='metadata')