#!/usr/bin/env python3
"""
Fast Database Schema Scanner
Quick analysis focusing on critical issues for production database
"""
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Any
from sqlalchemy import create_engine, text, inspect, MetaData
from sqlalchemy.engine import Engine
import json

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

try:
    from backend.db import models
    from backend.core.config import get_settings
except ImportError as e:
    print(f"Warning: Could not import backend modules: {e}")
    models = None

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class FastSchemaScanner:
    """Quick schema analysis for production database"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = None
        self.inspector = None
        self.issues = []
        
    def connect(self):
        """Connect to database"""
        try:
            self.engine = create_engine(
                self.db_url, 
                pool_pre_ping=True, 
                pool_timeout=10,
                connect_args={"connect_timeout": 10}
            )
            
            # Quick connection test
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.inspector = inspect(self.engine)
            logger.info("✅ Connected to production database")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            return False
    
    def get_table_list(self) -> List[str]:
        """Get list of all tables quickly"""
        try:
            tables = self.inspector.get_table_names()
            logger.info(f"📋 Found {len(tables)} tables in database")
            return tables
        except Exception as e:
            logger.error(f"❌ Could not get table list: {e}")
            return []
    
    def get_model_tables(self) -> Set[str]:
        """Get expected tables from models"""
        model_tables = set()
        
        if not models:
            logger.warning("⚠️  Could not import models")
            return model_tables
        
        try:
            for attr_name in dir(models):
                attr = getattr(models, attr_name)
                if hasattr(attr, '__tablename__'):
                    model_tables.add(attr.__tablename__)
            
            logger.info(f"📊 Found {len(model_tables)} model definitions")
            return model_tables
            
        except Exception as e:
            logger.error(f"❌ Error scanning models: {e}")
            return model_tables
    
    def check_critical_tables(self, db_tables: List[str], model_tables: Set[str]) -> Dict[str, Any]:
        """Check for critical missing tables"""
        db_set = set(db_tables)
        
        # Critical tables that must exist
        critical_tables = {
            'users', 'organizations', 'social_connections', 'content',
            'alembic_version', 'social_platform_connections'
        }
        
        results = {
            'missing_critical': [],
            'missing_from_models': [],
            'extra_tables': [],
            'total_tables': len(db_tables),
            'model_tables': len(model_tables)
        }
        
        # Check critical tables
        for table in critical_tables:
            if table not in db_set:
                results['missing_critical'].append(table)
                self.issues.append({
                    'severity': 'CRITICAL',
                    'type': 'missing_critical_table',
                    'table': table,
                    'description': f'Critical table {table} is missing'
                })
        
        # Check model tables
        for table in model_tables:
            if table not in db_set:
                results['missing_from_models'].append(table)
                self.issues.append({
                    'severity': 'WARNING',
                    'type': 'missing_table',
                    'table': table,
                    'description': f'Table {table} defined in models but missing from database'
                })
        
        # Check extra tables (not in models)
        for table in db_tables:
            if table not in model_tables and not table.startswith(('alembic_', 'pg_')):
                results['extra_tables'].append(table)
        
        return results
    
    def check_table_row_counts(self, tables: List[str]) -> Dict[str, int]:
        """Get row counts for all tables efficiently"""
        row_counts = {}
        
        try:
            with self.engine.connect() as conn:
                for table in tables:
                    try:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        row_counts[table] = count
                    except Exception as e:
                        logger.warning(f"⚠️  Could not count rows in {table}: {e}")
                        row_counts[table] = -1
            
            logger.info("📊 Retrieved row counts for all tables")
            
        except Exception as e:
            logger.error(f"❌ Error getting row counts: {e}")
        
        return row_counts
    
    def check_alembic_status(self) -> Dict[str, Any]:
        """Check Alembic migration status"""
        status = {
            'table_exists': False,
            'current_version': None,
            'version_count': 0
        }
        
        try:
            tables = self.inspector.get_table_names()
            
            if 'alembic_version' in tables:
                status['table_exists'] = True
                
                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                    current = result.scalar()
                    status['current_version'] = current
                    
                    if current:
                        logger.info(f"🔄 Current Alembic version: {current}")
                    else:
                        logger.warning("⚠️  No Alembic version set")
                        self.issues.append({
                            'severity': 'WARNING',
                            'type': 'no_alembic_version',
                            'table': 'alembic_version',
                            'description': 'Alembic version table exists but no version is set'
                        })
            else:
                logger.warning("⚠️  Alembic version table not found")
                self.issues.append({
                    'severity': 'WARNING',
                    'type': 'missing_alembic',
                    'table': 'alembic_version',
                    'description': 'Alembic version tracking table is missing'
                })
        
        except Exception as e:
            logger.error(f"❌ Error checking Alembic: {e}")
        
        return status
    
    def check_critical_columns(self, critical_tables: List[str]) -> Dict[str, Any]:
        """Check critical columns exist in important tables"""
        results = {
            'missing_columns': [],
            'tables_checked': 0,
            'issues_found': 0
        }
        
        # Expected columns for critical tables
        expected_columns = {
            'users': ['id', 'email', 'username', 'created_at'],
            'organizations': ['id', 'name', 'created_at'],
            'social_connections': ['id', 'user_id', 'platform', 'created_at'],
            'social_platform_connections': ['id', 'organization_id', 'platform', 'created_at'],
            'content': ['id', 'user_id', 'title', 'created_at']
        }
        
        try:
            for table_name in critical_tables:
                if table_name in expected_columns:
                    try:
                        columns = [col['name'] for col in self.inspector.get_columns(table_name)]
                        results['tables_checked'] += 1
                        
                        for expected_col in expected_columns[table_name]:
                            if expected_col not in columns:
                                issue = f"{table_name}.{expected_col}"
                                results['missing_columns'].append(issue)
                                results['issues_found'] += 1
                                self.issues.append({
                                    'severity': 'CRITICAL',
                                    'type': 'missing_column',
                                    'table': table_name,
                                    'column': expected_col,
                                    'description': f'Critical column {expected_col} missing from {table_name}'
                                })
                    
                    except Exception as e:
                        logger.warning(f"⚠️  Could not check columns in {table_name}: {e}")
        
        except Exception as e:
            logger.error(f"❌ Error checking critical columns: {e}")
        
        return results
    
    def check_indexes_and_constraints(self, tables: List[str]) -> Dict[str, Any]:
        """Quick check for basic indexes and constraints"""
        results = {
            'tables_without_pk': [],
            'large_tables_without_indexes': [],
            'foreign_key_issues': []
        }
        
        try:
            for table_name in tables[:10]:  # Check first 10 tables for speed
                try:
                    # Check primary key
                    pk_constraint = self.inspector.get_pk_constraint(table_name)
                    if not pk_constraint or not pk_constraint.get('constrained_columns'):
                        results['tables_without_pk'].append(table_name)
                        self.issues.append({
                            'severity': 'CRITICAL',
                            'type': 'no_primary_key',
                            'table': table_name,
                            'description': f'Table {table_name} has no primary key'
                        })
                
                except Exception as e:
                    logger.warning(f"⚠️  Could not check constraints for {table_name}: {e}")
        
        except Exception as e:
            logger.error(f"❌ Error checking indexes and constraints: {e}")
        
        return results
    
    def generate_summary_report(self, analysis_results: Dict[str, Any]) -> str:
        """Generate concise summary report"""
        
        critical_issues = [i for i in self.issues if i['severity'] == 'CRITICAL']
        warning_issues = [i for i in self.issues if i['severity'] == 'WARNING']
        
        lines = []
        lines.append("=" * 70)
        lines.append("🔍 FAST DATABASE SCHEMA ANALYSIS REPORT")
        lines.append("=" * 70)
        lines.append(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Overall Status
        if len(critical_issues) == 0:
            lines.append("✅ SCHEMA STATUS: HEALTHY")
            lines.append("   No critical issues found")
        else:
            lines.append("❌ SCHEMA STATUS: CRITICAL ISSUES FOUND")
            lines.append(f"   {len(critical_issues)} critical issues require immediate attention")
        lines.append("")
        
        # Summary Statistics
        lines.append("📊 DATABASE SUMMARY")
        lines.append(f"  Total Tables: {analysis_results.get('table_count', 0)}")
        lines.append(f"  Model Tables: {analysis_results.get('model_count', 0)}")
        lines.append(f"  Critical Issues: {len(critical_issues)}")
        lines.append(f"  Warning Issues: {len(warning_issues)}")
        lines.append("")
        
        # Table Status
        table_results = analysis_results.get('table_check', {})
        if table_results:
            lines.append("📋 TABLE STATUS")
            if table_results.get('missing_critical'):
                lines.append(f"  ❌ Missing Critical Tables: {table_results['missing_critical']}")
            if table_results.get('missing_from_models'):
                lines.append(f"  ⚠️  Missing Model Tables: {len(table_results['missing_from_models'])}")
            if table_results.get('extra_tables'):
                lines.append(f"  ℹ️  Extra Tables: {len(table_results['extra_tables'])}")
            lines.append("")
        
        # Row Counts (top tables)
        row_counts = analysis_results.get('row_counts', {})
        if row_counts:
            lines.append("📈 TOP TABLES BY SIZE")
            sorted_tables = sorted(row_counts.items(), key=lambda x: x[1], reverse=True)
            for table, count in sorted_tables[:10]:
                if count >= 0:
                    lines.append(f"  {table:<25} {count:>10,} rows")
            lines.append("")
        
        # Critical Issues
        if critical_issues:
            lines.append("🚨 CRITICAL ISSUES")
            for i, issue in enumerate(critical_issues[:10], 1):
                lines.append(f"{i:2d}. {issue['description']}")
                if 'table' in issue:
                    lines.append(f"     Table: {issue['table']}")
            if len(critical_issues) > 10:
                lines.append(f"     ... and {len(critical_issues) - 10} more critical issues")
            lines.append("")
        
        # Alembic Status
        alembic_status = analysis_results.get('alembic', {})
        if alembic_status:
            lines.append("🔄 MIGRATION STATUS")
            if alembic_status.get('table_exists'):
                version = alembic_status.get('current_version', 'None')
                lines.append(f"  Current Version: {version}")
            else:
                lines.append("  ❌ Alembic not initialized")
            lines.append("")
        
        # Recommendations
        lines.append("💡 IMMEDIATE ACTIONS REQUIRED")
        if critical_issues:
            lines.append("1. 🚨 Address critical issues immediately:")
            for issue in critical_issues[:5]:
                lines.append(f"   - {issue['description']}")
        
        if warning_issues:
            lines.append("2. ⚠️  Review warning issues:")
            lines.append(f"   - {len(warning_issues)} warning issues found")
        
        lines.append("3. 📋 Run full schema migration if needed")
        lines.append("4. 🔄 Ensure Alembic is properly configured")
        
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def run_fast_scan(self) -> Dict[str, Any]:
        """Run fast schema analysis"""
        if not self.connect():
            return {"error": "Connection failed"}
        
        logger.info("🚀 Starting fast database schema scan...")
        
        # Get table lists
        db_tables = self.get_table_list()
        model_tables = self.get_model_tables()
        
        # Core analysis
        results = {
            'table_count': len(db_tables),
            'model_count': len(model_tables),
            'table_check': self.check_critical_tables(db_tables, model_tables),
            'row_counts': self.check_table_row_counts(db_tables),
            'alembic': self.check_alembic_status(),
            'critical_columns': self.check_critical_columns(db_tables),
            'constraints': self.check_indexes_and_constraints(db_tables),
            'issues': self.issues
        }
        
        # Generate report
        report = self.generate_summary_report(results)
        results['report'] = report
        
        logger.info("✅ Fast schema scan completed")
        return results


def main():
    """Run fast schema scan"""
    
    # Get database URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        print("Set it with: export DATABASE_URL='postgresql://...'")
        return 1
    
    print("🔍 Fast Database Schema Scanner")
    print("=" * 50)
    
    scanner = FastSchemaScanner(db_url)
    results = scanner.run_fast_scan()
    
    if "error" in results:
        print(f"❌ Error: {results['error']}")
        return 1
    
    # Print report
    print(results["report"])
    
    # Save results
    with open("fast_schema_analysis.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    with open("fast_schema_report.txt", "w") as f:
        f.write(results["report"])
    
    print(f"\n📄 Results saved to: fast_schema_analysis.json")
    print(f"📄 Report saved to: fast_schema_report.txt")
    
    # Exit code based on critical issues
    critical_count = len([i for i in results['issues'] if i['severity'] == 'CRITICAL'])
    
    if critical_count > 0:
        print(f"\n❌ SCAN FAILED: {critical_count} critical issues found")
        return 1
    else:
        print(f"\n✅ SCAN PASSED: No critical issues found")
        return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())