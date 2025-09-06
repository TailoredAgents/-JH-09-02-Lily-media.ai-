"""Add organization_id to content_logs for tenant isolation

Revision ID: 999_add_org_id_content_log
Revises: 016_remove_registration_keys
Create Date: 2025-09-06 00:00:00.000000

CRITICAL SECURITY FIX: Adds organization_id to content_logs table to prevent 
cross-tenant data leaks as identified in production readiness audit.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '999_add_org_id_content_log'
down_revision = '016_remove_registration_keys'
branch_labels = None
depends_on = None


def upgrade():
    """Add organization_id column to content_logs for tenant isolation"""
    
    # Step 1: Add nullable organization_id column
    op.add_column('content_logs', 
        sa.Column('organization_id', sa.Integer, sa.ForeignKey('organizations.id'), nullable=True)
    )
    
    # Step 2: Populate organization_id based on user's default organization
    # This is a best-effort migration - some content may need manual assignment
    connection = op.get_bind()
    
    # Update content_logs with user's default organization
    connection.execute(text("""
        UPDATE content_logs 
        SET organization_id = users.default_organization_id
        FROM users 
        WHERE content_logs.user_id = users.id 
        AND users.default_organization_id IS NOT NULL
    """))
    
    # For users without default org, try to get their first organization membership
    connection.execute(text("""
        UPDATE content_logs 
        SET organization_id = uor.organization_id
        FROM user_organization_roles uor
        WHERE content_logs.user_id = uor.user_id 
        AND content_logs.organization_id IS NULL
        AND uor.is_active = true
        AND content_logs.id IN (
            SELECT cl.id FROM content_logs cl
            JOIN user_organization_roles uor2 ON cl.user_id = uor2.user_id
            WHERE cl.organization_id IS NULL
            AND uor2.is_active = true
            GROUP BY cl.id
            HAVING COUNT(uor2.organization_id) = 1  -- Only if user has exactly one org
        )
    """))
    
    # Step 3: Log any orphaned content for manual review
    orphaned_count = connection.execute(text("""
        SELECT COUNT(*) FROM content_logs WHERE organization_id IS NULL
    """)).scalar()
    
    if orphaned_count > 0:
        print(f"WARNING: {orphaned_count} content_logs entries could not be assigned to organizations")
        print("These may need manual review and assignment")
        
        # Create a temporary table to track orphaned content
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS temp_orphaned_content_logs AS
            SELECT id, user_id, content, platform, created_at, 
                   'Migration 999 - needs manual org assignment' as note
            FROM content_logs 
            WHERE organization_id IS NULL
        """))
    
    # Step 4: Add index for performance
    op.create_index('ix_content_logs_organization_id', 'content_logs', ['organization_id'])
    
    # Step 5: Add constraint to make organization_id NOT NULL for new records
    # We keep it nullable for now to avoid breaking existing data
    print("SECURITY NOTE: organization_id is now tracked for content isolation")
    print("Consider making this field NOT NULL after reviewing orphaned content")


def downgrade():
    """Remove organization_id column from content_logs"""
    
    # Drop the index first
    op.drop_index('ix_content_logs_organization_id', table_name='content_logs')
    
    # Drop the column
    op.drop_column('content_logs', 'organization_id')
    
    # Drop temporary table if it exists
    connection = op.get_bind()
    connection.execute(text("DROP TABLE IF EXISTS temp_orphaned_content_logs"))