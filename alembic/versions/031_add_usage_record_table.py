"""add usage record table for subscription enforcement

Revision ID: 031
Revises: 030
Create Date: 2025-09-05 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '031'
down_revision = '030'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add usage record table for tracking subscription usage limits"""
    
    # Create usage_records table
    op.create_table('usage_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('usage_type', sa.String(length=50), nullable=False),
        sa.Column('resource', sa.String(length=50), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True, default=1),
        sa.Column('cost_credits', sa.Numeric(precision=10, scale=4), nullable=True, default=0.0),
        sa.Column('cost_usd', sa.Numeric(precision=10, scale=4), nullable=True, default=0.0),
        sa.Column('usage_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('billing_period', sa.String(length=7), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('idx_usage_user_period', 'usage_records', ['user_id', 'billing_period'])
    op.create_index('idx_usage_org_period', 'usage_records', ['organization_id', 'billing_period'])  
    op.create_index('idx_usage_type_period', 'usage_records', ['usage_type', 'billing_period'])
    op.create_index('idx_usage_created', 'usage_records', ['created_at'])
    op.create_index(op.f('ix_usage_records_id'), 'usage_records', ['id'], unique=False)
    op.create_index(op.f('ix_usage_records_user_id'), 'usage_records', ['user_id'], unique=False)
    op.create_index(op.f('ix_usage_records_organization_id'), 'usage_records', ['organization_id'], unique=False)
    op.create_index(op.f('ix_usage_records_billing_period'), 'usage_records', ['billing_period'], unique=False)
    op.create_index(op.f('ix_usage_records_created_at'), 'usage_records', ['created_at'], unique=False)


def downgrade() -> None:
    """Remove usage record table"""
    
    # Drop all indexes
    op.drop_index(op.f('ix_usage_records_created_at'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_billing_period'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_organization_id'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_user_id'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_id'), table_name='usage_records')
    op.drop_index('idx_usage_created', table_name='usage_records')
    op.drop_index('idx_usage_type_period', table_name='usage_records')
    op.drop_index('idx_usage_org_period', table_name='usage_records')
    op.drop_index('idx_usage_user_period', table_name='usage_records')
    
    # Drop table
    op.drop_table('usage_records')