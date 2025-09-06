#!/usr/bin/env python3
"""
Comprehensive Secrets Audit Script
Scans for hard-coded secrets, credentials, and security violations in the codebase
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import json

class SecretsAuditor:
    """Comprehensive secrets and security auditor for codebase"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.violations = []
        
        # Patterns to detect various types of secrets
        self.patterns = {
            'hard_coded_passwords': [
                r'password\s*=\s*["\'][^"\']{8,}["\']',
                r'PASSWORD\s*=\s*["\'][^"\']{8,}["\']',
                r'Admin053103',  # Specific hard-coded admin password
            ],
            
            'database_credentials': [
                r'postgresql://[^:]+:[^@]+@[^/]+/[^"\'\s]+',
                r'mysql://[^:]+:[^@]+@[^/]+/[^"\'\s]+',
                r'mongodb://[^:]+:[^@]+@[^/]+/[^"\'\s]+',
            ],
            
            'api_keys': [
                r'sk-[a-zA-Z0-9]{48}',  # OpenAI API keys
                r'pk_live_[a-zA-Z0-9]{24}',  # Stripe live keys
                r'sk_live_[a-zA-Z0-9]{24}',  # Stripe secret keys
                r'rk_live_[a-zA-Z0-9]{24}',  # Stripe restricted keys
                r'AKIA[0-9A-Z]{16}',  # AWS access keys
                r'ghp_[a-zA-Z0-9]{36}',  # GitHub personal access tokens
            ],
            
            'jwt_secrets': [
                r'jwt.*secret.*["\'][^"\']{20,}["\']',
                r'secret.*key.*["\'][^"\']{20,}["\']',
                r'your.*secret.*key.*change.*this',
                r'your_super_secure_secret_key_change_this_in_production',
            ],
            
            'encryption_keys': [
                r'encryption.*key.*["\'][^"\']{16,}["\']',
                r'token.*encryption.*key.*["\'][^"\']{16,}["\']',
                r'your-secure-32-char-encryption-key-here',
            ],
            
            'oauth_secrets': [
                r'client_secret\s*=\s*["\'][^"\']{10,}["\']',
                r'consumer_secret\s*=\s*["\'][^"\']{10,}["\']',
                r'app_secret\s*=\s*["\'][^"\']{10,}["\']',
            ],
            
            'email_credentials': [
                r'smtp.*password\s*=\s*["\'][^"\']{8,}["\']',
                r'email.*password\s*=\s*["\'][^"\']{8,}["\']',
                r'mail.*password\s*=\s*["\'][^"\']{8,}["\']',
            ],
            
            'default_secrets': [
                r'changeme',
                r'password123',
                r'admin123',
                r'secret123',
                r'default.*password',
                r'temp.*password',
            ]
        }
        
        # Files and directories to exclude
        self.exclude_patterns = [
            '.git/',
            '__pycache__/',
            'node_modules/',
            '.venv/',
            'venv/',
            '.pytest_cache/',
            'scripts/secrets_audit.py',  # This script itself
            '.env.example',  # Example files are OK
            '.env.template',
        ]
        
        # File extensions to scan
        self.scan_extensions = [
            '.py', '.js', '.tsx', '.ts', '.json', '.yml', '.yaml',
            '.env', '.config', '.ini', '.conf', '.md', '.txt'
        ]
    
    def should_exclude_file(self, file_path: str) -> bool:
        """Check if file should be excluded from scanning"""
        for pattern in self.exclude_patterns:
            if pattern in file_path:
                return True
        return False
    
    def scan_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Scan a single file for secrets"""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                line_content = line.strip()
                
                # Skip empty lines and comments
                if not line_content or line_content.startswith('#'):
                    continue
                
                # Check each pattern category
                for category, patterns in self.patterns.items():
                    for pattern in patterns:
                        matches = re.findall(pattern, line, re.IGNORECASE)
                        if matches:
                            for match in matches:
                                violations.append({
                                    'file': str(file_path.relative_to(self.project_root)),
                                    'line': line_num,
                                    'category': category,
                                    'pattern': pattern,
                                    'match': match if len(match) < 100 else match[:100] + '...',
                                    'line_content': line_content[:200] if len(line_content) <= 200 else line_content[:200] + '...',
                                    'severity': self.get_severity(category)
                                })
        
        except (UnicodeDecodeError, PermissionError, OSError):
            # Skip files that can't be read
            pass
        
        return violations
    
    def get_severity(self, category: str) -> str:
        """Determine severity level based on category"""
        critical_categories = ['hard_coded_passwords', 'database_credentials', 'api_keys']
        high_categories = ['jwt_secrets', 'encryption_keys', 'oauth_secrets']
        medium_categories = ['email_credentials', 'default_secrets']
        
        if category in critical_categories:
            return 'CRITICAL'
        elif category in high_categories:
            return 'HIGH'
        elif category in medium_categories:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def scan_project(self) -> Dict[str, Any]:
        """Scan entire project for secrets"""
        print(f"🔍 Scanning project: {self.project_root}")
        print(f"📁 Extensions: {', '.join(self.scan_extensions)}")
        print()
        
        total_files = 0
        scanned_files = 0
        
        # Scan all files
        for file_path in self.project_root.rglob('*'):
            if not file_path.is_file():
                continue
            
            total_files += 1
            
            # Check extension
            if file_path.suffix not in self.scan_extensions:
                continue
            
            # Check exclusions
            rel_path = str(file_path.relative_to(self.project_root))
            if self.should_exclude_file(rel_path):
                continue
            
            scanned_files += 1
            
            # Scan file
            file_violations = self.scan_file(file_path)
            self.violations.extend(file_violations)
        
        # Categorize and summarize results
        results = self.analyze_results()
        results['scan_stats'] = {
            'total_files': total_files,
            'scanned_files': scanned_files,
            'violations_found': len(self.violations)
        }
        
        return results
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze and categorize scan results"""
        if not self.violations:
            return {
                'status': 'CLEAN',
                'summary': 'No secrets or security violations detected',
                'violations': []
            }
        
        # Group by severity
        severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        category_counts = {}
        
        for violation in self.violations:
            severity = violation['severity']
            category = violation['category']
            
            severity_counts[severity] += 1
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Determine overall status
        if severity_counts['CRITICAL'] > 0:
            status = 'CRITICAL'
        elif severity_counts['HIGH'] > 0:
            status = 'HIGH_RISK'
        elif severity_counts['MEDIUM'] > 0:
            status = 'MEDIUM_RISK'
        else:
            status = 'LOW_RISK'
        
        return {
            'status': status,
            'severity_counts': severity_counts,
            'category_counts': category_counts,
            'violations': self.violations,
            'recommendations': self.get_recommendations()
        }
    
    def get_recommendations(self) -> List[str]:
        """Generate security recommendations based on findings"""
        recommendations = []
        
        if any(v['category'] == 'hard_coded_passwords' for v in self.violations):
            recommendations.append("🚨 Remove all hard-coded passwords and use environment variables")
        
        if any(v['category'] == 'database_credentials' for v in self.violations):
            recommendations.append("🔒 Move database URLs to environment variables (DATABASE_URL)")
        
        if any(v['category'] == 'api_keys' for v in self.violations):
            recommendations.append("🔑 Store all API keys in environment variables, never in code")
        
        if any(v['category'] == 'jwt_secrets' for v in self.violations):
            recommendations.append("🛡️ Use strong, random JWT secrets from environment (SECRET_KEY)")
        
        if any(v['category'] == 'encryption_keys' for v in self.violations):
            recommendations.append("🔐 Generate strong encryption keys and store in environment")
        
        recommendations.extend([
            "✅ Use a secrets management service (AWS Secrets Manager, HashiCorp Vault)",
            "✅ Add secrets scanning to your CI/CD pipeline",
            "✅ Regularly rotate all secrets and API keys",
            "✅ Use .env files for local development (never commit them)",
            "✅ Review and audit secrets access regularly"
        ])
        
        return recommendations
    
    def print_report(self, results: Dict[str, Any]):
        """Print comprehensive security audit report"""
        print("🛡️  SECRETS AUDIT REPORT")
        print("=" * 60)
        print()
        
        # Overall status
        status = results['status']
        status_emoji = {
            'CLEAN': '✅',
            'LOW_RISK': '🟡',
            'MEDIUM_RISK': '🟠',
            'HIGH_RISK': '🔴',
            'CRITICAL': '🚨'
        }
        
        print(f"{status_emoji.get(status, '❓')} Overall Status: {status}")
        print()
        
        # Scan statistics
        stats = results.get('scan_stats', {})
        print(f"📊 Scan Statistics:")
        print(f"   Total files: {stats.get('total_files', 0)}")
        print(f"   Scanned files: {stats.get('scanned_files', 0)}")
        print(f"   Violations found: {stats.get('violations_found', 0)}")
        print()
        
        if results['status'] == 'CLEAN':
            print("🎉 Congratulations! No secrets or security violations detected.")
            return
        
        # Severity breakdown
        severity_counts = results.get('severity_counts', {})
        print("🔍 Severity Breakdown:")
        for severity, count in severity_counts.items():
            if count > 0:
                emoji = {'CRITICAL': '🚨', 'HIGH': '🔴', 'MEDIUM': '🟠', 'LOW': '🟡'}.get(severity, '❓')
                print(f"   {emoji} {severity}: {count}")
        print()
        
        # Category breakdown
        category_counts = results.get('category_counts', {})
        print("📋 Categories Found:")
        for category, count in category_counts.items():
            print(f"   • {category.replace('_', ' ').title()}: {count}")
        print()
        
        # Detailed violations
        violations = results.get('violations', [])
        if violations:
            print("🚨 DETAILED VIOLATIONS:")
            print("-" * 40)
            
            # Sort by severity and file
            sorted_violations = sorted(violations, 
                                     key=lambda x: (x['severity'] == 'CRITICAL', x['severity'] == 'HIGH', x['file']))
            
            current_file = None
            for violation in sorted_violations:
                if violation['file'] != current_file:
                    current_file = violation['file']
                    print(f"\n📁 {current_file}:")
                
                severity_emoji = {
                    'CRITICAL': '🚨', 'HIGH': '🔴', 
                    'MEDIUM': '🟠', 'LOW': '🟡'
                }.get(violation['severity'], '❓')
                
                print(f"   {severity_emoji} Line {violation['line']}: {violation['category'].replace('_', ' ').title()}")
                print(f"      Match: {violation['match']}")
                print()
        
        # Recommendations
        recommendations = results.get('recommendations', [])
        if recommendations:
            print("💡 SECURITY RECOMMENDATIONS:")
            print("-" * 40)
            for i, rec in enumerate(recommendations, 1):
                print(f"{i:2d}. {rec}")
            print()
        
        # Final status
        if results['status'] in ['CRITICAL', 'HIGH_RISK']:
            print("❌ ACTION REQUIRED: Critical security issues detected!")
            print("   Please address all violations before deployment.")
        elif results['status'] == 'MEDIUM_RISK':
            print("⚠️  ATTENTION NEEDED: Security issues detected.")
            print("   Consider addressing violations to improve security posture.")
        else:
            print("✅ No critical issues detected, but monitor continuously.")

def main():
    """Main execution function"""
    project_root = Path(__file__).parent.parent
    
    print("🔐 LILY AI SOCIAL MEDIA - SECRETS AUDIT")
    print("=" * 50)
    print()
    
    auditor = SecretsAuditor(str(project_root))
    results = auditor.scan_project()
    auditor.print_report(results)
    
    # Exit with error code if critical issues found
    if results['status'] in ['CRITICAL', 'HIGH_RISK']:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()