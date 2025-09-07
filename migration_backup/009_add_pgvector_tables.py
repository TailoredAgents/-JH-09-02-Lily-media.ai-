"""Add pgvector tables and enable extension

Revision ID: 009
Revises: 008
Create Date: 2025-01-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = '009'
down_revision = '008a_add_social_platform_connections'
branch_labels = None
depends_on = None

def upgrade():
    # Enable pgvector extension
    op.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
    
    # Create content_embeddings table
    op.create_table(
        'content_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content_id', sa.Integer(), nullable=False),
        sa.Column('content_text', sa.Text(), nullable=False),
        sa.Column('embedding', sa.String(), nullable=False),  # Will be vector(1536) in PostgreSQL
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('embedding_model', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.Index('ix_content_embeddings_user_id', 'user_id'),
        sa.Index('ix_content_embeddings_content_id', 'content_id'),
    )
    
    # Create memory_embeddings table
    op.create_table(
        'memory_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('memory_type', sa.String(100), nullable=False),
        sa.Column('embedding', sa.String(), nullable=False),  # Will be vector(1536) in PostgreSQL
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('embedding_model', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.Index('ix_memory_embeddings_user_id', 'user_id'),
        sa.Index('ix_memory_embeddings_type', 'memory_type'),
    )
    
    # For PostgreSQL, alter the embedding columns to be vector type
    try:
        # This will only work with PostgreSQL + pgvector
        op.execute(text('ALTER TABLE content_embeddings ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536);'))
        op.execute(text('ALTER TABLE memory_embeddings ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536);'))
        
        # Add HNSW indexes for fast vector similarity search
        op.execute(text('CREATE INDEX content_embeddings_embedding_idx ON content_embeddings USING hnsw (embedding vector_cosine_ops);'))
        op.execute(text('CREATE INDEX memory_embeddings_embedding_idx ON memory_embeddings USING hnsw (embedding vector_cosine_ops);'))
        
    except Exception as e:
        # If not PostgreSQL or pgvector not available, keep as text for development
        pass

def downgrade():
    # Drop tables
    op.drop_table('memory_embeddings')
    op.drop_table('content_embeddings')
    
    # Disable pgvector extension (optional - may be used by other tables)
    # op.execute(text('DROP EXTENSION IF EXISTS vector;'))