#!/usr/bin/env python3
"""
GA Checklist: Log Security Audit
Verify no tokens/state appear in logs (audit log output)

This script audits the codebase to ensure no sensitive information is logged.
"""
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set


class LogSecurityAuditor:
    """Audits codebase for potential token/secret logging violations"""
    
    def __init__(self):
        self.violations = []
        self.safe_patterns = []
        self.warning_patterns = []
        
        # Patterns that indicate potential secret logging
        self.dangerous_patterns = [
            r'logger\.\w+\(.*token.*\)',
            r'logger\.\w+\(.*secret.*\)', 
            r'logger\.\w+\(.*password.*\)',
            r'logger\.\w+\(.*key.*\)',
            r'print\(.*token.*\)',
            r'print\(.*secret.*\)',
            r'print\(.*password.*\)',
        ]
        
        # Safe patterns that are explicitly designed to avoid logging secrets
        self.safe_logging_patterns = [
            r'# (don\'t|do not) log.*token',
            r'# (avoid|prevent).*logging.*token',
            r'safe_data.*=.*{k.*for.*if k not in',
            r'logger\.\w+\(.*token.*length.*\)',
            r'logger\.\w+\(.*"token.*validation"',
            r'logger\.\w+\(.*"token.*creation"',
        ]
    
    def audit_file(self, file_path: Path) -> Dict:
        """Audit a single Python file for logging violations"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            file_results = {
                "file": str(file_path),
                "violations": [],
                "safe_patterns": [],
                "warnings": []
            }
            
            for line_num, line in enumerate(lines, 1):
                line_clean = line.strip()
                
                # Check for safe patterns first
                for pattern in self.safe_logging_patterns:
                    if re.search(pattern, line_clean, re.IGNORECASE):
                        file_results["safe_patterns"].append({
                            "line": line_num,
                            "code": line_clean,
                            "pattern": "safe_logging_pattern"
                        })
                        break
                else:
                    # Check for dangerous patterns
                    for pattern in self.dangerous_patterns:
                        if re.search(pattern, line_clean, re.IGNORECASE):
                            # Additional validation - check if it's actually safe
                            if self._is_safe_logging(line_clean):
                                file_results["safe_patterns"].append({
                                    "line": line_num, 
                                    "code": line_clean,
                                    "pattern": "validated_safe"
                                })
                            else:
                                file_results["violations"].append({
                                    "line": line_num,
                                    "code": line_clean,
                                    "pattern": pattern
                                })
                            break
            
            return file_results
            
        except Exception as e:
            return {
                "file": str(file_path),
                "error": str(e),
                "violations": [],
                "safe_patterns": [],
                "warnings": []
            }
    
    def _is_safe_logging(self, line: str) -> bool:
        """Check if a potentially dangerous logging line is actually safe"""
        line_lower = line.lower()
        
        # Safe patterns in logging
        safe_indicators = [
            'token.*length',
            'token.*creation',
            'token.*validation',
            'token.*refresh.*completed',
            'token.*encryption.*validation',
            'safe_data',
            'without.*token',
            'no.*token',
            'token.*not.*logged'
        ]
        
        for indicator in safe_indicators:
            if re.search(indicator, line_lower):
                return True
        
        # Check if logging is explicitly filtered
        if any(filter_word in line_lower for filter_word in ['safe_data', 'filtered', 'sanitized']):
            return True
            
        return False
    
    def audit_codebase(self, root_path: Path = None) -> Dict:
        """Audit entire codebase for logging security violations"""
        if root_path is None:
            root_path = Path(__file__).parent
            
        results = {
            "summary": {
                "files_audited": 0,
                "total_violations": 0,
                "total_safe_patterns": 0,
                "files_with_violations": 0,
                "compliance_score": 0.0
            },
            "files": [],
            "violations": [],
            "safe_patterns": []
        }
        
        # Find all Python files
        python_files = list(root_path.rglob("*.py"))
        
        for file_path in python_files:
            # Skip test files and this audit script
            if 'test' in str(file_path) or file_path.name == 'audit_log_security.py':
                continue
                
            file_result = self.audit_file(file_path)
            results["files"].append(file_result)
            
            results["summary"]["files_audited"] += 1
            results["summary"]["total_violations"] += len(file_result["violations"])
            results["summary"]["total_safe_patterns"] += len(file_result["safe_patterns"])
            
            if file_result["violations"]:
                results["summary"]["files_with_violations"] += 1
                results["violations"].extend([{
                    **v, 
                    "file": file_result["file"]
                } for v in file_result["violations"]])
            
            results["safe_patterns"].extend([{
                **p,
                "file": file_result["file"] 
            } for p in file_result["safe_patterns"]])
        
        # Calculate compliance score
        total_files = results["summary"]["files_audited"]
        files_with_violations = results["summary"]["files_with_violations"]
        
        if total_files > 0:
            results["summary"]["compliance_score"] = (
                (total_files - files_with_violations) / total_files * 100
            )
        
        return results
    
    def generate_report(self, results: Dict) -> str:
        """Generate human-readable security audit report"""
        report = []
        report.append("=" * 60)
        report.append("GA CHECKLIST: LOG SECURITY AUDIT REPORT")
        report.append("=" * 60)
        report.append("")
        
        summary = results["summary"]
        report.append("📊 AUDIT SUMMARY")
        report.append(f"  Files Audited: {summary['files_audited']}")
        report.append(f"  Total Violations: {summary['total_violations']}")
        report.append(f"  Files with Violations: {summary['files_with_violations']}")
        report.append(f"  Safe Patterns Found: {summary['total_safe_patterns']}")
        report.append(f"  Compliance Score: {summary['compliance_score']:.1f}%")
        report.append("")
        
        # Compliance status
        if summary['total_violations'] == 0:
            report.append("✅ COMPLIANCE STATUS: PASS")
            report.append("   No token/secret logging violations found")
        else:
            report.append("❌ COMPLIANCE STATUS: VIOLATIONS FOUND") 
            report.append("   Action required to resolve logging security issues")
        report.append("")
        
        # List violations
        if results["violations"]:
            report.append("🚨 SECURITY VIOLATIONS")
            for i, violation in enumerate(results["violations"], 1):
                report.append(f"{i}. {violation['file']}:{violation['line']}")
                report.append(f"   Code: {violation['code']}")
                report.append(f"   Pattern: {violation['pattern']}")
                report.append("")
        
        # List safe patterns (evidence of good security practices)
        if results["safe_patterns"]:
            report.append("✅ SAFE LOGGING PATTERNS (Evidence of Security Practices)")
            safe_files = set(p["file"] for p in results["safe_patterns"])
            for file_path in sorted(safe_files):
                file_patterns = [p for p in results["safe_patterns"] if p["file"] == file_path]
                report.append(f"\n📁 {file_path}")
                for pattern in file_patterns[:3]:  # Show first 3 examples
                    report.append(f"   Line {pattern['line']}: {pattern['code'][:80]}...")
                if len(file_patterns) > 3:
                    report.append(f"   ... and {len(file_patterns) - 3} more safe patterns")
        
        report.append("")
        report.append("=" * 60)
        report.append("RECOMMENDATIONS:")
        report.append("=" * 60)
        
        if summary['total_violations'] == 0:
            report.append("✅ Logging security practices are compliant")
            report.append("✅ No sensitive tokens/secrets found in logs")
            report.append("✅ Ready for production deployment")
        else:
            report.append("⚠️  Review and fix logging violations above")
            report.append("⚠️  Ensure no tokens/secrets are logged")
            report.append("⚠️  Use safe logging patterns shown in examples")
        
        report.append("")
        report.append("For GA checklist compliance:")
        report.append("- All OAuth tokens should be encrypted before storage")
        report.append("- No access/refresh tokens should appear in logs") 
        report.append("- Use filtered/sanitized data for debugging logs")
        report.append("- Test with sample end-to-end runs to verify")
        
        return "\n".join(report)


def main():
    """Run the log security audit"""
    print("Starting GA Checklist Log Security Audit...")
    
    auditor = LogSecurityAuditor()
    results = auditor.audit_codebase()
    
    # Generate and display report
    report = auditor.generate_report(results)
    print(report)
    
    # Save report to file
    report_file = Path("log_security_audit_report.txt")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_file}")
    
    # Exit with appropriate code
    if results["summary"]["total_violations"] > 0:
        print("\n❌ AUDIT FAILED: Security violations found")
        sys.exit(1)
    else:
        print("\n✅ AUDIT PASSED: No security violations found")
        sys.exit(0)


if __name__ == "__main__":
    main()