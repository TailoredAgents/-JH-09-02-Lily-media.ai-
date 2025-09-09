"""
Multi-tenant models for organizations, teams, and role-based access control
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.db.database import Base
import uuid

# Note: User model is imported in models.py to avoid circular imports

# Association table for many-to-many relationship between users and teams
user_teams = Table(
    'user_teams',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('team_id', String, ForeignKey('teams.id'), primary_key=True),
    Column('role', String, nullable=False, default='member'),  # owner, admin, member, viewer
    Column('joined_at', DateTime(timezone=True), server_default=func.now()),
    Column('is_active', Boolean, default=True)
)

# Association table for role permissions
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', String, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', String, ForeignKey('permissions.id'), primary_key=True)
)

class Organization(Base):
    """
    Organization model for multi-tenancy
    Each organization can have multiple teams and users
    """
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)  # URL-friendly identifier
    description = Column(Text)
    
    # Organization settings
    plan_type = Column(String, default="starter")  # starter, professional, enterprise
    max_users = Column(Integer, default=5)  # Limit based on plan
    max_teams = Column(Integer, default=2)
    max_social_accounts = Column(Integer, default=3)
    
    # Billing and subscription
    subscription_status = Column(String, default="active")  # active, suspended, cancelled
    billing_email = Column(String)
    
    # Organization metadata
    settings = Column(JSON, default={})
    features_enabled = Column(JSON, default=["basic_posting", "scheduling", "analytics"])
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Owner relationship
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", foreign_keys=[owner_id], overlaps="owned_organizations")
    
    # Relationships
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")
    invitations = relationship("OrganizationInvitation", back_populates="organization", cascade="all, delete-orphan")
    social_connections = relationship("SocialConnection", back_populates="organization", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization(name='{self.name}', slug='{self.slug}')>"

class Team(Base):
    """
    Team model for organizing users within an organization
    """
    __tablename__ = "teams"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Team settings
    default_role = Column(String, default="member")  # Default role for new team members
    is_default = Column(Boolean, default=False)  # Is this the default team for the org?
    
    # Team metadata
    settings = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Creator relationship
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    # Relationships
    organization = relationship("Organization", back_populates="teams")
    members = relationship("User", secondary=user_teams, back_populates="teams")

    # Ensure team names are unique within an organization
    __table_args__ = (
        UniqueConstraint('organization_id', 'name', name='uq_org_team_name'),
    )

    def __repr__(self):
        return f"<Team(name='{self.name}', org='{self.organization_id}')>"

class Role(Base):
    """
    Role model for role-based access control
    """
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)  # super_admin, org_owner, admin, member, viewer
    display_name = Column(String, nullable=False)
    description = Column(Text)
    
    # Role hierarchy
    level = Column(Integer, nullable=False)  # Higher number = more permissions
    is_system_role = Column(Boolean, default=False)  # System roles cannot be deleted
    
    # Role metadata
    color = Column(String, default="#6B7280")  # UI color for role badge
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

    def __repr__(self):
        return f"<Role(name='{self.name}', level={self.level})>"

class Permission(Base):
    """
    Permission model for granular access control
    """
    __tablename__ = "permissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)  # users.create, posts.publish, etc.
    display_name = Column(String, nullable=False)
    description = Column(Text)
    resource = Column(String, nullable=False)  # users, posts, organizations, etc.
    action = Column(String, nullable=False)  # create, read, update, delete, publish, etc.
    
    # Permission metadata
    is_system_permission = Column(Boolean, default=False)  # System permissions cannot be deleted
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    # Ensure permission names are unique
    __table_args__ = (
        UniqueConstraint('resource', 'action', name='uq_resource_action'),
    )

    def __repr__(self):
        return f"<Permission(name='{self.name}', resource='{self.resource}', action='{self.action}')>"

class OrganizationInvitation(Base):
    """
    Organization invitation model for inviting users to join organizations
    """
    __tablename__ = "organization_invitations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)  # Optional specific team
    
    # Invitation details
    email = Column(String, nullable=False)
    role = Column(String, nullable=False, default="member")
    token = Column(String, unique=True, nullable=False)  # Secure invitation token
    
    # Invitation status
    status = Column(String, default="pending")  # pending, accepted, expired, cancelled
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True))
    
    # User relationships
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invited_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Set when accepted
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="invitations")
    team = relationship("Team")
    invited_by = relationship("User", foreign_keys=[invited_by_id], overlaps="sent_invitations")
    invited_user = relationship("User", foreign_keys=[invited_user_id], overlaps="received_invitations")

    def __repr__(self):
        return f"<OrganizationInvitation(email='{self.email}', org='{self.organization_id}', status='{self.status}')>"

class UserOrganizationRole(Base):
    """
    User's role within an organization (separate from team roles)
    """
    __tablename__ = "user_organization_roles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    role_id = Column(String, ForeignKey("roles.id"), nullable=False)
    
    # Role assignment details
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization")
    role = relationship("Role")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])

    # Ensure unique user-organization-role combination
    __table_args__ = (
        UniqueConstraint('user_id', 'organization_id', name='uq_user_organization'),
    )

    def __repr__(self):
        return f"<UserOrganizationRole(user={self.user_id}, org={self.organization_id}, role={self.role_id})>"