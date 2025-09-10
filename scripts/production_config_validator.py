#!/usr/bin/env python3
"""
Production Configuration Validator
P1-3a: Ensure production-ready configuration

Validates that all production configurations are properly set and secure.
"""

import os
import logging
import json
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConfigIssue:
    """Configuration validation issue"""
    config_name: str
    current_value: str
    issue_type: str
    severity: str
    recommendation: str

class ProductionConfigValidator:
    """Validates production configuration settings"""
    
    def __init__(self):
        self.issues: List[ConfigIssue] = []
        
        # Required production environment variables
        self.required_configs = [
            "DATABASE_URL",
            "REDIS_URL", 
            "SECRET_KEY",
            "CORS_ORIGINS",
            "ALLOWED_HOSTS",
            "ENVIRONMENT"
        ]
        
        # Security-critical configurations
        self.security_configs = {
            "ENVIRONMENT": ("production", "Must be 'production' in prod environment"),
            "DEBUG": ("false", "Debug mode must be disabled"),
            "SSL_REQUIRED": ("true", "SSL should be required"),
            "SECURE_COOKIES": ("true", "Cookies should be secure"),
            "CSRF_PROTECTION": ("true", "CSRF protection should be enabled"),
        }
        
        # Insecure values that should not be used
        self.insecure_values = [
            "*",  # Wildcard CORS
            "localhost",  # Should not be in production CORS
            "127.0.0.1",  # Should not be in production CORS
            "debug",  # Debug-related values
            "test",   # Test-related values
            "dev",    # Development-related values
        ]
    
    def validate_environment_variables(self) -> List[ConfigIssue]:
        """Validate environment variables"""
        issues = []
        
        # Check required variables exist
        for var_name in self.required_configs:
            value = os.getenv(var_name)
            if not value:
                issues.append(ConfigIssue(
                    config_name=var_name,
                    current_value="<missing>",
                    issue_type="missing_required_config",
                    severity="CRITICAL",
                    recommendation=f"Set {var_name} environment variable"
                ))
        
        # Check security configurations
        for var_name, (expected_value, description) in self.security_configs.items():
            value = os.getenv(var_name, "").lower()
            if value != expected_value.lower():
                issues.append(ConfigIssue(
                    config_name=var_name,
                    current_value=value or "<not set>",
                    issue_type="insecure_config",
                    severity="HIGH",
                    recommendation=f"Set {var_name}={expected_value}. {description}"
                ))
        
        # Check for insecure CORS origins
        cors_origins = os.getenv("CORS_ORIGINS", "")
        if cors_origins:
            for insecure_val in self.insecure_values:
                if insecure_val in cors_origins:
                    issues.append(ConfigIssue(
                        config_name="CORS_ORIGINS",
                        current_value=cors_origins,
                        issue_type="insecure_cors",
                        severity="CRITICAL",
                        recommendation=f"Remove '{insecure_val}' from CORS_ORIGINS. Use specific domains only."
                    ))
        
        return issues
    
    def validate_application_config(self) -> List[ConfigIssue]:
        """Validate application configuration"""
        issues = []
        
        try:
            from backend.core.config import get_settings
            settings = get_settings()
            
            # Check environment setting
            if hasattr(settings, 'environment'):
                if settings.environment.lower() != "production":
                    issues.append(ConfigIssue(
                        config_name="app.environment",
                        current_value=settings.environment,
                        issue_type="wrong_environment",
                        severity="CRITICAL", 
                        recommendation="Set environment to 'production'"
                    ))
            
            # Check debug mode
            if hasattr(settings, 'debug'):
                if settings.debug:
                    issues.append(ConfigIssue(
                        config_name="app.debug",
                        current_value=str(settings.debug),
                        issue_type="debug_enabled",
                        severity="HIGH",
                        recommendation="Disable debug mode in production"
                    ))
            
            # Check CORS settings
            if hasattr(settings, 'cors_origins'):
                if "*" in str(settings.cors_origins):
                    issues.append(ConfigIssue(
                        config_name="app.cors_origins",
                        current_value=str(settings.cors_origins),
                        issue_type="wildcard_cors",
                        severity="CRITICAL",
                        recommendation="Replace wildcard CORS with specific domains"
                    ))
        
        except Exception as e:
            logger.warning(f"Could not validate application config: {e}")
            issues.append(ConfigIssue(
                config_name="app_config",
                current_value="<error>",
                issue_type="config_load_error",
                severity="MEDIUM",
                recommendation=f"Fix application config loading: {e}"
            ))
        
        return issues
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete production config validation"""
        logger.info("Validating production configuration...")
        
        # Validate environment variables
        env_issues = self.validate_environment_variables()
        
        # Validate application config
        app_issues = self.validate_application_config()
        
        all_issues = env_issues + app_issues
        
        # Categorize by severity
        critical_issues = [i for i in all_issues if i.severity == "CRITICAL"]
        high_issues = [i for i in all_issues if i.severity == "HIGH"] 
        medium_issues = [i for i in all_issues if i.severity == "MEDIUM"]
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "environment": os.getenv("ENVIRONMENT", "unknown"),
            "total_issues": len(all_issues),
            "critical_issues": len(critical_issues),
            "high_issues": len(high_issues),
            "medium_issues": len(medium_issues),
            "issues": {
                "critical": [self._issue_to_dict(i) for i in critical_issues],
                "high": [self._issue_to_dict(i) for i in high_issues],
                "medium": [self._issue_to_dict(i) for i in medium_issues]
            },
            "production_ready": len(critical_issues) == 0,
            "recommendations": self._generate_recommendations(critical_issues, high_issues)
        }
        
        return results
    
    def _issue_to_dict(self, issue: ConfigIssue) -> Dict[str, Any]:
        """Convert issue to dictionary"""
        return {
            "config_name": issue.config_name,
            "current_value": issue.current_value,
            "issue_type": issue.issue_type,
            "severity": issue.severity,
            "recommendation": issue.recommendation
        }
    
    def _generate_recommendations(self, critical: List[ConfigIssue], high: List[ConfigIssue]) -> List[str]:
        """Generate remediation recommendations"""
        recommendations = []
        
        if critical:
            recommendations.append("🚨 CRITICAL: Fix all critical configuration issues before deploying to production")
            
        if high:
            recommendations.append("⚠️ HIGH: Review and fix high-priority security configurations")
        
        # Specific recommendations
        recommendations.extend([
            "1. Set ENVIRONMENT=production in deployment environment",
            "2. Configure CORS_ORIGINS with specific domains only",
            "3. Set DEBUG=false and disable all debug features",
            "4. Configure SSL_REQUIRED=true for HTTPS enforcement",
            "5. Set SECURE_COOKIES=true for cookie security",
            "6. Review all environment variables for production values"
        ])
        
        return recommendations

def main():
    """Main validation function"""
    validator = ProductionConfigValidator()
    results = validator.run_validation()
    
    # Save results
    output_file = "production_config_validation.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("=" * 80)
    print("🔧 PRODUCTION CONFIGURATION VALIDATION")
    print("=" * 80)
    
    print(f"🌍 Environment: {results['environment']}")
    print(f"🚨 Critical Issues: {results['critical_issues']}")
    print(f"⚠️  High Issues: {results['high_issues']}")
    print(f"📋 Medium Issues: {results['medium_issues']}")
    print(f"📊 Total Issues: {results['total_issues']}")
    print(f"✅ Production Ready: {results['production_ready']}")
    print()
    
    # Show critical issues
    if results['critical_issues'] > 0:
        print("🚨 CRITICAL CONFIGURATION ISSUES:")
        for issue in results['issues']['critical']:
            print(f"   {issue['config_name']}: {issue['current_value']}")
            print(f"      Issue: {issue['issue_type']}")
            print(f"      Fix: {issue['recommendation']}")
        print()
    
    # Show high priority issues
    if results['high_issues'] > 0:
        print("⚠️ HIGH PRIORITY ISSUES:")
        for issue in results['issues']['high']:
            print(f"   {issue['config_name']}: {issue['current_value']} - {issue['recommendation']}")
        print()
    
    print("📋 RECOMMENDATIONS:")
    for i, rec in enumerate(results['recommendations'], 1):
        print(f"   {i}. {rec}")
    
    print(f"\n📄 Detailed report saved to: {output_file}")
    
    # Return status based on results
    if results['critical_issues'] > 0:
        print("\n❌ CONFIGURATION VALIDATION FAILED - Critical issues must be fixed")
        return 1
    elif results['high_issues'] > 0:
        print("\n⚠️  CONFIGURATION VALIDATION WARNINGS - Review recommended")
        return 1
    else:
        print("\n✅ CONFIGURATION VALIDATION PASSED - Ready for production")
        return 0

if __name__ == "__main__":
    exit(main())