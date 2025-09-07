"""Add user_id columns to memory and content tables for performance

Revision ID: 023
Revises: f42f94c7a129
Create Date: 2025-08-28 (Performance Fix)

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '023'
down_revision = 'f42f94c7a129'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add user_id columns to memory and content tables for proper user filtering"""
    
    # Add user_id to memories table
    try:
        op.add_column('memories', sa.Column('user_id', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_memories_user_id', 'memories', 'users', ['user_id'], ['id'])
        op.create_index('ix_memories_user_id', 'memories', ['user_id'])
        print("✅ Added user_id to memories table")
    except Exception as e:
        print(f"⚠️ memories table user_id: {e}")
    
    # Add user_id to content table
    try:
        op.add_column('content', sa.Column('user_id', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_content_user_id', 'content', 'users', ['user_id'], ['id'])
        op.create_index('ix_content_user_id', 'content', ['user_id'])
        print("✅ Added user_id to content table")
    except Exception as e:
        print(f"⚠️ content table user_id: {e}")
    
    # Add indexes for performance on commonly queried columns
    try:
        # Index on memories.created_at for recent memory queries
        op.create_index('ix_memories_created_at', 'memories', ['created_at'])
        
        # Index on content.created_at for recent content queries  
        op.create_index('ix_content_created_at', 'content', ['created_at'])
        
        # Composite index for user + created_at queries (most common pattern)
        op.create_index('ix_memories_user_created', 'memories', ['user_id', 'created_at'])
        op.create_index('ix_content_user_created', 'content', ['user_id', 'created_at'])
        
        print("✅ Added performance indexes")
    except Exception as e:
        print(f"⚠️ indexes: {e}")


def downgrade() -> None:
    """Remove user_id columns and indexes"""
    
    # Drop composite indexes
    try:
        op.drop_index('ix_content_user_created', table_name='content')
        op.drop_index('ix_memories_user_created', table_name='memories')
        op.drop_index('ix_content_created_at', table_name='content')
        op.drop_index('ix_memories_created_at', table_name='memories')
    except Exception as e:
        print(f"⚠️ dropping indexes: {e}")
    
    # Drop foreign keys and columns
    try:
        op.drop_index('ix_content_user_id', table_name='content')
        op.drop_constraint('fk_content_user_id', 'content', type_='foreignkey')
        op.drop_column('content', 'user_id')
    except Exception as e:
        print(f"⚠️ dropping content user_id: {e}")
    
    try:
        op.drop_index('ix_memories_user_id', table_name='memories')
        op.drop_constraint('fk_memories_user_id', 'memories', type_='foreignkey')
        op.drop_column('memories', 'user_id')
    except Exception as e:
        print(f"⚠️ dropping memories user_id: {e}")