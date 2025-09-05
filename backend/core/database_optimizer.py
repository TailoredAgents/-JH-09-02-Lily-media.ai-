"""
Database optimization utilities for improved query performance
Includes index management, query optimization, and connection pooling
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import (
    Index, text, inspect, MetaData, Table, Column, 
    create_engine, event, pool
)
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine
from sqlalchemy.dialects import postgresql
from datetime import datetime, timedelta
import asyncio
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """
    Database optimization service for PostgreSQL
    
    Features:
    - Index analysis and recommendations
    - Query performance monitoring
    - Connection pool optimization
    - Table statistics analysis
    - Automated maintenance tasks
    """
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.metadata = MetaData()
    
    def analyze_missing_indexes(self, db: Session) -> List[Dict[str, Any]]:
        """
        Analyze database for missing indexes that could improve performance
        
        Args:
            db: Database session
            
        Returns:
            List of index recommendations
        """
        recommendations = []
        
        try:
            # Get tables that need indexing
            tables_to_analyze = [
                ("users", ["email", "created_at", "subscription_status"]),
                ("content_logs", ["user_id", "created_at", "platform", "status"]),
                ("social_platform_connections", ["user_id", "platform", "is_active", "connected_at"]),
                ("scheduled_posts", ["user_id", "scheduled_for", "status"]),
                ("notifications", ["user_id", "created_at", "is_read"]),
                ("organizations", ["owner_id", "created_at", "plan_type"]),
                ("team_members", ["user_id", "organization_id", "role"]),
            ]
            
            for table_name, columns in tables_to_analyze:
                existing_indexes = self._get_existing_indexes(db, table_name)
                
                for column in columns:
                    if not self._has_index_on_column(existing_indexes, column):
                        recommendations.append({
                            "table": table_name,
                            "column": column,
                            "index_type": "btree",
                            "reason": f"Frequent queries on {column} would benefit from index",
                            "sql": f"CREATE INDEX idx_{table_name}_{column} ON {table_name} ({column});"
                        })
                
                # Check for composite indexes
                if table_name == "content_logs":
                    composite_columns = ["user_id", "created_at"]
                    if not self._has_composite_index(existing_indexes, composite_columns):
                        recommendations.append({
                            "table": table_name,
                            "columns": composite_columns,
                            "index_type": "btree",
                            "reason": "User content queries frequently filter by user_id and sort by created_at",
                            "sql": f"CREATE INDEX idx_{table_name}_user_created ON {table_name} (user_id, created_at DESC);"
                        })
                
                elif table_name == "social_platform_connections":
                    composite_columns = ["user_id", "is_active"]
                    if not self._has_composite_index(existing_indexes, composite_columns):
                        recommendations.append({
                            "table": table_name,
                            "columns": composite_columns,
                            "index_type": "btree",
                            "reason": "Connection queries frequently filter by user_id and is_active",
                            "sql": f"CREATE INDEX idx_{table_name}_user_active ON {table_name} (user_id, is_active);"
                        })
            
            logger.info(f"Generated {len(recommendations)} index recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error analyzing missing indexes: {e}")
            return []
    
    def _get_existing_indexes(self, db: Session, table_name: str) -> List[Dict[str, Any]]:
        """Get existing indexes for a table"""
        try:
            query = text("""
                SELECT 
                    indexname,
                    indexdef,
                    schemaname
                FROM pg_indexes 
                WHERE tablename = :table_name
            """)
            
            result = db.execute(query, {"table_name": table_name})
            return [dict(row) for row in result.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting indexes for {table_name}: {e}")
            return []
    
    def _has_index_on_column(self, indexes: List[Dict[str, Any]], column: str) -> bool:
        """Check if column has an index"""
        for index in indexes:
            indexdef = index.get("indexdef", "").lower()
            if f"({column})" in indexdef or f"({column} " in indexdef:
                return True
        return False
    
    def _has_composite_index(self, indexes: List[Dict[str, Any]], columns: List[str]) -> bool:
        """Check if composite index exists"""
        for index in indexes:
            indexdef = index.get("indexdef", "").lower()
            if all(col.lower() in indexdef for col in columns):
                return True
        return False
    
    def analyze_table_statistics(self, db: Session) -> Dict[str, Any]:
        """
        Analyze table statistics for performance insights
        
        Args:
            db: Database session
            
        Returns:
            Table statistics analysis
        """
        try:
            # Get table sizes and row counts
            query = text("""
                SELECT 
                    schemaname,
                    tablename,
                    attname as column_name,
                    n_distinct,
                    correlation,
                    null_frac
                FROM pg_stats 
                WHERE schemaname = 'public'
                AND tablename IN ('users', 'content_logs', 'social_platform_connections', 
                                'scheduled_posts', 'notifications', 'organizations')
                ORDER BY tablename, attname
            """)
            
            result = db.execute(query)
            stats = [dict(row) for row in result.fetchall()]
            
            # Get table sizes
            size_query = text("""
                SELECT 
                    relname as table_name,
                    pg_size_pretty(pg_total_relation_size(relid)) as size,
                    pg_total_relation_size(relid) as size_bytes,
                    reltuples::bigint as estimated_rows
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(relid) DESC
            """)
            
            size_result = db.execute(size_query)
            table_sizes = [dict(row) for row in size_result.fetchall()]
            
            return {
                "column_statistics": stats,
                "table_sizes": table_sizes,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing table statistics: {e}")
            return {"error": str(e)}
    
    def analyze_slow_queries(self, db: Session, min_duration_ms: int = 1000) -> List[Dict[str, Any]]:
        """
        Analyze slow queries from pg_stat_statements (if available)
        
        Args:
            db: Database session
            min_duration_ms: Minimum duration in milliseconds
            
        Returns:
            List of slow query analysis
        """
        try:
            # Check if pg_stat_statements extension is available
            check_query = text("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                )
            """)
            
            result = db.execute(check_query).scalar()
            
            if not result:
                return [{
                    "message": "pg_stat_statements extension not available",
                    "recommendation": "Enable pg_stat_statements for query performance monitoring"
                }]
            
            # Get slow queries
            slow_query = text("""
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    max_time,
                    rows,
                    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                FROM pg_stat_statements
                WHERE mean_time > :min_duration
                ORDER BY total_time DESC
                LIMIT 20
            """)
            
            result = db.execute(slow_query, {"min_duration": min_duration_ms})
            slow_queries = [dict(row) for row in result.fetchall()]
            
            return slow_queries
            
        except Exception as e:
            logger.error(f"Error analyzing slow queries: {e}")
            return [{"error": str(e)}]
    
    def optimize_connection_pool(self) -> Dict[str, Any]:
        """
        Optimize database connection pool settings
        
        Returns:
            Optimization recommendations
        """
        recommendations = {
            "current_settings": {},
            "recommendations": [],
            "optimized_settings": {}
        }
        
        try:
            # Get current pool settings
            current_pool = self.engine.pool
            
            recommendations["current_settings"] = {
                "pool_size": getattr(current_pool, 'size', None),
                "max_overflow": getattr(current_pool, 'max_overflow', None),
                "timeout": getattr(current_pool, 'timeout', None),
                "recycle": getattr(current_pool, 'recycle', None)
            }
            
            # Provide optimization recommendations
            recommendations["recommendations"] = [
                {
                    "setting": "pool_size",
                    "current": recommendations["current_settings"]["pool_size"],
                    "recommended": 20,
                    "reason": "Optimal pool size for typical web application load"
                },
                {
                    "setting": "max_overflow",
                    "current": recommendations["current_settings"]["max_overflow"],
                    "recommended": 30,
                    "reason": "Allow burst capacity for high traffic periods"
                },
                {
                    "setting": "pool_timeout",
                    "current": recommendations["current_settings"]["timeout"],
                    "recommended": 30,
                    "reason": "Reasonable timeout to prevent indefinite waiting"
                },
                {
                    "setting": "pool_recycle",
                    "current": recommendations["current_settings"]["recycle"],
                    "recommended": 3600,
                    "reason": "Recycle connections hourly to prevent staleness"
                }
            ]
            
            recommendations["optimized_settings"] = {
                "poolclass": "QueuePool",
                "pool_size": 20,
                "max_overflow": 30,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
                "pool_timeout": 30,
                "connect_args": {
                    "connect_timeout": 10,
                    "command_timeout": 60,
                    "sslmode": "require"
                }
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error optimizing connection pool: {e}")
            return {"error": str(e)}
    
    def create_recommended_indexes(self, db: Session, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create recommended indexes (use with caution in production)
        
        Args:
            db: Database session
            recommendations: Index recommendations from analyze_missing_indexes
            
        Returns:
            Results of index creation
        """
        results = {
            "created": [],
            "failed": [],
            "skipped": []
        }
        
        for rec in recommendations:
            try:
                sql = rec.get("sql")
                if not sql:
                    results["skipped"].append({
                        "recommendation": rec,
                        "reason": "No SQL provided"
                    })
                    continue
                
                # Execute index creation
                db.execute(text(sql))
                db.commit()
                
                results["created"].append({
                    "table": rec.get("table"),
                    "column": rec.get("column", rec.get("columns")),
                    "sql": sql
                })
                
                logger.info(f"Created index: {sql}")
                
            except Exception as e:
                db.rollback()
                results["failed"].append({
                    "recommendation": rec,
                    "error": str(e)
                })
                logger.error(f"Failed to create index: {e}")
        
        return results
    
    def vacuum_analyze_tables(self, db: Session, tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run VACUUM ANALYZE on specified tables or all tables
        
        Args:
            db: Database session
            tables: Specific tables to analyze (optional)
            
        Returns:
            Results of vacuum analyze operation
        """
        results = {
            "analyzed": [],
            "failed": [],
            "start_time": datetime.utcnow().isoformat()
        }
        
        try:
            if not tables:
                # Get all user tables
                tables_query = text("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                result = db.execute(tables_query)
                tables = [row[0] for row in result.fetchall()]
            
            for table in tables:
                try:
                    # Use autocommit for VACUUM ANALYZE
                    with self.engine.connect().execution_options(autocommit=True) as conn:
                        conn.execute(text(f"VACUUM ANALYZE {table}"))
                    
                    results["analyzed"].append(table)
                    logger.info(f"Analyzed table: {table}")
                    
                except Exception as e:
                    results["failed"].append({
                        "table": table,
                        "error": str(e)
                    })
                    logger.error(f"Failed to analyze table {table}: {e}")
            
            results["end_time"] = datetime.utcnow().isoformat()
            return results
            
        except Exception as e:
            logger.error(f"Error in vacuum analyze: {e}")
            return {"error": str(e)}
    
    def get_database_health(self, db: Session) -> Dict[str, Any]:
        """
        Get overall database health metrics
        
        Args:
            db: Database session
            
        Returns:
            Database health summary
        """
        try:
            health = {
                "status": "healthy",
                "issues": [],
                "metrics": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Check database size
            size_query = text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as size,
                       pg_database_size(current_database()) as size_bytes
            """)
            size_result = db.execute(size_query).fetchone()
            health["metrics"]["database_size"] = dict(size_result)
            
            # Check connection count
            conn_query = text("""
                SELECT count(*) as active_connections,
                       max_conn.setting::int as max_connections,
                       (count(*) * 100.0 / max_conn.setting::int) as usage_percent
                FROM pg_stat_activity, 
                     (SELECT setting FROM pg_settings WHERE name='max_connections') max_conn
                WHERE state = 'active'
                GROUP BY max_conn.setting
            """)
            conn_result = db.execute(conn_query).fetchone()
            if conn_result:
                health["metrics"]["connections"] = dict(conn_result)
                
                if conn_result["usage_percent"] > 80:
                    health["status"] = "warning"
                    health["issues"].append("High connection usage detected")
            
            # Check for long-running queries
            long_query = text("""
                SELECT count(*) as long_running_queries
                FROM pg_stat_activity 
                WHERE state = 'active' 
                AND now() - query_start > interval '5 minutes'
            """)
            long_result = db.execute(long_query).scalar()
            health["metrics"]["long_running_queries"] = long_result
            
            if long_result > 0:
                health["status"] = "warning"  
                health["issues"].append(f"{long_result} long-running queries detected")
            
            # Check table bloat (simplified)
            bloat_query = text("""
                SELECT schemaname, tablename, 
                       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 5
            """)
            bloat_result = db.execute(bloat_query)
            health["metrics"]["largest_tables"] = [dict(row) for row in bloat_result.fetchall()]
            
            return health
            
        except Exception as e:
            logger.error(f"Error getting database health: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }