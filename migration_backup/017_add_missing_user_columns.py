"""Add missing user columns for production database

Revision ID: 017_add_missing_user_columns
Revises: 016_open_saas_auth
Create Date: 2025-08-25 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '017_add_missing_user_columns'
down_revision = '016_open_saas_auth'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Add missing columns that exist in model but not in production database"""
    # Add is_superuser column if it doesn't exist
    op.execute("""
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE;
    """)
    
    # Add is_verified column if it doesn't exist (for FastAPI Users compatibility)
    op.execute("""
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;
    """)
    
    # Ensure all boolean columns have defaults
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN is_active SET DEFAULT TRUE;
    """)
    
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN is_superuser SET DEFAULT FALSE;
    """)
    
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN is_verified SET DEFAULT FALSE;
    """)
    
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN email_verified SET DEFAULT FALSE;
    """)
    
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN two_factor_enabled SET DEFAULT FALSE;
    """)

def downgrade() -> None:
    """Remove the added columns"""
    op.drop_column('users', 'is_superuser')
    op.drop_column('users', 'is_verified')