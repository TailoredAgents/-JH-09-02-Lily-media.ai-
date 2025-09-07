"""Add user credentials and platform configuration tables

Revision ID: 014
Revises: 013
Create Date: 2025-08-19 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create platform_configs table
    op.create_table('platform_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('platform_name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('requires_oauth', sa.Boolean(), nullable=True, default=False),
        sa.Column('requires_app_credentials', sa.Boolean(), nullable=True, default=False),
        sa.Column('required_fields', sa.JSON(), nullable=False),
        sa.Column('optional_fields', sa.JSON(), nullable=True, default={}),
        sa.Column('oauth_config', sa.JSON(), nullable=True),
        sa.Column('api_base_url', sa.String(), nullable=True),
        sa.Column('api_version', sa.String(), nullable=True),
        sa.Column('rate_limits', sa.JSON(), nullable=True),
        sa.Column('setup_instructions', sa.Text(), nullable=True),
        sa.Column('help_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_configs_id'), 'platform_configs', ['id'], unique=False)
    op.create_index(op.f('ix_platform_configs_platform_name'), 'platform_configs', ['platform_name'], unique=True)

    # Create user_credentials table
    op.create_table('user_credentials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('platform_user_id', sa.String(), nullable=True),
        sa.Column('platform_username', sa.String(), nullable=True),
        sa.Column('encrypted_credentials', sa.Text(), nullable=False),
        sa.Column('credential_type', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('last_verified', sa.DateTime(), nullable=True),
        sa.Column('verification_error', sa.Text(), nullable=True),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_credentials_id'), 'user_credentials', ['id'], unique=False)
    op.create_index(op.f('ix_user_credentials_user_id'), 'user_credentials', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_credentials_platform'), 'user_credentials', ['platform'], unique=False)
    
    # Create unique constraint for user + platform combination
    op.create_index('ix_user_credentials_user_platform', 'user_credentials', ['user_id', 'platform'], unique=True)

    # Insert default platform configurations
    platform_configs_table = sa.table('platform_configs',
        sa.column('platform_name', sa.String),
        sa.column('display_name', sa.String),
        sa.column('requires_oauth', sa.Boolean),
        sa.column('requires_app_credentials', sa.Boolean),
        sa.column('required_fields', sa.JSON),
        sa.column('optional_fields', sa.JSON),
        sa.column('oauth_config', sa.JSON),
        sa.column('api_base_url', sa.String),
        sa.column('setup_instructions', sa.Text),
        sa.column('help_url', sa.String),
        sa.column('is_active', sa.Boolean)
    )
    
    op.bulk_insert(platform_configs_table, [
        {
            "platform_name": "twitter",
            "display_name": "Twitter/X",
            "requires_oauth": False,
            "requires_app_credentials": True,
            "required_fields": {
                "api_key": {"type": "string", "description": "Twitter API Key"},
                "api_secret": {"type": "string", "description": "Twitter API Secret"},
                "access_token": {"type": "string", "description": "Access Token"},
                "access_token_secret": {"type": "string", "description": "Access Token Secret"},
                "bearer_token": {"type": "string", "description": "Bearer Token"}
            },
            "optional_fields": {},
            "oauth_config": None,
            "api_base_url": "https://api.twitter.com/2",
            "setup_instructions": "Get your API keys from https://developer.twitter.com",
            "help_url": "https://developer.twitter.com/en/docs/authentication",
            "is_active": True
        },
        {
            "platform_name": "linkedin",
            "display_name": "LinkedIn",
            "requires_oauth": True,
            "requires_app_credentials": True,
            "required_fields": {
                "client_id": {"type": "string", "description": "LinkedIn Client ID"},
                "client_secret": {"type": "string", "description": "LinkedIn Client Secret"},
                "access_token": {"type": "string", "description": "Access Token"}
            },
            "optional_fields": {
                "refresh_token": {"type": "string", "description": "Refresh Token"}
            },
            "oauth_config": {
                "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
                "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
                "scopes": ["r_liteprofile", "r_emailaddress", "w_member_social"]
            },
            "api_base_url": "https://api.linkedin.com/v2",
            "setup_instructions": "Create an app at https://www.linkedin.com/developers/",
            "help_url": "https://docs.microsoft.com/en-us/linkedin/",
            "is_active": True
        },
        {
            "platform_name": "instagram",
            "display_name": "Instagram Business",
            "requires_oauth": True,
            "requires_app_credentials": True,
            "required_fields": {
                "app_id": {"type": "string", "description": "Instagram App ID"},
                "app_secret": {"type": "string", "description": "Instagram App Secret"},
                "access_token": {"type": "string", "description": "Access Token"},
                "business_account_id": {"type": "string", "description": "Instagram Business Account ID"}
            },
            "optional_fields": {},
            "oauth_config": None,
            "api_base_url": "https://graph.facebook.com",
            "setup_instructions": "Set up Instagram Business API through Facebook Developers",
            "help_url": "https://developers.facebook.com/docs/instagram-api/",
            "is_active": True
        },
        {
            "platform_name": "facebook",
            "display_name": "Facebook Pages",
            "requires_oauth": True,
            "requires_app_credentials": True,
            "required_fields": {
                "app_id": {"type": "string", "description": "Facebook App ID"},
                "app_secret": {"type": "string", "description": "Facebook App Secret"},
                "access_token": {"type": "string", "description": "Page Access Token"},
                "page_id": {"type": "string", "description": "Facebook Page ID"}
            },
            "optional_fields": {},
            "oauth_config": None,
            "api_base_url": "https://graph.facebook.com",
            "setup_instructions": "Create an app at https://developers.facebook.com",
            "help_url": "https://developers.facebook.com/docs/pages-api/",
            "is_active": True
        }
    ])


def downgrade() -> None:
    # Drop indexes and tables
    op.drop_index('ix_user_credentials_user_platform', table_name='user_credentials')
    op.drop_table('user_credentials')
    op.drop_table('platform_configs')