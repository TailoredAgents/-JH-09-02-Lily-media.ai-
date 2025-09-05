#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Versioning Migration Script

Automatically migrates routers to use the new versioned API system.
"""
import os
import re
from pathlib import Path

# Key routers from registry that need migration
ROUTER_FILES = [
    "auth_fastapi_users.py",
    "two_factor.py", 
    "admin.py",
    "user_credentials.py",
    "user_settings.py",
    "ai_suggestions.py",
    "memory.py",
    "workflow_v2.py",
    "monitoring.py",
    "diagnostics.py",
    "content_history.py",
    "notifications.py",
    "vector_search_production.py",
    "vector_search.py",
    "similarity.py",
    "integration_services.py",
    "feature_flags.py",
    "autonomous.py",
    "social_platforms.py",
    "social_inbox.py",
    "organizations.py",
    "system_logs.py",
    "database_health.py",
    "partner_oauth.py",
    "assistant_chat.py"
]

# Special cases that need legacy routing or custom handling
SPECIAL_CASES = {
    "auth_fastapi_users.py": "legacy",  # Keep legacy for backward compatibility
    "webhooks.py": "no_api_prefix",  # Webhooks don't need /api prefix
    "deep_research.py": "already_versioned",  # Already uses v1
    "assistant_chat.py": "root_api"  # Uses root /api prefix
}

def migrate_router_file(file_path):
    """
    Migrate a single router file to use versioned routing.
    
    Args:
        file_path: Path to the router file
        
    Returns:
        True if migration was successful, False otherwise
    """
    try:
        content = file_path.read_text()
        original_content = content
        
        filename = file_path.name
        
        # Skip if already migrated
        if "create_versioned_router" in content:
            print(f"✅ {filename} - Already migrated")
            return True
            
        # Handle special cases
        if filename in SPECIAL_CASES:
            special_case = SPECIAL_CASES[filename]
            
            if special_case == "legacy":
                # Use legacy routing
                content = add_import(content)
                content = replace_router_declaration(content, legacy=True)
            elif special_case == "no_api_prefix":
                # Skip webhooks - they don't need versioning
                print(f"⏭️  {filename} - Skipped (no API prefix needed)")
                return True
            elif special_case == "already_versioned":
                # Already properly versioned
                print(f"✅ {filename} - Already properly versioned")
                return True
            elif special_case == "root_api":
                # Uses root /api prefix
                content = add_import(content)
                content = replace_router_declaration(content, root_api=True)
        else:
            # Standard migration
            content = add_import(content)
            content = replace_router_declaration(content)
        
        # Only write if content changed
        if content != original_content:
            file_path.write_text(content)
            print(f"✅ {filename} - Migrated successfully")
        else:
            print(f"ℹ️  {filename} - No changes needed")
            
        return True
        
    except Exception as e:
        print(f"❌ {filename} - Error: {e}")
        return False

def add_import(content: str) -> str:
    """Add the versioned router import."""
    if "from backend.core.api_version import create_versioned_router" in content:
        return content
        
    # Find the last import line
    lines = content.split('\n')
    last_import_idx = -1
    
    for i, line in enumerate(lines):
        if line.strip().startswith(('import ', 'from ')) and 'backend' in line:
            last_import_idx = i
    
    if last_import_idx >= 0:
        lines.insert(last_import_idx + 1, "from backend.core.api_version import create_versioned_router")
        return '\n'.join(lines)
    
    return content

def replace_router_declaration(content: str, legacy: bool = False, root_api: bool = False) -> str:
    """Replace APIRouter declaration with versioned router."""
    
    # Pattern to match router = APIRouter(...)
    pattern = r'router\s*=\s*APIRouter\s*\(\s*prefix\s*=\s*["\']([^"\']*)["\']([^)]*)\)'
    
    def replacement(match):
        prefix = match.group(1)
        other_args = match.group(2)
        
        if legacy:
            # Use legacy routing
            new_prefix = prefix.replace("/api", "")  # Remove /api prefix
            return f'router = create_versioned_router(prefix="{new_prefix}"{other_args}, legacy=True)'
        elif root_api:
            # Root /api prefix
            new_prefix = prefix.replace("/api", "")  # Remove /api prefix  
            return f'router = create_versioned_router(prefix="{new_prefix}"{other_args})'
        else:
            # Standard versioned routing
            new_prefix = prefix.replace("/api", "")  # Remove /api prefix
            return f'router = create_versioned_router(prefix="{new_prefix}"{other_args})'
    
    return re.sub(pattern, replacement, content)

def main():
    """Run the migration."""
    api_dir = Path("/Users/jeffreyhacker/Lily-Media.AI/socialmedia2/backend/api")
    
    print("🚀 Starting API versioning migration...")
    print(f"📁 Target directory: {api_dir}")
    print("=" * 50)
    
    success_count = 0
    total_count = 0
    
    for filename in ROUTER_FILES:
        file_path = api_dir / filename
        if file_path.exists():
            total_count += 1
            if migrate_router_file(file_path):
                success_count += 1
        else:
            print(f"⚠️  {filename} - File not found")
    
    print("=" * 50)
    print(f"📊 Migration Results: {success_count}/{total_count} successful")
    
    if success_count == total_count:
        print("🎉 All migrations completed successfully!")
    else:
        print(f"⚠️  {total_count - success_count} files had issues")

if __name__ == "__main__":
    main()