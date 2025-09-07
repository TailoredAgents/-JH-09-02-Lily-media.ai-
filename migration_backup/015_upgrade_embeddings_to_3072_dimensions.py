"""Upgrade embeddings to text-embedding-3-large (3072 dimensions)

Revision ID: 015_upgrade_embeddings
Revises: 014
Create Date: 2025-08-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = '015_upgrade_embeddings'
down_revision = '014'
branch_labels = None
depends_on = None

def upgrade():
    """
    Upgrade embedding tables to support text-embedding-3-large (3072 dimensions)
    
    This migration:
    1. Changes vector columns from 1536 to 3072 dimensions
    2. Clears existing embeddings (they'll be regenerated with new model)
    3. Updates embedding_model field to text-embedding-3-large
    """
    
    # Check if tables exist before attempting modifications
    conn = op.get_bind()
    
    # Check for content_embeddings table
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'content_embeddings'
        );
    """))
    content_embeddings_exists = result.scalar()
    
    # Check for memory_embeddings table
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'memory_embeddings'
        );
    """))
    memory_embeddings_exists = result.scalar()
    
    if content_embeddings_exists:
        print("Upgrading content_embeddings table to 3072 dimensions...")
        
        # Clear existing embeddings (they need to be regenerated with new model)
        op.execute(text("DELETE FROM content_embeddings;"))
        
        # Change vector dimension from 1536 to 3072
        op.execute(text("ALTER TABLE content_embeddings ALTER COLUMN embedding TYPE vector(3072);"))
        
        # Update default embedding model
        op.execute(text("""
            UPDATE content_embeddings 
            SET embedding_model = 'text-embedding-3-large' 
            WHERE embedding_model = 'text-embedding-ada-002' OR embedding_model IS NULL;
        """))
        
        print("✅ content_embeddings table upgraded successfully")
    else:
        print("⚠️  content_embeddings table not found, skipping...")
    
    if memory_embeddings_exists:
        print("Upgrading memory_embeddings table to 3072 dimensions...")
        
        # Clear existing embeddings (they need to be regenerated with new model)
        op.execute(text("DELETE FROM memory_embeddings;"))
        
        # Change vector dimension from 1536 to 3072
        op.execute(text("ALTER TABLE memory_embeddings ALTER COLUMN embedding TYPE vector(3072);"))
        
        # Update default embedding model
        op.execute(text("""
            UPDATE memory_embeddings 
            SET embedding_model = 'text-embedding-3-large' 
            WHERE embedding_model = 'text-embedding-ada-002' OR embedding_model IS NULL;
        """))
        
        print("✅ memory_embeddings table upgraded successfully")
    else:
        print("⚠️  memory_embeddings table not found, skipping...")
    
    # Check for other tables that might use embeddings
    result = conn.execute(text("""
        SELECT table_name, column_name 
        FROM information_schema.columns 
        WHERE column_name = 'embedding' 
        AND table_schema = 'public'
        AND table_name NOT IN ('content_embeddings', 'memory_embeddings');
    """))
    
    other_embedding_tables = result.fetchall()
    
    if other_embedding_tables:
        print(f"Found additional embedding columns in tables: {[row[0] for row in other_embedding_tables]}")
        print("These may need manual review for dimension compatibility.")
    
    print("🚀 Embedding dimension upgrade completed!")
    print("Note: All existing embeddings have been cleared and will be regenerated with text-embedding-3-large")

def downgrade():
    """
    Downgrade back to text-embedding-ada-002 (1536 dimensions)
    
    WARNING: This will clear all embeddings as they're incompatible between models
    """
    
    conn = op.get_bind()
    
    # Check for content_embeddings table
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'content_embeddings'
        );
    """))
    content_embeddings_exists = result.scalar()
    
    # Check for memory_embeddings table
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'memory_embeddings'
        );
    """))
    memory_embeddings_exists = result.scalar()
    
    if content_embeddings_exists:
        print("Downgrading content_embeddings table to 1536 dimensions...")
        
        # Clear existing embeddings
        op.execute(text("DELETE FROM content_embeddings;"))
        
        # Change vector dimension from 3072 to 1536
        op.execute(text("ALTER TABLE content_embeddings ALTER COLUMN embedding TYPE vector(1536);"))
        
        # Update embedding model back to ada-002
        op.execute(text("""
            UPDATE content_embeddings 
            SET embedding_model = 'text-embedding-ada-002' 
            WHERE embedding_model = 'text-embedding-3-large';
        """))
        
        print("✅ content_embeddings table downgraded successfully")
    
    if memory_embeddings_exists:
        print("Downgrading memory_embeddings table to 1536 dimensions...")
        
        # Clear existing embeddings
        op.execute(text("DELETE FROM memory_embeddings;"))
        
        # Change vector dimension from 3072 to 1536
        op.execute(text("ALTER TABLE memory_embeddings ALTER COLUMN embedding TYPE vector(1536);"))
        
        # Update embedding model back to ada-002
        op.execute(text("""
            UPDATE memory_embeddings 
            SET embedding_model = 'text-embedding-ada-002' 
            WHERE embedding_model = 'text-embedding-3-large';
        """))
        
        print("✅ memory_embeddings table downgraded successfully")
    
    print("⬇️  Embedding dimension downgrade completed!")
    print("Note: All existing embeddings have been cleared and will need to be regenerated with text-embedding-ada-002")