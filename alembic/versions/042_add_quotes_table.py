"""Add quotes table for org-scoped quote management

Revision ID: 042_quotes_table
Revises: 041_pricing_rules
Create Date: 2025-09-09

PW-PRICING-ADD-002: Add Quote model with status lifecycle for customer quote management
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '042_quotes_table'
down_revision = '041_pricing_rules'
branch_labels = None
depends_on = None


def upgrade():
    """Add quotes table for organization-scoped quote management"""
    
    op.create_table('quotes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('customer_email', sa.String(), nullable=False),
        sa.Column('customer_name', sa.String(), nullable=True),
        sa.Column('customer_phone', sa.String(), nullable=True),
        sa.Column('customer_address', sa.Text(), nullable=True),
        sa.Column('line_items', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('discounts', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('declined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('quote_number', sa.String(length=50), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('customer_notes', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('source_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('pricing_rule_id', sa.Integer(), nullable=True),
        sa.Column('pricing_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('updated_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('ix_quotes_organization_id', 'quotes', ['organization_id'])
    op.create_index('ix_quotes_customer_email', 'quotes', ['customer_email'])
    op.create_index('ix_quotes_status', 'quotes', ['status'])
    op.create_index('ix_quotes_quote_number', 'quotes', ['quote_number'])
    op.create_index('ix_quotes_valid_until', 'quotes', ['valid_until'])
    op.create_index('ix_quotes_org_status', 'quotes', ['organization_id', 'status'])
    op.create_index('ix_quotes_org_customer', 'quotes', ['organization_id', 'customer_email'])
    op.create_index('ix_quotes_org_created', 'quotes', ['organization_id', 'created_at'])
    
    # Create foreign key constraints
    op.create_foreign_key('fk_quotes_organization_id', 'quotes', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_quotes_pricing_rule_id', 'quotes', 'pricing_rules', ['pricing_rule_id'], ['id'])
    op.create_foreign_key('fk_quotes_created_by_id', 'quotes', 'users', ['created_by_id'], ['id'])
    op.create_foreign_key('fk_quotes_updated_by_id', 'quotes', 'users', ['updated_by_id'], ['id'])
    
    # Create unique constraint for quote_number
    op.create_unique_constraint('uq_quotes_quote_number', 'quotes', ['quote_number'])
    
    print("✅ Created quotes table with org-scoping and status lifecycle")


def downgrade():
    """Remove quotes table"""
    
    # Drop foreign key constraints
    op.drop_constraint('fk_quotes_updated_by_id', 'quotes', type_='foreignkey')
    op.drop_constraint('fk_quotes_created_by_id', 'quotes', type_='foreignkey')
    op.drop_constraint('fk_quotes_pricing_rule_id', 'quotes', type_='foreignkey')
    op.drop_constraint('fk_quotes_organization_id', 'quotes', type_='foreignkey')
    
    # Drop unique constraints
    op.drop_constraint('uq_quotes_quote_number', 'quotes', type_='unique')
    
    # Drop indexes
    op.drop_index('ix_quotes_org_created', table_name='quotes')
    op.drop_index('ix_quotes_org_customer', table_name='quotes')
    op.drop_index('ix_quotes_org_status', table_name='quotes')
    op.drop_index('ix_quotes_valid_until', table_name='quotes')
    op.drop_index('ix_quotes_quote_number', table_name='quotes')
    op.drop_index('ix_quotes_status', table_name='quotes')
    op.drop_index('ix_quotes_customer_email', table_name='quotes')
    op.drop_index('ix_quotes_organization_id', table_name='quotes')
    
    # Drop table
    op.drop_table('quotes')
    
    print("✅ Removed quotes table")