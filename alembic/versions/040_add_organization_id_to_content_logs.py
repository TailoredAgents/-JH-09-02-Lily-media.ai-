"""Add organization_id to content_logs and make it NOT NULL

Revision ID: 040_add_organization_id_to_content_logs
Revises: 039_webhook_reliability_improvements
Create Date: 2025-09-08

P1-1b: Make content_logs.organization_id NOT NULL
Critical multi-tenancy security fix - ensures proper data isolation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '040_add_organization_id_to_content_logs'
down_revision = '039_webhook_reliability_improvements'
branch_labels = None
depends_on = None


def upgrade():
    """Add organization_id column to content_logs table and populate it"""
    
    # Check if content_logs table exists
    conn = op.get_bind()
    table_exists = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'content_logs'
        );
    """)).scalar()
    
    if not table_exists:
        print("content_logs table does not exist - skipping migration")
        return
    
    # Check if organization_id column already exists
    column_exists = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'content_logs'
            AND column_name = 'organization_id'
        );
    """)).scalar()
    
    if column_exists:
        print("organization_id column already exists in content_logs")
        
        # Check if it's nullable and needs to be made NOT NULL
        is_nullable = conn.execute(text("""
            SELECT is_nullable 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'content_logs'
            AND column_name = 'organization_id';
        """)).scalar()
        
        if is_nullable == 'YES':
            print("Making organization_id NOT NULL...")
            
            # First, ensure all existing records have organization_id populated
            # Get organization_id from user's default organization
            conn.execute(text("""
                UPDATE content_logs 
                SET organization_id = users.default_organization_id
                FROM users 
                WHERE content_logs.user_id = users.id 
                AND content_logs.organization_id IS NULL
                AND users.default_organization_id IS NOT NULL;
            """))
            
            # For any remaining records without organization_id, create personal orgs
            remaining_count = conn.execute(text("""
                SELECT COUNT(*) FROM content_logs WHERE organization_id IS NULL;
            """)).scalar()
            
            if remaining_count > 0:
                print(f"Creating personal organizations for {remaining_count} content logs...")
                
                # Create personal organizations for users without them
                conn.execute(text("""
                    WITH user_orgs AS (
                        INSERT INTO organizations (id, name, slug, organization_type, created_at)
                        SELECT 
                            gen_random_uuid(),
                            COALESCE(users.full_name, users.username) || '''s Organization',
                            LOWER(REGEXP_REPLACE(COALESCE(users.username, users.email), '[^a-zA-Z0-9]', '-', 'g')),
                            'personal',
                            NOW()
                        FROM users
                        WHERE users.id IN (
                            SELECT DISTINCT user_id FROM content_logs 
                            WHERE organization_id IS NULL
                        )
                        AND users.default_organization_id IS NULL
                        ON CONFLICT (slug) DO NOTHING
                        RETURNING id, (SELECT id FROM users WHERE users.id IN (
                            SELECT DISTINCT user_id FROM content_logs WHERE organization_id IS NULL
                        ) LIMIT 1) as user_id
                    )
                    UPDATE users 
                    SET default_organization_id = user_orgs.id
                    FROM user_orgs
                    WHERE users.id = user_orgs.user_id;
                """))
                
                # Now update content_logs with the new organization_id
                conn.execute(text("""
                    UPDATE content_logs 
                    SET organization_id = users.default_organization_id
                    FROM users 
                    WHERE content_logs.user_id = users.id 
                    AND content_logs.organization_id IS NULL;
                """))
            
            # Finally, make the column NOT NULL
            op.alter_column('content_logs', 'organization_id',
                           existing_type=postgresql.UUID(),
                           nullable=False)
            
            print("✅ organization_id column is now NOT NULL")
        else:
            print("✅ organization_id column is already NOT NULL")
    else:
        print("Adding organization_id column to content_logs...")
        
        # Add the column as nullable first
        op.add_column('content_logs', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True))
        
        # Add foreign key constraint
        op.create_foreign_key('fk_content_logs_organization_id', 'content_logs', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
        
        # Populate the column with organization data
        print("Populating organization_id from user relationships...")
        
        # First pass: Set from user's default organization
        conn.execute(text("""
            UPDATE content_logs 
            SET organization_id = users.default_organization_id
            FROM users 
            WHERE content_logs.user_id = users.id 
            AND users.default_organization_id IS NOT NULL;
        """))
        
        # Second pass: Create personal organizations for users without them
        users_without_org = conn.execute(text("""
            SELECT COUNT(DISTINCT cl.user_id) 
            FROM content_logs cl
            JOIN users u ON cl.user_id = u.id
            WHERE cl.organization_id IS NULL
            AND u.default_organization_id IS NULL;
        """)).scalar()
        
        if users_without_org > 0:
            print(f"Creating personal organizations for {users_without_org} users...")
            
            # Create personal organizations for users who don't have them
            conn.execute(text("""
                WITH new_orgs AS (
                    INSERT INTO organizations (id, name, slug, organization_type, created_at)
                    SELECT 
                        gen_random_uuid(),
                        COALESCE(users.full_name, users.username) || '''s Organization',
                        LOWER(REGEXP_REPLACE(COALESCE(users.username, users.email), '[^a-zA-Z0-9]', '-', 'g')) || '-' || users.id::text,
                        'personal',
                        NOW()
                    FROM users
                    WHERE users.id IN (
                        SELECT DISTINCT cl.user_id 
                        FROM content_logs cl
                        WHERE cl.organization_id IS NULL
                    )
                    AND users.default_organization_id IS NULL
                    RETURNING id, name
                ),
                user_org_mapping AS (
                    SELECT 
                        u.id as user_id,
                        no.id as org_id
                    FROM users u
                    CROSS JOIN new_orgs no
                    WHERE u.id IN (
                        SELECT DISTINCT cl.user_id 
                        FROM content_logs cl
                        WHERE cl.organization_id IS NULL
                    )
                    AND u.default_organization_id IS NULL
                    AND no.name = COALESCE(u.full_name, u.username) || '''s Organization'
                )
                UPDATE users 
                SET default_organization_id = uom.org_id
                FROM user_org_mapping uom
                WHERE users.id = uom.user_id;
            """))
            
            # Update content_logs with new organization_id
            conn.execute(text("""
                UPDATE content_logs 
                SET organization_id = users.default_organization_id
                FROM users 
                WHERE content_logs.user_id = users.id 
                AND content_logs.organization_id IS NULL;
            """))
        
        # Check if any records still lack organization_id
        remaining_nulls = conn.execute(text("""
            SELECT COUNT(*) FROM content_logs WHERE organization_id IS NULL;
        """)).scalar()
        
        if remaining_nulls > 0:
            print(f"WARNING: {remaining_nulls} content_logs records still have NULL organization_id")
            
            # Create a fallback "system" organization for orphaned records
            system_org_result = conn.execute(text("""
                INSERT INTO organizations (id, name, slug, organization_type, created_at)
                VALUES (gen_random_uuid(), 'System Organization', 'system-fallback', 'system', NOW())
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                RETURNING id;
            """))
            system_org_id = system_org_result.scalar()
            
            # Assign orphaned records to system organization
            conn.execute(text("""
                UPDATE content_logs 
                SET organization_id = :system_org_id 
                WHERE organization_id IS NULL;
            """), {"system_org_id": system_org_id})
            
            print(f"Assigned {remaining_nulls} orphaned records to system organization")
        
        # Finally, make the column NOT NULL
        op.alter_column('content_logs', 'organization_id',
                       existing_type=postgresql.UUID(),
                       nullable=False)
        
        print("✅ organization_id column added and set to NOT NULL")
    
    # Create index for performance
    try:
        op.create_index('ix_content_logs_organization_id', 'content_logs', ['organization_id'])
        print("✅ Created index on content_logs.organization_id")
    except Exception as e:
        if "already exists" not in str(e):
            print(f"Warning: Could not create index: {e}")
    
    # Create compound index for common query patterns
    try:
        op.create_index('ix_content_logs_org_user', 'content_logs', ['organization_id', 'user_id'])
        print("✅ Created compound index on content_logs(organization_id, user_id)")
    except Exception as e:
        if "already exists" not in str(e):
            print(f"Warning: Could not create compound index: {e}")


def downgrade():
    """Remove organization_id column from content_logs"""
    
    # Drop indexes first
    try:
        op.drop_index('ix_content_logs_org_user', table_name='content_logs')
        op.drop_index('ix_content_logs_organization_id', table_name='content_logs')
    except Exception:
        pass  # Indexes might not exist
    
    # Drop foreign key constraint
    try:
        op.drop_constraint('fk_content_logs_organization_id', 'content_logs', type_='foreignkey')
    except Exception:
        pass  # Constraint might not exist
    
    # Drop column
    op.drop_column('content_logs', 'organization_id')