#!/usr/bin/env python3
"""
OpenAPI Schema Management Tool

Automatically generates, validates, and updates OpenAPI schema documentation
to ensure API documentation stays current with implementation.

Addresses P2-2a: Keep OpenAPI schema current
"""
import json
import sys
import os
import argparse
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, asdict
import hashlib
import importlib.util

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

@dataclass
class SchemaValidationResult:
    """Result of OpenAPI schema validation"""
    is_valid: bool
    warnings: List[str]
    errors: List[str]
    missing_endpoints: List[str]
    undocumented_endpoints: List[str]
    schema_hash: str
    timestamp: str

class OpenAPISchemaManager:
    """Manages OpenAPI schema generation and validation"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.schema_file = self.project_root / "docs" / "openapi.json"
        self.schema_history_dir = self.project_root / "docs" / "schema-history"
        self.backend_path = self.project_root / "backend"
        
        # Create directories if they don't exist
        self.schema_file.parent.mkdir(parents=True, exist_ok=True)
        self.schema_history_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_openapi_schema(self) -> Dict[str, Any]:
        """Generate OpenAPI schema from current FastAPI application"""
        
        try:
            # Import the FastAPI app
            sys.path.insert(0, str(self.project_root))
            from app import app
            
            # Import enhanced OpenAPI if available
            try:
                from backend.docs.openapi_enhanced import setup_enhanced_openapi
                setup_enhanced_openapi(app)
                print("✅ Using enhanced OpenAPI documentation")
            except ImportError:
                print("⚠️ Enhanced OpenAPI not available, using basic documentation")
            
            # Generate schema
            schema = app.openapi()
            
            # Add metadata
            schema["info"]["x-generated-at"] = datetime.now(timezone.utc).isoformat()
            schema["info"]["x-generator"] = "lily-media-openapi-manager"
            schema["info"]["x-schema-version"] = self._calculate_schema_hash(schema)
            
            return schema
            
        except Exception as e:
            print(f"❌ Failed to generate OpenAPI schema: {e}")
            raise
    
    def save_schema(self, schema: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """Save OpenAPI schema to file with backup"""
        
        if filename is None:
            filename = self.schema_file
        else:
            filename = Path(filename)
        
        # Create backup if file exists
        if filename.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.schema_history_dir / f"openapi_backup_{timestamp}.json"
            
            with open(filename, 'r') as f:
                old_schema = json.load(f)
            
            with open(backup_file, 'w') as f:
                json.dump(old_schema, f, indent=2, ensure_ascii=False)
            
            print(f"📁 Created backup: {backup_file}")
        
        # Save new schema
        with open(filename, 'w') as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved OpenAPI schema: {filename}")
        return filename
    
    def validate_schema(self, schema: Dict[str, Any]) -> SchemaValidationResult:
        """Validate OpenAPI schema for completeness and accuracy"""
        
        warnings = []
        errors = []
        missing_endpoints = []
        undocumented_endpoints = []
        
        # Extract documented endpoints
        documented_paths = set(schema.get("paths", {}).keys())
        
        # Get actual endpoints from FastAPI app
        try:
            sys.path.insert(0, str(self.project_root))
            from app import app
            
            actual_paths = set()
            for route in app.routes:
                if hasattr(route, 'path') and hasattr(route, 'methods'):
                    # Skip static files and internal routes
                    if not route.path.startswith('/static') and not route.path.startswith('/{'):
                        actual_paths.add(route.path)
            
            # Find missing and undocumented endpoints
            missing_endpoints = list(actual_paths - documented_paths)
            undocumented_endpoints = list(documented_paths - actual_paths)
            
        except Exception as e:
            errors.append(f"Failed to extract actual endpoints: {e}")
        
        # Validate schema structure
        required_fields = ["openapi", "info", "paths"]
        for field in required_fields:
            if field not in schema:
                errors.append(f"Missing required field: {field}")
        
        # Validate info section
        if "info" in schema:
            info_required = ["title", "version"]
            for field in info_required:
                if field not in schema["info"]:
                    errors.append(f"Missing required info field: {field}")
        
        # Validate paths
        if "paths" in schema:
            for path, methods in schema["paths"].items():
                if not isinstance(methods, dict):
                    errors.append(f"Invalid path structure: {path}")
                    continue
                
                for method, details in methods.items():
                    if not isinstance(details, dict):
                        continue
                    
                    # Check for required response codes
                    if "responses" not in details:
                        warnings.append(f"Missing responses for {method.upper()} {path}")
                    elif "200" not in details["responses"] and "201" not in details["responses"]:
                        warnings.append(f"No success response defined for {method.upper()} {path}")
                    
                    # Check for request body documentation in POST/PUT/PATCH
                    if method.lower() in ["post", "put", "patch"]:
                        if "requestBody" not in details:
                            warnings.append(f"Missing request body documentation for {method.upper()} {path}")
                    
                    # Check for parameter documentation
                    if "parameters" in details:
                        for param in details["parameters"]:
                            if "description" not in param:
                                warnings.append(f"Missing description for parameter in {method.upper()} {path}")
        
        # Check for security definitions
        if "components" in schema and "securitySchemes" in schema["components"]:
            if not schema["components"]["securitySchemes"]:
                warnings.append("No security schemes defined")
        else:
            warnings.append("Missing security scheme definitions")
        
        # Validate tags
        if "paths" in schema:
            used_tags = set()
            for methods in schema["paths"].values():
                for details in methods.values():
                    if isinstance(details, dict) and "tags" in details:
                        used_tags.update(details["tags"])
            
            defined_tags = set()
            if "tags" in schema:
                defined_tags = {tag["name"] for tag in schema["tags"]}
            
            undefined_tags = used_tags - defined_tags
            if undefined_tags:
                warnings.append(f"Used but undefined tags: {', '.join(undefined_tags)}")
        
        # Calculate schema hash
        schema_hash = self._calculate_schema_hash(schema)
        
        is_valid = len(errors) == 0
        
        return SchemaValidationResult(
            is_valid=is_valid,
            warnings=warnings,
            errors=errors,
            missing_endpoints=missing_endpoints,
            undocumented_endpoints=undocumented_endpoints,
            schema_hash=schema_hash,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    def compare_schemas(self, old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two OpenAPI schemas and return differences"""
        
        changes = {
            "added_paths": [],
            "removed_paths": [], 
            "modified_paths": [],
            "version_changed": False,
            "breaking_changes": [],
            "summary": {}
        }
        
        # Compare paths
        old_paths = set(old_schema.get("paths", {}).keys())
        new_paths = set(new_schema.get("paths", {}).keys())
        
        changes["added_paths"] = list(new_paths - old_paths)
        changes["removed_paths"] = list(old_paths - new_paths)
        
        # Check for modified paths
        for path in old_paths.intersection(new_paths):
            old_path_spec = old_schema["paths"][path]
            new_path_spec = new_schema["paths"][path]
            
            if old_path_spec != new_path_spec:
                changes["modified_paths"].append(path)
                
                # Check for breaking changes
                old_methods = set(old_path_spec.keys())
                new_methods = set(new_path_spec.keys())
                
                removed_methods = old_methods - new_methods
                if removed_methods:
                    changes["breaking_changes"].append(f"Removed methods {removed_methods} from {path}")
        
        # Compare versions
        old_version = old_schema.get("info", {}).get("version")
        new_version = new_schema.get("info", {}).get("version")
        changes["version_changed"] = old_version != new_version
        
        # Generate summary
        changes["summary"] = {
            "total_changes": len(changes["added_paths"]) + len(changes["removed_paths"]) + len(changes["modified_paths"]),
            "new_endpoints": len(changes["added_paths"]),
            "removed_endpoints": len(changes["removed_paths"]),
            "modified_endpoints": len(changes["modified_paths"]),
            "breaking_changes": len(changes["breaking_changes"]),
            "version_update": changes["version_changed"]
        }
        
        return changes
    
    def _calculate_schema_hash(self, schema: Dict[str, Any]) -> str:
        """Calculate hash of schema for change detection"""
        # Remove volatile fields for hash calculation
        schema_copy = schema.copy()
        if "info" in schema_copy:
            schema_copy["info"] = {k: v for k, v in schema_copy["info"].items() 
                                 if not k.startswith("x-")}
        
        schema_str = json.dumps(schema_copy, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(schema_str.encode()).hexdigest()[:16]
    
    def load_existing_schema(self) -> Optional[Dict[str, Any]]:
        """Load existing OpenAPI schema if it exists"""
        
        if not self.schema_file.exists():
            return None
        
        try:
            with open(self.schema_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load existing schema: {e}")
            return None
    
    def generate_schema_report(self, validation_result: SchemaValidationResult, 
                             changes: Optional[Dict[str, Any]] = None) -> str:
        """Generate a comprehensive schema validation report"""
        
        report_lines = [
            "# OpenAPI Schema Validation Report",
            f"Generated: {validation_result.timestamp}",
            f"Schema Hash: {validation_result.schema_hash}",
            ""
        ]
        
        # Validation status
        if validation_result.is_valid:
            report_lines.extend([
                "## ✅ Schema Validation: PASSED",
                ""
            ])
        else:
            report_lines.extend([
                "## ❌ Schema Validation: FAILED",
                ""
            ])
        
        # Errors
        if validation_result.errors:
            report_lines.extend([
                "### 🚨 Errors",
                ""
            ])
            for error in validation_result.errors:
                report_lines.append(f"- {error}")
            report_lines.append("")
        
        # Warnings
        if validation_result.warnings:
            report_lines.extend([
                "### ⚠️ Warnings",
                ""
            ])
            for warning in validation_result.warnings:
                report_lines.append(f"- {warning}")
            report_lines.append("")
        
        # Missing endpoints
        if validation_result.missing_endpoints:
            report_lines.extend([
                "### 📋 Missing Documentation",
                "These endpoints exist in the code but are not documented:",
                ""
            ])
            for endpoint in validation_result.missing_endpoints:
                report_lines.append(f"- {endpoint}")
            report_lines.append("")
        
        # Undocumented endpoints
        if validation_result.undocumented_endpoints:
            report_lines.extend([
                "### 👻 Orphaned Documentation", 
                "These endpoints are documented but don't exist in the code:",
                ""
            ])
            for endpoint in validation_result.undocumented_endpoints:
                report_lines.append(f"- {endpoint}")
            report_lines.append("")
        
        # Changes if provided
        if changes and changes["summary"]["total_changes"] > 0:
            report_lines.extend([
                "### 🔄 Schema Changes",
                ""
            ])
            
            summary = changes["summary"]
            report_lines.append(f"**Total Changes:** {summary['total_changes']}")
            
            if changes["added_paths"]:
                report_lines.extend([
                    "",
                    "**Added Endpoints:**"
                ])
                for path in changes["added_paths"]:
                    report_lines.append(f"- ➕ {path}")
            
            if changes["removed_paths"]:
                report_lines.extend([
                    "",
                    "**Removed Endpoints:**"
                ])
                for path in changes["removed_paths"]:
                    report_lines.append(f"- ➖ {path}")
            
            if changes["modified_paths"]:
                report_lines.extend([
                    "",
                    "**Modified Endpoints:**"
                ])
                for path in changes["modified_paths"]:
                    report_lines.append(f"- 🔄 {path}")
            
            if changes["breaking_changes"]:
                report_lines.extend([
                    "",
                    "**⚠️ Breaking Changes:**"
                ])
                for change in changes["breaking_changes"]:
                    report_lines.append(f"- {change}")
            
            report_lines.append("")
        
        # Recommendations
        report_lines.extend([
            "### 📝 Recommendations",
            ""
        ])
        
        if validation_result.missing_endpoints:
            report_lines.append("- Add documentation for missing endpoints")
        
        if validation_result.undocumented_endpoints:
            report_lines.append("- Remove or update orphaned documentation")
        
        if validation_result.warnings:
            report_lines.append("- Address documentation warnings for better API usability")
        
        if not validation_result.warnings and not validation_result.errors:
            report_lines.append("- ✅ Schema is comprehensive and up-to-date")
        
        return "\n".join(report_lines)
    
    def update_schema(self, force: bool = False, validate_only: bool = False) -> SchemaValidationResult:
        """Main method to update OpenAPI schema"""
        
        print("🔄 Starting OpenAPI schema update...")
        
        # Load existing schema
        existing_schema = self.load_existing_schema()
        
        # Generate new schema
        print("📊 Generating OpenAPI schema from application...")
        new_schema = self.generate_openapi_schema()
        
        # Validate new schema
        print("🔍 Validating schema...")
        validation_result = self.validate_schema(new_schema)
        
        # Compare with existing schema
        changes = None
        if existing_schema:
            changes = self.compare_schemas(existing_schema, new_schema)
            
            if changes["summary"]["total_changes"] == 0 and not force:
                print("✅ Schema is already up-to-date")
                return validation_result
        
        # Generate report
        report = self.generate_schema_report(validation_result, changes)
        report_file = self.schema_file.parent / "schema-validation-report.md"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"📄 Generated validation report: {report_file}")
        
        if validate_only:
            print("🔍 Validation-only mode - schema not updated")
            return validation_result
        
        # Save new schema
        if not validation_result.is_valid and not force:
            print("❌ Schema validation failed - use --force to save anyway")
            return validation_result
        
        self.save_schema(new_schema)
        
        # Print summary
        if changes:
            summary = changes["summary"]
            print(f"📊 Schema updated: {summary['total_changes']} changes detected")
            if summary["breaking_changes"] > 0:
                print(f"⚠️ Warning: {summary['breaking_changes']} breaking changes detected")
        
        print("✅ OpenAPI schema update completed")
        return validation_result


def main():
    """Main entry point for OpenAPI schema management"""
    
    parser = argparse.ArgumentParser(
        description="OpenAPI Schema Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python openapi-schema-manager.py --update          # Update schema
  python openapi-schema-manager.py --validate        # Validate only
  python openapi-schema-manager.py --force           # Force update even if validation fails
  python openapi-schema-manager.py --project-root .. # Specify project root
        """
    )
    
    parser.add_argument("--project-root", default=".", 
                       help="Project root directory (default: current directory)")
    parser.add_argument("--update", action="store_true", 
                       help="Update OpenAPI schema")
    parser.add_argument("--validate", action="store_true", 
                       help="Validate schema without updating")
    parser.add_argument("--force", action="store_true", 
                       help="Force update even if validation fails")
    parser.add_argument("--output", help="Output file for generated schema")
    
    args = parser.parse_args()
    
    if not args.update and not args.validate:
        parser.print_help()
        sys.exit(1)
    
    try:
        manager = OpenAPISchemaManager(args.project_root)
        
        if args.validate:
            # Validate existing or generate new schema
            if manager.schema_file.exists():
                schema = manager.load_existing_schema()
            else:
                schema = manager.generate_openapi_schema()
            
            result = manager.validate_schema(schema)
            
            if result.is_valid:
                print("✅ Schema validation passed")
                sys.exit(0)
            else:
                print(f"❌ Schema validation failed: {len(result.errors)} errors")
                for error in result.errors[:5]:  # Show first 5 errors
                    print(f"  - {error}")
                sys.exit(1)
        
        elif args.update:
            result = manager.update_schema(
                force=args.force, 
                validate_only=False
            )
            
            if not result.is_valid and not args.force:
                sys.exit(1)
            
            sys.exit(0)
    
    except Exception as e:
        print(f"❌ OpenAPI schema management failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()