"""Add multi-tenant schema with organizations, teams and RBAC

Revision ID: 012_add_multi_tenant_schema
Revises: 011_add_audit_logs_table
Create Date: 2025-08-18 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012_add_multi_tenant_schema'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create organizations table
    op.create_table('organizations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('plan_type', sa.String(), nullable=True),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('max_teams', sa.Integer(), nullable=True),
        sa.Column('max_social_accounts', sa.Integer(), nullable=True),
        sa.Column('subscription_status', sa.String(), nullable=True),
        sa.Column('billing_email', sa.String(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('features_enabled', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)

    # Create teams table
    op.create_table('teams',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('default_role', sa.String(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_org_team_name')
    )

    # Create roles table
    op.create_table('roles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('is_system_role', sa.Boolean(), nullable=True),
        sa.Column('color', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)

    # Create permissions table
    op.create_table('permissions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('resource', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('is_system_permission', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resource', 'action', name='uq_resource_action')
    )
    op.create_index(op.f('ix_permissions_name'), 'permissions', ['name'], unique=True)

    # Create role_permissions association table
    op.create_table('role_permissions',
        sa.Column('role_id', sa.String(), nullable=False),
        sa.Column('permission_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    # Create user_teams association table
    op.create_table('user_teams',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'team_id')
    )

    # Create organization_invitations table
    op.create_table('organization_invitations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('team_id', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invited_by_id', sa.Integer(), nullable=False),
        sa.Column('invited_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['invited_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organization_invitations_token'), 'organization_invitations', ['token'], unique=True)

    # Create user_organization_roles table
    op.create_table('user_organization_roles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('role_id', sa.String(), nullable=False),
        sa.Column('assigned_by_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'organization_id', name='uq_user_organization')
    )

    # Add default_organization_id column to users table
    op.add_column('users', sa.Column('default_organization_id', sa.String(), nullable=True))
    op.create_foreign_key('fk_users_default_organization', 'users', 'organizations', ['default_organization_id'], ['id'])

    # Insert default system roles
    op.execute("""
        INSERT INTO roles (id, name, display_name, description, level, is_system_role, color) VALUES
        ('super_admin', 'super_admin', 'Super Admin', 'Full system access across all organizations', 100, true, '#DC2626'),
        ('org_owner', 'org_owner', 'Organization Owner', 'Full access within organization', 90, true, '#7C3AED'),
        ('admin', 'admin', 'Administrator', 'Administrative access within organization', 80, true, '#059669'),
        ('manager', 'manager', 'Manager', 'Team management and content approval', 70, true, '#0EA5E9'),
        ('member', 'member', 'Member', 'Standard user access', 50, true, '#6B7280'),
        ('viewer', 'viewer', 'Viewer', 'Read-only access', 30, true, '#9CA3AF')
    """)

    # Insert default system permissions
    op.execute("""
        INSERT INTO permissions (id, name, display_name, description, resource, action, is_system_permission) VALUES
        ('users_create', 'users.create', 'Create Users', 'Create new user accounts', 'users', 'create', true),
        ('users_read', 'users.read', 'View Users', 'View user information', 'users', 'read', true),
        ('users_update', 'users.update', 'Update Users', 'Update user information', 'users', 'update', true),
        ('users_delete', 'users.delete', 'Delete Users', 'Delete user accounts', 'users', 'delete', true),
        ('organizations_create', 'organizations.create', 'Create Organizations', 'Create new organizations', 'organizations', 'create', true),
        ('organizations_read', 'organizations.read', 'View Organizations', 'View organization information', 'organizations', 'read', true),
        ('organizations_update', 'organizations.update', 'Update Organizations', 'Update organization settings', 'organizations', 'update', true),
        ('organizations_delete', 'organizations.delete', 'Delete Organizations', 'Delete organizations', 'organizations', 'delete', true),
        ('teams_create', 'teams.create', 'Create Teams', 'Create new teams', 'teams', 'create', true),
        ('teams_read', 'teams.read', 'View Teams', 'View team information', 'teams', 'read', true),
        ('teams_update', 'teams.update', 'Update Teams', 'Update team settings', 'teams', 'update', true),
        ('teams_delete', 'teams.delete', 'Delete Teams', 'Delete teams', 'teams', 'delete', true),
        ('content_create', 'content.create', 'Create Content', 'Create new content', 'content', 'create', true),
        ('content_read', 'content.read', 'View Content', 'View content', 'content', 'read', true),
        ('content_update', 'content.update', 'Update Content', 'Edit content', 'content', 'update', true),
        ('content_delete', 'content.delete', 'Delete Content', 'Delete content', 'content', 'delete', true),
        ('content_publish', 'content.publish', 'Publish Content', 'Publish content to social platforms', 'content', 'publish', true),
        ('social_accounts_connect', 'social_accounts.connect', 'Connect Social Accounts', 'Connect social media accounts', 'social_accounts', 'connect', true),
        ('social_accounts_read', 'social_accounts.read', 'View Social Accounts', 'View connected social accounts', 'social_accounts', 'read', true),
        ('social_accounts_disconnect', 'social_accounts.disconnect', 'Disconnect Social Accounts', 'Disconnect social media accounts', 'social_accounts', 'disconnect', true),
        ('analytics_read', 'analytics.read', 'View Analytics', 'View performance analytics', 'analytics', 'read', true),
        ('settings_read', 'settings.read', 'View Settings', 'View organization/team settings', 'settings', 'read', true),
        ('settings_update', 'settings.update', 'Update Settings', 'Update organization/team settings', 'settings', 'update', true)
    """)

    # Assign permissions to roles
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id) 
        SELECT 'super_admin', id FROM permissions WHERE is_system_permission = true
    """)

    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id) VALUES
        ('org_owner', 'users_create'), ('org_owner', 'users_read'), ('org_owner', 'users_update'), ('org_owner', 'users_delete'),
        ('org_owner', 'organizations_read'), ('org_owner', 'organizations_update'),
        ('org_owner', 'teams_create'), ('org_owner', 'teams_read'), ('org_owner', 'teams_update'), ('org_owner', 'teams_delete'),
        ('org_owner', 'content_create'), ('org_owner', 'content_read'), ('org_owner', 'content_update'), ('org_owner', 'content_delete'), ('org_owner', 'content_publish'),
        ('org_owner', 'social_accounts_connect'), ('org_owner', 'social_accounts_read'), ('org_owner', 'social_accounts_disconnect'),
        ('org_owner', 'analytics_read'), ('org_owner', 'settings_read'), ('org_owner', 'settings_update'),
        
        ('admin', 'users_create'), ('admin', 'users_read'), ('admin', 'users_update'),
        ('admin', 'organizations_read'), ('admin', 'teams_read'), ('admin', 'teams_update'),
        ('admin', 'content_create'), ('admin', 'content_read'), ('admin', 'content_update'), ('admin', 'content_delete'), ('admin', 'content_publish'),
        ('admin', 'social_accounts_connect'), ('admin', 'social_accounts_read'), ('admin', 'social_accounts_disconnect'),
        ('admin', 'analytics_read'), ('admin', 'settings_read'), ('admin', 'settings_update'),
        
        ('manager', 'users_read'), ('manager', 'organizations_read'), ('manager', 'teams_read'),
        ('manager', 'content_create'), ('manager', 'content_read'), ('manager', 'content_update'), ('manager', 'content_publish'),
        ('manager', 'social_accounts_read'), ('manager', 'analytics_read'), ('manager', 'settings_read'),
        
        ('member', 'users_read'), ('member', 'organizations_read'), ('member', 'teams_read'),
        ('member', 'content_create'), ('member', 'content_read'), ('member', 'content_update'),
        ('member', 'social_accounts_connect'), ('member', 'social_accounts_read'), ('member', 'analytics_read'), ('member', 'settings_read'),
        
        ('viewer', 'users_read'), ('viewer', 'organizations_read'), ('viewer', 'teams_read'),
        ('viewer', 'content_read'), ('viewer', 'social_accounts_read'), ('viewer', 'analytics_read'), ('viewer', 'settings_read')
    """)


def downgrade() -> None:
    # Drop foreign key constraint from users table first
    op.drop_constraint('fk_users_default_organization', 'users', type_='foreignkey')
    op.drop_column('users', 'default_organization_id')
    
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('user_organization_roles')
    op.drop_table('organization_invitations')
    op.drop_table('user_teams')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('teams')
    op.drop_table('organizations')