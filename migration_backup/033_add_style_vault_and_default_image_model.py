"""Add style_vault and default_image_model to user_settings

Revision ID: 033_add_style_vault_and_default_image_model
Revises: 032_add_missing_user_settings_columns
Create Date: 2025-09-06 18:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '033_add_style_vault_and_default_image_model'
down_revision = '032_add_missing_user_settings_columns'
branch_labels = None
depends_on = None


def upgrade():
    """Add style_vault and default_image_model columns with proper indexes"""
    
    # Add default image model selection
    op.add_column('user_settings', sa.Column('default_image_model', sa.String(), 
                                           server_default='grok2', nullable=True))
    
    # Add style vault for brand consistency (JSONB)
    op.add_column('user_settings', sa.Column('style_vault', postgresql.JSONB(astext_type=sa.Text()), 
                                           server_default='{}', nullable=True))
    
    # Create GIN indexes for JSONB columns for performance
    # These indexes are essential for fast querying of JSONB fields
    op.create_index('idx_user_settings_style_vault_gin', 'user_settings', ['style_vault'], 
                   postgresql_using='gin')
    
    op.create_index('idx_user_settings_image_mood_gin', 'user_settings', ['image_mood'], 
                   postgresql_using='gin')
    
    op.create_index('idx_user_settings_brand_keywords_gin', 'user_settings', ['brand_keywords'], 
                   postgresql_using='gin')
    
    op.create_index('idx_user_settings_avoid_list_gin', 'user_settings', ['avoid_list'], 
                   postgresql_using='gin')
    
    op.create_index('idx_user_settings_preferred_image_style_gin', 'user_settings', ['preferred_image_style'], 
                   postgresql_using='gin')
    
    op.create_index('idx_user_settings_custom_image_prompts_gin', 'user_settings', ['custom_image_prompts'], 
                   postgresql_using='gin')
    
    # Add index for default_image_model for fast model-based queries
    op.create_index('idx_user_settings_default_image_model', 'user_settings', ['default_image_model'])


def downgrade():
    """Remove style_vault, default_image_model and their indexes"""
    
    # Drop indexes first
    op.drop_index('idx_user_settings_default_image_model', table_name='user_settings')
    op.drop_index('idx_user_settings_custom_image_prompts_gin', table_name='user_settings')
    op.drop_index('idx_user_settings_preferred_image_style_gin', table_name='user_settings')
    op.drop_index('idx_user_settings_avoid_list_gin', table_name='user_settings')
    op.drop_index('idx_user_settings_brand_keywords_gin', table_name='user_settings')
    op.drop_index('idx_user_settings_image_mood_gin', table_name='user_settings')
    op.drop_index('idx_user_settings_style_vault_gin', table_name='user_settings')
    
    # Drop columns
    op.drop_column('user_settings', 'style_vault')
    op.drop_column('user_settings', 'default_image_model')