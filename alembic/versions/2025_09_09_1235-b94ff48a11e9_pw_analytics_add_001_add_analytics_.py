"""PW-ANALYTICS-ADD-001: Add analytics indexes for business KPIs performance

Revision ID: b94ff48a11e9
Revises: 12f93173f8ff
Create Date: 2025-09-09 12:35:59.340568

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b94ff48a11e9'
down_revision = '12f93173f8ff'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for business analytics queries"""
    
    # Analytics indexes for Lead model
    # Composite index for org + created_at + platform filtering (time range + platform breakdown)
    op.create_index(
        'idx_leads_analytics_org_created_platform',
        'leads',
        ['organization_id', 'created_at', 'source_platform'],
        postgresql_using='btree'
    )
    
    # Composite index for org + created_at + status (for conversion analytics)
    op.create_index(
        'idx_leads_analytics_org_created_status',
        'leads',
        ['organization_id', 'created_at', 'status'],
        postgresql_using='btree'
    )
    
    # Analytics indexes for Quote model  
    # Composite index for org + created_at + status (for quote conversion rates)
    op.create_index(
        'idx_quotes_analytics_org_created_status',
        'quotes',
        ['organization_id', 'created_at', 'status'],
        postgresql_using='btree'
    )
    
    # Composite index for org + status + total (for revenue aggregations)
    op.create_index(
        'idx_quotes_analytics_org_status_total',
        'quotes',
        ['organization_id', 'status', 'total'],
        postgresql_using='btree'
    )
    
    # Analytics indexes for Job model
    # Composite index for org + created_at + status (for job completion analytics)
    op.create_index(
        'idx_jobs_analytics_org_created_status',
        'jobs',
        ['organization_id', 'created_at', 'status'],
        postgresql_using='btree'
    )
    
    # Composite index for org + service_type + status (for service type breakdowns)
    op.create_index(
        'idx_jobs_analytics_org_service_status',
        'jobs',
        ['organization_id', 'service_type', 'status'],
        postgresql_using='btree'
    )
    
    # Composite index for org + status + estimated_cost + actual_cost (for revenue analytics)
    op.create_index(
        'idx_jobs_analytics_org_status_costs',
        'jobs',
        ['organization_id', 'status', 'estimated_cost', 'actual_cost'],
        postgresql_using='btree'
    )
    
    # Cross-table analytics indexes for join performance
    # Index on Quote.lead_id for lead->quote analytics joins
    op.create_index(
        'idx_quotes_analytics_lead_id',
        'quotes',
        ['lead_id'],
        postgresql_where="lead_id IS NOT NULL",
        postgresql_using='btree'
    )
    
    # Index on Job.quote_id for quote->job analytics joins  
    op.create_index(
        'idx_jobs_analytics_quote_id',
        'jobs',
        ['quote_id'],
        postgresql_where="quote_id IS NOT NULL",
        postgresql_using='btree'
    )
    
    # Time-based partitioning preparation indexes
    # Monthly partitions for time series queries
    op.create_index(
        'idx_leads_analytics_monthly',
        'leads',
        ['organization_id', sa.text("DATE_TRUNC('month', created_at)")],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_quotes_analytics_monthly',
        'quotes', 
        ['organization_id', sa.text("DATE_TRUNC('month', created_at)")],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_jobs_analytics_monthly',
        'jobs',
        ['organization_id', sa.text("DATE_TRUNC('month', created_at)")],
        postgresql_using='btree'
    )


def downgrade() -> None:
    """Remove analytics performance indexes"""
    
    # Drop time-based indexes
    op.drop_index('idx_jobs_analytics_monthly', table_name='jobs')
    op.drop_index('idx_quotes_analytics_monthly', table_name='quotes')
    op.drop_index('idx_leads_analytics_monthly', table_name='leads')
    
    # Drop cross-table indexes
    op.drop_index('idx_jobs_analytics_quote_id', table_name='jobs')
    op.drop_index('idx_quotes_analytics_lead_id', table_name='quotes')
    
    # Drop job analytics indexes
    op.drop_index('idx_jobs_analytics_org_status_costs', table_name='jobs')
    op.drop_index('idx_jobs_analytics_org_service_status', table_name='jobs')
    op.drop_index('idx_jobs_analytics_org_created_status', table_name='jobs')
    
    # Drop quote analytics indexes
    op.drop_index('idx_quotes_analytics_org_status_total', table_name='quotes')
    op.drop_index('idx_quotes_analytics_org_created_status', table_name='quotes')
    
    # Drop lead analytics indexes
    op.drop_index('idx_leads_analytics_org_created_status', table_name='leads')
    op.drop_index('idx_leads_analytics_org_created_platform', table_name='leads')