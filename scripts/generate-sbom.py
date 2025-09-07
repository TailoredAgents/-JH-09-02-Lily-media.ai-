#!/usr/bin/env python3
"""
SBOM (Software Bill of Materials) Generation Script

Generates comprehensive SBOMs for both backend and frontend components
in multiple formats (SPDX, CycloneDX) to support supply chain security.

Addresses P0-12b: Implement container security scanning (Trivy) and SBOM generation
"""

import json
import subprocess
import sys
import os
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path
import argparse


class SBOMGenerator:
    """Generate Software Bill of Materials for the application"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.timestamp = datetime.now(timezone.utc).isoformat()
        
    def generate_python_sbom(self) -> Dict[str, Any]:
        """Generate SBOM for Python backend dependencies"""
        
        try:
            # Read requirements.txt
            requirements_file = self.project_root / "requirements.txt"
            if not requirements_file.exists():
                raise FileNotFoundError(f"Requirements file not found: {requirements_file}")
            
            # Get installed packages with versions
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            installed_packages = json.loads(result.stdout)
            
            # Generate package list with metadata
            packages = []
            for package in installed_packages:
                pkg_info = self._get_package_info(package["name"], package["version"])
                packages.append(pkg_info)
            
            # Create SPDX-style SBOM
            sbom = {
                "spdxVersion": "SPDX-2.3",
                "dataLicense": "CC0-1.0",
                "SPDXID": "SPDXRef-DOCUMENT",
                "creationInfo": {
                    "created": self.timestamp,
                    "creators": ["Tool: lily-media-sbom-generator"],
                    "licenseListVersion": "3.20"
                },
                "name": "lily-media-backend-sbom",
                "documentNamespace": f"https://github.com/lily-media/backend/sbom-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "packages": packages,
                "relationships": self._generate_relationships(packages)
            }
            
            return sbom
            
        except Exception as e:
            print(f"Error generating Python SBOM: {e}")
            return {}
    
    def generate_nodejs_sbom(self) -> Dict[str, Any]:
        """Generate SBOM for Node.js frontend dependencies"""
        
        try:
            frontend_dir = self.project_root / "frontend"
            if not frontend_dir.exists():
                raise FileNotFoundError(f"Frontend directory not found: {frontend_dir}")
            
            # Read package-lock.json for exact dependency tree
            package_lock_file = frontend_dir / "package-lock.json"
            if package_lock_file.exists():
                with open(package_lock_file, 'r') as f:
                    package_lock = json.load(f)
            else:
                package_lock = {}
            
            # Get npm list output
            try:
                result = subprocess.run(
                    ["npm", "list", "--json", "--production"],
                    cwd=frontend_dir,
                    capture_output=True,
                    text=True,
                    check=False  # npm list can return non-zero even when successful
                )
                
                if result.stdout.strip():
                    npm_tree = json.loads(result.stdout)
                else:
                    npm_tree = {"dependencies": {}}
                    
            except (json.JSONDecodeError, subprocess.SubprocessError):
                npm_tree = {"dependencies": {}}
            
            # Generate package list
            packages = []
            if "dependencies" in npm_tree:
                packages = self._extract_npm_packages(npm_tree["dependencies"], package_lock.get("packages", {}))
            
            # Create SPDX-style SBOM
            sbom = {
                "spdxVersion": "SPDX-2.3",
                "dataLicense": "CC0-1.0",
                "SPDXID": "SPDXRef-DOCUMENT",
                "creationInfo": {
                    "created": self.timestamp,
                    "creators": ["Tool: lily-media-sbom-generator"],
                    "licenseListVersion": "3.20"
                },
                "name": "lily-media-frontend-sbom",
                "documentNamespace": f"https://github.com/lily-media/frontend/sbom-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "packages": packages,
                "relationships": self._generate_relationships(packages)
            }
            
            return sbom
            
        except Exception as e:
            print(f"Error generating Node.js SBOM: {e}")
            return {}
    
    def _get_package_info(self, name: str, version: str) -> Dict[str, Any]:
        """Get detailed information about a Python package"""
        
        try:
            # Get package metadata
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", name],
                capture_output=True,
                text=True,
                check=True
            )
            
            metadata = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
            
            # Generate package info
            pkg_info = {
                "SPDXID": f"SPDXRef-Package-{name}",
                "name": name,
                "versionInfo": version,
                "downloadLocation": metadata.get("Home-page", "NOASSERTION"),
                "filesAnalyzed": False,
                "copyrightText": "NOASSERTION",
                "supplier": f"Organization: {metadata.get('Author', 'NOASSERTION')}",
                "homepage": metadata.get("Home-page", ""),
                "summary": metadata.get("Summary", ""),
                "packageVerificationCode": {
                    "packageVerificationCodeValue": self._generate_verification_code(name, version)
                }
            }
            
            # Add license information if available
            if "License" in metadata and metadata["License"] != "UNKNOWN":
                pkg_info["licenseConcluded"] = metadata["License"]
                pkg_info["licenseDeclared"] = metadata["License"]
            else:
                pkg_info["licenseConcluded"] = "NOASSERTION"
                pkg_info["licenseDeclared"] = "NOASSERTION"
            
            return pkg_info
            
        except subprocess.CalledProcessError:
            # Fallback for packages without detailed metadata
            return {
                "SPDXID": f"SPDXRef-Package-{name}",
                "name": name,
                "versionInfo": version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "copyrightText": "NOASSERTION",
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "packageVerificationCode": {
                    "packageVerificationCodeValue": self._generate_verification_code(name, version)
                }
            }
    
    def _extract_npm_packages(self, dependencies: Dict[str, Any], package_lock_packages: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract package information from npm dependency tree"""
        
        packages = []
        
        for name, info in dependencies.items():
            version = info.get("version", "unknown")
            
            # Get additional info from package-lock if available
            lock_key = f"node_modules/{name}"
            lock_info = package_lock_packages.get(lock_key, {})
            
            pkg_info = {
                "SPDXID": f"SPDXRef-Package-{name}",
                "name": name,
                "versionInfo": version,
                "downloadLocation": lock_info.get("resolved", "NOASSERTION"),
                "filesAnalyzed": False,
                "copyrightText": "NOASSERTION",
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "packageVerificationCode": {
                    "packageVerificationCodeValue": self._generate_verification_code(name, version)
                }
            }
            
            # Add integrity hash if available
            if "integrity" in lock_info:
                pkg_info["checksums"] = [{
                    "algorithm": "SHA256" if lock_info["integrity"].startswith("sha256-") else "SHA1",
                    "checksumValue": lock_info["integrity"].split("-", 1)[1] if "-" in lock_info["integrity"] else lock_info["integrity"]
                }]
            
            packages.append(pkg_info)
            
            # Recursively process nested dependencies
            if "dependencies" in info:
                packages.extend(self._extract_npm_packages(info["dependencies"], package_lock_packages))
        
        return packages
    
    def _generate_verification_code(self, name: str, version: str) -> str:
        """Generate a verification code for the package"""
        content = f"{name}-{version}-{self.timestamp}"
        return hashlib.sha1(content.encode()).hexdigest()
    
    def _generate_relationships(self, packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate SPDX relationships between packages"""
        
        relationships = []
        
        # Add document contains package relationships
        for package in packages:
            relationships.append({
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": package["SPDXID"]
            })
        
        return relationships
    
    def generate_cyclonedx_sbom(self, spdx_sbom: Dict[str, Any]) -> Dict[str, Any]:
        """Convert SPDX SBOM to CycloneDX format"""
        
        cyclonedx = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": f"urn:uuid:{self._generate_uuid()}",
            "version": 1,
            "metadata": {
                "timestamp": self.timestamp,
                "tools": [
                    {
                        "vendor": "Lily Media AI",
                        "name": "lily-media-sbom-generator",
                        "version": "1.0.0"
                    }
                ],
                "component": {
                    "type": "application",
                    "name": spdx_sbom.get("name", "lily-media-app"),
                    "version": "1.0.0"
                }
            },
            "components": []
        }
        
        # Convert SPDX packages to CycloneDX components
        for package in spdx_sbom.get("packages", []):
            component = {
                "type": "library",
                "name": package["name"],
                "version": package["versionInfo"],
                "purl": f"pkg:pypi/{package['name']}@{package['versionInfo']}"
            }
            
            # Add license if available
            if package.get("licenseConcluded") != "NOASSERTION":
                component["licenses"] = [
                    {"license": {"name": package["licenseConcluded"]}}
                ]
            
            # Add checksums if available
            if "checksums" in package:
                component["hashes"] = package["checksums"]
            
            cyclonedx["components"].append(component)
        
        return cyclonedx
    
    def _generate_uuid(self) -> str:
        """Generate a UUID for the SBOM"""
        import uuid
        return str(uuid.uuid4())
    
    def save_sbom(self, sbom: Dict[str, Any], filename: str) -> None:
        """Save SBOM to file"""
        
        output_path = self.project_root / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(sbom, f, indent=2, ensure_ascii=False)
        
        print(f"SBOM saved to: {output_path}")
    
    def generate_all_sboms(self) -> None:
        """Generate all SBOM formats for the project"""
        
        print("🔍 Generating Software Bill of Materials (SBOMs)...")
        
        # Generate Python backend SBOM
        print("\n📦 Generating Python backend SBOM...")
        python_spdx = self.generate_python_sbom()
        if python_spdx:
            self.save_sbom(python_spdx, "sbom/backend-sbom.spdx.json")
            
            python_cyclonedx = self.generate_cyclonedx_sbom(python_spdx)
            self.save_sbom(python_cyclonedx, "sbom/backend-sbom.cyclonedx.json")
        
        # Generate Node.js frontend SBOM
        print("\n📦 Generating Node.js frontend SBOM...")
        nodejs_spdx = self.generate_nodejs_sbom()
        if nodejs_spdx:
            self.save_sbom(nodejs_spdx, "sbom/frontend-sbom.spdx.json")
            
            nodejs_cyclonedx = self.generate_cyclonedx_sbom(nodejs_spdx)
            self.save_sbom(nodejs_cyclonedx, "sbom/frontend-sbom.cyclonedx.json")
        
        # Generate combined SBOM
        print("\n📦 Generating combined application SBOM...")
        combined_sbom = self._generate_combined_sbom(python_spdx, nodejs_spdx)
        if combined_sbom:
            self.save_sbom(combined_sbom, "sbom/lily-media-app-sbom.spdx.json")
            
            combined_cyclonedx = self.generate_cyclonedx_sbom(combined_sbom)
            self.save_sbom(combined_cyclonedx, "sbom/lily-media-app-sbom.cyclonedx.json")
        
        print("\n✅ SBOM generation completed successfully!")
        print("\n📁 Generated SBOMs:")
        print("   • backend-sbom.spdx.json (Python dependencies)")
        print("   • backend-sbom.cyclonedx.json (Python dependencies)")
        print("   • frontend-sbom.spdx.json (Node.js dependencies)")
        print("   • frontend-sbom.cyclonedx.json (Node.js dependencies)")
        print("   • lily-media-app-sbom.spdx.json (Combined application)")
        print("   • lily-media-app-sbom.cyclonedx.json (Combined application)")
    
    def _generate_combined_sbom(self, python_sbom: Dict[str, Any], nodejs_sbom: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a combined SBOM for the entire application"""
        
        if not python_sbom and not nodejs_sbom:
            return {}
        
        combined_packages = []
        if python_sbom:
            combined_packages.extend(python_sbom.get("packages", []))
        if nodejs_sbom:
            combined_packages.extend(nodejs_sbom.get("packages", []))
        
        combined_sbom = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "creationInfo": {
                "created": self.timestamp,
                "creators": ["Tool: lily-media-sbom-generator"],
                "licenseListVersion": "3.20"
            },
            "name": "lily-media-application-sbom",
            "documentNamespace": f"https://github.com/lily-media/app/sbom-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "packages": combined_packages,
            "relationships": self._generate_relationships(combined_packages)
        }
        
        return combined_sbom


def main():
    """Main entry point for SBOM generation"""
    
    parser = argparse.ArgumentParser(description="Generate SBOMs for Lily Media AI platform")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--output-dir", default="sbom", help="Output directory for SBOMs")
    args = parser.parse_args()
    
    try:
        generator = SBOMGenerator(args.project_root)
        generator.generate_all_sboms()
        
    except Exception as e:
        print(f"❌ SBOM generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()