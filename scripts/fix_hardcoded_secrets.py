#!/usr/bin/env python3
"""
Emergency Script to Fix Hard-coded Secrets
Removes all hard-coded database credentials and other secrets from codebase
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict

class SecretsFixer:
    """Fix hard-coded secrets in files"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        
        # Known hard-coded production credentials that must be removed
        self.dangerous_credentials = [
            "BbsIYQtjBnhKwRL3F9kXbv1wrtsVxuTg",  # Database password
            "socialmedia:BbsIYQtjBnhKwRL3F9kXbv1wrtsVxuTg",  # Full credential
            "Admin053103",  # Hard-coded admin password
        ]
        
        # Files that should be fixed
        self.files_to_fix = [
            "initialize_alembic_from_existing.py",
            "run_migration.py",
            "alembic_simple_env.py",
            "comprehensive_schema_analysis.py",
            "create_all_remaining_tables.py",
            "create_essential_tables.py",
            "database_deep_scan.py",
            "database_scan.py", 
            "database_scan_simple.py",
            "database_simple_scan.py",
        ]
    
    def fix_database_credentials_in_file(self, file_path: Path) -> bool:
        """Fix hard-coded database credentials in a specific file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Replace hard-coded database URLs with environment variable usage
            patterns = [
                (r'DATABASE_URL\s*=\s*["\']postgresql://[^"\']+["\']', 
                 'DATABASE_URL = os.getenv("DATABASE_URL")\nif not DATABASE_URL:\n    print("❌ CRITICAL: DATABASE_URL environment variable must be set")\n    sys.exit(1)'),
                
                (r'database_url\s*=\s*["\']postgresql://[^"\']+["\']',
                 'database_url = os.getenv("DATABASE_URL")\nif not database_url:\n    print("❌ CRITICAL: DATABASE_URL environment variable must be set")\n    sys.exit(1)'),
                
                (r'db_url\s*=\s*["\']postgresql://[^"\']+["\']',
                 'db_url = os.getenv("DATABASE_URL")\nif not db_url:\n    print("❌ CRITICAL: DATABASE_URL environment variable must be set")\n    sys.exit(1)'),
                
                # Remove specific hard-coded credentials
                (r'postgresql://socialmedia:[^@]+@[^/]+/[^\s\'"]+', 'postgresql://USER:PASS@HOST:PORT/DB'),
            ]
            
            fixed = False
            for pattern, replacement in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
                    fixed = True
            
            # Ensure imports are present
            if fixed and 'import os' not in content:
                content = 'import os\nimport sys\n' + content
            
            # Write back if changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Fixed: {file_path.name}")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error fixing {file_path}: {e}")
            return False
    
    def fix_all_files(self):
        """Fix all files with hard-coded secrets"""
        print("🔧 Fixing Hard-coded Secrets in Codebase")
        print("=" * 50)
        
        fixed_files = 0
        
        for file_name in self.files_to_fix:
            file_path = self.project_root / file_name
            if file_path.exists():
                if self.fix_database_credentials_in_file(file_path):
                    fixed_files += 1
            else:
                print(f"⚠️  File not found: {file_name}")
        
        print(f"\n✅ Fixed {fixed_files} files")
        print("\n🚨 SECURITY ALERT: If you found credentials in these files:")
        print("   1. Immediately rotate all database passwords")
        print("   2. Check access logs for unauthorized usage")
        print("   3. Review and update all environment variables")
        print("   4. Consider this a potential security breach")

def main():
    """Main execution"""
    project_root = Path(__file__).parent.parent
    fixer = SecretsFixer(str(project_root))
    fixer.fix_all_files()

if __name__ == "__main__":
    main()