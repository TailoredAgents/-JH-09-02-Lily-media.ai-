"""Add public_id UUID columns to core models

Revision ID: 017_add_public_uuid_columns
Revises: 016_remove_registration_keys
Create Date: 2025-09-03 13:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers
revision = '017_add_public_uuid_columns'
down_revision = '016_open_saas_auth'
branch_labels = None
depends_on = None


def upgrade():
    """Add public_id UUID columns to core user-facing models."""
    
    # Add public_id to users table
    op.add_column('users', sa.Column(
        'public_id', 
        postgresql.UUID(as_uuid=True), 
        nullable=True,  # Temporarily nullable for migration
        unique=True
    ))
    
    # Add index for public_id
    op.create_index('ix_users_public_id', 'users', ['public_id'])
    
    # Add public_id to content_logs table
    op.add_column('content_logs', sa.Column(
        'public_id', 
        postgresql.UUID(as_uuid=True), 
        nullable=True,  # Temporarily nullable for migration
        unique=True
    ))
    
    # Add index for content_logs public_id
    op.create_index('ix_content_logs_public_id', 'content_logs', ['public_id'])
    
    # Populate existing records with UUIDs
    connection = op.get_bind()
    
    # Update users table
    connection.execute("""
        UPDATE users 
        SET public_id = gen_random_uuid() 
        WHERE public_id IS NULL
    """)
    
    # Update content_logs table
    connection.execute("""
        UPDATE content_logs 
        SET public_id = gen_random_uuid() 
        WHERE public_id IS NULL
    """)
    
    # Make public_id columns not nullable after populating data
    op.alter_column('users', 'public_id', nullable=False)
    op.alter_column('content_logs', 'public_id', nullable=False)


def downgrade():
    """Remove public_id UUID columns."""
    
    # Drop indexes first
    op.drop_index('ix_users_public_id')
    op.drop_index('ix_content_logs_public_id')
    
    # Drop columns
    op.drop_column('users', 'public_id')
    op.drop_column('content_logs', 'public_id')