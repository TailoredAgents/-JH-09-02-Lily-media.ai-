"""Convert to open SaaS authentication model

Revision ID: 016_open_saas_auth
Revises: 015_upgrade_embeddings
Create Date: 2025-08-25 16:00:00.000000

This migration:
1. Adds email verification fields to users table
2. Adds password reset token fields
3. Adds subscription/tier management fields  
4. Removes registration_key_id foreign key
5. Drops registration_keys table
6. Backfills existing users
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from datetime import datetime

# revision identifiers
revision = '016_open_saas_auth'
down_revision = '015_upgrade_embeddings'
branch_labels = None
depends_on = None

def upgrade():
    """
    Convert from registration-key system to open SaaS authentication
    """
    
    # Step 1: Add new columns to users table
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('email_verification_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('email_verification_sent_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('password_reset_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('password_reset_sent_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('subscription_status', sa.String(50), nullable=False, server_default='active'))
    op.add_column('users', sa.Column('subscription_end_date', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('stripe_subscription_id', sa.String(255), nullable=True))
    
    # Step 2: Create indexes for new fields
    op.create_index('ix_users_email_verification_token', 'users', ['email_verification_token'])
    op.create_index('ix_users_password_reset_token', 'users', ['password_reset_token'])
    op.create_index('ix_users_stripe_customer_id', 'users', ['stripe_customer_id'])
    
    # Step 3: Backfill existing users
    # Mark all existing users as email_verified=true since they're already active
    op.execute(text("UPDATE users SET email_verified = true WHERE is_active = true"))
    
    # Make the first user (lowest ID) a superuser if no admins exist
    op.execute(text("""
        UPDATE users 
        SET is_superuser = true 
        WHERE id = (SELECT MIN(id) FROM users)
        AND NOT EXISTS (SELECT 1 FROM admin_users LIMIT 1)
    """))
    
    # Set subscription status based on existing tier
    op.execute(text("""
        UPDATE users 
        SET subscription_status = CASE 
            WHEN tier = 'premium' THEN 'active'
            WHEN tier = 'enterprise' THEN 'active'
            ELSE 'free'
        END
    """))
    
    # Step 4: Drop foreign key constraint to registration_keys table
    try:
        op.drop_constraint('users_registration_key_id_fkey', 'users', type_='foreignkey')
    except:
        pass  # Constraint might not exist in all environments
    
    # Step 5: Drop registration_key_id column from users table
    try:
        op.drop_column('users', 'registration_key_id')
    except:
        pass  # Column might not exist in all environments
    
    # Step 6: Drop registration_keys table
    try:
        op.drop_table('registration_keys')
    except:
        pass  # Table might not exist in all environments
    
    # Step 7: Add tier constraints if not exists
    op.execute(text("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'user_tier_enum'
            ) THEN
                CREATE TYPE user_tier_enum AS ENUM ('free', 'premium', 'enterprise');
            END IF;
        END$$;
    """))
    
    # Step 8: Update tier column to use enum (if it's just a string)
    try:
        op.execute(text("""
            ALTER TABLE users 
            ALTER COLUMN tier TYPE user_tier_enum 
            USING tier::user_tier_enum
        """))
    except:
        pass  # Column might already be the correct type

def downgrade():
    """
    Revert to registration-key based system
    """
    
    # Step 1: Recreate registration_keys table
    op.create_table('registration_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('max_uses', sa.Integer(), nullable=True, default=1),
        sa.Column('current_uses', sa.Integer(), nullable=True, default=0),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('email_domain_restriction', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    
    # Step 2: Add registration_key_id back to users table
    op.add_column('users', sa.Column('registration_key_id', sa.String(), nullable=True))
    
    # Step 3: Remove new columns
    op.drop_index('ix_users_email_verification_token', 'users')
    op.drop_index('ix_users_password_reset_token', 'users')
    op.drop_index('ix_users_stripe_customer_id', 'users')
    
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'email_verification_sent_at')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'password_reset_sent_at')
    op.drop_column('users', 'is_superuser')
    op.drop_column('users', 'subscription_status')
    op.drop_column('users', 'subscription_end_date')
    op.drop_column('users', 'stripe_customer_id')
    op.drop_column('users', 'stripe_subscription_id')