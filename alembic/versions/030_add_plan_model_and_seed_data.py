"""add plan model and seed data

Revision ID: 030
Revises: 029
Create Date: 2025-09-05 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '030'
down_revision = '029'
branch_labels = None
depends_on = None


def upgrade():
    """Add Plan model and seed with Starter/Pro/Enterprise data"""
    
    # Create the plans table
    op.create_table('plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('monthly_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('annual_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('trial_days', sa.Integer(), nullable=True),
        sa.Column('max_social_profiles', sa.Integer(), nullable=False),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('max_workspaces', sa.Integer(), nullable=True),
        sa.Column('max_posts_per_day', sa.Integer(), nullable=False),
        sa.Column('max_posts_per_week', sa.Integer(), nullable=False),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('full_ai', sa.Boolean(), nullable=True),
        sa.Column('enhanced_autopilot', sa.Boolean(), nullable=True),
        sa.Column('ai_inbox', sa.Boolean(), nullable=True),
        sa.Column('crm_integration', sa.Boolean(), nullable=True),
        sa.Column('advanced_analytics', sa.Boolean(), nullable=True),
        sa.Column('predictive_analytics', sa.Boolean(), nullable=True),
        sa.Column('white_label', sa.Boolean(), nullable=True),
        sa.Column('basic_ai_only', sa.Boolean(), nullable=True),
        sa.Column('premium_ai_models', sa.Boolean(), nullable=True),
        sa.Column('image_generation_limit', sa.Integer(), nullable=True),
        sa.Column('autopilot_posts_per_day', sa.Integer(), nullable=True),
        sa.Column('autopilot_research_enabled', sa.Boolean(), nullable=True),
        sa.Column('autopilot_ad_campaigns', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_popular', sa.Boolean(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('stripe_product_id', sa.String(), nullable=True),
        sa.Column('stripe_monthly_price_id', sa.String(), nullable=True),
        sa.Column('stripe_annual_price_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    op.create_index(op.f('ix_plans_id'), 'plans', ['id'], unique=False)
    
    # Add plan_id column to users table
    op.add_column('users', sa.Column('plan_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'users', 'plans', ['plan_id'], ['id'])
    
    # Seed plan data
    plans_table = sa.table('plans',
        sa.column('name', sa.String),
        sa.column('display_name', sa.String),
        sa.column('description', sa.Text),
        sa.column('monthly_price', sa.Numeric(10, 2)),
        sa.column('annual_price', sa.Numeric(10, 2)),
        sa.column('trial_days', sa.Integer),
        sa.column('max_social_profiles', sa.Integer),
        sa.column('max_users', sa.Integer),
        sa.column('max_workspaces', sa.Integer),
        sa.column('max_posts_per_day', sa.Integer),
        sa.column('max_posts_per_week', sa.Integer),
        sa.column('features', sa.JSON),
        sa.column('full_ai', sa.Boolean),
        sa.column('enhanced_autopilot', sa.Boolean),
        sa.column('ai_inbox', sa.Boolean),
        sa.column('crm_integration', sa.Boolean),
        sa.column('advanced_analytics', sa.Boolean),
        sa.column('predictive_analytics', sa.Boolean),
        sa.column('white_label', sa.Boolean),
        sa.column('basic_ai_only', sa.Boolean),
        sa.column('premium_ai_models', sa.Boolean),
        sa.column('image_generation_limit', sa.Integer),
        sa.column('autopilot_posts_per_day', sa.Integer),
        sa.column('autopilot_research_enabled', sa.Boolean),
        sa.column('autopilot_ad_campaigns', sa.Boolean),
        sa.column('is_active', sa.Boolean),
        sa.column('is_popular', sa.Boolean),
        sa.column('sort_order', sa.Integer)
    )
    
    op.bulk_insert(plans_table, [
        {
            'name': 'starter',
            'display_name': 'Starter',
            'description': 'Perfect for individuals getting started with AI-powered social media management',
            'monthly_price': 29.00,
            'annual_price': 290.00,  # 2 months free
            'trial_days': 14,
            'max_social_profiles': 5,
            'max_users': 1,
            'max_workspaces': 1,
            'max_posts_per_day': 5,
            'max_posts_per_week': 25,
            'features': {
                'basic_content_generation': True,
                'basic_scheduling': True,
                'basic_analytics': True,
                'email_support': True
            },
            'full_ai': False,
            'enhanced_autopilot': False,
            'ai_inbox': False,
            'crm_integration': False,
            'advanced_analytics': False,
            'predictive_analytics': False,
            'white_label': False,
            'basic_ai_only': True,
            'premium_ai_models': False,
            'image_generation_limit': 10,
            'autopilot_posts_per_day': 1,
            'autopilot_research_enabled': False,
            'autopilot_ad_campaigns': False,
            'is_active': True,
            'is_popular': False,
            'sort_order': 1
        },
        {
            'name': 'pro',
            'display_name': 'Pro',
            'description': 'Advanced features for growing businesses and marketing teams',
            'monthly_price': 79.00,
            'annual_price': 790.00,  # 2 months free
            'trial_days': 14,
            'max_social_profiles': 25,
            'max_users': 5,
            'max_workspaces': 3,
            'max_posts_per_day': 15,
            'max_posts_per_week': 100,
            'features': {
                'advanced_content_generation': True,
                'multi_platform_scheduling': True,
                'advanced_analytics': True,
                'team_collaboration': True,
                'priority_support': True,
                'custom_branding': True
            },
            'full_ai': True,
            'enhanced_autopilot': True,
            'ai_inbox': True,
            'crm_integration': False,
            'advanced_analytics': True,
            'predictive_analytics': False,
            'white_label': False,
            'basic_ai_only': False,
            'premium_ai_models': True,
            'image_generation_limit': 50,
            'autopilot_posts_per_day': 5,
            'autopilot_research_enabled': True,
            'autopilot_ad_campaigns': True,
            'is_active': True,
            'is_popular': True,
            'sort_order': 2
        },
        {
            'name': 'enterprise',
            'display_name': 'Enterprise',
            'description': 'Full-featured solution for large organizations with custom requirements',
            'monthly_price': 199.00,
            'annual_price': 1990.00,  # 2 months free
            'trial_days': 30,
            'max_social_profiles': 100,
            'max_users': 25,
            'max_workspaces': 10,
            'max_posts_per_day': 50,
            'max_posts_per_week': 300,
            'features': {
                'enterprise_content_generation': True,
                'unlimited_scheduling': True,
                'enterprise_analytics': True,
                'advanced_team_management': True,
                'dedicated_support': True,
                'white_label_branding': True,
                'custom_integrations': True,
                'sso_support': True
            },
            'full_ai': True,
            'enhanced_autopilot': True,
            'ai_inbox': True,
            'crm_integration': True,
            'advanced_analytics': True,
            'predictive_analytics': True,
            'white_label': True,
            'basic_ai_only': False,
            'premium_ai_models': True,
            'image_generation_limit': 200,
            'autopilot_posts_per_day': 15,
            'autopilot_research_enabled': True,
            'autopilot_ad_campaigns': True,
            'is_active': True,
            'is_popular': False,
            'sort_order': 3
        }
    ])
    
    # Migrate existing users to Starter plan based on their current tier
    # Get the Starter plan ID
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id FROM plans WHERE name = 'starter' LIMIT 1"))
    starter_plan_id = result.fetchone()[0] if result.rowcount > 0 else None
    
    if starter_plan_id:
        # Update all existing users to use the Starter plan
        op.execute(f"UPDATE users SET plan_id = {starter_plan_id} WHERE plan_id IS NULL")


def downgrade():
    """Remove Plan model and plan_id field"""
    
    # Remove plan_id column from users table
    op.drop_constraint(None, 'users', type_='foreignkey')
    op.drop_column('users', 'plan_id')
    
    # Drop plans table
    op.drop_index(op.f('ix_plans_id'), table_name='plans')
    op.drop_table('plans')