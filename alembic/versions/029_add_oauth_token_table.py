"""Add OAuthToken table for centralized secure token storage

Revision ID: 029_add_oauth_token_table
Revises: 028_add_organization_id_to_social_platform_connections
Create Date: 2025-09-04 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision = '029_add_oauth_token_table'
down_revision = '028_add_organization_id_to_social_platform_connections'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the oauth_tokens table
    op.create_table(
        'oauth_tokens',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', sa.Integer, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        
        # Token identification
        sa.Column('token_name', sa.String(255), nullable=False),
        sa.Column('token_type', sa.String(50), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('platform_account_id', sa.String(255)),
        sa.Column('connection_reference', UUID(as_uuid=True)),
        
        # Encrypted token data (versioned envelope JSON)
        sa.Column('encrypted_token', sa.Text, nullable=False),
        
        # Encryption metadata for key rotation
        sa.Column('encryption_version', sa.Integer, nullable=False, default=1),
        sa.Column('encryption_key_id', sa.String(50), nullable=False, default='default'),
        
        # Token lifecycle
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('last_validated_at', sa.DateTime(timezone=True)),
        sa.Column('is_valid', sa.Boolean, default=True),
        
        # OAuth metadata
        sa.Column('scopes', sa.JSON),
        sa.Column('token_metadata', sa.JSON, default={}),
        
        # Security and audit
        sa.Column('created_by_user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.Column('revoked_reason', sa.String(255)),
        sa.Column('last_rotation_at', sa.DateTime(timezone=True)),
        sa.Column('rotation_count', sa.Integer, default=0),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes for performance and security
    op.create_index('idx_oauth_tokens_org_platform', 'oauth_tokens', ['organization_id', 'platform'])
    op.create_index('idx_oauth_tokens_valid', 'oauth_tokens', ['is_valid'])
    op.create_index('idx_oauth_tokens_expires', 'oauth_tokens', ['expires_at'])
    op.create_index('idx_oauth_tokens_connection_ref', 'oauth_tokens', ['connection_reference'])
    
    # Create unique constraint for one token per account/type combination
    op.create_unique_constraint(
        'uq_oauth_tokens_unique_per_account_type',
        'oauth_tokens',
        ['organization_id', 'platform', 'platform_account_id', 'token_type']
    )


def downgrade() -> None:
    # Drop the oauth_tokens table and all associated indexes/constraints
    op.drop_table('oauth_tokens')