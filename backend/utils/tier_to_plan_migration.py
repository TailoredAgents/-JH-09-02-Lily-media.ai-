"""
Tier to Plan Migration Utility

Migrates legacy tier system to plan_id based system.
Part of P1-5a: Migrate from legacy tier system to plan_id
"""

import logging
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.db.models import User, Plan
try:
    from backend.core.database import get_db
except ImportError:
    # Alternative import for database
    from backend.db.database import get_db
from backend.core.tiers import SubscriptionTier

logger = logging.getLogger(__name__)

class TierToPlanMigrator:
    """Utility class to migrate from legacy tier system to plan_id"""
    
    def __init__(self, db: Session):
        self.db = db
        self._tier_to_plan_mapping = None
        
    def get_tier_to_plan_mapping(self) -> Dict[str, int]:
        """Get mapping from legacy tier names to plan IDs"""
        if self._tier_to_plan_mapping is None:
            # Build mapping from database
            plans = self.db.query(Plan).all()
            
            # Map legacy tier names to plan IDs
            mapping = {}
            for plan in plans:
                # Map based on plan names
                if plan.name.lower() in ['starter', 'free', 'basic']:
                    mapping['base'] = plan.id
                elif plan.name.lower() in ['pro', 'professional']:
                    mapping['pro'] = plan.id
                elif plan.name.lower() in ['enterprise', 'business']:
                    mapping['enterprise'] = plan.id
                elif plan.name.lower() in ['mid', 'standard', 'plus']:
                    mapping['mid'] = plan.id
            
            self._tier_to_plan_mapping = mapping
            logger.info(f"Tier to plan mapping: {mapping}")
        
        return self._tier_to_plan_mapping
    
    def get_plan_from_tier(self, tier: str) -> Optional[int]:
        """Convert legacy tier string to plan_id"""
        mapping = self.get_tier_to_plan_mapping()
        return mapping.get(tier)
    
    def migrate_user_tiers_to_plans(self) -> Dict[str, int]:
        """Migrate all users from tier to plan_id"""
        try:
            # Get users who have tier but no plan_id
            users_to_migrate = self.db.query(User).filter(
                User.tier.isnot(None),
                User.plan_id.is_(None)
            ).all()
            
            migration_stats = {
                'total_users': len(users_to_migrate),
                'migrated': 0,
                'errors': 0,
                'by_tier': {}
            }
            
            mapping = self.get_tier_to_plan_mapping()
            
            for user in users_to_migrate:
                try:
                    plan_id = mapping.get(user.tier)
                    if plan_id:
                        user.plan_id = plan_id
                        migration_stats['migrated'] += 1
                        migration_stats['by_tier'][user.tier] = migration_stats['by_tier'].get(user.tier, 0) + 1
                        logger.debug(f"Migrated user {user.id} from tier '{user.tier}' to plan_id {plan_id}")
                    else:
                        logger.warning(f"No plan mapping found for tier '{user.tier}' for user {user.id}")
                        migration_stats['errors'] += 1
                        
                except Exception as e:
                    logger.error(f"Error migrating user {user.id}: {e}")
                    migration_stats['errors'] += 1
            
            # Commit changes
            self.db.commit()
            logger.info(f"Migration completed: {migration_stats}")
            return migration_stats
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.db.rollback()
            raise
    
    def verify_migration(self) -> Dict[str, Any]:
        """Verify migration was successful"""
        try:
            # Count users by migration status
            total_users = self.db.query(User).count()
            users_with_plan = self.db.query(User).filter(User.plan_id.isnot(None)).count()
            users_with_tier_only = self.db.query(User).filter(
                User.tier.isnot(None),
                User.plan_id.is_(None)
            ).count()
            
            # Get tier distribution for remaining unmigrated users
            unmigrated_tiers = self.db.execute(
                text("SELECT tier, COUNT(*) FROM users WHERE tier IS NOT NULL AND plan_id IS NULL GROUP BY tier")
            ).fetchall()
            
            return {
                'total_users': total_users,
                'users_with_plan': users_with_plan,
                'users_with_tier_only': users_with_tier_only,
                'migration_percentage': round((users_with_plan / total_users) * 100, 2) if total_users > 0 else 0,
                'unmigrated_tiers': dict(unmigrated_tiers) if unmigrated_tiers else {}
            }
            
        except Exception as e:
            logger.error(f"Migration verification failed: {e}")
            return {'error': str(e)}


def get_user_plan_capabilities(user: User, db: Session) -> Dict[str, Any]:
    """Get user plan capabilities (new plan-based approach)"""
    if user.plan_id and user.plan:
        # Use plan-based capabilities
        plan = user.plan
        return {
            'plan_id': plan.id,
            'plan_name': plan.name,
            'plan_display_name': plan.display_name,
            'capabilities': {
                'max_social_profiles': plan.max_social_profiles,
                'max_users': plan.max_users,
                'max_posts_per_day': plan.max_posts_per_day,
                'max_posts_per_week': plan.max_posts_per_week,
                'image_generation_limit': plan.image_generation_limit,
                'research_enabled': plan.research_enabled,
                'premium_ai_models': plan.premium_ai_models,
                'advanced_analytics': plan.advanced_analytics,
                'custom_branding': plan.custom_branding,
                'priority_support': plan.priority_support,
                'api_access': plan.api_access
            }
        }
    
    # Fallback to legacy tier system
    elif user.tier:
        logger.warning(f"User {user.id} still using legacy tier system: {user.tier}")
        return _get_legacy_tier_capabilities(user.tier)
    
    # Default to free plan capabilities
    else:
        return _get_default_plan_capabilities()


def _get_legacy_tier_capabilities(tier: str) -> Dict[str, Any]:
    """Legacy tier capabilities mapping (deprecated)"""
    legacy_mapping = {
        'base': {
            'max_social_profiles': 3,
            'max_posts_per_day': 5,
            'image_generation_limit': 10,
            'research_enabled': True,
            'premium_ai_models': False
        },
        'mid': {
            'max_social_profiles': 5,
            'max_posts_per_day': 15,
            'image_generation_limit': 50,
            'research_enabled': True,
            'premium_ai_models': True
        },
        'pro': {
            'max_social_profiles': 10,
            'max_posts_per_day': 50,
            'image_generation_limit': 200,
            'research_enabled': True,
            'premium_ai_models': True
        },
        'enterprise': {
            'max_social_profiles': -1,  # unlimited
            'max_posts_per_day': -1,
            'image_generation_limit': -1,
            'research_enabled': True,
            'premium_ai_models': True
        }
    }
    
    return {
        'plan_name': tier,
        'capabilities': legacy_mapping.get(tier, legacy_mapping['base']),
        'legacy': True
    }


def _get_default_plan_capabilities() -> Dict[str, Any]:
    """Default free plan capabilities"""
    return {
        'plan_name': 'free',
        'capabilities': {
            'max_social_profiles': 2,
            'max_posts_per_day': 3,
            'image_generation_limit': 5,
            'research_enabled': False,
            'premium_ai_models': False
        },
        'default': True
    }


# Migration utility functions for backward compatibility
def migrate_tier_reference(tier_value: str, db: Session) -> Optional[int]:
    """Convert tier reference to plan_id (for code migration)"""
    migrator = TierToPlanMigrator(db)
    return migrator.get_plan_from_tier(tier_value)


def is_migration_needed(db: Session) -> bool:
    """Check if migration is still needed"""
    users_needing_migration = db.query(User).filter(
        User.tier.isnot(None),
        User.plan_id.is_(None)
    ).count()
    
    return users_needing_migration > 0


def run_migration_if_needed(db: Session) -> Dict[str, Any]:
    """Run migration only if needed"""
    if is_migration_needed(db):
        logger.info("Running tier to plan migration...")
        migrator = TierToPlanMigrator(db)
        stats = migrator.migrate_user_tiers_to_plans()
        verification = migrator.verify_migration()
        return {
            'migration_run': True,
            'stats': stats,
            'verification': verification
        }
    else:
        logger.info("No migration needed - all users already have plan_id")
        return {'migration_run': False, 'message': 'Migration not needed'}