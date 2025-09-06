"""Add missing user_settings columns for image generation

Revision ID: 032_add_missing_user_settings_columns
Revises: 031_add_usage_record_table
Create Date: 2025-09-06 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '032_add_missing_user_settings_columns'
down_revision = '031_add_usage_record_table'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing user_settings columns for image generation and style preferences"""
    
    # Add image mood settings (JSONB)
    op.add_column('user_settings', sa.Column('image_mood', postgresql.JSONB(astext_type=sa.Text()), 
                                           server_default='["professional", "clean"]', nullable=True))
    
    # Add brand keywords (JSONB)
    op.add_column('user_settings', sa.Column('brand_keywords', postgresql.JSONB(astext_type=sa.Text()), 
                                           server_default='[]', nullable=True))
    
    # Add avoid list (JSONB)
    op.add_column('user_settings', sa.Column('avoid_list', postgresql.JSONB(astext_type=sa.Text()), 
                                           server_default='[]', nullable=True))
    
    # Add preferred image style (JSONB)
    op.add_column('user_settings', sa.Column('preferred_image_style', postgresql.JSONB(astext_type=sa.Text()), 
                                           server_default='{"lighting": "natural", "composition": "rule_of_thirds", "color_temperature": "neutral"}', 
                                           nullable=True))
    
    # Add custom image prompts (JSONB)
    op.add_column('user_settings', sa.Column('custom_image_prompts', postgresql.JSONB(astext_type=sa.Text()), 
                                           server_default='{}', nullable=True))
    
    # Add image quality setting
    op.add_column('user_settings', sa.Column('image_quality', sa.String(), 
                                           server_default='high', nullable=True))
    
    # Add image aspect ratio
    op.add_column('user_settings', sa.Column('image_aspect_ratio', sa.String(), 
                                           server_default='1:1', nullable=True))
    
    # Add creativity level (float for 0-1 scale)
    op.add_column('user_settings', sa.Column('creativity_level', sa.Float(), 
                                           server_default='0.7', nullable=True))
    
    # Add auto image generation toggle
    op.add_column('user_settings', sa.Column('enable_auto_image_generation', sa.Boolean(), 
                                           server_default='true', nullable=True))
    
    # Add repurposing toggle
    op.add_column('user_settings', sa.Column('enable_repurposing', sa.Boolean(), 
                                           server_default='true', nullable=True))


def downgrade():
    """Remove the added user_settings columns"""
    
    op.drop_column('user_settings', 'enable_repurposing')
    op.drop_column('user_settings', 'enable_auto_image_generation')
    op.drop_column('user_settings', 'creativity_level')
    op.drop_column('user_settings', 'image_aspect_ratio')
    op.drop_column('user_settings', 'image_quality')
    op.drop_column('user_settings', 'custom_image_prompts')
    op.drop_column('user_settings', 'preferred_image_style')
    op.drop_column('user_settings', 'avoid_list')
    op.drop_column('user_settings', 'brand_keywords')
    op.drop_column('user_settings', 'image_mood')