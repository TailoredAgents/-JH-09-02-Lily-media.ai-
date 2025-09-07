#!/usr/bin/env python3
"""
Migration Rollback Utility

Provides emergency rollback capabilities for database migrations
using the automated backups created by migration guardrails.

Addresses P0-12c: Add migration guardrails with automated backup and rollback procedures
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import argparse
from dataclasses import dataclass

# Import the MigrationGuardrails class
from migration_guardrails import MigrationGuardrails, MigrationContext


class MigrationRollback:
    """Emergency rollback utility for database migrations"""
    
    def __init__(self, database_url: str, backup_dir: str = "migration-backups"):
        self.database_url = database_url
        self.backup_dir = Path(backup_dir)
        self.guardrails = MigrationGuardrails(database_url, backup_dir)
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging for rollback operations"""
        logger = logging.getLogger("migration_rollback")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def list_available_rollbacks(self) -> List[Dict[str, Any]]:
        """List all available rollback points with context"""
        rollback_points = []
        
        # Get all backup files
        backups = self.guardrails.list_available_backups()
        
        for backup in backups:
            # Extract migration ID from filename
            filename = backup['file']
            if filename.startswith('backup_migration_'):
                migration_id = filename.replace('backup_', '').replace('.sql', '')
                
                # Try to load migration context
                context = self.guardrails.load_migration_context(migration_id)
                
                rollback_point = {
                    'migration_id': migration_id,
                    'backup_file': backup['file'],
                    'backup_path': backup['path'],
                    'backup_size': backup['size_bytes'],
                    'created': backup['created'],
                    'age_hours': backup['age_hours'],
                    'context': context
                }
                
                if context:
                    rollback_point.update({
                        'pre_migration_head': context.alembic_head_before,
                        'environment': context.environment,
                        'migration_files': context.migration_files
                    })
                
                rollback_points.append(rollback_point)
        
        # Sort by creation time, newest first
        rollback_points.sort(key=lambda x: x['created'], reverse=True)
        return rollback_points
    
    def validate_rollback_safety(self, migration_id: str) -> Tuple[bool, List[str]]:
        """Validate that a rollback operation is safe to perform"""
        warnings = []
        
        # Load migration context
        context = self.guardrails.load_migration_context(migration_id)
        if not context:
            return False, ["Migration context not found - cannot validate rollback safety"]
        
        # Check backup file exists
        backup_path = Path(context.backup_path)
        if not backup_path.exists():
            return False, [f"Backup file not found: {backup_path}"]
        
        # Check backup file integrity
        if backup_path.stat().st_size == 0:
            return False, ["Backup file is empty - cannot perform rollback"]
        
        # Check environment
        current_env = os.getenv("ENVIRONMENT", "unknown")
        if context.environment != current_env:
            warnings.append(f"Environment mismatch: backup from {context.environment}, current {current_env}")
        
        # Check time since backup
        backup_age_hours = (datetime.now(timezone.utc) - datetime.fromisoformat(context.timestamp.replace('Z', '+00:00'))).total_seconds() / 3600
        
        if backup_age_hours > 24:
            warnings.append(f"Backup is {backup_age_hours:.1f} hours old - data loss may occur")
        elif backup_age_hours > 6:
            warnings.append(f"Backup is {backup_age_hours:.1f} hours old - recent changes may be lost")
        
        # Check current database state
        current_head = self.guardrails.get_current_alembic_head()
        if current_head == context.alembic_head_before:
            warnings.append("Database appears to already be at the rollback target version")
        
        return True, warnings
    
    def emergency_rollback(self, migration_id: str, confirm: bool = False) -> bool:
        """Perform emergency rollback to a specific migration point"""
        
        if not confirm:
            self.logger.error("❌ Emergency rollback requires explicit confirmation")
            self.logger.error("   Use --confirm flag to proceed with rollback")
            return False
        
        self.logger.warning(f"🚨 Starting EMERGENCY ROLLBACK for migration: {migration_id}")
        
        # Load migration context
        context = self.guardrails.load_migration_context(migration_id)
        if not context:
            self.logger.error(f"❌ Migration context not found: {migration_id}")
            return False
        
        # Validate rollback safety
        is_safe, warnings = self.validate_rollback_safety(migration_id)
        
        if not is_safe:
            self.logger.error("❌ Rollback validation failed:")
            for warning in warnings:
                self.logger.error(f"   • {warning}")
            return False
        
        # Display warnings
        if warnings:
            self.logger.warning("⚠️ Rollback warnings:")
            for warning in warnings:
                self.logger.warning(f"   • {warning}")
        
        try:
            # Create emergency backup of current state before rollback
            self.logger.info("💾 Creating emergency backup of current state...")
            emergency_backup_id = f"emergency_rollback_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            emergency_backup_path = self.guardrails.create_backup(emergency_backup_id)
            
            # Perform the rollback
            self.logger.warning(f"🔄 Rolling back database to {context.timestamp}")
            self.logger.info(f"📁 Using backup file: {context.backup_path}")
            
            rollback_success = self.guardrails.rollback_from_backup(context.backup_path)
            
            if rollback_success:
                # Verify rollback success
                current_head = self.guardrails.get_current_alembic_head()
                self.logger.info(f"✅ Rollback completed successfully")
                self.logger.info(f"📊 Current database head: {current_head}")
                self.logger.info(f"💾 Emergency backup created: {emergency_backup_path}")
                
                # Create rollback record
                rollback_record = {
                    "rollback_timestamp": datetime.now(timezone.utc).isoformat(),
                    "original_migration_id": migration_id,
                    "rolled_back_from_head": self.guardrails.get_current_alembic_head(),
                    "rolled_back_to_head": context.alembic_head_before,
                    "backup_used": context.backup_path,
                    "emergency_backup_created": emergency_backup_path,
                    "performed_by": os.getenv("USER", "unknown")
                }
                
                rollback_file = self.backup_dir / f"rollback_record_{emergency_backup_id}.json"
                with open(rollback_file, 'w') as f:
                    json.dump(rollback_record, f, indent=2)
                
                self.logger.info(f"📋 Rollback record saved: {rollback_file}")
                return True
            else:
                self.logger.error("❌ Rollback failed")
                return False
                
        except Exception as e:
            self.logger.error(f"💥 Emergency rollback failed with exception: {e}")
            return False
    
    def show_rollback_status(self) -> None:
        """Show current rollback status and available options"""
        print("🔄 MIGRATION ROLLBACK STATUS")
        print("=" * 50)
        
        # Show current database state
        current_head = self.guardrails.get_current_alembic_head()
        current_schema_hash = self.guardrails.get_schema_hash()
        
        print(f"\n📊 Current Database State:")
        print(f"   • Alembic Head: {current_head}")
        print(f"   • Schema Hash: {current_schema_hash[:16]}...")
        print(f"   • Environment: {os.getenv('ENVIRONMENT', 'unknown')}")
        
        # Show available rollback points
        rollback_points = self.list_available_rollbacks()
        
        if not rollback_points:
            print("\n⚠️ No rollback points available")
            return
        
        print(f"\n📁 Available Rollback Points ({len(rollback_points)} found):")
        
        for i, point in enumerate(rollback_points[:10]):  # Show max 10 most recent
            age_str = f"{point['age_hours']:.1f}h ago" if point['age_hours'] < 24 else f"{point['age_hours']/24:.1f}d ago"
            size_str = f"{point['backup_size']:,} bytes"
            
            print(f"\n   {i+1}. Migration: {point['migration_id']}")
            print(f"      • Created: {age_str}")
            print(f"      • Size: {size_str}")
            print(f"      • Environment: {point.get('environment', 'unknown')}")
            
            if point.get('pre_migration_head'):
                print(f"      • Pre-migration Head: {point['pre_migration_head']}")
            
            if point.get('migration_files'):
                file_count = len(point['migration_files'])
                print(f"      • Migration Files: {file_count} files")
        
        if len(rollback_points) > 10:
            print(f"\n   ... and {len(rollback_points) - 10} more rollback points")
        
        print(f"\n💡 To perform rollback: python scripts/migration-rollback.py --rollback <migration_id> --confirm")
        print(f"💡 To validate rollback: python scripts/migration-rollback.py --validate <migration_id>")
    
    def validate_specific_rollback(self, migration_id: str) -> None:
        """Validate a specific rollback point"""
        print(f"🔍 VALIDATING ROLLBACK: {migration_id}")
        print("=" * 50)
        
        is_safe, warnings = self.validate_rollback_safety(migration_id)
        
        if is_safe:
            print("✅ Rollback validation PASSED")
            
            if warnings:
                print("\n⚠️ Warnings:")
                for warning in warnings:
                    print(f"   • {warning}")
        else:
            print("❌ Rollback validation FAILED")
            print("\n🚫 Errors:")
            for error in warnings:  # warnings contains errors when is_safe is False
                print(f"   • {error}")
        
        # Show rollback point details
        context = self.guardrails.load_migration_context(migration_id)
        if context:
            print(f"\n📋 Rollback Point Details:")
            print(f"   • Backup Path: {context.backup_path}")
            print(f"   • Backup Size: {context.backup_size_bytes:,} bytes")
            print(f"   • Created: {context.timestamp}")
            print(f"   • Environment: {context.environment}")
            print(f"   • Pre-migration Head: {context.alembic_head_before}")
            print(f"   • Migration Files: {len(context.migration_files)} files")


def main():
    """Main entry point for migration rollback utility"""
    
    parser = argparse.ArgumentParser(description="Emergency database migration rollback utility")
    parser.add_argument("--database-url", required=True, help="Database connection URL")
    parser.add_argument("--backup-dir", default="migration-backups", help="Backup directory")
    
    # Action arguments
    parser.add_argument("--status", action="store_true", help="Show rollback status")
    parser.add_argument("--list", action="store_true", help="List available rollback points")
    parser.add_argument("--validate", metavar="MIGRATION_ID", help="Validate specific rollback point")
    parser.add_argument("--rollback", metavar="MIGRATION_ID", help="Perform emergency rollback")
    parser.add_argument("--confirm", action="store_true", help="Confirm destructive rollback operation")
    
    args = parser.parse_args()
    
    try:
        rollback_tool = MigrationRollback(args.database_url, args.backup_dir)
        
        if args.status or (not any([args.list, args.validate, args.rollback])):
            rollback_tool.show_rollback_status()
            
        elif args.list:
            rollback_points = rollback_tool.list_available_rollbacks()
            print(f"Found {len(rollback_points)} rollback points")
            for point in rollback_points:
                print(f"• {point['migration_id']} ({point['age_hours']:.1f}h ago)")
                
        elif args.validate:
            rollback_tool.validate_specific_rollback(args.validate)
            
        elif args.rollback:
            success = rollback_tool.emergency_rollback(args.rollback, args.confirm)
            sys.exit(0 if success else 1)
    
    except Exception as e:
        print(f"💥 Migration rollback utility failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()