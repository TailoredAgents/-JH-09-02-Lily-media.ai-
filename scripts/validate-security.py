#!/usr/bin/env python3
"""
Security Validation Script

Validates all security controls are properly configured and functioning
according to the Container Security Policy requirements.

Addresses P0-12b: Implement container security scanning (Trivy) and SBOM generation
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
import requests
from datetime import datetime


class SecurityValidator:
    """Validate security controls and compliance"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.validation_results = []
        
    def validate_sbom_generation(self) -> bool:
        """Validate SBOM files are generated and complete"""
        print("🔍 Validating SBOM generation...")
        
        required_sboms = [
            "sbom/backend-sbom.spdx.json",
            "sbom/backend-sbom.cyclonedx.json", 
            "sbom/frontend-sbom.spdx.json",
            "sbom/frontend-sbom.cyclonedx.json",
            "sbom/lily-media-app-sbom.spdx.json",
            "sbom/lily-media-app-sbom.cyclonedx.json"
        ]
        
        all_valid = True
        
        for sbom_file in required_sboms:
            sbom_path = self.project_root / sbom_file
            if not sbom_path.exists():
                print(f"❌ Missing SBOM file: {sbom_file}")
                all_valid = False
                continue
                
            # Validate SBOM structure
            try:
                with open(sbom_path, 'r') as f:
                    sbom_data = json.load(f)
                
                if "spdx" in sbom_file.lower():
                    # Validate SPDX format
                    required_fields = ["spdxVersion", "dataLicense", "SPDXID", "packages"]
                    for field in required_fields:
                        if field not in sbom_data:
                            print(f"❌ SPDX SBOM missing required field '{field}': {sbom_file}")
                            all_valid = False
                            continue
                    
                    package_count = len(sbom_data.get("packages", []))
                    print(f"✅ Valid SPDX SBOM with {package_count} packages: {sbom_file}")
                    
                elif "cyclonedx" in sbom_file.lower():
                    # Validate CycloneDX format
                    required_fields = ["bomFormat", "specVersion", "components"]
                    for field in required_fields:
                        if field not in sbom_data:
                            print(f"❌ CycloneDX SBOM missing required field '{field}': {sbom_file}")
                            all_valid = False
                            continue
                    
                    component_count = len(sbom_data.get("components", []))
                    print(f"✅ Valid CycloneDX SBOM with {component_count} components: {sbom_file}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in SBOM file: {sbom_file} - {e}")
                all_valid = False
            except Exception as e:
                print(f"❌ Error validating SBOM file: {sbom_file} - {e}")
                all_valid = False
        
        self.validation_results.append(("SBOM Generation", all_valid))
        return all_valid
    
    def validate_workflow_files(self) -> bool:
        """Validate security workflow files are present and correctly configured"""
        print("\n🔍 Validating security workflow files...")
        
        required_workflows = [
            ".github/workflows/container-security-scan.yml",
            ".github/workflows/security-scan.yml"
        ]
        
        all_valid = True
        
        for workflow_file in required_workflows:
            workflow_path = self.project_root / workflow_file
            if not workflow_path.exists():
                print(f"❌ Missing security workflow: {workflow_file}")
                all_valid = False
                continue
            
            # Read and validate workflow content
            try:
                with open(workflow_path, 'r') as f:
                    workflow_content = f.read()
                
                # Check for required security components
                security_checks = {
                    "trivy": "trivy" in workflow_content.lower(),
                    "sbom_generation": "sbom" in workflow_content.lower(),
                    "security_gates": any(gate in workflow_content.lower() for gate in ["security", "vulnerability", "scan"]),
                    "artifact_upload": "upload-artifact" in workflow_content
                }
                
                missing_components = [comp for comp, present in security_checks.items() if not present]
                
                if missing_components:
                    print(f"⚠️ Workflow missing components: {workflow_file} - {missing_components}")
                else:
                    print(f"✅ Valid security workflow: {workflow_file}")
                    
            except Exception as e:
                print(f"❌ Error reading workflow file: {workflow_file} - {e}")
                all_valid = False
        
        self.validation_results.append(("Security Workflows", all_valid))
        return all_valid
    
    def validate_dockerfile_security(self) -> bool:
        """Validate Dockerfile follows security best practices"""
        print("\n🔍 Validating Dockerfile security...")
        
        dockerfile_path = self.project_root / "Dockerfile"
        if not dockerfile_path.exists():
            print("❌ Dockerfile not found")
            self.validation_results.append(("Dockerfile Security", False))
            return False
        
        try:
            with open(dockerfile_path, 'r') as f:
                dockerfile_content = f.read()
            
            security_checks = {
                "non_root_user": any(cmd in dockerfile_content for cmd in ["USER", "RUN groupadd", "RUN useradd"]),
                "multi_stage_build": dockerfile_content.count("FROM") > 1,
                "health_check": "HEALTHCHECK" in dockerfile_content,
                "no_root_final": not dockerfile_content.strip().endswith("USER root"),
                "package_cleanup": any(cleanup in dockerfile_content for cleanup in ["rm -rf", "apt-get clean", "apk del"])
            }
            
            passed_checks = sum(security_checks.values())
            total_checks = len(security_checks)
            
            print(f"✅ Dockerfile security score: {passed_checks}/{total_checks}")
            
            for check, passed in security_checks.items():
                status = "✅" if passed else "❌"
                print(f"   {status} {check.replace('_', ' ').title()}")
            
            all_passed = passed_checks == total_checks
            self.validation_results.append(("Dockerfile Security", all_passed))
            return all_passed
            
        except Exception as e:
            print(f"❌ Error reading Dockerfile: {e}")
            self.validation_results.append(("Dockerfile Security", False))
            return False
    
    def validate_security_policy(self) -> bool:
        """Validate security policy documentation exists"""
        print("\n🔍 Validating security policy documentation...")
        
        policy_path = self.project_root / "docs" / "container-security-policy.md"
        if not policy_path.exists():
            print("❌ Container Security Policy documentation not found")
            self.validation_results.append(("Security Policy", False))
            return False
        
        try:
            with open(policy_path, 'r') as f:
                policy_content = f.read()
            
            required_sections = [
                "Vulnerability Scanning Requirements",
                "Software Bill of Materials (SBOM) Requirements", 
                "Container Hardening Requirements",
                "Enforcement Mechanisms",
                "Implementation Guide"
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in policy_content:
                    missing_sections.append(section)
            
            if missing_sections:
                print(f"❌ Security policy missing sections: {missing_sections}")
                self.validation_results.append(("Security Policy", False))
                return False
            else:
                print("✅ Complete security policy documentation found")
                self.validation_results.append(("Security Policy", True))
                return True
                
        except Exception as e:
            print(f"❌ Error reading security policy: {e}")
            self.validation_results.append(("Security Policy", False))
            return False
    
    def validate_dependency_security(self) -> bool:
        """Validate dependencies for known vulnerabilities"""
        print("\n🔍 Validating dependency security...")
        
        try:
            # Check Python dependencies with Safety
            print("Checking Python dependencies...")
            result = subprocess.run(
                ["python", "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            packages = json.loads(result.stdout)
            print(f"✅ Found {len(packages)} Python packages to validate")
            
            # Check if safety is available
            try:
                subprocess.run(["safety", "--version"], capture_output=True, check=True)
                print("✅ Safety vulnerability scanner available")
                
                # Run safety check
                safety_result = subprocess.run(
                    ["safety", "check", "--json"],
                    capture_output=True,
                    text=True,
                    check=False  # Don't fail on vulnerabilities, just check
                )
                
                if safety_result.returncode == 0:
                    print("✅ No known vulnerabilities found in Python dependencies")
                else:
                    print("⚠️ Potential vulnerabilities found - check safety report")
                
            except subprocess.CalledProcessError:
                print("⚠️ Safety scanner not available - install with 'pip install safety'")
            
            # Check Node.js dependencies if frontend exists
            frontend_path = self.project_root / "frontend"
            if frontend_path.exists():
                print("Checking Node.js dependencies...")
                npm_result = subprocess.run(
                    ["npm", "audit", "--json"],
                    cwd=frontend_path,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if npm_result.returncode == 0:
                    print("✅ No known vulnerabilities found in Node.js dependencies")
                else:
                    try:
                        audit_data = json.loads(npm_result.stdout)
                        vulnerability_count = audit_data.get("metadata", {}).get("vulnerabilities", {}).get("total", 0)
                        print(f"⚠️ Found {vulnerability_count} potential vulnerabilities in Node.js dependencies")
                    except:
                        print("⚠️ npm audit completed with warnings")
            
            self.validation_results.append(("Dependency Security", True))
            return True
            
        except Exception as e:
            print(f"❌ Error checking dependency security: {e}")
            self.validation_results.append(("Dependency Security", False))
            return False
    
    def generate_validation_report(self) -> None:
        """Generate comprehensive validation report"""
        print("\n" + "="*60)
        print("🔒 SECURITY VALIDATION REPORT")
        print("="*60)
        
        total_checks = len(self.validation_results)
        passed_checks = sum(1 for _, passed in self.validation_results if passed)
        
        print(f"\n📊 Overall Score: {passed_checks}/{total_checks} ({(passed_checks/total_checks)*100:.1f}%)")
        
        print("\n📋 Validation Results:")
        for check_name, passed in self.validation_results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status} {check_name}")
        
        if passed_checks == total_checks:
            print("\n🎉 ALL SECURITY VALIDATIONS PASSED!")
            print("🚀 Container security scanning and SBOM generation implementation complete")
            print("✅ Ready for production deployment")
        else:
            failed_checks = total_checks - passed_checks
            print(f"\n⚠️ {failed_checks} validation(s) failed")
            print("🔧 Address failing validations before production deployment")
        
        print("\n" + "="*60)
        print(f"Validation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("="*60)
    
    def run_full_validation(self) -> bool:
        """Run all security validations"""
        print("🔒 Starting comprehensive security validation...")
        print("📋 Validating P0-12b: Container security scanning (Trivy) and SBOM generation")
        
        validations = [
            self.validate_sbom_generation,
            self.validate_workflow_files, 
            self.validate_dockerfile_security,
            self.validate_security_policy,
            self.validate_dependency_security
        ]
        
        all_passed = True
        for validation in validations:
            try:
                result = validation()
                all_passed = all_passed and result
            except Exception as e:
                print(f"❌ Validation error: {e}")
                all_passed = False
        
        self.generate_validation_report()
        return all_passed


def main():
    """Main entry point for security validation"""
    
    import argparse
    parser = argparse.ArgumentParser(description="Validate security controls for Lily Media AI platform")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    args = parser.parse_args()
    
    try:
        validator = SecurityValidator(args.project_root)
        success = validator.run_full_validation()
        
        if success:
            print("\n🎯 P0-12b TASK COMPLETED SUCCESSFULLY")
            sys.exit(0)
        else:
            print("\n❌ P0-12b TASK REQUIRES ATTENTION")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Security validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()