#!/usr/bin/env python3
"""
Tier to Plan Migration Script

Migrates legacy tier system to plan_id based system.
Part of P1-5a: Migrate from legacy tier system to plan_id

Usage:
    python scripts/migrate_tiers_to_plans.py [--dry-run] [--force]
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from backend.core.database import SessionLocal
except ImportError:
    # Try alternative import path
    from backend.db.database import engine
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
from backend.db.models import User, Plan
from backend.utils.tier_to_plan_migration import (
    TierToPlanMigrator, 
    is_migration_needed,
    run_migration_if_needed
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_default_plans_if_missing(db):
    """Create default plans if they don't exist"""
    existing_plans = db.query(Plan).count()
    
    if existing_plans == 0:
        logger.info("No plans found, creating default plans...")
        
        default_plans = [
            {
                'name': 'free',
                'display_name': 'Free',
                'description': 'Basic features for personal use',
                'monthly_price': 0.00,
                'annual_price': 0.00,
                'trial_days': 0,
                'max_social_profiles': 2,
                'max_users': 1,
                'max_workspaces': 1,
                'max_posts_per_day': 3,
                'max_posts_per_week': 15,
                'image_generation_limit': 5,
                'research_enabled': False,
                'premium_ai_models': False,
                'advanced_analytics': False,
                'custom_branding': False,
                'priority_support': False,
                'api_access': False
            },
            {
                'name': 'starter',
                'display_name': 'Starter',
                'description': 'Perfect for small businesses and personal brands',
                'monthly_price': 19.00,
                'annual_price': 190.00,
                'trial_days': 14,
                'max_social_profiles': 5,
                'max_users': 2,
                'max_workspaces': 1,
                'max_posts_per_day': 10,
                'max_posts_per_week': 50,
                'image_generation_limit': 25,
                'research_enabled': True,
                'premium_ai_models': False,
                'advanced_analytics': True,
                'custom_branding': False,
                'priority_support': False,
                'api_access': False
            },
            {
                'name': 'pro',
                'display_name': 'Pro',
                'description': 'Advanced features for growing businesses',
                'monthly_price': 49.00,
                'annual_price': 490.00,
                'trial_days': 14,
                'max_social_profiles': 10,
                'max_users': 5,
                'max_workspaces': 3,
                'max_posts_per_day': 25,
                'max_posts_per_week': 150,
                'image_generation_limit': 100,
                'research_enabled': True,
                'premium_ai_models': True,
                'advanced_analytics': True,
                'custom_branding': True,
                'priority_support': True,
                'api_access': True
            },
            {
                'name': 'enterprise',
                'display_name': 'Enterprise',
                'description': 'Full-featured solution for large organizations',
                'monthly_price': 199.00,
                'annual_price': 1990.00,
                'trial_days': 30,
                'max_social_profiles': -1,  # unlimited
                'max_users': -1,  # unlimited
                'max_workspaces': -1,  # unlimited
                'max_posts_per_day': -1,  # unlimited
                'max_posts_per_week': -1,  # unlimited
                'image_generation_limit': -1,  # unlimited
                'research_enabled': True,
                'premium_ai_models': True,
                'advanced_analytics': True,
                'custom_branding': True,
                'priority_support': True,
                'api_access': True
            }
        ]
        
        for plan_data in default_plans:
            plan = Plan(**plan_data)
            db.add(plan)
        
        db.commit()
        logger.info(f"Created {len(default_plans)} default plans")
        
        return len(default_plans)
    
    else:
        logger.info(f"Found {existing_plans} existing plans")
        return 0


def show_migration_preview(db):
    """Show what would be migrated"""
    print("\n📊 Migration Preview")
    print("=" * 50)
    
    # Get users needing migration
    users_to_migrate = db.query(User).filter(
        User.tier.isnot(None),
        User.plan_id.is_(None)
    ).all()
    
    if not users_to_migrate:
        print("✅ No users need migration (all users already have plan_id)")
        return
    
    print(f"👥 Users needing migration: {len(users_to_migrate)}")
    
    # Group by tier
    tier_counts = {}
    for user in users_to_migrate:
        tier_counts[user.tier] = tier_counts.get(user.tier, 0) + 1
    
    print("\n📈 Tier distribution:")
    for tier, count in tier_counts.items():
        print(f"   {tier}: {count} users")
    
    # Show plan mapping
    print("\n🔄 Tier to Plan mapping:")
    migrator = TierToPlanMigrator(db)
    mapping = migrator.get_tier_to_plan_mapping()
    plans = db.query(Plan).all()
    plan_lookup = {p.id: p.display_name for p in plans}
    
    for tier, plan_id in mapping.items():
        plan_name = plan_lookup.get(plan_id, f"Plan ID {plan_id}")
        user_count = tier_counts.get(tier, 0)
        print(f"   {tier} → {plan_name} ({user_count} users)")
    
    print()


def run_migration(dry_run=False, force=False):
    """Run the migration"""
    db = SessionLocal()
    
    try:
        print("🚀 Starting Tier to Plan Migration")
        print("=" * 40)
        
        # Create plans if missing
        plans_created = create_default_plans_if_missing(db)
        
        # Check if migration is needed
        if not is_migration_needed(db) and not force:
            print("✅ Migration not needed - all users already have plan_id")
            return
        
        # Show preview
        show_migration_preview(db)
        
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
            return
        
        # Confirm before proceeding
        if not force:
            response = input("Proceed with migration? (y/N): ")
            if response.lower() != 'y':
                print("Migration cancelled")
                return
        
        # Run migration
        print("\n🔄 Running migration...")
        result = run_migration_if_needed(db)
        
        if result['migration_run']:
            stats = result['stats']
            verification = result['verification']
            
            print(f"\n✅ Migration completed successfully!")
            print(f"   Total users: {stats['total_users']}")
            print(f"   Migrated: {stats['migrated']}")
            print(f"   Errors: {stats['errors']}")
            
            if stats['by_tier']:
                print("   Migration by tier:")
                for tier, count in stats['by_tier'].items():
                    print(f"     {tier}: {count} users")
            
            print(f"\n📊 Verification:")
            print(f"   Users with plan_id: {verification['users_with_plan']}")
            print(f"   Migration percentage: {verification['migration_percentage']}%")
            
            if verification['unmigrated_tiers']:
                print("   ⚠️  Unmigrated tiers remain:")
                for tier, count in verification['unmigrated_tiers'].items():
                    print(f"     {tier}: {count} users")
        else:
            print(result['message'])
    
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        logger.error(f"Migration error: {e}", exc_info=True)
        db.rollback()
    
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Migrate legacy tier system to plan_id')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be migrated without making changes')
    parser.add_argument('--force', action='store_true',
                       help='Force migration even if not needed')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    run_migration(dry_run=args.dry_run, force=args.force)


if __name__ == '__main__':
    main()