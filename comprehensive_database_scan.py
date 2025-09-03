#!/usr/bin/env python3
"""
Comprehensive Database Schema Scanner
Performs deep analysis of database structure and identifies schema issues
"""
import os
import sys
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass
from sqlalchemy import (
    create_engine, inspect, MetaData, Table, Column, 
    text, Integer, String, Boolean, DateTime, Text, JSON
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

try:
    from backend.core.config import get_settings
    from backend.db.database import get_db_url
    from backend.db import models
except ImportError as e:
    print(f"Warning: Could not import backend modules: {e}")
    models = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Information about a database column"""
    name: str
    type_: str
    nullable: bool
    default: Optional[str]
    primary_key: bool
    foreign_keys: List[str]
    unique: bool
    index: bool


@dataclass
class TableInfo:
    """Information about a database table"""
    name: str
    columns: Dict[str, ColumnInfo]
    primary_keys: List[str]
    foreign_keys: Dict[str, str]
    indexes: List[str]
    constraints: List[str]
    row_count: Optional[int] = None


@dataclass
class SchemaIssue:
    """Represents a schema issue found during scanning"""
    severity: str  # 'critical', 'warning', 'info'
    category: str  # 'missing_table', 'missing_column', 'type_mismatch', etc.
    table: str
    column: Optional[str]
    description: str
    suggested_fix: str


class DatabaseSchemaScanner:
    """Comprehensive database schema analysis tool"""
    
    def __init__(self):
        self.engine: Optional[Engine] = None
        self.inspector = None
        self.metadata = None
        self.issues: List[SchemaIssue] = []
        self.tables: Dict[str, TableInfo] = {}
        self.model_tables: Set[str] = set()
        
    def connect(self) -> bool:
        """Connect to the database"""
        try:
            # Try multiple ways to get database URL
            db_url = None
            
            # Method 1: Try to get from config
            try:
                settings = get_settings()
                db_url = settings.get_database_url()
            except Exception as e:
                logger.warning(f"Could not get database URL from settings: {e}")
            
            # Method 2: Environment variable
            if not db_url:
                db_url = os.getenv('DATABASE_URL')
            
            # Method 3: Try production database (from production environment)
            if not db_url:
                # Check for production database patterns
                potential_vars = [
                    'DATABASE_URL',
                    'POSTGRES_URL', 
                    'DB_URL',
                    'DATABASE_CONNECTION_STRING'
                ]
                for var in potential_vars:
                    val = os.getenv(var)
                    if val and val.startswith(('postgresql://', 'postgres://')):
                        db_url = val
                        break
            
            # Method 4: Default local PostgreSQL for development
            if not db_url:
                db_url = "postgresql://postgres:postgres@localhost:5432/socialmedia_dev"
                logger.warning(f"No database URL configured, using default: {db_url}")
            
            # Validate and fix URL format
            if db_url.startswith("sqlite"):
                logger.error("SQLite databases are not supported for this analysis")
                return False
            
            # Add SSL mode for production PostgreSQL if needed
            if db_url.startswith("postgresql://") and "sslmode" not in db_url:
                if "localhost" not in db_url and "127.0.0.1" not in db_url:
                    db_url += "?sslmode=require"
            
            self.engine = create_engine(db_url, pool_pre_ping=True, pool_timeout=30)
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.inspector = inspect(self.engine)
            self.metadata = MetaData()
            self.metadata.reflect(bind=self.engine)
            
            # Hide sensitive parts of URL for logging
            safe_url = db_url
            if '@' in safe_url:
                parts = safe_url.split('@')
                user_part = parts[0].split('//')[-1]
                if ':' in user_part:
                    user, _ = user_part.split(':', 1)
                    safe_url = safe_url.replace(user_part, f"{user}:***")
            
            logger.info(f"Connected to database: {safe_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            logger.error(f"Tried database URL pattern: {db_url[:30]}... (truncated)")
            return False
    
    def scan_existing_tables(self) -> Dict[str, TableInfo]:
        """Scan all existing tables in the database"""
        tables = {}
        
        try:
            table_names = self.inspector.get_table_names()
            logger.info(f"Found {len(table_names)} tables in database")
            
            for table_name in table_names:
                logger.info(f"Scanning table: {table_name}")
                tables[table_name] = self._analyze_table(table_name)
                
        except Exception as e:
            logger.error(f"Error scanning tables: {e}")
            self._add_issue('critical', 'scan_error', 'unknown', None, 
                          f"Failed to scan database tables: {e}", 
                          "Check database connection and permissions")
        
        return tables
    
    def _analyze_table(self, table_name: str) -> TableInfo:
        """Analyze a single table structure"""
        columns = {}
        primary_keys = []
        foreign_keys = {}
        indexes = []
        constraints = []
        
        try:
            # Get column information
            for col_info in self.inspector.get_columns(table_name):
                col_name = col_info['name']
                columns[col_name] = ColumnInfo(
                    name=col_name,
                    type_=str(col_info['type']),
                    nullable=col_info['nullable'],
                    default=col_info.get('default'),
                    primary_key=col_info.get('primary_key', False),
                    foreign_keys=[],
                    unique=False,
                    index=False
                )
            
            # Get primary key information
            pk_constraint = self.inspector.get_pk_constraint(table_name)
            if pk_constraint:
                primary_keys = pk_constraint.get('constrained_columns', [])
                for pk_col in primary_keys:
                    if pk_col in columns:
                        columns[pk_col].primary_key = True
            
            # Get foreign key information
            for fk in self.inspector.get_foreign_keys(table_name):
                constrained_cols = fk.get('constrained_columns', [])
                referred_table = fk.get('referred_table')
                referred_cols = fk.get('referred_columns', [])
                
                for i, col in enumerate(constrained_cols):
                    if i < len(referred_cols):
                        foreign_keys[col] = f"{referred_table}.{referred_cols[i]}"
                        if col in columns:
                            columns[col].foreign_keys.append(foreign_keys[col])
            
            # Get index information
            for idx in self.inspector.get_indexes(table_name):
                idx_name = idx['name']
                indexes.append(idx_name)
                for col_name in idx.get('column_names', []):
                    if col_name in columns:
                        columns[col_name].index = True
                        if idx.get('unique', False):
                            columns[col_name].unique = True
            
            # Get unique constraints
            for uc in self.inspector.get_unique_constraints(table_name):
                constraint_name = uc.get('name', 'unnamed')
                constraints.append(f"UNIQUE: {constraint_name}")
                for col_name in uc.get('column_names', []):
                    if col_name in columns:
                        columns[col_name].unique = True
            
            # Get check constraints
            try:
                for cc in self.inspector.get_check_constraints(table_name):
                    constraint_name = cc.get('name', 'unnamed')
                    constraints.append(f"CHECK: {constraint_name}")
            except:
                # Some databases don't support check constraints
                pass
            
            # Get row count
            row_count = None
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    row_count = result.scalar()
            except:
                pass
            
        except Exception as e:
            logger.error(f"Error analyzing table {table_name}: {e}")
            self._add_issue('warning', 'table_analysis_error', table_name, None,
                          f"Could not fully analyze table: {e}",
                          "Check table structure and permissions")
        
        return TableInfo(
            name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            indexes=indexes,
            constraints=constraints,
            row_count=row_count
        )
    
    def scan_model_definitions(self) -> Set[str]:
        """Scan SQLAlchemy model definitions"""
        model_tables = set()
        
        if not models:
            logger.warning("Could not import models module")
            return model_tables
        
        try:
            # Get all model classes
            for attr_name in dir(models):
                attr = getattr(models, attr_name)
                if (hasattr(attr, '__tablename__') and 
                    hasattr(attr, '__table__')):
                    table_name = attr.__tablename__
                    model_tables.add(table_name)
                    logger.info(f"Found model for table: {table_name}")
            
            logger.info(f"Found {len(model_tables)} model definitions")
            
        except Exception as e:
            logger.error(f"Error scanning model definitions: {e}")
            self._add_issue('warning', 'model_scan_error', 'models', None,
                          f"Could not scan model definitions: {e}",
                          "Check models.py file and imports")
        
        return model_tables
    
    def compare_tables_with_models(self, tables: Dict[str, TableInfo], model_tables: Set[str]):
        """Compare database tables with model definitions"""
        db_tables = set(tables.keys())
        
        # Check for missing tables
        missing_tables = model_tables - db_tables
        for table in missing_tables:
            self._add_issue('critical', 'missing_table', table, None,
                          f"Table {table} defined in models but missing from database",
                          f"Run migration or create table {table}")
        
        # Check for extra tables
        extra_tables = db_tables - model_tables
        for table in extra_tables:
            # Skip system tables and common extras
            if not table.startswith(('alembic_', 'pg_', 'information_', 'sql_')):
                self._add_issue('info', 'extra_table', table, None,
                              f"Table {table} exists in database but not in models",
                              f"Consider adding model for {table} or removing table")
        
        # Check for tables that exist in both
        common_tables = db_tables & model_tables
        logger.info(f"Comparing {len(common_tables)} common tables with models")
        
        for table_name in common_tables:
            self._compare_table_with_model(table_name, tables[table_name])
    
    def _compare_table_with_model(self, table_name: str, table_info: TableInfo):
        """Compare a specific table with its model definition"""
        if not models:
            return
            
        try:
            # Find the model class
            model_class = None
            for attr_name in dir(models):
                attr = getattr(models, attr_name)
                if (hasattr(attr, '__tablename__') and 
                    attr.__tablename__ == table_name):
                    model_class = attr
                    break
            
            if not model_class:
                return
            
            # Compare columns
            model_columns = {}
            for column in model_class.__table__.columns:
                model_columns[column.name] = column
            
            db_columns = set(table_info.columns.keys())
            model_column_names = set(model_columns.keys())
            
            # Check for missing columns in database
            missing_columns = model_column_names - db_columns
            for col_name in missing_columns:
                model_col = model_columns[col_name]
                self._add_issue('critical', 'missing_column', table_name, col_name,
                              f"Column {col_name} defined in model but missing from database table {table_name}",
                              f"Add column {col_name} {model_col.type} to table {table_name}")
            
            # Check for extra columns in database
            extra_columns = db_columns - model_column_names
            for col_name in extra_columns:
                self._add_issue('warning', 'extra_column', table_name, col_name,
                              f"Column {col_name} exists in database but not in model for table {table_name}",
                              f"Add {col_name} to model or remove from database")
            
            # Check column types for common columns
            common_columns = db_columns & model_column_names
            for col_name in common_columns:
                db_col = table_info.columns[col_name]
                model_col = model_columns[col_name]
                self._compare_column_types(table_name, col_name, db_col, model_col)
                
        except Exception as e:
            logger.error(f"Error comparing table {table_name} with model: {e}")
            self._add_issue('warning', 'model_comparison_error', table_name, None,
                          f"Could not compare with model: {e}",
                          "Check model definition and database structure")
    
    def _compare_column_types(self, table_name: str, col_name: str, 
                             db_col: ColumnInfo, model_col):
        """Compare database column type with model column type"""
        try:
            db_type = db_col.type_.upper()
            model_type = str(model_col.type).upper()
            
            # Normalize type names for comparison
            type_mappings = {
                'VARCHAR': 'TEXT',
                'CHAR': 'TEXT', 
                'CHARACTER VARYING': 'TEXT',
                'CHARACTER': 'TEXT',
                'INT': 'INTEGER',
                'INT4': 'INTEGER',
                'INT8': 'BIGINT',
                'BOOL': 'BOOLEAN',
                'TIMESTAMP WITHOUT TIME ZONE': 'TIMESTAMP',
                'TIMESTAMP WITH TIME ZONE': 'TIMESTAMPTZ'
            }
            
            # Apply mappings
            for old_type, new_type in type_mappings.items():
                if old_type in db_type:
                    db_type = db_type.replace(old_type, new_type)
                if old_type in model_type:
                    model_type = model_type.replace(old_type, new_type)
            
            # Check for type mismatches
            if not self._types_compatible(db_type, model_type):
                self._add_issue('warning', 'type_mismatch', table_name, col_name,
                              f"Column {col_name} type mismatch: DB={db_type}, Model={model_type}",
                              f"Align column types or create migration")
            
            # Check nullable mismatch
            model_nullable = model_col.nullable
            if db_col.nullable != model_nullable:
                self._add_issue('warning', 'nullable_mismatch', table_name, col_name,
                              f"Column {col_name} nullable mismatch: DB={db_col.nullable}, Model={model_nullable}",
                              "Update model or create migration to align nullable settings")
                              
        except Exception as e:
            logger.warning(f"Could not compare types for {table_name}.{col_name}: {e}")
    
    def _types_compatible(self, db_type: str, model_type: str) -> bool:
        """Check if database type and model type are compatible"""
        # Remove size specifications and extra info
        db_clean = db_type.split('(')[0].strip()
        model_clean = model_type.split('(')[0].strip()
        
        # Direct match
        if db_clean == model_clean:
            return True
        
        # Compatible type groups
        compatible_groups = [
            {'TEXT', 'VARCHAR', 'STRING', 'CHAR'},
            {'INTEGER', 'INT', 'BIGINT', 'SMALLINT'},
            {'BOOLEAN', 'BOOL'},
            {'TIMESTAMP', 'DATETIME'},
            {'NUMERIC', 'DECIMAL', 'FLOAT', 'REAL'},
            {'JSON', 'JSONB'}
        ]
        
        for group in compatible_groups:
            if db_clean in group and model_clean in group:
                return True
        
        return False
    
    def check_foreign_key_integrity(self, tables: Dict[str, TableInfo]):
        """Check foreign key relationships for integrity"""
        for table_name, table_info in tables.items():
            for col_name, fk_ref in table_info.foreign_keys.items():
                try:
                    ref_table, ref_col = fk_ref.split('.')
                    
                    # Check if referenced table exists
                    if ref_table not in tables:
                        self._add_issue('critical', 'missing_referenced_table', 
                                      table_name, col_name,
                                      f"Foreign key {col_name} references non-existent table {ref_table}",
                                      f"Create table {ref_table} or fix foreign key reference")
                    else:
                        # Check if referenced column exists
                        if ref_col not in tables[ref_table].columns:
                            self._add_issue('critical', 'missing_referenced_column',
                                          table_name, col_name,
                                          f"Foreign key {col_name} references non-existent column {ref_table}.{ref_col}",
                                          f"Create column {ref_col} in {ref_table} or fix reference")
                        
                except ValueError:
                    self._add_issue('warning', 'malformed_foreign_key',
                                  table_name, col_name,
                                  f"Malformed foreign key reference: {fk_ref}",
                                  "Fix foreign key reference format")
    
    def check_index_optimization(self, tables: Dict[str, TableInfo]):
        """Check for missing indexes on important columns"""
        important_patterns = [
            ('_id', 'ID columns should be indexed'),
            ('email', 'Email columns should be indexed'),  
            ('username', 'Username columns should be indexed'),
            ('created_at', 'Timestamp columns should be indexed'),
            ('updated_at', 'Timestamp columns should be indexed'),
            ('organization_id', 'Organization ID should be indexed'),
            ('user_id', 'User ID should be indexed'),
            ('platform', 'Platform columns should be indexed')
        ]
        
        for table_name, table_info in tables.items():
            for col_name, col_info in table_info.columns.items():
                for pattern, reason in important_patterns:
                    if (pattern in col_name.lower() and 
                        not col_info.index and 
                        not col_info.primary_key and
                        not col_info.unique):
                        self._add_issue('info', 'missing_index', table_name, col_name,
                                      f"Column {col_name} might benefit from an index: {reason}",
                                      f"Consider adding index on {table_name}.{col_name}")
    
    def check_alembic_consistency(self):
        """Check Alembic migration consistency"""
        try:
            # Check if alembic_version table exists
            if 'alembic_version' not in self.tables:
                self._add_issue('warning', 'missing_alembic_table', 'alembic_version', None,
                              "Alembic version table not found",
                              "Initialize Alembic: alembic init alembic")
                return
            
            # Check current migration version
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                current_version = result.scalar()
                
                if current_version:
                    logger.info(f"Current Alembic version: {current_version}")
                else:
                    self._add_issue('warning', 'no_alembic_version', 'alembic_version', None,
                                  "No Alembic version found in database",
                                  "Run: alembic stamp head")
            
            # Check for pending migrations
            alembic_dir = Path("alembic/versions")
            if alembic_dir.exists():
                migration_files = list(alembic_dir.glob("*.py"))
                logger.info(f"Found {len(migration_files)} migration files")
                
                if len(migration_files) == 0:
                    self._add_issue('info', 'no_migrations', 'alembic', None,
                                  "No Alembic migrations found",
                                  "Consider creating initial migration")
                                  
        except Exception as e:
            logger.error(f"Error checking Alembic consistency: {e}")
            self._add_issue('warning', 'alembic_check_error', 'alembic', None,
                          f"Could not check Alembic status: {e}",
                          "Check Alembic configuration and database connection")
    
    def _add_issue(self, severity: str, category: str, table: str, 
                   column: Optional[str], description: str, suggested_fix: str):
        """Add an issue to the issues list"""
        issue = SchemaIssue(
            severity=severity,
            category=category, 
            table=table,
            column=column,
            description=description,
            suggested_fix=suggested_fix
        )
        self.issues.append(issue)
        
        # Log immediately for visibility
        log_level = {'critical': logging.ERROR, 'warning': logging.WARNING, 'info': logging.INFO}
        logger.log(log_level.get(severity, logging.INFO), f"{severity.upper()}: {description}")
    
    def generate_report(self) -> str:
        """Generate comprehensive schema analysis report"""
        report = []
        
        # Header
        report.append("=" * 80)
        report.append("COMPREHENSIVE DATABASE SCHEMA ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Summary
        critical_count = len([i for i in self.issues if i.severity == 'critical'])
        warning_count = len([i for i in self.issues if i.severity == 'warning'])
        info_count = len([i for i in self.issues if i.severity == 'info'])
        
        report.append("📊 SUMMARY")
        report.append(f"  Total Tables Scanned: {len(self.tables)}")
        report.append(f"  Model Tables Found: {len(self.model_tables)}")
        report.append(f"  Critical Issues: {critical_count}")
        report.append(f"  Warning Issues: {warning_count}")
        report.append(f"  Info Issues: {info_count}")
        report.append("")
        
        # Overall status
        if critical_count == 0 and warning_count == 0:
            report.append("✅ SCHEMA STATUS: EXCELLENT")
            report.append("   No critical issues or warnings found")
        elif critical_count == 0:
            report.append("⚠️  SCHEMA STATUS: GOOD WITH RECOMMENDATIONS")
            report.append("   No critical issues, but some recommendations available")
        else:
            report.append("❌ SCHEMA STATUS: ISSUES FOUND")
            report.append("   Critical issues require immediate attention")
        report.append("")
        
        # Table overview
        if self.tables:
            report.append("📋 TABLE OVERVIEW")
            total_rows = 0
            for table_name, table_info in sorted(self.tables.items()):
                row_count = table_info.row_count or 0
                total_rows += row_count
                cols = len(table_info.columns)
                indexes = len(table_info.indexes)
                report.append(f"  {table_name:30} {cols:3} cols, {indexes:3} indexes, {row_count:8} rows")
            
            report.append(f"  {'TOTAL':30} {len(self.tables):3} tables, {total_rows:17} rows")
            report.append("")
        
        # Issues by severity
        if self.issues:
            for severity in ['critical', 'warning', 'info']:
                severity_issues = [i for i in self.issues if i.severity == severity]
                if severity_issues:
                    icon = {'critical': '🚨', 'warning': '⚠️', 'info': 'ℹ️'}[severity]
                    report.append(f"{icon} {severity.upper()} ISSUES ({len(severity_issues)})")
                    
                    for i, issue in enumerate(severity_issues, 1):
                        location = f"{issue.table}"
                        if issue.column:
                            location += f".{issue.column}"
                        
                        report.append(f"{i:3}. {location}")
                        report.append(f"     {issue.description}")
                        report.append(f"     Fix: {issue.suggested_fix}")
                        report.append("")
        
        # Recommendations
        report.append("🔧 RECOMMENDATIONS")
        report.append("=" * 50)
        
        if critical_count > 0:
            report.append("1. Address Critical Issues First:")
            critical_issues = [i for i in self.issues if i.severity == 'critical']
            for issue in critical_issues[:5]:  # Show top 5
                report.append(f"   - {issue.description}")
        
        if warning_count > 0:
            report.append("2. Review Warning Issues:")
            report.append("   - These may indicate schema inconsistencies")
            report.append("   - Consider creating migrations to resolve")
        
        report.append("3. Performance Optimizations:")
        index_issues = [i for i in self.issues if i.category == 'missing_index']
        if index_issues:
            report.append(f"   - Consider adding {len(index_issues)} suggested indexes")
        
        report.append("4. Maintenance Tasks:")
        report.append("   - Regular schema validation")
        report.append("   - Keep models in sync with database")
        report.append("   - Monitor database performance")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def run_full_scan(self) -> Dict[str, Any]:
        """Run complete database schema analysis"""
        if not self.connect():
            return {"error": "Could not connect to database"}
        
        logger.info("Starting comprehensive database schema scan...")
        
        # Step 1: Scan existing database tables
        self.tables = self.scan_existing_tables()
        
        # Step 2: Scan model definitions
        self.model_tables = self.scan_model_definitions()
        
        # Step 3: Compare tables with models
        self.compare_tables_with_models(self.tables, self.model_tables)
        
        # Step 4: Check foreign key integrity
        self.check_foreign_key_integrity(self.tables)
        
        # Step 5: Check index optimization
        self.check_index_optimization(self.tables)
        
        # Step 6: Check Alembic consistency
        self.check_alembic_consistency()
        
        # Generate final report
        report = self.generate_report()
        
        # Results summary
        results = {
            "status": "completed",
            "tables_scanned": len(self.tables),
            "model_tables": len(self.model_tables),
            "issues": {
                "critical": len([i for i in self.issues if i.severity == 'critical']),
                "warning": len([i for i in self.issues if i.severity == 'warning']),
                "info": len([i for i in self.issues if i.severity == 'info'])
            },
            "report": report,
            "issues_list": [
                {
                    "severity": issue.severity,
                    "category": issue.category,
                    "table": issue.table,
                    "column": issue.column,
                    "description": issue.description,
                    "fix": issue.suggested_fix
                } 
                for issue in self.issues
            ]
        }
        
        logger.info("Database schema scan completed")
        return results


def main():
    """Run the comprehensive database scanner"""
    print("Starting Comprehensive Database Schema Scan...")
    print("=" * 60)
    
    scanner = DatabaseSchemaScanner()
    results = scanner.run_full_scan()
    
    if "error" in results:
        print(f"❌ Error: {results['error']}")
        return 1
    
    # Print report
    print(results["report"])
    
    # Save detailed results
    report_file = Path("database_schema_analysis.json")
    import json
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: {report_file}")
    
    # Save report text
    report_text_file = Path("database_schema_report.txt") 
    with open(report_text_file, "w") as f:
        f.write(results["report"])
    
    print(f"📄 Report saved to: {report_text_file}")
    
    # Return appropriate exit code
    critical_issues = results["issues"]["critical"]
    if critical_issues > 0:
        print(f"\n❌ SCAN FAILED: {critical_issues} critical issues found")
        return 1
    else:
        warning_issues = results["issues"]["warning"]
        if warning_issues > 0:
            print(f"\n⚠️  SCAN PASSED WITH WARNINGS: {warning_issues} warnings found")
        else:
            print(f"\n✅ SCAN PASSED: No critical issues found")
        return 0


if __name__ == "__main__":
    sys.exit(main())