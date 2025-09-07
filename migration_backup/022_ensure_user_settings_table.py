"""Ensure user_settings table exists with all required columns

Revision ID: 022_ensure_user_settings
Revises: 2025_08_20_1420-f42f94c7a129_add_two_factor_authentication_fields_to_
Create Date: 2025-08-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers
revision = '022_ensure_user_settings'
down_revision = 'f42f94c7a129'
branch_labels = None
depends_on = None


def upgrade():
    """Ensure user_settings table exists with all columns"""
    
    # Check if user_settings table exists
    conn = op.get_bind()
    
    # Check if table exists
    table_exists = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'user_settings'
        );
    """)).scalar()
    
    if not table_exists:
        print("Creating user_settings table from scratch...")
        # Create the complete user_settings table
        op.create_table('user_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            
            # Brand settings
            sa.Column('brand_name', sa.String(), nullable=True),
            sa.Column('brand_voice', sa.String(), nullable=True, server_default='professional'),
            sa.Column('primary_color', sa.String(), nullable=True, server_default='#3b82f6'),
            sa.Column('logo_url', sa.String(), nullable=True),
            
            # Content preferences
            sa.Column('content_frequency', sa.Integer(), nullable=True, server_default='3'),
            sa.Column('preferred_platforms', sa.JSON(), nullable=True),
            sa.Column('posting_times', sa.JSON(), nullable=True),
            
            # AI settings
            sa.Column('creativity_level', sa.Float(), nullable=True, server_default='0.7'),
            sa.Column('enable_images', sa.Boolean(), nullable=True, server_default='true'),
            sa.Column('enable_repurposing', sa.Boolean(), nullable=True, server_default='true'),
            sa.Column('enable_autonomous_mode', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('timezone', sa.String(), nullable=False, server_default='UTC'),
            
            # Integrations
            sa.Column('connected_accounts', sa.JSON(), nullable=True),
            
            # Social Inbox Settings
            sa.Column('default_response_personality', sa.String(), nullable=True, server_default='professional'),
            sa.Column('auto_response_enabled', sa.Boolean(), nullable=True, server_default='false'),
            sa.Column('auto_response_confidence_threshold', sa.Float(), nullable=True, server_default='0.8'),
            sa.Column('auto_response_business_hours_only', sa.Boolean(), nullable=True, server_default='true'),
            sa.Column('auto_response_delay_minutes', sa.Integer(), nullable=True, server_default='5'),
            sa.Column('business_hours_start', sa.String(), nullable=True, server_default='09:00'),
            sa.Column('business_hours_end', sa.String(), nullable=True, server_default='17:00'),
            sa.Column('business_days', sa.JSON(), nullable=True),
            sa.Column('escalation_keywords', sa.JSON(), nullable=True),
            sa.Column('excluded_response_keywords', sa.JSON(), nullable=True),
            
            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_user_settings_id'), 'user_settings', ['id'], unique=False)
        
        # Set JSON default values
        op.execute("""
            ALTER TABLE user_settings 
            ALTER COLUMN preferred_platforms SET DEFAULT '["twitter", "instagram"]'::json
        """)
        op.execute("""
            ALTER TABLE user_settings 
            ALTER COLUMN posting_times SET DEFAULT '{"twitter": "09:00", "instagram": "10:00"}'::json
        """)
        op.execute("""
            ALTER TABLE user_settings 
            ALTER COLUMN business_days SET DEFAULT '["monday", "tuesday", "wednesday", "thursday", "friday"]'::json
        """)
        op.execute("""
            ALTER TABLE user_settings 
            ALTER COLUMN escalation_keywords SET DEFAULT '["complaint", "lawsuit", "refund", "angry", "terrible"]'::json
        """)
        op.execute("""
            ALTER TABLE user_settings 
            ALTER COLUMN excluded_response_keywords SET DEFAULT '["spam", "bot", "fake"]'::json
        """)
        
    else:
        print("user_settings table exists, checking for missing columns...")
        
        # Check for missing columns and add them
        columns_to_add = [
            ('enable_autonomous_mode', sa.Boolean(), 'false'),
            ('timezone', sa.String(), 'UTC'),
            ('default_response_personality', sa.String(), 'professional'),
            ('auto_response_enabled', sa.Boolean(), 'false'),
            ('auto_response_confidence_threshold', sa.Float(), '0.8'),
            ('auto_response_business_hours_only', sa.Boolean(), 'true'),
            ('auto_response_delay_minutes', sa.Integer(), '5'),
            ('business_hours_start', sa.String(), '09:00'),
            ('business_hours_end', sa.String(), '17:00'),
            ('business_days', sa.JSON(), None),
            ('escalation_keywords', sa.JSON(), None),
            ('excluded_response_keywords', sa.JSON(), None),
        ]
        
        for column_name, column_type, default_value in columns_to_add:
            # Check if column exists
            column_exists = conn.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'user_settings'
                    AND column_name = '{column_name}'
                );
            """)).scalar()
            
            if not column_exists:
                print(f"Adding missing column: {column_name}")
                if default_value:
                    op.add_column('user_settings', sa.Column(column_name, column_type, nullable=True, server_default=default_value))
                else:
                    op.add_column('user_settings', sa.Column(column_name, column_type, nullable=True))
        
        # Set JSON defaults for new columns if they were just added
        try:
            op.execute("""
                UPDATE user_settings SET 
                    business_days = '["monday", "tuesday", "wednesday", "thursday", "friday"]'::json
                WHERE business_days IS NULL
            """)
            op.execute("""
                UPDATE user_settings SET 
                    escalation_keywords = '["complaint", "lawsuit", "refund", "angry", "terrible"]'::json
                WHERE escalation_keywords IS NULL
            """)
            op.execute("""
                UPDATE user_settings SET 
                    excluded_response_keywords = '["spam", "bot", "fake"]'::json
                WHERE excluded_response_keywords IS NULL
            """)
        except:
            pass  # Ignore if columns don't exist or are already populated


def downgrade():
    """This migration is designed to be non-destructive"""
    pass