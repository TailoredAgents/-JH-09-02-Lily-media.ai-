"""
Multi-tenant service for organization, team, and role management
Provides centralized multi-tenancy operations with proper isolation
"""
import logging
import secrets
import string
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from sqlalchemy.exc import IntegrityError

from backend.db.database import get_db
from backend.db.models import User
from backend.core.config import get_settings

logger = logging.getLogger(__name__)

class MultiTenantError(Exception):
    """Base exception for multi-tenant operations"""
    pass

class OrganizationNotFoundError(MultiTenantError):
    """Organization not found"""
    pass

class InsufficientPermissionsError(MultiTenantError):
    """User lacks required permissions"""
    pass

class MultiTenantService:
    """
    Centralized multi-tenancy management service
    
    Features:
    - Organization lifecycle management
    - Team management within organizations
    - Role-based access control (RBAC)
    - User invitation and membership management
    - Permission checking and enforcement
    """
    
    def __init__(self, db: Session = None):
        """
        Initialize multi-tenant service
        
        Args:
            db: Database session (optional, will create if not provided)
        """
        self.db = db or next(get_db())
        self.settings = get_settings()
    
    def initialize_system_data(self) -> Dict[str, int]:
        """
        Initialize system with default roles and permissions if not present
        
        Returns:
            Dictionary with counts of created entities
        """
        try:
            created_counts = {"roles": 0, "permissions": 0}
            
            # Check if system roles already exist
            existing_roles = self.db.execute(text("SELECT COUNT(*) FROM roles")).scalar()
            
            if existing_roles == 0:
                logger.info("Initializing system roles and permissions...")
                
                # Create system roles
                roles_sql = text("""
                    INSERT INTO roles (id, public_id, name, description, permissions, is_system_role, created_at) VALUES
                    (1, 'super_admin', 'super_admin', 'Full system access across all organizations', ARRAY['*'], true, NOW()),
                    (2, 'org_owner', 'org_owner', 'Full access within organization', ARRAY['organizations.*', 'teams.*', 'users.*', 'content.*', 'social_accounts.*', 'analytics.*', 'settings.*'], true, NOW()),
                    (3, 'admin', 'admin', 'Administrative access within organization', ARRAY['users.create', 'users.read', 'users.update', 'teams.read', 'teams.update', 'content.*', 'social_accounts.*', 'analytics.read', 'settings.*'], true, NOW()),
                    (4, 'manager', 'manager', 'Team management and content approval', ARRAY['users.read', 'teams.read', 'content.*', 'social_accounts.read', 'analytics.read', 'settings.read'], true, NOW()),
                    (5, 'member', 'member', 'Standard user access', ARRAY['users.read', 'teams.read', 'content.create', 'content.read', 'content.update', 'social_accounts.connect', 'social_accounts.read', 'analytics.read', 'settings.read'], true, NOW()),
                    (6, 'viewer', 'viewer', 'Read-only access', ARRAY['users.read', 'teams.read', 'content.read', 'social_accounts.read', 'analytics.read', 'settings.read'], true, NOW())
                """)
                self.db.execute(roles_sql)
                created_counts["roles"] = 6
                
                # Create system permissions  
                permissions_sql = text("""
                    INSERT INTO permissions (id, public_id, name, description, resource, action, created_at) VALUES
                    (1, 'users_create', 'users.create', 'Create new user accounts', 'users', 'create', NOW()),
                    (2, 'users_read', 'users.read', 'View user information', 'users', 'read', NOW()),
                    (3, 'users_update', 'users.update', 'Update user information', 'users', 'update', NOW()),
                    (4, 'users_delete', 'users.delete', 'Delete user accounts', 'users', 'delete', NOW()),
                    (5, 'organizations_create', 'organizations.create', 'Create new organizations', 'organizations', 'create', NOW()),
                    (6, 'organizations_read', 'organizations.read', 'View organization information', 'organizations', 'read', NOW()),
                    (7, 'organizations_update', 'organizations.update', 'Update organization settings', 'organizations', 'update', NOW()),
                    (8, 'organizations_delete', 'organizations.delete', 'Delete organizations', 'organizations', 'delete', NOW()),
                    (9, 'teams_create', 'teams.create', 'Create new teams', 'teams', 'create', NOW()),
                    (10, 'teams_read', 'teams.read', 'View team information', 'teams', 'read', NOW()),
                    (11, 'teams_update', 'teams.update', 'Update team settings', 'teams', 'update', NOW()),
                    (12, 'teams_delete', 'teams.delete', 'Delete teams', 'teams', 'delete', NOW()),
                    (13, 'content_create', 'content.create', 'Create new content', 'content', 'create', NOW()),
                    (14, 'content_read', 'content.read', 'View content', 'content', 'read', NOW()),
                    (15, 'content_update', 'content.update', 'Edit content', 'content', 'update', NOW()),
                    (16, 'content_delete', 'content.delete', 'Delete content', 'content', 'delete', NOW()),
                    (17, 'content_publish', 'content.publish', 'Publish content to social platforms', 'content', 'publish', NOW()),
                    (18, 'social_accounts_connect', 'social_accounts.connect', 'Connect social media accounts', 'social_accounts', 'connect', NOW()),
                    (19, 'social_accounts_read', 'social_accounts.read', 'View connected social accounts', 'social_accounts', 'read', NOW()),
                    (20, 'social_accounts_disconnect', 'social_accounts.disconnect', 'Disconnect social media accounts', 'social_accounts', 'disconnect', NOW()),
                    (21, 'analytics_read', 'analytics.read', 'View performance analytics', 'analytics', 'read', NOW()),
                    (22, 'settings_read', 'settings.read', 'View organization/team settings', 'settings', 'read', NOW()),
                    (23, 'settings_update', 'settings.update', 'Update organization/team settings', 'settings', 'update', NOW())
                """)
                self.db.execute(permissions_sql)
                created_counts["permissions"] = 23
                
                self.db.commit()
                logger.info(f"Created {created_counts['roles']} roles and {created_counts['permissions']} permissions")
            else:
                logger.info("System roles and permissions already exist")
            
            return created_counts
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to initialize system data: {e}")
            raise MultiTenantError(f"System initialization failed: {e}")
    
    def create_organization(
        self,
        name: str,
        slug: str,
        owner_id: int,
        description: str = None,
        plan_type: str = "starter"
    ) -> Dict[str, Any]:
        """
        Create a new organization
        
        Args:
            name: Organization name
            slug: URL-friendly identifier
            owner_id: ID of user who will own the organization
            description: Optional description
            plan_type: Subscription plan type
            
        Returns:
            Organization data dictionary
            
        Raises:
            MultiTenantError: If organization creation fails
        """
        try:
            # Check if slug is already taken
            existing = self.db.execute(
                text("SELECT id FROM organizations WHERE slug = :slug"),
                {"slug": slug}
            ).first()
            
            if existing:
                raise MultiTenantError(f"Organization slug '{slug}' is already taken")
            
            # Create organization
            org_sql = text("""
                INSERT INTO organizations (
                    public_id, name, slug, description, subscription_plan, 
                    subscription_status, max_users, max_social_accounts, 
                    created_by_id, is_active, created_at, updated_at
                ) VALUES (
                    :public_id, :name, :slug, :description, :plan_type,
                    'active', :max_users, :max_accounts,
                    :owner_id, true, NOW(), NOW()
                )
                RETURNING id, public_id, name, slug, created_at
            """)
            
            result = self.db.execute(org_sql, {
                "public_id": secrets.token_urlsafe(16),
                "name": name,
                "slug": slug,
                "description": description,
                "plan_type": plan_type,
                "max_users": 10 if plan_type == "starter" else 50,
                "max_accounts": 3 if plan_type == "starter" else 10,
                "owner_id": owner_id
            }).first()
            
            if not result:
                raise MultiTenantError("Failed to create organization")
            
            org_id = result[0]
            
            # Create default team
            team_sql = text("""
                INSERT INTO teams (
                    public_id, organization_id, name, description, 
                    is_default, created_by_id, created_at, updated_at
                ) VALUES (
                    :public_id, :org_id, 'Default Team', 'Default team for all organization members',
                    true, :owner_id, NOW(), NOW()
                )
                RETURNING id, public_id
            """)
            
            team_result = self.db.execute(team_sql, {
                "public_id": secrets.token_urlsafe(16),
                "org_id": org_id,
                "owner_id": owner_id
            }).first()
            
            # Assign owner role to creator
            user_role_sql = text("""
                INSERT INTO user_organization_roles (
                    public_id, user_id, organization_id, role_id,
                    assigned_by_id, assigned_at, is_active, created_at, updated_at
                ) VALUES (
                    :public_id, :user_id, :org_id, 
                    (SELECT id FROM roles WHERE name = 'org_owner'),
                    :owner_id, NOW(), true, NOW(), NOW()
                )
            """)
            
            self.db.execute(user_role_sql, {
                "public_id": secrets.token_urlsafe(16),
                "user_id": owner_id,
                "org_id": org_id,
                "owner_id": owner_id
            })
            
            self.db.commit()
            
            logger.info(f"Created organization '{name}' (slug: {slug}) for user {owner_id}")
            
            return {
                "id": org_id,
                "public_id": result[1],
                "name": result[2],
                "slug": result[3],
                "default_team_id": team_result[0] if team_result else None,
                "created_at": result[4].isoformat()
            }
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Organization creation failed (integrity): {e}")
            raise MultiTenantError("Organization slug must be unique")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Organization creation failed: {e}")
            raise MultiTenantError(f"Organization creation failed: {e}")
    
    def get_user_organizations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all organizations a user belongs to
        
        Args:
            user_id: User ID
            
        Returns:
            List of organization dictionaries
        """
        try:
            query = text("""
                SELECT DISTINCT 
                    o.id, o.public_id, o.name, o.slug, o.description, o.subscription_plan,
                    r.name as role_name, uro.assigned_at, o.created_at
                FROM organizations o
                LEFT JOIN user_organization_roles uro ON o.id = uro.organization_id AND uro.user_id = :user_id
                LEFT JOIN roles r ON uro.role_id = r.id
                WHERE uro.user_id = :user_id AND uro.is_active = true
                ORDER BY o.name
            """)
            
            results = self.db.execute(query, {"user_id": user_id}).fetchall()
            
            organizations = []
            for row in results:
                organizations.append({
                    "id": row[0],
                    "public_id": row[1],
                    "name": row[2],
                    "slug": row[3],
                    "description": row[4],
                    "plan_type": row[5],
                    "user_role": row[6],
                    "joined_at": row[7].isoformat() if row[7] else None,
                    "created_at": row[8].isoformat()
                })
            
            return organizations
            
        except Exception as e:
            logger.error(f"Failed to get user organizations: {e}")
            return []
    
    def check_user_permission(
        self, 
        user_id: int, 
        organization_id: int, 
        permission: str
    ) -> bool:
        """
        Check if user has specific permission in organization
        
        Args:
            user_id: User ID
            organization_id: Organization ID  
            permission: Permission string (e.g., 'content.create')
            
        Returns:
            True if user has permission, False otherwise
        """
        try:
            query = text("""
                SELECT COUNT(*) > 0
                FROM user_organization_roles uro
                JOIN roles r ON uro.role_id = r.id
                WHERE uro.user_id = :user_id 
                AND uro.organization_id = :org_id
                AND uro.is_active = true
                AND (
                    :permission = ANY(r.permissions)
                    OR '*' = ANY(r.permissions)
                    OR :resource_wildcard = ANY(r.permissions)
                )
            """)
            
            # Extract resource for wildcard permission checking
            resource = permission.split('.')[0] if '.' in permission else permission
            resource_wildcard = f"{resource}.*"
            
            result = self.db.execute(query, {
                "user_id": user_id,
                "org_id": organization_id,
                "permission": permission,
                "resource_wildcard": resource_wildcard
            }).scalar()
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return False
    
    def get_organization_members(self, organization_id: int) -> List[Dict[str, Any]]:
        """
        Get all members of an organization
        
        Args:
            organization_id: Organization ID
            
        Returns:
            List of member dictionaries
        """
        try:
            query = text("""
                SELECT 
                    u.id, u.public_id, u.email, u.username, u.full_name,
                    r.name as role_name, uro.assigned_at, uro.is_active
                FROM users u
                JOIN user_organization_roles uro ON u.id = uro.user_id
                JOIN roles r ON uro.role_id = r.id
                WHERE uro.organization_id = :org_id
                ORDER BY uro.assigned_at
            """)
            
            results = self.db.execute(query, {"org_id": organization_id}).fetchall()
            
            members = []
            for row in results:
                members.append({
                    "id": row[0],
                    "public_id": row[1],
                    "email": row[2],
                    "username": row[3],
                    "full_name": row[4],
                    "role": row[5],
                    "joined_at": row[6].isoformat() if row[6] else None,
                    "is_active": row[7]
                })
            
            return members
            
        except Exception as e:
            logger.error(f"Failed to get organization members: {e}")
            return []
    
    def assign_user_role(
        self,
        user_id: int,
        organization_id: int,
        role_name: str,
        assigned_by_id: int
    ) -> bool:
        """
        Assign role to user in organization
        
        Args:
            user_id: User to assign role to
            organization_id: Organization ID
            role_name: Role name to assign
            assigned_by_id: User performing the assignment
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if role exists
            role_query = text("SELECT id FROM roles WHERE name = :role_name")
            role_result = self.db.execute(role_query, {"role_name": role_name}).first()
            
            if not role_result:
                logger.error(f"Role '{role_name}' not found")
                return False
            
            role_id = role_result[0]
            
            # Update or insert role assignment
            upsert_sql = text("""
                INSERT INTO user_organization_roles (
                    public_id, user_id, organization_id, role_id,
                    assigned_by_id, assigned_at, is_active, created_at, updated_at
                ) VALUES (
                    :public_id, :user_id, :org_id, :role_id,
                    :assigned_by_id, NOW(), true, NOW(), NOW()
                )
                ON CONFLICT (user_id, organization_id) 
                DO UPDATE SET
                    role_id = EXCLUDED.role_id,
                    assigned_by_id = EXCLUDED.assigned_by_id,
                    assigned_at = EXCLUDED.assigned_at,
                    is_active = true,
                    updated_at = NOW()
            """)
            
            self.db.execute(upsert_sql, {
                "public_id": secrets.token_urlsafe(16),
                "user_id": user_id,
                "org_id": organization_id,
                "role_id": role_id,
                "assigned_by_id": assigned_by_id
            })
            
            self.db.commit()
            logger.info(f"Assigned role '{role_name}' to user {user_id} in organization {organization_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to assign user role: {e}")
            return False
    
    def cleanup_expired_invitations(self, older_than_days: int = 7) -> int:
        """
        Clean up expired organization invitations
        
        Args:
            older_than_days: Remove invitations older than this many days
            
        Returns:
            Number of invitations cleaned up
        """
        try:
            cleanup_sql = text("""
                DELETE FROM organization_invitations
                WHERE status = 'pending' 
                AND expires_at < NOW() - INTERVAL ':days days'
            """)
            
            result = self.db.execute(cleanup_sql, {"days": older_than_days})
            count = result.rowcount
            self.db.commit()
            
            logger.info(f"Cleaned up {count} expired organization invitations")
            return count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to cleanup expired invitations: {e}")
            return 0


# Singleton service instance
_multi_tenant_service = None

def get_multi_tenant_service(db: Session = None) -> MultiTenantService:
    """Get singleton multi-tenant service instance"""
    global _multi_tenant_service
    if _multi_tenant_service is None or db is not None:
        _multi_tenant_service = MultiTenantService(db)
    return _multi_tenant_service