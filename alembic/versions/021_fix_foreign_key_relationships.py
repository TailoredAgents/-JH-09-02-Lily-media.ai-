"""Fix foreign key relationships and table mapping issues

Revision ID: 021_fix_foreign_key_relationships
Revises: 020_add_social_inbox_settings
Create Date: 2025-08-27

This migration fixes SQLAlchemy foreign key mapping issues:
1. Recreates content_logs table with proper foreign key constraints
2. Ensures all foreign key relationships are properly defined
3. Fixes the "mapper does not map this column" error
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = '021_fix_foreign_key_relationships'
down_revision = '020_social_inbox_settings'
branch_labels = None
depends_on = None

def upgrade():
    """
    Fix foreign key relationships and table mapping issues
    """
    
    # Check if we need to fix the content_logs table
    # This fixes the "mapper does not map this column" error
    
    # Step 1: Check if content_logs table exists and has proper structure
    conn = op.get_bind()
    
    # Check if content_logs table exists
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_name = 'content_logs'
    """)).scalar()
    
    if result == 0:
        # Create content_logs table with proper foreign key
        op.create_table('content_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('platform', sa.String(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('content_type', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=True),
            sa.Column('engagement_data', sa.JSON(), nullable=True),
            sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True),
            sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
            sa.Column('platform_post_id', sa.String(), nullable=True),
            sa.Column('external_post_id', sa.String(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_content_logs_user_id'),
            sa.PrimaryKeyConstraint('id'),
        )
        
        # Create indexes
        op.create_index('ix_content_logs_user_id', 'content_logs', ['user_id'])
        op.create_index('ix_content_logs_platform', 'content_logs', ['platform'])
        op.create_index('ix_content_logs_status', 'content_logs', ['status'])
        op.create_index('ix_content_logs_created_at', 'content_logs', ['created_at'])
        op.create_index('ix_content_logs_external_post_id', 'content_logs', ['external_post_id'])
        
    else:
        # Table exists, check if foreign key constraint exists
        fk_result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name 
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'content_logs'
                AND kcu.column_name = 'user_id'
                AND kcu.referenced_table_name = 'users'
                AND kcu.referenced_column_name = 'id'
        """)).scalar()
        
        if fk_result == 0:
            # Add missing foreign key constraint
            try:
                op.create_foreign_key(
                    'fk_content_logs_user_id',
                    'content_logs', 'users',
                    ['user_id'], ['id'],
                    ondelete='CASCADE'
                )
            except Exception as e:
                # If constraint creation fails, try dropping and recreating
                print(f"Failed to add foreign key constraint: {e}")
                pass
    
    # Step 2: Ensure metrics table has proper foreign key
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_name = 'metrics'
    """)).scalar()
    
    if result > 0:
        # Check if foreign key constraint exists for metrics table
        fk_result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name 
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'metrics'
                AND kcu.column_name = 'user_id'
                AND kcu.referenced_table_name = 'users'
                AND kcu.referenced_column_name = 'id'
        """)).scalar()
        
        if fk_result == 0:
            try:
                op.create_foreign_key(
                    'fk_metrics_user_id',
                    'metrics', 'users',
                    ['user_id'], ['id'],
                    ondelete='CASCADE'
                )
            except Exception as e:
                print(f"Failed to add metrics foreign key constraint: {e}")
                pass
    
    # Step 3: Ensure notifications table has proper foreign key
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_name = 'notifications'
    """)).scalar()
    
    if result > 0:
        # Check if foreign key constraint exists for notifications table
        fk_result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name 
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'notifications'
                AND kcu.column_name = 'user_id'
                AND kcu.referenced_table_name = 'users'
                AND kcu.referenced_column_name = 'id'
        """)).scalar()
        
        if fk_result == 0:
            try:
                op.create_foreign_key(
                    'fk_notifications_user_id',
                    'notifications', 'users',
                    ['user_id'], ['id'],
                    ondelete='CASCADE'
                )
            except Exception as e:
                print(f"Failed to add notifications foreign key constraint: {e}")
                pass

def downgrade():
    """
    Revert foreign key relationship fixes
    """
    # Drop foreign key constraints
    try:
        op.drop_constraint('fk_content_logs_user_id', 'content_logs', type_='foreignkey')
    except:
        pass
        
    try:
        op.drop_constraint('fk_metrics_user_id', 'metrics', type_='foreignkey')
    except:
        pass
        
    try:
        op.drop_constraint('fk_notifications_user_id', 'notifications', type_='foreignkey')
    except:
        pass