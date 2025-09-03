"""
Celery tasks for X (Twitter) mentions polling
Handles automated polling with rate limiting and organization-level throttling
"""
import asyncio
import logging
import json
import redis
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from celery import Celery
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.db.database import get_db
from backend.db.models import SocialConnection, SocialAudit
from backend.services.x_mentions_service import get_x_mentions_service

logger = logging.getLogger(__name__)

# Initialize Celery app (this should match your main Celery configuration)
settings = get_settings()
celery_app = Celery('x_polling_tasks')

# Configure Celery for X polling tasks
celery_app.conf.update(
    # Task routing
    task_routes={
        'backend.tasks.x_polling_tasks.poll_all_x_mentions': {'queue': 'x_polling'},
        'backend.tasks.x_polling_tasks.poll_connection_mentions': {'queue': 'x_polling'},
    },
    
    # Task settings
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    result_expires=3600,       # 1 hour
)

# Redis rate limiting configuration
REDIS_RATE_LIMIT_PREFIX = "rate_limit:x_mentions"
DEFAULT_RATE_LIMIT = {
    "requests_per_window": 75,  # X API allows 75 requests per 15 minutes
    "window_seconds": 900,      # 15 minutes window
    "burst_allowance": 5        # Allow small burst above limit
}


def is_partner_oauth_enabled() -> bool:
    """Check if partner OAuth feature is enabled"""
    settings = get_settings()
    return getattr(settings, 'feature_partner_oauth', False)


def get_redis_client():
    """Get Redis client for rate limiting"""
    try:
        redis_url = getattr(settings, 'redis_url', None)
        if redis_url:
            return redis.from_url(redis_url)
        else:
            # Fallback to local Redis
            return redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    except Exception as e:
        logger.warning(f"Redis not available for rate limiting: {e}")
        return None


@celery_app.task(name='backend.tasks.x_polling_tasks.poll_all_x_mentions')
def poll_all_x_mentions() -> Dict[str, Any]:
    """
    Poll mentions for all active X connections with organization-level rate limiting
    
    This task runs every 15 minutes to poll for new mentions across all X connections.
    Uses Redis-based token bucket for rate limiting per organization.
    
    Returns:
        Dictionary with polling results and statistics
    """
    try:
        if not is_partner_oauth_enabled():
            logger.info("X mentions polling skipped - feature disabled")
            return {"status": "skipped", "reason": "feature_disabled"}
        
        start_time = datetime.now(timezone.utc)
        logger.info("Starting X mentions polling for all connections")
        
        # Get database session
        db_gen = get_db()
        db: Session = next(db_gen)
        
        try:
            # Find all active X connections
            x_connections = db.query(SocialConnection).filter(
                SocialConnection.is_active == True,
                SocialConnection.platform == "x",
                SocialConnection.revoked_at.is_(None)
            ).all()
            
            poll_results = {
                "poll_time": start_time.isoformat(),
                "total_connections": len(x_connections),
                "connections_polled": 0,
                "connections_skipped": 0,
                "total_new_mentions": 0,
                "rate_limited_orgs": [],
                "errors": []
            }
            
            # Get Redis client for rate limiting
            redis_client = get_redis_client()
            
            # Group connections by organization for rate limiting
            org_connections = {}
            for conn in x_connections:
                org_id = str(conn.organization_id)
                if org_id not in org_connections:
                    org_connections[org_id] = []
                org_connections[org_id].append(conn)
            
            # Poll each organization's connections with rate limiting
            mentions_service = get_x_mentions_service()
            
            for org_id, connections in org_connections.items():
                try:
                    # Check organization rate limit
                    if redis_client and not _check_org_rate_limit(redis_client, org_id):
                        logger.warning(f"Organization {org_id} rate limited for X mentions polling")
                        poll_results["rate_limited_orgs"].append(org_id)
                        poll_results["connections_skipped"] += len(connections)
                        continue
                    
                    # Poll mentions for each connection in this org
                    for connection in connections:
                        try:
                            logger.info(f"Polling mentions for X connection {connection.id}")
                            
                            result = asyncio.run(mentions_service.poll_mentions(connection, db))
                            
                            if result.get("success"):
                                poll_results["connections_polled"] += 1
                                poll_results["total_new_mentions"] += result.get("new_mentions", 0)
                                
                                # Create audit log for successful poll
                                asyncio.run(_create_poll_audit(
                                    db, connection, "poll_mentions", "success",
                                    {
                                        "new_mentions": result.get("new_mentions", 0),
                                        "since_id": result.get("since_id"),
                                        "total_fetched": result.get("total_fetched", 0)
                                    }
                                ))
                                
                            elif result.get("error") == "rate_limited":
                                # Handle rate limiting
                                poll_results["connections_skipped"] += 1
                                logger.warning(f"Connection {connection.id} rate limited: {result}")
                                
                                # Create audit log for rate limit
                                asyncio.run(_create_poll_audit(
                                    db, connection, "poll_mentions", "rate_limited",
                                    {
                                        "backoff_seconds": result.get("backoff_seconds"),
                                        "retry_after": result.get("retry_after", {}).isoformat() if result.get("retry_after") else None
                                    }
                                ))
                                
                            else:
                                # Handle other errors
                                poll_results["connections_skipped"] += 1
                                error_msg = result.get("error", "unknown error")
                                poll_results["errors"].append({
                                    "connection_id": str(connection.id),
                                    "error": error_msg
                                })
                                
                                # Create audit log for error
                                asyncio.run(_create_poll_audit(
                                    db, connection, "poll_mentions", "failure",
                                    {"error": error_msg}
                                ))
                        
                        except Exception as e:
                            poll_results["connections_skipped"] += 1
                            error_msg = f"Exception polling connection {connection.id}: {str(e)}"
                            logger.error(error_msg)
                            poll_results["errors"].append({
                                "connection_id": str(connection.id),
                                "error": str(e)
                            })
                            
                            # Create audit log for exception
                            try:
                                asyncio.run(_create_poll_audit(
                                    db, connection, "poll_mentions", "failure",
                                    {"error": str(e), "exception": True}
                                ))
                            except Exception as audit_err:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.warning("Audit write failed in X mentions polling",
                                             extra={"err": str(audit_err)}, exc_info=audit_err)
                    
                    # Update rate limit counter for this organization
                    if redis_client:
                        _update_org_rate_limit(redis_client, org_id, len(connections))
                
                except Exception as e:
                    error_msg = f"Error polling organization {org_id}: {str(e)}"
                    logger.error(error_msg)
                    poll_results["errors"].append({
                        "organization_id": org_id,
                        "error": str(e)
                    })
            
            # Calculate polling duration
            end_time = datetime.now(timezone.utc)
            poll_duration = (end_time - start_time).total_seconds()
            poll_results["poll_duration_seconds"] = poll_duration
            
            # Reset session cache to avoid memory leaks
            mentions_service.reset_session_cache()
            
            logger.info(f"X mentions polling completed: {poll_results}")
            return poll_results
            
        finally:
            db.close()
    
    except Exception as e:
        error_msg = f"X mentions polling failed: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "failed",
            "error": error_msg,
            "poll_time": datetime.now(timezone.utc).isoformat()
        }


@celery_app.task(name='backend.tasks.x_polling_tasks.poll_connection_mentions')
def poll_connection_mentions(connection_id: str) -> Dict[str, Any]:
    """
    Poll mentions for a specific X connection (for manual/on-demand polling)
    
    Args:
        connection_id: UUID string of the connection to poll
        
    Returns:
        Dictionary with polling result
    """
    try:
        if not is_partner_oauth_enabled():
            return {"status": "skipped", "reason": "feature_disabled"}
        
        logger.info(f"Manual mentions poll requested for connection {connection_id}")
        
        # Get database session
        db_gen = get_db()
        db: Session = next(db_gen)
        
        try:
            # Find the connection
            connection = db.query(SocialConnection).filter(
                SocialConnection.id == connection_id,
                SocialConnection.is_active == True,
                SocialConnection.platform == "x"
            ).first()
            
            if not connection:
                return {
                    "status": "failed",
                    "error": "X connection not found or inactive",
                    "connection_id": connection_id
                }
            
            # Poll mentions
            mentions_service = get_x_mentions_service()
            result = asyncio.run(mentions_service.poll_mentions(connection, db))
            
            # Create audit log
            if result.get("success"):
                asyncio.run(_create_poll_audit(
                    db, connection, "poll_mentions", "success",
                    {
                        "new_mentions": result.get("new_mentions", 0),
                        "since_id": result.get("since_id"),
                        "total_fetched": result.get("total_fetched", 0),
                        "manual_poll": True
                    }
                ))
            else:
                asyncio.run(_create_poll_audit(
                    db, connection, "poll_mentions", "failure",
                    {
                        "error": result.get("error"),
                        "manual_poll": True
                    }
                ))
            
            poll_result = {
                **result,
                "connection_id": connection_id,
                "poll_time": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Manual mentions poll completed for connection {connection_id}: {poll_result}")
            return poll_result
            
        finally:
            db.close()
    
    except Exception as e:
        error_msg = f"Manual mentions poll failed for connection {connection_id}: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "failed",
            "error": error_msg,
            "connection_id": connection_id,
            "poll_time": datetime.now(timezone.utc).isoformat()
        }


def _check_org_rate_limit(redis_client: redis.Redis, org_id: str) -> bool:
    """
    Check if organization has available rate limit quota
    
    Args:
        redis_client: Redis client
        org_id: Organization ID
        
    Returns:
        True if within rate limit, False if rate limited
    """
    try:
        key = f"{REDIS_RATE_LIMIT_PREFIX}:{org_id}"
        current_time = int(datetime.now(timezone.utc).timestamp())
        window_start = current_time - DEFAULT_RATE_LIMIT["window_seconds"]
        
        # Remove old entries outside the window
        redis_client.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        current_requests = redis_client.zcard(key)
        max_requests = DEFAULT_RATE_LIMIT["requests_per_window"] + DEFAULT_RATE_LIMIT["burst_allowance"]
        
        # Check if under limit
        if current_requests < max_requests:
            return True
        
        logger.warning(f"Organization {org_id} rate limited: {current_requests}/{max_requests}")
        return False
        
    except Exception as e:
        logger.warning(f"Error checking rate limit: {e}")
        return True  # Allow on Redis errors


def _update_org_rate_limit(redis_client: redis.Redis, org_id: str, request_count: int) -> None:
    """
    Update organization rate limit counter
    
    Args:
        redis_client: Redis client
        org_id: Organization ID
        request_count: Number of requests made
    """
    try:
        key = f"{REDIS_RATE_LIMIT_PREFIX}:{org_id}"
        current_time = int(datetime.now(timezone.utc).timestamp())
        
        # Add current requests to the sorted set
        for i in range(request_count):
            # Use slight time offsets to avoid duplicate scores
            score = current_time + (i * 0.001)
            redis_client.zadd(key, {f"req_{score}": score})
        
        # Set expiry to clean up automatically
        redis_client.expire(key, DEFAULT_RATE_LIMIT["window_seconds"] + 3600)
        
    except Exception as e:
        logger.warning(f"Error updating rate limit: {e}")


async def _create_poll_audit(
    db: Session,
    connection: SocialConnection,
    action: str,
    status: str,
    metadata: Dict[str, Any]
) -> None:
    """
    Create audit log for mentions polling operation
    
    Args:
        db: Database session
        connection: SocialConnection instance
        action: Action type (e.g., 'poll_mentions')
        status: Status ('success', 'failure', 'rate_limited')
        metadata: Additional metadata
    """
    try:
        audit = SocialAudit(
            organization_id=connection.organization_id,
            connection_id=connection.id,
            action=action,
            platform=connection.platform,
            user_id=None,  # System operation
            status=status,
            audit_metadata={
                **metadata,
                "platform_account_id": connection.platform_account_id,
                "platform_username": connection.platform_username
            }
        )
        db.add(audit)
        db.commit()
        
    except Exception as e:
        logger.error(f"Failed to create poll audit log: {e}")
        # Don't raise - audit logging shouldn't break the main operation