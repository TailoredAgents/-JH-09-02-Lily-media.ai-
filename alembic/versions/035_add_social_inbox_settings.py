"""Add social inbox settings to user_settings

Revision ID: 020_social_inbox_settings
Revises: 019_add_phase3a_social_inbox_models
Create Date: 2025-08-26 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '035_social_inbox_settings'
down_revision = '033_add_style_vault_and_default_image_model'
branch_labels = None
depends_on = None


def upgrade():
    # Add social inbox settings columns to user_settings table
    op.add_column('user_settings', sa.Column('default_response_personality', sa.String(), nullable=True))
    op.add_column('user_settings', sa.Column('auto_response_enabled', sa.Boolean(), nullable=True))
    op.add_column('user_settings', sa.Column('auto_response_confidence_threshold', sa.Float(), nullable=True))
    op.add_column('user_settings', sa.Column('auto_response_business_hours_only', sa.Boolean(), nullable=True))
    op.add_column('user_settings', sa.Column('auto_response_delay_minutes', sa.Integer(), nullable=True))
    op.add_column('user_settings', sa.Column('business_hours_start', sa.String(), nullable=True))
    op.add_column('user_settings', sa.Column('business_hours_end', sa.String(), nullable=True))
    op.add_column('user_settings', sa.Column('business_days', sa.JSON(), nullable=True))
    op.add_column('user_settings', sa.Column('escalation_keywords', sa.JSON(), nullable=True))
    op.add_column('user_settings', sa.Column('excluded_response_keywords', sa.JSON(), nullable=True))
    
    # Set default values
    op.execute("ALTER TABLE user_settings ALTER COLUMN default_response_personality SET DEFAULT 'professional'")
    op.execute("ALTER TABLE user_settings ALTER COLUMN auto_response_enabled SET DEFAULT false")
    op.execute("ALTER TABLE user_settings ALTER COLUMN auto_response_confidence_threshold SET DEFAULT 0.8")
    op.execute("ALTER TABLE user_settings ALTER COLUMN auto_response_business_hours_only SET DEFAULT true")
    op.execute("ALTER TABLE user_settings ALTER COLUMN auto_response_delay_minutes SET DEFAULT 5")
    op.execute("ALTER TABLE user_settings ALTER COLUMN business_hours_start SET DEFAULT '09:00'")
    op.execute("ALTER TABLE user_settings ALTER COLUMN business_hours_end SET DEFAULT '17:00'")
    op.execute("ALTER TABLE user_settings ALTER COLUMN business_days SET DEFAULT '[\"monday\", \"tuesday\", \"wednesday\", \"thursday\", \"friday\"]'")
    op.execute("ALTER TABLE user_settings ALTER COLUMN escalation_keywords SET DEFAULT '[\"complaint\", \"lawsuit\", \"refund\", \"angry\", \"terrible\"]'")
    op.execute("ALTER TABLE user_settings ALTER COLUMN excluded_response_keywords SET DEFAULT '[\"spam\", \"bot\", \"fake\"]'")
    
    # Update existing rows with default values
    op.execute("""
        UPDATE user_settings SET 
            default_response_personality = 'professional',
            auto_response_enabled = false,
            auto_response_confidence_threshold = 0.8,
            auto_response_business_hours_only = true,
            auto_response_delay_minutes = 5,
            business_hours_start = '09:00',
            business_hours_end = '17:00',
            business_days = '["monday", "tuesday", "wednesday", "thursday", "friday"]'::json,
            escalation_keywords = '["complaint", "lawsuit", "refund", "angry", "terrible"]'::json,
            excluded_response_keywords = '["spam", "bot", "fake"]'::json
        WHERE default_response_personality IS NULL
    """)


def downgrade():
    # Remove social inbox settings columns from user_settings table
    op.drop_column('user_settings', 'excluded_response_keywords')
    op.drop_column('user_settings', 'escalation_keywords')
    op.drop_column('user_settings', 'business_days')
    op.drop_column('user_settings', 'business_hours_end')
    op.drop_column('user_settings', 'business_hours_start')
    op.drop_column('user_settings', 'auto_response_delay_minutes')
    op.drop_column('user_settings', 'auto_response_business_hours_only')
    op.drop_column('user_settings', 'auto_response_confidence_threshold')
    op.drop_column('user_settings', 'auto_response_enabled')
    op.drop_column('user_settings', 'default_response_personality')