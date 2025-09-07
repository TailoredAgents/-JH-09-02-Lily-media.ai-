"""
Performance monitoring and optimization API endpoints
Provides insights into system performance and optimization recommendations
"""
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User
from backend.auth.dependencies import get_current_user, get_admin_user, AuthUser
from backend.core.performance import (
    performance_metrics,
    analyze_performance_bottlenecks,
    cache_optimizer,
    monitor_performance
)
from backend.core.pagination import (
    PaginationService,
    get_pagination_params,
    PaginationParams,
    PaginatedResponse
)
from backend.core.api_version import create_versioned_router

logger = logging.getLogger(__name__)
router = create_versioned_router(prefix="/performance", tags=["performance"])

# Response models
class PerformanceMetricsResponse(BaseModel):
    """Performance metrics summary response"""
    api_performance: Dict[str, Any]
    db_performance: Dict[str, Any]
    cache_performance: Dict[str, Any]
    timestamp: str
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class PerformanceAnalysisResponse(BaseModel):
    """Performance analysis with recommendations"""
    metrics: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    analysis_timestamp: str
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class SlowQueryResponse(BaseModel):
    """Slow query information"""
    query: str
    duration: float
    timestamp: str
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class CacheStatsResponse(BaseModel):
    """Cache statistics response"""
    size: int
    max_size: int
    hit_rate: float
    stats: Dict[str, int]
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class EndpointPerformanceResponse(BaseModel):
    """Endpoint performance metrics"""
    endpoint: str
    count: int
    avg_duration: float
    total_duration: float
    status_codes: Dict[str, int]
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

@router.get("/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    current_user: User = Depends(get_admin_user)
):
    """
    Get current performance metrics summary
    
    Requires admin access for security
    """
    try:
        with monitor_performance("get_performance_metrics"):
            metrics = performance_metrics.get_summary()
            
            return PerformanceMetricsResponse(
                api_performance=metrics["api_performance"],
                db_performance=metrics["db_performance"], 
                cache_performance=metrics["cache_performance"],
                timestamp=metrics["timestamp"]
            )
            
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )

@router.get("/analysis", response_model=PerformanceAnalysisResponse)
async def get_performance_analysis(
    current_user: User = Depends(get_admin_user)
):
    """
    Get performance analysis with optimization recommendations
    
    Requires admin access for security
    """
    try:
        with monitor_performance("get_performance_analysis"):
            analysis = analyze_performance_bottlenecks()
            
            return PerformanceAnalysisResponse(
                metrics=analysis["metrics"],
                recommendations=analysis["recommendations"],
                analysis_timestamp=analysis["analysis_timestamp"]
            )
            
    except Exception as e:
        logger.error(f"Error analyzing performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze performance"
        )

@router.get("/slow-queries", response_model=PaginatedResponse[SlowQueryResponse])
async def get_slow_queries(
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_admin_user),
    min_duration: float = Query(1.0, ge=0.1, description="Minimum query duration in seconds")
):
    """
    Get paginated list of slow database queries
    
    Args:
        pagination: Pagination parameters
        min_duration: Minimum duration to consider a query slow
        
    Requires admin access for security
    """
    try:
        with monitor_performance("get_slow_queries"):
            # Get slow queries from performance metrics
            all_slow_queries = [
                SlowQueryResponse(
                    query=q["query"],
                    duration=q["duration"],
                    timestamp=q["timestamp"]
                )
                for q in performance_metrics.metrics["slow_queries"]
                if q["duration"] >= min_duration
            ]
            
            # Manual pagination for in-memory data
            start_idx = (pagination.page - 1) * pagination.page_size
            end_idx = start_idx + pagination.page_size
            page_queries = all_slow_queries[start_idx:end_idx]
            
            total_items = len(all_slow_queries)
            total_pages = (total_items + pagination.page_size - 1) // pagination.page_size
            
            pagination_info = {
                "current_page": pagination.page,
                "page_size": pagination.page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": pagination.page < total_pages,
                "has_previous": pagination.page > 1,
                "next_page": pagination.page + 1 if pagination.page < total_pages else None,
                "previous_page": pagination.page - 1 if pagination.page > 1 else None
            }
            
            return PaginatedResponse(
                items=page_queries,
                pagination=pagination_info
            )
            
    except Exception as e:
        logger.error(f"Error getting slow queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve slow queries"
        )

@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    current_user: User = Depends(get_admin_user)
):
    """
    Get cache statistics
    
    Requires admin access for security
    """
    try:
        with monitor_performance("get_cache_stats"):
            stats = cache_optimizer.get_stats()
            
            return CacheStatsResponse(
                size=stats["size"],
                max_size=stats["max_size"],
                hit_rate=stats["hit_rate"],
                stats=stats["stats"]
            )
            
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics"
        )

@router.delete("/cache/clear")
async def clear_cache(
    current_user: User = Depends(get_admin_user)
):
    """
    Clear all cache entries
    
    Requires admin access for security
    """
    try:
        with monitor_performance("clear_cache"):
            cache_optimizer.clear()
            logger.info(f"Cache cleared by admin user {current_user.user_id}")
            
            return {"message": "Cache cleared successfully"}
            
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )

@router.get("/endpoints", response_model=PaginatedResponse[EndpointPerformanceResponse])
async def get_endpoint_performance(
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_admin_user),
    sort_by: str = Query("avg_duration", description="Sort by: count, avg_duration, total_duration"),
    min_calls: int = Query(1, ge=1, description="Minimum number of calls to include endpoint")
):
    """
    Get paginated endpoint performance metrics
    
    Args:
        pagination: Pagination parameters
        sort_by: Field to sort by
        min_calls: Minimum number of calls to include endpoint
        
    Requires admin access for security
    """
    try:
        with monitor_performance("get_endpoint_performance"):
            # Get endpoint metrics from performance metrics
            api_calls = performance_metrics.metrics["api_calls"]
            
            endpoint_list = [
                EndpointPerformanceResponse(
                    endpoint=endpoint,
                    count=metrics["count"],
                    avg_duration=metrics["avg_duration"],
                    total_duration=metrics["total_duration"],
                    status_codes=metrics["status_codes"]
                )
                for endpoint, metrics in api_calls.items()
                if metrics["count"] >= min_calls
            ]
            
            # Sort endpoints
            reverse = True  # Default to descending
            if sort_by == "count":
                endpoint_list.sort(key=lambda x: x.count, reverse=reverse)
            elif sort_by == "avg_duration":
                endpoint_list.sort(key=lambda x: x.avg_duration, reverse=reverse)
            elif sort_by == "total_duration":
                endpoint_list.sort(key=lambda x: x.total_duration, reverse=reverse)
            else:
                endpoint_list.sort(key=lambda x: x.avg_duration, reverse=reverse)
            
            # Manual pagination for in-memory data
            start_idx = (pagination.page - 1) * pagination.page_size
            end_idx = start_idx + pagination.page_size
            page_endpoints = endpoint_list[start_idx:end_idx]
            
            total_items = len(endpoint_list)
            total_pages = (total_items + pagination.page_size - 1) // pagination.page_size
            
            pagination_info = {
                "current_page": pagination.page,
                "page_size": pagination.page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": pagination.page < total_pages,
                "has_previous": pagination.page > 1,
                "next_page": pagination.page + 1 if pagination.page < total_pages else None,
                "previous_page": pagination.page - 1 if pagination.page > 1 else None
            }
            
            return PaginatedResponse(
                items=page_endpoints,
                pagination=pagination_info
            )
            
    except Exception as e:
        logger.error(f"Error getting endpoint performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve endpoint performance"
        )

@router.get("/health")
async def performance_health_check():
    """
    Basic health check for performance monitoring system
    """
    try:
        metrics = performance_metrics.get_summary()
        cache_stats = cache_optimizer.get_stats()
        
        # Determine health status
        health_status = "healthy"
        issues = []
        
        # Check for performance issues
        if metrics["api_performance"]["avg_response_time"] > 2.0:
            health_status = "degraded"
            issues.append("High API response times detected")
        
        if metrics["db_performance"]["avg_query_time"] > 1.0:
            health_status = "degraded"  
            issues.append("Slow database queries detected")
        
        if cache_stats["hit_rate"] < 0.5:
            health_status = "degraded"
            issues.append("Low cache hit rate")
        
        return {
            "status": health_status,
            "issues": issues,
            "metrics_summary": {
                "api_calls": metrics["api_performance"]["total_calls"],
                "db_queries": metrics["db_performance"]["total_queries"],
                "cache_hit_rate": cache_stats["hit_rate"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Performance health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }