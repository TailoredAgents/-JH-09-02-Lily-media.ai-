#!/usr/bin/env python3
"""
Standalone script to create super admin - no backend imports needed
"""
import os
import sys
from datetime import datetime
from enum import Enum

# Check for required packages
try:
    from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
    from sqlalchemy.orm import sessionmaker, declarative_base
    from passlib.context import CryptContext
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Please install: pip install sqlalchemy passlib[bcrypt] psycopg2-binary")
    sys.exit(1)

# Admin role enum
class AdminRole(Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"

# Simple model definition
Base = declarative_base()

class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(AdminRole), nullable=False, default=AdminRole.ADMIN)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False)
    last_login = Column(DateTime, nullable=True)

def create_admin():
    # Get database URL from environment - NEVER hard-code credentials
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ CRITICAL: DATABASE_URL environment variable must be set")
        print("   Example: export DATABASE_URL='postgresql://user:password@host:port/database'")
        sys.exit(1)
    
    # Initialize password context
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Admin user details - GET FROM ENVIRONMENT FOR SECURITY
    username = os.getenv("ADMIN_USERNAME", "superadmin")
    email = os.getenv("ADMIN_EMAIL", "admin@company.com")
    password = os.getenv("ADMIN_PASSWORD")
    
    if not password:
        print("❌ CRITICAL: ADMIN_PASSWORD environment variable must be set")
        print("   Example: export ADMIN_PASSWORD='your_secure_admin_password'")
        sys.exit(1)
    
    # Create engine
    engine = create_engine(db_url.replace("postgresql+asyncpg://", "postgresql://"))
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = SessionLocal()
    
    try:
        # Check if admin exists
        existing = db.query(AdminUser).filter(
            (AdminUser.email == email) | (AdminUser.username == username)
        ).first()
        
        if existing:
            print(f"Admin already exists: {existing.username} ({existing.email})")
            if existing.role != AdminRole.SUPER_ADMIN:
                existing.role = AdminRole.SUPER_ADMIN
                existing.hashed_password = pwd_context.hash(password)
                db.commit()
                print("Updated to SUPER_ADMIN role")
            return True
        
        # Create new admin
        admin = AdminUser(
            username=username,
            email=email,
            hashed_password=pwd_context.hash(password),
            role=AdminRole.SUPER_ADMIN,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(admin)
        db.commit()
        
        print("SUCCESS: Super admin created!")
        print(f"Username: {username}")
        print(f"Email: {email}")
        print("Login at: https://www.lily-ai-socialmedia.com/admin")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()