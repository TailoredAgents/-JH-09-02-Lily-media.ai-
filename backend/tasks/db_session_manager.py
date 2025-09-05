"""
Database Session Manager for Celery Tasks

Provides proper database session management for Celery workers to prevent
connection leaks and ensure proper cleanup in worker threads.
"""
import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session

from backend.db.database import SessionLocal

logger = logging.getLogger(__name__)

@contextmanager
def get_celery_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions in Celery tasks.
    
    Ensures proper session cleanup and error handling in worker threads.
    
    Usage:
        @celery_app.task
        def my_task():
            with get_celery_db_session() as db:
                # Use db session
                users = db.query(User).all()
                # Session is automatically closed
    
    Returns:
        Database session that is automatically cleaned up
    """
    
    # Create a new session for this task
    db = SessionLocal()
    
    try:
        logger.debug("Created database session for Celery task")
        yield db
        
        # Commit any pending transactions
        db.commit()
        logger.debug("Committed database session for Celery task")
        
    except Exception as e:
        # Roll back on any exception
        logger.error(f"Database error in Celery task, rolling back: {e}")
        db.rollback()
        raise
        
    finally:
        # Always close the session to prevent connection leaks
        db.close()
        logger.debug("Closed database session for Celery task")

class CeleryDBSessionManager:
    """
    Class-based database session manager for Celery tasks.
    
    Useful for tasks that need multiple session scopes or
    more complex session management.
    """
    
    def __init__(self):
        self.sessions = []
    
    def create_session(self) -> Session:
        """
        Create a new database session tracked by this manager.
        
        Returns:
            New database session
        """
        db = SessionLocal()
        self.sessions.append(db)
        logger.debug(f"Created tracked database session. Total sessions: {len(self.sessions)}")
        return db
    
    def commit_all(self):
        """Commit all tracked sessions."""
        for db in self.sessions:
            try:
                db.commit()
                logger.debug("Committed database session")
            except Exception as e:
                logger.error(f"Failed to commit session: {e}")
                db.rollback()
                raise
    
    def rollback_all(self):
        """Roll back all tracked sessions."""
        for db in self.sessions:
            try:
                db.rollback()
                logger.debug("Rolled back database session")
            except Exception as e:
                logger.error(f"Failed to rollback session: {e}")
    
    def close_all(self):
        """Close all tracked sessions and clear the list."""
        for db in self.sessions:
            try:
                db.close()
                logger.debug("Closed database session")
            except Exception as e:
                logger.error(f"Failed to close session: {e}")
        
        self.sessions.clear()
        logger.debug("Cleared all database sessions")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures all sessions are cleaned up."""
        if exc_type:
            logger.error(f"Exception in session manager: {exc_val}")
            self.rollback_all()
        else:
            self.commit_all()
        
        self.close_all()
        
        if exc_type:
            # Re-raise the exception
            return False
        return True

def with_db_session(task_func):
    """
    Decorator for Celery tasks that need database access.
    
    Automatically injects a 'db' parameter with a managed session.
    
    Usage:
        @celery_app.task
        @with_db_session
        def my_task(db: Session):
            users = db.query(User).all()
            # Session is automatically managed
    """
    def wrapper(*args, **kwargs):
        with get_celery_db_session() as db:
            # Inject db as the first parameter
            return task_func(db, *args, **kwargs)
    
    return wrapper