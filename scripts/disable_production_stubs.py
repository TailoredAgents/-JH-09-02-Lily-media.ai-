#!/usr/bin/env python3
"""
Production Stub/Fallback Disabling Script
P1-3a: Disable stubs/fallbacks in production

This script identifies and disables development-specific stubs, fallbacks, and insecure configurations
that should not be active in production environments.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SecurityIssue:
    """Security issue found in code"""
    file_path: str
    line_number: int
    issue_type: str
    description: str
    current_code: str
    recommended_fix: str
    severity: str

class ProductionStubDisabler:
    """Identifies and fixes production security issues"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.issues_found: List[SecurityIssue] = []
        
        # Patterns that indicate development-only features
        self.insecure_patterns = [
            # CORS wildcards - CRITICAL
            (r'allow_origins=\["?\*"?\]', 'CRITICAL', 'CORS wildcard origins', 
             'Replace with specific allowed origins'),
            (r'allow_methods=\["?\*"?\]', 'HIGH', 'CORS wildcard methods',
             'Replace with specific HTTP methods'),
            (r'allow_headers=\["?\*"?\]', 'HIGH', 'CORS wildcard headers', 
             'Replace with specific headers'),
            (r'allow_credentials=True.*allow_origins=\["?\*"?\]', 'CRITICAL', 
             'CORS credentials with wildcard origins', 'Fix credentials + wildcard combination'),
             
            # Development mode checks
            (r'if.*environment.*==.*["\']development["\']', 'MEDIUM', 
             'Development environment check', 'Ensure production security'),
            (r'if.*debug.*==.*True', 'MEDIUM', 
             'Debug mode check', 'Ensure disabled in production'),
             
            # Hardcoded test/development values
            (r'test_mode\s*=\s*True', 'HIGH', 'Test mode enabled', 'Disable test mode'),
            (r'debug\s*=\s*True', 'HIGH', 'Debug mode enabled', 'Disable debug mode'),
            (r'ENVIRONMENT.*=.*["\']development["\']', 'MEDIUM', 
             'Hardcoded development environment', 'Use environment variables'),
             
            # Insecure defaults
            (r'verify_ssl\s*=\s*False', 'HIGH', 'SSL verification disabled', 'Enable SSL verification'),
            (r'check_hostname\s*=\s*False', 'HIGH', 'Hostname verification disabled', 
             'Enable hostname verification'),
            (r'ssl_context.*=.*None', 'MEDIUM', 'No SSL context', 'Configure SSL context'),
        ]
    
    def scan_file(self, file_path: Path) -> List[SecurityIssue]:
        """Scan a single file for security issues"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return []
        
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            for pattern, severity, issue_type, recommendation in self.insecure_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issue = SecurityIssue(
                        file_path=str(file_path),
                        line_number=line_num,
                        issue_type=issue_type,
                        description=f"Line {line_num}: {issue_type}",
                        current_code=line.strip(),
                        recommended_fix=recommendation,
                        severity=severity
                    )
                    issues.append(issue)
        
        return issues
    
    def scan_project(self) -> Dict[str, Any]:
        """Scan entire project for production security issues"""
        logger.info("Scanning project for production stubs and fallbacks...")
        
        # Scan Python files
        python_files = list(self.project_root.rglob("*.py"))
        
        # Exclude test files and migrations
        excluded_patterns = [r'test_.*\.py$', r'.*_test\.py$', r'alembic/versions/', r'__pycache__']
        python_files = [
            f for f in python_files 
            if not any(re.search(pattern, str(f)) for pattern in excluded_patterns)
        ]
        
        logger.info(f"Scanning {len(python_files)} Python files...")
        
        for file_path in python_files:
            file_issues = self.scan_file(file_path)
            self.issues_found.extend(file_issues)
        
        # Categorize issues by severity
        critical_issues = [i for i in self.issues_found if i.severity == "CRITICAL"]
        high_issues = [i for i in self.issues_found if i.severity == "HIGH"]
        medium_issues = [i for i in self.issues_found if i.severity == "MEDIUM"]
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "files_scanned": len(python_files),
            "total_issues": len(self.issues_found),
            "critical_issues": len(critical_issues),
            "high_issues": len(high_issues), 
            "medium_issues": len(medium_issues),
            "issues_by_severity": {
                "critical": [self._issue_to_dict(i) for i in critical_issues],
                "high": [self._issue_to_dict(i) for i in high_issues],
                "medium": [self._issue_to_dict(i) for i in medium_issues]
            },
            "remediation_plan": self._generate_remediation_plan(critical_issues, high_issues, medium_issues)
        }
        
        return results
    
    def _issue_to_dict(self, issue: SecurityIssue) -> Dict[str, Any]:
        """Convert SecurityIssue to dictionary"""
        return {
            "file_path": issue.file_path,
            "line_number": issue.line_number,
            "issue_type": issue.issue_type,
            "description": issue.description,
            "current_code": issue.current_code,
            "recommended_fix": issue.recommended_fix,
            "severity": issue.severity
        }
    
    def _generate_remediation_plan(self, critical: List[SecurityIssue], 
                                  high: List[SecurityIssue], medium: List[SecurityIssue]) -> List[str]:
        """Generate specific remediation recommendations"""
        plan = []
        
        if critical:
            plan.append("🚨 CRITICAL: Fix CORS wildcard configurations immediately")
            cors_files = set(i.file_path for i in critical if "CORS" in i.issue_type)
            for file_path in cors_files:
                plan.append(f"  - Fix CORS configuration in {file_path}")
        
        if high:
            plan.append("⚠️ HIGH: Disable debug modes and insecure SSL settings")
            
        if medium:
            plan.append("📋 MEDIUM: Review development environment checks")
        
        # Specific fixes
        plan.extend([
            "1. Replace allow_origins=['*'] with specific domains",
            "2. Set ENVIRONMENT=production in all deployment configs", 
            "3. Ensure debug=False in production configurations",
            "4. Enable SSL verification for all external connections",
            "5. Review and harden all middleware configurations"
        ])
        
        return plan

def apply_cors_fixes():
    """Apply fixes to critical CORS issues"""
    logger.info("Applying CORS security fixes...")
    
    # Critical files with CORS wildcards that need immediate fixing
    cors_fixes = [
        {
            "file": "backend/app_complete.py",
            "old": '    allow_origins=["*"],',
            "new": '    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),',
            "imports": "import os"
        },
        {
            "file": "backend/core/app_factory.py", 
            "old": '            allow_origins=["*"],',
            "new": '            allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),',
            "imports": None  # Already has os import
        },
        {
            "file": "backend/main_minimal.py",
            "old": '    allow_origins=["*"],',
            "new": '    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),',
            "imports": "import os"
        }
    ]
    
    for fix in cors_fixes:
        file_path = Path(fix["file"])
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Add imports if needed
                if fix["imports"] and fix["imports"] not in content:
                    # Add import at the top after existing imports
                    lines = content.splitlines()
                    import_line = len([l for l in lines if l.startswith("import ") or l.startswith("from ")])
                    lines.insert(import_line, fix["imports"])
                    content = "\n".join(lines)
                
                # Apply the fix
                if fix["old"] in content:
                    content = content.replace(fix["old"], fix["new"])
                    
                    with open(file_path, 'w') as f:
                        f.write(content)
                    
                    logger.info(f"✅ Fixed CORS wildcard in {file_path}")
                else:
                    logger.info(f"⚠️ Pattern not found in {file_path}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to fix {file_path}: {e}")

def main():
    """Main execution function"""
    scanner = ProductionStubDisabler()
    results = scanner.scan_project()
    
    # Save detailed results
    output_file = "production_stubs_audit.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("=" * 80)
    print("🔒 PRODUCTION STUBS & FALLBACKS AUDIT")
    print("=" * 80)
    
    print(f"📂 Files Scanned: {results['files_scanned']}")
    print(f"🚨 Critical Issues: {results['critical_issues']}")
    print(f"⚠️  High Issues: {results['high_issues']}")
    print(f"📋 Medium Issues: {results['medium_issues']}")
    print(f"📊 Total Issues: {results['total_issues']}")
    print()
    
    # Show critical issues
    if results['critical_issues'] > 0:
        print("🚨 CRITICAL ISSUES:")
        for issue in results['issues_by_severity']['critical']:
            print(f"   {issue['file_path']}:{issue['line_number']} - {issue['issue_type']}")
            print(f"      Code: {issue['current_code']}")
            print(f"      Fix:  {issue['recommended_fix']}")
        print()
    
    # Show high issues
    if results['high_issues'] > 0:
        print("⚠️ HIGH PRIORITY ISSUES:")
        for issue in results['issues_by_severity']['high'][:10]:  # Show first 10
            print(f"   {issue['file_path']}:{issue['line_number']} - {issue['issue_type']}")
        if results['high_issues'] > 10:
            print(f"   ... and {results['high_issues'] - 10} more")
        print()
    
    print("📋 REMEDIATION PLAN:")
    for i, rec in enumerate(results['remediation_plan'], 1):
        print(f"   {i}. {rec}")
    
    # Apply critical fixes automatically
    if results['critical_issues'] > 0:
        print("\n🔧 APPLYING CRITICAL CORS FIXES...")
        apply_cors_fixes()
    
    print(f"\n📄 Detailed report saved to: {output_file}")
    
    # Return exit code based on severity
    if results['critical_issues'] > 0:
        print("\n❌ CRITICAL ISSUES FOUND - Manual intervention required")
        return 1
    elif results['high_issues'] > 5:
        print("\n⚠️  HIGH PRIORITY ISSUES - Review recommended")
        return 1
    else:
        print("\n✅ No critical production security issues found")
        return 0

if __name__ == "__main__":
    exit(main())