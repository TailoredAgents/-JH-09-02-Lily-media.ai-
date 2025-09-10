#!/usr/bin/env python3
"""
Organization ID Filtering Audit Script
P1-1a: Audit all service queries for organization_id filtering

This script audits all database queries in services, APIs, and other components
to ensure proper multi-tenant isolation through organization_id filtering.
"""

import os
import re
import ast
import logging
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass, asdict
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QueryAuditResult:
    """Result of auditing a single query"""
    file_path: str
    line_number: int
    query_type: str
    has_org_filter: bool
    has_user_filter: bool
    query_snippet: str
    risk_level: str
    recommendation: str

@dataclass
class FileAuditSummary:
    """Summary of auditing a single file"""
    file_path: str
    total_queries: int
    secure_queries: int
    risky_queries: int
    issues_found: List[QueryAuditResult]

class OrganizationFilterAuditor:
    """Comprehensive auditor for organization_id filtering"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.results: List[QueryAuditResult] = []
        self.file_summaries: Dict[str, FileAuditSummary] = {}
        
        # Patterns for detecting database queries
        self.query_patterns = [
            # SQLAlchemy patterns
            r'\.query\(',
            r'db\.query\(',
            r'session\.query\(',
            r'\.filter\(',
            r'\.filter_by\(',
            r'\.execute\(',
            r'\.get\(',
            r'\.all\(\)',
            r'\.first\(\)',
            r'\.scalar\(\)',
            r'\.join\(',
            # Raw SQL patterns
            r'SELECT.*FROM',
            r'UPDATE.*SET',
            r'DELETE.*FROM',
            r'INSERT.*INTO',
            # ORM relationship queries
            r'\.relationship\(',
            r'\.backref\(',
        ]
        
        # Patterns indicating organization filtering
        self.org_filter_patterns = [
            r'organization_id\s*==',
            r'organization_id\s*=\s*',
            r'filter.*organization_id',
            r'filter_by.*organization_id',
            r'WHERE.*organization_id',
            r'organization_id\s*IN\s*\(',
            r'filter_by_organization\(',
            r'ensure_user_in_organization\(',
        ]
        
        # Patterns indicating user filtering (acceptable alternative)
        self.user_filter_patterns = [
            r'user_id\s*==',
            r'user_id\s*=\s*',
            r'filter.*user_id',
            r'filter_by.*user_id',
            r'WHERE.*user_id',
            r'user_id\s*IN\s*\(',
            r'current_user\.id',
        ]
        
        # Files to exclude from audit
        self.excluded_patterns = [
            r'test_.*\.py$',
            r'.*_test\.py$',
            r'migrations?/',
            r'alembic/',
            r'__pycache__',
            r'\.pyc$',
        ]

    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from audit"""
        file_str = str(file_path)
        return any(re.search(pattern, file_str) for pattern in self.excluded_patterns)

    def detect_queries_in_line(self, line: str, line_num: int) -> List[str]:
        """Detect database queries in a line of code"""
        queries = []
        for pattern in self.query_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                queries.append(pattern)
        return queries

    def has_organization_filter(self, content: str, context_lines: List[str]) -> bool:
        """Check if query has organization filtering"""
        # Check current line and surrounding context
        full_context = '\n'.join(context_lines) + '\n' + content
        return any(re.search(pattern, full_context, re.IGNORECASE) 
                  for pattern in self.org_filter_patterns)

    def has_user_filter(self, content: str, context_lines: List[str]) -> bool:
        """Check if query has user filtering"""
        full_context = '\n'.join(context_lines) + '\n' + content
        return any(re.search(pattern, full_context, re.IGNORECASE) 
                  for pattern in self.user_filter_patterns)

    def get_risk_level(self, has_org_filter: bool, has_user_filter: bool, 
                      file_path: str, query_snippet: str) -> Tuple[str, str]:
        """Determine risk level and recommendation"""
        
        # Check for safe patterns
        safe_patterns = [
            r'User\.id\s*==\s*current_user\.id',  # Self-access
            r'public\s*=\s*True',  # Public data
            r'is_active\s*=\s*True',  # Status filtering only
            r'configuration',  # Configuration tables
            r'system',  # System tables
        ]
        
        is_safe_pattern = any(re.search(pattern, query_snippet, re.IGNORECASE) 
                             for pattern in safe_patterns)
        
        if is_safe_pattern:
            return "LOW", "Query appears to access safe/public data"
        elif has_org_filter:
            return "LOW", "Query properly filtered by organization_id"
        elif has_user_filter:
            return "MEDIUM", "Query filtered by user_id - verify user belongs to organization"
        elif 'admin' in file_path.lower() or 'system' in file_path.lower():
            return "MEDIUM", "Admin/system query - verify proper authorization"
        else:
            return "HIGH", "Query lacks organization filtering - potential data leak"

    def audit_file(self, file_path: Path) -> FileAuditSummary:
        """Audit a single Python file for organization filtering"""
        
        if self.should_exclude_file(file_path):
            return FileAuditSummary(str(file_path), 0, 0, 0, [])
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return FileAuditSummary(str(file_path), 0, 0, 0, [])
        
        results = []
        total_queries = 0
        secure_queries = 0
        risky_queries = 0
        
        for line_num, line in enumerate(lines, 1):
            line_content = line.strip()
            
            # Skip comments and empty lines
            if not line_content or line_content.startswith('#'):
                continue
                
            # Detect queries in this line
            detected_queries = self.detect_queries_in_line(line_content, line_num)
            
            if detected_queries:
                total_queries += 1
                
                # Get context (5 lines before and after)
                start_idx = max(0, line_num - 6)
                end_idx = min(len(lines), line_num + 5)
                context_lines = [lines[i].strip() for i in range(start_idx, line_num - 1)]
                
                # Check for filtering
                has_org_filter = self.has_organization_filter(line_content, context_lines)
                has_user_filter = self.has_user_filter(line_content, context_lines)
                
                risk_level, recommendation = self.get_risk_level(
                    has_org_filter, has_user_filter, str(file_path), line_content
                )
                
                result = QueryAuditResult(
                    file_path=str(file_path),
                    line_number=line_num,
                    query_type=", ".join(detected_queries),
                    has_org_filter=has_org_filter,
                    has_user_filter=has_user_filter,
                    query_snippet=line_content,
                    risk_level=risk_level,
                    recommendation=recommendation
                )
                
                results.append(result)
                
                if risk_level == "HIGH":
                    risky_queries += 1
                else:
                    secure_queries += 1
        
        return FileAuditSummary(
            file_path=str(file_path),
            total_queries=total_queries,
            secure_queries=secure_queries,
            risky_queries=risky_queries,
            issues_found=results
        )

    def audit_directory(self, directory: str) -> None:
        """Audit all Python files in a directory"""
        dir_path = self.project_root / directory
        
        if not dir_path.exists():
            logger.warning(f"Directory {dir_path} does not exist")
            return
        
        logger.info(f"Auditing directory: {directory}")
        
        for py_file in dir_path.rglob("*.py"):
            if self.should_exclude_file(py_file):
                continue
                
            summary = self.audit_file(py_file)
            if summary.total_queries > 0:
                self.file_summaries[str(py_file)] = summary
                self.results.extend(summary.issues_found)

    def run_full_audit(self) -> Dict[str, Any]:
        """Run complete organization_id filtering audit"""
        logger.info("Starting comprehensive organization_id filtering audit...")
        
        # Audit key directories
        directories_to_audit = [
            "backend/api",
            "backend/services", 
            "backend/tasks",
            "backend/core",
            "backend/middleware"
        ]
        
        for directory in directories_to_audit:
            self.audit_directory(directory)
        
        # Analyze results
        total_files = len(self.file_summaries)
        total_queries = sum(s.total_queries for s in self.file_summaries.values())
        total_risky = sum(s.risky_queries for s in self.file_summaries.values())
        total_secure = sum(s.secure_queries for s in self.file_summaries.values())
        
        high_risk_queries = [r for r in self.results if r.risk_level == "HIGH"]
        medium_risk_queries = [r for r in self.results if r.risk_level == "MEDIUM"]
        
        # Generate summary
        audit_summary = {
            "timestamp": datetime.now().isoformat(),
            "audit_scope": directories_to_audit,
            "summary": {
                "total_files_audited": total_files,
                "total_queries_found": total_queries,
                "secure_queries": total_secure,
                "risky_queries": total_risky,
                "high_risk_count": len(high_risk_queries),
                "medium_risk_count": len(medium_risk_queries),
                "security_score": round((total_secure / max(total_queries, 1)) * 100, 1)
            },
            "high_risk_queries": [asdict(r) for r in high_risk_queries],
            "medium_risk_queries": [asdict(r) for r in medium_risk_queries], 
            "file_summaries": {k: asdict(v) for k, v in self.file_summaries.items()},
            "recommendations": self._generate_recommendations(high_risk_queries, medium_risk_queries)
        }
        
        return audit_summary

    def _generate_recommendations(self, high_risk: List[QueryAuditResult], 
                                 medium_risk: List[QueryAuditResult]) -> List[str]:
        """Generate specific recommendations based on audit results"""
        recommendations = []
        
        if high_risk:
            recommendations.append(
                f"CRITICAL: {len(high_risk)} high-risk queries found lacking organization filtering. "
                "These queries could lead to cross-tenant data access."
            )
            
            # Group by file for specific recommendations
            high_risk_files = {}
            for query in high_risk:
                if query.file_path not in high_risk_files:
                    high_risk_files[query.file_path] = []
                high_risk_files[query.file_path].append(query)
            
            for file_path, queries in high_risk_files.items():
                recommendations.append(
                    f"Review {file_path} (lines: {', '.join(str(q.line_number) for q in queries)}) "
                    "and add organization_id filtering using filter_by_organization() helper"
                )
        
        if medium_risk:
            recommendations.append(
                f"REVIEW: {len(medium_risk)} medium-risk queries found. "
                "Verify these queries properly enforce multi-tenant isolation."
            )
        
        if not high_risk and not medium_risk:
            recommendations.append("✅ All queries appear to have proper organization filtering!")
        
        # General recommendations
        recommendations.extend([
            "Use backend.middleware.tenant_isolation.filter_by_organization() helper for consistent filtering",
            "Implement organization_id as NOT NULL column where missing",
            "Add database-level multi-tenant policies for defense in depth",
            "Create automated tests for cross-tenant access prevention"
        ])
        
        return recommendations

def main():
    """Main execution function"""
    auditor = OrganizationFilterAuditor()
    results = auditor.run_full_audit()
    
    # Write detailed results to file
    output_file = "organization_id_audit_report.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary to console
    print("=" * 80)
    print("🔒 ORGANIZATION ID FILTERING AUDIT REPORT")
    print("=" * 80)
    
    summary = results["summary"]
    print(f"📊 Files Audited: {summary['total_files_audited']}")
    print(f"🔍 Total Queries: {summary['total_queries_found']}")
    print(f"✅ Secure Queries: {summary['secure_queries']}")
    print(f"⚠️  Risky Queries: {summary['risky_queries']}")
    print(f"🚨 High Risk: {summary['high_risk_count']}")
    print(f"⚡ Medium Risk: {summary['medium_risk_count']}")
    print(f"🛡️  Security Score: {summary['security_score']}%")
    print()
    
    if summary['high_risk_count'] > 0:
        print("🚨 HIGH RISK QUERIES:")
        for query in results["high_risk_queries"]:
            print(f"   {query['file_path']}:{query['line_number']} - {query['query_snippet']}")
        print()
    
    if summary['medium_risk_count'] > 0:
        print("⚡ MEDIUM RISK QUERIES:")
        for query in results["medium_risk_queries"][:10]:  # Show first 10
            print(f"   {query['file_path']}:{query['line_number']} - {query['query_snippet']}")
        if len(results["medium_risk_queries"]) > 10:
            print(f"   ... and {len(results['medium_risk_queries']) - 10} more")
        print()
    
    print("📋 RECOMMENDATIONS:")
    for i, rec in enumerate(results["recommendations"], 1):
        print(f"   {i}. {rec}")
    
    print(f"\n📄 Detailed report saved to: {output_file}")
    
    # Return status code based on risk level
    if summary['high_risk_count'] > 0:
        print("\n❌ AUDIT FAILED: High-risk queries found")
        return 1
    elif summary['medium_risk_count'] > 5:  # Allow some medium risk
        print("\n⚠️  AUDIT WARNING: Multiple medium-risk queries found")
        return 2
    else:
        print("\n✅ AUDIT PASSED: No critical issues found")
        return 0

if __name__ == "__main__":
    exit(main())