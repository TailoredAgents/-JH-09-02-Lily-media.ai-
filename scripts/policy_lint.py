#!/usr/bin/env python3
"""
Content Policy Linter
Scans codebase for prohibited DALL-E references to prevent policy violations
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Prohibited patterns
PROHIBITED_PATTERNS = [
    r'dall.?e',
    r'DALL.?E',
    r'dalle3',
    r'dalle_3',
    r'dall_e'
]

# File extensions to scan
SCAN_EXTENSIONS = ['.py', '.js', '.tsx', '.ts', '.json', '.md', '.yml', '.yaml']

# Files/directories to exclude from scanning
EXCLUDE_PATTERNS = [
    '.git/',
    '__pycache__/',
    'node_modules/',
    '.venv/',             # Virtual environment
    'venv/',              # Virtual environment  
    '.content-policy.md',  # Policy definition file
    'Audit.md',           # Audit documentation
    'Agent Coordination Guide.md',  # Coordination documentation
    'scripts/policy_lint.py',  # This linter itself
    'docs/archive/',      # Archived documentation
    'GA_HANDOFF_REPORT.md', # Historical handoff documentation
    'plan_aware_image_service.py'  # Contains policy enforcement code
]

def should_exclude_file(file_path: str) -> bool:
    """Check if file should be excluded from scanning"""
    for pattern in EXCLUDE_PATTERNS:
        if pattern in file_path:
            return True
    return False

def scan_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """Scan a file for prohibited patterns"""
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                for pattern in PROHIBITED_PATTERNS:
                    matches = re.findall(pattern, line, re.IGNORECASE)
                    if matches:
                        for match in matches:
                            violations.append((line_num, match, line.strip()))
    except (UnicodeDecodeError, PermissionError):
        # Skip binary or inaccessible files
        pass
    
    return violations

def main():
    """Main linter function"""
    project_root = Path(__file__).parent.parent
    total_violations = 0
    violation_files = []
    
    print("🔍 DALL-E Policy Linter - Scanning codebase...")
    print(f"📂 Project root: {project_root}")
    print(f"🚫 Prohibited patterns: {PROHIBITED_PATTERNS}")
    print()
    
    # Scan all files in project
    for file_path in project_root.rglob('*'):
        if not file_path.is_file():
            continue
            
        if file_path.suffix not in SCAN_EXTENSIONS:
            continue
            
        rel_path = str(file_path.relative_to(project_root))
        if should_exclude_file(rel_path):
            continue
            
        violations = scan_file(file_path)
        if violations:
            violation_files.append((rel_path, violations))
            total_violations += len(violations)
    
    # Report results
    if total_violations == 0:
        print("✅ POLICY COMPLIANCE: No DALL-E references found in codebase")
        return 0
    else:
        print(f"❌ POLICY VIOLATIONS: Found {total_violations} DALL-E references in {len(violation_files)} files")
        print()
        
        for file_path, violations in violation_files:
            print(f"📁 {file_path}:")
            for line_num, match, line in violations:
                print(f"   Line {line_num}: '{match}' in '{line[:80]}{'...' if len(line) > 80 else ''}'")
            print()
        
        print("🚨 ACTION REQUIRED: Remove all DALL-E references before deployment")
        return 1

if __name__ == "__main__":
    sys.exit(main())