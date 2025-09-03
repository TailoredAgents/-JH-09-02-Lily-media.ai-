"""Add core missing tables: goals, organizations, and public_id columns

Revision ID: 001_add_core_missing_tables
Revises: baseline_existing_schema
Create Date: 2025-09-03 10:40:00.000000

This migration adds the most critical missing tables from the model definitions:
1. public_id columns to existing tables (users, content_logs)
2. Goals and milestone tracking tables  
3. Multi-tenant organization support tables
4. Social connections and audit tables

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers
revision = '001_add_core_missing_tables'
down_revision = 'baseline_existing_schema'
branch_labels = None
depends_on = None

def generate_uuid():
    """Generate a UUID string for default values"""
    return str(uuid.uuid4())

def upgrade():
    """Add missing core tables and public_id columns"""
    
    # 1. Add public_id columns to existing tables
    print("Adding public_id columns to existing tables...")
    
    # Add public_id to users table
    op.add_column('users', sa.Column('public_id', sa.String(length=36), nullable=True))
    op.create_index('ix_users_public_id', 'users', ['public_id'])
    op.create_unique_constraint('uq_users_public_id', 'users', ['public_id'])
    
    # Add public_id to content_logs table  
    op.add_column('content_logs', sa.Column('public_id', sa.String(length=36), nullable=True))
    op.create_index('ix_content_logs_public_id', 'content_logs', ['public_id'])
    op.create_unique_constraint('uq_content_logs_public_id', 'content_logs', ['public_id'])
    
    # 2. Add Organizations table (multi-tenant support)
    print("Creating organizations table...")
    op.create_table('organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('size', sa.String(length=50), nullable=True),
        sa.Column('timezone', sa.String(length=100), nullable=True, default='UTC'),
        sa.Column('billing_email', sa.String(length=255), nullable=True),
        sa.Column('subscription_plan', sa.String(length=50), nullable=True, default='free'),
        sa.Column('subscription_status', sa.String(length=50), nullable=True, default='active'),
        sa.Column('subscription_end_date', sa.DateTime(), nullable=True),
        sa.Column('max_users', sa.Integer(), nullable=True, default=5),
        sa.Column('max_social_accounts', sa.Integer(), nullable=True, default=3),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('public_id')
    )
    op.create_index('ix_organizations_created_at', 'organizations', ['created_at'])
    op.create_index('ix_organizations_name', 'organizations', ['name'])
    op.create_index('ix_organizations_public_id', 'organizations', ['public_id'])
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])
    op.create_index('ix_organizations_subscription_status', 'organizations', ['subscription_status'])
    
    # 3. Add Goals table 
    print("Creating goals table...")
    op.create_table('goals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('target_value', sa.Float(), nullable=True),
        sa.Column('current_value', sa.Float(), nullable=True, default=0.0),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('target_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, default='active'),
        sa.Column('priority', sa.String(length=20), nullable=True, default='medium'),
        sa.Column('is_public', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_id')
    )
    op.create_index('ix_goals_category', 'goals', ['category'])
    op.create_index('ix_goals_created_at', 'goals', ['created_at'])
    op.create_index('ix_goals_organization_id', 'goals', ['organization_id'])
    op.create_index('ix_goals_public_id', 'goals', ['public_id'])
    op.create_index('ix_goals_status', 'goals', ['status'])
    op.create_index('ix_goals_user_id', 'goals', ['user_id'])
    
    # 4. Add Goal Progress table
    print("Creating goal_progress table...")
    op.create_table('goal_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('goal_id', sa.Integer(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_goal_progress_created_at', 'goal_progress', ['created_at'])
    op.create_index('ix_goal_progress_goal_id', 'goal_progress', ['goal_id'])
    
    # 5. Add Milestones table
    print("Creating milestones table...")
    op.create_table('milestones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('goal_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_date', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_milestones_created_at', 'milestones', ['created_at'])
    op.create_index('ix_milestones_goal_id', 'milestones', ['goal_id'])
    op.create_index('ix_milestones_is_completed', 'milestones', ['is_completed'])
    
    # 6. Add Social Connections table (OAuth connections)
    print("Creating social_connections table...")
    op.create_table('social_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('platform_user_id', sa.String(length=255), nullable=False),
        sa.Column('platform_username', sa.String(length=255), nullable=True),
        sa.Column('platform_name', sa.String(length=255), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('scopes', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('profile_image_url', sa.String(length=512), nullable=True),
        sa.Column('follower_count', sa.Integer(), nullable=True),
        sa.Column('following_count', sa.Integer(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('platform', 'platform_user_id', name='uq_social_connections_platform_user'),
        sa.UniqueConstraint('public_id')
    )
    op.create_index('ix_social_connections_created_at', 'social_connections', ['created_at'])
    op.create_index('ix_social_connections_is_active', 'social_connections', ['is_active'])
    op.create_index('ix_social_connections_organization_id', 'social_connections', ['organization_id'])
    op.create_index('ix_social_connections_platform', 'social_connections', ['platform'])
    op.create_index('ix_social_connections_public_id', 'social_connections', ['public_id'])
    op.create_index('ix_social_connections_user_id', 'social_connections', ['user_id'])
    
    # 7. Add Social Audit table (audit trail)
    print("Creating social_audit table...")
    op.create_table('social_audit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('connection_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['connection_id'], ['social_connections.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_social_audit_action', 'social_audit', ['action'])
    op.create_index('ix_social_audit_created_at', 'social_audit', ['created_at'])
    op.create_index('ix_social_audit_organization_id', 'social_audit', ['organization_id'])
    op.create_index('ix_social_audit_platform', 'social_audit', ['platform'])
    op.create_index('ix_social_audit_resource_type', 'social_audit', ['resource_type'])
    op.create_index('ix_social_audit_user_id', 'social_audit', ['user_id'])
    
    print("✅ Core missing tables migration completed successfully!")

def downgrade():
    """Remove the added tables and columns"""
    
    # Remove tables in reverse order
    op.drop_table('social_audit')
    op.drop_table('social_connections')
    op.drop_table('milestones')
    op.drop_table('goal_progress')
    op.drop_table('goals')
    op.drop_table('organizations')
    
    # Remove public_id columns
    op.drop_constraint('uq_content_logs_public_id', 'content_logs')
    op.drop_index('ix_content_logs_public_id', 'content_logs')
    op.drop_column('content_logs', 'public_id')
    
    op.drop_constraint('uq_users_public_id', 'users')
    op.drop_index('ix_users_public_id', 'users')
    op.drop_column('users', 'public_id')