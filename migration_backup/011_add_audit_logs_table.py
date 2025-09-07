"""Add audit logs table for security tracking

Revision ID: 011
Revises: 010
Create Date: 2025-01-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None

def upgrade():
    # Create audit_logs table for security and compliance tracking
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, index=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('event_type', sa.String(100), nullable=False, index=True),
        sa.Column('user_id', sa.String(100), nullable=True, index=True),
        sa.Column('session_id', sa.String(100), nullable=True, index=True),
        sa.Column('ip_address', sa.String(45), nullable=True),  # IPv6 compatible
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('resource', sa.String(200), nullable=True),
        sa.Column('action', sa.String(100), nullable=True),
        sa.Column('outcome', sa.String(50), nullable=True),  # success, failure, error
        sa.Column('details', JSON, nullable=True),
        sa.Column('compliance_flags', JSON, nullable=True)
    )
    
    # Create indexes for common query patterns
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_outcome', 'audit_logs', ['outcome'])
    op.create_index('idx_audit_logs_security_events', 'audit_logs', ['event_type', 'outcome', 'timestamp'])

def downgrade():
    # Drop indexes first
    op.drop_index('idx_audit_logs_security_events', table_name='audit_logs')
    op.drop_index('idx_audit_logs_outcome', table_name='audit_logs')
    op.drop_index('idx_audit_logs_user_id', table_name='audit_logs')
    op.drop_index('idx_audit_logs_event_type', table_name='audit_logs')
    op.drop_index('idx_audit_logs_timestamp', table_name='audit_logs')
    
    # Drop table
    op.drop_table('audit_logs')