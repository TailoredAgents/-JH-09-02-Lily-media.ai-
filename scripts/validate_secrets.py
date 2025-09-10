#!/usr/bin/env python3
"""
Secrets Validation and Management Script

Validates that all required secrets are properly configured for production deployment.
Part of P0-2d: Comprehensive secrets management implementation.
"""

import os
import sys
import re
import secrets
import string
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

try:
    from backend.core.config import get_settings
    from backend.core.config import Settings
except ImportError as e:
    print(f"❌ Could not import settings: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SecretValidationResult:
    """Result of secret validation"""
    key: str
    is_valid: bool
    severity: str  # 'critical', 'high', 'medium', 'low'
    message: str
    recommendation: Optional[str] = None

@dataclass 
class SecurityIssue:
    """Security issue found in codebase"""
    file_path: str
    line_number: int
    issue_type: str
    content: str
    severity: str

class SecretsValidator:
    """Comprehensive secrets validation and management"""
    
    def __init__(self):
        self.settings = get_settings()
        self.results: List[SecretValidationResult] = []
        self.security_issues: List[SecurityIssue] = []
        self.project_root = project_root
        
        # Define critical secrets for production
        self.critical_secrets = {
            'SECRET_KEY': {
                'min_length': 32,
                'description': 'Application secret key for cryptographic operations',
                'env_var': 'SECRET_KEY'
            },
            'TOKEN_ENCRYPTION_KEY': {
                'min_length': 32,
                'max_length': 32,  # Exactly 32 characters
                'description': 'Key for encrypting OAuth tokens',
                'env_var': 'TOKEN_ENCRYPTION_KEY'
            },
            'JWT_SECRET': {
                'min_length': 32,
                'description': 'JWT token signing secret',
                'env_var': 'JWT_SECRET'
            },
            'DATABASE_URL': {
                'min_length': 20,
                'description': 'PostgreSQL database connection URL',
                'env_var': 'DATABASE_URL',
                'required_patterns': [r'postgresql://']
            },
            'OPENAI_API_KEY': {
                'min_length': 40,
                'description': 'OpenAI API key for AI services',
                'env_var': 'OPENAI_API_KEY',
                'required_patterns': [r'sk-proj-', r'sk-[a-zA-Z0-9]']
            }
        }
        
        # Optional but recommended secrets
        self.recommended_secrets = {
            'REDIS_URL': {
                'min_length': 10,
                'description': 'Redis URL for caching and rate limiting',
                'env_var': 'REDIS_URL'
            },
            'XAI_API_KEY': {
                'min_length': 20,
                'description': 'xAI API key for image generation',
                'env_var': 'XAI_API_KEY'
            }
        }
        
        # Dangerous default values that should never be used in production
        self.dangerous_defaults = [
            'your-secret-key-change-this-in-production',
            'change-this-in-production',
            'your-32-byte-encryption-key-change-this',
            'development-secret-key-not-for-production',
            'sk-proj-placeholder-key-for-development-testing-only',
            'your-api-key-here',
            'your-openai-api-key-here',
            'test-key',
            'dev-key',
            'placeholder'
        ]
    
    def validate_all_secrets(self) -> bool:
        """Validate all secrets and return True if all critical secrets are valid"""
        logger.info("🔍 Starting comprehensive secrets validation...")
        
        # 1. Validate critical secrets
        self._validate_critical_secrets()
        
        # 2. Validate recommended secrets  
        self._validate_recommended_secrets()
        
        # 3. Scan for hard-coded secrets in codebase
        self._scan_codebase_for_secrets()
        
        # 4. Check .gitignore coverage
        self._validate_gitignore_coverage()
        
        # 5. Generate report
        return self._generate_validation_report()
    
    def _validate_critical_secrets(self):
        """Validate all critical secrets required for production"""
        logger.info("🔒 Validating critical secrets...")
        
        for secret_name, config in self.critical_secrets.items():
            try:
                # Get secret value from settings
                secret_value = self._get_secret_value(secret_name)
                
                if not secret_value:
                    self.results.append(SecretValidationResult(
                        key=secret_name,
                        is_valid=False,
                        severity='critical',
                        message=f'{secret_name} is not set',
                        recommendation=f'Set environment variable {config["env_var"]}'
                    ))
                    continue
                
                # Check for dangerous defaults
                if secret_value in self.dangerous_defaults:
                    self.results.append(SecretValidationResult(
                        key=secret_name,
                        is_valid=False, 
                        severity='critical',
                        message=f'{secret_name} is using a dangerous default value',
                        recommendation=f'Generate a secure value for {config["env_var"]}'
                    ))
                    continue
                
                # Check minimum length
                min_length = config.get('min_length', 0)
                if len(secret_value) < min_length:
                    self.results.append(SecretValidationResult(
                        key=secret_name,
                        is_valid=False,
                        severity='high',
                        message=f'{secret_name} is too short (minimum {min_length} characters)',
                        recommendation=f'Generate a longer secure value for {config["env_var"]}'
                    ))
                    continue
                
                # Check maximum length (for encryption keys)
                max_length = config.get('max_length')
                if max_length and len(secret_value) != max_length:
                    self.results.append(SecretValidationResult(
                        key=secret_name,
                        is_valid=False,
                        severity='high',
                        message=f'{secret_name} must be exactly {max_length} characters',
                        recommendation=f'Generate a {max_length}-character key for {config["env_var"]}'
                    ))
                    continue
                
                # Check required patterns
                required_patterns = config.get('required_patterns', [])
                if required_patterns:
                    pattern_match = any(re.search(pattern, secret_value) for pattern in required_patterns)
                    if not pattern_match:
                        self.results.append(SecretValidationResult(
                            key=secret_name,
                            is_valid=False,
                            severity='high',
                            message=f'{secret_name} does not match expected format',
                            recommendation=f'Ensure {config["env_var"]} has the correct format'
                        ))
                        continue
                
                # Secret passed all checks
                self.results.append(SecretValidationResult(
                    key=secret_name,
                    is_valid=True,
                    severity='info',
                    message=f'{secret_name} is properly configured'
                ))
                
            except Exception as e:
                self.results.append(SecretValidationResult(
                    key=secret_name,
                    is_valid=False,
                    severity='critical',
                    message=f'Error validating {secret_name}: {str(e)}',
                    recommendation=f'Check {config["env_var"]} configuration'
                ))
    
    def _validate_recommended_secrets(self):
        """Validate recommended but optional secrets"""
        logger.info("📋 Validating recommended secrets...")
        
        for secret_name, config in self.recommended_secrets.items():
            try:
                secret_value = self._get_secret_value(secret_name)
                
                if not secret_value:
                    self.results.append(SecretValidationResult(
                        key=secret_name,
                        is_valid=True,  # Optional secrets don't fail validation
                        severity='medium',
                        message=f'{secret_name} is not set (optional)',
                        recommendation=f'Consider setting {config["env_var"]} for enhanced functionality'
                    ))
                    continue
                
                # Basic validation for optional secrets
                min_length = config.get('min_length', 0)
                if len(secret_value) < min_length:
                    self.results.append(SecretValidationResult(
                        key=secret_name,
                        is_valid=True,
                        severity='medium',
                        message=f'{secret_name} is too short (minimum {min_length} characters)',
                        recommendation=f'Use a longer secure value for {config["env_var"]}'
                    ))
                    continue
                
                # Secret is properly configured
                self.results.append(SecretValidationResult(
                    key=secret_name,
                    is_valid=True,
                    severity='info',
                    message=f'{secret_name} is properly configured'
                ))
                
            except Exception as e:
                self.results.append(SecretValidationResult(
                    key=secret_name,
                    is_valid=True,  # Don't fail on optional secrets
                    severity='low',
                    message=f'Could not validate {secret_name}: {str(e)}'
                ))
    
    def _get_secret_value(self, secret_name: str) -> Optional[str]:
        """Safely get secret value from settings"""
        try:
            # Handle different secret access patterns
            if secret_name == 'SECRET_KEY':
                return self.settings.get_secret_key()
            elif secret_name == 'TOKEN_ENCRYPTION_KEY':
                return self.settings.get_encryption_key() 
            elif secret_name == 'JWT_SECRET':
                return self.settings.get_jwt_secret()
            elif secret_name == 'DATABASE_URL':
                return self.settings.get_database_url()
            elif secret_name == 'OPENAI_API_KEY':
                return self.settings.get_openai_api_key()
            elif secret_name == 'REDIS_URL':
                return self.settings.redis_url
            elif secret_name == 'XAI_API_KEY':
                return self.settings.get_xai_api_key()
            else:
                # Generic environment variable access
                return os.getenv(secret_name, "")
        except Exception:
            return None
    
    def _scan_codebase_for_secrets(self):
        """Scan codebase for potential hard-coded secrets"""
        logger.info("🔍 Scanning codebase for hard-coded secrets...")
        
        # Patterns to detect potential secrets
        secret_patterns = [
            (r'(?i)(api[_-]?key|secret[_-]?key|password|token)\s*[=:]\s*["\'][^"\']{15,}["\']', 'hardcoded_secret'),
            (r'sk-[a-zA-Z0-9]{40,}', 'openai_api_key'),
            (r'xai-[a-zA-Z0-9]{40,}', 'xai_api_key'), 
            (r'postgres://[^/]+:[^@]+@[^/]+', 'database_url'),
            (r'redis://[^/]+:[^@]+@[^/]+', 'redis_url'),
        ]
        
        # Files to scan
        python_files = list(self.project_root.rglob("*.py"))
        config_files = list(self.project_root.rglob("*.yml")) + list(self.project_root.rglob("*.yaml"))
        js_files = list(self.project_root.rglob("*.js")) + list(self.project_root.rglob("*.ts"))
        
        all_files = python_files + config_files + js_files
        
        for file_path in all_files:
            # Skip certain directories
            if any(skip_dir in str(file_path) for skip_dir in [
                'node_modules', '.git', '__pycache__', 'dist', 'build',
                'docs/api', 'frontend/src/services/__tests__'  # Skip documentation and test files
            ]):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                for line_num, line in enumerate(content.split('\n'), 1):
                    for pattern, issue_type in secret_patterns:
                        matches = re.findall(pattern, line, re.IGNORECASE)
                        if matches:
                            # Skip obvious documentation examples
                            if any(doc_indicator in line.lower() for doc_indicator in [
                                'example', 'placeholder', 'your-', 'change-this',
                                'test-token', 'mock-', 'demo-', 'sample-'
                            ]):
                                continue
                            
                            self.security_issues.append(SecurityIssue(
                                file_path=str(file_path.relative_to(self.project_root)),
                                line_number=line_num,
                                issue_type=issue_type,
                                content=line.strip()[:100],  # Truncate long lines
                                severity='high' if issue_type in ['openai_api_key', 'database_url'] else 'medium'
                            ))
                            
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
    
    def _validate_gitignore_coverage(self):
        """Validate that .gitignore properly excludes secrets"""
        logger.info("📋 Validating .gitignore coverage...")
        
        gitignore_path = self.project_root / '.gitignore'
        if not gitignore_path.exists():
            self.results.append(SecretValidationResult(
                key='gitignore',
                is_valid=False,
                severity='critical',
                message='.gitignore file is missing',
                recommendation='Create .gitignore file to prevent committing secrets'
            ))
            return
        
        try:
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read().lower()
            
            # Check for essential patterns
            required_patterns = [
                '.env',
                '*.key',
                '*.pem',
                'secrets',
                'credentials',
                'api_keys'
            ]
            
            missing_patterns = []
            for pattern in required_patterns:
                if pattern not in gitignore_content:
                    missing_patterns.append(pattern)
            
            if missing_patterns:
                self.results.append(SecretValidationResult(
                    key='gitignore',
                    is_valid=False,
                    severity='high',
                    message=f'.gitignore missing patterns: {", ".join(missing_patterns)}',
                    recommendation='Add missing patterns to .gitignore'
                ))
            else:
                self.results.append(SecretValidationResult(
                    key='gitignore',
                    is_valid=True,
                    severity='info',
                    message='.gitignore properly configured'
                ))
                
        except Exception as e:
            self.results.append(SecretValidationResult(
                key='gitignore',
                is_valid=False,
                severity='medium',
                message=f'Could not validate .gitignore: {str(e)}'
            ))
    
    def _generate_validation_report(self) -> bool:
        """Generate comprehensive validation report"""
        logger.info("📊 Generating validation report...")
        
        print("\n" + "=" * 80)
        print("🔒 SECRETS VALIDATION REPORT")
        print("=" * 80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Environment: {self.settings.environment}")
        print()
        
        # Categorize results
        critical_failures = [r for r in self.results if not r.is_valid and r.severity == 'critical']
        high_issues = [r for r in self.results if (not r.is_valid and r.severity == 'high') or r.severity == 'high']
        medium_issues = [r for r in self.results if r.severity == 'medium']
        successes = [r for r in self.results if r.is_valid and r.severity == 'info']
        
        # Critical failures
        if critical_failures:
            print("🚨 CRITICAL FAILURES:")
            for result in critical_failures:
                print(f"   ❌ {result.key}: {result.message}")
                if result.recommendation:
                    print(f"      💡 {result.recommendation}")
            print()
        
        # High severity issues
        if high_issues:
            print("⚠️  HIGH PRIORITY ISSUES:")
            for result in high_issues:
                print(f"   ⚠️  {result.key}: {result.message}")
                if result.recommendation:
                    print(f"      💡 {result.recommendation}")
            print()
        
        # Medium priority issues
        if medium_issues:
            print("📋 RECOMMENDATIONS:")
            for result in medium_issues:
                print(f"   📋 {result.key}: {result.message}")
                if result.recommendation:
                    print(f"      💡 {result.recommendation}")
            print()
        
        # Security issues found in codebase
        if self.security_issues:
            print("🔍 POTENTIAL SECURITY ISSUES:")
            for issue in self.security_issues:
                severity_icon = "🚨" if issue.severity == 'high' else "⚠️"
                print(f"   {severity_icon} {issue.file_path}:{issue.line_number}")
                print(f"      Type: {issue.issue_type}")
                print(f"      Content: {issue.content}")
            print()
        
        # Successes
        if successes:
            print("✅ PROPERLY CONFIGURED:")
            for result in successes:
                print(f"   ✅ {result.key}: {result.message}")
            print()
        
        # Summary
        total_issues = len(critical_failures) + len(high_issues) + len(medium_issues)
        security_issues_count = len(self.security_issues)
        
        print("📊 SUMMARY:")
        print(f"   ✅ Properly configured: {len(successes)}")
        print(f"   ⚠️  Issues found: {total_issues}")
        print(f"   🔍 Security concerns: {security_issues_count}")
        
        # Overall status
        is_production_ready = len(critical_failures) == 0 and security_issues_count == 0
        
        print()
        if is_production_ready:
            print("🎉 PRODUCTION READY: All critical secrets properly configured!")
        else:
            print("❌ NOT PRODUCTION READY: Critical issues must be resolved!")
        
        print("=" * 80)
        
        return is_production_ready
    
    def generate_secure_keys(self):
        """Generate secure keys for production use"""
        print("\n🔐 SECURE KEY GENERATOR")
        print("=" * 50)
        print("Use these cryptographically secure keys for production:\n")
        
        print("# Core Security Keys")
        print(f"SECRET_KEY={secrets.token_urlsafe(64)}")
        print(f"JWT_SECRET={secrets.token_urlsafe(64)}")
        print(f"TOKEN_ENCRYPTION_KEY={''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))}")
        print()
        
        print("⚠️  IMPORTANT:")
        print("   1. Never commit these keys to version control")
        print("   2. Set them as environment variables in production")
        print("   3. Keep them secure and rotate regularly")
        print("   4. Each environment should have unique keys")
        print()

def main():
    """Main validation script"""
    print("🔒 Lily Media AI - Secrets Validation")
    print("=" * 50)
    
    validator = SecretsValidator()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'generate-keys':
            validator.generate_secure_keys()
            return
        elif command == 'scan-only':
            validator._scan_codebase_for_secrets()
            if validator.security_issues:
                print("\n🔍 Security issues found:")
                for issue in validator.security_issues:
                    print(f"   {issue.file_path}:{issue.line_number} - {issue.issue_type}")
            else:
                print("\n✅ No security issues found in codebase scan")
            return
    
    # Run full validation
    is_valid = validator.validate_all_secrets()
    
    # Exit with appropriate code
    sys.exit(0 if is_valid else 1)

if __name__ == '__main__':
    main()