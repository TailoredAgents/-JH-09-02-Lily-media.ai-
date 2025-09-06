#!/usr/bin/env python3
"""
Direct script to create the super admin account
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set required environment variables if not set
if 'DATABASE_URL' not in os.environ:
    print("Error: DATABASE_URL environment variable not set")
    print("Please set it to your production database URL")
    sys.exit(1)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from backend.db.admin_models import AdminUser, AdminRole

# Initialize password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_super_admin():
    """Create the super admin account"""
    
    # Super admin credentials - GET FROM ENVIRONMENT FOR SECURITY
    username = os.getenv("ADMIN_USERNAME", "superadmin")
    email = os.getenv("ADMIN_EMAIL", "admin@company.com") 
    password = os.getenv("ADMIN_PASSWORD")
    
    if not password:
        print("❌ CRITICAL: ADMIN_PASSWORD environment variable must be set")
        print("   Example: export ADMIN_PASSWORD='your_secure_admin_password'")
        sys.exit(1)
    
    # Get database URL from environment
    database_url = os.environ['DATABASE_URL'].replace("postgresql+asyncpg://", "postgresql://")
    
    # Create database engine
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    print("\n" + "="*60)
    print("LILY AI SOCIAL MEDIA - CREATING SUPER ADMIN")
    print("="*60)
    
    # Create session
    db = SessionLocal()
    
    try:
        # Check if super admin already exists
        existing_admin = db.query(AdminUser).filter(
            (AdminUser.email == email) | (AdminUser.username == username)
        ).first()
        
        if existing_admin:
            print(f"\nAdmin already exists:")
            print(f"Username: {existing_admin.username}")
            print(f"Email: {existing_admin.email}")
            print(f"Role: {existing_admin.role}")
            
            if existing_admin.role != AdminRole.SUPER_ADMIN:
                # Update to super admin
                existing_admin.role = AdminRole.SUPER_ADMIN
                existing_admin.hashed_password = pwd_context.hash(password)
                db.commit()
                print("\nUpdated existing admin to SUPER_ADMIN role")
            else:
                print("\nSuper admin already exists - no changes made")
            
            return True
        
        # Create the super admin
        super_admin = AdminUser(
            username=username,
            email=email,
            hashed_password=pwd_context.hash(password),
            role=AdminRole.SUPER_ADMIN,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            last_login=None
        )
        
        db.add(super_admin)
        db.commit()
        
        print("\n" + "="*60)
        print("SUCCESS: Super Admin created!")
        print("="*60)
        print(f"\nUsername: {username}")
        print(f"Email: {email}")
        print(f"Role: SUPER_ADMIN")
        print(f"\nLogin at: https://www.lily-ai-socialmedia.com/admin")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = create_super_admin()
    sys.exit(0 if success else 1)