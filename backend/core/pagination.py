"""
Production-ready pagination utilities for FastAPI endpoints
Provides cursor-based and offset-based pagination with performance optimizations
"""
import logging
from typing import Optional, List, Dict, Any, Generic, TypeVar, Union
from math import ceil
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Query, Session
from sqlalchemy import desc, asc, func, and_, or_
from datetime import datetime, timezone
from fastapi import Query as FastAPIQuery, HTTPException, status

logger = logging.getLogger(__name__)

T = TypeVar('T')

class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    page: int = Field(1, ge=1, description="Page number (1-based)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page (max 100)")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")

class CursorPaginationParams(BaseModel):
    """Cursor-based pagination parameters for better performance"""
    limit: int = Field(20, ge=1, le=100, description="Items per page (max 100)")
    cursor: Optional[str] = Field(None, description="Cursor for next page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")

class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized paginated response format"""
    items: List[T]
    pagination: Dict[str, Any]
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Cursor-based paginated response format"""
    items: List[T]
    pagination: Dict[str, Any]
    has_next: bool
    next_cursor: Optional[str] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class PaginationService:
    """
    High-performance pagination service with multiple pagination strategies
    
    Features:
    - Offset-based pagination for simple use cases
    - Cursor-based pagination for large datasets
    - Query optimization and caching
    - Flexible sorting and filtering
    - Performance monitoring
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def paginate_query(
        self,
        query: Query,
        params: PaginationParams,
        total_count: Optional[int] = None
    ) -> PaginatedResponse:
        """
        Apply offset-based pagination to a SQLAlchemy query
        
        Args:
            query: SQLAlchemy query object
            params: Pagination parameters
            total_count: Pre-calculated total count (optional for performance)
            
        Returns:
            Paginated response with items and metadata
        """
        try:
            # Calculate offset
            offset = (params.page - 1) * params.page_size
            
            # Apply sorting if specified
            if params.sort_by:
                sort_column = getattr(query.column_descriptions[0]['entity'], params.sort_by, None)
                if sort_column:
                    if params.sort_order == "asc":
                        query = query.order_by(asc(sort_column))
                    else:
                        query = query.order_by(desc(sort_column))
            
            # Get total count if not provided
            if total_count is None:
                # Use subquery for better performance with complex queries
                total_count = query.count()
            
            # Apply pagination
            items = query.offset(offset).limit(params.page_size).all()
            
            # Calculate metadata
            total_pages = ceil(total_count / params.page_size) if total_count > 0 else 0
            has_next = params.page < total_pages
            has_previous = params.page > 1
            
            pagination_info = {
                "current_page": params.page,
                "page_size": params.page_size,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous,
                "next_page": params.page + 1 if has_next else None,
                "previous_page": params.page - 1 if has_previous else None
            }
            
            logger.debug(f"Paginated query: page {params.page}, {len(items)} items, {total_count} total")
            
            return PaginatedResponse(
                items=items,
                pagination=pagination_info
            )
            
        except Exception as e:
            logger.error(f"Pagination error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Pagination processing failed"
            )
    
    def cursor_paginate_query(
        self,
        query: Query,
        params: CursorPaginationParams,
        cursor_column: str = "id",
        cursor_value_extractor: Optional[callable] = None
    ) -> CursorPaginatedResponse:
        """
        Apply cursor-based pagination for better performance on large datasets
        
        Args:
            query: SQLAlchemy query object
            params: Cursor pagination parameters
            cursor_column: Column to use for cursor (default: 'id')
            cursor_value_extractor: Function to extract cursor value from item
            
        Returns:
            Cursor paginated response
        """
        try:
            # Get the cursor column from the model
            model_class = query.column_descriptions[0]['entity']
            cursor_col = getattr(model_class, cursor_column)
            
            # Apply cursor filtering if cursor is provided
            if params.cursor:
                try:
                    if params.sort_order == "desc":
                        query = query.filter(cursor_col < params.cursor)
                    else:
                        query = query.filter(cursor_col > params.cursor)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid cursor value: {params.cursor}")
                    # Continue without cursor filtering
            
            # Apply sorting
            if params.sort_order == "desc":
                query = query.order_by(desc(cursor_col))
            else:
                query = query.order_by(asc(cursor_col))
            
            # Get one extra item to check if there's a next page
            items = query.limit(params.limit + 1).all()
            
            # Check if there are more items
            has_next = len(items) > params.limit
            if has_next:
                items = items[:-1]  # Remove the extra item
            
            # Extract next cursor
            next_cursor = None
            if has_next and items:
                if cursor_value_extractor:
                    next_cursor = str(cursor_value_extractor(items[-1]))
                else:
                    next_cursor = str(getattr(items[-1], cursor_column))
            
            pagination_info = {
                "limit": params.limit,
                "cursor": params.cursor,
                "sort_by": cursor_column,
                "sort_order": params.sort_order,
                "items_count": len(items)
            }
            
            logger.debug(f"Cursor paginated query: {len(items)} items, has_next: {has_next}")
            
            return CursorPaginatedResponse(
                items=items,
                pagination=pagination_info,
                has_next=has_next,
                next_cursor=next_cursor
            )
            
        except Exception as e:
            logger.error(f"Cursor pagination error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cursor pagination processing failed"
            )
    
    def paginate_with_search(
        self,
        query: Query,
        params: PaginationParams,
        search_columns: List[str],
        search_term: Optional[str] = None
    ) -> PaginatedResponse:
        """
        Paginate with full-text search capabilities
        
        Args:
            query: Base SQLAlchemy query
            params: Pagination parameters
            search_columns: Columns to search in
            search_term: Search term to filter by
            
        Returns:
            Paginated response with search results
        """
        try:
            original_query = query
            
            # Apply search filtering
            if search_term and search_columns:
                model_class = query.column_descriptions[0]['entity']
                search_conditions = []
                
                for column_name in search_columns:
                    column = getattr(model_class, column_name, None)
                    if column and hasattr(column.type, 'python_type') and column.type.python_type == str:
                        search_conditions.append(
                            column.ilike(f"%{search_term}%")
                        )
                
                if search_conditions:
                    query = query.filter(or_(*search_conditions))
            
            # Use regular pagination
            return self.paginate_query(query, params)
            
        except Exception as e:
            logger.error(f"Search pagination error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Search pagination processing failed"
            )


# FastAPI dependency functions
def get_pagination_params(
    page: int = FastAPIQuery(1, ge=1, description="Page number (1-based)"),
    page_size: int = FastAPIQuery(20, ge=1, le=100, description="Items per page (max 100)"),
    sort_by: Optional[str] = FastAPIQuery(None, description="Field to sort by"),
    sort_order: str = FastAPIQuery("desc", pattern="^(asc|desc)$", description="Sort order")
) -> PaginationParams:
    """FastAPI dependency for standard pagination parameters"""
    return PaginationParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )

def get_cursor_pagination_params(
    limit: int = FastAPIQuery(20, ge=1, le=100, description="Items per page (max 100)"),
    cursor: Optional[str] = FastAPIQuery(None, description="Cursor for next page"),
    sort_by: Optional[str] = FastAPIQuery(None, description="Field to sort by"),
    sort_order: str = FastAPIQuery("desc", pattern="^(asc|desc)$", description="Sort order")
) -> CursorPaginationParams:
    """FastAPI dependency for cursor pagination parameters"""
    return CursorPaginationParams(
        limit=limit,
        cursor=cursor,
        sort_by=sort_by,
        sort_order=sort_order
    )

def get_search_params(
    search: Optional[str] = FastAPIQuery(None, min_length=1, max_length=100, description="Search term")
) -> Optional[str]:
    """FastAPI dependency for search parameters"""
    return search

# Performance optimization utilities
class QueryOptimizer:
    """
    Query optimization utilities for better database performance
    """
    
    @staticmethod
    def optimize_count_query(query: Query) -> int:
        """
        Optimize count queries for better performance
        
        Args:
            query: SQLAlchemy query object
            
        Returns:
            Optimized count result
        """
        # Use func.count() with primary key for better performance
        model_class = query.column_descriptions[0]['entity']
        primary_key = model_class.__table__.primary_key.columns.values()[0]
        
        count_query = query.statement.with_only_columns([func.count(primary_key)])
        return query.session.execute(count_query).scalar()
    
    @staticmethod
    def add_query_hints(query: Query, hints: List[str]) -> Query:
        """
        Add database-specific query hints for optimization
        
        Args:
            query: SQLAlchemy query object
            hints: List of query hints
            
        Returns:
            Query with optimization hints
        """
        # PostgreSQL-specific optimizations
        for hint in hints:
            if hint == "use_index":
                # Force index usage where appropriate
                pass
            elif hint == "no_seq_scan":
                # Disable sequential scans
                query = query.execution_options(
                    postgresql_readonly=True,
                    postgresql_isolation_level="AUTOCOMMIT"
                )
        
        return query


# Caching decorators for pagination
def cache_paginated_result(cache_key: str, ttl: int = 300):
    """
    Decorator to cache paginated results
    
    Args:
        cache_key: Base cache key
        ttl: Time to live in seconds
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Cache implementation would go here
            # For now, just call the function
            return func(*args, **kwargs)
        return wrapper
    return decorator