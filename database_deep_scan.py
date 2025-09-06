#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Database Deep Scan and Validation
Performs thorough analysis of database schema, API compatibility, and data integrity
"""
import os
import sys
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Any, Set, Optional
from sqlalchemy import create_engine, inspect, text, MetaData, Table
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
import json

# Add backend to path
sys.path.insert(0, '/Users/jeffreyhacker/Lily-Media.AI/socialmedia2')
sys.path.insert(0, '/Users/jeffreyhacker/Lily-Media.AI/socialmedia2/backend')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/Users/jeffreyhacker/Lily-Media.AI/socialmedia2/database_scan_report.log')
    ]
)
logger = logging.getLogger(__name__)

# Production database URL
DATABASE_URL = "postgresql://socialmedia:BbsIYQtjBnhKwRL3F9kXbv1wrtsVxuTg@dpg-d2ln7eer433s739509lg-a.oregon-postgres.render.com/socialmedia_uq72?sslmode=require"

class DatabaseDeepScanner:
    """Comprehensive database scanner and validator"""
    
    def __init__(self):
        self.engine = None
        self.inspector = None
        self.session = None
        self.issues = []
        self.warnings = []
        self.info = []
        
    def connect(self):
        """Establish database connection"""
        try:
            logger.info("Connecting to production database...")
            self.engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_timeout=30)
            
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"Connected to PostgreSQL: {version}")
            
            self.inspector = inspect(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            self.issues.append(f"Database connection failed: {e}")
            return False
    
    def scan_database_structure(self):
        """Scan and analyze database structure"""
        logger.info("\n🔍 SCANNING DATABASE STRUCTURE")
        logger.info("=" * 50)
        
        try:
            # Get all tables
            tables = self.inspector.get_table_names()
            logger.info(f"📊 Found {len(tables)} tables in database")
            
            structure_info = {
                "total_tables": len(tables),
                "tables": {},
                "missing_tables": [],
                "column_issues": [],
                "constraint_issues": []
            }
            
            for table_name in sorted(tables):
                logger.info(f"\n📋 Analyzing table: {table_name}")
                
                # Get columns
                columns = self.inspector.get_columns(table_name)
                column_info = {}
                
                for col in columns:
                    col_name = col['name']
                    col_type = str(col['type'])
                    nullable = col.get('nullable', True)
                    default = col.get('default')
                    
                    column_info[col_name] = {
                        'type': col_type,
                        'nullable': nullable,
                        'default': str(default) if default else None
                    }
                
                # Get primary keys
                pk = self.inspector.get_pk_constraint(table_name)
                primary_keys = pk.get('constrained_columns', []) if pk else []
                
                # Get foreign keys
                fks = self.inspector.get_foreign_keys(table_name)
                foreign_keys = []
                for fk in fks:
                    foreign_keys.append({
                        'constrained_columns': fk.get('constrained_columns', []),
                        'referred_table': fk.get('referred_table', ''),
                        'referred_columns': fk.get('referred_columns', [])
                    })
                
                # Get indexes
                indexes = self.inspector.get_indexes(table_name)
                index_info = []
                for idx in indexes:
                    index_info.append({
                        'name': idx.get('name', ''),
                        'columns': idx.get('column_names', []),
                        'unique': idx.get('unique', False)
                    })
                
                # Get unique constraints
                unique_constraints = self.inspector.get_unique_constraints(table_name)
                
                structure_info["tables"][table_name] = {
                    'columns': column_info,
                    'primary_keys': primary_keys,
                    'foreign_keys': foreign_keys,
                    'indexes': index_info,
                    'unique_constraints': unique_constraints,
                    'column_count': len(columns)
                }
                
                logger.info(f"   📊 Columns: {len(columns)}")
                logger.info(f"   🔑 Primary keys: {primary_keys}")
                logger.info(f"   🔗 Foreign keys: {len(foreign_keys)}")
                logger.info(f"   📇 Indexes: {len(indexes)}")
            
            return structure_info
            
        except Exception as e:
            logger.error(f"❌ Database structure scan failed: {e}")
            self.issues.append(f"Database structure scan failed: {e}")
            return None
    
    def validate_model_compatibility(self):
        """Validate database schema against SQLAlchemy models"""
        logger.info("\n🔍 VALIDATING MODEL COMPATIBILITY")
        logger.info("=" * 50)
        
        try:
            # Import models
            from backend.db.models import (
                User, Organization, Content, Goal, Memory, 
                UserSettings, NotificationSettings, SocialPlatformConnection,
                OAuthToken, UsageRecord
            )
            
            # Get model definitions
            models_to_check = [
                User, Organization, Content, Goal, Memory,
                UserSettings, NotificationSettings, SocialPlatformConnection,
                OAuthToken, UsageRecord
            ]
            
            model_validation = {
                "models_checked": len(models_to_check),
                "table_matches": [],
                "missing_tables": [],
                "column_mismatches": [],
                "type_mismatches": []
            }
            
            database_tables = set(self.inspector.get_table_names())
            
            for model in models_to_check:
                table_name = model.__tablename__
                logger.info(f"\n📋 Validating model: {model.__name__} -> {table_name}")
                
                if table_name not in database_tables:
                    logger.error(f"❌ Missing table: {table_name}")
                    model_validation["missing_tables"].append(table_name)
                    self.issues.append(f"Missing table for model {model.__name__}: {table_name}")
                    continue
                
                model_validation["table_matches"].append(table_name)
                logger.info(f"✅ Table exists: {table_name}")
                
                # Check columns
                db_columns = {col['name']: col for col in self.inspector.get_columns(table_name)}
                model_columns = {}
                
                # Get model column definitions
                for column_name, column in model.__table__.columns.items():
                    model_columns[column_name] = {
                        'type': str(column.type),
                        'nullable': column.nullable,
                        'primary_key': column.primary_key,
                        'default': str(column.default) if column.default else None
                    }
                
                # Compare columns
                for col_name, col_info in model_columns.items():
                    if col_name not in db_columns:
                        logger.error(f"❌ Missing column: {table_name}.{col_name}")
                        model_validation["column_mismatches"].append(f"{table_name}.{col_name}")
                        self.issues.append(f"Missing column: {table_name}.{col_name}")
                    else:
                        # Check type compatibility (basic check)
                        db_type = str(db_columns[col_name]['type'])
                        model_type = col_info['type']
                        
                        # Basic type mapping checks
                        type_compatible = self._check_type_compatibility(model_type, db_type)
                        if not type_compatible:
                            logger.warning(f"⚠️  Type mismatch: {table_name}.{col_name} - Model: {model_type}, DB: {db_type}")
                            model_validation["type_mismatches"].append({
                                "table": table_name,
                                "column": col_name,
                                "model_type": model_type,
                                "db_type": db_type
                            })
                            self.warnings.append(f"Type mismatch: {table_name}.{col_name}")
                
                # Check for extra columns in database
                extra_columns = set(db_columns.keys()) - set(model_columns.keys())
                if extra_columns:
                    logger.info(f"ℹ️  Extra columns in DB (not in model): {extra_columns}")
                    for extra_col in extra_columns:
                        self.info.append(f"Extra column in database: {table_name}.{extra_col}")
                
                logger.info(f"   ✅ Model validation complete for {table_name}")
            
            return model_validation
            
        except ImportError as e:
            logger.error(f"❌ Could not import models: {e}")
            self.issues.append(f"Could not import models: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Model validation failed: {e}")
            self.issues.append(f"Model validation failed: {e}")
            return None
    
    def _check_type_compatibility(self, model_type: str, db_type: str) -> bool:
        """Check if model type is compatible with database type"""
        
        # Normalize types for comparison
        model_type = model_type.lower()
        db_type = db_type.lower()
        
        # Common compatible mappings
        compatible_mappings = {
            'integer': ['integer', 'int4', 'int'],
            'varchar': ['varchar', 'character varying', 'text'],
            'text': ['text', 'varchar', 'character varying'],
            'boolean': ['boolean', 'bool'],
            'datetime': ['timestamp', 'datetime', 'timestamp without time zone'],
            'date': ['date'],
            'time': ['time'],
            'float': ['real', 'float4', 'float8', 'double precision'],
            'decimal': ['numeric', 'decimal'],
            'json': ['json', 'jsonb'],
            'uuid': ['uuid']
        }
        
        # Check direct matches
        if model_type in db_type or db_type in model_type:
            return True
        
        # Check compatible mappings
        for model_base, db_compatible in compatible_mappings.items():
            if model_base in model_type:
                for db_compat in db_compatible:
                    if db_compat in db_type:
                        return True
        
        return False
    
    def check_api_endpoint_compatibility(self):
        """Check if database supports all API endpoints"""
        logger.info("\n🔍 CHECKING API ENDPOINT COMPATIBILITY")
        logger.info("=" * 50)
        
        try:
            # Import API modules to check endpoints
            api_check_results = {
                "total_endpoints_checked": 0,
                "supported_endpoints": [],
                "unsupported_endpoints": [],
                "table_dependencies": {}
            }
            
            # Common API endpoint table dependencies
            endpoint_table_mapping = {
                "/api/auth": ["users"],
                "/api/content": ["content", "users"],
                "/api/goals": ["goals", "users"],
                "/api/memory": ["memory", "users"],
                "/api/organizations": ["organizations", "users"],
                "/api/user-settings": ["user_settings", "users"],
                "/api/notifications": ["notification_settings", "users"],
                "/api/social-platforms": ["social_platform_connections", "users"],
                "/api/partner-oauth": ["oauth_tokens", "users"],
                "/api/billing": ["users", "organizations"],
                "/api/monitoring": ["users", "system_logs"],
                "/api/sre": ["users", "organizations"]
            }
            
            database_tables = set(self.inspector.get_table_names())
            
            for endpoint, required_tables in endpoint_table_mapping.items():
                api_check_results["total_endpoints_checked"] += 1
                
                missing_tables = []
                for table in required_tables:
                    if table not in database_tables:
                        missing_tables.append(table)
                
                if missing_tables:
                    logger.error(f"❌ Endpoint {endpoint} missing tables: {missing_tables}")
                    api_check_results["unsupported_endpoints"].append({
                        "endpoint": endpoint,
                        "missing_tables": missing_tables
                    })
                    self.issues.append(f"Endpoint {endpoint} missing required tables: {missing_tables}")
                else:
                    logger.info(f"✅ Endpoint {endpoint} supported")
                    api_check_results["supported_endpoints"].append(endpoint)
                
                api_check_results["table_dependencies"][endpoint] = {
                    "required_tables": required_tables,
                    "missing_tables": missing_tables,
                    "supported": len(missing_tables) == 0
                }
            
            return api_check_results
            
        except Exception as e:
            logger.error(f"❌ API compatibility check failed: {e}")
            self.issues.append(f"API compatibility check failed: {e}")
            return None
    
    def check_data_integrity(self):
        """Check data integrity and constraints"""
        logger.info("\n🔍 CHECKING DATA INTEGRITY")
        logger.info("=" * 50)
        
        try:
            integrity_results = {
                "constraint_violations": [],
                "orphaned_records": [],
                "duplicate_checks": [],
                "data_quality_issues": []
            }
            
            # Check foreign key constraints
            tables = self.inspector.get_table_names()
            
            for table_name in tables:
                logger.info(f"🔍 Checking integrity for table: {table_name}")
                
                try:
                    # Get row count
                    result = self.session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    row_count = result.fetchone()[0]
                    logger.info(f"   📊 Row count: {row_count}")
                    
                    if row_count > 0:
                        # Check for NULL values in NOT NULL columns
                        columns = self.inspector.get_columns(table_name)
                        for col in columns:
                            if not col.get('nullable', True):
                                null_check = self.session.execute(
                                    text(f"SELECT COUNT(*) FROM {table_name} WHERE {col['name']} IS NULL")
                                )
                                null_count = null_check.fetchone()[0]
                                
                                if null_count > 0:
                                    logger.error(f"❌ NULL values in NOT NULL column: {table_name}.{col['name']} ({null_count} records)")
                                    integrity_results["constraint_violations"].append({
                                        "table": table_name,
                                        "column": col['name'],
                                        "issue": f"NULL values in NOT NULL column ({null_count} records)"
                                    })
                                    self.issues.append(f"Constraint violation: NULL values in {table_name}.{col['name']}")
                        
                        # Check foreign key integrity
                        foreign_keys = self.inspector.get_foreign_keys(table_name)
                        for fk in foreign_keys:
                            if fk.get('constrained_columns') and fk.get('referred_table'):
                                constrained_col = fk['constrained_columns'][0]
                                referred_table = fk['referred_table']
                                referred_col = fk['referred_columns'][0] if fk.get('referred_columns') else 'id'
                                
                                # Check for orphaned records
                                orphan_check = self.session.execute(text(f"""
                                    SELECT COUNT(*) FROM {table_name} t1 
                                    LEFT JOIN {referred_table} t2 ON t1.{constrained_col} = t2.{referred_col}
                                    WHERE t1.{constrained_col} IS NOT NULL AND t2.{referred_col} IS NULL
                                """))
                                orphan_count = orphan_check.fetchone()[0]
                                
                                if orphan_count > 0:
                                    logger.error(f"❌ Orphaned records: {table_name}.{constrained_col} -> {referred_table}.{referred_col} ({orphan_count} records)")
                                    integrity_results["orphaned_records"].append({
                                        "table": table_name,
                                        "column": constrained_col,
                                        "referred_table": referred_table,
                                        "referred_column": referred_col,
                                        "orphaned_count": orphan_count
                                    })
                                    self.issues.append(f"Orphaned records: {table_name}.{constrained_col} -> {referred_table}.{referred_col}")
                    
                except Exception as table_error:
                    logger.error(f"❌ Error checking table {table_name}: {table_error}")
                    self.issues.append(f"Error checking table {table_name}: {table_error}")
            
            return integrity_results
            
        except Exception as e:
            logger.error(f"❌ Data integrity check failed: {e}")
            self.issues.append(f"Data integrity check failed: {e}")
            return None
    
    def check_extensions_and_features(self):
        """Check PostgreSQL extensions and features"""
        logger.info("\n🔍 CHECKING POSTGRESQL EXTENSIONS AND FEATURES")
        logger.info("=" * 50)
        
        try:
            extensions_info = {
                "installed_extensions": [],
                "missing_extensions": [],
                "version_info": {},
                "feature_support": {}
            }
            
            # Check PostgreSQL version
            result = self.session.execute(text("SELECT version()"))
            version_info = result.fetchone()[0]
            extensions_info["version_info"]["postgresql"] = version_info
            logger.info(f"📊 PostgreSQL Version: {version_info}")
            
            # Check installed extensions
            result = self.session.execute(text("SELECT extname, extversion FROM pg_extension"))
            extensions = result.fetchall()
            
            for ext_name, ext_version in extensions:
                extensions_info["installed_extensions"].append({
                    "name": ext_name,
                    "version": ext_version
                })
                logger.info(f"✅ Extension: {ext_name} v{ext_version}")
            
            # Check for required extensions
            required_extensions = ['pgvector', 'uuid-ossp', 'btree_gin']
            installed_ext_names = [ext["name"] for ext in extensions_info["installed_extensions"]]
            
            for req_ext in required_extensions:
                if req_ext not in installed_ext_names:
                    logger.warning(f"⚠️  Missing recommended extension: {req_ext}")
                    extensions_info["missing_extensions"].append(req_ext)
                    self.warnings.append(f"Missing recommended extension: {req_ext}")
                else:
                    logger.info(f"✅ Required extension available: {req_ext}")
            
            # Check vector support (if pgvector is installed)
            if 'pgvector' in installed_ext_names:
                try:
                    # Test vector operations
                    result = self.session.execute(text("SELECT '[1,2,3]'::vector"))
                    vector_test = result.fetchone()[0]
                    extensions_info["feature_support"]["vector_operations"] = True
                    logger.info("✅ Vector operations supported")
                except Exception as e:
                    extensions_info["feature_support"]["vector_operations"] = False
                    logger.warning(f"⚠️  Vector operations not working: {e}")
                    self.warnings.append(f"Vector operations not working: {e}")
            else:
                extensions_info["feature_support"]["vector_operations"] = False
            
            # Check UUID support
            try:
                result = self.session.execute(text("SELECT gen_random_uuid()"))
                uuid_test = result.fetchone()[0]
                extensions_info["feature_support"]["uuid_generation"] = True
                logger.info("✅ UUID generation supported")
            except Exception as e:
                extensions_info["feature_support"]["uuid_generation"] = False
                logger.warning(f"⚠️  UUID generation not working: {e}")
                self.warnings.append(f"UUID generation not working: {e}")
            
            # Check JSON/JSONB support
            try:
                result = self.session.execute(text("SELECT '{\"test\": true}'::jsonb"))
                json_test = result.fetchone()[0]
                extensions_info["feature_support"]["jsonb_operations"] = True
                logger.info("✅ JSONB operations supported")
            except Exception as e:
                extensions_info["feature_support"]["jsonb_operations"] = False
                logger.warning(f"⚠️  JSONB operations not working: {e}")
                self.warnings.append(f"JSONB operations not working: {e}")
            
            return extensions_info
            
        except Exception as e:
            logger.error(f"❌ Extensions check failed: {e}")
            self.issues.append(f"Extensions check failed: {e}")
            return None
    
    def check_performance_metrics(self):
        """Check database performance metrics"""
        logger.info("\n🔍 CHECKING PERFORMANCE METRICS")
        logger.info("=" * 50)
        
        try:
            performance_info = {
                "connection_stats": {},
                "table_sizes": {},
                "index_usage": {},
                "slow_queries": [],
                "recommendations": []
            }
            
            # Check connection stats
            try:
                result = self.session.execute(text("""
                    SELECT count(*) as total_connections,
                           count(*) FILTER (WHERE state = 'active') as active_connections,
                           count(*) FILTER (WHERE state = 'idle') as idle_connections
                    FROM pg_stat_activity
                """))
                conn_stats = result.fetchone()
                performance_info["connection_stats"] = {
                    "total_connections": conn_stats[0],
                    "active_connections": conn_stats[1], 
                    "idle_connections": conn_stats[2]
                }
                logger.info(f"📊 Connections - Total: {conn_stats[0]}, Active: {conn_stats[1]}, Idle: {conn_stats[2]}")
            except Exception as e:
                logger.warning(f"⚠️  Could not get connection stats: {e}")
            
            # Check table sizes
            try:
                result = self.session.execute(text("""
                    SELECT schemaname, tablename, 
                           pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                           pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """))
                table_sizes = result.fetchall()
                
                for schema, table, size_pretty, size_bytes in table_sizes:
                    performance_info["table_sizes"][table] = {
                        "size_pretty": size_pretty,
                        "size_bytes": size_bytes
                    }
                    logger.info(f"📊 Table size: {table} = {size_pretty}")
                    
                    # Warn about very large tables
                    if size_bytes > 100 * 1024 * 1024:  # > 100MB
                        performance_info["recommendations"].append(f"Large table detected: {table} ({size_pretty})")
                        self.warnings.append(f"Large table: {table} ({size_pretty})")
            except Exception as e:
                logger.warning(f"⚠️  Could not get table sizes: {e}")
            
            # Check index usage
            try:
                result = self.session.execute(text("""
                    SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
                    FROM pg_stat_user_indexes
                    ORDER BY idx_scan DESC
                """))
                index_stats = result.fetchall()
                
                for schema, table, index, scans, tup_read, tup_fetch in index_stats:
                    performance_info["index_usage"][f"{table}.{index}"] = {
                        "scans": scans,
                        "tuples_read": tup_read,
                        "tuples_fetched": tup_fetch
                    }
                    
                    if scans == 0:
                        performance_info["recommendations"].append(f"Unused index: {table}.{index}")
                        self.warnings.append(f"Unused index: {table}.{index}")
                
                logger.info(f"📊 Analyzed {len(index_stats)} indexes")
            except Exception as e:
                logger.warning(f"⚠️  Could not get index usage stats: {e}")
            
            return performance_info
            
        except Exception as e:
            logger.error(f"❌ Performance check failed: {e}")
            self.issues.append(f"Performance check failed: {e}")
            return None
    
    def generate_report(self, scan_results: Dict[str, Any]):
        """Generate comprehensive scan report"""
        logger.info("\n📋 GENERATING COMPREHENSIVE REPORT")
        logger.info("=" * 50)
        
        report = {
            "scan_timestamp": datetime.utcnow().isoformat(),
            "database_url": DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('://')[1], '***:***'),
            "summary": {
                "total_issues": len(self.issues),
                "total_warnings": len(self.warnings),
                "total_info": len(self.info)
            },
            "issues": self.issues,
            "warnings": self.warnings,
            "info": self.info,
            "detailed_results": scan_results
        }
        
        # Save detailed report
        report_file = '/Users/jeffreyhacker/Lily-Media.AI/socialmedia2/database_deep_scan_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Generate summary
        logger.info("\n" + "="*80)
        logger.info("📊 DATABASE DEEP SCAN SUMMARY")
        logger.info("="*80)
        
        if scan_results.get("structure"):
            logger.info(f"🗃️  Total Tables: {scan_results['structure']['total_tables']}")
        
        if scan_results.get("model_validation"):
            logger.info(f"🏗️  Models Validated: {scan_results['model_validation']['models_checked']}")
            logger.info(f"✅ Table Matches: {len(scan_results['model_validation']['table_matches'])}")
            logger.info(f"❌ Missing Tables: {len(scan_results['model_validation']['missing_tables'])}")
        
        if scan_results.get("api_compatibility"):
            logger.info(f"🔌 API Endpoints Checked: {scan_results['api_compatibility']['total_endpoints_checked']}")
            logger.info(f"✅ Supported Endpoints: {len(scan_results['api_compatibility']['supported_endpoints'])}")
            logger.info(f"❌ Unsupported Endpoints: {len(scan_results['api_compatibility']['unsupported_endpoints'])}")
        
        logger.info(f"\n📊 SCAN RESULTS:")
        logger.info(f"🚨 Critical Issues: {len(self.issues)}")
        logger.info(f"⚠️  Warnings: {len(self.warnings)}")
        logger.info(f"ℹ️  Information: {len(self.info)}")
        
        if self.issues:
            logger.info(f"\n🚨 CRITICAL ISSUES TO RESOLVE:")
            for i, issue in enumerate(self.issues, 1):
                logger.error(f"   {i}. {issue}")
        
        if self.warnings:
            logger.info(f"\n⚠️  WARNINGS TO REVIEW:")
            for i, warning in enumerate(self.warnings, 1):
                logger.warning(f"   {i}. {warning}")
        
        logger.info(f"\n📄 Detailed report saved to: {report_file}")
        
        # Overall health assessment
        if len(self.issues) == 0:
            if len(self.warnings) == 0:
                logger.info("🎉 DATABASE STATUS: EXCELLENT - No issues found!")
            elif len(self.warnings) <= 3:
                logger.info("✅ DATABASE STATUS: GOOD - Minor warnings only")
            else:
                logger.info("⚠️  DATABASE STATUS: FAIR - Multiple warnings to review")
        elif len(self.issues) <= 2:
            logger.info("🔧 DATABASE STATUS: NEEDS ATTENTION - Minor issues to fix")
        else:
            logger.info("🚨 DATABASE STATUS: CRITICAL - Multiple issues require immediate attention")
        
        return report
    
    def close(self):
        """Close database connections"""
        if self.session:
            self.session.close()
        if self.engine:
            self.engine.dispose()

def main():
    """Main scanning function"""
    logger.info("🚀 Starting Comprehensive Database Deep Scan")
    logger.info(f"📅 Scan Date: {datetime.utcnow()}")
    logger.info("="*80)
    
    scanner = DatabaseDeepScanner()
    
    try:
        # Connect to database
        if not scanner.connect():
            logger.error("❌ Cannot proceed - database connection failed")
            return 1
        
        scan_results = {}
        
        # Perform all scans
        logger.info("🔍 Performing comprehensive database analysis...")
        
        # 1. Database structure scan
        scan_results["structure"] = scanner.scan_database_structure()
        
        # 2. Model compatibility validation
        scan_results["model_validation"] = scanner.validate_model_compatibility()
        
        # 3. API endpoint compatibility check
        scan_results["api_compatibility"] = scanner.check_api_endpoint_compatibility()
        
        # 4. Data integrity check
        scan_results["integrity"] = scanner.check_data_integrity()
        
        # 5. Extensions and features check
        scan_results["extensions"] = scanner.check_extensions_and_features()
        
        # 6. Performance metrics check
        scan_results["performance"] = scanner.check_performance_metrics()
        
        # Generate comprehensive report
        report = scanner.generate_report(scan_results)
        
        # Return appropriate exit code
        return 1 if scanner.issues else 0
        
    except Exception as e:
        logger.error(f"❌ Scan failed with unexpected error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1
        
    finally:
        scanner.close()

if __name__ == "__main__":
    sys.exit(main())