"""Add organization_id to social_platform_connections table

This migration fixes a critical schema issue where social_platform_connections
was missing the organization_id column required for multi-tenant functionality.

Revision ID: 028_add_organization_id_to_social_platform_connections
Revises: 027_create_content_drafts_and_schedules
Create Date: 2025-09-03 14:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '028_add_organization_id_to_social_platform_connections'
down_revision = '027_create_content_drafts_and_schedules'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add organization_id column to social_platform_connections table"""
    
    # Add organization_id column
    op.add_column('social_platform_connections', 
        sa.Column('organization_id', 
                  postgresql.UUID(as_uuid=True), 
                  nullable=True)  # Start as nullable to allow data migration
    )
    
    # Add index for performance
    op.create_index('idx_social_platform_conn_org_id', 
                    'social_platform_connections', 
                    ['organization_id'])
    
    # For existing data, we need to handle the migration
    # Since this is a critical fix, we'll create a default organization if needed
    
    # First, check if organizations table exists and has data
    conn = op.get_bind()
    
    # Create a migration script to populate organization_id for existing records
    migration_sql = """
    -- Step 1: Create a default organization if none exists
    INSERT INTO organizations (id, name, display_name, is_active, created_at, updated_at)
    SELECT 
        gen_random_uuid(),
        'default-org',
        'Default Organization',
        true,
        NOW(),
        NOW()
    WHERE NOT EXISTS (SELECT 1 FROM organizations LIMIT 1);
    
    -- Step 2: Get the first organization ID (either existing or newly created)
    WITH default_org AS (
        SELECT id FROM organizations ORDER BY created_at ASC LIMIT 1
    )
    -- Step 3: Update all social_platform_connections to use the default organization
    UPDATE social_platform_connections 
    SET organization_id = (SELECT id FROM default_org)
    WHERE organization_id IS NULL;
    """
    
    # Execute the migration SQL
    conn.execute(sa.text(migration_sql))
    
    # Now make the column NOT NULL since all records have been migrated
    op.alter_column('social_platform_connections', 'organization_id',
                    nullable=False)
    
    # Add foreign key constraint
    op.create_foreign_key('fk_social_platform_conn_organization_id',
                         'social_platform_connections', 
                         'organizations',
                         ['organization_id'], 
                         ['id'],
                         ondelete='CASCADE')
    
    # Add unique constraint to prevent duplicate connections per platform per organization
    # First drop the old constraint if it exists
    try:
        op.drop_index('idx_social_conn_user_platform', 'social_platform_connections')
    except:
        pass  # Index might not exist
        
    # Create new unique index that includes organization_id
    op.create_index('idx_social_platform_conn_org_user_platform', 
                    'social_platform_connections',
                    ['organization_id', 'user_id', 'platform'],
                    unique=True)


def downgrade() -> None:
    """Remove organization_id column from social_platform_connections table"""
    
    # Drop the foreign key constraint
    op.drop_constraint('fk_social_platform_conn_organization_id', 
                      'social_platform_connections', 
                      type_='foreignkey')
    
    # Drop the unique index
    op.drop_index('idx_social_platform_conn_org_user_platform', 
                  'social_platform_connections')
    
    # Drop the organization_id index
    op.drop_index('idx_social_platform_conn_org_id', 
                  'social_platform_connections')
    
    # Recreate the old index
    op.create_index('idx_social_conn_user_platform',
                    'social_platform_connections',
                    ['user_id', 'platform'])
    
    # Drop the organization_id column
    op.drop_column('social_platform_connections', 'organization_id')