"""Add comprehensive admin system

Revision ID: 013
Revises: 007
Create Date: 2025-08-19 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012_add_multi_tenant_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create admin_users table
    op.create_table('admin_users',
        sa.Column('id', sa.String(), nullable=False, default=lambda: str(uuid.uuid4())),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('role', sa.Enum('SUPER_ADMIN', 'ADMIN', 'MODERATOR', 'SUPPORT', name='adminrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), default=0),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('two_factor_enabled', sa.Boolean(), default=False),
        sa.Column('two_factor_secret', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('updated_by', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['admin_users.id'], ),
        sa.ForeignKeyConstraint(['updated_by'], ['admin_users.id'], )
    )
    op.create_index(op.f('ix_admin_users_id'), 'admin_users', ['id'], unique=False)
    op.create_index(op.f('ix_admin_users_email'), 'admin_users', ['email'], unique=True)
    op.create_index(op.f('ix_admin_users_username'), 'admin_users', ['username'], unique=True)

    # Create admin_sessions table
    op.create_table('admin_sessions',
        sa.Column('id', sa.String(), nullable=False, default=lambda: str(uuid.uuid4())),
        sa.Column('admin_user_id', sa.String(), nullable=False),
        sa.Column('session_token', sa.String(), nullable=False),
        sa.Column('refresh_token', sa.String(), nullable=False),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_activity', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('logout_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['admin_user_id'], ['admin_users.id'], )
    )
    op.create_index(op.f('ix_admin_sessions_id'), 'admin_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_admin_sessions_admin_user_id'), 'admin_sessions', ['admin_user_id'], unique=False)
    op.create_index(op.f('ix_admin_sessions_session_token'), 'admin_sessions', ['session_token'], unique=True)
    op.create_index(op.f('ix_admin_sessions_refresh_token'), 'admin_sessions', ['refresh_token'], unique=True)

    # Create user_management table
    op.create_table('user_management',
        sa.Column('id', sa.String(), nullable=False, default=lambda: str(uuid.uuid4())),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('api_key', sa.String(), nullable=True),
        sa.Column('api_secret', sa.String(), nullable=True),
        sa.Column('api_key_created_at', sa.DateTime(), nullable=True),
        sa.Column('api_key_last_used', sa.DateTime(), nullable=True),
        sa.Column('api_key_usage_count', sa.Integer(), default=0),
        sa.Column('monthly_request_limit', sa.Integer(), default=1000),
        sa.Column('monthly_requests_used', sa.Integer(), default=0),
        sa.Column('daily_request_limit', sa.Integer(), default=100),
        sa.Column('daily_requests_used', sa.Integer(), default=0),
        sa.Column('is_suspended', sa.Boolean(), default=False),
        sa.Column('suspension_reason', sa.Text(), nullable=True),
        sa.Column('suspended_at', sa.DateTime(), nullable=True),
        sa.Column('suspension_expires', sa.DateTime(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('verification_notes', sa.Text(), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('subscription_tier', sa.String(), default='free'),
        sa.Column('subscription_expires', sa.DateTime(), nullable=True),
        sa.Column('billing_customer_id', sa.String(), nullable=True),
        sa.Column('managed_by_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['managed_by_id'], ['admin_users.id'], )
    )
    op.create_index(op.f('ix_user_management_id'), 'user_management', ['id'], unique=False)
    op.create_index('idx_user_management_api_key', 'user_management', ['api_key'], unique=False)
    op.create_index('idx_user_management_user_id', 'user_management', ['user_id'], unique=True)
    op.create_index('idx_user_management_managed_by', 'user_management', ['managed_by_id'], unique=False)

    # Create admin_audit_logs table
    op.create_table('admin_audit_logs',
        sa.Column('id', sa.String(), nullable=False, default=lambda: str(uuid.uuid4())),
        sa.Column('admin_user_id', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('old_values', sa.JSON(), nullable=True),
        sa.Column('new_values', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(), nullable=True),
        sa.Column('success', sa.Boolean(), default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['admin_user_id'], ['admin_users.id'], )
    )
    op.create_index(op.f('ix_admin_audit_logs_id'), 'admin_audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_admin_audit_logs_admin_user_id'), 'admin_audit_logs', ['admin_user_id'], unique=False)
    op.create_index(op.f('ix_admin_audit_logs_action'), 'admin_audit_logs', ['action'], unique=False)
    op.create_index('idx_audit_admin_action', 'admin_audit_logs', ['admin_user_id', 'action'], unique=False)
    op.create_index('idx_audit_resource', 'admin_audit_logs', ['resource_type', 'resource_id'], unique=False)
    op.create_index('idx_audit_created_at', 'admin_audit_logs', ['created_at'], unique=False)

    # Create system_settings table
    op.create_table('system_settings',
        sa.Column('id', sa.String(), nullable=False, default=lambda: str(uuid.uuid4())),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.JSON(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('setting_type', sa.String(), nullable=False),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('is_readonly', sa.Boolean(), default=False),
        sa.Column('validation_rules', sa.JSON(), nullable=True),
        sa.Column('default_value', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('updated_by', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['admin_users.id'], ),
        sa.ForeignKeyConstraint(['updated_by'], ['admin_users.id'], )
    )
    op.create_index(op.f('ix_system_settings_id'), 'system_settings', ['id'], unique=False)
    op.create_index(op.f('ix_system_settings_key'), 'system_settings', ['key'], unique=True)

    # Create api_key_revocations table
    op.create_table('api_key_revocations',
        sa.Column('id', sa.String(), nullable=False, default=lambda: str(uuid.uuid4())),
        sa.Column('api_key', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('revoked_by', sa.String(), nullable=False),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['revoked_by'], ['admin_users.id'], )
    )
    op.create_index(op.f('ix_api_key_revocations_id'), 'api_key_revocations', ['id'], unique=False)
    op.create_index(op.f('ix_api_key_revocations_api_key'), 'api_key_revocations', ['api_key'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('api_key_revocations')
    op.drop_table('system_settings')
    op.drop_table('admin_audit_logs')
    op.drop_table('user_management')
    op.drop_table('admin_sessions')
    op.drop_table('admin_users')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS adminrole')