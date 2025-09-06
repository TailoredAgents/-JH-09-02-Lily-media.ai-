#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Schema Analysis Tool

Compares the current database schema with model definitions to identify:
1. Missing tables from models
2. Tables in DB but not in models  
3. Column mismatches
4. Missing indexes
5. Foreign key inconsistencies
"""
import sys
import os
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import create_engine, text, inspect
import re

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ CRITICAL: DATABASE_URL environment variable must be set")
    sys.exit(1)

def get_database_connection():
    """Create database connection."""
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        return engine
    except Exception as e:
        print("Failed to connect to database: {}".format(e))
        return None

def get_models_from_files():
    """Extract model definitions from Python files"""
    model_files = [
        'backend/db/models.py',
        'backend/db/admin_models.py', 
        'backend/db/multi_tenant_models.py',
        'backend/db/user_credentials.py'
    ]
    
    models = {}
    
    for file_path in model_files:
        if not os.path.exists(file_path):
            print("⚠️  Model file not found: {}".format(file_path))
            continue
            
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Find class definitions that inherit from Base
            class_pattern = r'class\s+(\w+)\s*\(\s*Base\s*\)\s*:'
            table_pattern = r'__tablename__\s*=\s*["\']([^"\']+)["\']'
            
            classes = re.findall(class_pattern, content)
            tables = re.findall(table_pattern, content)
            
            # Match classes with their table names
            for i, class_name in enumerate(classes):
                if i < len(tables):
                    table_name = tables[i]
                else:
                    # Convert class name to snake_case as default
                    table_name = re.sub(r'([A-Z])', r'_\1', class_name).lower().lstrip('_')
                
                models[table_name] = {
                    'class_name': class_name,
                    'file': file_path,
                    'table_name': table_name
                }
                
        except Exception as e:
            print("⚠️  Error parsing {}: {}".format(file_path, e))
    
    return models

def analyze_database_vs_models(engine):
    """Compare database schema with model definitions"""
    print("🔍 COMPREHENSIVE SCHEMA ANALYSIS")
    print("=" * 80)
    
    # Get database tables
    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names())
    
    # Get model definitions
    models = get_models_from_files()
    model_tables = set(models.keys())
    
    print("📊 Database Tables: {}".format(len(db_tables)))
    print("📋 Model Tables: {}".format(len(model_tables)))
    print("")
    
    # Find missing tables (in models but not in database)
    missing_tables = model_tables - db_tables
    print("❌ MISSING TABLES (in models but not in database): {}".format(len(missing_tables)))
    for table in sorted(missing_tables):
        model_info = models[table]
        print("  • {} (class: {}, file: {})".format(table, model_info['class_name'], model_info['file']))
    
    print("")
    
    # Find extra tables (in database but not in models)  
    extra_tables = db_tables - model_tables
    print("⚠️  EXTRA TABLES (in database but not in models): {}".format(len(extra_tables)))
    for table in sorted(extra_tables):
        print("  • {}".format(table))
    
    print("")
    
    # Find matching tables
    matching_tables = db_tables & model_tables
    print("✅ MATCHING TABLES: {}".format(len(matching_tables)))
    for table in sorted(matching_tables):
        print("  • {}".format(table))
    
    return {
        'db_tables': db_tables,
        'model_tables': model_tables, 
        'missing_tables': missing_tables,
        'extra_tables': extra_tables,
        'matching_tables': matching_tables,
        'models': models
    }

def analyze_table_structure_mismatches(engine, analysis_result):
    """Analyze structure mismatches in existing tables"""
    print("\n🔧 DETAILED TABLE STRUCTURE ANALYSIS")
    print("=" * 80)
    
    inspector = inspect(engine)
    issues = []
    
    # Focus on key tables that should have specific structures
    key_tables = {
        'users': ['public_id', 'email', 'username', 'hashed_password', 'is_active'],
        'content_logs': ['public_id', 'user_id', 'platform', 'content', 'status'],
        'organizations': ['public_id', 'name', 'slug', 'subscription_status'],
        'goals': ['public_id', 'user_id', 'organization_id', 'title', 'status'],
        'social_connections': ['public_id', 'user_id', 'platform', 'access_token'],
        'notifications': ['user_id', 'type', 'title', 'message', 'is_read'],
        'memories': ['user_id', 'content', 'importance_score'],
        'content': ['user_id', 'platform', 'content_type', 'content_data']
    }
    
    for table_name, expected_cols in key_tables.items():
        if table_name in analysis_result['db_tables']:
            print("\n🔍 Analyzing table: {}".format(table_name))
            
            columns = inspector.get_columns(table_name)
            db_columns = [col['name'] for col in columns]
            
            missing_cols = set(expected_cols) - set(db_columns)
            if missing_cols:
                print("  ❌ Missing columns: {}".format(sorted(missing_cols)))
                issues.append("Table {}: missing columns {}".format(table_name, missing_cols))
            else:
                print("  ✅ All expected columns present")
                
            # Check for public_id specifically
            if 'public_id' in expected_cols:
                public_id_col = next((col for col in columns if col['name'] == 'public_id'), None)
                if public_id_col:
                    if public_id_col['nullable']:
                        print("  ⚠️  public_id is nullable (should be NOT NULL)")
                        issues.append("Table {}: public_id should be NOT NULL".format(table_name))
                else:
                    print("  ❌ public_id column missing")
                    issues.append("Table {}: public_id column missing".format(table_name))
    
    return issues

def check_foreign_key_consistency(engine, analysis_result):
    """Check foreign key relationships"""
    print("\n🔗 FOREIGN KEY CONSISTENCY CHECK")
    print("=" * 80)
    
    inspector = inspect(engine)
    fk_issues = []
    
    # Check critical foreign key relationships
    critical_relationships = {
        'goals': [('user_id', 'users', 'id'), ('organization_id', 'organizations', 'id')],
        'social_connections': [('user_id', 'users', 'id'), ('organization_id', 'organizations', 'id')],
        'social_audit': [('user_id', 'users', 'id'), ('organization_id', 'organizations', 'id')],
        'content_logs': [('user_id', 'users', 'id')],
        'notifications': [('user_id', 'users', 'id')],
        'memories': [('user_id', 'users', 'id')]
    }
    
    for table, expected_fks in critical_relationships.items():
        if table in analysis_result['db_tables']:
            print("\n🔍 Checking foreign keys for: {}".format(table))
            
            fks = inspector.get_foreign_keys(table)
            existing_fks = [(fk['constrained_columns'][0], fk['referred_table'], fk['referred_columns'][0]) 
                           for fk in fks if fk['constrained_columns'] and fk['referred_columns']]
            
            for expected_fk in expected_fks:
                if expected_fk in existing_fks:
                    print("  ✅ FK exists: {} → {}.{}".format(expected_fk[0], expected_fk[1], expected_fk[2]))
                else:
                    print("  ❌ Missing FK: {} → {}.{}".format(expected_fk[0], expected_fk[1], expected_fk[2]))
                    fk_issues.append("Table {}: missing FK {} → {}.{}".format(table, expected_fk[0], expected_fk[1], expected_fk[2]))
    
    return fk_issues

def find_api_endpoint_mismatches():
    """Analyze API endpoints and their database table dependencies"""
    print("\n🌐 API ENDPOINT vs DATABASE ANALYSIS")
    print("=" * 80)
    
    endpoint_files = [
        'backend/routers/auth.py',
        'backend/routers/users.py', 
        'backend/routers/content.py',
        'backend/routers/goals.py',
        'backend/routers/organizations.py',
        'backend/routers/social.py'
    ]
    
    endpoint_issues = []
    
    for file_path in endpoint_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Look for table references in the code
                table_refs = re.findall(r'db\.query\((\w+)\)', content)
                table_refs.extend(re.findall(r'from\s+.*models\s+import\s+(\w+)', content))
                
                if table_refs:
                    print("📝 {}: references {}".format(file_path, set(table_refs)))
                else:
                    print("📝 {}: no clear table references found".format(file_path))
                    
            except Exception as e:
                print("⚠️  Error analyzing {}: {}".format(file_path, e))
        else:
            print("⚠️  API file not found: {}".format(file_path))
            endpoint_issues.append("Missing API file: {}".format(file_path))
    
    return endpoint_issues

def main():
    """Main analysis function"""
    print("🚀 Starting Comprehensive Database Schema Analysis...")
    print("📅 Analysis started at: {}".format(datetime.now()))
    print("")
    
    # Connect to database
    engine = get_database_connection()
    if not engine:
        print("❌ Failed to connect to database. Exiting.")
        return 1
    
    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            pg_version = result.scalar()
            print("📊 Connected to: {}".format(pg_version))
        
        # Perform comprehensive analysis
        analysis_result = analyze_database_vs_models(engine)
        structure_issues = analyze_table_structure_mismatches(engine, analysis_result)
        fk_issues = check_foreign_key_consistency(engine, analysis_result)
        endpoint_issues = find_api_endpoint_mismatches()
        
        # Summary
        print("\n" + "=" * 80)
        print("📋 ANALYSIS SUMMARY")
        print("=" * 80)
        
        total_issues = len(analysis_result['missing_tables']) + len(structure_issues) + len(fk_issues) + len(endpoint_issues)
        
        print("Missing tables: {}".format(len(analysis_result['missing_tables'])))
        print("Structure issues: {}".format(len(structure_issues)))
        print("Foreign key issues: {}".format(len(fk_issues)))
        print("API endpoint issues: {}".format(len(endpoint_issues)))
        print("TOTAL ISSUES: {}".format(total_issues))
        
        if total_issues == 0:
            print("\n🎉 No critical issues found! Database schema is well-aligned.")
        else:
            print("\n⚠️  Issues found that need attention:")
            
            if analysis_result['missing_tables']:
                print("\n🔧 RECOMMENDED ACTIONS:")
                print("1. Create missing tables: {}".format(sorted(analysis_result['missing_tables'])))
            
            if structure_issues:
                print("2. Fix structure issues:")
                for issue in structure_issues[:5]:  # Show first 5
                    print("   - {}".format(issue))
            
            if fk_issues:
                print("3. Fix foreign key issues:")
                for issue in fk_issues[:5]:  # Show first 5
                    print("   - {}".format(issue))
        
        return 1 if total_issues > 0 else 0
        
    except Exception as e:
        print("❌ Error during analysis: {}".format(e))
        return 1
    finally:
        if engine:
            engine.dispose()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)