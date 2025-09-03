"""
Database table existence checks and safe query utilities
"""
import logging
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional

logger = logging.getLogger(__name__)

def check_table_exists(db: Session, table_name: str) -> bool:
    """
    Check if a table exists in the database
    
    Args:
        db: Database session
        table_name: Name of table to check
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        inspector = inspect(db.bind)
        return table_name in inspector.get_table_names()
    except Exception as e:
        logger.error(f"Error checking if table {table_name} exists: {e}")
        return False

def ensure_table_exists(db: Session, table_name: str, endpoint_name: str = "") -> None:
    """
    Ensure a table exists, raise HTTPException if not
    
    Args:
        db: Database session  
        table_name: Name of table to check
        endpoint_name: Name of endpoint for error message
        
    Raises:
        HTTPException: 503 if table doesn't exist
    """
    if not check_table_exists(db, table_name):
        error_msg = f"Database table '{table_name}' does not exist"
        if endpoint_name:
            error_msg = f"{endpoint_name}: {error_msg}"
        
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Service temporarily unavailable", 
                "message": f"Database schema is incomplete. Please contact support.",
                "missing_table": table_name,
                "endpoint": endpoint_name
            }
        )

def ensure_tables_exist(db: Session, table_names: List[str], endpoint_name: str = "") -> None:
    """
    Ensure multiple tables exist, raise HTTPException if any are missing
    
    Args:
        db: Database session
        table_names: List of table names to check  
        endpoint_name: Name of endpoint for error message
        
    Raises:
        HTTPException: 503 if any table doesn't exist
    """
    missing_tables = []
    for table_name in table_names:
        if not check_table_exists(db, table_name):
            missing_tables.append(table_name)
    
    if missing_tables:
        error_msg = f"Database tables do not exist: {', '.join(missing_tables)}"
        if endpoint_name:
            error_msg = f"{endpoint_name}: {error_msg}"
            
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Service temporarily unavailable",
                "message": f"Database schema is incomplete. Please contact support.", 
                "missing_tables": missing_tables,
                "endpoint": endpoint_name
            }
        )

def safe_table_query(db: Session, table_name: str, query_func, fallback_value=None, endpoint_name: str = ""):
    """
    Safely execute a query against a table, handling missing table errors
    
    Args:
        db: Database session
        table_name: Name of table to query
        query_func: Function that executes the query (should take db as parameter)
        fallback_value: Value to return if table doesn't exist
        endpoint_name: Name of endpoint for logging
        
    Returns:
        Query result or fallback_value if table doesn't exist
    """
    try:
        # First check if table exists
        if not check_table_exists(db, table_name):
            logger.warning(f"{endpoint_name}: Table '{table_name}' does not exist, returning fallback value")
            return fallback_value
        
        # Execute the query
        return query_func(db)
        
    except Exception as e:
        # Always rollback the session on any exception to prevent failed state
        try:
            db.rollback()
        except Exception as rollback_error:
            logger.warning(f"Failed to rollback session in safe_table_query: {rollback_error}")
        
        error_str = str(e).lower()
        
        # Check if it's a schema-related error (table/column missing)
        schema_errors = [
            'does not exist', 'no such table', 'undefined table', 'undefined column',
            'no such column', 'column does not exist', 'relation does not exist'
        ]
        
        if any(phrase in error_str for phrase in schema_errors):
            # Schema mismatch - log as WARNING since we have fallback
            logger.warning(f"{endpoint_name}: Schema mismatch for table '{table_name}': {e}")
            logger.info(f"{endpoint_name}: Using fallback value due to schema mismatch")
            return fallback_value
        else:
            # Other database errors - still log as ERROR and re-raise
            logger.error(f"{endpoint_name}: Database error querying table '{table_name}': {e}")
            raise

def get_table_row_count(db: Session, table_name: str) -> Optional[int]:
    """
    Get row count for a table, returns None if table doesn't exist
    
    Args:
        db: Database session
        table_name: Name of table
        
    Returns:
        int: Row count, or None if table doesn't exist
    """
    try:
        if not check_table_exists(db, table_name):
            return None
        
        result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()
        
    except Exception as e:
        logger.error(f"Error getting row count for table {table_name}: {e}")
        return None

def check_critical_tables_exist(db: Session) -> dict:
    """
    Check if all critical application tables exist
    
    Args:
        db: Database session
        
    Returns:
        dict: Status of critical tables
    """
    critical_tables = [
        # Core identity and settings
        'users', 'user_settings', 'organizations',
        # Content and analytics
        'content_logs', 'content_items', 'content_performance_snapshots', 'metrics',
        # Scheduling and drafts
        'content_drafts', 'content_schedules',
        # Social integrations
        'social_connections', 'social_audit',
        # Other core data
        'notifications', 'memories', 'refresh_token_blacklist'
    ]
    
    status = {
        'all_exist': True,
        'existing': [],
        'missing': []
    }
    
    for table in critical_tables:
        if check_table_exists(db, table):
            status['existing'].append(table)
        else:
            status['missing'].append(table)
            status['all_exist'] = False
    
    return status
