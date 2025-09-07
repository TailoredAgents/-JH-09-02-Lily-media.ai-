"""Add milestones table for goal tracking

Revision ID: 005_add_milestones
Revises: 373835cefaf9
Create Date: 2025-07-24 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = '005_add_milestones'
down_revision = '373835cefaf9'
branch_labels = None
depends_on = None


def upgrade():
    """Add milestones table"""
    
    # Create milestones table
    op.create_table(
        'milestones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('goal_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_value', sa.Float(), nullable=False),
        sa.Column('target_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('achieved', sa.Boolean(), nullable=True, default=False),
        sa.Column('achieved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=True),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on goal_id for performance
    op.create_index(op.f('ix_milestones_id'), 'milestones', ['id'], unique=False)
    op.create_index(op.f('ix_milestones_goal_id'), 'milestones', ['goal_id'], unique=False)


def downgrade():
    """Remove milestones table"""
    
    # Drop indexes
    op.drop_index(op.f('ix_milestones_goal_id'), table_name='milestones')
    op.drop_index(op.f('ix_milestones_id'), table_name='milestones')
    
    # Drop table
    op.drop_table('milestones')