"""Add Memory table and vector_id fields

Revision ID: 373835cefaf9
Revises: 004_add_notifications
Create Date: 2025-07-23 19:03:53.041354

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '373835cefaf9'
down_revision = '004_add_notifications'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create Memory table
    op.create_table('memories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('memory_type', sa.String(), nullable=False),
        sa.Column('vector_id', sa.String(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('memory_metadata', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=True),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memories_id'), 'memories', ['id'], unique=False)
    op.create_index(op.f('ix_memories_vector_id'), 'memories', ['vector_id'], unique=False)
    
    # Create Content table
    op.create_table('content',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('engagement_data', sa.JSON(), nullable=True),
        sa.Column('performance_score', sa.Float(), nullable=True),
        sa.Column('ai_model', sa.String(), nullable=True),
        sa.Column('prompt_used', sa.Text(), nullable=True),
        sa.Column('generation_params', sa.JSON(), nullable=True),
        sa.Column('memory_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['memory_id'], ['memories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_content_id'), 'content', ['id'], unique=False)


def downgrade() -> None:
    # Drop Content table
    op.drop_index(op.f('ix_content_id'), table_name='content')
    op.drop_table('content')
    
    # Drop Memory table
    op.drop_index(op.f('ix_memories_vector_id'), table_name='memories')
    op.drop_index(op.f('ix_memories_id'), table_name='memories')
    op.drop_table('memories')