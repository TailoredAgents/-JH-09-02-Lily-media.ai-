"""Ensure engagement_data column exists in content_logs

Revision ID: 018_ensure_engagement_data
Revises: 017_add_missing_user_columns
Create Date: 2025-08-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '018_ensure_engagement_data'
down_revision = '017_add_missing_user_columns'
branch_labels = None
depends_on = None

def upgrade():
    """Add engagement_data column to content_logs if it doesn't exist"""
    
    # Check if column exists before adding it
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='content_logs' AND column_name='engagement_data'
    """)).fetchall()
    
    if not result:
        # Column doesn't exist, add it
        op.add_column('content_logs', 
            sa.Column('engagement_data', sa.JSON(), nullable=True, default=sa.text('{}'))
        )
        print("✅ Added missing engagement_data column to content_logs")
    else:
        print("✅ engagement_data column already exists in content_logs")

def downgrade():
    """Remove engagement_data column"""
    # Check if column exists before removing it
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='content_logs' AND column_name='engagement_data'
    """)).fetchall()
    
    if result:
        op.drop_column('content_logs', 'engagement_data')
        print("Removed engagement_data column from content_logs")
    else:
        print("engagement_data column doesn't exist in content_logs, nothing to remove")