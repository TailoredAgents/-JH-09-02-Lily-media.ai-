"""Add PricingRule table for org-scoped pricing engine

Revision ID: 041_pricing_rules
Revises: 040_add_organization_id_to_content_logs
Create Date: 2025-09-09

PW-PRICING-ADD-001: Add comprehensive pricing engine with org-scoping
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '041_pricing_rules'
down_revision = '040_add_organization_id_to_content_logs'
branch_labels = None
depends_on = None


def upgrade():
    """Add pricing_rules table for organization-scoped pricing engine"""
    
    op.create_table('pricing_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('min_job_total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('base_rates', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('bundles', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('seasonal_modifiers', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('travel_settings', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('additional_services', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('business_rules', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('updated_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('ix_pricing_rules_organization_id', 'pricing_rules', ['organization_id'])
    op.create_index('ix_pricing_rules_is_active', 'pricing_rules', ['is_active'])
    op.create_index('ix_pricing_rules_org_active', 'pricing_rules', ['organization_id', 'is_active'])
    op.create_index('ix_pricing_rules_org_priority', 'pricing_rules', ['organization_id', 'priority'])
    op.create_index('ix_pricing_rules_effective_dates', 'pricing_rules', ['effective_from', 'effective_until'])
    
    # Create foreign key constraints
    op.create_foreign_key('fk_pricing_rules_organization_id', 'pricing_rules', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_pricing_rules_created_by_id', 'pricing_rules', 'users', ['created_by_id'], ['id'])
    op.create_foreign_key('fk_pricing_rules_updated_by_id', 'pricing_rules', 'users', ['updated_by_id'], ['id'])
    
    print("✅ Created pricing_rules table with org-scoping and comprehensive pricing fields")


def downgrade():
    """Remove pricing_rules table"""
    
    # Drop foreign key constraints
    op.drop_constraint('fk_pricing_rules_updated_by_id', 'pricing_rules', type_='foreignkey')
    op.drop_constraint('fk_pricing_rules_created_by_id', 'pricing_rules', type_='foreignkey')
    op.drop_constraint('fk_pricing_rules_organization_id', 'pricing_rules', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_pricing_rules_effective_dates', table_name='pricing_rules')
    op.drop_index('ix_pricing_rules_org_priority', table_name='pricing_rules')
    op.drop_index('ix_pricing_rules_org_active', table_name='pricing_rules')
    op.drop_index('ix_pricing_rules_is_active', table_name='pricing_rules')
    op.drop_index('ix_pricing_rules_organization_id', table_name='pricing_rules')
    
    # Drop table
    op.drop_table('pricing_rules')
    
    print("✅ Removed pricing_rules table")